"""Propose application lint/test changes from a completed knowledge review."""

from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from contextops import gitutil
from contextops.access import sensitive
from contextops.agents import Ledger, READ_ONLY_TOOLS, load_agent, run_agent
from contextops.config import InitConfig, load_config
from contextops.review import SECRET_PATTERNS
from contextops.run import RunContext, load_run

OUTPUT = "check-proposals"

PROPOSAL_SCHEMA = {
    "type": "object",
    "required": ["reason", "candidate"],
    "additionalProperties": False,
    "properties": {
        "reason": {"type": "string"},
        "candidate": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["record", "kind", "patch", "passing", "failing", "verification"],
                    "properties": {
                        "record": {"type": "integer", "minimum": 1},
                        "kind": {"enum": ["lint", "test"]},
                        "patch": {"type": "string"},
                        "passing": {"type": "string"},
                        "failing": {"type": "string"},
                        "verification": {"type": "string"},
                    },
                },
            ],
        },
    },
}


def _write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


@contextmanager
def _worktree(repo: Path, revision: str, parent: Path):
    with TemporaryDirectory(prefix=".check-", dir=parent) as temporary:
        checkout = Path(temporary) / "tree"
        gitutil.add_worktree(repo, checkout, revision)
        try:
            yield checkout
        finally:
            gitutil.remove_worktree(repo, checkout)


def _apply_patch(repo: Path, patch: bytes) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "apply", "--index", "--whitespace=error", "-"],
        input=patch, capture_output=True,
    )
    if result.returncode:
        raise ValueError("Check patch could not be applied cleanly to the selected revision")


def _validate_patch(repo: Path, patch: str) -> list[str]:
    if not patch.startswith("diff --git ") or any(p.search(patch) for p in SECRET_PATTERNS):
        raise ValueError("Check patch must be a Git diff without possible credential content")
    _apply_patch(repo, patch.encode("utf-8"))
    changes = gitutil.git(repo, "diff", "--cached", "--no-renames", "--raw", "-z").rstrip("\0").split("\0")
    paths = []
    for metadata, path in zip(changes[::2], changes[1::2]):
        modes = metadata[1:].split()[:2]
        if sensitive(Path(path)) or any(mode not in {"000000", "100644", "100755"} for mode in modes):
            raise ValueError("Check patch contains a sensitive path or non-regular file")
        paths.append(path)
    stats = gitutil.git(repo, "diff", "--cached", "--numstat", "--no-renames", "-z").split("\0")
    if not paths or any(item.startswith("-\t-\t") for item in stats):
        raise ValueError("Check patch must contain text changes")
    return paths


async def propose(
    ctx: RunContext, config: InitConfig, records: list[dict], ledger: Ledger, *, manual: bool = False,
) -> Path:
    """Run the shared, fresh-session step and persist a local review artifact."""
    directory = ctx.run_dir / OUTPUT
    directory.mkdir(mode=0o700, exist_ok=True)
    receipt = directory / "proposal.json"
    if _has_proposal(receipt, manual):
        return receipt
    lock = directory / ".proposing"
    try:
        marker = lock.open("x")
    except FileExistsError:
        raise ValueError("A check proposal is already being prepared for this run") from None
    with marker:
        try:
            if not _has_proposal(receipt, manual):
                await _propose(ctx, config, records, ledger, receipt)
        finally:
            lock.unlink()
    return receipt


def _has_proposal(receipt: Path, manual: bool) -> bool:
    return receipt.is_file() and (
        not manual or json.loads(receipt.read_text(encoding="utf-8"))["status"] not in {"budget-skipped", "failed"}
    )


