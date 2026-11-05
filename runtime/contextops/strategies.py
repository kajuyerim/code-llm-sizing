"""Evidence-gathering strategies, the only step where the two experiments differ.

fresh-specialists (experiment B): every worker sweeps the raw evidence on its own.
sweeper-first (experiment A): a sweeper completes, then each worker independently
forks that session. Shared collection, review, and writing stay outside this module.

Both strategies give every agent the same role-free system prompt and output schema and
put the role in the first user message. A fork then shares its sweeper's prompt cache
prefix up to the new role message and reads the inherited history from the cache instead
of writing it again. B uses the same layout so the two differ only in the sweeper.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass

from contextops.agents import AgentRun, AgentSpec, Ledger, load_agent, role_message, run_agent, shared_system_prompt
from contextops.config import InitConfig
from contextops.initializer import Worker
from contextops.run import RunContext
from contextops.schemas import AGENT_OUTPUT


@dataclass
class WorkerResult:
    worker: Worker
    run: AgentRun


def worker_prompt(worker: Worker, ctx: RunContext) -> str:
    lines = [
        f"Assignment: {worker.label}",
        f"You own: {worker.owns}",
    ]
    if worker.tool:
        lines.append(f"Tool: {worker.tool}")
    lines += [
        "",
        f"Evidence pack, read manifest.json first: {ctx.pack}",
        "- diff/changes.patch, diff/files.txt, diff/commits.txt",
        "- conversation/<session-id>.md, every message tagged [msg:<uuid>]",
        "- memory/repo/ (instruction files at head) and memory/auto/ (agent memory)",
        "",
        f"Source application, read-only, checked out at {ctx.head_sha}: {ctx.app_snapshot}",
        f"Knowledge base at baseline {ctx.kb_baseline[:7]}: {ctx.kb_snapshot}",
        "",
        "Sweep the evidence for your assignment, compare it with the current knowledge, "
        "and return your change records. When nothing applies, return a single NO_CHANGE "
        "record for your target and describe what you inspected in coverage. Return "
        "findings as an empty list.",
    ]
    return "\n".join(lines)


async def run_worker(
    worker: Worker,
    ctx: RunContext,
    config: InitConfig,
    ledger: Ledger,
    *,
    prompt: str | None = None,
    resume: str | None = None,
    fork: bool = False,
) -> WorkerResult:
    run = await run_agent(
        worker.spec,
        label=worker.label,
        system=shared_system_prompt(config),
        prompt=prompt or role_message(worker.spec) + "\n\n" + worker_prompt(worker, ctx),
        schema=AGENT_OUTPUT,
        cwd=ctx.pack,
        dirs=[ctx.app_snapshot, ctx.kb_snapshot],
        budget_usd=config.budget.per_agent_usd,
        max_turns=config.budget.max_turns,
        resume=resume,
        fork=fork,
    )
    ledger.add(run)
    return WorkerResult(worker, run)


async def fresh_specialists(
    workers: list[Worker], ctx: RunContext, config: InitConfig, ledger: Ledger
) -> list[WorkerResult]:
    gate = asyncio.Semaphore(config.budget.max_parallel)

    async def start(worker: Worker) -> WorkerResult:
        async with gate:
            if not ledger.has_room():
                return WorkerResult(worker, AgentRun(worker.label, status="skipped-budget"))
            return await run_worker(worker, ctx, config, ledger)

    return list(await asyncio.gather(*(start(worker) for worker in workers)))


TOKEN_FIELDS = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD")


def sweeper_prompt(spec: AgentSpec, workers: list[Worker], ctx: RunContext) -> str:
    roster = "\n".join(f"- {worker.label}: {worker.owns}" for worker in workers)
    return "\n".join([
        role_message(spec),
        "",
        f"Evidence pack, read manifest.json first: {ctx.pack}",
        "- diff/changes.patch, diff/files.txt, diff/commits.txt",
        "- conversation/<session-id>.md, every message tagged [msg:<uuid>]",
        "- memory/repo/ (instruction files at head) and memory/auto/ (agent memory)",
        "",
        f"Source application, read-only, checked out at {ctx.head_sha}: {ctx.app_snapshot}",
        f"Knowledge base at baseline {ctx.kb_baseline[:7]}: {ctx.kb_snapshot}",
        "",
        "Specialists that will continue from your session:",
        roster,
        "",
        "Inspect the evidence broadly before they start. Return findings, handoffs, "
        "contradictions, unresolved questions, and the coverage you actually read. Return "
        "records and unowned as empty lists; the specialists propose changes. Do not edit files.",
    ])


def fork_prompt(worker: Worker, ctx: RunContext) -> str:
    return "\n\n".join([
        "The sweeper phase above is complete. From this message on you are not the sweeper: "
        "its role instructions no longer apply, and you work only in the role below. The "
        "sweeper's findings are candidates, not admitted claims: check the original evidence "
        "for everything you return.",
        role_message(worker.spec),
        worker_prompt(worker, ctx),
    ])


def _prefix(system: str, schema: dict, spec: AgentSpec) -> dict:
    """What must match between a sweeper and its forks for the cache prefix to be shared."""
    digest = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return {"system": digest(system), "schema": digest(json.dumps(schema, sort_keys=True)),
            "tools": sorted(spec.tools), "model": spec.model}


def _subtract_parent(child: AgentRun, parent: AgentRun) -> dict:
    """Estimate incremental usage from cumulative fork reports, retaining raw values."""
    raw = {"raw": asdict(child), "accounting": "cumulative-parent subtraction estimate"}
    if child.cost_usd >= parent.cost_usd:
        child.cost_usd -= parent.cost_usd
    else:
        raw["note"] = "fork reported less than its parent; cost left as reported"
    if child.model_usage and parent.model_usage:
        delta = {}
        for model, usage in child.model_usage.items():
            previous = parent.model_usage.get(model, {})
            delta[model] = {
                key: (value - previous.get(key, 0) if key in TOKEN_FIELDS and value >= previous.get(key, 0) else value)
                for key, value in usage.items()
            }
        child.model_usage = delta
    return raw


async def sweeper_first(
    workers: list[Worker], ctx: RunContext, config: InitConfig, ledger: Ledger
) -> list[WorkerResult]:
    spec = load_agent(config.sweeper, config.default_model)
    system = shared_system_prompt(config)
    sweeper = await run_agent(
        spec,
        label="sweeper",
        system=system,
        prompt=sweeper_prompt(spec, workers, ctx),
        schema=AGENT_OUTPUT,
        cwd=ctx.pack,
        dirs=[ctx.app_snapshot, ctx.kb_snapshot],
        budget_usd=config.budget.per_agent_usd,
        max_turns=config.budget.max_turns,
    )
    ledger.add(sweeper)
    parent_prefix = _prefix(system, AGENT_OUTPUT, spec)
    handoff = {"parent": asdict(sweeper), "children": [], "cache_prefix": parent_prefix}
    if sweeper.status != "success" or not sweeper.session_id:
        # No fresh-session fallback: that would turn this run into experiment B.
        _write(ctx.run_dir / "sweeper.json", handoff)
        return [WorkerResult(worker, AgentRun(worker.label, status="skipped-sweeper-failed")) for worker in workers]

    gate = asyncio.Semaphore(config.budget.max_parallel)

    async def start(worker: Worker) -> WorkerResult:
        async with gate:
            if not ledger.has_room():
                return WorkerResult(worker, AgentRun(worker.label, status="skipped-budget"))
            run = await run_agent(
                worker.spec,
                label=worker.label,
                system=system,
                prompt=fork_prompt(worker, ctx),
                schema=AGENT_OUTPUT,
                cwd=ctx.pack,
                dirs=[ctx.app_snapshot, ctx.kb_snapshot],
                # The SDK cap sees the inherited spend too, so give each fork the same headroom.
                budget_usd=config.budget.per_agent_usd + sweeper.cost_usd,
                max_turns=config.budget.max_turns,
                resume=sweeper.session_id,
                fork=True,
            )
            raw = _subtract_parent(run, sweeper)
            ledger.add(run)
            handoff["children"].append({
                "label": worker.label, "session_id": run.session_id, "status": run.status,
                # False means this fork cannot read the inherited history from the cache.
                "shares_cache_prefix": _prefix(system, AGENT_OUTPUT, worker.spec) == parent_prefix,
                "incremental": asdict(run), **raw,
            })
            return WorkerResult(worker, run)

    results = list(await asyncio.gather(*(start(worker) for worker in workers)))
    ids = [result.run.session_id for result in results if result.run.session_id]
    for result in results:
        run = result.run
        if run.status == "success" and (not run.session_id or run.session_id == sweeper.session_id
                                         or ids.count(run.session_id) > 1):
            run.status = "invalid-fork-lineage"
            run.output = None
            run.error = "Fork must report a unique child session distinct from its parent"
    handoff["independent_children"] = all(
        r.run.status != "invalid-fork-lineage" for r in results
    ) and len(ids) == len(set(ids)) and sweeper.session_id not in ids
    handoff["validated_children"] = [asdict(r.run) for r in results]
    _write(ctx.run_dir / "sweeper.json", handoff)
    return results


def _write(path, data) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


STRATEGIES = {
    "fresh-specialists": fresh_specialists,
    "sweeper-first": sweeper_first,
}
