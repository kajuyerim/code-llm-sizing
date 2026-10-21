"""Artifact writes and canonical, symlink-free paths."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def identity(*paths: Path) -> str:
    return hashlib.sha256("\0".join(str(p.resolve()) for p in paths).encode()).hexdigest()[:24]


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or any(ord(c) < 32 for c in value):
        raise ValueError("expected a nonempty relative POSIX path")
    parts = value.split("/")
    if value.startswith("/") or any(p in ("", ".", "..", ".git") for p in parts):
        raise ValueError(f"noncanonical path: {value!r}")
    return PurePosixPath(value).as_posix()


def inside(root: Path, relative: str) -> Path:
    relative = relative_path(relative)
    root = root.resolve()
    candidate = root / relative
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"symlink is not an allowed evidence or output path: {relative}")
    candidate.resolve().relative_to(root)
    return candidate


def knowledge_path(value: str) -> str:
    path = relative_path(value)
    if path in ("index.md", "log.md") or (
        path.endswith(".md") and path.startswith(("core/", "products/"))
    ):
        return path
    raise ValueError(f"not a knowledge output: {path}")


def owned(target: str, assignment: str) -> bool:
    return target.startswith(assignment) if assignment.endswith("/") else target == assignment


@contextmanager
def lock(path: Path):
    """POSIX local lock; concurrent runs fail explicitly instead of racing state."""
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another process holds {path}") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
