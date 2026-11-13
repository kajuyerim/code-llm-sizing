# Install, configure, and run Context Ops

Keep this knowledge checkout separate from your application. You need Python 3.11+, Git, private Claude authentication, an existing application with committed development changes, and its local Claude Code sessions. Any coding agent can help with setup; the maintenance backend and conversation collector currently support Claude only.

For agent-guided setup, use the prompt in the [README](README.md#set-up-with-your-agent). The [setup skill](skills/setup-shared-knowledge/SKILL.md) is the authoritative agent procedure. The commands below are the equivalent manual path. The agent prepares configuration and invokes the runtime; it does not prefill learned knowledge.

## 1. Install in a clean environment

From the cloned Context Ops repository:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r runtime/requirements-lock.txt
python -m pip install --no-deps -e runtime
contextops --help
```

Installation downloads packages but does not authenticate or call a model. Keep the full clone: roles, maintenance instructions, and runtime are used together.

## 2. Test without credentials

```sh
python -m unittest discover -s runtime/tests -v
python runtime/check_docs.py
python runtime/check_public.py --history
```

Tests use fake responses and disposable repositories outside this checkout. They do not read your Claude history, authenticate, call a model, push, or install hooks. They verify software behavior, not live model quality. The [live acceptance record](docs/first-run-acceptance.md) remains pending until a separately authorized clean-clone run is completed.

## 3. Choose your development evidence

Identify the separate application and the committed range containing the development you want to learn from. Inspect its Git log, then resolve your chosen refs with:

```sh
git -C /path/to/application rev-parse --verify BASE_REF^{commit}
git -C /path/to/application rev-parse --verify HEAD_REF^{commit}
contextops sessions --repo /path/to/application
```

Use the resolved commit SHAs and selected session IDs in the run command. Session listing prints each ID, last message time, and opening line without inference. Do not guess the range or automatically choose the latest session. Uncommitted application edits are not included; completing application development is outside this setup.

Choose an explicit cutoff after the relevant development messages, using ISO 8601 with a timezone, for example `2026-11-13T12:00:00+03:00`. It cannot be in the future. For a cutoff of now, capture the value once with:

```sh
python -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())'
```

The collector requires local Claude Code JSONL history for this application. Arbitrary exports and Codex history are not accepted. Missing or ambiguous sessions fail before inference. Selected sessions include their complete retained history through the cutoff, not just messages newer than the base commit. Tool results and thinking are omitted, sidechains are excluded by default, and truncation is reported. Your setup conversation is not a substitute for the development conversation.

## 4. Prepare a blank knowledge branch

For a **fresh clone only**, choose a new branch name:

```sh
contextops init --kb . --branch knowledge/my-app
```

This requires a clean checkout. It creates and switches to the new branch, replaces core knowledge with four blank templates, empties tool entry points while retaining frontmatter/relevance hints, removes additional learned Markdown in core/tools, and refreshes the index/log. Runtime, roles, maintenance guides, skills, and historical research documents are retained. The original branch and its committed knowledge remain available. Symlinks and non-Markdown knowledge files are rejected before initialization.

Initialization leaves changes unstaged and uncommitted. It makes no model calls. The original Context Ops glossary and project-specific knowledge are absent from the new knowledge baseline. Empty templates are expected; do not invent facts to populate them.

For an existing installation, reuse the accepted knowledge branch and skip `init`. It is not a reset step for later runs. An existing branch name or dirty checkout is a reason to inspect your current work, not force a reset.

## 5. Configure and commit the baseline

Review [init.md](init.md). Keep `mode: null` and choose the strategy in the command. Defaults are `claude-sonnet-5-5`, $1.50 estimated per agent, a $10 estimated aggregate threshold, 30 turns, and up to three concurrent specialists. Change the model only when needed for your account or requested. Client estimates are not invoices; concurrent calls and the writer can exceed the threshold.

Keep `open_pr: false`, auto-memory disabled, and run output outside both checkouts. The default output parent is `~/.contextops/runs`. Both repositories must be separate and non-nested. Firebase/Dataform folders are relevance categories, not assumptions about your application's stack.

Check your Git identity before committing. If missing, configure your own name/email locally; never use an invented identity. From the knowledge checkout:

```sh
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git diff --stat
git diff -- core tools index.md log.md init.md
git add -- core tools index.md log.md init.md
git commit -m "Prepare empty knowledge for my application"
git rev-parse HEAD
git status --short
```

Record the resulting baseline SHA and the Context Ops implementation revision. Configuration and roles must be committed so the runtime's snapshot matches the reviewed settings. The checkout must be clean before sweeping.

Authenticate privately using your Claude Code installation. Subscription mode uses that login and removes the API-key environment variable from the runtime process. Optional API-key mode reads your environment. Never paste a credential into chat or place one in tracked files. Authentication is only needed for real inference; the configured Claude service performs inference remotely.

## 6. Run A manually

Substitute the paths, immutable commits, selected session, and fixed cutoff:

```sh
contextops sweep \
  --repo /path/to/application \
  --kb /path/to/code-llm-sizing \
  --base BASE_COMMIT --head HEAD_COMMIT \
  --strategy sweeper-first \
  --session SESSION_ID \
  --cutoff CUTOFF_WITH_TIMEZONE
