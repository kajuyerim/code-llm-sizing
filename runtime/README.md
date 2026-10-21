# Standalone Sweeper-First Runtime

Status: **implemented, not run or verified**. This is the independent Experiment A implementation on `feat/sweeper-first-runtime`, based on foundation commit `fdecc82`. No dependencies or hooks were installed, no agents or tests were executed, and no API charges were incurred during implementation. GitHub tracking remains unchanged.

Application code and evaluation fixtures belong in separate repositories. This package maintains only knowledge. It has no comparison mode or cross-experiment orchestration.

## Flow

```text
manual sweep, or application pre-push refs
  -> run manifest and separate application/knowledge worktrees
  -> raw evidence pack and deterministic worker roster
  -> sweeper reads broadly and completes successfully
  -> independent literal forks of that completed session
  -> specialist records and deterministic checks
  -> optional cartographer proposals, never applied
  -> writer, provenance, post-edit validation, local commit
  -> optional branch push and PR, never automatic merge
  -> local report, metrics, retained patch, worktree cleanup
```

The hook waits only for local configuration/ref capture and process dispatch. It does not wait for maintenance and its shell wrapper always exits successfully. Git may still reject or fail the subsequent push; a captured pre-push ref is push intent, not proof that the remote accepted it.

Four core workers always run: terminology, stack standards, naming conventions, and pitfalls. Firebase and Dataform workers are conditional on README path patterns or conversation keywords. A product without hints runs unconditionally. Selection is deterministic and happens before model calls.

## Configuration and dependencies

[init.md](../init.md) specifies the sole supported mode, `sweeper-first`, and [agent definitions](../agents/README.md). Role frontmatter declares name, description, tools, and optionally model. Instructions combine shared rules, run notes, and the active role. Unknown configuration keys and invalid budgets fail explicitly.

Python 3.10+, SHA-1 Git repositories, and POSIX local file locks are required. Dependencies declare Claude Agent SDK **0.2.170**, PyYAML 6.x, and jsonschema 4.x. The runtime requires that SDK's bundled Claude Code **2.1.306** and does not select an arbitrary globally installed CLI. Versions and resolved model names are recorded when available.

Defaults are `sonnet`, 30 turns per call, three concurrent specialists, USD 0.50 estimated allowance per call, and USD 3.00 estimated total. A writer allowance stays reserved while other calls run. Every launch reserves its full allowance. Skipped workers and exhausted or unavailable budgets make the run incomplete. SDK estimates can exceed a cap during a request; this is not a hard billing limit.

Only subscription authentication is supported. The dedicated runtime process removes API-key credentials before spawning SDK children and restores its own environment afterward. The invoking shell is unaffected. Alternate provider/base-URL overrides are refused, and there is no API-key fallback. Existing Claude Code login or a separately configured Claude Code OAuth token is required for a future run; subscription quota use remains possible.

## Commands for a later authorized setup

These commands are operational documentation. They were not executed as part of implementation. A manual sweep also invokes agents and may publish a PR by default.

Commit the runtime, configuration, and definitions before using the checkout: run snapshots come from the recorded knowledge HEAD, not uncommitted files. The active knowledge branch is recorded as the eventual PR base and should exist on origin before publishing. `open_pr: false` retains a validated commit locally and skips both pushing and PR creation.

```bash
python3 -m venv /path/to/contextops-venv
/path/to/contextops-venv/bin/pip install -e /path/to/code-llm-sizing/runtime

/path/to/contextops-venv/bin/contextops sweep \
  --repo /path/to/application --kb /path/to/code-llm-sizing \
  --base OLD_COMMIT --head NEW_COMMIT

# A separate, explicit installation action for a future application checkout:
/path/to/contextops-venv/bin/contextops install \
  --repo /path/to/application --kb /path/to/code-llm-sizing
```

| Command | Behavior |
| --- | --- |
| `contextops sweep --base REF [--head REF] [--repo PATH] [--kb PATH]` | Prepare an immutable commit range and run in the foreground. Head defaults to HEAD; repo defaults to cwd; kb can come from git config contextops.kb. Returns nonzero for an incomplete run. |
| `contextops install --repo PATH --kb PATH [--force]` | Write the actual application pre-push adapter and contextops.kb setting. Refuse shared core.hooksPath and symlink hooks. A foreign hook requires --force and a preserved backup. |
| `contextops hook REMOTE [URL]` | Read Git's local/remote ref names and SHAs from stdin and dispatch background runs. Ignore deletions. Errors do not abort the push. |
| `contextops run RUN_DIR` | Execute a prepared, never-attempted directory. Refuse overwriting prior status or evidence. |

A new remote ref uses the empty tree as base and records that the diff covers the entire head snapshot. An unavailable nonzero remote base fails instead of guessing another commit. The current command does not fetch missing source revisions automatically.

## Evidence and session inheritance

The pack contains source base/head references, the explicit diff and per-file patches, commit messages, normalized conversation, and memory copies. Source and knowledge worktrees are checked out at immutable recorded revisions.

Conversation collection scans matching local Claude Code JSONL files by repository and time window, preserving user/assistant roles, message UUIDs, order, and timestamps. The window begins at the last complete run's cutoff or base commit time. Sidechains default off. Meta records, tool results, and thinking are omitted; tool invocations retain a short target. Per-session character caps retain the newest whole messages. Counts of exclusions and truncation are recorded.

