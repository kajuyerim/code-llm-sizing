"""Builds the frozen evidence pack that every agent in a run reads from.

pack/
  manifest.json          refs, conversation window, what was included or cut
  diff/                  changes.patch, files.txt, commits.txt
  conversation/          one Markdown file per session, messages tagged [msg:<uuid>]
  memory/repo/           agent instruction files at the pushed head
  memory/auto/           Claude Code auto memory for the repository
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from contextops import gitutil, transcripts
from contextops.config import InitConfig
from contextops.run import RunContext, frozen_sessions


@dataclass
class Evidence:
    root: Path
    changed_files: list[str]
    messages: dict[str, set[str]] = field(default_factory=dict)  # session id -> message uuids
    memory_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def conversation_text(self) -> str:
        files = sorted((self.root / "conversation").glob("*.md"))
        return "\n".join(path.read_text(encoding="utf-8") for path in files)


def build_pack(ctx: RunContext, config: InitConfig) -> Evidence:
    evidence = Evidence(root=ctx.pack, changed_files=_write_diff(ctx, ctx.pack / "diff"))
    _write_conversation(ctx, config, evidence)
    _write_memory(ctx, config, evidence)
    _write_manifest(ctx, evidence)
    return evidence


def _write_diff(ctx: RunContext, out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    repo, base, head = ctx.app_root, ctx.base_sha, ctx.head_sha
    (out / "changes.patch").write_text(gitutil.git(repo, "diff", "--no-color", base, head) + "\n")

    names = gitutil.git(repo, "diff", "--name-status", base, head)
    (out / "files.txt").write_text(names + "\n")

    log_range = head if base == gitutil.EMPTY_TREE else f"{base}..{head}"
    log = gitutil.git(repo, "log", "--date=iso", "--format=%H %an %ad%n%s%n%b", log_range)
    (out / "commits.txt").write_text(log + "\n")

    # Renames are listed as "R100<TAB>old<TAB>new"; the new path is the one that exists at head.
    return [line.split("\t")[-1] for line in names.splitlines() if line]


def _write_conversation(ctx: RunContext, config: InitConfig, evidence: Evidence) -> None:
    out = ctx.pack / "conversation"
    out.mkdir(parents=True, exist_ok=True)
    settings = config.conversation
    sessions = frozen_sessions(ctx)
    if not sessions:
        raise ValueError("Frozen conversation contains no selected sessions")
    evidence.notes.append("Explicit sessions: complete retained history through cutoff; tool results and thinking excluded.")

    for session in sessions:
        text, kept = transcripts.to_markdown(session, settings.max_chars_per_session)
        (out / f"{session.session_id}.md").write_text(text, encoding="utf-8")
        evidence.messages[session.session_id] = kept
        if len(kept) < len(session.messages):
            evidence.notes.append(
                f"Session {session.session_id}: kept the newest {len(kept)} "
                f"of {len(session.messages)} messages."
            )


def _write_memory(ctx: RunContext, config: InitConfig, evidence: Evidence) -> None:
    sources = [
        (ctx.app_snapshot / name, f"memory/repo/{name}") for name in config.memory.repo_files
    ]
    if config.memory.auto_memory:
        auto = transcripts.auto_memory_dir(ctx.app_root)
        if auto.is_dir():
            sources += [(path, f"memory/auto/{path.name}") for path in sorted(auto.glob("*.md"))]

    for source, relative in sources:
        if source.is_file():
            target = ctx.pack / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            evidence.memory_files.append(relative)


def _write_manifest(ctx: RunContext, evidence: Evidence) -> None:
    manifest = {
        "run_id": ctx.run_id,
        "strategy": ctx.strategy,
        "selected_sessions": ctx.sessions,
        "conversation_sha256": ctx.conversation_sha256,
        "application": str(ctx.app_snapshot),
        "ref": ctx.ref,
        "base_sha": ctx.base_sha,
        "head_sha": ctx.head_sha,
        "knowledge_base": str(ctx.kb_snapshot),
        "knowledge_baseline": ctx.kb_baseline,
        "conversation_window": {
            "since": ctx.since.isoformat() if ctx.since else None,
            "cutoff": ctx.cutoff.isoformat(),
        },
        "sessions": {sid: len(uuids) for sid, uuids in evidence.messages.items()},
        "changed_files": len(evidence.changed_files),
        "memory_files": evidence.memory_files,
        "notes": evidence.notes,
    }
    (ctx.pack / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
