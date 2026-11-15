"""Attaching an application, push-triggered runs, and review requests, with disposable repositories."""
from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import test_runtime
import test_onboarding
from contextops import frontmatter, gitutil, transcripts
from contextops.attach import BEGIN, END
from contextops.cli import main
from contextops.config import load_config
from contextops.orchestrator import orchestrate
from contextops.run import create_run, load_run, record_cutoff
from contextops.strategies import worker_prompt


class AttachTests(unittest.TestCase):
    commit = test_runtime.RuntimeTests.commit
    command = test_onboarding.FirstRunTests.command
    specialist = test_onboarding.FirstRunTests.specialist
    writer = staticmethod(test_onboarding.FirstRunTests.writer)

    def setUp(self):
        test_runtime.RuntimeTests.setUp(self)
        gitutil.git(self.app, 'config', '--unset', 'core.hooksPath')

    def fails(self, *args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            self.command(*args)
        return err.getvalue()

    def set_output(self, **values):
        meta, body = frontmatter.read(self.kb / 'init.md')
        meta['output'].update(values)
        import yaml
        (self.kb / 'init.md').write_text('---\n' + yaml.safe_dump(meta, sort_keys=False) + '---\n' + body)
        self.commit(self.kb)

    def bare_remote(self, repo: Path, name: str) -> Path:
        remote = self.root / f'{name}.git'
        gitutil.git(self.root, 'init', '--bare', '-b', 'main', str(remote))
        gitutil.git(repo, 'remote', 'add', 'origin', str(remote))
        gitutil.git(repo, 'push', '-u', 'origin', 'main')
        return remote

    def test_init_sets_scope_and_repository_scope_binds_one_application(self):
        self.command('init', '--kb', str(self.kb), '--branch', 'knowledge/one', '--scope', 'repository',
                     '--application', 'billing')
        self.commit(self.kb)
        config = load_config(self.kb)
        self.assertEqual((config.scope, config.application), ('repository', 'billing'))
        self.assertIn("serves only 'billing'", self.fails('attach', '--repo', str(self.app), '--kb', str(self.kb), '--no-hook'))
        self.command('attach', '--repo', str(self.app), '--kb', str(self.kb), '--no-hook', '--name', 'billing')
        ctx = create_run(self.app, self.kb, 'origin', 'manual', self.head, self.base, strategy='sweeper-first',
                         sessions=['chosen-session'], cutoff=self.cutoff)
        self.assertEqual((ctx.scope, ctx.app), ('repository', 'billing'))
        prompt = worker_prompt(type('W', (), {'label': 'x', 'owns': 'core/pitfalls.md', 'tool': None})(), ctx)
        self.assertIn('serves one application, billing', prompt)
        self.assertIn('--scope repository', self.fails('init', '--kb', str(self.kb), '--branch', 'knowledge/two',
                                                       '--application', 'billing'))

    def test_team_scope_prompt_protects_other_applications(self):
        ctx = create_run(self.app, self.kb, 'origin', 'manual', self.head, self.base, strategy='sweeper-first',
                         sessions=['chosen-session'], cutoff=self.cutoff, app_name='web')
        text = worker_prompt(type('W', (), {'label': 'x', 'owns': 'core/pitfalls.md', 'tool': None})(), ctx)
        self.assertIn('shared by a team', text)
        self.assertIn('`app:web`', text)
        self.assertIn('other applications', text)

    def test_attach_writes_only_untracked_local_files_and_is_idempotent(self):
        (self.app / 'AGENTS.md').write_text('Project rules\n')
        self.commit(self.app)
        (self.app / 'CLAUDE.local.md').write_text('My own notes\n')
        settings = self.app / '.claude' / 'settings.local.json'
        settings.parent.mkdir()
        settings.write_text(json.dumps({'permissions': {'allow': ['Bash(make:*)']}, 'model': 'x'}))
        for _ in range(2):
            self.command('attach', '--repo', str(self.app), '--kb', str(self.kb), '--strategy', 'sweeper-first')
        memory = (self.app / 'CLAUDE.local.md').read_text()
        self.assertTrue(memory.startswith('My own notes\n'))
        self.assertEqual(memory.count(BEGIN), 1)
        self.assertIn('@AGENTS.md', memory)
        self.assertIn(str(self.kb.resolve() / 'index.md'), memory)
        data = json.loads(settings.read_text())
        self.assertEqual(data['permissions']['allow'], ['Bash(make:*)'])
        self.assertEqual(data['permissions']['additionalDirectories'], [str(self.kb.resolve())])
        self.assertEqual(len(data['hooks']['SessionStart']), 1)
        self.assertIn('contextops refresh', data['hooks']['SessionStart'][0]['hooks'][0]['command'])
        self.assertEqual(gitutil.status(self.app), [])  # nothing tracked or visible to Git changed
        self.assertEqual(gitutil.config_get(self.app, 'contextops.strategy'), 'sweeper-first')
        hook = Path(gitutil.git(self.app, 'rev-parse', '--git-path', 'hooks/pre-push'))
        hook = hook if hook.is_absolute() else self.app / hook
        self.assertIn('contextops hook', hook.read_text())
        self.assertTrue(hook.stat().st_mode & stat.S_IXUSR)

    def test_attach_refuses_tracked_local_files_and_missing_strategy(self):
        self.assertIn('strategy', self.fails('attach', '--repo', str(self.app), '--kb', str(self.kb)))
        (self.app / 'CLAUDE.local.md').write_text('committed by mistake\n')
        self.commit(self.app)
        self.assertIn('tracked', self.fails('attach', '--repo', str(self.app), '--kb', str(self.kb), '--no-hook'))

    def test_automatic_selection_takes_sessions_active_since_the_last_run(self):
        old = self.history / transcripts.encode_project(self.app) / 'old-session.jsonl'
        message = dict(self.message, uuid='old-1', timestamp=(self.cutoff - timedelta(days=3)).isoformat())
        old.write_text(json.dumps(message) + '\n')
        config = load_config(self.kb)
        record_cutoff(config.output.runs_dir / 'sweeper-first', self.app, self.cutoff - timedelta(days=1))
        ctx = create_run(self.app, self.kb, 'origin', 'manual', self.head, self.base,
                         strategy='sweeper-first', auto_select=True, cutoff=self.cutoff)
        self.assertEqual(ctx.sessions, ['chosen-session'])
        record_cutoff(config.output.runs_dir / 'sweeper-first', self.app, self.cutoff)
        with self.assertRaisesRegex(ValueError, 'No Claude Code session'):
            create_run(self.app, self.kb, 'origin', 'manual', self.head, self.base,
                       strategy='sweeper-first', auto_select=True, cutoff=self.cutoff)

    def push_and_run(self):
        """Run the pre-push hook for the application's new commit, then the prepared run with fakes."""
        spawned = []
        message = dict(self.message, timestamp=datetime.now(timezone.utc).isoformat())
        self.session_file.write_text(json.dumps(message) + '\n')
        stdin = io.StringIO(f'refs/heads/main {self.head} refs/heads/main {self.base}\n')
        with patch('contextops.cli._spawn', spawned.append), patch.object(sys, 'stdin', stdin), \
             contextlib.redirect_stderr(io.StringIO()) as err, patch('os.getcwd', return_value=str(self.app)):
            main(['hook', 'origin'])
        self.assertEqual(len(spawned), 1, err.getvalue())
        with patch('contextops.strategies.run_agent', self.specialist()), \
             patch('contextops.writer.run_agent', self.writer), patch('contextops.orchestrator._prepare_auth'):
            import asyncio
            asyncio.run(orchestrate(spawned[0]))
        return load_run(spawned[0])

    def test_push_opens_a_review_branch_on_the_knowledge_remote(self):
        self.set_output(open_pr=True)
        remote = self.bare_remote(self.kb, 'knowledge')
        self.command('attach', '--repo', str(self.app), '--kb', str(self.kb), '--strategy', 'sweeper-first')
        ctx = self.push_and_run()
        self.assertEqual(ctx.sessions, ['chosen-session'])
        self.assertIn('Test definition', gitutil.git(remote, 'show', f'{ctx.branch}:core/terminology.md'))
        self.assertNotIn('Test definition', gitutil.git(remote, 'show', 'main:core/terminology.md'))
        completion = (ctx.run_dir / 'completion.txt').read_text()
        self.assertIn(f'pushed {ctx.branch}', completion)
        self.assertIn('into main', completion)

    def test_github_and_gitlab_requests(self):
        self.set_output(open_pr=True, forge='github')
        self.bare_remote(self.kb, 'knowledge')
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        calls = self.root / 'gh-calls.txt'
        (bin_dir / 'gh').write_text(f'#!/bin/sh\necho "$@" >> {calls}\necho https://github.example/pr/7\n')
        (bin_dir / 'gh').chmod(0o755)
        self.command('attach', '--repo', str(self.app), '--kb', str(self.kb), '--strategy', 'sweeper-first')
        with patch.dict(os.environ, {'PATH': f'{bin_dir}:{os.environ["PATH"]}'}):
            ctx = self.push_and_run()
        self.assertIn(f'pr create --base main --head {ctx.branch}', calls.read_text())
        self.assertIn('https://github.example/pr/7', (ctx.run_dir / 'completion.txt').read_text())

        self.set_output(open_pr=True, forge='gitlab')
        remote = self.root / 'knowledge.git'
        gitutil.git(remote, 'config', 'receive.advertisePushOptions', 'true')
        gitutil.git(self.kb, 'push', 'origin', 'main')
        self.head = self.make_commit('More development.\n')
        with patch('contextops.publish.shutil.which', return_value=None):
            ctx = self.push_and_run()
        self.assertIn('Test definition', gitutil.git(remote, 'show', f'{ctx.branch}:core/terminology.md'))
        self.assertIn('asked GitLab to open a merge request into main', (ctx.run_dir / 'completion.txt').read_text())

    def make_commit(self, text):
        self.base = gitutil.rev_parse(self.app, 'HEAD')
        (self.app / 'README.md').write_text(text)
        self.commit(self.app)
        message = dict(self.message, uuid='message-2')
        self.session_file.write_text(json.dumps(message) + '\n')
        return gitutil.rev_parse(self.app, 'HEAD')

    def test_session_start_digest_lists_entries_within_the_limit(self):
        (self.kb / 'core/pitfalls.md').write_text(
            '# Pitfalls\n\n| ID | Trigger | What goes wrong | Do instead | Scope | Evidence |\n| --- | --- | --- | --- | --- | --- |\n'
            '| PIT-001 | Backfill inside a migration | Long deploys | Run the data_migration task by hand | app:demo | msg-1 |\n')
        self.commit(self.kb)
        self.command('attach', '--repo', str(self.app), '--kb', str(self.kb), '--no-hook')
        data = json.loads((self.app / '.claude/settings.local.json').read_text())
        self.assertIn('--digest', data['hooks']['SessionStart'][0]['hooks'][0]['command'])
        self.assertIn('digest of its entries', (self.app / 'CLAUDE.local.md').read_text())
        text = self.command('refresh', '--kb', str(self.kb), '--digest')
        self.assertIn('core/pitfalls.md:', text)
        self.assertIn('- PIT-001: Backfill inside a migration / Long deploys / Run the data_migration task by hand / app:demo', text)
        self.assertNotIn('msg-1', text)
        self.assertNotIn('contextops:', text)  # no upstream is not a problem worth adding to context
        from contextops.attach import digest
        self.assertLessEqual(len(digest(self.kb, limit=400)), 400)
        self.assertIn('truncated', digest(self.kb, limit=400))

    def test_refresh_fast_forwards_only_clean_checkouts(self):
        remote = self.bare_remote(self.kb, 'knowledge')
        other = self.root / 'other-clone'
        gitutil.git(self.root, 'clone', str(remote), str(other))
        for key, value in (('user.name', 'Other'), ('user.email', 'o@example.invalid'), ('commit.gpgsign', 'false')):
            gitutil.git(other, 'config', key, value)
        (other / 'log.md').write_text('# Log\n\nMerged knowledge.\n')
        self.commit(other)
        gitutil.git(other, 'push', 'origin', 'main')
        (self.kb / 'core/pitfalls.md').write_text('local edit\n')
        self.assertIn('local changes', self.command('refresh', '--kb', str(self.kb)))
        gitutil.git(self.kb, 'checkout', '--', 'core/pitfalls.md')
        self.assertEqual(self.command('refresh', '--kb', str(self.kb)), '')
        self.assertIn('Merged knowledge', (self.kb / 'log.md').read_text())


if __name__ == '__main__':
    unittest.main()
