"""Immutable run inputs and a successful-conversation checkpoint."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from contextops import git
from contextops.config import load_config
from contextops.files import dump, identity, load


@dataclass
class Run:
    run_id: str
    directory: Path
    application: Path
    knowledge: Path
    ref: str
    remote_ref: str
    remote: str
    base: str
    head: str
    baseline: str
    base_branch: str
    branch: str
    since: str | None
    cutoff: str
    notes: list[str]

    @property
    def pack(self) -> Path:
        return self.directory / "pack"

    @property
    def app_snapshot(self) -> Path:
        return self.directory / "application"

    @property
    def kb_snapshot(self) -> Path:
        return self.directory / "knowledge"

    @property
    def state_dir(self) -> Path:
        return self.directory.parent / "state" / identity(self.application, self.knowledge)

    def record(self) -> dict:
        return {k: str(v) if isinstance(v, Path) else v for k, v in asdict(self).items()}


def prepare(app: Path, kb: Path, base: str, head: str, *, ref: str = "manual", remote_ref: str = "", remote: str = "origin") -> Run:
    app, kb = git.root(app), git.root(kb)
    if app == kb or app in kb.parents or kb in app.parents:
        raise ValueError("application and knowledge must be separate, non-nested repositories")
    if any(git.call(repo, "rev-parse", "--show-object-format").strip() != "sha1" for repo in (app, kb)):
        raise ValueError("this initial runtime supports SHA-1 Git repositories only")
    config = load_config(kb)
    baseline, head = git.revision(kb, "HEAD"), git.revision(app, head)
    notes = []
    if base == git.ZERO:
        base = git.EMPTY_TREE
        notes.append("New remote ref: base is the empty tree; evidence includes the entire head snapshot.")
    elif base != git.EMPTY_TREE:
        base = git.revision(app, base)
    if base == git.EMPTY_TREE:
        # A new repository need not already contain the canonical empty tree.
        # This adds a Git object only, never an application file or commit.
        if git.call(app, "mktree", input_text="").strip() != git.EMPTY_TREE:
            raise ValueError("unexpected empty-tree object ID")
    if base == head:
        raise ValueError("base and head are identical")
    runs = Path(config.output["runs_dir"])
    if any(runs == p or p in runs.parents or runs in p.parents for p in (app, kb)):
        raise ValueError("run artifacts must be outside both repositories and their ancestors")
    now = datetime.now(timezone.utc)
    run_id = f"{now:%Y%m%d-%H%M%S}-{head[:7]}-{uuid.uuid4().hex[:8]}"
    checkpoint = runs / "state" / identity(app, kb) / "checkpoint.json"
    previous = load(checkpoint).get("cutoff") if checkpoint.exists() else None
    since = previous if config.conversation["since"] == "last-run" and previous else None
    if not since:
        stamp = git.commit_time(app, base)
        since = stamp.isoformat() if stamp else None
    run = Run(run_id, runs / run_id, app, kb, ref, remote_ref, remote, base, head,
              baseline, git.branch(kb), f"contextops/{run_id}", since, now.isoformat(), notes)
    run.directory.mkdir(parents=True, exist_ok=False)
    dump(run.directory / "run.json", run.record())
    return run


def read_run(directory: Path) -> Run:
    data = load(directory.expanduser().resolve() / "run.json")
    for key in ("directory", "application", "knowledge"):
        data[key] = Path(data[key])
    run = Run(**data)
    if run.directory != directory.expanduser().resolve():
        raise ValueError("run directory does not match its manifest")
    return run


def checkpoint(run: Run) -> None:
    path = run.state_dir / "checkpoint.json"
    previous = load(path).get("cutoff") if path.exists() else None
    if previous is None or datetime.fromisoformat(previous) < datetime.fromisoformat(run.cutoff):
        dump(path, {"cutoff": run.cutoff, "run_id": run.run_id, "head": run.head})