async def _propose(
    ctx: RunContext, config: InitConfig, records: list[dict], ledger: Ledger, receipt: Path,
) -> None:
    records = [
        item for item in records if item["op"] in {"ADD", "UPDATE", "MERGE"}
        and (item["scope"] in {"company", f"app:{ctx.app_label}"} or item["scope"].startswith("tool:"))
    ]
    result = {"base": ctx.head_sha, "status": "no-candidate"}
    if not records:
        _write_json(receipt, {**result, "reason": "No validated active decision from this sweep"})
        return
    remaining = ledger.limit_usd - ledger.spent
    if remaining <= 0:
        _write_json(receipt, {**result, "status": "budget-skipped", "reason": "No maintenance budget remaining"})
        return
    if not config.checks.agent:
        raise ValueError("The committed configuration has no checks.agent")
    from contextops.orchestrator import _prepare_auth

    if config.backend == "claude":
        _prepare_auth(config)
    spec = replace(load_agent(config.checks.agent, config.default_model, config.backend, config.model_override),
                   tools=READ_ONLY_TOOLS)
    prompt = "\n".join([
        f"Application {ctx.app_label} at {ctx.head_sha}.",
        f"Evidence pack: {ctx.pack}",
        "Validated records in order (one-based):",
        json.dumps(records, indent=2),
    ])
    with _worktree(ctx.app_root, ctx.head_sha, receipt.parent) as checkout:
        run = await run_agent(
            spec, label="check-proposer", system=spec.prompt, prompt=prompt, schema=PROPOSAL_SCHEMA,
            cwd=checkout, dirs=[ctx.pack], run_dir=ctx.run_dir, budget_usd=min(config.budget.per_agent_usd, remaining),
            max_turns=config.budget.max_turns,
        )
        ledger.add(run)
        result.update(cost_usd=run.cost_usd, duration_ms=run.duration_ms)
        if run.output is None:
            _write_json(receipt, {**result, "status": "failed", "reason": "Check proposer did not complete"})
            return
        candidate = run.output["candidate"]
        if candidate is None:
            _write_json(receipt, {**result, "reason": run.output["reason"]})
            return
        try:
            index = candidate["record"]
            if not 1 <= index <= len(records):
                raise ValueError("Check proposal did not cite a validated decision")
            patch = candidate["patch"]
            paths = _validate_patch(checkout, patch)
        except ValueError as exc:
            _write_json(receipt, {**result, "status": "failed", "reason": str(exc)})
            return
        (receipt.parent / "check.patch").write_bytes(patch.encode("utf-8"))
        _write_json(receipt, {
            **result, "status": "pending-review", "reason": run.output["reason"],
            "record": records[index - 1], "kind": candidate["kind"], "paths": paths,
            "passing": candidate["passing"], "failing": candidate["failing"],
            "suggested_verification": candidate["verification"],
            "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        })


def _completed_run(run_dir: Path) -> RunContext:
    ctx = load_run(run_dir)
    if ctx.run_dir.resolve() != run_dir.resolve() or not (ctx.run_dir / "completion.txt").is_file():
        raise ValueError("Select the original directory of a completed sweep")
    return ctx


async def propose_manually(run_dir: Path) -> Path:
    ctx = _completed_run(run_dir)
    receipt = ctx.run_dir / OUTPUT / "proposal.json"
    if _has_proposal(receipt, manual=True):
        return receipt
    records = json.loads((ctx.run_dir / "review.json").read_text(encoding="utf-8"))["accepted"]
    with _worktree(ctx.kb_root, ctx.kb_baseline, ctx.run_dir) as checkout:
        config = load_config(checkout, ctx.backend)
        config.model_override = ctx.model
        if not config.checks.agent:
            raise ValueError("This sweep's committed configuration has no checks.agent")
        return await propose(ctx, config, records, Ledger(config.budget.per_agent_usd), manual=True)


def _reviewed_patch(ctx: RunContext, digest: str) -> bytes:
    directory = ctx.run_dir / OUTPUT
    proposal = json.loads((directory / "proposal.json").read_text(encoding="utf-8"))
    patch = (directory / "check.patch").read_bytes()
    if (proposal["status"] != "pending-review" or proposal["base"] != ctx.head_sha
            or digest != proposal["patch_sha256"] or digest != hashlib.sha256(patch).hexdigest()):
        raise ValueError("The patch does not match the reviewed proposal digest and revision")
    return patch


def verify(run_dir: Path, digest: str, command: list[str]) -> int:
    ctx = _completed_run(run_dir)
    if not command:
        raise ValueError("Provide the exact command to run in the disposable application worktree")
    patch = _reviewed_patch(ctx, digest)
    directory = ctx.run_dir / OUTPUT
    with _worktree(ctx.app_root, ctx.head_sha, directory) as checkout:
        _apply_patch(checkout, patch)
        try:
            code = subprocess.run(command, cwd=checkout, timeout=120).returncode
        except subprocess.TimeoutExpired:
            code = 124
    _write_json(directory / "verification.json", {
        "patch_sha256": digest, "command": command, "exit_code": code,
    })
    return code


def apply(run_dir: Path, digest: str) -> Path:
    ctx = _completed_run(run_dir)
    patch = _reviewed_patch(ctx, digest)
    if (gitutil.rev_parse(ctx.app_root, "HEAD") != ctx.head_sha or gitutil.status(ctx.app_root)):
        raise ValueError("Application checkout must be clean and at the exact reviewed revision")
    _apply_patch(ctx.app_root, patch)
    _write_json(ctx.run_dir / OUTPUT / "applied.json", {"patch_sha256": digest, "base": ctx.head_sha})
    return ctx.app_root
