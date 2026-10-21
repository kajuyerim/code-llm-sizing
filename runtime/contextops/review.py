"""Structural and locator checks, not a semantic truth evaluator."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from contextops.agents import AgentResult
from contextops.config import Worker
from contextops.evidence import messages
from contextops.files import inside, knowledge_path, load, owned, relative_path
from contextops.runs import Run

SECRET_PATTERNS = [re.compile(p) for p in (
    r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"gh[pousr]_[A-Za-z0-9]{36,}", r"sk-[A-Za-z0-9_-]{20,}",
    r"xox[abpr]-[A-Za-z0-9-]{10,}", r"AIza[0-9A-Za-z_-]{35}",
    r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?[^\s'\"]{12,}",
)]
ID = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d{3,})\s*\|", re.MULTILINE)


def secrets(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)


def ids(text: str) -> set[str]:
    return set(ID.findall(text))


@dataclass
class Review:
    accepted: list[dict] = field(default_factory=list)
    deferred: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    no_change: list[dict] = field(default_factory=list)
    handoffs: list[dict] = field(default_factory=list)
    unowned: list[dict] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


class Validator:
    def __init__(self, run: Run, manifest: dict):
        self.run = run
        self.messages = messages(run.pack)
        self.diff = load(run.pack / "diff/sections.json")
        self.memory = {m["path"] for m in manifest["memory_files"]}

    def evidence(self, entries: list[dict]) -> None:
        if not entries:
            raise ValueError("at least one evidence locator is required")
        for item in entries:
            quote = item["quote"]
            if not quote.strip() or secrets(json.dumps(item)):
                raise ValueError("missing evidence quote or possible secret")
            kind = item["kind"]
            if kind == "conversation":
                message = self.messages.get((item["session"], item["message"]))
                if message is None or quote not in message["text"]:
                    raise ValueError("conversation UUID or verbatim quote does not resolve")
            elif kind == "source":
                path = inside(self.run.app_snapshot, item["path"])
                if not path.is_file():
                    raise ValueError("source locator is not a regular file at head")
                lines = path.read_text(encoding="utf-8").splitlines()
                line = item["line"]
                if line is None or line > len(lines) or quote not in "\n".join(lines[line - 1:line - 1 + len(quote.splitlines())]):
                    raise ValueError("source line and verbatim quote do not resolve")
            elif kind == "diff":
                name = relative_path(item["path"])
                if name not in self.diff or quote not in self.diff[name]:
                    raise ValueError("diff path or verbatim quote does not resolve")
            elif kind == "memory":
                name = relative_path(item["path"])
                if name not in self.memory or quote not in inside(self.run.pack, name).read_text(encoding="utf-8"):
                    raise ValueError("memory path or verbatim quote does not resolve")
            else:
                raise ValueError("unknown evidence kind")

    def record(self, record: dict, worker: Worker) -> None:
        target = knowledge_path(record["target"])
        if not owned(target, worker.owns):
            raise ValueError("target is outside the worker assignment")
        if secrets("\n".join((record["text"], record["reason"], record["scope"]))) or "\u2014" in record["text"]:
            raise ValueError("possible secret or em dash in proposed text")
        if not record["reason"].strip():
            raise ValueError("reason must describe the change or inspected scope")
        if record["op"] == "NO_CHANGE":
            if record["fact_id"] is not None or record["merge_ids"]:
                raise ValueError("NO_CHANGE must have null fact_id and empty merge_ids")
            return
        self.evidence(record["evidence"])
        if not re.fullmatch(r"(?:company|app:[^\s]+|product:[^\s]+)", record["scope"]):
            raise ValueError("scope must be company, app:<name>, or product:<name>")
        path = inside(self.run.kb_snapshot, target)
        current = ids(path.read_text(encoding="utf-8")) if path.is_file() else set()
        fact_id = record["fact_id"]
        if record["op"] == "NEEDS_REVIEW":
            if fact_id is not None and fact_id not in current:
                raise ValueError("deferred existing fact ID does not exist")
            return
        if not isinstance(fact_id, str) or not re.fullmatch(rf"{worker.prefix}-\d{{3,}}", fact_id):
            raise ValueError(f"fact ID must use prefix {worker.prefix}")
        if record["op"] == "ADD":
            if fact_id in current:
                raise ValueError("ADD would reuse an existing fact ID")
        elif fact_id not in current:
            raise ValueError("operation refers to a missing fact ID")
        if record["op"] in ("ADD", "UPDATE", "MERGE") and not record["text"].strip():
            raise ValueError("operation requires final wording")
        if record["op"] in ("ADD", "UPDATE", "MERGE"):
            row = record["text"].strip()
            if "\n" in row or not row.endswith("|") or ID.findall(row) != [fact_id]:
                raise ValueError("final wording must be one complete Markdown table row with fact_id in the first cell")
        if record["op"] == "MERGE":
            removed = record["merge_ids"]
            if not removed or len(removed) != len(set(removed)) or fact_id in removed or not set(removed) <= current:
                raise ValueError("MERGE requires distinct existing merge_ids, excluding the retained fact")
            if fact_id != min([fact_id, *removed], key=lambda x: int(x.rsplit("-", 1)[1])):
                raise ValueError("MERGE must retain the lowest fact ID")
        elif record["merge_ids"]:
            raise ValueError("merge_ids must be empty except for MERGE")


def review_results(run: Run, manifest: dict, results: list[tuple[Worker, AgentResult]]) -> Review:
    validator, review = Validator(run, manifest), Review()
    candidates = []
    for worker, result in results:
        if not result.succeeded:
            review.failures.append(f"{worker.label}: {result.status}; {'; '.join(result.errors)}")
            continue
        for index, record in enumerate(result.output["records"]):
            tagged = {**record, "agent": worker.label, "record_id": f"{worker.label}/{index + 1}"}
            try:
                validator.record(record, worker)
                if record["op"] == "NO_CHANGE":
                    review.no_change.append(tagged)
                elif record["op"] == "NEEDS_REVIEW":
                    review.deferred.append(tagged)
                else:
                    candidates.append(tagged)
            except (ValueError, OSError, TypeError, UnicodeError) as exc:
                # Rejected payloads stay local; reports include the ID and error only.
                review.rejected.append({**tagged, "rejected_because": str(exc)})
        for category in ("handoffs", "unowned"):
            for item in result.output[category]:
                try:
                    if secrets(json.dumps(item)):
                        raise ValueError("possible secret in finding")
                    validator.evidence(item["evidence"])
                    if category == "handoffs":
                        knowledge_path(item["to"])
                    getattr(review, category).append({**item, "agent": worker.label,
                                                       "finding_id": f"{run.run_id}/{worker.label}/{category}/{len(getattr(review, category)) + 1}"})
                except (ValueError, OSError, TypeError, UnicodeError) as exc:
                    review.failures.append(f"{worker.label}: discarded {category} item ({exc})")
    owners = {}
    for record in candidates:
        for fact_id in [record["fact_id"], *record["merge_ids"]]:
            owners.setdefault((record["target"], fact_id), []).append(record["record_id"])
    conflicts = {record_id for group in owners.values() if len(group) > 1 for record_id in group}
    for record in candidates:
        if record["record_id"] in conflicts:
            review.deferred.append({**record, "reason": "Conflicting operations on the same fact; human decision required."})
        else:
            review.accepted.append(record)
    return review
