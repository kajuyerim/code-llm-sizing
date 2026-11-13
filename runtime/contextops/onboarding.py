"""Prepare empty knowledge on a new local branch without running maintenance."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from contextops import frontmatter, gitutil
from contextops.config import load_config


CORE = {
    "terminology.md": ("Terminology", "TERM", "| ID | Term | Meaning | Scope | Evidence |"),
    "tech-stack-standards.md": (
        "Tech Stack Standards", "STACK", "| ID | Decision or constraint | Scope | Rationale | Evidence |"
    ),
    "naming-conventions.md": (
        "Naming Conventions", "NAME", "| ID | Convention | Scope | Evidence |"
    ),
    "pitfalls.md": (
        "Pitfalls", "PIT", "| ID | Trigger | What goes wrong | Do instead | Scope | Evidence |"
    ),
}


def initialize_knowledge(kb: Path, branch: str) -> list[str]:
    """Reset knowledge content on a new branch; leave edits uncommitted for setup."""
    kb = gitutil.repo_root(kb.expanduser()).resolve()
    if gitutil.status(kb):
        raise ValueError("Knowledge checkout must be clean before initialization")
    if (branch.startswith("-")
            or not gitutil.succeeds(kb, "check-ref-format", "--branch", branch)
            or not gitutil.succeeds(kb, "check-ref-format", f"refs/heads/{branch}")):
        raise ValueError("Choose a valid new knowledge branch name")
    if gitutil.succeeds(kb, "show-ref", "--verify", f"refs/heads/{branch}"):
        raise ValueError("Knowledge branch already exists; reuse it without initialization")
    load_config(kb)
    baseline = gitutil.rev_parse(kb, "HEAD")

    # Validate every target before switching branches or modifying a file.
    paths = [kb / "index.md", kb / "log.md"]
    for area in ("core", "tools"):
        root = kb / area
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"Initialization requires a regular {area}/ directory")
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError("Knowledge templates cannot replace symlinks")
            if not path.is_dir():
                paths.append(path)
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.suffix != ".md":
            raise ValueError("Initialization requires regular Markdown knowledge files")
        if not gitutil.file_exists(kb, baseline, path.relative_to(kb).as_posix()):
            raise ValueError("Initialization cannot replace untracked or ignored knowledge files")
    if any(not (kb / "core" / name).is_file() for name in CORE):
        raise ValueError("Initialization requires the four core knowledge documents")

    bodies = {}
    for name, (title, prefix, table) in CORE.items():
        separator = "| " + " | ".join("---" for _ in range(table.count("|") - 1)) + " |"
        bodies[kb / "core" / name] = (
            f"# {title}\n\n"
            "Status: empty template. No application or company facts have been admitted.\n\n"
            f"Use {prefix} IDs for evidence-backed entries, with explicit scope. "
            "Generated entries require human review. Implementation observations do not "
            "establish company policy.\n\n"
            f"{table}\n{separator}\n\n"
            "Follow the [core maintenance guide](../maintenance/core.md).\n"
        )
    tools = sorted(path for path in (kb / "tools").iterdir() if path.is_dir())
    for tool in tools:
        entry = tool / "README.md"
        if entry not in paths:
            raise ValueError("Each tool folder needs a tracked README.md with relevance hints")
        bodies[entry] = (
            f"# {tool.name} Knowledge\n\n"
            "Status: empty template. This folder does not establish application usage "
            "or a mandatory technology choice.\n\n"
            "Record supported findings with stable IDs, application or tool scope, "
            "and revision-specific source or conversation evidence. Generated entries "
            "require human review.\n\n"
            "Follow the [tool maintenance guide](../../maintenance/tools.md).\n"
        )
    links = ["# Knowledge Index", "", "## Core", ""]
    links += [f"- [{title}]({quote('core/' + name)})" for name, (title, _, _) in CORE.items()]
    links += ["", "## Tools", ""]
    links += [f"- [{tool.name}]({quote('tools/' + tool.name + '/README.md')})" for tool in tools]
    links += ["", "## Using this bundle", ""]
    for label, target in (
        ("Setup", "setup.md"), ("Repository instructions", "AGENTS.md"),
        ("Run configuration", "init.md"), ("Core maintenance", "maintenance/core.md"),
        ("Tool maintenance", "maintenance/tools.md"), ("Agents", "agents/README.md"),
        ("Runtime", "runtime/README.md"), ("Setup skill", "skills/setup-shared-knowledge/SKILL.md"),
        ("Historical walkthrough", "docs/walkthrough/README.md"),
        ("Historical evaluation", "docs/evaluation.md"), ("Provenance", "docs/provenance.md"),
        ("Knowledge change history", "log.md"),
    ):
        if (kb / target).is_file():
            links.append(f"- [{label}]({target})")
    bodies[kb / "index.md"] = "\n".join(links) + "\n"
    bodies[kb / "log.md"] = (
        "# Knowledge Change History\n\n"
        f"## {datetime.now(timezone.utc):%Y-%m-%d}: Initialize empty knowledge\n\n"
        f"- Starting repository revision: `{baseline}`.\n"
        "- Prepared empty templates on a new local branch. No model calls or learned facts.\n"
        "- Configure and commit this baseline before maintenance.\n"
    )
    # Retain metadata (notably tool relevance hints) byte for byte.
    replacements = {}
    for path, body in bodies.items():
        original = path.read_text(encoding="utf-8")
        _, old_body = frontmatter.split(original)
        replacements[path] = original[:len(original) - len(old_body)] + body

    gitutil.git(kb, "-c", "core.hooksPath=/dev/null", "switch", "-c", branch)
    for path in paths:
        if path in replacements:
            path.write_text(replacements[path], encoding="utf-8")
        else:
            path.unlink()  # Additional learned documents survive on the original branch.
    return sorted(path.relative_to(kb).as_posix() for path in paths)
