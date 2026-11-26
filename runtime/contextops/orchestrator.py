"""A full maintenance run, from frozen evidence to a knowledge-base PR.

    initializer -> strategy (specialists) -> review -> cartographer -> writer -> PR
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from contextops import gitutil
from contextops.agents import Ledger
from contextops.cartographer import run_cartographer
from contextops.checks import propose
from contextops.config import InitConfig, load_config
from contextops.evidence import build_pack
from contextops.events import emit
from contextops.profiles import apply_profile
from contextops.initializer import plan_workers
from contextops.report import Outcome, render_report, render_completion
from contextops.review import review_results
from contextops.run import RunContext, load_run, record_cutoff, frozen_sessions
from contextops.strategies import STRATEGIES, deliver_handoffs
from contextops.publish import publish
from contextops.writer import write_changes


async def orchestrate(run_dir: Path) -> Path:
    """Run everything for a prepared run directory and return the report path."""
    ctx = load_run(run_dir)
    frozen_sessions(ctx)
    if ctx.strategy not in STRATEGIES:
        raise ValueError("Prepared strategy is unavailable in this runtime")
    if gitutil.succeeds(ctx.kb_root, "show-ref", "--verify", f"refs/heads/{ctx.branch}"):
        raise ValueError("Run branch already exists; existing branches are never replaced")
    if ctx.backend == "codex":
        home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser().resolve()
        if any(home.is_relative_to(root) for root in (ctx.app_root, ctx.kb_root, ctx.run_dir)):
            raise ValueError("Codex login and session storage must be outside both checkouts and the run")
    # Never overwrite an attempted run or reuse its branch/session state.
    with (ctx.run_dir / "started").open("x") as marker:
        marker.write("This run was attempted. Prepare a new run for another attempt.\n")
    emit(ctx.run_dir, "run_started")
    committed = False
    kb_created = app_created = False
    try:
        # Agents read from snapshots, never from the developer's live checkouts.
        gitutil.add_worktree(ctx.kb_root, ctx.kb_snapshot, ctx.kb_baseline, branch=ctx.branch)
        kb_created = True
        gitutil.add_worktree(ctx.app_root, ctx.app_snapshot, ctx.head_sha)
        app_created = True
        config = load_config(ctx.kb_snapshot, ctx.backend)
        config.mode = ctx.strategy
        config.model_override = ctx.model
        if ctx.model:
            config.default_model = ctx.model
        if ctx.local_only:
            config.output.open_pr = False
        config.instructions += apply_profile(ctx.profile)
        strategy = STRATEGIES.get(ctx.strategy)
        if strategy is None:
            raise ValueError(f"init.md: unknown mode '{config.mode}', known: {', '.join(STRATEGIES)}")
        if config.backend == "claude":
            _prepare_auth(config)

        evidence = build_pack(ctx, config)
        workers, skipped = plan_workers(config, evidence)
        ledger = Ledger(config.budget.total_usd)

        results = await strategy(workers, ctx, config, ledger)
        handoff_pass = await deliver_handoffs(results, ctx, config, ledger)
        for result in results:
            name = result.run.label.replace(":", "-")
            _dump(ctx.run_dir / "workers" / f"{name}.json", asdict(result.run))
        review = review_results(results, ctx, evidence)
        emit(ctx.run_dir, "review_finished", accepted=len(review.accepted), deferred=len(review.deferred),
             rejected=len(review.rejected))
        for entry in handoff_pass:
            if entry.get("error"):
                review.failures.append(f"{entry['to']} handoff: {entry['error']}")
        _dump(ctx.run_dir / "review.json", asdict(review))

        outcome = Outcome(workers=workers, skipped=skipped, review=review, handoff_pass=handoff_pass)
        if config.cartographer and review.unowned and ledger.has_room():
            outcome.proposals = await run_cartographer(ctx, config, review, ledger)
            _dump(ctx.run_dir / "proposals.json", outcome.proposals)
        if review.accepted and not ledger.has_room():
            review.failures.append("budget exhausted before the writer; accepted records were not applied")
        elif review.accepted:
            outcome.publication, outcome.writer_output = await write_changes(ctx, config, review, ledger)
            committed = outcome.publication.committed

        check_summary = ""
        if config.checks.automatic:
            try:
                proposal = await propose(ctx, config, review.accepted, ledger)
                status = json.loads(proposal.read_text(encoding="utf-8"))["status"]
                check_summary = f"{status}. Local record at {proposal.relative_to(ctx.run_dir)}."
            except (OSError, ValueError, subprocess.CalledProcessError):
                check_summary = "Preparation failed. Run the manual command to retry."
        report = render_report(ctx, config, outcome, ledger, evidence)
        if committed and config.output.open_pr:
            published = publish(ctx, config, report)
            outcome.publication.pr_url = published.url
            outcome.publication.published = published.note
            report += f"\n## Review request\n\n- {published.note}\n" + (
                f"- {published.url}\n" if published.url else "")

        _write_metrics(ctx, config, ledger)
        report_path = ctx.run_dir / "report.md"
        completion = render_completion(ctx, outcome, ledger)
        if check_summary:
            report += f"\n## Application check proposal\n\n{check_summary}\n"
            completion += f"\nApplication check proposal. {check_summary}\n"
        report_path.write_text(report, encoding="utf-8")
        (ctx.run_dir / "completion.txt").write_text(completion, encoding="utf-8")
        record_cutoff(ctx.runs_dir, ctx.app_root, ctx.cutoff)
        failed = bool(review.failures) or any(
            run.status != "success" for run in ledger.runs if run.label != "check-proposer"
        )
        # The console skips work only after a complete evaluation. A written patch
        # counts once its knowledge commit is in the selected checkout's history.
        rejected = any(item["rejected_because"] != "Category is disabled in the active profile"
                       for item in review.rejected)
        applied = (outcome.writer_output or {}).get("applied", [])
        fully_written = False
        if ctx.source_branch and committed:
            paths = set(gitutil.git(ctx.kb_snapshot, "diff", "--name-only", ctx.kb_baseline, "HEAD").splitlines())
            fully_written = (
                not (outcome.writer_output or {}).get("skipped")
                and len(applied) == len(review.accepted)
                and all(record["target"] in paths and any(
                    item["target"] == record["target"] and item["op"] == record["op"]
                    and (record["fact_id"] is None or item["fact_id"] == record["fact_id"])
                    for item in applied
                ) for record in review.accepted)
            )
        if (ctx.source_branch and not failed and not review.deferred and not rejected
                and not review.unowned and (fully_written or not review.accepted)):
            _dump(ctx.run_dir / "checkpoint.json", {
                "knowledge_commit": gitutil.rev_parse(ctx.kb_snapshot, "HEAD") if committed else ctx.kb_baseline,
            })
        emit(ctx.run_dir, "run_finished", status="failed" if failed else "complete")
        return report_path
    except Exception:
        emit(ctx.run_dir, "run_finished", status="failed")
        raise
    finally:
        if app_created:
            gitutil.remove_worktree(ctx.app_root, ctx.app_snapshot)
        if kb_created:
            gitutil.remove_worktree(ctx.kb_root, ctx.kb_snapshot)
        if kb_created and not committed:
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
        "backend": config.backend,
        "model": config.default_model,
        "total_cost_usd": ledger.spent if config.backend == "claude" else None,
        "total_duration_ms": sum(run.duration_ms for run in ledger.runs),
        "agents": agents,
    })


def _dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
