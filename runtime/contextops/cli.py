"""Explicit installation and foreground commands; the hook only captures and spawns."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from contextops import git
from contextops.config import load_config
from contextops.runs import prepare

HOOK_MARKER = "# Context Ops sweeper-first pre-push adapter"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="contextops")
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install", help="explicitly install the pre-push adapter")
    install.add_argument("--repo", type=Path, default=Path.cwd())
    install.add_argument("--kb", type=Path, required=True)
    install.add_argument("--force", action="store_true")
    hook = commands.add_parser("hook", help="read exact refs from Git's pre-push stdin")
    hook.add_argument("remote")
    hook.add_argument("url", nargs="?")
    run = commands.add_parser("run", help="execute a prepared, never-attempted run directory")
    run.add_argument("run_dir", type=Path)
    sweep = commands.add_parser("sweep", help="prepare and execute an explicit commit range")
    sweep.add_argument("--repo", type=Path, default=Path.cwd())
    sweep.add_argument("--kb", type=Path)
    sweep.add_argument("--base", required=True)
    sweep.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            _install(args)
        elif args.command == "hook":
            _hook(args)
        else:
            from contextops.orchestrator import execute

            if args.command == "sweep":
                app = git.root(args.repo)
                configured = git.call(app, "config", "--get", "contextops.kb", check=False).strip()
                kb = args.kb or (Path(configured) if configured else None)
                if kb is None:
                    raise ValueError("pass --kb or explicitly install the adapter first")
                directory = prepare(app, kb, args.base, args.head).directory
            else:
                directory = args.run_dir
            report = asyncio.run(execute(directory))
            print(report)
            from contextops.files import load
            if load(report.parent / "status.json")["status"] != "complete":
                raise SystemExit(1)
    except Exception as exc:
        print(f"contextops: {exc}", file=sys.stderr)
        if args.command != "hook":
            raise SystemExit(1) from exc


def _install(args) -> None:
    import shlex

    app, kb = git.root(args.repo), git.root(args.kb)
    if app == kb or app in kb.parents or kb in app.parents:
        raise ValueError("application and knowledge checkouts must be separate")
    load_config(kb)
    hooks = git.setting(app, "core.hooksPath")
    if hooks:
        raise ValueError("core.hooksPath is configured; integrate the adapter manually instead of replacing shared hooks")
    hook = Path(git.call(app, "rev-parse", "--git-path", "hooks/pre-push").strip())
    if not hook.is_absolute():
        hook = app / hook
    if hook.is_symlink():
        raise ValueError("refusing to replace a symlink hook")
    if hook.exists() and HOOK_MARKER not in hook.read_text(encoding="utf-8"):
        if not args.force:
            raise ValueError("an existing pre-push hook needs explicit --force replacement")
        backup = hook.with_name("pre-push.contextops-backup")
        if backup.exists():
            raise ValueError("hook backup already exists; inspect it before replacement")
        backup.write_bytes(hook.read_bytes())
        backup.chmod(hook.stat().st_mode)
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f'#!/bin/sh\n{HOOK_MARKER}\n{shlex.quote(sys.executable)} -m contextops hook "$@" || true\nexit 0\n', encoding="utf-8")
    hook.chmod(0o755)
    git.call(app, "config", "contextops.kb", str(kb))
    print(f"Installed {hook}; runtime remains unverified until a separately authorized run.")


def _hook(args) -> None:
    app = git.root(Path.cwd())
    configured = git.call(app, "config", "--get", "contextops.kb", check=False).strip()
    if not configured:
        return
    kb = Path(configured).resolve()
    if kb == app:
        return
    for line in sys.stdin:
        fields = line.split()
        if len(fields) != 4 or fields[1] == git.ZERO:
            continue
        local_ref, head, remote_ref, base = fields
        try:
            # Preparation contains no SDK calls. Every ref gets an independent run.
            run = prepare(app, kb, base, head, ref=local_ref, remote_ref=remote_ref, remote=args.remote)
            environment = git.environment()
            for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
                environment.pop(key, None)
            with (run.directory / "run.log").open("a", encoding="utf-8") as log:
                subprocess.Popen([sys.executable, "-m", "contextops", "run", str(run.directory)],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 cwd=run.directory, env=environment, start_new_session=True)
            print(f"contextops: background report will be {run.directory / 'report.md'}", file=sys.stderr)
        except Exception as exc:
            print(f"contextops: maintenance skipped for {local_ref}: {exc}", file=sys.stderr)
