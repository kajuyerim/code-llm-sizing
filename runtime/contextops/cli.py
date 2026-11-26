"""Command line: install the hook, react to a push, or sweep a range by hand."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from contextops import gitutil
from contextops.config import BACKENDS
from contextops.run import create_run

from contextops.attach import HOOK


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="contextops")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("ui", help="open the local web console")

    initialize = commands.add_parser("init", help="prepare empty knowledge on a new local branch")
    initialize.add_argument("--kb", type=Path, required=True)
    initialize.add_argument("--branch", required=True)
    initialize.add_argument("--scope", choices=["team", "repository"],
                            help="team: shared by a team's applications; repository: one application")
    initialize.add_argument("--application", help="with --scope repository, the application's name")

    attach = commands.add_parser("attach", help="connect an application so its coding agent reads this knowledge "
                                 "and its pushes start maintenance")
    attach.add_argument("--repo", type=Path, default=Path.cwd(), help="the application checkout")
    attach.add_argument("--kb", type=Path, required=True, help="the knowledge checkout")
    attach.add_argument("--strategy", choices=["fresh-specialists", "sweeper-first"],
                        help="strategy for push-triggered runs (required unless --no-hook)")
    attach.add_argument("--name", help="application name used in scopes; defaults to the folder name")
    attach.add_argument("--no-hook", action="store_true", help="only wire reading, no push-triggered maintenance")
    attach.add_argument("--no-refresh", action="store_true", help="do not fast-forward knowledge at session start")
    attach.add_argument("--no-digest", action="store_true", help="do not add a digest of the entries at session start")
    attach.add_argument("--force", action="store_true", help="replace an existing pre-push hook")

    refresh = commands.add_parser("refresh", help="fast-forward a clean knowledge checkout to its upstream")
    refresh.add_argument("--kb", type=Path, required=True)
    refresh.add_argument("--verbose", action="store_true")
    refresh.add_argument("--no-fetch", action="store_true", help="only print the digest")
    refresh.add_argument("--digest", action="store_true", help="print a digest of the entries (session-start context)")

    install = commands.add_parser("install", help="install the pre-push hook in an application repo")
    install.add_argument("--kb", type=Path, required=True, help="path to the knowledge base checkout")
    install.add_argument("--repo", type=Path, default=Path.cwd())
    install.add_argument("--force", action="store_true", help="replace an existing pre-push hook")

    hook = commands.add_parser("hook", help="called by git's pre-push hook")
    hook.add_argument("remote")
    hook.add_argument("url", nargs="?")

    run = commands.add_parser("run", help="run a prepared run directory in the foreground")
    run.add_argument("run_dir", type=Path)

    checks = commands.add_parser("checks", help="propose, verify, or apply a local application check")
    check_commands = checks.add_subparsers(dest="action", required=True)
    for action in ("propose", "verify", "apply"):
        check = check_commands.add_parser(action)
        check.add_argument("run_dir", type=Path)
        if action != "propose":
            check.add_argument("sha256", help="digest of the reviewed check.patch")
        if action == "verify":
            check.add_argument("verification_command", nargs=argparse.REMAINDER,
                               metavar="COMMAND", help="explicit command and arguments to run")

    sessions = commands.add_parser("sessions", help="list Claude Code sessions for an application, to pick --session IDs")
    sessions.add_argument("--repo", type=Path, default=Path.cwd())
    sessions.add_argument("--limit", type=int, default=20)

    export = commands.add_parser("export-session", help="write a shareable copy of one session, with local paths replaced")
    export.add_argument("--repo", type=Path, default=Path.cwd())
    export.add_argument("--session", required=True)
    export.add_argument("--out", type=Path, required=True)

    imp = commands.add_parser("import-session", help="install exported sessions for an application checkout")
    imp.add_argument("--repo", type=Path, default=Path.cwd())
    imp.add_argument("files", type=Path, nargs="+")

    sweep = commands.add_parser("sweep", help="sweep a commit range by hand, without pushing")
    sweep.add_argument("--base", required=True)
    sweep.add_argument("--head", default="HEAD")
    sweep.add_argument("--repo", type=Path, default=Path.cwd())
    sweep.add_argument("--kb", type=Path, help="defaults to the repo's contextops.kb setting")
    sweep.add_argument("--backend", choices=BACKENDS, help="maintenance backend (default from init.md)")
    sweep.add_argument("--strategy", choices=["fresh-specialists", "sweeper-first"], required=True)
    sweep.add_argument("--session", action="append", required=True, help="Claude Code session ID; repeat to include more")
    sweep.add_argument("--cutoff", type=_cutoff, help="ISO 8601 timestamp with timezone; defaults to now")

    args = parser.parse_args(argv)
    handlers = {"ui": _ui, "init": _init, "attach": _attach, "refresh": _refresh, "install": _install, "hook": _hook, "run": _run, "sweep": _sweep, "sessions": _sessions,
                "export-session": _export_session, "import-session": _import_session, "checks": _checks}
    try:
        handlers[args.command](args)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        # Do not echo subprocess stderr, which can contain private source or auth data.
        message = "Git operation failed; check the repository and commit refs" if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        parser.exit(2, f"contextops: {message}\n")


def _ui(_args: argparse.Namespace) -> None:
    from contextops.web_console import serve

    serve()


def _cutoff(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError
        return stamp
    except ValueError:
        raise argparse.ArgumentTypeError("cutoff must be ISO 8601 with a timezone") from None


def _init(args: argparse.Namespace) -> None:
    from contextops.onboarding import initialize_knowledge

    changed = initialize_knowledge(args.kb, args.branch, args.scope, args.application)
    print(f"Prepared empty knowledge on {args.branch} (no model calls)."
          + (f" Scope: {args.scope}." if args.scope else ""))
    print("Files reset:\n" + "\n".join(f"  {name}" for name in changed))
    print("Review init.md, configure your run, and commit the baseline before sweeping.")
    print("For subsequent runs, reuse the accepted knowledge branch without running init again.")


def _attach(args: argparse.Namespace) -> None:
    from contextops.attach import attach

    done = attach(args.repo, args.kb, args.strategy, args.name, hook=not args.no_hook,
                  refresh=not args.no_refresh, force=args.force, digest=not args.no_digest)
    print("Attached:\n" + "\n".join(f"  {item}" for item in done))
    print("These files are local to this checkout and excluded from Git. New Claude Code sessions in the "
          "application read the knowledge; pushes start maintenance in the background when a hook is installed.")


def _refresh(args: argparse.Namespace) -> None:
    from contextops.attach import digest, refresh

    if not args.no_fetch:
        message = refresh(args.kb)
        # Session-start output becomes agent context, so mention only real problems.
        quiet = message.startswith(("knowledge checkout at", "knowledge checkout has no upstream"))
        if args.verbose or not quiet:
            print(f"contextops: {message}")
    if args.digest:
        text = digest(args.kb)
        if text:
            print(text)


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
    from contextops.attach import refresh

    app = gitutil.repo_root(Path.cwd())
    kb = gitutil.config_get(app, "contextops.kb")
    if not kb or Path(kb).resolve() == app.resolve():
        return  # not configured, or a push of the knowledge base itself
    strategy = gitutil.config_get(app, "contextops.strategy")
    selected = gitutil.config_get(app, "contextops.sessions")
    # Start from the latest merged knowledge so the review request applies cleanly.
    note = refresh(Path(kb))
    if not note.startswith("knowledge checkout at"):
        print(f"contextops: {note}", file=sys.stderr)

    # git sends one line per ref: <local ref> <local sha> <remote ref> <remote sha>
    for line in sys.stdin:
        fields = line.split()
        if len(fields) != 4 or fields[1] == gitutil.ZERO_SHA:
            continue  # malformed, or a branch deletion
        local_ref, local_sha, _, remote_sha = fields
        try:
            # Pinned sessions win; otherwise every session active since the last run is evidence.
            ctx = create_run(app, Path(kb), args.remote, local_ref, local_sha, remote_sha, strategy=strategy,
                             sessions=selected.split() if selected else None, auto_select=not selected)
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

    _execute(args.run_dir.expanduser(), orchestrate)


def _checks(args: argparse.Namespace) -> None:
    from contextops import checks

    run_dir = args.run_dir.expanduser().resolve()
    if args.action == "propose":
        print(asyncio.run(checks.propose_manually(run_dir)))
    elif args.action == "apply":
        print(f"Staged the reviewed patch in {checks.apply(run_dir, args.sha256)}")
    else:
        command = args.verification_command
        if command and command[0] == "--":
            command = command[1:]
        code = checks.verify(run_dir, args.sha256, command)
        if code:
            raise SystemExit(code if code > 0 else 128 - code)


def _sessions(args: argparse.Namespace) -> None:
    from contextops import transcripts

    app = gitutil.repo_root(args.repo).resolve()
    found = transcripts.list_sessions(app)
    if not found:
        sys.exit(f"No Claude Code sessions with messages in {app} under {transcripts.PROJECTS_DIR}.")
    print(f"{'SESSION ID':36}  {'LAST MESSAGE (UTC)':19}  {'USER':>4}  {'AGENT':>5}  OPENING MESSAGE")
    for s in found[: args.limit]:
        print(f"{s.session_id:36}  {s.last[:19].replace('T', ' '):19}  {s.user_messages:>4}  {s.agent_messages:>5}  {s.opening}")
    print(f"\nPass the ones you want as --session ID (repeat for several). {len(found)} session(s) found.")


def _export_session(args: argparse.Namespace) -> None:
    from contextops import transcripts

    app = gitutil.repo_root(args.repo).resolve()
    lines = transcripts.export_session(app, args.session)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} records to {args.out}. Thinking and tool results were dropped and local paths "
          "replaced; message text is unchanged, so review it before sharing.")


def _import_session(args: argparse.Namespace) -> None:
    from contextops import transcripts

    app = gitutil.repo_root(args.repo).resolve()
    for source in args.files:
        target = transcripts.import_session(source, app)
        print(f"{target.stem}  ->  {target}")


def _sweep(args: argparse.Namespace) -> None:
    from contextops.orchestrator import orchestrate

    app = gitutil.repo_root(args.repo)
    kb = args.kb or gitutil.config_get(app, "contextops.kb")
    if not kb:
        sys.exit("No knowledge base: pass --kb or run `contextops install` first.")
    ctx = create_run(
        app, Path(kb).expanduser(), "origin", "manual",
        args.head, args.base, backend=args.backend, strategy=args.strategy, sessions=args.session, cutoff=args.cutoff,
    )
    if ctx is None:
        sys.exit("Nothing to sweep: base and head are the same commit.")
    _execute(ctx.run_dir, orchestrate)


def _execute(run_dir: Path, orchestrate) -> None:
    print(f"Run artifacts: {run_dir}", flush=True)
    was_started = (run_dir / "started").exists()
    try:
        asyncio.run(orchestrate(run_dir))
    except Exception:
        from contextops.events import emit
        if not was_started and not (run_dir / "started").exists() and (run_dir / "run.json").is_file():
            emit(run_dir, "run_finished", status="failed")
        raise
    print((run_dir / "completion.txt").read_text(encoding="utf-8"), end="")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    if metrics.get("backend") == "codex" and any(a["status"] != "success" for a in metrics["agents"]):
        raise SystemExit(1)


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
