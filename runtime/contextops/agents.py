"""Restricted SDK sessions, tool traces, and reserved estimated budgets."""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from pathlib import Path

from contextops.config import Config, Role
from contextops.files import dump, inside, knowledge_path

SDK_VERSION = "0.2.170"
CLI_VERSION = "2.1.306"
TOKEN_FIELDS = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "webSearchRequests")


@dataclass
class AgentResult:
    label: str
    model: str
    status: str = "not-started"
    session_id: str | None = None
    parent_session_id: str | None = None
    raw_cost_usd: float | None = None
    cost_usd: float | None = None
    raw_model_usage: dict | None = None
    model_usage: dict | None = None
    usage: dict | None = None
    turns: int = 0
    duration_ms: int = 0
    wall_ms: int = 0
    output: dict | None = None
    errors: list[str] = field(default_factory=list)
    tool_reads: list[dict] = field(default_factory=list)
    denied_tools: list[dict] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.status == "success" and self.output is not None and not self.errors


class Ledger:
    """Reserve full call allowances before launch, including a protected writer slot."""

    def __init__(self, total: float, allowance: float):
        self.total = total
        self.allowance = allowance
        self.writer_hold = allowance
        self.reservations: dict[str, float] = {}
        self.results: list[AgentResult] = []
        self.blocked = False

    @property
    def spent(self) -> float:
        return sum(r.cost_usd for r in self.results if r.cost_usd is not None)

    def reserve(self, label: str, *, writer: bool = False) -> bool:
        hold = 0.0 if writer else self.writer_hold
        if self.blocked or self.spent + sum(self.reservations.values()) + hold + self.allowance > self.total + 1e-9:
            return False
        if writer:
            self.writer_hold = 0.0
        self.reservations[label] = self.allowance
        return True

    def settle(self, result: AgentResult) -> None:
        self.reservations.pop(result.label, None)
        self.results.append(result)
        if result.cost_usd is None or self.spent > self.total + 1e-9:
            self.blocked = True


def versions() -> dict:
    from claude_agent_sdk._cli_version import __cli_version__

    installed = version("claude-agent-sdk")
    if installed != SDK_VERSION or __cli_version__ != CLI_VERSION:
        raise RuntimeError(f"requires SDK {SDK_VERSION} with bundled CLI {CLI_VERSION}; found {installed}/{__cli_version__}")
    return {"sdk": installed, "bundled_cli": __cli_version__}


