"""Git subprocesses with repository hooks and external diff helpers disabled."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ZERO = "0" * 40
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def environment() -> dict[str, str]:
    # Git exports repository-local variables to hooks. They must not redirect
    # commands intended for the separate knowledge checkout or its worktrees.
    result = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_SHALLOW_FILE",
                 "GIT_GRAFT_FILE", "GIT_REPLACE_REF_BASE", "GIT_QUARANTINE_PATH"):
        result.pop(name, None)
    return result


def setting(repo: Path, key: str) -> str:
    # Read the actual configuration without call()'s hook-disabling override.
    result = subprocess.run(["git", "-C", str(repo), "config", "--get", key],
                            capture_output=True, text=True, env=environment())
    return result.stdout.strip()


def call(root: Path, *args: str, check: bool = True, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=environment(), input=input_text,
    )
    if check and result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout


def root(path: Path) -> Path:
    return Path(call(path.expanduser().resolve(), "rev-parse", "--show-toplevel").strip()).resolve()


def revision(repo: Path, ref: str) -> str:
    return call(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip()


def branch(repo: Path) -> str:
    value = call(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).strip()
    if not value:
        raise ValueError("knowledge checkout must have a named branch for PR targeting")
    return value


def commit_time(repo: Path, sha: str) -> datetime | None:
    if sha == EMPTY_TREE:
        return None
    return datetime.fromtimestamp(int(call(repo, "show", "-s", "--format=%ct", sha)), timezone.utc)


def worktree(repo: Path, destination: Path, sha: str, new_branch: str | None = None) -> None:
    options = ["-b", new_branch] if new_branch else ["--detach"]
    call(repo, "worktree", "add", *options, str(destination), sha)


def remove_worktree(repo: Path, destination: Path) -> None:
    if destination.exists():
        call(repo, "worktree", "remove", "--force", str(destination))


def status(repo: Path) -> list[tuple[str, str]]:
    tokens = call(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0")
    result, index = [], 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        code, name = token[:2], token[3:]
        result.append((code, name))
        if "R" in code or "C" in code:
            result.append(("original", tokens[index]))
            index += 1
    return result


def diff(repo: Path, base: str, head: str, *paths: str) -> str:
    return call(repo, "diff", "--no-ext-diff", "--no-textconv", "--no-color", base, head, "--", *paths)


def changed(repo: Path, base: str, head: str) -> list[str]:
    # No rename detection: both old and new names remain explicit evidence paths.
    return [p for p in call(repo, "diff", "--no-renames", "--name-only", "-z", base, head, "--").split("\0") if p]
