# First-run acceptance

Status: implementation and credential-free verification are reviewable. Live acceptance runs on the public [first-run demo](demo/README.md) are recorded below, the latest at revision `b20f3f9`; it used simulated development conversations, so acceptance on a team's own application and sessions is still open.

## Software verification

The first-run tests initialize blank knowledge in disposable repositories, exercise A and optional B with fake agents, and inspect the actual local branch changes. They cover clean-start requirements, preserved original knowledge/history, links/configuration, unchanged source applications, no-change outcomes, invalid selections, deferred findings, budget exhaustion, and failed-writer candidate patches.

Run the checks in [setup](../setup.md#2-test-without-credentials). These checks use no private history or inference and do not establish live model quality or production hook behavior.

## Live acceptance checklist

Use a clean clone of the implementation revision and a separately selected application that already has committed development changes and real local Claude Code development sessions. Obtain authorization for this specific live run and its model/budget. Follow the README prompt and [setup skill](../skills/setup-shared-knowledge/SKILL.md) without unpublished team-only instructions.

Record:

- Implementation revision, Python/runtime versions, platform, and installation outcome.
- Source base/head, knowledge baseline, strategy, selected session IDs, cutoff, and normalized conversation hash.
- Model/settings, configured budgets, actual worker roster, filtering or truncation.
- Wall-clock start/end and elapsed time, estimated cost, and any unavailable measurements. Agent-duration sums are not elapsed wall time.
- The initial empty knowledge, accepted/deferred/rejected records, actual patch and committed result, and the review commands.
- Failures, manual interventions, discrepancies between proposals and written documents, and unresolved limitations.

Acceptance requires supported knowledge to appear in the actual committed documents for a relevant selected development change. A legitimate no-change run is valid runtime behavior but does not demonstrate the requested template-to-populated result. Preserve it and choose any additional run deliberately, without inventing facts or silently discarding failures.

Keep application sources, raw conversations, credentials, and full run directories outside the knowledge repository. Share only explicitly selected, sanitized evidence. Mark generated knowledge as awaiting human review. Do not claim this checklist is complete until the evidence exists.

## Live acceptance record 1 (14 November 2026, `caf4bdb`)

| Item | Value |
| --- | --- |
| Implementation | Branch `feat/first-run-demo` at `caf4bdb` (PR #13 at `7976024` plus `export-session` and `import-session`), cloned from a local checkout before it was pushed |
| Platform | macOS 27.0.1 on arm64, Python 3.13.14, Claude Agent SDK from `runtime/requirements-lock.txt` |
| Installation and checks | Lock-file install succeeded; 39 deterministic tests passed |
| Application | [Demo inputs](demo/README.md): upstream actualbudget/actual `d9d15c12` plus the eight demo commits. The run applied them from a Git bundle; the published patch series reproduces the same head tree (`f53804376c1c`), with different commit IDs |
| Source range | base `c9ec8e97da4d8eb96630fee0f7716389c8a061f5`, head `8cece049fa39354313e70b8719c958b5d16755d8` (seven development commits) |
| Knowledge baseline | `2451dfaada532b3b43fba95eac0ae26d86f237fa`: `contextops init --branch knowledge/actual-demo`, committed without edits |
| Sessions | Six imported sessions (`6866729d`, `70de19bb`, `b44d114c`, `d34fc234`, `de720aee`, `f57650bf`), cutoff `2026-11-05T18:40:03Z`, conversation SHA-256 `9a747bce1dd33368579c427c203e23ef3e3eda788c4535cda6009baa76001720` |
| Model and limits | `claude-sonnet-5-5`; checked-in budgets (1.5 USD per agent, 10 USD per run, 30 turns, 3 parallel) |
| Roster | Sweeper, then forks for terminology, stack, conventions, and pitfalls; Firebase and Dataform maintainers skipped as irrelevant; writer |
| Wall clock | 10:14:50 to 10:18:49 UTC, 3 min 59 s |
| Estimated cost | $1.01 (sweeper $0.44, four forks $0.41, writer $0.16) |
| Outcome | Knowledge committed on `contextops/sweeper-first/20261114-101450-8cece04-3374e54c`; 10 accepted, 0 deferred, 1 rejected |
| Written documents | `core/terminology.md` (2 entries), `core/tech-stack-standards.md` (3), `core/pitfalls.md` (5), `log.md`; the actual patch is [result.patch](demo/actual/result.patch) |

What the run learned matches decisions stated in the sessions: amounts are stored at x100 for every currency, the sync server imports `fetch` from `undici`, report range validation compares normalized dates, snapdom replaced html-to-image, and the quarter key is the quarter's first month.

Discrepancies and limitations found in this run:

- A supported convention was lost. The conventions maintainer proposed that commit messages start with `[AI]`, citing two developer messages and `diff/commits.txt`. Review rejects a record when any locator fails to resolve, and `diff/commits.txt` is not accepted as a diff path, so the whole record was rejected and `core/naming-conventions.md` stayed empty.
- Fact IDs are inconsistent: the writer used `STACK-001` and `TERM-001` but `PIT001`. The empty template shows the prefix but no example, and the run notes do not state the hyphen.
- Handoffs are reported but not acted on. The conventions maintainer handed typing rules (`satisfies` over `as`, no `@ts-strict-ignore`) and the release note requirement to the stack document, but forks run in parallel, so no specialist picked them up.
- The developer side of the sessions was simulated, and this is a single run.

These three problems, and inconsistent application scopes seen in a later run, were fixed in `43888a7` and `b20f3f9`:

- Review drops only unresolvable locators and accepts `diff/commits.txt`.
- Handoffs reach their owner in one extra turn on a fork of its own session.
- The run notes and empty templates state the ID format.
- Specialists are told to scope facts as `app:<checkout folder name>`.

## Live acceptance record 2 (14 November 2026, `b20f3f9`)

Same platform, application, range, sessions, cutoff, conversation hash, model, and budgets as record 1. A clean clone of `feat/first-run-demo` at `b20f3f9` was installed from the lock file; 42 tests passed.

| Item | Value |
| --- | --- |
| Knowledge baseline | `ce001cde3bedc6987b2e790aa75b07fd899abf4e`, from `contextops init`, committed without edits |
| Roster | Sweeper, then forks for terminology, stack, conventions, and pitfalls; Firebase and Dataform skipped; no handoffs were sent; writer |
| Wall clock | 20:27:10 to 20:32:08 UTC, 4 min 58 s |
| Estimated cost | $1.35 (sweeper $0.66, four forks $0.50, writer $0.19) |
| Outcome | Knowledge committed on `contextops/sweeper-first/20261114-202710-8cece04-ab77e26d`; 15 accepted, 1 deferred, 0 rejected |
| Written documents | `core/naming-conventions.md` (3 entries), `core/tech-stack-standards.md` (5), `core/pitfalls.md` (5), `core/terminology.md` (2), `log.md`; the actual patch is [result.patch](demo/actual/result.patch) |

All fifteen entries use `app:actual` and hyphenated IDs. The naming document now holds the `[AI]` commit prefix, the release note requirement, and one component per file. Two of these records had cited `diff/files.txt`, which is not a diff path. Review dropped that locator and kept the records on their conversation evidence, where record 1's rules would have rejected them.

An intermediate run at `43888a7` exercised the handoff pass:

- The conventions specialist handed the `ts-strict-ignore` rule to the stack document.
- The stack specialist's extra turn added it as `STACK-004`, for $0.03.
- The run cost $0.72 and wrote 14 entries.

A strategy B run from the same empty baseline wrote 3 entries for $0.50.

Single runs on simulated sessions; the remaining limitation is acceptance on a team's own application.
