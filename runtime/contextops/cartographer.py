"""Retain validated unowned findings and propose structure without applying it."""

from __future__ import annotations

import re

from contextops.agents import Ledger, run_agent
from contextops.config import Config
from contextops.files import dump, inside, load
from contextops.review import Review, secrets
from contextops.runs import Run
from contextops.schemas import CARTOGRAPHER_OUTPUT


async def propose(run: Run, config: Config, review: Review, ledger: Ledger) -> dict:
    backlog_file = run.state_dir / "unowned.json"
    backlog = load(backlog_file) if backlog_file.exists() else []
    known = {item["finding_id"] for item in backlog}
    backlog += [{**item, "run_id": run.run_id, "head": run.head, "pack": str(run.pack)}
                for item in review.unowned if item["finding_id"] not in known]
    dump(backlog_file, backlog)
    recent = backlog[-200:]
    findings = run.directory / "unowned-backlog.json"
    dump(findings, recent)
    if config.cartographer is None:
        return {"proposals": [], "status": "disabled", "note": "unowned findings retained locally"}
    result = await run_agent(
        config.cartographer, "cartographer",
        f"Read validated unowned findings from {findings}; current evidence is {run.pack}. "
        f"The knowledge baseline is {run.kb_snapshot}. Propose new structure only for recurring gaps. "
        "Never apply proposals. Cite finding_id values. An empty proposals array is valid.",
        CARTOGRAPHER_OUTPUT, config, run.directory,
        [findings, run.pack, run.kb_snapshot], run.directory / "cartographer.json", ledger,
    )
    if not result.succeeded:
        review.failures.append(f"cartographer: {result.status}")
        return {"proposals": [], "status": result.status}
    allowed_refs = {item["finding_id"] for item in recent}
    accepted = []
    for proposal in result.output["proposals"]:
        try:
            path = proposal["path"]
            pattern = r"core/[a-z0-9]+(?:-[a-z0-9]+)*\.md" if proposal["kind"] == "core-file" else r"products/[a-z0-9]+(?:-[a-z0-9]+)*/"
            if not re.fullmatch(pattern, path):
                raise ValueError("invalid proposed structure path")
            if inside(run.kb_snapshot, path.rstrip("/")).exists():
                raise ValueError("proposed location already exists")
            refs = proposal["finding_refs"]
            if len(set(refs)) < 2 or not set(refs) <= allowed_refs:
                raise ValueError("structure proposal needs at least two known findings")
            text = "\n".join([proposal["rationale"], proposal["definition_draft"], proposal["index_line"], *proposal["seed_entries"]])
            if secrets(text) or "\u2014" in text:
                raise ValueError("structure proposal failed text checks")
            accepted.append(proposal)
        except (ValueError, OSError) as exc:
            review.failures.append(f"discarded structure proposal: {exc}")
    return {"proposals": accepted, "status": "success", "applied": False}
