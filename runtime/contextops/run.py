"""Freeze a run's revisions, strategy and selected conversation before inference."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from contextops import gitutil, transcripts
from contextops.config import load_config

MANIFEST = "run.json"
STATE = "state.json"


@dataclass
class RunContext:
    run_id: str
    run_dir: Path
    app_root: Path
    kb_root: Path
    ref: str
    base_sha: str
    head_sha: str
    kb_baseline: str
    branch: str
    since: datetime | None
    cutoff: datetime
    strategy: str | None = None
    sessions: list[str] = field(default_factory=list)
    conversation_sha256: str | None = None

    @property
    def pack(self) -> Path:
        return self.run_dir / "pack"

    @property
    def app_snapshot(self) -> Path:
        return self.run_dir / "app"

    @property
    def kb_snapshot(self) -> Path:
        return self.run_dir / "kb"

    @property
    def runs_dir(self) -> Path:
        return self.run_dir.parent


def create_run(
    app_root: Path, kb_root: Path, remote: str, ref: str, local_sha: str, remote_sha: str,
    *, strategy: str | None = None, sessions: list[str] | None = None,
    cutoff: datetime | None = None,
) -> RunContext | None:
    from contextops.strategies import STRATEGIES

    app_root, kb_root = gitutil.repo_root(app_root).resolve(), gitutil.repo_root(kb_root).resolve()
    if app_root == kb_root or app_root.is_relative_to(kb_root) or kb_root.is_relative_to(app_root):
        raise ValueError("Application and knowledge repositories must be separate, non-nested checkouts")
    # Settings and roles must match the committed baseline used by orchestration.
    if gitutil.status(kb_root):
        raise ValueError("Commit or stash knowledge checkout changes before preparing a run")
    config = load_config(kb_root)
    strategy = strategy or config.mode
    if strategy not in STRATEGIES:
        raise ValueError("Choose an implemented strategy explicitly: " + ", ".join(STRATEGIES))
    if not sessions or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", s) for s in sessions):
        raise ValueError("Select at least one Claude Code session ID with --session")
    sessions = sorted(set(sessions))
    head = gitutil.rev_parse(app_root, local_sha)
    base = (gitutil.rev_parse(app_root, remote_sha) if ref == "manual"
            else gitutil.push_base(app_root, head, remote_sha, remote))
    if base == head:
        return None
    now = datetime.now(timezone.utc)
    cutoff = cutoff or now
    if cutoff.tzinfo is None or cutoff > now:
        raise ValueError("Cutoff must include a timezone and must not be in the future")
    cutoff = cutoff.astimezone(timezone.utc)
    # Explicit sessions include their complete retained history up to the cutoff.
    selected = transcripts.load_sessions(app_root, None, cutoff,
                                        config.conversation.include_sidechains, selected=sessions)
    frozen = json.dumps([asdict(s) for s in selected], indent=2).encode("utf-8")
    parent = config.output.runs_dir.resolve()
    runs_dir = (parent / strategy).resolve()
    if runs_dir != parent / strategy:
        raise ValueError("Strategy output directories must not be symlinks")
    if runs_dir.is_relative_to(kb_root) or runs_dir.is_relative_to(app_root):
        raise ValueError("Run artifacts must be outside application and knowledge checkouts")
    run_id = f"{now:%Y%m%d-%H%M%S}-{head[:7]}-{uuid4().hex[:8]}"
    ctx = RunContext(
        run_id=run_id, run_dir=runs_dir / run_id, app_root=app_root, kb_root=kb_root,
        ref=ref, base_sha=base, head_sha=head, kb_baseline=gitutil.rev_parse(kb_root, "HEAD"),
        branch=config.output.branch.format(strategy=strategy, run_id=run_id,
                                          date=f"{now:%Y-%m-%d}", short_sha=head[:7]),
        since=None, cutoff=cutoff, strategy=strategy, sessions=sessions,
        conversation_sha256=hashlib.sha256(frozen).hexdigest(),
    )
    if not gitutil.succeeds(kb_root, "check-ref-format", "--branch", ctx.branch):
        raise ValueError("init.md: output.branch produces an invalid Git branch")
    if gitutil.succeeds(kb_root, "show-ref", "--verify", f"refs/heads/{ctx.branch}"):
        raise ValueError("Run branch already exists; existing branches are never replaced")
    ctx.run_dir.mkdir(parents=True, mode=0o700)
    (ctx.run_dir / "conversation.json").write_bytes(frozen)
    (ctx.run_dir / MANIFEST).write_text(json.dumps(_to_json(ctx), indent=2), encoding="utf-8")
    return ctx


def load_run(run_dir: Path) -> RunContext:
    """Read old manifests without rewriting them; execution requires frozen inputs."""
    data = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    for key in ("run_dir", "app_root", "kb_root"):
        data[key] = Path(data[key])
    for key in ("since", "cutoff"):
        data[key] = datetime.fromisoformat(data[key]) if data[key] else None
    return RunContext(**data)


def frozen_sessions(ctx: RunContext) -> list[transcripts.Session]:
    if not ctx.conversation_sha256 or not ctx.strategy or not ctx.sessions:
        raise ValueError("Legacy run is readable but not replayable here; prepare a new explicit run")
    raw = (ctx.run_dir / "conversation.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != ctx.conversation_sha256:
        raise ValueError("Frozen conversation integrity check failed")
    return [transcripts.Session(s['session_id'], s['branch'],
                               [transcripts.Message(**m) for m in s['messages']])
            for s in json.loads(raw)]


def last_cutoff(runs_dir: Path, app_root: Path) -> datetime | None:
    value = _read_state(runs_dir).get(str(app_root))
    return datetime.fromisoformat(value) if value else None


def record_cutoff(runs_dir: Path, app_root: Path, cutoff: datetime) -> None:
    state = _read_state(runs_dir)
    state[str(app_root)] = cutoff.isoformat()
    (runs_dir / STATE).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _read_state(runs_dir: Path) -> dict:
    path = runs_dir / STATE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _to_json(ctx: RunContext) -> dict:
    return {k: v.isoformat() if isinstance(v, datetime) else str(v) if isinstance(v, Path) else v
            for k, v in asdict(ctx).items()}