```

Repeat `--session` for additional selected sessions. This makes real model calls. The selected conversation is copied and hashed before inference. A completes its sweeper before independently forking specialists; a failed sweeper never falls back to B. No hook is needed.

A setup-and-run request to your agent includes this configured local run. A setup-only request ends with the prepared command. Neither request implies publication or merging.

## 7. Inspect the actual result

The command prints the outcome, actual changed files, report/patch locations when present, estimated spend, and commands to review and open a committed result branch. It preserves the starting checkout branch. `completion.txt` saves the same summary.

Run artifacts are under `~/.contextops/runs/<strategy>/<run-id>/`. Inspect `run.json`, `pack/manifest.json`, `workers/`, `review.json`, `report.md`, and `metrics.json`. When produced, `knowledge.patch` contains the written changes. Compare it with accepted records; neither accepted proposals nor writer-reported applications establish faithful writing.

For a successful commit, use the exact printed commands, equivalent to:

```sh
git -C /path/to/code-llm-sizing diff BASELINE_COMMIT RESULT_BRANCH
git -C /path/to/code-llm-sizing show RESULT_BRANCH:core/terminology.md
# After review, explicitly open the result if you want to use it:
git -C /path/to/code-llm-sizing switch RESULT_BRANCH
```

A run with no relevant knowledge changes is valid. Deferred findings require review. Budget exhaustion can leave accepted records unapplied. A failed writer is not committed; its candidate patch is retained and its temporary worktree is removed. Failed or no-change runs do not advertise nonexistent result branches. Unexpected interruptions may leave only partial artifacts; the command prints the run directory before inference. Preserve it and investigate before creating another attempt.

For your next maintenance run, use the accepted knowledge branch as the baseline and select the next committed development range and appropriate sessions. Generated knowledge remains subject to human review. Raw runs are private local artifacts; sharing them requires deliberate selection and sanitization.

## Optional B from the same baseline

B is available with `--strategy fresh-specialists`. For an independent A/B comparison, use the same original knowledge baseline, source commits, selected sessions, cutoff, model and budgets. Do not switch to A's result before preparing B.

For an exact replay of A's frozen selections, prepare B without inference and verify its conversation hash before running it. Set `A_RUN` to the completed A run directory. This advanced snippet uses the installed runtime's Python preparation interface:

```sh
python - /path/to/A_RUN <<'PY'
import sys
from pathlib import Path
from contextops import gitutil
from contextops.run import create_run, load_run

a = load_run(Path(sys.argv[1]).expanduser())
if gitutil.rev_parse(a.kb_root, 'HEAD') != a.kb_baseline:
    raise SystemExit('Return to the original knowledge baseline before preparing B.')
b = create_run(a.app_root, a.kb_root, 'origin', 'manual', a.head_sha, a.base_sha,
               strategy='fresh-specialists', sessions=a.sessions, cutoff=a.cutoff)
if b is None or b.conversation_sha256 != a.conversation_sha256:
    raise SystemExit('Conversation history changed. Do not run this prepared directory.')
print(b.run_dir)
PY
contextops run /path/printed/for/B_RUN
```

Execute the final command only if preparation succeeded. B receives raw evidence and fresh sessions, with independent run artifacts and output branches. The snippet does not copy A's summaries or generated knowledge. Preserve changed-history attempts for diagnosis rather than quietly substituting different evidence.

## Troubleshooting and optional integration

- **No sessions found:** check the application path and local Claude Code history. Complete setup when the actual development sessions are available; unsupported exports are not a workaround.
- **Dirty knowledge checkout:** inspect the changes and commit the intended baseline. Preserve unrelated user work.
- **Missing Git identity:** configure the user's identity locally before committing.
- **Invalid refs or identical base/head:** inspect the application's history and select the intended committed development range.
- **Authentication/model failure:** resolve private login or model availability, retain failed artifacts, and create a new run only when ready. Do not loop retries automatically.
- **No result branch:** read the outcome and failures; no-change, deferred, budget-limited, and failed-writer runs may correctly have no branch.

Existing integrations can be preserved. A new subtree integration or application-instruction edit is a separate setup choice. The pre-push adapter remains experimental and is not installed by these steps; see the [runtime guide](runtime/README.md).
