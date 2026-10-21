"""Build the immutable raw pack before any agent receives access."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from contextops import git, transcripts
from contextops.config import Config
from contextops.files import dump, inside, load
from contextops.runs import Run


def build(run: Run, config: Config) -> dict:
    if run.pack.exists():
        raise ValueError("refusing to overwrite an existing evidence pack")
    diff_dir = run.pack / "diff"
    diff_dir.mkdir(parents=True)
    names = git.changed(run.application, run.base, run.head)
    (diff_dir / "changes.patch").write_text(git.diff(run.application, run.base, run.head), encoding="utf-8")
    dump(diff_dir / "files.json", names)
    log_range = run.head if run.base == git.EMPTY_TREE else f"{run.base}..{run.head}"
    (diff_dir / "commits.txt").write_text(git.call(run.application, "log", "--format=%H %aI %an%n%s%n%b", log_range, "--"), encoding="utf-8")
    dump(diff_dir / "sections.json", {name: git.diff(run.application, run.base, run.head, name) for name in names})
    sessions, selection = transcripts.read(run.application, run.since, run.cutoff, config.conversation)
    conversation = run.pack / "conversation"
    conversation.mkdir()
    for session in sessions:
        blocks = [f"# Session {session['session']}", f"Older messages omitted: {session['dropped']}", ""]
        for message in session["messages"]:
            blocks.append(f"[msg:{message['message']}] {message['role']} @ {message['timestamp']}\n{message['text']}\n")
        (conversation / f"{session['session']}.md").write_text("\n".join(blocks), encoding="utf-8")
    dump(conversation / "messages.json", sessions)
    memory, missing_memory, notes = [], [], list(run.notes)
    captured = datetime.now(timezone.utc).isoformat()
    for name in config.memory["repo_files"]:
        try:
            source = inside(run.app_snapshot, name)
            if source.is_file():
                _copy(source, run.pack, f"memory/repo/{name}", memory)
            else:
                missing_memory.append(name)
        except ValueError as exc:
            notes.append(str(exc))
    if config.memory["auto_memory"]:
        for directory in transcripts.project_directories(run.application):
            auto = directory / "memory"
            if auto.is_symlink() or not auto.is_dir():
                continue
            for source in sorted(auto.rglob("*.md")):
                relative = source.relative_to(auto).as_posix()
                try:
                    source = inside(auto, relative)
                    _copy(source, run.pack, f"memory/auto/{directory.name}/{relative}", memory)
                except ValueError as exc:
                    notes.append(str(exc))
    manifest = {
        **run.record(), "application_snapshot": str(run.app_snapshot), "knowledge_snapshot": str(run.kb_snapshot),
        "memory_capture_time": captured, "memory_cutoff_aligned": False,
        "memory_note": "Repository memory is from head; auto memory is a mutable development artifact copied at collection time, not historical conversation-cutoff evidence.",
        "changed_files": names, "sessions": [s["session"] for s in sessions],
        "conversation_selection": selection, "memory_files": memory,
        "optional_memory_files_absent_at_head": missing_memory, "notes": notes,
        "complete": bool(sessions),
    }
    if not sessions:
        notes.append("Missing retained developer-agent conversation: no model calls or publication are permitted.")
    hashes = {}
    for path in sorted(run.pack.rglob("*")):
        if path.is_file():
            hashes[path.relative_to(run.pack).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["sha256"] = hashes
    dump(run.pack / "manifest.json", manifest)
    return manifest


def _copy(source: Path, pack: Path, relative: str, records: list[dict]) -> None:
    target = inside(pack, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = source.read_bytes()
    target.write_bytes(content)
    records.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest(),
                    "captured_at": datetime.now(timezone.utc).isoformat()})


def messages(pack: Path) -> dict[tuple[str, str], dict]:
    return {(m["session"], m["message"]): m
            for session in load(pack / "conversation/messages.json") for m in session["messages"]}


def check_hashes(run: Run, manifest: dict) -> None:
    for name, digest in manifest["sha256"].items():
        path = inside(run.pack, name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"evidence changed during the run: {name}")
