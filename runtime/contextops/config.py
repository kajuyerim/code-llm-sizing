"""Loads init.md: which agents run, on what evidence, under which limits."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from contextops import frontmatter

BACKENDS = ("claude", "codex")
RUN_POLICIES = ("always", "when-relevant")
SCOPES = ("team", "repository")


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
    auto_memory: bool = False


@dataclass
class OutputSettings:
    runs_dir: Path
    branch: str
    open_pr: bool
    remote: str = "origin"
    target_branch: str | None = None
    forge: str = "auto"


@dataclass
class InitConfig:
    kb_root: Path
    instructions: str
    mode: str | None
    scope: str
    application: str | None
    auth: str
    backend: str
    default_model: str
    shared_rules: Path
    workers: list[WorkerEntry]
    cartographer: Path | None
    writer: Path
    sweeper: Path
    budget: Budget
    conversation: ConversationSettings
    memory: MemorySettings
    output: OutputSettings


def load_config(kb_root: Path, backend: str | None = None) -> InitConfig:
    meta, body = frontmatter.read(kb_root / "init.md")
    evidence = meta.get("evidence", {})
    after = meta.get("after", {})
    output = meta.get("output", {})

    backend = backend if backend is not None else meta.get("backend", "claude")
    if backend not in BACKENDS:
        raise ValueError("Choose claude or codex as the maintenance backend")
    if backend == "codex" and meta.get("auth", "subscription") != "subscription":
        raise ValueError("Codex requires auth: subscription for ChatGPT sign-in")

    # Unknown keys in these sections raise TypeError on purpose, so typos in init.md surface early.
    config = InitConfig(
        kb_root=kb_root,
        instructions=body.strip(),
        mode=meta.get("mode"),
        scope=meta.get("scope", "team"),
        application=meta.get("application"),
        auth=meta.get("auth", "subscription"),
        backend=backend,
        default_model=(meta.get("codex_model", "gpt-6.1-terra") if backend == "codex"
                       else meta.get("model", "sonnet")),
        shared_rules=kb_root / meta.get("shared_rules", "agents/shared-rules.md"),
        workers=[_worker(kb_root, raw) for raw in meta.get("workers", [])],
        cartographer=kb_root / after["cartographer"] if after.get("cartographer") else None,
        writer=kb_root / after.get("writer", "agents/writer.md"),
        sweeper=kb_root / meta.get("sweeper", "agents/sweeper.md"),
        budget=Budget(**meta.get("budget", {})),
        conversation=ConversationSettings(**evidence.get("conversation", {})),
        memory=MemorySettings(**evidence.get("memory", {})),
        output=OutputSettings(
            runs_dir=Path(output.get("runs_dir", "~/.contextops/runs")).expanduser(),
            branch=output.get("branch", "contextops/{strategy}/{run_id}"),
            open_pr=output.get("open_pr", False),
            remote=output.get("remote", "origin"),
            target_branch=output.get("target_branch"),
            forge=output.get("forge", "auto"),
        ),
    )

    if not isinstance(config.default_model, str) or not config.default_model.strip():
        raise ValueError("The maintenance model must be a nonempty string")
    if not config.workers:
        raise ValueError("init.md lists no workers")
    if config.output.forge not in ("auto", "github", "gitlab", "none"):
        raise ValueError("init.md: output.forge must be auto, github, gitlab, or none")
    if config.scope not in SCOPES:
        raise ValueError("init.md: scope must be team or repository")
    if config.application is not None and not _valid_name(config.application):
        raise ValueError("init.md: application must be a lowercase name such as my-app")
    if config.auth not in ("subscription", "api-key"):
        raise ValueError(f"init.md: unknown auth '{config.auth}'")
    if config.conversation.source != "claude-code":
        raise ValueError("init.md: only claude-code transcripts are supported for now")
    if config.conversation.since not in ("last-run", "base-commit"):
        raise ValueError("init.md: conversation since must be last-run or base-commit")
    if min(config.budget.per_agent_usd, config.budget.total_usd,
           config.budget.max_turns, config.budget.max_parallel,
           config.conversation.max_chars_per_session) <= 0:
        raise ValueError("init.md: budgets and limits must be positive")
    if not all(token in config.output.branch for token in ("{strategy}", "{run_id}")):
        raise ValueError("init.md: output.branch must include {strategy} and {run_id}")
    for path in [config.shared_rules, config.writer, config.cartographer, config.sweeper,
                 *(w.agent for w in config.workers)]:
        if path and (not path.is_file() or not path.resolve().is_relative_to(kb_root.resolve())):
            raise ValueError("init.md: agent definitions must exist inside the knowledge checkout")
    return config


def _valid_name(name: str) -> bool:
    import re
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]*", str(name)))


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
    target = entry.owns or entry.for_each
    if Path(target).is_absolute() or ".." in Path(target).parts:
        raise ValueError("init.md: worker targets must be relative knowledge paths")
    if not target.startswith(("core/", "tools/")):
        raise ValueError("init.md: worker targets must be under core/ or tools/")
    return entry
