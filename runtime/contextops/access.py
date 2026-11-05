"""SDK pre-tool checks for evidence reads and the writer's knowledge paths."""
from pathlib import Path


def writable(path: str) -> bool:
    p = Path(path)
    return (not p.is_absolute() and '..' not in p.parts and
            (path in ('index.md', 'log.md') or
             (len(p.parts) > 1 and p.parts[0] in ('core', 'tools') and p.suffix == '.md')))


def sensitive(path: Path) -> bool:
    return any(part in {'.git', '.claude', '.codex', '.aws'} for part in path.parts) or (
        path.name.startswith('.env') or path.name in {'auth.json', 'credentials.json', '.credentials.json'}
        or path.suffix in {'.pem', '.key'})


def file_guard(cwd: Path, roots: list[Path], writer: bool):
    allowed = [p.resolve() for p in [cwd, *roots]]

    async def guard(data, tool_use_id, context):
        name, args = data['tool_name'], data.get('tool_input', {})
        raw = args.get('file_path', args.get('path', str(cwd)))
        candidate = Path(raw)
        lexical = candidate if candidate.is_absolute() else cwd / candidate
        resolved = lexical.resolve()
        ok = (not sensitive(lexical) and not sensitive(resolved)
              and any(resolved.is_relative_to(root) for root in allowed))
        if name == 'Glob':
            pattern = Path(args.get('pattern', ''))
            ok = ok and not pattern.is_absolute() and '..' not in pattern.parts
        if name == 'Grep' and not resolved.is_file():
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                    'permissionDecision': 'deny',
                    'permissionDecisionReason': 'Use Glob to discover paths, then Grep a specific permitted file; recursive content searches can include credential files'}}
        if name in ('Edit', 'Write'):
            ok = ok and writer and resolved.is_relative_to(cwd.resolve())
            if ok:
                ok = writable(resolved.relative_to(cwd.resolve()).as_posix())
        if not ok:
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                    'permissionDecision': 'deny', 'permissionDecisionReason': 'Outside permitted evidence or knowledge paths'}}
        return {}
    return guard
