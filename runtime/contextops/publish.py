"""Opens a pull or merge request for a committed result branch in the knowledge repository."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from contextops import gitutil
from contextops.config import InitConfig
from contextops.run import RunContext


@dataclass
class Published:
    url: str | None
    note: str


def forge_of(url: str, setting: str) -> str:
    if setting != "auto":
        return setting
    host = url.lower()
    if "github" in host:
        return "github"
    if "gitlab" in host:
        return "gitlab"
    return "none"


def target_branch(ctx: RunContext, config: InitConfig) -> str | None:
    if config.output.target_branch:
        return config.output.target_branch
    head = gitutil.git(ctx.kb_root, "symbolic-ref", "--quiet", "--short",
                       f"refs/remotes/{config.output.remote}/HEAD", check=False)
    if head:
        return head.split("/", 1)[1]
    # The branch the developer's checkout tracks is the one runs start from.
    upstream = gitutil.git(ctx.kb_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    if upstream.startswith(config.output.remote + "/"):
        return upstream.split("/", 1)[1]
    return None


def publish(ctx: RunContext, config: InitConfig, body: str) -> Published:
    """Push the result branch and open a request for review. Never merges."""
    remote = config.output.remote
    url = gitutil.git(ctx.kb_root, "remote", "get-url", remote, check=False)
    if not url:
        return Published(None, f"no '{remote}' remote in the knowledge checkout; the branch stays local")
    target = target_branch(ctx, config)
    if not target:
        return Published(None, f"could not tell which branch of '{remote}' to target; set output.target_branch")
    title = f"Knowledge updates from {ctx.app_label}@{ctx.head_sha[:7]}"
    forge = forge_of(url, config.output.forge)
    push = ["git", "-C", str(ctx.kb_root), "push", "--set-upstream", remote, ctx.branch]
    if forge == "gitlab" and shutil.which("glab") is None:
        # GitLab push options open the merge request without a separate CLI.
        summary = (f"Context Ops run {ctx.run_id}. Accepted records and evidence are listed in the "
                   "run report on the developer's machine; review the diff before merging.")
        push[4:4] = ["-o", "merge_request.create", "-o", f"merge_request.target={target}",
                     "-o", f"merge_request.title={title}", "-o", f"merge_request.description={summary}"]
    pushed = subprocess.run(push, capture_output=True, text=True)
    if pushed.returncode != 0:
        # Do not echo the remote's message; it can contain credentials or private URLs.
        return Published(None, f"pushing {ctx.branch} to '{remote}' failed; the branch stays local")
    body_file = ctx.run_dir / "pr-body.md"
    body_file.write_text(body, encoding="utf-8")
    if forge == "github" and shutil.which("gh"):
        command = ["gh", "pr", "create", "--base", target, "--head", ctx.branch,
                   "--title", title, "--body-file", str(body_file)]
    elif forge == "gitlab" and shutil.which("glab"):
        command = ["glab", "mr", "create", "--source-branch", ctx.branch, "--target-branch", target,
                   "--title", title, "--description", body, "--yes"]
    elif forge == "gitlab":
        link = next((word for line in pushed.stderr.splitlines() if "merge_request" in line
                     for word in line.split() if word.startswith("https://")), None)
        return Published(link, f"pushed {ctx.branch} and asked GitLab to open a merge request into {target}")
    else:
        return Published(None, f"pushed {ctx.branch} to '{remote}'; open a pull or merge request into {target}")
    created = subprocess.run(command, cwd=ctx.kb_root, capture_output=True, text=True)
    if created.returncode != 0:
        return Published(None, f"pushed {ctx.branch}, but creating the request failed; open it into {target} by hand")
    link = next((w for w in created.stdout.split() if w.startswith("https://")), None)
    return Published(link, f"opened a request from {ctx.branch} into {target}")
