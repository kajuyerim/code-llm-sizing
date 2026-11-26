"""Codex process, frozen-run and file-tool contracts. All model responses are synthetic."""

import asyncio
import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client, StdioServerParameters

import test_runtime
from contextops import gitutil
from contextops.cli import main
from contextops.config import load_config
from contextops.orchestrator import orchestrate
from contextops.run import load_run


# Installed as a temporary executable. Check the actual CLI argv, stdin and JSONL contract.
FAKE_CLI = r'''
import json, os, sys, uuid
from pathlib import Path

args = sys.argv[1:]
prompt = sys.stdin.read()
settings = dict(args[i+1].split("=", 1) for i, arg in enumerate(args) if arg == "-c")
assert args[:2] == ["exec", "--ignore-user-config"]
assert args[args.index("-s")+1] == "read-only"
assert "--ignore-rules" in args and "--strict-config" in args
assert json.loads(settings["forced_login_method"]) == "chatgpt"
assert {"memories", "shell_tool", "unified_exec", "plugins", "hooks", "multi_agent"} <= set(args)
assert not {"OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_THREAD_ID"} & set(os.environ)
assert Path(os.environ["CODEX_HOME"]).name == "fake-login"
scope = json.loads(json.loads(settings["mcp_servers.contextops_files.args"])[-1])
cwd, roots, tools, writer = scope
parent = args[-2] if args[-3] == "fork" else None
assert args[-1] == "-" and "resume" not in args
scenario = Path(__file__).with_name("scenario").read_text()
sid = str(uuid.uuid4())
run = Path.cwd().parent
with (run / "fake-calls").open("a") as log:
    print(json.dumps([sid, parent, args[args.index("-m")+1], tools]), file=log)
if parent and scenario == "failed-fork":
    sys.exit(17)
if parent and scenario == "parent-id":
    sid = parent
output = dict(records=[], findings=[], handoffs=[], unowned=[], unresolved=[], contradictions=[],
              coverage=dict(sessions_read=[], files_read=[], notes=""))
if writer:
    assert "Write" in tools and "Edit" in tools
    accepted = json.loads((run / "accepted.json").read_text())
    assert len(accepted) == 1
    path = Path(cwd) / accepted[0]["target"]
    path.write_text(path.read_text() + "\nTERM-999 Test definition\n")
    output = dict(applied=[], skipped=[], log_entry="")
elif "Validated records in order" in prompt:
    assert set(tools) == {"Read", "Glob", "Grep"}
    assert str(run / "pack") in roots
    output = dict(reason="No check needed for a terminology definition", candidate=None)
elif "Unowned findings, newest last:" in prompt:
    assert set(tools) == {"Read", "Glob", "Grep"}
    assert str(run/"unowned-backlog.jsonl") in roots
    output = dict(proposals=[])
else:
    assert set(tools) == {"Read", "Glob", "Grep"}
    assert set(roots) == {str(run/"app"), str(run/"kb")}
    assert (Path(cwd)/"diff/changes.patch").is_file()
    assert "[msg:message-1]" in (Path(cwd)/"conversation/chosen-session.md").read_text()
    if scenario == "handoff" and "Assignment: terminology-maintainer" in prompt:
        output["handoffs"] = [dict(to="core/naming-conventions.md", note="Check this name", evidence=[])]
        output["unowned"] = [dict(summary="Example", suggested_home="new group", evidence=[])]
    if "Assignment: terminology-maintainer" in prompt:
        output["records"].append(dict(op="ADD", fact_id=None, target="core/terminology.md",
            text="Test definition", scope="app:application", reason="Developer definition",
            evidence=[dict(kind="conversation", session="chosen-session", message="message-1",
                           path=None, quote=None, line=None)]))
        schema = json.loads(Path(args[args.index("--output-schema") + 1]).read_text())
        if "category" in schema["properties"]["records"]["items"]["properties"]:
            output["records"][0]["category"] = "domain"
print(json.dumps(dict(type="thread.started", thread_id=sid)))
print(json.dumps(dict(type="item.completed", item=dict(type="agent_message", text="Reviewing selected evidence"))))
if scenario != "incomplete":
    print(json.dumps(dict(type="turn.completed", usage=dict(input_tokens=123, output_tokens=9))))
Path(args[args.index("-o")+1]).write_text(json.dumps({} if scenario == "bad-schema" else output))
'''


