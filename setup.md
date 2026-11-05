# Install, test, and run Context Ops

Keep this knowledge checkout separate from your application. Do not copy your application, conversation exports, or evaluation fixtures into it. Read the [walkthrough](docs/walkthrough/README.md) first.

## 1. Install in a clean environment

Use Python 3.11 or newer and Git. From this repository's root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r runtime/requirements-lock.txt
python -m pip install --no-deps -e runtime
contextops --help
```

The lock records the dependencies verified for this integration. Installation downloads packages but does not authenticate or call a model.

## 2. Test without credentials

```sh
python -m unittest discover -s runtime/tests -v
python runtime/check_docs.py
python runtime/check_public.py --history
```

Tests inject fake agent responses and create disposable repositories in the system temporary directory, outside this checkout. They do not read your real Claude history, install hooks, call a model, or push anything. Mock checks verify software wiring; they do not establish live SDK inheritance or reproduce pilot scores.

## 3. Prepare your own evidence

Identify an existing application repository outside this checkout and an explicit committed base/head range. Keep its development conversation in the local Claude Code history for that repository. Find the desired session IDs through Claude Code's session history or the filenames in its project history directory. Use only IDs, never account tokens.

The current collector supports Claude Code JSONL history. It does not accept arbitrary chat exports or Codex history. Each selected session must contain developer/assistant messages for the application before the cutoff. Missing or ambiguous sessions fail before inference. Explicit selection includes the complete retained session history through the cutoff, not only messages newer than the base commit. Tool results and thinking are omitted; sidechains are excluded by default. Truncation is reported.

Commit any changes to the knowledge configuration or role definitions first. Runs use the committed knowledge baseline. Keep both strategies on the same baseline, refs, selected sessions, cutoff, model, and budgets when comparing them. Their output states remain separate; this command is not an automatic evaluation harness.

## 4. Choose settings and authenticate privately

Review [init.md](init.md). It selects no strategy. The baseline uses `claude-sonnet-5-5`, a $1.50 estimated per-agent allowance, a $10 estimated total threshold, 30 turns, and at most three concurrent specialists. Choose a model available to your own Claude account and commit that setting before running. Client estimates are not subscription invoices, and concurrent calls can overshoot the total threshold.

Use your own Claude Code login outside this repository. Subscription mode uses that local login and removes the API-key environment variable from the runtime process. An optional API-key mode reads the user's environment. Never place a credential value in `init.md`, command examples, issue bodies, chat evidence, screenshots, or tracked files. Do not paste credentials into this project's discussions.

Authentication is needed only for real inference. It does not make inference local; this runtime invokes the configured Claude service. Auto-memory ingestion is disabled by default. Repository instruction files are treated as evidence, not runtime instructions.

## 5. Run once manually

Replace the placeholders below with your paths, immutable commits, session ID, and development cutoff:

```sh
contextops sweep \
  --repo /path/to/application \
  --kb /path/to/code-llm-sizing \
  --base BASE_COMMIT \
  --head HEAD_COMMIT \
  --strategy fresh-specialists \
  --session SESSION_ID \
  --cutoff 2026-11-01T12:00:00+03:00
```

Repeat `--session` to select additional sessions. Omit `--cutoff` to freeze the current time. The selected normalized conversation is copied and hashed before inference. A run cannot silently switch to another strategy or pick up later messages. The A strategy name is `sweeper-first`; it becomes available through the dependent A integration PR.

This command makes real model calls. No hook installation is necessary. The current defaults keep all output local and may create a local knowledge branch and commit. A run containing only NO_CHANGE records is a valid result.

## 6. Inspect the output

New artifacts are under `~/.contextops/runs/<strategy>/<run-id>/`. The printed report location is the starting point. Inspect `run.json`, `pack/manifest.json`, `workers/`, `review.json`, `knowledge.patch`, `report.md`, and `metrics.json`. Compare accepted proposals with the actual patch; accepted records do not prove faithful writing.

The report identifies any local knowledge branch. Inspect it using Git before merging or publishing it yourself. The application checkout is not a write target. A failed writer is not committed; its candidate patch is retained. A failed or interrupted run is not silently reused: prepare a new run and preserve the old artifacts.

Raw evidence and logs are private local artifacts, not automatically sanitized publication material. Scan any material you decide to share. Do not upload an entire run directory.

## Optional integration

Existing separate-checkout references or subtree integrations can be preserved. A new subtree integration is an explicit application setup choice, not part of installation. Link the application's agent instructions to this bundle only when setting up that application intentionally.

The pre-push installer remains experimental. It is not installed by these steps and is not a verified production trigger. See the [runtime guide](runtime/README.md) for its requirements and limitations.
