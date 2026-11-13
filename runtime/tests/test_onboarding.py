"""First-run behavior with disposable Git repositories and fake inference."""
from __future__ import annotations

import contextlib
import io
import re
import shlex
import subprocess
import unittest
from unittest.mock import patch
from urllib.parse import unquote

import test_runtime
from contextops import frontmatter, gitutil
from contextops.agents import AgentRun
from contextops.cli import main
from contextops.config import load_config
from contextops.onboarding import initialize_knowledge
from contextops.run import create_run, load_run


class FirstRunTests(unittest.TestCase):
    # Reuse the existing external source/history fixture, not its test cases.
    setUp = test_runtime.RuntimeTests.setUp
    commit = test_runtime.RuntimeTests.commit

    def command(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(list(args))
        return output.getvalue()

    def initialize(self):
        self.command('init', '--kb', str(self.kb), '--branch', 'knowledge/test-app')
        self.commit(self.kb)

    def sweep(self, *extra):
        return self.command('sweep', '--kb', str(self.kb), '--repo', str(self.app),
                            '--base', self.base, '--head', self.head,
                            '--strategy', 'sweeper-first', '--session', 'chosen-session',
                            '--cutoff', self.cutoff.isoformat(), *extra)

    def specialist(self, op='ADD', cost=0):
        async def respond(spec, **kw):
            records = []
            if kw['label'] == 'terminology-maintainer' and op:
                records = [{'op': op, 'fact_id': 'TERM-001', 'target': 'core/terminology.md',
                            'text': 'Test term: an application-scoped definition.', 'scope': 'app:test',
                            'reason': 'Developer definition',
                            'evidence': [{'kind': 'conversation', 'session': 'chosen-session',
                                          'message': 'message-1'}]}]
            return AgentRun(kw['label'], status='success', session_id=kw['label'],
                            cost_usd=cost if records else 0,
                            output={'records': records, 'handoffs': [], 'unowned': [],
                                    'findings': [], 'coverage': {'files_read': [],
                                    'sessions_read': ['chosen-session'], 'notes': ''}})
        return respond

    @staticmethod
    async def writer(spec, **kw):
        path = kw['cwd'] / 'core/terminology.md'
        path.write_text(path.read_text() + '\nTERM-001: Test definition with message-1 evidence.\n')
        # Deliberately omit the claim: completion must inspect Git, not this list.
        return AgentRun('writer', status='success', output={'applied': [], 'skipped': [], 'log_entry': ''})

    def test_initialization_preserves_original_and_operational_files(self):
        (self.kb / 'core' / 'old-facts.md').write_text('# Old application facts\n')
        (self.kb / 'tools/firebase/learned.md').write_text('# Old tool findings\n')
        (self.kb / 'docs').mkdir()
        (self.kb / 'docs/history.md').write_text('# Historical evaluation\n')
        self.commit(self.kb)
        original = gitutil.rev_parse(self.kb, 'HEAD')
        old_term = (self.kb / 'core/terminology.md').read_text()
        operational = {p.relative_to(self.kb): p.read_bytes() for p in self.kb.rglob('*.md')
                       if p.parts[-2] in ('agents', 'maintenance', 'docs') or p.name == 'init.md'}
        old_meta = frontmatter.read(self.kb / 'tools/firebase/README.md')[0]
        self.command('init', '--kb', str(self.kb), '--branch', 'knowledge/test-app')
        self.assertEqual(gitutil.git(self.kb, 'branch', '--show-current'), 'knowledge/test-app')
        self.assertEqual(gitutil.rev_parse(self.kb, 'main'), original)
        self.assertEqual(gitutil.git(self.kb, 'show', 'main:core/terminology.md'), old_term.rstrip())
        self.assertNotIn('TERM-001', (self.kb / 'core/terminology.md').read_text())
        self.assertFalse((self.kb / 'core/old-facts.md').exists())
        self.assertFalse((self.kb / 'tools/firebase/learned.md').exists())
        self.assertEqual(frontmatter.read(self.kb / 'tools/firebase/README.md')[0], old_meta)
        for path, raw in operational.items():
            self.assertEqual((self.kb / path).read_bytes(), raw)
        self.assertEqual(gitutil.git(self.kb, 'diff', '--cached'), '')
        self.assertTrue(load_config(self.kb).workers)
        self.assertIn(original, (self.kb / 'log.md').read_text())
        # Every local link written by initialization resolves in the resulting bundle.
        for _, name in gitutil.status(self.kb):
            path = self.kb / name
            if path.is_file():
                for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text()):
                    self.assertTrue((path.parent / unquote(target)).exists(), (name, target))

    def test_initialization_rejects_dirty_checkout_and_existing_branch(self):
        original = gitutil.rev_parse(self.kb, 'HEAD')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            initialize_knowledge(self.kb, 'main')
        for branch in ('-bad', 'HEAD', '@{-1}', 'bad branch'):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                initialize_knowledge(self.kb, branch)
        (self.kb / 'uncommitted.md').write_text('Keep this work\n')
        with self.assertRaisesRegex(ValueError, 'clean'):
            initialize_knowledge(self.kb, 'knowledge/test-app')
        self.assertEqual(gitutil.rev_parse(self.kb, 'HEAD'), original)
        self.assertEqual(gitutil.git(self.kb, 'branch', '--show-current'), 'main')
        self.assertEqual((self.kb / 'uncommitted.md').read_text(), 'Keep this work\n')
        self.assertFalse(gitutil.succeeds(self.kb, 'show-ref', '--verify', 'refs/heads/knowledge/test-app'))

    def test_initialization_rejects_symlinks_and_non_markdown_before_switching(self):
        outside = self.root / 'outside.md'
        outside.write_text('Must remain unchanged\n')
        (self.kb / 'core/link.md').symlink_to(outside)
        self.commit(self.kb)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            initialize_knowledge(self.kb, 'knowledge/test-app')
        self.assertEqual(outside.read_text(), 'Must remain unchanged\n')
        (self.kb / 'core/link.md').unlink()
        (self.kb / 'core/data.json').write_text('{}')
        self.commit(self.kb)
        with self.assertRaisesRegex(ValueError, 'Markdown'):
            initialize_knowledge(self.kb, 'knowledge/test-app')
        self.assertEqual(gitutil.git(self.kb, 'branch', '--show-current'), 'main')
        self.assertEqual(gitutil.status(self.kb), [])

    def test_first_run_a_then_optional_b_with_same_frozen_inputs(self):
        # Exercise shell quoting in the printed commands.
        destination = self.root / 'knowledge with spaces'
        self.kb.rename(destination)
        self.kb = destination
        self.assertIn('chosen-session', self.command('sessions', '--repo', str(self.app)))
        self.initialize()
        baseline = gitutil.rev_parse(self.kb, 'HEAD')
        before = gitutil.git(self.app, 'show', 'HEAD:README.md')
        with patch('contextops.strategies.run_agent', self.specialist()), \
             patch('contextops.writer.run_agent', self.writer), \
             patch('contextops.orchestrator._prepare_auth'), \
             patch('contextops.orchestrator.open_pr', side_effect=AssertionError('Publication forbidden')):
            summary = self.sweep()
            a_dir = next((self.root / 'runs/sweeper-first').glob('*/run.json')).parent
            a = load_run(a_dir)
            self.assertIn('Result branch: ' + a.branch, summary)
            self.assertIn('core/terminology.md', summary)
            self.assertIn('TERM-001', gitutil.git(self.kb, 'show', f'{a.branch}:core/terminology.md'))
            self.assertNotIn('TERM-001', (self.kb / 'core/terminology.md').read_text())
            self.assertEqual(gitutil.rev_parse(self.kb, 'HEAD'), baseline)
            self.assertEqual(gitutil.git(self.kb, 'branch', '--show-current'), 'knowledge/test-app')
            command = next(line for line in summary.splitlines() if line.startswith('git ') and ' diff ' in line)
            diff = subprocess.check_output(shlex.split(command), text=True)
            self.assertIn('+TERM-001', diff)
            self.assertEqual((a_dir / 'completion.txt').read_text(), summary.split('\n', 1)[1])
            b = create_run(a.app_root, a.kb_root, 'origin', 'manual', a.head_sha, a.base_sha,
                           strategy='fresh-specialists', sessions=a.sessions, cutoff=a.cutoff)
            self.assertEqual(b.kb_baseline, a.kb_baseline)
            self.assertEqual(b.conversation_sha256, a.conversation_sha256)
            self.assertNotEqual(b.branch, a.branch)
            b_summary = self.command('run', str(b.run_dir))
            self.assertIn('Result branch: ' + b.branch, b_summary)
        self.assertEqual(gitutil.git(self.app, 'show', 'HEAD:README.md'), before)
        self.assertEqual(gitutil.status(self.app), [])
        self.assertEqual(gitutil.status(self.kb), [])
        self.assertFalse(a.kb_snapshot.exists())
        self.assertFalse(a.app_snapshot.exists())

    def test_no_change_and_deferred_runs_do_not_advertise_missing_artifacts(self):
        self.initialize()
        for op, expected in (('NO_CHANGE', 'No knowledge changes'), ('NEEDS_REVIEW', 'findings need review')):
            with self.subTest(op=op), patch('contextops.strategies.run_agent', self.specialist(op)), \
                 patch('contextops.writer.run_agent', side_effect=AssertionError('Writer not needed')), \
                 patch('contextops.orchestrator._prepare_auth'):
                summary = self.sweep()
            self.assertIn(expected, summary)
            self.assertNotIn('Result branch:', summary)
            self.assertNotIn('patch:', summary)
            self.assertNotIn('git -C', summary)
        branches = gitutil.git(self.kb, 'branch', '--list', 'contextops/*')
        self.assertEqual(branches, '')

    def test_failed_writer_retains_candidate_without_result_branch(self):
        self.initialize()
        async def failed_writer(spec, **kw):
            await self.writer(spec, **kw)
            return AgentRun('writer', status='crashed')
        with patch('contextops.strategies.run_agent', self.specialist()), \
             patch('contextops.writer.run_agent', failed_writer), \
             patch('contextops.orchestrator._prepare_auth'):
            summary = self.sweep()
        self.assertIn('writer failed', summary)
        self.assertIn('Candidate patch:', summary)
        self.assertNotIn('Result branch:', summary)
        run_dir = next((self.root / 'runs/sweeper-first').glob('*/run.json')).parent
        ctx = load_run(run_dir)
        self.assertIn('+TERM-001', (run_dir / 'knowledge.patch').read_text())
        self.assertFalse(gitutil.succeeds(self.kb, 'show-ref', '--verify', f'refs/heads/{ctx.branch}'))
        self.assertFalse(ctx.kb_snapshot.exists())

    def test_budget_exhaustion_reports_accepted_but_unapplied_records(self):
        self.initialize()
        with patch('contextops.strategies.run_agent', self.specialist(cost=20)), \
             patch('contextops.writer.run_agent', side_effect=AssertionError('No budget for writer')), \
             patch('contextops.orchestrator._prepare_auth'):
            summary = self.sweep()
        self.assertIn('Run incomplete', summary)
        self.assertIn('accepted records were not applied', summary)
        self.assertNotIn('Result branch:', summary)
        self.assertNotIn('patch:', summary)

    def test_invalid_inputs_fail_before_model_calls_or_run_creation(self):
        self.initialize()
        for extra in (('--session', 'missing'), ('--head', 'not-a-commit')):
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit) as error:
                self.sweep(*extra)
            self.assertEqual(error.exception.code, 2)
        self.assertFalse((self.root / 'runs').exists())


if __name__ == '__main__':
    unittest.main()
