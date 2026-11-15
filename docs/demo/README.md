# First-run demo: prepare locally, inspect recorded knowledge

You can prepare this demo and present its recorded result **without Claude authentication or model calls**. A fresh maintenance run is a separate optional step that needs your own provider access. Historical live runs exist at `caf4bdb` and `b20f3f9`; live acceptance of the current revision remains pending. See the [acceptance records](../first-run-acceptance.md) and [credential-free verification](verification.md).

## What is in this folder

| File | What it is |
| --- | --- |
| `actual/actual-demo.patch` | Eight commits on public Actual Budget commit `d9d15c12fa41a0bb8380fab09519e0180333e146` ([upstream](https://github.com/actualbudget/actual), MIT). The first prepares the simulation's agent instructions; the next seven are development work. Apply only in a disposable demo checkout, not your own application. |
| `actual/sessions/*.jsonl` | Six exported Claude Code sessions from that development. |
| [result-caf4bdb.patch](actual/result-caf4bdb.patch) | Recorded first-run knowledge output: ten entries, with the known issues in acceptance record 1. |
| [result-b20f3f9.patch](actual/result-b20f3f9.patch) | Recorded post-fix knowledge output: fifteen entries, acceptance record 2. |
| `actual/result.patch` | Unchanged legacy copy of the second result, retained for existing links. |

The sessions come from [experiment v2](../evaluation.md#experiment-v2-5-november-2026). Language-model teammate personas played the developer; Claude Code performed development in a real checkout. Exported inputs retain messages and tool calls, omit thinking and tool-result contents, and replace local paths with placeholders. Commits were re-authored as `Context Ops Demo`; that identity describes the supplied simulation history, not the person setting up knowledge. Original branch/commit names inside messages are historical and will differ from the reconstructed commit IDs.

## Prepare without inference

Use Python 3.11+, Git, network access for public dependencies, and a new disposable parent directory. Run these blocks in order, stopping if any command fails. Existing application development and local Claude Code sessions are required for [your own application](../../setup.md); the demo supplies its own simulated history.

### 1. Select the implementation and install

```sh
mkdir contextops-demo
cd contextops-demo
DEMO_ROOT="$PWD"
git clone --branch feat/team-knowledge-loop https://github.com/kajuyerim/code-llm-sizing.git knowledge
cd knowledge
IMPLEMENTATION=$(git rev-parse HEAD)
printf 'Implementation: %s\n' "$IMPLEMENTATION"
python3 -m venv "$DEMO_ROOT/.venv"
. "$DEMO_ROOT/.venv/bin/activate"
python -m pip install -r runtime/requirements-lock.txt
python -m pip install --no-deps -e runtime
python -m pip check
contextops --help
python -m unittest discover -s runtime/tests
DEMO="$PWD/docs/demo/actual"
```

Until this branch is merged, a plain default-branch clone does not select the first-run implementation. After the merge, cloning the default branch is appropriate; still record its exact SHA. Unpushed local commits are not available through a remote clone. Keep the full clone, including runtime and role definitions.

### 2. Reconstruct the separate application

```sh
cd "$DEMO_ROOT"
git init actual
cd actual
git fetch --depth 1 https://github.com/actualbudget/actual.git d9d15c12fa41a0bb8380fab09519e0180333e146
git checkout -b demo FETCH_HEAD
git -c user.name="Context Ops Demo" -c user.email=demo@example.invalid \
  am --keep-non-patch --committer-date-is-author-date "$DEMO/actual-demo.patch"
APP="$PWD"
DEMO_BASE=$(git rev-parse 'HEAD~7^{commit}')
DEMO_HEAD=$(git rev-parse 'HEAD^{commit}')
git rev-list --count "$DEMO_BASE..$DEMO_HEAD"
git rev-parse 'HEAD^{tree}'
git status --short
```

Expect seven development commits, tree `f53804376c1c736b7dc20b2840f9a944a71c4232`, and a clean checkout. Tree equality is the check: reconstructed commit IDs can differ from the original bundle because of committer metadata. No application build or feature development is needed for maintenance preparation.

### 3. Initialize and commit empty knowledge

```sh
cd "$DEMO_ROOT/knowledge"
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
contextops init --kb . --branch knowledge/actual-demo --scope team
python - "$DEMO_ROOT/runs" <<'PY'
import json, sys
from pathlib import Path
path = Path('init.md')
text = path.read_text()
old = 'runs_dir: ~/.contextops/runs'
if old not in text:
    raise SystemExit('Inspect the existing runs_dir setting before continuing.')
path.write_text(text.replace(old, 'runs_dir: ' + json.dumps(sys.argv[1]), 1))
PY
git diff -- core tools index.md log.md init.md
git add -- core tools index.md log.md init.md
git commit -m "Initialize empty knowledge for the actual demo"
git rev-parse HEAD
git status --short
```

If either identity check fails, stop and configure your real Git name/email locally before committing. Do not reuse the simulation author identity. Review `init.md`: keep `open_pr: false`, the default model/budgets and admission policy, and external run output. The default application label is `actual`. The [setup guide](../../setup.md#4-choose-scope-and-prepare-a-blank-knowledge-branch) explains repository scope and names containing spaces. Initialization writes blank templates, not learned facts. Your original implementation branch remains available.

### 4. Import the sessions in an isolated history directory

```sh
DEMO_CLAUDE_CONFIG="$DEMO_ROOT/claude-demo"
CLAUDE_CONFIG_DIR="$DEMO_CLAUDE_CONFIG" contextops import-session --repo "$APP" "$DEMO"/sessions/*.jsonl
CLAUDE_CONFIG_DIR="$DEMO_CLAUDE_CONFIG" contextops sessions --repo "$APP"
```

Expect all six session IDs to be listed. Only this disposable history directory is used; your normal Claude history is unchanged. This isolates history, not an authenticated account. No credentials are copied. The frozen cutoff below is the last development message, `2026-11-05T18:40:03Z`.

### 5. Freeze the selections and print the optional execution command

This uses the same preparation API as the CLI, without invoking maintenance agents. It records the source refs, knowledge baseline, selected conversation and its hash outside both repositories. Run it once per intended attempt; keep attempted artifacts rather than overwriting them.

```sh
CLAUDE_CONFIG_DIR="$DEMO_CLAUDE_CONFIG" python - "$APP" "$DEMO" "$DEMO_BASE" "$DEMO_HEAD" <<'PY'
from datetime import datetime
from pathlib import Path
import shlex, sys
from contextops.run import create_run
app, demo, base, head = sys.argv[1:]
ctx = create_run(Path(app), Path.cwd(), 'origin', 'manual', head, base,
                 strategy='sweeper-first',
                 sessions=[p.stem for p in sorted((Path(demo) / 'sessions').glob('*.jsonl'))],
                 cutoff=datetime.fromisoformat('2026-11-05T18:40:03+00:00'))
if ctx is None:
    raise SystemExit('No development range selected.')
print('Prepared only; no inference.')
print('Knowledge baseline:', ctx.kb_baseline)
print('Conversation SHA-256:', ctx.conversation_sha256)
print('Manifest:', ctx.run_dir / 'run.json')
print('Optional execution:', shlex.join(['contextops', 'run', str(ctx.run_dir)]))
PY
```

**Stop here for the no-authentication walkthrough.** No result branch or newly learned knowledge exists yet. The conversation hash includes the reconstructed local paths, so a different parent directory can produce a different hash. Configuration and roles are pinned to the recorded knowledge baseline. Keep the recorded implementation checkout and environment unchanged for execution: an editable installation still reads its installed runtime source. Changing authentication mode, model, budget or other settings requires committing a new baseline and preparing a new run.

## Present the recorded result without inference

1. Show the seven development commits and six selected sessions. Explain that the developer personas were simulated.
2. Open a blank core document on `knowledge/actual-demo` to show what initialization produces.
3. Open [result-b20f3f9.patch](actual/result-b20f3f9.patch) and the matching [acceptance record](../first-run-acceptance.md#live-acceptance-record-2-14-november-2026-b20f3f9). These are the actual recorded changes from **14 November at `b20f3f9`**, not output from today's preparation. Do not apply this historical patch and describe it as a new run.
4. Trace selected recorded rows to the following evidence, then show the optional command printed in step 5 as the step still awaiting authentication.

| Historical knowledge | Development evidence to inspect |
| --- | --- |
| `STACK-001` / `STACK-002`: use imported `undici.fetch`; avoid mismatching Node's bundled fetch and the project's dispatcher | [Fetch session](actual/sessions/70de19bb-341e-4ca0-a42f-f4262eb59326.jsonl), messages `fe370a12-46b9-470c-8115-39752c432913` and `aeb3ca2c-cd97-49d0-8c21-cb2687b48a96`. The developer rejects global fetch and adding axios/node-fetch. |
| `TERM-001`: amounts remain stored at x100, including yen | [Currency session](actual/sessions/de720aee-7716-4ecb-ba17-3a38c00ee07e.jsonl), message `d208a293-ba9d-4d21-bb27-8001a9983cc5`. The developer corrects zero-decimal storage and explains existing-data compatibility. |

Check the corresponding source files in the reconstructed application when explaining implemented behavior. Conversation evidence establishes the decision; a recorded proposal alone does not establish that it was written or implemented. Generated knowledge still needs human review.

The second historical run wrote fifteen entries in 4m 58s for an estimated $1.35. These are recorded measurements, not a promise for the current model, account or admission policy. Later rules exclude UI/component conventions and code-obvious patterns, so the current result may differ substantially or legitimately contain no changes.

## Optional live execution, when access is available

Authentication is your own provider access, not a file supplied with the repository. Follow [setup step 5](../../setup.md#5-configure-and-commit-the-baseline). The checked-in subscription mode uses private Claude Code authentication; API-key execution requires `auth: api-key` and `ANTHROPIC_API_KEY` in the execution environment. A key is ignored in subscription mode. If changing settings, commit and prepare a new run first.

Only then run the exact `contextops run ...` command printed for that preparation. The conversation is already frozen, so execution does not need to re-import or rediscover the sessions. Do not invoke a prepared directory twice or retry automatically after failure. Keep `open_pr: false`; no hook is part of this demo.

The completion summary identifies actual changed files, report/patch paths and, only if committed, the result branch and review commands. The baseline branch stays selected. Inspect the actual Git diff and resulting documents; accepted records and writer claims are not substitutes. Preserve no-change, deferred, budget-limited and failed-writer outcomes. Record any new live acceptance separately before describing the current revision as live-verified.
