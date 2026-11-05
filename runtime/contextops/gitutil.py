"""Thin wrappers around the git CLI."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

ZERO_SHA = "0" * 40
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check
    )
    # Only trailing whitespace: porcelain status lines start with a meaningful space.
    return result.stdout.rstrip()


def succeeds(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).returncode == 0


def repo_root(path: Path) -> Path:
    return Path(git(path, "rev-parse", "--show-toplevel"))


def rev_parse(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")


def config_get(repo: Path, key: str) -> str | None:
    return git(repo, "config", "--get", key, check=False) or None


def push_base(repo: Path, local_sha: str, remote_sha: str, remote: str) -> str:
    """Pick the commit the pushed work starts from."""
    if remote_sha != ZERO_SHA and succeeds(repo, "cat-file", "-e", remote_sha):
        return remote_sha
    # New branch, or a remote tip we never fetched: start from what the remote already has.
    commits = git(repo, "rev-list", local_sha, "--not", f"--remotes={remote}").splitlines()
    if not commits:
        return local_sha
    parent = git(repo, "rev-parse", "--verify", "--quiet", f"{commits[-1]}^", check=False)
    return parent or EMPTY_TREE


def commit_time(repo: Path, sha: str) -> datetime | None:
    if sha == EMPTY_TREE:
        return None
    stamp = int(git(repo, "show", "-s", "--format=%ct", sha))
    return datetime.fromtimestamp(stamp, tz=timezone.utc)


def file_exists(repo: Path, sha: str, path: str) -> bool:
    return succeeds(repo, "cat-file", "-e", f"{sha}:{path}")


def add_worktree(repo: Path, path: Path, ref: str, branch: str | None = None) -> None:
    # Hooks are switched off so a checkout here never runs the project's post-checkout scripts.
    args = ["-c", "core.hooksPath=/dev/null", "worktree", "add"]
    args += ["-b", branch] if branch else ["--detach"]
    git(repo, *args, str(path), ref)


def remove_worktree(repo: Path, path: Path) -> None:
    if path.exists():
        git(repo, "worktree", "remove", "--force", str(path), check=False)


def status(repo: Path) -> list[tuple[str, str]]:
    """(code, path) pairs from `git status --porcelain`, untracked files listed one by one."""
    result = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "-z", "-uall"],
                            capture_output=True, text=True, check=True)
    records = iter(result.stdout.split("\0"))
    entries = []
    for item in records:
        if not item:
            continue
        code, path = item[:2].strip(), item[3:]
        entries.append((code, path))
        if "R" in code or "C" in code:
            next(records, None)  # NUL format puts the old path after the destination.
    return entries
