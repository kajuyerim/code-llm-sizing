"""Evidence-gathering strategies, the only step where the two experiments differ.

fresh-specialists (experiment B): every worker sweeps the raw evidence on its own.
sweeper-first (experiment A) belongs here as another entry in STRATEGIES: run the
sweeper once, then call run_worker with resume=<sweeper session> and fork=True.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from contextops.agents import AgentRun, Ledger, run_agent, system_prompt
from contextops.config import InitConfig
from contextops.initializer import Worker
from contextops.run import RunContext
from contextops.schemas import WORKER_OUTPUT


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


STRATEGIES = {
    "fresh-specialists": fresh_specialists,
}
