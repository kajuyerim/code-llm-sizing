"""Connect an application checkout to a local knowledge checkout.

Reading: a managed block in the application's CLAUDE.local.md tells the coding agent where the
knowledge is, and .claude/settings.local.json lets it read that directory without prompts. A
SessionStart hook fast-forwards the knowledge checkout so new sessions read merged knowledge.
Maintenance: the pre-push hook prepares a run for the pushed commits in the background.
All application-side files are local and excluded through .git/info/exclude; nothing tracked changes.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

from contextops import gitutil
from contextops.config import load_config

BEGIN, END = "<!-- contextops:begin -->", "<!-- contextops:end -->"
LOCAL_FILES = ("CLAUDE.local.md", ".claude/settings.local.json")
HOOK = """#!/bin/sh
# Installed by contextops. Sweeps the pushed work in the background; never blocks the push.
"{python}" -m contextops hook "$@" || true
exit 0
"""


def pointer(kb: Path, app: str, scope: str, has_agents_md: bool) -> str:
    lines = [BEGIN, "## Shared knowledge", ""]
    if has_agents_md:
        # A CLAUDE.local.md stops Claude Code from reading AGENTS.md on its own.
        lines += ["@AGENTS.md", ""]
    whose = "this application" if scope == "repository" else "this team's applications"
    lines += [
        f"Shared knowledge for {whose} (terminology, stack standards, naming conventions, pitfalls, "
        f"and tool notes) is in a separate checkout: {kb}",
        "",
        f"Read `{kb / 'index.md'}` before starting a task and follow the entries that apply. This "
        f"application is `app:{app}`; `company` entries apply to every application"
        + ("" if scope == "repository" else ", and entries scoped to another application do not apply here")
        + ". The checkout is maintained through reviewed pull or merge requests; do not edit it from here.",
        END,
    ]
    return "\n".join(lines) + "\n"


def attach(app: Path, kb: Path, strategy: str | None, name: str | None = None,
           hook: bool = True, refresh: bool = True, force: bool = False) -> list[str]:
    from contextops.strategies import STRATEGIES

    app, kb = gitutil.repo_root(app).resolve(), gitutil.repo_root(kb.expanduser()).resolve()
    if app == kb or app.is_relative_to(kb) or kb.is_relative_to(app):
        raise ValueError("Application and knowledge repositories must be separate, non-nested checkouts")
    config = load_config(kb)
    name = name or gitutil.config_get(app, "contextops.app") or app.name.lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name):
        raise ValueError("Choose an application name with --name: lowercase letters, digits, dots, hyphens")
    if config.scope == "repository" and config.application and name != config.application:
        raise ValueError(f"This knowledge base serves only '{config.application}' (scope: repository)")
    if hook and strategy not in STRATEGIES:
        raise ValueError("Choose the strategy push-triggered runs use: " + ", ".join(STRATEGIES))
    if hook and gitutil.config_get(app, "core.hooksPath"):
        raise ValueError("core.hooksPath is set, so a hook manager owns the hooks. Rerun with --no-hook and "
                         "call `python -m contextops hook \"$@\"` from its pre-push hook.")
    done = []

    for path in LOCAL_FILES:
        if gitutil.succeeds(app, "ls-files", "--error-unmatch", path):
            raise ValueError(f"{path} is tracked in the application; attach only writes untracked local files")
    exclude = Path(gitutil.git(app, "rev-parse", "--git-path", "info/exclude"))
    exclude = exclude if exclude.is_absolute() else app / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    present = exclude.read_text().splitlines() if exclude.is_file() else []
    missing = [f"/{path}" for path in LOCAL_FILES if f"/{path}" not in present]
    if missing:
        with exclude.open("a") as out:
            out.write("".join(f"{line}\n" for line in missing))

    memory = app / "CLAUDE.local.md"
    text = memory.read_text(encoding="utf-8") if memory.is_file() else ""
    block = pointer(kb, name, config.scope, (app / "AGENTS.md").is_file() and not (app / "CLAUDE.md").is_file())
    if BEGIN in text and END in text:
        start, end = text.index(BEGIN), text.index(END) + len(END)
        text = text[:start] + block.rstrip("\n") + text[end:]
    else:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    memory.write_text(text, encoding="utf-8")
    done.append(f"pointer in {memory}")

    settings_path = app / ".claude" / "settings.local.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    directories = settings.setdefault("permissions", {}).setdefault("additionalDirectories", [])
    if str(kb) not in directories:
        directories.append(str(kb))
    if refresh:
        command = f"{shlex.quote(sys.executable)} -m contextops refresh --kb {shlex.quote(str(kb))}"
        starts = settings.setdefault("hooks", {}).setdefault("SessionStart", [])
        starts[:] = [entry for entry in starts
                     if not any("contextops refresh" in h.get("command", "") for h in entry.get("hooks", []))]
        starts.append({"matcher": "startup", "hooks": [{"type": "command", "command": command, "timeout": 30}]})
    settings_path.parent.mkdir(exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    done.append(f"read access{' and session-start refresh' if refresh else ''} in {settings_path}")

    gitutil.git(app, "config", "contextops.kb", str(kb))
    gitutil.git(app, "config", "contextops.app", name)
    if hook:
        hook_path = Path(gitutil.git(app, "rev-parse", "--git-path", "hooks/pre-push"))
        hook_path = hook_path if hook_path.is_absolute() else app / hook_path
        if hook_path.exists() and "contextops" not in hook_path.read_text() and not force:
            raise ValueError(f"{hook_path} already exists. Rerun with --force to replace it.")
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        hook_path.write_text(HOOK.format(python=sys.executable))
        hook_path.chmod(0o755)
        gitutil.git(app, "config", "contextops.strategy", strategy)
        done.append(f"pre-push maintenance with {strategy} in {hook_path}")
    return done


def refresh(kb: Path, remote: str = "origin") -> str:
    """Fast-forward a clean knowledge checkout to its upstream. Never merges or discards work."""
    kb = gitutil.repo_root(kb.expanduser())
    upstream = gitutil.git(kb, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    if not upstream:
        return "knowledge checkout has no upstream branch; not refreshed"
    if not gitutil.succeeds(kb, "fetch", "--quiet", upstream.split("/", 1)[0]):
        return "could not fetch the knowledge remote; using the local checkout"
    if gitutil.status(kb):
        return "knowledge checkout has local changes; not refreshed"
    if not gitutil.succeeds(kb, "-c", "core.hooksPath=/dev/null", "merge", "--ff-only", "--quiet", "@{u}"):
        return "knowledge checkout has diverged from its upstream; not refreshed"
    return f"knowledge checkout at {gitutil.git(kb, 'rev-parse', '--short', 'HEAD')}"
