"""YAML frontmatter for the Markdown files that drive a run."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_BLOCK = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def split(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body). A file without frontmatter gets an empty dict."""
    match = _BLOCK.match(text)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, text[match.end():]


def read(path: Path) -> tuple[dict, str]:
    return split(path.read_text(encoding="utf-8"))
