# Agent definitions and experiment conventions

The runtime combines [shared rules](shared-rules.md), committed [run notes](../init.md), and each role's definition. Both strategies use the same selected responsibilities and raw evidence. The role files on this integration branch are unified from A's stricter definitions and are a new configuration, not the archived pilot prompts.

## Run stages

Collection freezes source refs, the knowledge baseline, and explicitly selected conversation sessions/cutoff. Plain code selects specialists. A then investigates with the [sweeper](sweeper.md) before specialist forks; B starts fresh specialists immediately. Shared checks validate proposals. The optional [cartographer](cartographer.md) proposes structure changes, and one [writer](writer.md) applies accepted knowledge locally.

The common strategy registry includes B with fresh sessions and A with literal SDK forks from a completed sweeper. The architecture and historical walkthrough explain both approaches.

## Initial specialist assignments

| Assignment | Definition | Knowledge target | Selection |
| --- | --- | --- | --- |
| Terminology | [Terminology maintainer](terminology-maintainer.md) | core/terminology.md | Always |
| Stack | [Stack maintainer](stack-maintainer.md) | core/tech-stack-standards.md | Always |
| Conventions | [Conventions maintainer](conventions-maintainer.md) | core/naming-conventions.md | Always |
| Pitfalls | [Pitfalls maintainer](pitfalls-maintainer.md) | core/pitfalls.md | Always |
| Firebase | [Tool maintainer](tool-maintainer.md) | tools/firebase/ | When relevant |
| Dataform | [Tool maintainer](tool-maintainer.md) | tools/dataform/ | When relevant |

Tool maintainers are instantiated from existing folders and selected with their frontmatter relevance hints. The actual roster is recorded. The five specialists in the Actual P3 walkthrough are a case-specific roster, not a fixed runtime count. Knowledge about tools is distinct from Read/Grep/Glob/Edit/Write capabilities available to an agent.

## Shared inputs and isolation

Preserve immutable source base/head, explicit diff, selected conversation sessions and cutoff, baseline revision, and declared settings. Keep message roles, order, references, exclusions, and truncation. Both strategies read the conversation. B receives no semantic sweeper summary, inherited session, A-generated memory, or A-produced knowledge. Keep evaluator answers and future evidence outside agent access.

A must record actual parent/child lineage and inheritance mechanism. A summary is not a literal fork. Its sweeper failure must skip specialists rather than turn the run into B. Count sweeper calls and inherited-resource accounting in A's totals. Keep raw usage alongside adjusted figures.

## Outputs

Use the [change record](../maintenance/core.md#change-record), including NO_CHANGE and NEEDS_REVIEW. Each specialist proposes changes only within its assignment. The application stays read-only. Unowned findings and handoffs do not expand write permissions. Structure and relevance-hint changes are human-review proposals.

The writer preserves frontmatter and writes only permitted knowledge paths. Publication is off by default; a successful writer can create a local knowledge commit. Inspect the actual patch separately from accepted proposals and writer claims. Run state, backlog, and knowledge branches are strategy-specific and outside the maintained knowledge folders.

Legacy evidence retains `products/`, `product:` scopes, and original role names. The current role is `tool-maintainer`; new targets use `tools/` and new tool scopes use `tool:<name>`. Archived results remain historical, not rewritten to look like outputs of this revision.
