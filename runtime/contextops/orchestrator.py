"""Execute one prepared run, retaining artifacts on every failure path."""

from __future__ import annotations

import os
import time
from dataclasses import asdict
from pathlib import Path

from contextops import git
from contextops.agents import Ledger, versions
from contextops.cartographer import propose
from contextops.config import load_config
from contextops.evidence import build, check_hashes
from contextops.files import dump, lock
from contextops.report import metrics, render
from contextops.review import Review, review_results
from contextops.runs import checkpoint, read_run
from contextops.strategy import plan_workers, sweep_and_fork
from contextops.writer import publish, write


async def execute(directory: Path) -> Path:
    run = read_run(directory)
    # Locks and status are acquired before worktrees or SDK sessions are created.
    with lock(run.directory / "execution.lock"):
        if (run.directory / "status.json").exists():
            raise ValueError("run already attempted; prepare a new run rather than overwriting frozen evidence")
        try:
            with lock(run.state_dir / "execution.lock"):
                dump(run.directory / "status.json", {"status": "running"})
                return await _execute(run)
        except RuntimeError as exc:
            if (run.directory / "status.json").exists():
                raise
            # A different push for this application is already running. Do not
            # queue a stale conversation window or silently discard its refs.
            failures = [str(exc)]
            ledger = Ledger(3.0, 0.5)
            path = run.directory / "report.md"
            path.write_text(render(run, "incomplete", Review(), ledger, None, [], [], None, None, failures, 0, {}), encoding="utf-8")
            dump(run.directory / "status.json", {"status": "incomplete", "failures": failures})
            dump(run.directory / "metrics.json", metrics(run, ledger, {}, 0, "incomplete"))
            return path


async def _execute(run) -> Path:
    start = time.monotonic()
    ledger, review = Ledger(3.0, 0.5), Review()
    manifest = proposals = publication = None
    roster, skipped, failures, runtime_versions = [], [], [], {}
    made_app = made_kb = committed = False
    status = "incomplete"
    original_auth = {key: os.environ.pop(key) for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN") if key in os.environ}
    try:
        for key in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY", "ANTHROPIC_BASE_URL"):
            if os.environ.get(key, "").lower() not in ("", "0", "false", "no"):
                raise ValueError(f"subscription-only runtime cannot use provider override {key}")
        git.worktree(run.knowledge, run.kb_snapshot, run.baseline, run.branch)
        made_kb = True
        git.worktree(run.application, run.app_snapshot, run.head)
        made_app = True
        config = load_config(run.kb_snapshot)
        ledger = Ledger(config.budget["total_usd"], config.budget["per_agent_usd"])
        dump(run.directory / "config.json", config.record())
        manifest = build(run, config)
        if not manifest["complete"]:
            failures.append("conversation evidence is missing; agents and publication were not started")
        else:
            runtime_versions = versions()
            conversation = "\n".join(p.read_text(encoding="utf-8") for p in sorted((run.pack / "conversation").glob("*.md")))
            workers, skipped = plan_workers(config, manifest, conversation)
            roster = [{"label": w.label, "owns": w.owns, "reason": w.reason, "model": w.role.model} for w in workers]
            dump(run.directory / "workers.json", {"selected": roster, "irrelevant": skipped})
            sweeper, results = await sweep_and_fork(run, config, workers, ledger)
            if not sweeper.succeeded or len(results) != len(workers):
                failures.append("sweeper/session handoff did not complete; no fresh-session fallback was attempted")
            else:
                check_hashes(run, manifest)
                if git.status(run.app_snapshot):
                    raise ValueError("application snapshot changed during agent execution")
                review = review_results(run, manifest, results)
                skipped += [f"{worker.label}: budget allowance unavailable" for worker, result in results if result.status == "skipped-budget"]
                if review.unowned:
                    proposals = await propose(run, config, review, ledger)
                    dump(run.directory / "proposals.json", proposals)
                if review.accepted:
                    publication = await write(run, config, review, ledger)
                    committed = publication["committed"]
                check_hashes(run, manifest)
                if git.status(run.app_snapshot):
                    raise ValueError("application snapshot changed during final writing")
                if not review.failures and not ledger.blocked:
                    status = "complete"
                if committed and config.output["open_pr"] and status == "complete":
                    elapsed = round((time.monotonic() - start) * 1000)
                    body = render(run, status, review, ledger, manifest, roster, skipped, proposals, publication, failures, elapsed, runtime_versions)
                    publication.update(publish(run, body))
                    if publication.get("error"):
                        failures.append("publication failed; inspect publication.json before retrying to avoid duplicate PRs")
                        status = "incomplete"
                elif committed:
                    publication["note"] = "committed branch retained locally; publication disabled or run incomplete"
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
        status = "incomplete"
    finally:
        os.environ.update(original_auth)
        if made_kb:
            try:
                # Keep the actual patch even when validation or the writer failed.
                patch = git.call(run.kb_snapshot, "diff", "--no-ext-diff", "--no-textconv", run.baseline, "--")
                (run.directory / "knowledge.patch").write_text(patch, encoding="utf-8")
                committed = committed or git.revision(run.kb_snapshot, "HEAD") != run.baseline
                if not committed:
                    # Include new Markdown files in retained failure artifacts without staging them.
                    for code, name in git.status(run.kb_snapshot):
                        if code == "??":
                            source = run.kb_snapshot / name
                            if source.is_file() and not source.is_symlink():
                                destination = run.directory / "uncommitted" / name
                                destination.parent.mkdir(parents=True, exist_ok=True)
                                destination.write_bytes(source.read_bytes())
            except Exception as exc:
                failures.append(f"patch retention failed: {exc}")
                status = "incomplete"
        for made, repo, snapshot in ((made_app, run.application, run.app_snapshot), (made_kb, run.knowledge, run.kb_snapshot)):
            if made:
                try:
                    git.remove_worktree(repo, snapshot)
                except Exception as exc:
                    failures.append(f"worktree cleanup failed: {exc}")
                    status = "incomplete"
        if made_kb and not committed and not run.kb_snapshot.exists():
            try:
                git.call(run.knowledge, "branch", "-D", run.branch)
            except Exception as exc:
                failures.append(f"branch cleanup failed: {exc}")
                status = "incomplete"
        if status == "complete":
            try:
                checkpoint(run)
            except Exception as exc:
                failures.append(f"conversation checkpoint failed: {exc}")
                status = "incomplete"
        elapsed = round((time.monotonic() - start) * 1000)
        dump(run.directory / "review.json", asdict(review))
        dump(run.directory / "metrics.json", metrics(run, ledger, runtime_versions, elapsed, status))
        dump(run.directory / "status.json", {"status": status, "failures": failures, "committed": committed})
        report = render(run, status, review, ledger, manifest, roster, skipped, proposals, publication, failures, elapsed, runtime_versions)
        path = run.directory / "report.md"
        path.write_text(report, encoding="utf-8")
    return path
