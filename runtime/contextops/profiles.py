"""Repository profile discovery and policy rendering."""

import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from contextops import frontmatter, gitutil, transcripts
from contextops.access import sensitive
from contextops.agents import READ_ONLY_TOOLS, load_agent, run_agent
from contextops.config import load_config

SCAN_SCHEMA = {
    "type": "object",
    "required": ["categories"],
    "properties": {
        "categories": {"type": "array", "items": {
            "type": "object",
            "required": ["id", "name", "description", "reason", "path", "recommended"],
            "properties": {
                **{key: {"type": "string"} for key in ("id", "name", "description", "reason", "path")},
                "recommended": {"type": "boolean"},
            },
        }},
    },
}


def apply_profile(profile: dict | None) -> str:
    if profile is None:
        return ""
    return (
        "\n\n# Active collection profile\n"
        "For every proposed knowledge change, include its category ID from this profile. "
        "Propose only enabled categories. Leave uncertain classifications for human review. "
        "The category is separate from the destination and scope.\n"
        + json.dumps(profile, ensure_ascii=False)
    )


def validate_profile(items: list[dict]) -> dict:
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError("Provide a list of at most 100 categories")
    categories = []
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each category must be an object")
        key, name, description = (item.get(field) for field in ("id", "name", "description"))
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", key) or key in ids:
            raise ValueError("Category IDs must be unique lowercase identifiers")
        if not all(isinstance(value, str) and value.strip() and len(value) <= 1000 for value in (name, description)):
            raise ValueError("Each category needs a short name and description")
        if not isinstance(item.get("enabled"), bool):
            raise ValueError("Each category must be enabled or disabled")
        ids.add(key)
        categories.append({"id": key, "name": name.strip(), "description": description.strip(),
                           "enabled": item["enabled"]})
    return {"categories": categories}


async def discover(app: Path, kb: Path, backend: str, model: str | None,
                   sessions: list[str] | None = None) -> dict:
    config = load_config(kb, backend or None)
    if backend == "claude" and config.auth == "api-key":
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("Configure Claude API authentication before scanning")
    role = (kb / "agents" / "profile-discovery.md").resolve()
    if not role.is_relative_to(kb.resolve()) or not role.is_file():
        raise ValueError("The knowledge checkout needs agents/profile-discovery.md")
    spec = replace(load_agent(role, config.default_model, config.backend, model), tools=READ_ONLY_TOOLS)
    head = gitutil.rev_parse(app, "HEAD")
    evidence = ""
    if sessions:
        selected = transcripts.load_sessions(app, None, datetime.now(timezone.utc), selected=sessions)
        entries = [{"session": session.session_id, "role": msg.role, "text": msg.text[:1500]}
                   for session in selected for msg in session.messages[-6:]]
        evidence = "\nOptional development discussion, supplied as evidence:\n" + json.dumps(entries[:18])
    with TemporaryDirectory(prefix="contextops-profile-") as temporary:
        run_dir = Path(temporary).resolve()
        snapshot = run_dir / "source"
        gitutil.add_worktree(app, snapshot, head)
        try:
            result = await run_agent(
                spec, label="profile-discovery", system=spec.prompt,
                prompt=f"Inspect this committed application snapshot at {head}. Suggest a knowledge profile." + evidence,
                schema=SCAN_SCHEMA, cwd=snapshot, dirs=[], run_dir=run_dir,
                budget_usd=config.budget.per_agent_usd, max_turns=config.budget.max_turns,
                subscription=config.auth == "subscription",
            )
            if result.output is None:
                raise ValueError("Category scan failed. Check the selected provider and model.")
            candidates = []
            for item in result.output["categories"]:
                path = Path(item["path"])
                if (not path.is_absolute() and ".." not in path.parts and not sensitive(path)
                        and (snapshot / path).resolve().is_relative_to(snapshot)
                        and (snapshot / path).is_file()):
                    candidates.append({**item, "enabled": item["recommended"]})
            validate_profile(candidates)
            return {"revision": head, "categories": candidates}
        finally:
            gitutil.remove_worktree(app, snapshot)


def save(kb: Path, scope: str, items: list[dict]) -> None:
    path = kb / "init.md"
    import yaml
    profile = validate_profile(items)
    meta, body = frontmatter.read(path)
    meta.setdefault("knowledge_profiles", {})[scope] = profile
    path.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
