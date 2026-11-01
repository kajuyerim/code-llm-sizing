"""Deterministic contract checks. No real history, authentication, or model calls."""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import yaml
from contextops import access, frontmatter, gitutil, transcripts
from contextops.agents import AgentRun, Ledger, load_agent, run_agent
from contextops.cli import main
from contextops.config import load_config
from contextops.evidence import build_pack
from contextops.initializer import Worker, plan_workers
from contextops.orchestrator import orchestrate
from contextops.review import review_results
from contextops.run import create_run, frozen_sessions, load_run, record_cutoff, last_cutoff
from contextops.strategies import WorkerResult, fresh_specialists
from contextops.writer import _revert_outside_scope

ROOT = Path(__file__).resolve().parents[2]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='contextops-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.app, self.kb = self.root / 'application', self.root / 'knowledge'
        self.app.mkdir(); self.kb.mkdir()
        for repo in (self.app, self.kb):
            gitutil.git(repo, 'init', '-b', 'main')
            gitutil.git(repo, 'config', 'user.name', 'Context Ops Test')
            gitutil.git(repo, 'config', 'user.email', 'test@example.invalid')
            gitutil.git(repo, 'config', 'core.hooksPath', '/dev/null')
            gitutil.git(repo, 'config', 'commit.gpgsign', 'false')
        (self.app / 'README.md').write_text('Initial development notes\n')
        self.commit(self.app)
        self.base = gitutil.rev_parse(self.app, 'HEAD')
        (self.app / 'README.md').write_text('Development now uses Firebase.\n')
        self.commit(self.app)
        self.head = gitutil.rev_parse(self.app, 'HEAD')
        for name in ('agents', 'core', 'tools', 'maintenance'):
            shutil.copytree(ROOT / name, self.kb / name, ignore=shutil.ignore_patterns('.DS_Store'))
        for name in ('init.md', 'index.md', 'log.md'):
            shutil.copyfile(ROOT / name, self.kb / name)
        meta, body = frontmatter.read(self.kb / 'init.md')
        meta['output']['runs_dir'] = str(self.root / 'runs')
        meta['after']['cartographer'] = None
        (self.kb / 'init.md').write_text('---\n' + yaml.safe_dump(meta, sort_keys=False) + '---\n' + body)
        self.commit(self.kb)
        self.history = self.root / 'history'
        directory = self.history / transcripts.encode_project(self.app)
        directory.mkdir(parents=True)
        self.session_file = directory / 'chosen-session.jsonl'
        self.cutoff = datetime.now(timezone.utc)
        self.message = {'type': 'user', 'cwd': str(self.app), 'uuid': 'message-1',
                        'timestamp': (self.cutoff - timedelta(seconds=1)).isoformat(),
                        'message': {'content': 'Firebase is the chosen tool for this application.'}}
        self.session_file.write_text(json.dumps(self.message) + '\n')
        self.history_patch = patch.object(transcripts, 'PROJECTS_DIR', self.history)
        self.history_patch.start(); self.addCleanup(self.history_patch.stop)
        self.no_model = patch('contextops.agents.query', side_effect=AssertionError('Live inference forbidden in tests'))
        self.no_model.start(); self.addCleanup(self.no_model.stop)

    def commit(self, repo):
        gitutil.git(repo, 'add', '-A')
        gitutil.git(repo, 'commit', '-m', 'Deterministic test checkpoint')

    def prepare(self, **kwargs):
        args = dict(strategy='fresh-specialists', sessions=['chosen-session'], cutoff=self.cutoff)
        args.update(kwargs)
        return create_run(self.app, self.kb, 'origin', 'manual', self.head, self.base, **args)

    def test_explicit_selection_and_missing_evidence(self):
        for args in ({'strategy': None}, {'sessions': None}, {'sessions': ['missing']},
                     {'sessions': ['../invalid']}, {'cutoff': self.cutoff.replace(tzinfo=None)}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.prepare(**args)
        self.assertFalse((self.root / 'runs').exists())

    def test_cli_requires_selection(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            main(['sweep', '--base', self.base])
        self.assertEqual(result.exception.code, 2)

    def test_invalid_refs_fail_before_artifacts(self):
        with self.assertRaises(subprocess.CalledProcessError):
            create_run(self.app, self.kb, 'origin', 'manual', 'not-a-commit', self.base,
                       strategy='fresh-specialists', sessions=['chosen-session'])
        self.assertFalse((self.root / 'runs').exists())

    def test_frozen_conversation_and_integrity(self):
        ctx = self.prepare()
        self.session_file.write_text('')
        loaded = load_run(ctx.run_dir)
        self.assertEqual(loaded.strategy, 'fresh-specialists')
        self.assertEqual(loaded.sessions, ['chosen-session'])
        self.assertEqual(len(frozen_sessions(loaded)[0].messages), 1)
        self.assertEqual(loaded.cutoff, self.cutoff)
        (ctx.run_dir / 'conversation.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            frozen_sessions(loaded)

    def test_state_namespacing_and_unique_attempts(self):
        a, b = self.prepare(), self.prepare()
        self.assertNotEqual(a.run_dir, b.run_dir)
        self.assertEqual(a.runs_dir.name, 'fresh-specialists')
        self.assertIn('/fresh-specialists/', a.branch)
        record_cutoff(a.runs_dir, self.app, self.cutoff)
        self.assertEqual(last_cutoff(a.runs_dir, self.app), self.cutoff)
        self.assertIsNone(last_cutoff(self.root / 'runs' / 'sweeper-first', self.app))

    def test_legacy_manifest_is_readable_not_executable(self):
        ctx = self.prepare()
        data = json.loads((ctx.run_dir / 'run.json').read_text())
        for k in ('strategy', 'sessions', 'conversation_sha256'):
            data.pop(k)
        (ctx.run_dir / 'run.json').write_text(json.dumps(data))
        loaded = load_run(ctx.run_dir)
        self.assertIsNone(loaded.strategy)
        with self.assertRaisesRegex(ValueError, 'Legacy'):
            frozen_sessions(loaded)
        self.assertEqual(json.loads((ctx.run_dir / 'run.json').read_text()), data)

    def test_tool_roster_and_legacy_worker(self):
        ctx = self.prepare()
        evidence = build_pack(ctx, load_config(self.kb))
        workers, skipped = plan_workers(load_config(self.kb), evidence)
        self.assertEqual(len(workers), 5)
        self.assertIn('tool-maintainer:firebase', [w.label for w in workers])
        self.assertTrue(any('dataform' in s for s in skipped))
        worker = workers[-1]
        old = dict(label=worker.label, spec=worker.spec, owns='products/firebase/',
                   product='firebase', reason=worker.reason)
        restored = Worker.from_record(old)
        self.assertEqual(restored.tool, 'firebase')
        self.assertEqual(restored.owns, 'products/firebase/')
        self.assertIn('product', old)

    def test_truncation_is_recorded(self):
        session = transcripts.Session('s', None, [transcripts.Message(str(i), 'user', '', 'long message') for i in range(10)])
        rendered, kept = transcripts.to_markdown(session, 50)
        self.assertIn('Older messages dropped:', rendered)
        self.assertLess(len(kept), 10)

    def test_fresh_specialists_never_resume(self):
        ctx = self.prepare(); config = load_config(self.kb)
        workers, _ = plan_workers(config, build_pack(ctx, config))
        fake = AsyncMock(side_effect=lambda spec, **kw: AgentRun(kw['label'], status='success'))
        with patch('contextops.strategies.run_agent', fake):
            asyncio.run(fresh_specialists(workers, ctx, config, Ledger(10)))
        self.assertEqual(fake.call_count, len(workers))
        for call in fake.call_args_list:
            self.assertIsNone(call.kwargs['resume']); self.assertFalse(call.kwargs['fork'])

    def test_path_guard_blocks_source_writes_and_escapes(self):
        guard = access.file_guard(self.kb, [self.app], True)
        (self.kb / 'tools' / 'escape').symlink_to(self.app, target_is_directory=True)
        async def allowed(name, path):
            return not await guard({'tool_name': name, 'tool_input': {'file_path': str(path)}}, None, None)
        self.assertTrue(asyncio.run(allowed('Write', self.kb / 'tools/firebase/notes.md')))
        for path in (self.app / 'README.md', self.kb / 'tools/escape/README.md',
                     self.kb / 'index.md.extra', self.kb / '.git/config', self.kb / 'tools/firebase/auth.json'):
            self.assertFalse(asyncio.run(allowed('Write', path)))
        self.assertTrue(asyncio.run(allowed('Read', self.app / 'README.md')))
        self.assertFalse(asyncio.run(allowed('Read', self.root / 'outside.md')))

    def test_rejects_outside_assignment_and_old_new_scope(self):
        ctx = self.prepare(); config = load_config(self.kb); evidence = build_pack(ctx, config)
        worker = plan_workers(config, evidence)[0][0]
        record = {'op':'ADD','fact_id':'TERM-999','target':worker.owns,'text':'Supported definition',
                  'scope':'app:test','reason':'Developer decision','evidence':[{'kind':'conversation','session':'chosen-session','message':'message-1'}]}
        for target, scope in [('core/../README.md','app:test'), ('tools/firebase/README.md','tool:firebase'), (worker.owns,'product:firebase')]:
            output={'records':[{**record,'target':target,'scope':scope}],'handoffs':[],'unowned':[]}
            review=review_results([WorkerResult(worker,AgentRun(worker.label,output=output))],ctx,evidence)
            self.assertEqual(len(review.rejected),1)

    def test_shared_pipeline_no_network_or_source_writes(self):
        ctx=self.prepare(); before=gitutil.rev_parse(self.app,'HEAD')
        async def specialist(spec, **kw):
            records=[]
            if kw['label']=='terminology-maintainer':
                records=[{'op':'ADD','fact_id':'TERM-999','target':'core/terminology.md',
                          'text':'Test term: an application-scoped definition.','scope':'app:test',
                          'reason':'Developer definition','evidence':[{'kind':'conversation','session':'chosen-session','message':'message-1'}]}]
            return AgentRun(kw['label'],status='success',session_id=kw['label'],output={'records':records,'handoffs':[],'unowned':[],'coverage':{'files_read':[],'sessions_read':['chosen-session'],'notes':''}})
        async def writer(spec, **kw):
            path=kw['cwd']/'core/terminology.md'
            path.write_text(path.read_text()+'\nTERM-999: Test definition.\n')
            return AgentRun('writer',status='success',output={'applied':[],'skipped':[],'log_entry':''})
        with patch('contextops.strategies.run_agent',specialist), patch('contextops.writer.run_agent',writer), patch('contextops.orchestrator._prepare_auth'), patch('contextops.orchestrator.open_pr',side_effect=AssertionError('Publication forbidden')):
            report=asyncio.run(orchestrate(ctx.run_dir))
        self.assertTrue(report.exists())
        self.assertTrue(gitutil.succeeds(self.kb,'rev-parse','--verify',ctx.branch))
        self.assertEqual(gitutil.rev_parse(self.app,'HEAD'),before)
        self.assertEqual(gitutil.status(self.app),[])
        self.assertFalse(ctx.app_snapshot.exists())
        with self.assertRaises((FileExistsError, ValueError)):
            asyncio.run(orchestrate(ctx.run_dir))

    def test_failed_writer_never_commits(self):
        from contextops.review import Review
        from contextops.writer import write_changes
        ctx=self.prepare();gitutil.add_worktree(self.kb,ctx.kb_snapshot,ctx.kb_baseline,branch=ctx.branch)
        async def failed(spec, **kw):
            path=kw['cwd']/'core/terminology.md';path.write_text(path.read_text()+'\nPartial edit\n')
            (kw['cwd']/'tools/firebase/new.md').write_text('New retained candidate\n')
            return AgentRun('writer',status='crashed')
        try:
            with patch('contextops.writer.run_agent',failed):
                publication,_=asyncio.run(write_changes(ctx,load_config(ctx.kb_snapshot),Review(),Ledger(10)))
            self.assertFalse(publication.committed)
            self.assertIn('Partial edit',(ctx.run_dir/'knowledge.patch').read_text())
            self.assertIn('New retained candidate',(ctx.run_dir/'knowledge.patch').read_text())
        finally:
            gitutil.remove_worktree(self.kb,ctx.kb_snapshot)

    def test_sdk_options_are_restricted_without_inference(self):
        config=load_config(self.kb);spec=load_agent(config.writer,config.default_model)
        captured={}
        async def no_query(*,prompt,options):
            captured['options']=options
            if False: yield None
        with patch('contextops.agents.query',no_query):
            asyncio.run(run_agent(spec,label='writer',system='rules',prompt='task',schema={},cwd=self.kb,dirs=[self.app],budget_usd=1,max_turns=1))
        options=captured['options']
        self.assertEqual(options.setting_sources,[])
        self.assertEqual(options.tools,spec.tools)
        self.assertIn('PreToolUse',options.hooks)
        self.assertNotIn('Bash',options.tools)

    def test_recursive_grep_cannot_read_sensitive_descendants(self):
        (self.app / 'credentials.json').write_text('{}')
        guard = access.file_guard(self.app, [], False)
        blocked = asyncio.run(guard({'tool_name':'Grep','tool_input':{'path':str(self.app),'pattern':'.'}}, None, None))
        self.assertEqual(blocked['hookSpecificOutput']['permissionDecision'], 'deny')
        allowed = asyncio.run(guard({'tool_name':'Grep','tool_input':{'path':str(self.app/'README.md'),'pattern':'.'}}, None, None))
        self.assertEqual(allowed, {})

    def test_existing_branch_is_never_deleted(self):
        ctx = self.prepare()
        gitutil.git(self.kb, 'branch', ctx.branch)
        sentinel = gitutil.rev_parse(self.kb, ctx.branch)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            asyncio.run(orchestrate(ctx.run_dir))
        self.assertEqual(gitutil.rev_parse(self.kb, ctx.branch), sentinel)

    def test_frontmatter_and_outside_files_are_restored(self):
        from contextops.review import Review
        from contextops.writer import write_changes
        ctx=self.prepare();gitutil.add_worktree(self.kb,ctx.kb_snapshot,ctx.kb_baseline,branch=ctx.branch)
        original=(ctx.kb_snapshot/'tools/firebase/README.md').read_text()
        async def writer(spec, **kw):
            (kw['cwd']/'tools/firebase/README.md').write_text('---\nkeywords: [changed]\n---\ntext\n')
            (kw['cwd']/'index.md.extra').write_text('Outside scope')
            (kw['cwd']/'tools/firebase/new.md').write_text('Allowed new content\n')
            return AgentRun('writer',status='success',output={})
        try:
            with patch('contextops.writer.run_agent',writer):
                publication,_=asyncio.run(write_changes(ctx,load_config(ctx.kb_snapshot),Review(),Ledger(10)))
            self.assertTrue(publication.committed)
            self.assertEqual((ctx.kb_snapshot/'tools/firebase/README.md').read_text(),original)
            self.assertFalse((ctx.kb_snapshot/'index.md.extra').exists())
            self.assertIn('Allowed new content',(ctx.run_dir/'knowledge.patch').read_text())
        finally:
            gitutil.remove_worktree(self.kb,ctx.kb_snapshot)

    def test_strategy_output_symlink_cannot_enter_repositories(self):
        parent=self.root/'runs';parent.mkdir()
        for target in (self.app,self.kb):
            link=parent/'fresh-specialists';link.symlink_to(target,target_is_directory=True)
            try:
                with self.assertRaisesRegex(ValueError,'symlinks'):
                    self.prepare()
                self.assertEqual(gitutil.status(target),[])
            finally:
                link.unlink()
