"""Runs the cartographer over findings that no existing document owns."""

from __future__ import annotations

import json

from contextops.agents import Ledger, load_agent, run_agent, system_prompt
from contextops.config import InitConfig
from contextops.review import Review
from contextops.run import RunContext
from contextops.schemas import CARTOGRAPHER_OUTPUT

BACKLOG = "unowned.jsonl"
BACKLOG_WINDOW = 200  # newest findings the cartographer sees


async def run_cartographer(
    ctx: RunContext, config: InitConfig, review: Review, ledger: Ledger
) -> dict | None:
    # Unowned findings pile up across runs: one stray finding is noise, a recurring one is a gap.
    backlog = ctx.runs_dir / BACKLOG
    with backlog.open("a", encoding="utf-8") as out:
        for item in review.unowned:
            out.write(json.dumps({**item, "run": ctx.run_id, "app": ctx.app_root.name}) + "\n")

    recent = backlog.read_text(encoding="utf-8").splitlines()[-BACKLOG_WINDOW:]
    (ctx.run_dir / "unowned-backlog.jsonl").write_text("\n".join(recent) + "\n", encoding="utf-8")

    spec = load_agent(config.cartographer, config.default_model)
    prompt = "\n".join([
        f"Run: {ctx.run_id}, application {ctx.app_root.name} at {ctx.head_sha[:7]}",
        f"Unowned findings, newest last: {ctx.run_dir / 'unowned-backlog.jsonl'}",
        f"This run's evidence pack: {ctx.pack}",
        f"Knowledge base at baseline: {ctx.kb_snapshot} (start with index.md and init.md)",
        "",
        "Decide whether any group of findings justifies a new core document or product "
        "folder. Return an empty proposal list when none does.",
    ])
    run = await run_agent(
        spec,
        label="cartographer",
        system=system_prompt(config, spec),
        prompt=prompt,
        schema=CARTOGRAPHER_OUTPUT,
        cwd=ctx.run_dir,
        dirs=[ctx.kb_snapshot],
        budget_usd=config.budget.per_agent_usd,
        max_turns=config.budget.max_turns,
    )
    ledger.add(run)
    return run.output
