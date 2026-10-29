"""A full maintenance run, from frozen evidence to a knowledge-base PR.

    initializer -> strategy (specialists) -> review -> cartographer -> writer -> PR
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from contextops import gitutil
from contextops.agents import Ledger
from contextops.cartographer import run_cartographer
from contextops.config import InitConfig, load_config
from contextops.evidence import build_pack
from contextops.initializer import plan_workers
from contextops.report import Outcome, render_report
from contextops.review import review_results
from contextops.run import RunContext, load_run, record_cutoff
from contextops.strategies import STRATEGIES
from contextops.writer import open_pr, write_changes


async def orchestrate(run_dir: Path) -> Path:
    """Run everything for a prepared run directory and return the report path."""
    ctx = load_run(run_dir)
    committed = False
    try:
        # Agents read from snapshots, never from the developer's live checkouts.
        gitutil.add_worktree(ctx.kb_root, ctx.kb_snapshot, ctx.kb_baseline, branch=ctx.branch)
        gitutil.add_worktree(ctx.app_root, ctx.app_snapshot, ctx.head_sha)
        config = load_config(ctx.kb_snapshot)
        strategy = STRATEGIES.get(config.mode)
        if strategy is None:
            raise ValueError(f"init.md: unknown mode '{config.mode}', known: {', '.join(STRATEGIES)}")
        _prepare_auth(config)

        evidence = build_pack(ctx, config)
        workers, skipped = plan_workers(config, evidence)
        ledger = Ledger(config.budget.total_usd)

        results = await strategy(workers, ctx, config, ledger)
        for result in results:
            name = result.run.label.replace(":", "-")
            _dump(ctx.run_dir / "workers" / f"{name}.json", asdict(result.run))
        review = review_results(results, ctx, evidence)
        _dump(ctx.run_dir / "review.json", asdict(review))

        outcome = Outcome(workers=workers, skipped=skipped, review=review)
        if config.cartographer and review.unowned and ledger.has_room():
            outcome.proposals = await run_cartographer(ctx, config, review, ledger)
            _dump(ctx.run_dir / "proposals.json", outcome.proposals)
        if review.accepted and not ledger.has_room():
            review.failures.append("budget exhausted before the writer; accepted records were not applied")
        elif review.accepted:
            outcome.publication, outcome.writer_output = await write_changes(ctx, config, review, ledger)
            committed = outcome.publication.committed

        report = render_report(ctx, config, outcome, ledger, evidence)
        if committed and config.output.open_pr:
            outcome.publication.pr_url = open_pr(ctx, report)
            if outcome.publication.pr_url:
                report += f"\nPull request: {outcome.publication.pr_url}\n"

        _write_metrics(ctx, config, ledger)
        report_path = ctx.run_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")
        record_cutoff(ctx.runs_dir, ctx.app_root, ctx.cutoff)
        return report_path
    finally:
        gitutil.remove_worktree(ctx.app_root, ctx.app_snapshot)
        gitutil.remove_worktree(ctx.kb_root, ctx.kb_snapshot)
        if not committed:
            gitutil.git(ctx.kb_root, "branch", "-D", ctx.branch, check=False)


def _prepare_auth(config: InitConfig) -> None:
    if config.auth == "subscription":
        # An exported API key silently wins over the Claude Code login, so drop it for this run.
        os.environ.pop("ANTHROPIC_API_KEY", None)
    elif "ANTHROPIC_API_KEY" not in os.environ:
        raise RuntimeError("init.md asks for api-key auth but ANTHROPIC_API_KEY is not set")


def _write_metrics(ctx: RunContext, config: InitConfig, ledger: Ledger) -> None:
    agents = [{k: v for k, v in asdict(run).items() if k != "output"} for run in ledger.runs]
    _dump(ctx.run_dir / "metrics.json", {
        "run_id": ctx.run_id,
        "mode": config.mode,
        "total_cost_usd": ledger.spent,
        "total_duration_ms": sum(run.duration_ms for run in ledger.runs),
        "agents": agents,
    })


def _dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
