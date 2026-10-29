"""The run report. The same text becomes the PR body."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contextops.agents import Ledger
from contextops.config import InitConfig
from contextops.evidence import Evidence
from contextops.initializer import Worker
from contextops.review import Review
from contextops.run import RunContext
from contextops.writer import Publication


@dataclass
class Outcome:
    workers: list[Worker]
    skipped: list[str]
    review: Review
    proposals: dict | None = None
    publication: Publication | None = None
    writer_output: dict | None = None


def render_report(
    ctx: RunContext, config: InitConfig, outcome: Outcome, ledger: Ledger, evidence: Evidence
) -> str:
    review = outcome.review
    lines = [
        f"# ContextOps run {ctx.run_id}",
        "",
        f"- Application: `{ctx.app_root.name}` {ctx.ref} `{ctx.base_sha[:7]}..{ctx.head_sha[:7]}`",
        f"- Knowledge baseline: `{ctx.kb_baseline[:7]}`",
        f"- Mode: `{config.mode}`",
        f"- Conversation window: {_when(ctx.since)} to {_when(ctx.cutoff)}",
        f"- Estimated spend: ${ledger.spent:.2f} of ${config.budget.total_usd:.2f}",
        f"- Records: {len(review.accepted)} accepted, {len(review.deferred)} need review, "
        f"{len(review.rejected)} rejected, {len(review.no_change)} no change",
    ]

    writer = outcome.writer_output or {}
    lines += _section("Applied", [
        f"`{r['target']}` {r['op']} {r['fact_id'] or ''}" for r in writer.get("applied", [])
    ])
    lines += _section("Skipped by the writer", [
        f"`{r['target']}` {r['fact_id'] or ''}: {r['reason']}" for r in writer.get("skipped", [])
    ])
    lines += _section("Needs human review", [_record(r) for r in review.deferred])
    lines += _section("Rejected by checks", [
        f"{_record(r)}. Reason: {r['rejected_because']}" for r in review.rejected
    ])
    lines += _section("Handoffs to other owners", [
        f"to `{h['to']}` from {h['from']}: {h['note']}" for h in review.handoffs
    ])
    lines += _proposals(outcome.proposals)
    lines += _workers_table(outcome.workers, ledger)
    lines += _section("Skipped workers", outcome.skipped)
    lines += _section("Evidence notes", evidence.notes)
    lines += _section("Failures", review.failures)
    if outcome.publication:
        lines += _section("Publication", [
            f"branch `{outcome.publication.branch}`, committed: {outcome.publication.committed}",
            *(f"reverted out-of-scope edit: `{p}`" for p in outcome.publication.reverted),
            *([outcome.publication.note] if outcome.publication.note else []),
        ])
    return "\n".join(lines) + "\n"


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return ["", f"## {title}", ""] + [f"- {item}" for item in items]


def _record(record: dict) -> str:
    text = record["text"] if len(record["text"]) <= 200 else record["text"][:197] + "..."
    return f"`{record['target']}` {record['op']} {record['fact_id'] or 'new'} ({record['agent']}): {text}"


def _proposals(proposals: dict | None) -> list[str]:
    items = (proposals or {}).get("proposals", [])
    if not items:
        return []
    lines = ["", "## Structure proposals (not applied)", ""]
    for p in items:
        lines += [
            f"### `{p['path']}` ({p['kind']}, {p['type']})",
            "",
            p["rationale"],
            "",
            "Seed entries:",
            *(f"- {entry}" for entry in p["seed_entries"]),
            "",
            f"Index line: {p['index_line']}",
            "",
            "<details><summary>Draft agent definition</summary>",
            "",
            "```markdown",
            p["agent_draft"],
            "```",
            "",
            "</details>",
            "",
        ]
    return lines


def _workers_table(workers: list[Worker], ledger: Ledger) -> list[str]:
    reasons = {w.label: w.reason for w in workers}
    lines = ["", "## Agents", "", "| Agent | Why | Status | Turns | Cost |", "| --- | --- | --- | --- | --- |"]
    for run in ledger.runs:
        lines.append(
            f"| {run.label} | {reasons.get(run.label, '')} | {run.status} "
            f"| {run.num_turns} | ${run.cost_usd:.2f} |"
        )
    return lines


def _when(moment: datetime | None) -> str:
    return moment.strftime("%Y-%m-%d %H:%M UTC") if moment else "the beginning"
