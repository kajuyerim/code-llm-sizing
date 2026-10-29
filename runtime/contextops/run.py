"""One maintenance run: what was pushed, where its files live, and the conversation window."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from contextops import gitutil
from contextops.config import InitConfig, load_config

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
    app_root: Path, kb_root: Path, remote: str, ref: str, local_sha: str, remote_sha: str
) -> RunContext | None:
    """Freeze the inputs of a run. Returns None when the push brings nothing new."""
    config = load_config(kb_root)
    base = gitutil.push_base(app_root, local_sha, remote_sha, remote)
    if base == local_sha:
        return None

    now = datetime.now(timezone.utc)
    run_id = f"{now:%Y%m%d-%H%M%S}-{local_sha[:7]}"
    ctx = RunContext(
        run_id=run_id,
        run_dir=config.output.runs_dir / run_id,
        app_root=app_root,
        kb_root=kb_root,
        ref=ref,
        base_sha=base,
        head_sha=local_sha,
        kb_baseline=gitutil.rev_parse(kb_root, "HEAD"),
        branch=config.output.branch.format(
            run_id=run_id, date=f"{now:%Y-%m-%d}", short_sha=local_sha[:7]
        ),
        since=_since(config, app_root, base),
        cutoff=now,
    )
    ctx.run_dir.mkdir(parents=True)
    (ctx.run_dir / MANIFEST).write_text(json.dumps(_to_json(ctx), indent=2), encoding="utf-8")
    return ctx


def load_run(run_dir: Path) -> RunContext:
    data = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    for key in ("run_dir", "app_root", "kb_root"):
        data[key] = Path(data[key])
    for key in ("since", "cutoff"):
        data[key] = datetime.fromisoformat(data[key]) if data[key] else None
    return RunContext(**data)


def last_cutoff(runs_dir: Path, app_root: Path) -> datetime | None:
    value = _read_state(runs_dir).get(str(app_root))
    return datetime.fromisoformat(value) if value else None


def record_cutoff(runs_dir: Path, app_root: Path, cutoff: datetime) -> None:
    state = _read_state(runs_dir)
    state[str(app_root)] = cutoff.isoformat()
    (runs_dir / STATE).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _since(config: InitConfig, app_root: Path, base: str) -> datetime | None:
    if config.conversation.since == "last-run":
        previous = last_cutoff(config.output.runs_dir, app_root)
        if previous:
            return previous
    return gitutil.commit_time(app_root, base)


def _read_state(runs_dir: Path) -> dict:
    path = runs_dir / STATE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _to_json(ctx: RunContext) -> dict:
    def plain(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        return value

    return {key: plain(value) for key, value in asdict(ctx).items()}
