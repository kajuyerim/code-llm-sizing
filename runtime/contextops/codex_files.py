"""Scoped stdio tools for Codex. The Claude hook and this server share the path guard."""

import json
import re
import sys
from itertools import islice
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from contextops.access import file_guard, sensitive, writable


def file_server(cwd: Path, dirs: list[Path], tools: list[str], writer: bool) -> MCPServer:
    server = MCPServer("contextops_files", log_level="WARNING")
    guard = file_guard(cwd, dirs, writer)

    async def checked(name: str, path: str, **args) -> Path:
        candidate = cwd / path
        # Both the supplied writer path and its resolved destination must be in scope.
        if name in {"Edit", "Write"} and (not candidate.is_relative_to(cwd)
                                          or not writable(candidate.relative_to(cwd).as_posix())):
            raise ToolError("Outside knowledge output scope")
        decision = await guard({"tool_name": name, "tool_input": {"path": path, **args}}, None, None)
        if decision:
            raise ToolError("Outside permitted evidence or knowledge paths")
        return candidate.resolve()

    async def Read(path: str, offset: int = 1, limit: int = 500) -> str:
        """Read numbered lines of a file, starting at a one-based offset."""
        target = await checked("Read", path)
        start = max(1, offset)
        count = min(2000, max(1, limit))
        with target.open(encoding="utf-8", errors="replace") as stream:
            return "".join(f"{i}: {line}" for i, line in
                           enumerate(islice(stream, start - 1, start - 1 + count), start))

    async def Glob(pattern: str, path: str = ".") -> list[str]:
        """Find matching files under an evidence directory. Returns up to 1000 paths."""
        root = await checked("Glob", path, pattern=pattern)
        matches = []
        for target in root.glob(pattern):
            if target.is_file() and not sensitive(target):
                try:
                    await checked("Read", str(target))
                except ToolError:
                    continue
                matches.append(str(target))
                if len(matches) == 1000:
                    break
        return sorted(matches)

    async def Grep(path: str, pattern: str) -> list[str]:
        """Return up to 200 numbered lines matching a regular expression in a single file."""
        target = await checked("Grep", path)
        regex = re.compile(pattern)
        with target.open(encoding="utf-8", errors="replace") as stream:
            return list(islice((f"{i}: {line.rstrip()}" for i, line in enumerate(stream, 1)
                                if regex.search(line)), 200))

    async def Write(path: str, content: str) -> str:
        """Create or replace a scoped Markdown document with its complete UTF-8 content."""
        target = await checked("Write", path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return "Written"

    async def Edit(path: str, old_string: str, new_string: str) -> str:
        """Replace one exact, unique occurrence in a scoped knowledge document."""
        target = await checked("Edit", path)
        content = target.read_text(encoding="utf-8")
        if not old_string or content.count(old_string) != 1:
            raise ToolError("old_string must occur exactly once")
        target.write_text(content.replace(old_string, new_string, 1), encoding="utf-8")
        return "Edited"

    functions = [Read, Glob, Grep]
    if writer:
        functions.extend([Write, Edit])
    for function in functions:
        if function.__name__ in tools:
            server.tool()(function)
    return server


if __name__ == "__main__":
    cwd, roots, tools, writer = json.loads(sys.argv[1])
    file_server(Path(cwd), [Path(p) for p in roots], tools, writer).run()
