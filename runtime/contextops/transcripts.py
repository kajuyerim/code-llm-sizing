"""Read local Claude Code JSONL as evidence. This internal format is unverified."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def project_directories(application: Path) -> list[Path]:
    projects = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "projects"
    prefix = re.sub(r"[^A-Za-z0-9]", "-", str(application.resolve()))
    if not projects.is_dir():
        return []
    # Long encoded directory names are not guessed; missing evidence stops a run.
    return sorted(p for p in projects.iterdir() if p.is_dir() and not p.is_symlink()
                  and (p.name == prefix or p.name.startswith(prefix + "-")))


def timestamp(value: str | None) -> datetime | None:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
        return result if result and result.tzinfo else None
    except (ValueError, AttributeError):
        return None


def read(application: Path, since: str | None, cutoff: str, settings: dict) -> tuple[list[dict], dict]:
    lower, upper = timestamp(since), timestamp(cutoff)
    sessions, seen = [], set()
    exclusions = {"outside_window": 0, "sidechains": 0, "meta_or_other": 0,
                  "outside_repository": 0, "invalid_json": 0, "invalid_reference": 0,
                  "tool_results_and_thinking": 0, "truncated_messages": 0,
                  "duplicate_messages": 0, "unconfirmed_repository": 0}
    directories = project_directories(application)
    exact_directory = re.sub(r"[^A-Za-z0-9]", "-", str(application.resolve()))
    for directory in directories:
        for path in sorted(directory.glob("*.jsonl")):
            if path.is_symlink():
                continue
            messages = []
            with path.open(encoding="utf-8", errors="replace") as stream:
                for order, line in enumerate(stream):
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        exclusions["invalid_json"] += 1
                        continue
                    if not isinstance(entry, dict):
                        exclusions["invalid_json"] += 1
                        continue
                    if entry.get("type") not in ("user", "assistant") or entry.get("isMeta"):
                        exclusions["meta_or_other"] += 1
                        continue
                    if entry.get("isSidechain") and not settings["include_sidechains"]:
                        exclusions["sidechains"] += 1
                        continue
                    cwd = entry.get("cwd")
                    if cwd:
                        location = Path(cwd).resolve()
                        if location != application and application not in location.parents:
                            exclusions["outside_repository"] += 1
                            continue
                    elif directory.name != exact_directory:
                        exclusions["unconfirmed_repository"] += 1
                        continue
                    stamp = timestamp(entry.get("timestamp"))
                    if stamp is None or stamp > upper or (lower and stamp < lower):
                        exclusions["outside_window"] += 1
                        continue
                    message_id = entry.get("uuid")
                    session_id = entry.get("sessionId") or path.stem
                    if not all(isinstance(s, str) and re.fullmatch(r"[A-Za-z0-9_-]+", s) for s in (session_id, message_id)):
                        exclusions["invalid_reference"] += 1
                        continue
                    if (session_id, message_id) in seen:
                        exclusions["duplicate_messages"] += 1
                        continue
                    content = (entry.get("message") or {}).get("content", "")
                    parts = []
                    if isinstance(content, str):
                        parts.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if block.get("type") == "text":
                                parts.append(str(block.get("text", "")))
                            elif block.get("type") == "tool_use":
                                args = block.get("input") or {}
                                target = next((str(args[k])[:200] for k in ("file_path", "path", "pattern", "command", "url") if k in args), "")
                                parts.append(f"[tool {block.get('name', 'unknown')}] {target}")
                            else:
                                exclusions["tool_results_and_thinking"] += 1
                    text = "\n".join(parts).strip()
                    if text:
                        seen.add((session_id, message_id))
                        messages.append({"session": session_id, "message": message_id, "role": entry["type"],
                                         "timestamp": stamp.astimezone(timezone.utc).isoformat(), "order": order, "text": text,
                                         "source_file": str(path),
                                         "branch": entry.get("gitBranch")})
            by_session = {}
            for message in messages:
                by_session.setdefault(message["session"], []).append(message)
            sessions.extend({"session": sid, "messages": items} for sid, items in by_session.items())
    combined = {}
    for session in sessions:
        combined.setdefault(session["session"], []).extend(session["messages"])
    result = []
    for sid, messages in sorted(combined.items()):
        # Keep transcript order even when recorded clocks move backward. Discovery
        # order is deterministic; source_file/order retain the original locators.
        kept, size = [], 0
        for message in reversed(messages):
            length = len(message["text"]) + 160
            if size + length > settings["max_chars_per_session"]:
                break
            kept.append(message)
            size += length
        exclusions["truncated_messages"] += len(messages) - len(kept)
        if kept:
            result.append({"session": sid, "messages": list(reversed(kept)), "dropped": len(messages) - len(kept)})
    return result, {"directories": [str(p) for p in directories], "exclusions": exclusions,
                    "selection": "all matching repository sessions within the time window; not task-specific"}
