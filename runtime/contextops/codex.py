"""Codex exec/fork transport adapted from the historical GPT pilot's codex_backend.

Only the CLI transport, scoped file-tool pattern and strict-schema conversion carry over.
The installed runtime supplies roles, frozen evidence, validation, writing and reporting.
"""

import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import jsonschema

from contextops.agents import AgentRun, AgentSpec, EDIT_TOOLS, READ_ONLY_TOOLS

# With a read-only native sandbox, the only writer is the scoped stdio tool server.
DISABLED = (
    "shell_tool", "unified_exec", "shell_snapshot", "apps", "plugins", "remote_plugin",
    "memories", "multi_agent", "multi_agent_v2", "browser_use", "computer_use",
    "image_generation", "view_image", "hooks", "skill_search", "workspace_dependencies",
    "goals", "sleep_tool", "code_mode", "code_mode_host", "in_app_browser",
)
TIMEOUT_SECONDS = 600


class CodexResponseError(ValueError):
    """A protocol diagnostic safe to include in the run report."""


def strict_schema(schema: dict) -> dict:
    """Represent optional fields as required, nullable fields for Codex structured output."""
    result = dict(schema)
    if "enum" in schema:
        result.setdefault("type", "string")
    if "items" in schema:
        result["items"] = strict_schema(schema["items"])
    if "properties" in schema:
        properties = {}
        for key, value in schema["properties"].items():
            child = strict_schema(value)
            properties[key] = child if key in schema["required"] else {"anyOf": [child, {"type": "null"}]}
        result.update(properties=properties, required=list(properties), additionalProperties=False)
    return result


def _normalize(value):
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items() if v is not None or k == "fact_id"}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _command(spec, system, cwd, dirs, writer, work, scratch, parent):
    tools = [t for t in (READ_ONLY_TOOLS + (EDIT_TOOLS if writer else [])) if t in spec.tools]
    scope = json.dumps([str(cwd), [str(p) for p in dirs], tools, writer])
    settings = {
        "forced_login_method": "chatgpt",
        "approval_policy": "never",
        "project_doc_max_bytes": 0,
        "web_search": "disabled",
        "features.skip_host_skill_discovery": True,
        "memories.use_memories": False,
        "memories.generate_memories": False,
        "developer_instructions": system + "\nUse the contextops_files MCP tools for all file access. "
                                  + f"Relative file paths resolve under {cwd}.",
        "mcp_servers.contextops_files.command": sys.executable,
        "mcp_servers.contextops_files.args": ["-I", "-m", "contextops.codex_files", scope],
        "mcp_servers.contextops_files.required": True,
        "mcp_servers.contextops_files.enabled_tools": tools,
        "mcp_servers.contextops_files.default_tools_approval_mode": "approve",
    }
    cmd = ["codex", "exec", "--ignore-user-config", "--ignore-rules", "--strict-config",
           "--skip-git-repo-check", "--json", "-s", "read-only", "-C", str(work), "-m", spec.model,
           "--output-schema", str(scratch / "schema.json"), "-o", str(scratch / "output.json")]
    for feature in DISABLED:
        cmd.extend(["--disable", feature])
    for key, value in settings.items():
        cmd.extend(["-c", f"{key}={json.dumps(value, ensure_ascii=False)}"])
    return cmd + (["fork", parent, "-"] if parent else ["-"])


def _read_events(path: Path, run: AgentRun, model: str) -> None:
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event["type"]
            if kind == "thread.started":
                session = str(UUID(event["thread_id"]))
                if run.session_id:
                    raise CodexResponseError("Codex returned multiple thread IDs")
                run.session_id = session
                if session == run.parent_session_id:
                    raise CodexResponseError("Codex fork returned the parent thread ID")
            elif kind == "turn.completed":
                run.num_turns += 1
                usage = event["usage"]
                if not isinstance(usage, dict) or not all(type(n) is int and n >= 0 for n in usage.values()):
                    raise CodexResponseError("Invalid token usage in Codex completion event")
                run.model_usage = {model: usage}
            elif kind in ("error", "turn.failed"):
                raise CodexResponseError("Codex reported a failed turn")
    if not run.session_id or run.num_turns != 1:
        raise CodexResponseError("Expected a new Codex thread and one completed turn")


async def run_codex(spec: AgentSpec, *, label, system, prompt, schema, cwd, dirs, run_dir,
                    resume=None, fork=False) -> AgentRun:
    run = AgentRun(label, status="failed", cost_usd=None, parent_session_id=resume)
    if fork != bool(resume) or run_dir is None:
        run.error = "Codex requires an explicit run directory and an exact parent for every fork"
        return run
    started = time.monotonic()
    # Retain the login location (including a custom CODEX_HOME) without inheriting API keys,
    # provider overrides or another agent's thread/transport environment.
    env = {k: os.environ[k] for k in ("HOME", "PATH", "CODEX_HOME", "TMPDIR", "LANG", "LC_ALL",
                                       "SYSTEMROOT", "USERPROFILE") if k in os.environ}
    if env.get("CODEX_HOME"):
        env["CODEX_HOME"] = str(Path(env["CODEX_HOME"]).expanduser().resolve())
    try:
        # Keep a stable neutral CLI cwd for forks, outside both Git worktrees.
        work = run_dir / "codex-cwd"
        work.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=run_dir, prefix="codex-call-") as tmp:
            scratch = Path(tmp)
            strict = strict_schema(schema)
            (scratch / "schema.json").write_text(json.dumps(strict), encoding="utf-8")
            cmd = _command(spec, system, cwd, dirs, label == "writer", work, scratch, resume)
            with (scratch / "events").open("wb") as events:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, cwd=work, env=env, stdin=asyncio.subprocess.PIPE, stdout=events,
                    stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
                try:
                    await asyncio.wait_for(proc.communicate(prompt.encode()), TIMEOUT_SECONDS)
                finally:
                    if proc.returncode is None:
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        await proc.wait()
            if proc.returncode:
                run.error = f"Codex {'fork' if fork else 'exec'} exited with status {proc.returncode}"
                return run
            _read_events(scratch / "events", run, spec.model)
            raw = json.loads((scratch / "output.json").read_text(encoding="utf-8"))
            jsonschema.validate(raw, strict)
            run.output = _normalize(raw)
            run.status = "success"
    except TimeoutError:
        run.error = "Codex call timed out"
    except FileNotFoundError as exc:
        run.error = "Codex CLI unavailable" if exc.filename == "codex" else "Missing Codex output"
    except CodexResponseError as exc:
        run.error = str(exc)
    except jsonschema.ValidationError:
        run.error = "Codex output did not match the required schema"
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        run.error = f"Invalid Codex invocation or response ({type(exc).__name__})"
    finally:
        run.duration_ms = round((time.monotonic() - started) * 1000)
    return run
