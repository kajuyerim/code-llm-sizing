"""Loads init.md: which agents run, on what evidence, under which limits."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from contextops import frontmatter

RUN_POLICIES = ("always", "when-relevant")


@dataclass
class WorkerEntry:
    agent: Path
    owns: str | None
    for_each: str | None
    run: str


@dataclass
class Budget:
    per_agent_usd: float = 0.5
    total_usd: float = 3.0
    max_turns: int = 30
    max_parallel: int = 3


@dataclass
class ConversationSettings:
    source: str = "claude-code"
    since: str = "last-run"
    include_sidechains: bool = False
    max_chars_per_session: int = 200_000


@dataclass
class MemorySettings:
    repo_files: list[str] = field(
        default_factory=lambda: ["CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md"]
    )
    auto_memory: bool = True


@dataclass
class OutputSettings:
    runs_dir: Path
    branch: str
    open_pr: bool


@dataclass
class InitConfig:
    kb_root: Path
    instructions: str
    mode: str
    auth: str
    default_model: str
    shared_rules: Path
    workers: list[WorkerEntry]
    cartographer: Path | None
    writer: Path
    budget: Budget
    conversation: ConversationSettings
    memory: MemorySettings
    output: OutputSettings


def load_config(kb_root: Path) -> InitConfig:
    meta, body = frontmatter.read(kb_root / "init.md")
    evidence = meta.get("evidence", {})
    after = meta.get("after", {})
    output = meta.get("output", {})

    # Unknown keys in these sections raise TypeError on purpose, so typos in init.md surface early.
    config = InitConfig(
        kb_root=kb_root,
        instructions=body.strip(),
        mode=meta.get("mode", "fresh-specialists"),
        auth=meta.get("auth", "subscription"),
        default_model=meta.get("model", "sonnet"),
        shared_rules=kb_root / meta.get("shared_rules", "agents/shared-rules.md"),
        workers=[_worker(kb_root, raw) for raw in meta.get("workers", [])],
        cartographer=kb_root / after["cartographer"] if after.get("cartographer") else None,
        writer=kb_root / after.get("writer", "agents/writer.md"),
        budget=Budget(**meta.get("budget", {})),
        conversation=ConversationSettings(**evidence.get("conversation", {})),
        memory=MemorySettings(**evidence.get("memory", {})),
        output=OutputSettings(
            runs_dir=Path(output.get("runs_dir", "~/.contextops/runs")).expanduser(),
            branch=output.get("branch", "contextops/{run_id}"),
            open_pr=output.get("open_pr", True),
        ),
    )

    if not config.workers:
        raise ValueError("init.md lists no workers")
    if config.auth not in ("subscription", "api-key"):
        raise ValueError(f"init.md: unknown auth '{config.auth}'")
    if config.conversation.source != "claude-code":
        raise ValueError("init.md: only claude-code transcripts are supported for now")
    return config


def _worker(kb_root: Path, raw: dict) -> WorkerEntry:
    entry = WorkerEntry(
        agent=kb_root / raw["agent"],
        owns=raw.get("owns"),
        for_each=raw.get("for_each"),
        run=raw.get("run", "always"),
    )
    if bool(entry.owns) == bool(entry.for_each):
        raise ValueError(f"init.md: {raw['agent']} needs exactly one of 'owns' or 'for_each'")
    if entry.run not in RUN_POLICIES:
        raise ValueError(f"init.md: {raw['agent']} has unknown run policy '{entry.run}'")
    return entry
