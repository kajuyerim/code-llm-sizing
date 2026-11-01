"""Reads Claude Code session transcripts.

The JSONL format is internal to Claude Code and changes between versions, so every
assumption about it lives in this file. Adapters for other agents (Cursor, Codex)
would sit next to this one and return the same Session objects.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_HOME = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
PROJECTS_DIR = CLAUDE_HOME / "projects"


@dataclass
class Message:
    uuid: str
    role: str
    timestamp: str
    text: str


@dataclass
class Session:
    session_id: str
    branch: str | None
    messages: list[Message]


def encode_project(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def auto_memory_dir(repo_root: Path) -> Path:
    return PROJECTS_DIR / encode_project(repo_root) / "memory"


def load_sessions(
    app_root: Path, since: datetime | None, until: datetime, include_sidechains: bool = False,
    selected: list[str] | None = None,
) -> list[Session]:
    """Sessions with at least one developer or agent message inside the window."""
    sessions = []
    for directory in _project_dirs(app_root):
        for path in sorted(directory.glob("*.jsonl")):
            if selected is not None and path.stem not in selected:
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if since and modified < since:
                continue
            session = _parse(path, app_root, since, until, include_sidechains)
            if session.messages:
                sessions.append(session)
    if selected is not None:
        ids = [s.session_id for s in sessions]
        if len(ids) != len(set(ids)):
            raise ValueError("Selected conversation has an ambiguous session ID")
        if set(selected) != set(ids):
            raise ValueError("Selected conversation is missing or has no messages before the cutoff")
    return sessions


def to_markdown(session: Session, max_chars: int) -> tuple[str, set[str]]:
    """Render a session for agents. Keeps the newest messages when it is too long."""
    blocks = [f"[msg:{m.uuid}] {m.role} @ {m.timestamp}\n{m.text}\n" for m in session.messages]
    kept, size = [], 0
    for message, block in zip(reversed(session.messages), reversed(blocks)):
        if kept and size + len(block) > max_chars:
            break
        kept.append((message, block))
        size += len(block)
    kept.reverse()

    header = [f"# Session {session.session_id}", "", f"Branch: {session.branch or 'unknown'}"]
    if len(kept) < len(blocks):
        header.append(f"Older messages dropped: {len(blocks) - len(kept)} of {len(blocks)}")
    text = "\n".join(header) + "\n\n" + "\n".join(block for _, block in kept)
    return text, {message.uuid for message, _ in kept}


def _project_dirs(app_root: Path) -> list[Path]:
    # Sessions started in a subfolder get their own project dir; they share this prefix.
    prefix = encode_project(app_root)
    if not PROJECTS_DIR.is_dir():
        return []
    return [
        d for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and (d.name == prefix or d.name.startswith(prefix + "-"))
    ]


def _parse(
    path: Path, app_root: Path, since: datetime | None, until: datetime, include_sidechains: bool
) -> Session:
    messages, branch = [], None
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # the session may still be writing its last line
            if record.get("type") not in ("user", "assistant") or record.get("isMeta"):
                continue
            if record.get("isSidechain") and not include_sidechains:
                continue
            if not _inside(record.get("cwd"), app_root):
                continue
            stamp = _timestamp(record.get("timestamp"))
            if stamp is None or stamp > until or (since and stamp < since):
                continue
            text = _render(record)
            if text:
                branch = record.get("gitBranch") or branch
                messages.append(Message(record.get("uuid", ""), record["type"], record["timestamp"], text))
    return Session(path.stem, branch, messages)


def _render(record: dict) -> str:
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content or []:
        if block.get("type") == "text":
            parts.append(block.get("text", "").strip())
        elif block.get("type") == "tool_use":
            parts.append(f"[tool {block.get('name')}] {_tool_target(block.get('input') or {})}".rstrip())
        # Tool results and thinking are dropped: they are large and rarely carry decisions.
    return "\n".join(part for part in parts if part)


def _tool_target(args: dict) -> str:
    for key in ("file_path", "path", "pattern", "command", "url"):
        if key in args:
            return str(args[key])[:200]
    return ""


def _inside(cwd: str | None, root: Path) -> bool:
    if not cwd:
        return True
    path = Path(cwd)
    return path == root or root in path.parents


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
