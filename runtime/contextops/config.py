"""Declarative configuration and role definitions, loaded without agent calls."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from contextops.files import inside, knowledge_path, relative_path

READ_TOOLS = ["Read", "Grep", "Glob"]
WRITE_TOOLS = READ_TOOLS + ["Edit", "Write"]


def markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"frontmatter must be a mapping: {path}")
    return meta, text[match.end():]


def keys(value: dict, allowed: set[str], location: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be a mapping")
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown keys in {location}: {sorted(unknown)}")


@dataclass(frozen=True)
class Role:
    name: str
    definition: str
    instructions: str
    model: str
    tools: list[str]


@dataclass(frozen=True)
class Worker:
    label: str
    role: Role
    owns: str
    prefix: str
    reason: str


@dataclass
class Config:
    root: Path
    mode: str
    model: str
    shared: str
    notes: str
    sweeper: Role
    writer: Role
    cartographer: Role | None
    workers: list[dict]
    budget: dict
    conversation: dict
    memory: dict
    output: dict

    def prompt(self, role: Role) -> str:
        return "\n\n".join((self.shared, self.notes, role.instructions))

    def record(self) -> dict:
        value = asdict(self)
        value["root"] = str(self.root)
        return value


def load_role(root: Path, name: str, model: str, *, writer: bool = False) -> Role:
    path = inside(root, name)
    meta, body = markdown(path)
    keys(meta, {"name", "description", "tools", "model"}, name)
    tools = meta.get("tools", READ_TOOLS)
    expected = WRITE_TOOLS if writer else READ_TOOLS
    if tools != expected:
        raise ValueError(f"{name}: tools must be {expected}")
    label = meta.get("name")
    if not isinstance(label, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", label):
        raise ValueError(f"{name}: invalid role name")
    selected_model = meta.get("model", model)
    if not isinstance(selected_model, str) or not selected_model.strip():
        raise ValueError(f"{name}: model must be a nonempty string")
    return Role(label, name, body.strip(), selected_model, list(tools))


def load_config(root: Path) -> Config:
    root = root.resolve()
    meta, notes = markdown(inside(root, "init.md"))
    keys(meta, {"version", "mode", "auth", "model", "shared_rules", "sweeper", "workers", "after", "budget", "evidence", "output"}, "init.md")
    if meta.get("version") != "0.1" or meta.get("mode") != "sweeper-first":
        raise ValueError("init.md requires version '0.1' and mode sweeper-first")
    if meta.get("auth") != "subscription":
        raise ValueError("only subscription authentication is supported; no API-key fallback")
    model = meta.get("model", "sonnet")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a nonempty string")
    budget = {"per_agent_usd": 0.5, "total_usd": 3.0, "max_turns": 30, "max_parallel": 3}
    keys(meta.get("budget", {}), set(budget), "budget")
    budget.update(meta.get("budget", {}))
    for name, value in budget.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"budget.{name} must be positive and finite")
    for name in ("max_turns", "max_parallel"):
        if not isinstance(budget[name], int):
            raise ValueError(f"budget.{name} must be an integer")
    if budget["total_usd"] < 2 * budget["per_agent_usd"]:
        raise ValueError("total budget must cover a sweeper and the reserved writer allowance")

    evidence = meta.get("evidence", {})
    keys(evidence, {"conversation", "memory"}, "evidence")
    conversation = {"source": "claude-code", "since": "last-run", "include_sidechains": False, "max_chars_per_session": 200000}
    memory = {"repo_files": ["CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md"], "auto_memory": True}
    for name, defaults in (("conversation", conversation), ("memory", memory)):
        supplied = evidence.get(name, {})
        keys(supplied, set(defaults), f"evidence.{name}")
        defaults.update(supplied)
    if conversation["source"] != "claude-code" or conversation["since"] not in ("last-run", "base-commit"):
        raise ValueError("unsupported conversation source or window")
    if type(conversation["include_sidechains"]) is not bool or type(memory["auto_memory"]) is not bool:
        raise ValueError("evidence switches must be booleans")
    if type(conversation["max_chars_per_session"]) is not int or conversation["max_chars_per_session"] <= 0:
        raise ValueError("max_chars_per_session must be a positive integer")
    if not isinstance(memory["repo_files"], list):
        raise ValueError("memory.repo_files must be a list")
    for name in memory["repo_files"]:
        relative_path(name)

    after = meta.get("after", {})
    keys(after, {"writer", "cartographer"}, "after")
    output = {"runs_dir": "~/.contextops/sweeper-first/runs", "branch": "contextops/{run_id}", "open_pr": True}
    keys(meta.get("output", {}), set(output), "output")
    output.update(meta.get("output", {}))
    if type(output["open_pr"]) is not bool or output["branch"] != "contextops/{run_id}":
        raise ValueError("output requires boolean open_pr and branch contextops/{run_id}")
    output["runs_dir"] = str(Path(output["runs_dir"]).expanduser().resolve())
    workers = meta.get("workers", [])
    if not isinstance(workers, list) or not workers:
        raise ValueError("workers must be a nonempty list")
    for entry in workers:
        keys(entry, {"agent", "owns", "for_each", "run", "prefix"}, "worker")
        if bool(entry.get("owns")) == bool(entry.get("for_each")):
            raise ValueError("worker needs exactly one of owns or for_each")
        if entry.get("run") not in ("always", "when-relevant"):
            raise ValueError("worker.run must be always or when-relevant")
        if entry.get("owns"):
            knowledge_path(entry["owns"])
            if not re.fullmatch(r"[A-Z][A-Z0-9]*", entry.get("prefix", "")):
                raise ValueError("core worker requires a fact-ID prefix")
        elif entry["for_each"] != "products/*/":
            raise ValueError("only products/*/ is supported for product assignments")
        load_role(root, entry["agent"], model)
    return Config(
        root, "sweeper-first", model,
        markdown(inside(root, meta.get("shared_rules", "agents/shared-rules.md")))[1].strip(),
        notes.strip(), load_role(root, meta.get("sweeper", "agents/sweeper.md"), model),
        load_role(root, after.get("writer", "agents/writer.md"), model, writer=True),
        load_role(root, after["cartographer"], model) if after.get("cartographer") else None,
        workers, budget, conversation, memory, output,
    )
