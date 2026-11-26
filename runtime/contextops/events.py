"""Append-only local run events, separate from private provider logs."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def emit(directory: Path | None, kind: str, **fields) -> None:
    if directory is None:
        return
    event = {"id": uuid4().hex, "time": datetime.now(timezone.utc).isoformat(), "kind": kind, **fields}
    raw = (json.dumps(event, ensure_ascii=False) + "\n").encode()
    with (directory / "events.jsonl").open("ab", buffering=0) as stream:
        os.write(stream.fileno(), raw)


def message(directory: Path | None, label: str, text: str) -> None:
    from contextops.review import SECRET_PATTERNS

    text = text.strip()
    if text and not text.startswith(("{", "```")):
        for pattern in SECRET_PATTERNS:
            text = pattern.sub("[redacted]", text)
        emit(directory, "agent_message", agent=label, text=text[:4000])
