"""Test the browser-facing runtime without external inference."""

import asyncio
import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import test_runtime
from contextops import gitutil, profiles
from contextops.agents import AgentRun, load_agent
from contextops.events import emit, message
from contextops.review import Review, _file
from contextops.web_console import Console

CATEGORIES = [
    {"id": "domain", "name": "Domain rules", "description": "Compatibility agreements", "enabled": True},
    {"id": "ui", "name": "UI detail", "description": "Transient layout", "enabled": False},
]


class ConsoleTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    commit = test_runtime.RuntimeTests.commit
    prepare = test_runtime.RuntimeTests.prepare

    def connect(self):
        app_hook_manager = gitutil.config_get(self.app, "core.hooksPath")
        console = Console(self.root / "ui")
        key = console.connect({"app": str(self.app), "kb": str(self.kb), "name": "Example"})["id"]
        self.assertEqual(gitutil.config_get(self.app, "core.hooksPath"), app_hook_manager)
        self.assertEqual(gitutil.config_get(self.app, "contextops.kb"), str(self.kb))
        return console, key

    def test_init_profile_and_run_freeze(self):
        console, key = self.connect()
        self.assertEqual(Console(console.home).load_project(key)["name"], "Example")
        console.action("init", {"project": key, "branch": "knowledge/console", "scope": "repository"})
        console.action("profile", {"project": key, "categories": CATEGORIES})
        diff = console.load_project(key)["diff"]
        with self.assertRaisesRegex(ValueError, "diff changed"):
            console.action("commit", {"project": key, "preview": "old"})
        console.action("commit", {"project": key, "preview": diff})
        with patch.object(console, "launch") as launch:
            result = console.action("run", {"project": key, "head": self.head, "base": self.base,
                                            "backend": "codex", "model": "explicit-model",
                                            "strategy": "fresh-specialists", "sessions": ["chosen-session"]})
        ctx = launch.call_args.args[0]
        self.assertEqual(ctx.backend, "codex")
        self.assertEqual(ctx.model, "explicit-model")
        self.assertEqual(ctx.profile, {"categories": CATEGORIES})
        self.assertTrue(ctx.local_only)
        self.assertEqual(result["run"], ctx.run_id)
        self.assertEqual(console.runs(key)[ctx.run_id]["status"], "queued")

    def test_branch_picker_preserves_checkout_and_limits_commit_ranges(self):
        console, key = self.connect()
        gitutil.git(self.app, "branch", "older", self.base)
        selected = console.load_project(key)
        self.assertEqual(selected["branch"], "refs/heads/main")
        self.assertIn({"ref": "refs/heads/older", "label": "older"}, selected["branches"])
        rows = console.project_commits(key, "refs/heads/older")["commits"]
        self.assertEqual([row.split("\t")[0] for row in rows], [self.base])
        with self.assertRaisesRegex(ValueError, "selected branch"):
            console.action("run", {"project": key, "branch": "refs/heads/older",
                                   "head": self.head, "base": self.base})
        self.assertEqual(gitutil.rev_parse(self.app, "HEAD"), self.head)
        gitutil.git(self.app, "-c", "core.hooksPath=/dev/null", "switch", "--detach")
        self.assertEqual(console.load_project(key)["branch"], "HEAD")

    def test_profile_review_gate(self):
        ctx = replace(self.prepare(), profile={"categories": CATEGORIES})
        record = {"op": "ADD", "target": "core/pitfalls.md", "scope": "company",
                  "text": "Keep compatibility", "fact_id": "PIT-001", "reason": "Team decision",
                  "evidence": [{"kind": "diff", "path": "README.md"}]}
        review = Review()
        with patch("contextops.review._problem", return_value=None):
            for category in ("domain", "ui", None):
                _file({**record, "category": category}, "core/pitfalls.md", ctx, None, review)
        self.assertEqual([entry["category"] for entry in review.accepted], ["domain"])
        self.assertEqual([entry["category"] for entry in review.rejected], ["ui"])
        self.assertEqual(len(review.deferred), 1)

    def test_scan_records_distinct_suggestions_and_provider(self):
        rows = [{"id": "domain", "name": "Domain rules", "description": "Compatibility agreements",
                 "reason": "Existing behavior", "path": "README.md", "recommended": True}]
        runner = AsyncMock(return_value=AgentRun("profile-discovery", status="success", output={"categories": rows}))
        with patch("contextops.profiles.run_agent", runner):
            result = asyncio.run(profiles.discover(self.app, self.kb, "codex", "custom-model", ["chosen-session"]))
        self.assertEqual(result["revision"], self.head)
        self.assertEqual(result["categories"][0]["enabled"], True)
        spec = runner.call_args.args[0]
        self.assertEqual((spec.backend, spec.model), ("codex", "custom-model"))
        self.assertIn("chosen-session", runner.call_args.kwargs["prompt"])

    def test_events_distinguish_status_and_redact_values(self):
        ctx = self.prepare()
        emit(ctx.run_dir, "agent_started", agent="sweeper")
        key = "password"
        message(ctx.run_dir, "sweeper", f"{key}=temporary-value-for-testing")
        emit(ctx.run_dir, "run_finished", status="complete")
        events = Console.read_events(ctx.run_dir)
        self.assertEqual([item["kind"] for item in events], ["agent_started", "agent_message", "run_finished"])
        self.assertEqual(events[1]["text"], "[redacted]")
        self.assertNotIn("temporary-value", (ctx.run_dir / "events.jsonl").read_text())

    def test_model_override_uses_explicit_selection(self):
        role = self.kb / "agents" / "sweeper.md"
        self.assertEqual(load_agent(role, "default", "claude", "explicit").model, "explicit")
        self.assertEqual(load_agent(role, "default", "codex", "explicit").model, "explicit")
