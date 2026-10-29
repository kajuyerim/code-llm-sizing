"""Evidence-gathering strategies, the only step where the two experiments differ.

sweeper-first (experiment A): one sweeper reads the raw evidence broadly, then every
worker starts from a fork of the sweeper's completed session.
fresh-specialists (experiment B) lives on its own branch with the same helpers.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass

from contextops import frontmatter
from contextops.agents import AgentRun, Ledger, load_agent, run_agent, system_prompt
from contextops.config import InitConfig
from contextops.initializer import Worker
from contextops.run import RunContext
from contextops.schemas import HANDOFF, UNOWNED, WORKER_OUTPUT


@dataclass
class WorkerResult:
    worker: Worker
    run: AgentRun


def worker_prompt(worker: Worker, ctx: RunContext) -> str:
    lines = [
        f"Assignment: {worker.label}",
        f"You own: {worker.owns}",
    ]
    if worker.product:
        lines.append(f"Product: {worker.product}")
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
        "record for your target and describe what you inspected in coverage.",
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
        system=system_prompt(config, worker.spec),
        prompt=prompt or worker_prompt(worker, ctx),
        schema=WORKER_OUTPUT,
        cwd=ctx.pack,
        dirs=[ctx.app_snapshot, ctx.kb_snapshot],
        budget_usd=config.budget.per_agent_usd,
        max_turns=config.budget.max_turns,
        resume=resume,
        fork=fork,
    )
    ledger.add(run)
    return WorkerResult(worker, run)


SWEEPER_OUTPUT = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "items": UNOWNED},
        "handoffs": {"type": "array", "items": HANDOFF},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "unresolved": {"type": "array", "items": {"type": "string"}},
        "coverage": WORKER_OUTPUT["properties"]["coverage"],
    },
    "required": ["findings", "handoffs", "contradictions", "unresolved", "coverage"],
}

TOKEN_FIELDS = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD")


def sweeper_prompt(workers: list[Worker], ctx: RunContext) -> str:
    roster = "\n".join(f"- {worker.label}: {worker.owns}" for worker in workers)
    return "\n".join([
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
        "contradictions, unresolved questions, and the coverage you actually read. Do not edit files.",
    ])


def fork_prompt(worker: Worker, ctx: RunContext) -> str:
    return worker_prompt(worker, ctx) + (
        "\n\nYou continue from the sweeper's completed session. Its findings are candidates, "
        "not admitted claims: check the original evidence for everything you return."
    )


def _subtract_parent(child: AgentRun, parent: AgentRun) -> dict:
    """A fork reports its parent's spend again; keep only what the child added."""
    raw = {"raw_cost_usd": child.cost_usd, "raw_model_usage": child.model_usage}
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
    meta, _ = frontmatter.read(config.kb_root / "init.md")
    spec = load_agent(config.kb_root / meta.get("sweeper", "agents/sweeper.md"), config.default_model)
    sweeper = await run_agent(
        spec,
        label="sweeper",
        system=system_prompt(config, spec),
        prompt=sweeper_prompt(workers, ctx),
        schema=SWEEPER_OUTPUT,
        cwd=ctx.pack,
        dirs=[ctx.app_snapshot, ctx.kb_snapshot],
        budget_usd=config.budget.per_agent_usd,
        max_turns=config.budget.max_turns,
    )
    ledger.add(sweeper)
    handoff = {"parent": asdict(sweeper), "children": []}
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
                system=system_prompt(config, worker.spec),
                prompt=fork_prompt(worker, ctx),
                schema=WORKER_OUTPUT,
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
            handoff["children"].append({"label": worker.label, "session_id": run.session_id, "status": run.status, **raw})
            return WorkerResult(worker, run)

    results = list(await asyncio.gather(*(start(worker) for worker in workers)))
    ids = [result.run.session_id for result in results if result.run.session_id]
    handoff["independent_children"] = len(ids) == len(set(ids)) and sweeper.session_id not in ids
    _write(ctx.run_dir / "sweeper.json", handoff)
    return results


def _write(path, data) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


STRATEGIES = {
    "sweeper-first": sweeper_first,
}
