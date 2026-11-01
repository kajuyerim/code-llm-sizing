"""Command line: install the hook, react to a push, or sweep a range by hand."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from contextops import gitutil
from contextops.run import create_run

HOOK = """#!/bin/sh
# Installed by contextops. Sweeps the pushed work in the background; never blocks the push.
"{python}" -m contextops hook "$@" || true
exit 0
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="contextops")
    commands = parser.add_subparsers(dest="command", required=True)

    install = commands.add_parser("install", help="install the pre-push hook in an application repo")
    install.add_argument("--kb", type=Path, required=True, help="path to the knowledge base checkout")
    install.add_argument("--repo", type=Path, default=Path.cwd())
    install.add_argument("--force", action="store_true", help="replace an existing pre-push hook")

    hook = commands.add_parser("hook", help="called by git's pre-push hook")
    hook.add_argument("remote")
    hook.add_argument("url", nargs="?")

    run = commands.add_parser("run", help="run a prepared run directory in the foreground")
    run.add_argument("run_dir", type=Path)

    sweep = commands.add_parser("sweep", help="sweep a commit range by hand, without pushing")
    sweep.add_argument("--base", required=True)
    sweep.add_argument("--head", default="HEAD")
    sweep.add_argument("--repo", type=Path, default=Path.cwd())
    sweep.add_argument("--kb", type=Path, help="defaults to the repo's contextops.kb setting")
    sweep.add_argument("--strategy", choices=["fresh-specialists", "sweeper-first"], required=True)
    sweep.add_argument("--session", action="append", required=True, help="Claude Code session ID; repeat to include more")
    sweep.add_argument("--cutoff", type=_cutoff, help="ISO 8601 timestamp with timezone; defaults to now")

    args = parser.parse_args(argv)
    handlers = {"install": _install, "hook": _hook, "run": _run, "sweep": _sweep}
    try:
        handlers[args.command](args)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        # Do not echo subprocess stderr, which can contain private source or auth data.
        message = "Git operation failed; check the repository and commit refs" if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        parser.exit(2, f"contextops: {message}\n")


def _cutoff(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError
        return stamp
    except ValueError:
        raise argparse.ArgumentTypeError("cutoff must be ISO 8601 with a timezone") from None


def _install(args: argparse.Namespace) -> None:
    repo = gitutil.repo_root(args.repo)
    kb = gitutil.repo_root(args.kb.expanduser())
    hook_path = Path(gitutil.git(repo, "rev-parse", "--git-path", "hooks/pre-push"))
    if not hook_path.is_absolute():
        hook_path = repo / hook_path

    if hook_path.exists() and "contextops" not in hook_path.read_text() and not args.force:
        sys.exit(f"{hook_path} already exists. Rerun with --force to replace it.")
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK.format(python=sys.executable))
    hook_path.chmod(0o755)
    gitutil.git(repo, "config", "contextops.kb", str(kb))
    print(f"Installed {hook_path}\nKnowledge base: {kb}")


def _hook(args: argparse.Namespace) -> None:
    app = gitutil.repo_root(Path.cwd())
    kb = gitutil.config_get(app, "contextops.kb")
    if not kb or Path(kb).resolve() == app.resolve():
        return  # not configured, or a push of the knowledge base itself

    # git sends one line per ref: <local ref> <local sha> <remote ref> <remote sha>
    for line in sys.stdin:
        fields = line.split()
        if len(fields) != 4 or fields[1] == gitutil.ZERO_SHA:
            continue  # malformed, or a branch deletion
        local_ref, local_sha, _, remote_sha = fields
        try:
            # Explicit selection is required even for this experimental adapter.
            selected = gitutil.config_get(app, "contextops.sessions")
            ctx = create_run(app, Path(kb), args.remote, local_ref, local_sha, remote_sha,
                             sessions=selected.split() if selected else None)
        except Exception as exc:  # the push must go through whatever happens here
            print(f"contextops: skipped ({exc})", file=sys.stderr)
            continue
        if ctx:
            _spawn(ctx.run_dir)
            print(f"contextops: sweeping in the background, report at {ctx.run_dir / 'report.md'}",
                  file=sys.stderr)


def _run(args: argparse.Namespace) -> None:
    # Imported here so the hook path stays fast and does not load the Agent SDK.
    from contextops.orchestrator import orchestrate

    print(asyncio.run(orchestrate(args.run_dir.expanduser())))


def _sweep(args: argparse.Namespace) -> None:
    from contextops.orchestrator import orchestrate

    app = gitutil.repo_root(args.repo)
    kb = args.kb or gitutil.config_get(app, "contextops.kb")
    if not kb:
        sys.exit("No knowledge base: pass --kb or run `contextops install` first.")
    ctx = create_run(
        app, Path(kb).expanduser(), "origin", "manual",
        args.head, args.base, strategy=args.strategy, sessions=args.session, cutoff=args.cutoff,
    )
    if ctx is None:
        sys.exit("Nothing to sweep: base and head are the same commit.")
    print(asyncio.run(orchestrate(ctx.run_dir)))


def _spawn(run_dir: Path) -> None:
    log = (run_dir / "run.log").open("a")
    subprocess.Popen(
        [sys.executable, "-m", "contextops", "run", str(run_dir)],
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        cwd=run_dir,
        start_new_session=True,  # survives the end of `git push`
    )
