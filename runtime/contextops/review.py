"""Deterministic checks between the specialists and the writer.

A record reaches the writer only if its target is inside the proposing agent's
assignment, every evidence locator resolves to something real in the pack, and its
text does not look like it carries a secret.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from contextops import gitutil
from contextops.access import writable
from contextops.evidence import Evidence
from contextops.run import RunContext
from contextops.strategies import WorkerResult

SECRET_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"gh[pousr]_[A-Za-z0-9]{36,}",
        r"sk-[A-Za-z0-9_-]{20,}",
        r"xox[abpr]-[A-Za-z0-9-]{10,}",
        r"AIza[0-9A-Za-z_-]{35}",
        r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^\s'\"]{12,}",
    )
]


COMMIT_LOG = {"diff/commits.txt", "commits.txt"}


@dataclass
class Review:
    accepted: list[dict] = field(default_factory=list)
    deferred: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    no_change: list[dict] = field(default_factory=list)
    handoffs: list[dict] = field(default_factory=list)
    unowned: list[dict] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def review_results(results: list[WorkerResult], ctx: RunContext, evidence: Evidence) -> Review:
    review = Review()
    seen = set()
    for result in results:
        worker, run = result.worker, result.run
        if run.output is None:
            review.failures.append(f"{worker.label}: {run.error or run.status}")
            continue

        review.handoffs += [{**item, "from": worker.label} for item in run.output["handoffs"]]
        review.unowned += [{**item, "from": worker.label} for item in run.output["unowned"]]

        for record in run.output["records"]:
            record = {**record, "agent": worker.label, "target": _relative(record["target"], ctx.kb_snapshot)}
            key = (record["target"], record["fact_id"], record["op"], record["text"])
            if key in seen:
                continue
            seen.add(key)
            _file(record, worker.owns, ctx, evidence, review)
    return review


def _file(record: dict, owns: str, ctx: RunContext, evidence: Evidence, review: Review) -> None:
    if record["op"] == "NO_CHANGE":
        review.no_change.append(record)
        return
    problem = _problem(record, owns, ctx, evidence)
    if problem:
        review.rejected.append({**record, "rejected_because": problem})
    elif ctx.profile is not None and record["op"] != "NEEDS_REVIEW":
        categories = {item["id"]: item["enabled"] for item in ctx.profile["categories"]}
        category = record.get("category")
        if category not in categories:
            review.deferred.append({**record, "policy_reason": "Missing or unknown profile category"})
        elif not categories[category]:
            review.rejected.append({**record, "rejected_because": "Category is disabled in the active profile"})
        else:
            review.accepted.append(record)
    elif record["op"] == "NEEDS_REVIEW":
        review.deferred.append(record)
    else:
        review.accepted.append(record)


def _problem(record: dict, owns: str, ctx: RunContext, evidence: Evidence) -> str | None:
    target = record["target"]
    if not writable(target):
        return "target is not a permitted knowledge Markdown path"
    if not (target == owns or (owns.endswith("/") and target.startswith(owns))):
        return f"target {target} is outside the assignment {owns}"
    scope = record["scope"]
    if scope != "company" and not scope.startswith(("app:", "tool:")):
        return "scope must be company, app:<name>, or tool:<name>"
    if not record["evidence"]:
        return "no evidence"
    # Keep a record whose evidence partly resolves; drop and report only the locators that do not.
    # One bad locator used to discard a supported record together with its valid evidence.
    issues = [(item, _locator_issue(item, ctx, evidence)) for item in record["evidence"]]
    valid = [item for item, issue in issues if not issue]
    if not valid:
        return issues[0][1]
    dropped = [{"locator": item, "issue": issue} for item, issue in issues if issue]
    if dropped:
        record["evidence"] = valid
        record["dropped_locators"] = dropped

    text = " ".join(
        [record["text"], record["reason"]] + [item.get("quote", "") for item in record["evidence"]]
    )
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        return "possible secret in the proposed text or its evidence"
    return None


def _locator_issue(item: dict, ctx: RunContext, evidence: Evidence) -> str | None:
    kind = item["kind"]
    if kind == "conversation":
        session = item.get("session", "").removesuffix(".md")
        if session not in evidence.messages:
            return f"unknown session {session or '(missing)'}"
        if item.get("message") not in evidence.messages[session]:
            return f"message {item.get('message')} is not in session {session}"
    elif kind == "diff":
        path = _relative(item.get("path", ""), ctx.app_snapshot)
        if path in COMMIT_LOG:
            return None  # commit messages are part of the frozen diff evidence
        if path not in evidence.changed_files:
            return f"{path} is not part of the diff"
    elif kind == "source":
        path = _relative(item.get("path", ""), ctx.app_snapshot)
        if not gitutil.file_exists(ctx.app_root, ctx.head_sha, path):
            return f"{path} does not exist at {ctx.head_sha[:7]}"
    elif kind == "memory":
        path = _relative(item.get("path", ""), ctx.pack)
        if path not in evidence.memory_files:
            return f"unknown memory file {path}"
    return None


def _relative(path: str, root: Path) -> str:
    """Agents sometimes cite absolute paths inside the run; store everything relative."""
    prefix = str(root).rstrip("/") + "/"
    return path.removeprefix(prefix).removeprefix("./")