No retained conversation means an incomplete report with no model calls or publication. Session matching is coarse and not task-specific. Custom Claude project-directory encodings, long hashed directory names, worktree-specific transcript locations, and custom memory directories are not inferred. Missing or unsupported evidence is not silently replaced by a repository summary.

Repository instruction files come from head. Auto memory is copied at collection time, separately from the historical conversation cutoff. Its capture time and checksums are explicit; generated memory is not treated as an authoritative developer statement.

The sweeper returns structured findings and coverage. Every selected specialist then uses the same parent session ID with `fork_session=True`. The active specialist system prompt uses `snapshot: false` so role instructions can change while history is inherited. A failed sweeper, missing session ID, or reused child ID cannot become a fresh-session fallback. Parallel fork behavior remains unverified.

SDK settings, skills, plugins, external MCP connections, and auto memory are disabled for maintenance sessions. Original memory is available only as explicit evidence. Read/search tool traces and agent-reported coverage are retained separately; neither proves that all accessible material was read.

## Proposals and writing

The [change-record contract](../maintenance/core.md#change-record) uses stable IDs and `merge_ids`. ADD, UPDATE, and MERGE provide exact single-line Markdown table rows. Source evidence needs a path, starting line, and exact quote; diff, conversation, and memory locators resolve against the retained pack. Canonical paths reject traversal and symlinks. Existence and quote checks do not prove semantic support or policy authority.

Conflicts on the same fact are deferred. Handoffs are reported without another automatic agent pass. Unowned findings are retained per application/knowledge checkout; cartographer proposals need at least two distinct known finding IDs and are never applied.

Sweeper, specialists, and cartographer have only Read, Grep, and Glob. Writer additionally has Edit and Write. A pre-tool guard restricts paths before execution. Post-edit checks require a successful writer response, complete record accounting, declared target paths, exact accepted rows, stable unrelated fact rows, preserved frontmatter, valid ID transitions, resolvable links, and text checks.

The writer stage adds Evidence citations and generated-authorship history deterministically. It never changes human-verification metadata. It commits with Context Ops authorship and repository hooks disabled. Failed validation retains the patch without publishing. A partial run may retain a validated local commit, but only a complete run is eligible for automatic publication.

`gh` is required for publication. Missing gh, failed push, or failed PR creation is recorded while the local branch and artifacts remain available. Inspect publication.json and the remote before retrying: a failed response can be ambiguous. If no knowledge commit exists, structural and deferred proposals remain local rather than creating an empty PR.

## Artifacts and accounting

Default root: `~/.contextops/sweeper-first/runs/<run_id>/`.

| Artifact | Contents |
| --- | --- |
| run.json, config.json | Frozen refs, baseline, cutoff, paths, settings, and role instructions |
| pack/manifest.json, diff/, conversation/, memory/ | Raw retained evidence, locators, exclusions, capture times, checksums |
| workers.json, sweeper.json, workers/*.json | Roster, raw outputs, parent/child IDs, coverage, reads, denials, failures |
| handoff.json | Literal fork mechanism and child statuses |
| review.json, accepted.json | Accepted, deferred, rejected, NO_CHANGE, handoffs, and unowned findings |
| cartographer.json, proposals.json | Optional raw structural proposals and checked reportable proposals |
| writer.json, publication.json | Writer accounting, publication outcome, and errors |
| knowledge.patch, uncommitted/ | Actual retained tracked patch and uncommitted new files on failure |
| metrics.json, status.json, report.md | Raw/derived resources, completion status, and human report |
| run.log, pr-body.md | Background output and submitted PR body when applicable |

Run and application-state locks prevent concurrent attempts from racing checkpoints. A concurrent push gets an incomplete local report rather than silently sharing a running conversation window. Attempted directories are not overwritten; prepare a new run for another execution. Worktrees are cleaned up; committed branches remain. Interrupted-process cleanup is not automatically recovered.

Under the pinned bundled CLI, fork result totals restore prior session spend. Each child's incremental estimate subtracts the completed sweeper's raw total; the sweeper is counted once. New processing of inherited history still costs tokens and remains included. Raw per-model totals and derived deltas are both retained. Missing or inconsistent measurements stay unavailable and stop new launches. Wall-clock run time is separate from summed SDK and call durations. All costs are client-side estimates, not billing statements.

## References and pending work

SDK interfaces and version behavior were inspected against [Python reference](https://code.claude.com/docs/en/agent-sdk/python), [session documentation](https://code.claude.com/docs/en/agent-sdk/sessions), [cost accounting](https://code.claude.com/docs/en/agent-sdk/cost-tracking), and [pinned SDK source](https://github.com/anthropics/claude-agent-sdk-python/tree/dd27b703647a4f8989ab656f00c85f98090a60fd). Documentation inspection is not runtime verification.

Read [REVIEW.md](REVIEW.md) for static review coverage. [Issue #2](https://github.com/kajuyerim/code-llm-sizing/issues/2) remains preparation tracking and [issue #3](https://github.com/kajuyerim/code-llm-sizing/issues/3) remains future pilot tracking. No human review, pilot execution, evaluation results, working hook, or successful session fork is claimed.
