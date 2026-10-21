"""Human report and machine metrics with missing measurements kept explicit."""

from __future__ import annotations

import html
from dataclasses import asdict

from contextops.agents import Ledger
from contextops.review import Review, secrets
from contextops.runs import Run


def safe(value) -> str:
    text = str(value)
    if secrets(text):
        return "[withheld: possible secret]"
    return html.escape(text).replace("\n", " ").replace("|", "\\|").replace("`", "\\`")


def metrics(run: Run, ledger: Ledger, versions: dict, elapsed_ms: int, status: str) -> dict:
    agents = []
    for result in ledger.results:
        record = asdict(result)
        record.pop("output")
        agents.append(record)
    return {
        "run_id": run.run_id, "mode": "sweeper-first", "status": status, "versions": versions,
        "resolved_models": sorted({m for r in ledger.results for m in (r.raw_model_usage or {})}),
        "known_estimated_cost_usd": ledger.spent,
        "total_cost_available": all(r.cost_usd is not None for r in ledger.results),
        "budget_usd": ledger.total, "wall_clock_ms": elapsed_ms,
        "summed_agent_duration_ms": sum(r.duration_ms for r in ledger.results),
        "summed_call_wall_ms": sum(r.wall_ms for r in ledger.results),
        "accounting": "Pinned bundled CLI restores parent totals on forks; raw parent totals are subtracted once from each child. New inherited-context processing remains counted. Estimates are not billing.",
        "coverage": "tool_reads record successful read/search calls, not proof that every matching file or message was read; agent coverage is retained separately in raw stage output",
        "agents": agents,
    }


def render(run: Run, status: str, review: Review, ledger: Ledger, manifest: dict | None,
           roster: list[dict], skipped: list[str], proposals: dict | None,
           publication: dict | None, failures: list[str], elapsed_ms: int, versions: dict) -> str:
    lines = [f"# Context Ops run {run.run_id}", "", f"- Status: {safe(status)}",
             "- Mode: sweeper-first; context handoff: literal SDK session forks",
             f"- Application: {safe(run.application.name)} at {run.base}..{run.head}",
             f"- Knowledge baseline: {run.baseline}; publication base: {safe(run.base_branch)}",
             f"- Conversation window: {safe(run.since or 'all available history')} to {run.cutoff}",
             f"- SDK / bundled CLI: {safe(versions.get('sdk', 'unavailable'))} / {safe(versions.get('bundled_cli', 'unavailable'))}",
             f"- Wall-clock elapsed: {elapsed_ms} ms",
             f"- Known estimated spend: USD {ledger.spent:.6f}; configured total: USD {ledger.total:.2f}",
             "- Costs are estimates. Unavailable measurements are not zero. No automated semantic truth evaluation is performed."]
    def section(title, items):
        if items:
            lines.extend(["", f"## {title}", "", *(f"- {safe(item)}" for item in items)])
    section("Selected assignments", [f"{w['label']}: {w['owns']} ({w['reason']})" for w in roster])
    section("Skipped workers", skipped)
    lines.extend(["", "## Agent resources", "", "| Agent | Status | Session | Turns | Call estimate USD | SDK duration ms |", "| --- | --- | --- | --- | --- | --- |"])
    for result in ledger.results:
        amount = "unavailable" if result.cost_usd is None else f"{result.cost_usd:.6f}"
        lines.append(f"| {safe(result.label)} | {safe(result.status)} | {safe(result.session_id or 'unavailable')} | {result.turns} | {amount} | {result.duration_ms} |")
    section("Accepted proposals", [f"{r['record_id']}: {r['op']} {r['target']} {r['fact_id']}: {r['text']}" for r in review.accepted])
    section("Evidence for accepted proposals", [f"{r['record_id']}: {e['kind']} {e.get('path') or ''} {e.get('session') or ''}/{e.get('message') or ''}; quote: {e['quote']}" for r in review.accepted for e in r["evidence"]])
    section("Needs human review", [f"{r['record_id']}: {r['target']}: {r['text']}; {r['reason']}" for r in review.deferred])
    section("Rejected by structural checks", [f"{r['record_id']}: {r['rejected_because']}" for r in review.rejected])
    section("No change", [f"{r['agent']}: {r['target']}; {r['reason']}" for r in review.no_change])
    section("Handoffs", [f"{h['agent']} to {h['to']}: {h['note']}" for h in review.handoffs])
    section("Unowned findings", [f"{f['finding_id']}: {f['summary']}" for f in review.unowned])
    for proposal in (proposals or {}).get("proposals", []):
        section("Structure proposal, not applied", [f"{proposal['path']}: {proposal['rationale']}",
                *proposal["seed_entries"], f"Definition draft: {proposal['definition_draft']}",
                f"Index entry: {proposal['index_line']}", f"Findings: {', '.join(proposal['finding_refs'])}"])
    if manifest:
        section("Evidence collection", [f"Conversation selection/exclusions: {manifest['conversation_selection']}",
                f"Auto-memory collection time: {manifest['memory_capture_time']}; not aligned to the conversation cutoff.", *manifest["notes"]])
    if publication:
        section("Writer and publication", [str(publication)])
    section("Failures and incomplete work", failures + review.failures + [f"{r.label}: {error}" for r in ledger.results for error in r.errors])
    lines.extend(["", "Raw evidence, proposals, coverage reports, tool traces, and resource records are retained locally alongside this report. Generated knowledge requires human review."])
    return "\n".join(lines) + "\n"
