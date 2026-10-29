"""Agent definitions (agents/*.md) and how one of them is run through the Agent SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from contextops import frontmatter
from contextops.config import InitConfig

READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
EDIT_TOOLS = ["Edit", "Write"]
# Never available to maintenance agents: no shell, no network, no nested agents.
BLOCKED_TOOLS = ["Bash", "WebFetch", "WebSearch", "NotebookEdit", "Agent", "Task"]


@dataclass
class AgentSpec:
    name: str
    path: Path
    prompt: str
    model: str
    tools: list[str]
    max_turns: int | None = None


@dataclass
class AgentRun:
    label: str
    status: str = "not-started"
    session_id: str | None = None
    cost_usd: float = 0.0
    num_turns: int = 0
    duration_ms: int = 0
    model_usage: dict | None = None
    output: dict | None = None
    error: str | None = None


class Ledger:
    """Every agent call made in a run, and the run's spend cap."""

    def __init__(self, limit_usd: float):
        self.limit_usd = limit_usd
        self.runs: list[AgentRun] = []

    def add(self, run: AgentRun) -> None:
        self.runs.append(run)

    @property
    def spent(self) -> float:
        # A forked session reports the parent's cost again; a strategy that forks
        # should subtract the inherited part before adding the run here.
        return sum(run.cost_usd for run in self.runs)

    def has_room(self) -> bool:
        return self.spent < self.limit_usd


def load_agent(path: Path, default_model: str) -> AgentSpec:
    meta, body = frontmatter.read(path)
    return AgentSpec(
        name=meta.get("name", path.stem),
        path=path,
        prompt=body.strip(),
        model=meta.get("model", default_model),
        tools=list(meta.get("tools", READ_ONLY_TOOLS)),
        max_turns=meta.get("maxTurns"),
    )


def system_prompt(config: InitConfig, spec: AgentSpec) -> str:
    """Shared rules first, then the run notes from init.md, then the agent's own definition."""
    _, shared = frontmatter.read(config.shared_rules)
    parts = [shared.strip(), config.instructions, spec.prompt]
    return "\n\n---\n\n".join(part for part in parts if part)


async def run_agent(
    spec: AgentSpec,
    *,
    label: str,
    system: str,
    prompt: str,
    schema: dict,
    cwd: Path,
    dirs: list[Path],
    budget_usd: float,
    max_turns: int,
    resume: str | None = None,
    fork: bool = False,
) -> AgentRun:
    options = ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code", "append": system},
        model=spec.model,
        allowed_tools=spec.tools,
        disallowed_tools=[t for t in BLOCKED_TOOLS + EDIT_TOOLS if t not in spec.tools],
        permission_mode="dontAsk",
        cwd=str(cwd),
        add_dirs=[str(d) for d in dirs],
        max_turns=spec.max_turns or max_turns,
        max_budget_usd=budget_usd,
        output_format={"type": "json_schema", "schema": schema},
        # Keep the developer's own settings, hooks and CLAUDE.md out of maintenance runs.
        setting_sources=[],
        resume=resume,
        fork_session=fork,
    )

    run = AgentRun(label)
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                run.status = message.subtype
                run.session_id = message.session_id
                run.cost_usd = message.total_cost_usd or 0.0
                run.num_turns = message.num_turns
                run.duration_ms = message.duration_ms
                run.model_usage = getattr(message, "model_usage", None)
                run.output = message.structured_output if message.subtype == "success" else None
    except Exception as exc:  # one broken agent should not sink the whole run
        run.status, run.error = "crashed", f"{type(exc).__name__}: {exc}"
    return run
