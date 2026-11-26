"""Shared check-proposal workflow with deterministic replies and disposable repos."""

import asyncio
import contextlib
import io
import json
import sys
import unittest

import yaml
from unittest.mock import AsyncMock, patch

import test_runtime
from contextops import checks, frontmatter, gitutil
from contextops.agents import AgentRun
from contextops.cli import main
from contextops.orchestrator import orchestrate
from contextops.review import Review
from contextops.writer import Publication

TIMEOUT_RULE = """import ast


def violations(source):
    return [
        node.lineno for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'client'
        and node.func.attr == 'get'
        and all(keyword.arg != 'timeout' for keyword in node.keywords)
    ]
"""

TIMEOUT_CHECK = """from lint_timeout import violations

assert violations("client.get(url)") == [1]
assert violations("client.get(url, timeout=5)") == []
assert violations("other.get(url)") == []
"""

RECORD = {
    "op": "ADD", "scope": "company", "fact_id": "PIT-001",
    "text": "Pass an explicit timeout to the outbound HTTP client.",
    "evidence": [{"kind": "conversation", "session": "chosen-session", "message": "message-1"}],
}


def new_file(path, content):
    lines = content.splitlines()
    return (
        f"diff --git a/{path} b/{path}\nnew file mode 100644\n"
        f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n"
        + "".join("+" + line + "\n" for line in lines)
    )


class CheckTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    commit = test_runtime.RuntimeTests.commit
    prepare = test_runtime.RuntimeTests.prepare

    def finish(self, *, automatic=False, strategy="fresh-specialists", has_record=True, candidate=None):
        meta, body = frontmatter.read(self.kb / "init.md")
        meta["checks"]["automatic"] = automatic
        (self.kb / "init.md").write_text("---\n" + yaml.safe_dump(meta) + "---\n" + body)
        if gitutil.status(self.kb):
            self.commit(self.kb)
        ctx = self.prepare(strategy=strategy)
        candidate = candidate if candidate is not None else {
            "record": 1, "kind": "lint",
            "patch": new_file("lint_timeout.py", TIMEOUT_RULE) + new_file("check_timeout.py", TIMEOUT_CHECK),
            "passing": "client.get(url, timeout=5)", "failing": "client.get(url)",
            "verification": "python check_timeout.py",
        }
        self.proposer = AsyncMock(return_value=AgentRun(
            "check-proposer", status="success", cost_usd=.1,
            output={"candidate": candidate, "reason": "A direct call can be checked syntactically"},
        ))
        mock_proposer = patch.object(checks, "run_agent", self.proposer)
        mock_proposer.start()
        self.addCleanup(mock_proposer.stop)
        note = Review(accepted=[RECORD] if has_record else [])
        with (
            patch.dict("contextops.orchestrator.STRATEGIES", {strategy: AsyncMock(return_value=[])}),
            patch("contextops.orchestrator.review_results", return_value=note),
            patch("contextops.orchestrator.write_changes", new_callable=AsyncMock) as writer,
        ):
            writer.return_value = Publication(branch=ctx.branch), None
            asyncio.run(orchestrate(ctx.run_dir))
        return ctx

    def read_proposal(self, ctx):
        return json.loads((ctx.run_dir / checks.OUTPUT / "proposal.json").read_text())

    def test_timeout_manual_verify_and_explicit_apply(self):
        ctx = self.finish()
        self.proposer.assert_not_awaited()
        self.assertFalse((ctx.run_dir / checks.OUTPUT).exists())
        other = ctx.run_dir / "unreviewed"
        other.mkdir()
        with self.assertRaises(FileNotFoundError):
            asyncio.run(checks.propose_manually(other))
        with contextlib.redirect_stdout(io.StringIO()):
            main(["checks", "propose", str(ctx.run_dir)])
        proposal = self.read_proposal(ctx)
        self.assertEqual(proposal["status"], "pending-review")
        self.assertEqual(proposal["record"], RECORD)
        self.assertIsNone(self.proposer.call_args.kwargs.get("resume"))
        self.assertEqual(gitutil.status(self.app), [])
        digest = proposal["patch_sha256"]
        main(["checks", "verify", str(ctx.run_dir), digest, "--", sys.executable, "check_timeout.py"])
        verification = json.loads((ctx.run_dir / checks.OUTPUT / "verification.json").read_text())
        self.assertEqual((verification["patch_sha256"], verification["exit_code"]), (digest, 0))
        self.assertEqual(gitutil.status(self.app), [])
        asyncio.run(checks.propose_manually(ctx.run_dir))
        self.proposer.assert_awaited_once()
        with self.assertRaisesRegex(ValueError, "digest"):
            checks.apply(ctx.run_dir, "wrong")
        patch_file = ctx.run_dir / checks.OUTPUT / "check.patch"
        original_patch = patch_file.read_bytes()
        patch_file.write_bytes(original_patch + b"\n")
        with self.assertRaisesRegex(ValueError, "digest"):
            checks.apply(ctx.run_dir, digest)
        patch_file.write_bytes(original_patch)
        (self.app / "dirty.txt").write_text("keep me")
        with self.assertRaisesRegex(ValueError, "clean"):
            checks.apply(ctx.run_dir, digest)
        (self.app / "dirty.txt").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            main(["checks", "apply", str(ctx.run_dir), digest])
        self.assertEqual(set(gitutil.status(self.app)), {("A", "lint_timeout.py"), ("A", "check_timeout.py")})
        self.assertEqual(gitutil.rev_parse(self.app, "HEAD"), ctx.head_sha)

    def test_automatic_path_is_shared_between_strategies(self):
        for strategy in ("fresh-specialists", "sweeper-first"):
            with self.subTest(strategy=strategy):
                ctx = self.finish(automatic=True, strategy=strategy)
                self.proposer.assert_awaited_once()
                self.assertIsNone(self.proposer.call_args.kwargs.get("resume"))
                self.assertEqual(self.read_proposal(ctx)["status"], "pending-review")
                self.assertIn("Application check proposal", (ctx.run_dir / "report.md").read_text())
                metrics = json.loads((ctx.run_dir / "metrics.json").read_text())
                self.assertEqual(metrics["agents"][-1]["label"], "check-proposer")
                self.assertEqual(gitutil.status(self.app), [])

    def test_empty_review_does_not_call_the_agent(self):
        ctx = self.finish(automatic=True, has_record=False)
        self.proposer.assert_not_awaited()
        self.assertEqual(self.read_proposal(ctx)["status"], "no-candidate")

    def test_rejects_invalid_proposal_and_preserves_application(self):
        candidate = {
            "record": 1, "kind": "lint", "patch": new_file(".env", "TEST_SETTING=abc"),
            "passing": "accepted", "failing": "rejected", "verification": "check",
        }
        ctx = self.finish(automatic=True, candidate=candidate)
        self.assertEqual(self.read_proposal(ctx)["status"], "failed")
        self.assertFalse((ctx.run_dir / checks.OUTPUT / "check.patch").exists())
        self.assertEqual(gitutil.status(self.app), [])

    def test_revision_change_requires_new_review(self):
        ctx = self.finish(automatic=True)
        (self.app / "new.txt").write_text("next change")
        self.commit(self.app)
        with self.assertRaisesRegex(ValueError, "exact reviewed revision"):
            checks.apply(ctx.run_dir, self.read_proposal(ctx)["patch_sha256"])
        self.assertEqual(gitutil.status(self.app), [])
