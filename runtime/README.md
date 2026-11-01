# Runtime operations

Start with [setup](../setup.md) for installation and tests without credentials. The supported first-use path is a manual run against a separate application. This branch registers `fresh-specialists`; the dependent A PR adds `sweeper-first` to the same shared pipeline.

## Commands

| Command | Purpose |
| --- | --- |
| `contextops sweep --repo PATH --kb PATH --base REF --head REF --strategy MODE --session ID [--session ID] [--cutoff ISO_TIME]` | Freeze selected evidence and run locally. Real model calls occur. |
| `contextops run RUN_DIR` | Execute an unattempted prepared run with its recorded inputs. |
| `contextops install --kb PATH --repo PATH` | Explicitly install the experimental application pre-push hook. |
| `contextops hook REMOTE [URL]` | Internal experimental hook entry point. |

There is no implicit strategy. The checked-in `init.md` has `mode: null`; the manual command requires an explicit mode. Unknown or unimplemented modes fail before inference. Sessions come from Claude Code's local JSONL history. Missing/ambiguous sessions, invalid refs, dirty knowledge checkouts, and invalid settings fail before model calls. Cutoffs require a timezone and cannot be in the future.

The selected conversation is copied before inference, with a SHA-256 recorded in `run.json`. Later messages cannot change it. A changed frozen copy fails integrity validation. Explicit sessions include retained history through the cutoff, independently of the old last-run window. Tool results and thinking are excluded; truncation and sidechain policy are recorded. Legacy manifests remain readable, but cannot execute without the new frozen-input contract. Attempted runs are never overwritten; create a new attempt.

## Configuration and authentication

`init.md` supplies model, budgets, common instructions, role paths, and output settings. Commit configuration/role changes before running so the snapshot matches the settings you reviewed. Specialist tools are Read/Grep/Glob (Grep requires a specific file after Glob discovery); the writer additionally receives scoped Edit/Write. These SDK capabilities are unrelated to the `tools/` knowledge taxonomy.

Subscription mode uses the user's private Claude Code authentication and removes `ANTHROPIC_API_KEY` from the runtime process. API-key mode requires that environment variable. No credential value belongs in this repository or its chats, examples, logs, screenshots, or published evidence. No authentication is required for the deterministic tests. Inference uses the configured provider, not a local model.

`output.runs_dir` is the common parent, defaulting to `~/.contextops/runs`. The runtime always appends the strategy and run ID. `output.branch` must include `{strategy}` and `{run_id}`. `open_pr: false` is the default; no remote push occurs unless publication is explicitly enabled. A successful writer can create a local knowledge commit. Generated branches are never merged automatically.

## Outputs

| Artifact | Meaning |
| --- | --- |
| `run.json`, `conversation.json` | Frozen selections and normalized conversation with integrity hash |
| `pack/manifest.json`, `pack/diff/`, `pack/conversation/` | Evidence, source refs, selected sessions, and filtering notes |
| `workers/`, `review.json` | Raw specialist responses and accepted/deferred/rejected decisions |
| `proposals.json` | Optional cartographer suggestions, never automatically applied |
| `knowledge.patch` | Candidate or committed knowledge changes; inspect writer status |
| `report.md`, `metrics.json` | Outcomes, failures, and client-reported resource estimates |
| `started` | Prevents silently rerunning an attempted directory |

Cutoff state and unowned findings live under each strategy's directory. Raw evidence and run artifacts stay outside the repository. They are not guaranteed secret-free; the public credential scan is separate from the limited proposal validator. Do not publish raw directories.

## Experimental pre-push adapter

The hook source remains available but is not installed or production-verified by setup or tests. It requires an explicit committed `init.md` mode and application `contextops.sessions` configuration containing selected session IDs. It captures refs from Git, prepares evidence, and launches maintenance in the background. Preparation itself can delay the hook; background completion does not gate the push. A knowledge commit created afterward is not part of the original application push. The adapter skips failures and does not turn a missing conversation into a valid run.

## Known limits

- Claude Code history is an internal format. Deleted history, malformed entries, or filtered tool results may hide evidence.
- Relevance uses globs and keywords; unknown usage paths may require human updates to hints.
- Cost estimates are not billing. Concurrent calls and the writer can exceed the aggregate scheduling threshold.
- Reports include agent claims; deterministic locator checks do not prove semantic correctness. Review actual document changes.
- Tests exercise fake calls, permissions, and SDK option construction. They do not prove live provider behavior. No experiments were rerun for this integration.
- The separate historical GPT adapter is future Codex-backend work. It is not installed by this package.
