"""Applies accepted records on a branch of the knowledge base, then publishes it."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field

from contextops import gitutil, frontmatter
from contextops.access import writable
from contextops.agents import Ledger, load_agent, run_agent, system_prompt
from contextops.config import InitConfig
from contextops.review import Review
from contextops.run import RunContext
from contextops.schemas import WRITER_OUTPUT

# Agent definitions, maintenance guides, skills, init.md and the runtime are never a
# maintenance output, so anything the writer touches outside these paths is reverted.
WRITABLE = ("core/", "tools/", "index.md", "log.md")


@dataclass
class Publication:
    branch: str
    committed: bool = False
    pr_url: str | None = None
    reverted: list[str] = field(default_factory=list)
    note: str | None = None


async def write_changes(
    ctx: RunContext, config: InitConfig, review: Review, ledger: Ledger
) -> tuple[Publication, dict | None]:
    accepted = ctx.run_dir / "accepted.json"
    accepted.write_text(json.dumps(review.accepted, indent=2), encoding="utf-8")

    spec = load_agent(config.writer, config.default_model)
    prompt = "\n".join([
        f"Run: {ctx.run_id}, application {ctx.app_root.name} at {ctx.head_sha[:7]}",
        f"Records to apply: {accepted}",
        f"Evidence pack, if you need to check a record: {ctx.pack}",
        f"Date for log.md: {ctx.cutoff:%Y-%m-%d}",
        "",
        "Apply the records to the knowledge base in your working directory.",
    ])
    run = await run_agent(
        spec,
        label="writer",
        system=system_prompt(config, spec),
        prompt=prompt,
        schema=WRITER_OUTPUT,
        cwd=ctx.kb_snapshot,
        dirs=[ctx.run_dir],
        budget_usd=config.budget.per_agent_usd,
        max_turns=config.budget.max_turns,
    )
    ledger.add(run)

    publication = Publication(branch=ctx.branch, reverted=_revert_outside_scope(ctx))
    for _, path in gitutil.status(ctx.kb_snapshot):
        if gitutil.file_exists(ctx.kb_root, ctx.kb_baseline, path):
            original = gitutil.git(ctx.kb_root, "show", f"{ctx.kb_baseline}:{path}")
            current = ctx.kb_snapshot / path
            if current.is_file() and frontmatter.split(original)[0] != frontmatter.read(current)[0]:
                gitutil.git(ctx.kb_snapshot, "restore", "--source=HEAD", "--staged", "--worktree", "--", path)
                publication.reverted.append(path)
    # Include new Markdown files in the candidate patch, including failed writers.
    for code, path in gitutil.status(ctx.kb_snapshot):
        if code == "??":
            gitutil.git(ctx.kb_snapshot, "add", "-N", "--", path)
    (ctx.run_dir / "knowledge.patch").write_text(gitutil.git(ctx.kb_snapshot, "diff", "HEAD") + "\n")
    if run.status != "success":
        publication.note = "writer failed; candidate patch retained locally, no commit or publication"
        return publication, run.output
    if not gitutil.status(ctx.kb_snapshot):
        publication.note = "the writer made no changes"
        return publication, run.output

    gitutil.git(ctx.kb_snapshot, "add", "-A")
    gitutil.git(
        ctx.kb_snapshot, "-c", "core.hooksPath=/dev/null", "commit", "-m",
        f"contextops: knowledge updates from {ctx.app_root.name}@{ctx.head_sha[:7]}\n\n"
        f"Run: {ctx.run_id}\nAccepted records: {len(review.accepted)}",
    )
    publication.committed = True
    return publication, run.output


def open_pr(ctx: RunContext, body: str) -> str | None:
    """Push the branch and open a PR with gh. Returns the PR URL when one was created."""
    try:
        gitutil.git(ctx.kb_snapshot, "push", "-u", "origin", ctx.branch)
    except subprocess.CalledProcessError:
        return None
    if shutil.which("gh") is None:
        return None

    body_file = ctx.run_dir / "pr-body.md"
    body_file.write_text(body, encoding="utf-8")
    result = subprocess.run(
        [
            "gh", "pr", "create",
            "--head", ctx.branch,
            "--title", f"Knowledge updates from {ctx.app_root.name}@{ctx.head_sha[:7]}",
            "--body-file", str(body_file),
        ],
        cwd=ctx.kb_snapshot, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _revert_outside_scope(ctx: RunContext) -> list[str]:
    reverted = []
    for code, path in gitutil.status(ctx.kb_snapshot):
        if writable(path) and not (ctx.kb_snapshot / path).is_symlink():
            continue
        if code == "??":
            (ctx.kb_snapshot / path).unlink(missing_ok=True)
        else:
            gitutil.git(ctx.kb_snapshot, "restore", "--source=HEAD", "--staged", "--worktree", "--", path)
        reverted.append(path)
    return reverted
