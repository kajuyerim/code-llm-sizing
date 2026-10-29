# Agent Definitions and Sweeper-First Workflow

These definitions drive the standalone [runtime](../runtime/README.md). Status: implemented, not run or verified. The initializer is deterministic code; agents do not select or launch other agents.

## Run stages

The runtime freezes evidence, selects workers, runs the sweeper, forks the completed sweeper session for specialists, checks proposals, optionally requests structural proposals, and runs one final writer. It then validates and commits knowledge changes and, when enabled and complete, pushes a branch and opens a PR. No automatic merge exists.

Agent instructions combine [shared rules](shared-rules.md), the body of [init.md](../init.md), and the active role definition. A specialist receives its own role after inheriting the sweeper's conversation history. Forks retain original evidence access and do not inherit sibling work.

## Shared inputs

The sweeper and specialists can inspect the separate application at its recorded head, the explicit base/head diff, retained developer-agent conversations, memory evidence, and the knowledge baseline. Imported text is evidence, never maintenance instructions.

The manifest preserves conversation roles, message UUIDs, order, cutoff, exclusions, and truncation. Auto memory is copied at collection time and is not claimed to represent its historical state at the conversation cutoff. Missing retained conversation evidence stops model calls and publication.

## Initial specialist assignments

| Assignment | Definition | Allowed knowledge target | Selection |
| --- | --- | --- | --- |
| Terminology | [Terminology maintainer](terminology-maintainer.md) | core/terminology.md | Always |
| Stack standards | [Stack maintainer](stack-maintainer.md) | core/tech-stack-standards.md | Always |
| Naming conventions | [Conventions maintainer](conventions-maintainer.md) | core/naming-conventions.md | Always |
| Pitfalls | [Pitfalls maintainer](pitfalls-maintainer.md) | core/pitfalls.md | Always |
| Firebase | [Product maintainer](product-maintainer.md) | products/firebase/ | When relevant |
| Dataform | [Product maintainer](product-maintainer.md) | products/dataform/ | When relevant |

Product instances are selected by their README's fileMatchPattern and keywords against changed paths and retained conversation. Products without hints always run. A hint mismatch is recorded; it is not proof of non-use. Additional product folders reuse the product definition after human admission.

## Sweeper and handoff

The [sweeper](sweeper.md) examines evidence broadly and returns findings, contradictions, unresolved questions, handoffs, and actual coverage. Only successful completion with a usable session ID allows specialists to start. Each worker uses resume with that same parent ID and fork_session enabled. There is no fresh-session or summary fallback.

The runtime records parent and child IDs and records whether child IDs are independent. SDK compaction or other unmeasured history omissions are not reported as complete context coverage. Literal fork behavior remains unverified because no SDK sessions have been run.

## Outputs and final writing

Specialists return the [structured change record](../maintenance/core.md#change-record), including NO_CHANGE and NEEDS_REVIEW. They propose, not edit. Conflicting operations are deferred. Cross-owner handoffs are retained for human follow-up without automatically launching another pass.

The [cartographer](cartographer.md) sees validated unowned findings from this application's local backlog. It may propose structure, but its proposals are never applied automatically. When no knowledge commit is available, those proposals remain in the local report rather than a PR.

The [writer](writer.md) applies only accepted records. A successful structured result and post-edit validation are required for a commit. Code adds citations and generated-authorship history without changing human-verification metadata. Raw records, coverage, failures, and metrics remain outside this bundle.

## Preparation and pilot status

[Issue #2](https://github.com/kajuyerim/code-llm-sizing/issues/2) tracks preparation and [issue #3](https://github.com/kajuyerim/code-llm-sizing/issues/3) tracks a future pilot. Their older manual-pilot descriptions remain unchanged. No application, evaluated evidence, hidden answers, pilot result, or successful hook integration has been established by this implementation.