class CodexTests(unittest.TestCase):
    commit = test_runtime.RuntimeTests.commit
    prepare = test_runtime.RuntimeTests.prepare

    def setUp(self):
        test_runtime.RuntimeTests.setUp(self)
        fake = self.root / "codex"
        fake.write_text(f"#!{sys.executable}\n" + FAKE_CLI)
        fake.chmod(0o700)
        self.scenario = self.root / "scenario"
        self.scenario.write_text("success")
        env = patch.dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ["PATH"],
                         CODEX_HOME=str(self.root / "fake-login"), OPENAI_API_KEY="example",
                         CODEX_API_KEY="example", CODEX_THREAD_ID="unrelated")
        env.start()
        self.addCleanup(env.stop)

    def sweep(self, strategy, *, expect_failure=False, model=None):
        exit_check = self.assertRaises(SystemExit) if expect_failure else contextlib.nullcontext()
        with contextlib.redirect_stdout(io.StringIO()), exit_check as error:
            main(["sweep", "--repo", str(self.app), "--kb", str(self.kb), "--base", self.base,
                  "--head", self.head, "--session", "chosen-session", "--backend", "codex",
                  "--strategy", strategy, "--cutoff", self.cutoff.isoformat(),
                  *(["--model", model] if model else [])])
        if expect_failure:
            self.assertEqual(error.exception.code, 1)
        states = list((self.root / "runs" / "codex" / strategy).glob("*/run.json"))
        return load_run(max(states, key=lambda p: p.stat().st_mtime_ns).parent)

    def test_profile_and_check_proposer_use_codex_and_publish_visible_messages(self):
        from contextops import frontmatter
        import yaml

        meta, body = frontmatter.read(self.kb / "init.md")
        meta["checks"]["automatic"] = True
        meta["knowledge_profiles"] = {"application": {"categories": [
            {"id": "domain", "name": "Domain", "description": "Keep domain definitions", "enabled": True},
        ]}}
        (self.kb / "init.md").write_text("---\n" + yaml.safe_dump(meta) + "---\n" + body)
        self.commit(self.kb)

        ctx = self.sweep("fresh-specialists", model="test-selected-model")
        review = json.loads((ctx.run_dir / "review.json").read_text())
        self.assertEqual(review["accepted"][0]["category"], "domain")
        proposal = json.loads((ctx.run_dir / "check-proposals" / "proposal.json").read_text())
        self.assertEqual(proposal["status"], "no-candidate")
        events = [json.loads(line) for line in (ctx.run_dir / "events.jsonl").read_text().splitlines()]
        self.assertTrue(any(item["kind"] == "agent_message" and item["agent"] == "check-proposer"
                            for item in events))
        self.assertEqual({item["model"] for item in events if item["kind"] == "agent_started"},
                         {"test-selected-model"})

    def test_both_strategies_via_cli(self):
        claude = self.prepare()
        for mode in ("fresh-specialists", "sweeper-first"):
            ctx = self.sweep(mode)
            self.assertEqual(ctx.backend, "codex")
            self.assertNotEqual(ctx.runs_dir, claude.runs_dir)
            self.assertEqual((ctx.kb_baseline, ctx.head_sha, ctx.base_sha, ctx.conversation_sha256),
                             (claude.kb_baseline, claude.head_sha, claude.base_sha, claude.conversation_sha256))
            metrics = json.loads((ctx.run_dir / "metrics.json").read_text())
            self.assertIsNone(metrics["total_cost_usd"])
            self.assertEqual(metrics["backend"], "codex")
            calls = [json.loads(line) for line in (ctx.run_dir / "fake-calls").read_text().splitlines()]
            self.assertEqual(len({sid for sid, *_ in calls}), len(calls))
            self.assertEqual({model for _, _, model, _ in calls}, {"gpt-6.1-terra"})
            if mode == "fresh-specialists":
                self.assertTrue(all(parent is None for _, parent, *_ in calls))
                self.assertEqual(len(calls), 6)  # five selected specialists and one writer
            else:
                parent_id = calls[0][0]
                self.assertEqual([parent for _, parent, *_ in calls], [None] + [parent_id]*5 + [None])
                lineage = json.loads((ctx.run_dir / "sweeper.json").read_text())
                self.assertTrue(lineage["independent_children"])
                for child in lineage["children"]:
                    self.assertEqual(child["raw"]["parent_session_id"], parent_id)
                    self.assertEqual(child["incremental"]["model_usage"],
                                     {"gpt-6.1-terra": {"input_tokens": 123, "output_tokens": 9}})
            accepted, = json.loads((ctx.run_dir / "accepted.json").read_text())
            self.assertIsNone(accepted["fact_id"])
            self.assertNotIn("quote", accepted["evidence"][0])
            self.assertIn("TERM-999", gitutil.git(self.kb, "show", f"{ctx.branch}:core/terminology.md"))
            self.assertEqual(gitutil.status(self.app), [])
            self.assertEqual(gitutil.rev_parse(self.app, "HEAD"), self.head)
            self.assertFalse(list(ctx.run_dir.glob("codex-call-*")))
        self.assertFalse((claude.runs_dir / "state.json").exists())

    def test_a_failure_is_reported_without_fresh_fallback(self):
        for scenario in ("failed-fork", "parent-id", "bad-schema", "incomplete"):
            with self.subTest(scenario=scenario):
                self.scenario.write_text(scenario)
                ctx = self.sweep("sweeper-first", expect_failure=True)
                calls = [json.loads(line) for line in (ctx.run_dir / "fake-calls").read_text().splitlines()]
                self.assertEqual(sum(parent is None for _, parent, *_ in calls), 1)
                lineage = json.loads((ctx.run_dir / "sweeper.json").read_text())
                if scenario in ("bad-schema", "incomplete"):
                    self.assertEqual(len(calls), 1)
                else:
                    self.assertFalse(lineage["independent_children"])
                    self.assertEqual(len(calls), 6)
                self.assertIn("Run incomplete", (ctx.run_dir / "completion.txt").read_text())
                self.assertFalse(gitutil.succeeds(self.kb, "show-ref", "--verify", "refs/heads/" + ctx.branch))

    def test_handoff_cartographer_and_writer_use_selected_model(self):
        settings = self.kb / "init.md"
        settings.write_text(settings.read_text().replace("cartographer: null", "cartographer: agents/cartographer.md")
                            .replace("gpt-6.1-terra", "custom-model"))
        self.commit(self.kb)
        self.scenario.write_text("handoff")
        ctx = self.sweep("fresh-specialists")
        agents = {a["label"]: a for a in json.loads((ctx.run_dir / "metrics.json").read_text())["agents"]}
        handoff = agents["conventions-maintainer:handoffs"]
        self.assertEqual(handoff["parent_session_id"], agents["conventions-maintainer"]["session_id"])
        self.assertNotEqual(handoff["session_id"], handoff["parent_session_id"])
        self.assertIsNone(agents["cartographer"]["parent_session_id"])
        self.assertIn("writer", agents)
        for agent in agents.values():
            self.assertEqual(agent["status"], "success")
            self.assertEqual(set(agent["model_usage"]), {"custom-model"})

    def test_configuration_and_prepared_selection(self):
        settings = self.kb / "init.md"
        settings.write_text(settings.read_text().replace("backend: claude", "backend: codex")
                            .replace("gpt-6.1-terra", "custom-model"))
        self.commit(self.kb)
        self.assertEqual(load_config(self.kb).default_model, "custom-model")
        self.assertEqual(self.prepare().backend, "codex")
        self.assertEqual(self.prepare(backend="claude").backend, "claude")
        settings.write_text(settings.read_text().replace("auth: subscription", "auth: api-key"))
        with self.assertRaisesRegex(ValueError, "ChatGPT"):
            load_config(self.kb)

    def test_refuses_in_repo_cli_storage_before_execution(self):
        ctx = self.prepare(backend="codex")
        with patch.dict(os.environ, CODEX_HOME=str(self.kb / ".codex")):
            with self.assertRaisesRegex(ValueError, "storage must be outside"):
                asyncio.run(orchestrate(ctx.run_dir))
        self.assertFalse((ctx.run_dir / "started").exists())
        self.assertFalse((self.kb / ".codex").exists())

    def test_installed_stdio_server_enforces_scope(self):
        async def exercise(writer):
            tools = ["Read", "Glob", "Grep", "Write", "Edit"]
            scope = json.dumps([str(self.kb), [str(self.app)], tools, writer])
            params = StdioServerParameters(command=sys.executable, args=["-I", "-m", "contextops.codex_files", scope])
            async with Client(params) as client:
                listed = await client.list_tools()
                self.assertEqual({t.name for t in listed.tools}, set(tools if writer else tools[:3]))
                for name, args in [("Read", {"path": str(self.app/"README.md")}),
                                   ("Grep", {"path": str(self.app/"README.md"), "pattern": "Firebase"}),
                                   ("Glob", {"path": str(self.app), "pattern": "*.md"})]:
                    self.assertFalse((await client.call_tool(name, args)).is_error)
                if writer:
                    self.assertFalse((await client.call_tool("Write", {"path": "core/new.md", "content": "old"})).is_error)
                    self.assertFalse((await client.call_tool("Edit", {"path": "core/new.md", "old_string": "old",
                                                                      "new_string": "new"})).is_error)
                    self.assertEqual((self.kb/"core/new.md").read_text(), "new")
                    for path in [str(self.app/"README.md"), "core/escape/README.md", "../sibling.md", "init.md"]:
                        self.assertTrue((await client.call_tool("Write", {"path": path, "content": "invalid"})).is_error)
                for path in [str(self.app/".git/config"), str(self.session_file)]:
                    self.assertTrue((await client.call_tool("Read", {"path": path})).is_error)
        (self.kb/"core/escape").symlink_to(self.app, target_is_directory=True)
        asyncio.run(exercise(False))
        asyncio.run(exercise(True))
        self.assertEqual(gitutil.status(self.app), [])
