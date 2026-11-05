"""The initializer: turns init.md into the concrete workers of this run.

It is plain code on purpose. Choosing workers is a lookup, and keeping it
deterministic means both experiments start from exactly the same roster.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from contextops import frontmatter
from contextops.agents import AgentSpec, load_agent
from contextops.config import InitConfig, WorkerEntry
from contextops.evidence import Evidence


@dataclass
class Worker:
    label: str
    spec: AgentSpec
    owns: str
    tool: str | None
    reason: str

    @classmethod
    def from_record(cls, record: dict) -> "Worker":
        """Read archived worker metadata without modifying its historical names."""
        data = dict(record)
        if "tool" not in data and "product" in data:
            data["tool"] = data.pop("product")
        return cls(**data)


def plan_workers(config: InitConfig, evidence: Evidence) -> tuple[list[Worker], list[str]]:
    """Return the workers to start and a note for every worker that was skipped."""
    conversation = evidence.conversation_text().lower()
    planned, skipped = [], []
    for entry in config.workers:
        spec = load_agent(entry.agent, config.default_model)
        for owns, tool in _assignments(entry, config.kb_root):
            label = f"{spec.name}:{tool}" if tool else spec.name
            if entry.run == "always":
                reason = "always"
            else:
                reason = _relevance(config.kb_root / owns, evidence.changed_files, conversation)
            if reason:
                planned.append(Worker(label, spec, owns, tool, reason))
            else:
                skipped.append(f"{label}: nothing in the diff or conversation points at {owns}")
    return planned, skipped


def _assignments(entry: WorkerEntry, kb_root: Path) -> list[tuple[str, str | None]]:
    if entry.owns:
        return [(entry.owns, None)]
    folders = sorted(p for p in kb_root.glob(entry.for_each.rstrip("/")) if p.is_dir())
    return [(f"{p.relative_to(kb_root).as_posix()}/", p.name) for p in folders]


def _relevance(owned: Path, changed: list[str], conversation: str) -> str | None:
    """Why this knowledge area looks relevant, or None.

    Hints come from the owned document's frontmatter (a folder's README.md):
    `fileMatchPattern` globs over changed paths and `keywords` searched in the
    conversation. An area without hints always runs rather than being silently skipped.
    """
    hints_file = owned / "README.md" if owned.is_dir() else owned
    meta = frontmatter.read(hints_file)[0] if hints_file.is_file() else {}
    patterns = meta.get("fileMatchPattern") or []
    keywords = meta.get("keywords") or []
    if not patterns and not keywords:
        return "no relevance hints"

    for path in changed:
        if any(_matches(path, pattern) for pattern in patterns):
            return f"diff touches {path}"
    for word in keywords:
        if re.search(rf"\b{re.escape(word.lower())}\b", conversation):
            return f"conversation mentions '{word}'"
    return None


def _matches(path: str, pattern: str) -> bool:
    # fnmatch has no real "**"; also try the pattern without it so root-level files match.
    return fnmatch(path, pattern) or (pattern.startswith("**/") and fnmatch(path, pattern[3:]))
