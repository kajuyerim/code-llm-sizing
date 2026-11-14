# First-run demo: from empty knowledge to a populated branch

This demo lets anyone run Context Ops end to end without private data. It starts from the empty knowledge that `contextops init` prepares, runs strategy A (sweeper first) on six real Claude Code development sessions for Actual Budget, and ends with learned knowledge committed on a local branch. The [acceptance record](../first-run-acceptance.md#live-acceptance-record-2-14-november-2026-b20f3f9) lists what one run produced, with timing and cost.

## What is in this folder

| File | What it is |
| --- | --- |
| `actual/actual-demo.patch` | A `git format-patch` series of eight commits on top of the public upstream commit `d9d15c12fa41a0bb8380fab09519e0180333e146` of [actualbudget/actual](https://github.com/actualbudget/actual) (MIT). The first commit replaces the upstream agent rule files with a knowledge pointer; the next seven are the development work. |
| `actual/sessions/*.jsonl` | The six Claude Code sessions in which that work was developed, exported with `contextops export-session`. |
| `actual/result.patch` | The knowledge patch that the run in the acceptance record wrote. Yours will differ in wording. |

The sessions come from experiment v2 (see [evaluation](../evaluation.md#experiment-v2-5-november-2026)). The developer side was played by language-model teammate personas; the development agent was real Claude Code working in a real checkout. The export keeps developer and agent messages, text, and tool calls. It drops model thinking, tool results, and all other records, and replaces local paths with placeholders. Commits were re-authored as `Context Ops Demo` and local paths and user names were removed from them. Agent messages still mention the original branch and commit IDs; they do not affect the run.

## Run it

You need Python 3.11 or newer, Git, network access to GitHub, and a Claude Code login (the run makes real model calls, about $1 at list price with the default Sonnet model).

```sh
# 1. The knowledge checkout, installed and tested (no model calls)
git clone https://github.com/kajuyerim/code-llm-sizing.git knowledge
cd knowledge
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r runtime/requirements-lock.txt && python -m pip install --no-deps -e runtime
python -m unittest discover -s runtime/tests
DEMO="$PWD/docs/demo/actual"

# 2. The application: upstream commit plus the demo history
cd .. && git init actual && cd actual
git fetch --depth 1 https://github.com/actualbudget/actual.git d9d15c12fa41a0bb8380fab09519e0180333e146
git checkout -b demo FETCH_HEAD
git -c user.name="Context Ops Demo" -c user.email=demo@example.invalid \
  am --keep-non-patch --committer-date-is-author-date "$DEMO/actual-demo.patch"
APP="$PWD"

# 3. Empty knowledge on a new branch, committed as the baseline
cd ../knowledge
contextops init --kb . --branch knowledge/actual-demo
git add -A && git commit -m "Initialize empty knowledge for the actual demo"

# 4. Install the sessions for this checkout and check that they are listed
contextops import-session --repo "$APP" "$DEMO"/sessions/*.jsonl
contextops sessions --repo "$APP"

# 5. Maintenance, strategy A (real model calls)
contextops sweep --repo "$APP" --kb . \
  --base "$(git -C "$APP" rev-parse HEAD~7)" --head "$(git -C "$APP" rev-parse HEAD)" \
  --strategy sweeper-first --cutoff 2026-11-05T18:40:03Z \
  $(for f in "$DEMO"/sessions/*.jsonl; do printf -- '--session %s ' "$(basename "$f" .jsonl)"; done)
```

`import-session` writes the sessions under `~/.claude/projects/` for the new application path; remove that project folder afterwards if you do not want it there. The cutoff is the time of the last development message.

## Inspect the result

The command prints the changed files, the report and patch, and the Git commands to review the result branch. Your knowledge checkout stays on `knowledge/actual-demo`; nothing is merged or pushed.

```sh
git diff knowledge/actual-demo contextops/sweeper-first/<run id>
```

In the latest recorded run the empty core documents gained fifteen entries, for example:

- `TERM-001` Stored amount: every currency is stored at x100, including yen; decimal places only affect display.
- `STACK-001` Sync server code imports `fetch` from `undici`, never Node's global `fetch`.
- `NAME-001` Every commit message and PR title starts with `[AI]`.
- `PIT-004` Comparing a full From date with a bare month or year To key flips a same-period range.

Each entry cites the session message or source line that supports it, and all of them still need human review.