async def run_agent(
    role: Role, label: str, prompt: str, schema: dict, config: Config,
    directory: Path, read_roots: list[Path], artifact: Path, ledger: Ledger,
    *, parent: AgentResult | None = None, write_root: Path | None = None,
) -> AgentResult:
    result = AgentResult(label, role.model, parent_session_id=parent.session_id if parent else None)
    if not ledger.reserve(label, writer=write_root is not None):
        result.status = "skipped-budget"
        dump(artifact, asdict(result))
        return result
    start = time.monotonic()
    try:
        from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, ResultMessage, SystemMessage, query
        from jsonschema import validate

        versions()
        roots = [p.resolve() for p in read_roots]

        def permitted_path(raw, *, writing: bool = False) -> Path:
            if not isinstance(raw, str) or not raw:
                raise ValueError("tool requires an explicit path")
            path = Path(raw)
            path = path if path.is_absolute() else directory / path
            # Retain lexical components so inside() can reject symlink traversal.
            if ".." in path.parts:
                raise ValueError("parent traversal is forbidden")
            if writing:
                if write_root is None:
                    raise ValueError("this role is read-only")
                relative = path.relative_to(write_root.resolve()).as_posix()
                return inside(write_root, knowledge_path(relative))
            for root in roots:
                try:
                    relative = path.relative_to(root).as_posix()
                    return root if relative == "." else inside(root, relative)
                except ValueError:
                    continue
            raise ValueError("path is outside the declared evidence and knowledge roots")

        async def before(data, tool_use_id, context):
            tool, args = data.get("tool_name"), data.get("tool_input", {})
            try:
                if tool in ("Edit", "Write"):
                    permitted_path(args.get("file_path"), writing=True)
                elif tool == "Read":
                    permitted_path(args.get("file_path"))
                elif tool in ("Grep", "Glob"):
                    permitted_path(args.get("path", str(directory)))
                    pattern = args.get("pattern", "") if tool == "Glob" else args.get("glob", "")
                    if pattern and (Path(pattern).is_absolute() or ".." in Path(pattern).parts):
                        raise ValueError("search file patterns must stay within the supplied path")
                elif tool != "StructuredOutput":
                    raise ValueError("tool is not part of this role")
                return {}
            except (ValueError, OSError) as exc:
                result.denied_tools.append({"tool": tool, "reason": str(exc)})
                return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": str(exc)}}

        async def after(data, tool_use_id, context):
            tool, args = data.get("tool_name"), data.get("tool_input", {})
            if tool in ("Read", "Grep", "Glob"):
                result.tool_reads.append({"tool": tool, "path": args.get("file_path", args.get("path", str(directory))),
                                          "pattern": args.get("pattern"), "tool_use_id": tool_use_id})
            return {}

        # The orchestrator removes API credentials from this dedicated runtime
        # process. The invoking shell is unaffected, and SDK children inherit no key.
        options = ClaudeAgentOptions(
            tools=role.tools, allowed_tools=role.tools,
            disallowed_tools=["Bash", "Agent", "Task", "WebFetch", "WebSearch", "NotebookEdit", "Skill"],
            system_prompt={"type": "custom", "prompt": config.prompt(role), "snapshot": False},
            permission_mode="dontAsk", model=role.model,
            cwd=str(directory), add_dirs=[str(p) for p in roots],
            setting_sources=[], skills=[], plugins=[], strict_mcp_config=True, mcp_servers={},
            env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
            max_turns=config.budget["max_turns"], max_budget_usd=ledger.allowance,
            output_format={"type": "json_schema", "schema": schema},
            resume=parent.session_id if parent else None, fork_session=parent is not None,
            hooks={"PreToolUse": [HookMatcher(hooks=[before])], "PostToolUse": [HookMatcher(hooks=[after])]},
        )
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                result.session_id = message.data.get("session_id")
            if isinstance(message, ResultMessage):
                result.session_id = message.session_id
                result.status = message.subtype
                result.raw_cost_usd = message.total_cost_usd
                result.raw_model_usage = message.model_usage
                result.usage = message.usage
                result.turns = message.num_turns
                result.duration_ms = message.duration_ms
                result.output = message.structured_output
                result.errors.extend(message.errors or [])
                if message.is_error:
                    result.errors.append("SDK returned is_error=true")
        if result.status == "success":
            validate(result.output, schema)
            if not result.session_id:
                raise ValueError("SDK returned no session ID")
            if parent and result.session_id == parent.session_id:
                raise ValueError("fork returned its parent's session ID")
        _account(result, parent)
    except Exception as exc:
        result.errors.append(f"{type(exc).__name__}: {exc}")
        result.status = "failed"
        # Preserve usage from an error result, including before query() raises.
        _account(result, parent)
    finally:
        result.wall_ms = round((time.monotonic() - start) * 1000)
        ledger.settle(result)
        dump(artifact, asdict(result))
    return result


def _account(result: AgentResult, parent: AgentResult | None) -> None:
    if result.raw_cost_usd is None or not math.isfinite(result.raw_cost_usd) or result.raw_cost_usd < 0:
        return
    if result.status in ("error_during_execution", "failed") and result.raw_cost_usd == 0:
        # Crash results can be zeroed by the CLI. Do not turn that into a free call.
        return
    inherited = parent.raw_cost_usd if parent else 0.0
    if inherited is None or result.raw_cost_usd < inherited - 1e-9:
        result.cost_usd = None
        return
    result.cost_usd = max(0.0, result.raw_cost_usd - inherited)
    if result.raw_model_usage is None:
        return
    result.model_usage = {}
    for model, usage in result.raw_model_usage.items():
        previous = (parent.raw_model_usage or {}).get(model, {}) if parent else {}
        delta = {}
        for key in (*TOKEN_FIELDS, "costUSD"):
            if key in usage:
                value = usage[key] - previous.get(key, 0)
                if value < -1e-9:
                    result.model_usage = None
                    return
                delta[key] = max(0, value)
        result.model_usage[model] = delta
