# Context Ops

Context Ops is a CMPE 492 senior project at Boğaziçi University studying how agents maintain shared knowledge as software evolves. After application development, maintenance reads a separate application's source revision, Git diff, and developer-agent conversation, then proposes updates to this knowledge repository.

## Start here

1. **Understand:** read [How Our Knowledge Maintenance System Works](docs/walkthrough/README.md). Download its [interactive HTML](docs/walkthrough/index.html) and open it locally for original evidence and A/B comparisons.
2. **Install and test:** follow [setup](setup.md). Deterministic tests use fake responses and temporary repositories, with no account, model call, or API charge.
3. **Run on your application:** select a strategy, committed revision range, and Claude Code conversation sessions. Real runs use your own private Claude authentication.
4. **Inspect:** review the local proposals, knowledge patch, report, and knowledge branch before deciding what to keep.

## Two ways to acquire context

| Strategy | How specialists start |
| --- | --- |
| A: sweeper first | A sweeper investigates the original evidence; specialists independently fork its completed session. |
| B: fresh specialists | Specialists start fresh and inspect the same original evidence themselves. |

Both maintain documentation only, use equivalent responsibilities and common checks, and keep independent output state. Four core specialists always run; tool specialists are selected by relevance. The [architecture](docs/architecture.md) explains the boundaries and actual call flow.

Both **A, `sweeper-first`**, and **B, `fresh-specialists`**, are available through the shared Claude runtime. There is no default winner or implicit strategy choice.

## Repository layout

| Area | Responsibility |
| --- | --- |
| `core/` | Terminology, stack standards, naming conventions, and pitfalls |
| `tools/` | Knowledge about technologies, initially Firebase and Dataform |
| `maintenance/` | Procedures for maintaining core and tool knowledge |
| `agents/` | Shared role definitions, assignments, sweeper, and writer |
| `skills/` | Reusable setup and issue-creation procedures |
| `docs/` | Walkthrough, architecture, evaluation, and provenance |
| `runtime/` | Shared Claude runtime, operational guide, and tests |
| `init.md` | Common run settings and instructions |

[Knowledge index](index.md) · [Repository instructions](AGENTS.md) · [Change history](log.md)

`tools/` replaces the former `products/` folder. These are knowledge areas, not executable agent tools. Application sources, evaluation fixtures, and private run artifacts stay outside this repository. Firebase/Dataform folders do not imply application usage or company policy.

## Evidence and current status

The [evaluation summary](docs/evaluation.md) covers 60 archived maintenance outputs from three applications and five checkpoints. It separates proposals from applied documents and records execution limitations. The GPT results came from a separate evaluation adapter, not the Claude backend shipped here. The integrated code and unified prompts form a new configuration and have not been evaluated by rerunning those experiments.

The public checks use no model inference. Real model integration and the optional pre-push adapter still require separate verification. Publication is disabled by default; the runtime can create a local knowledge commit, but does not merge automatically.

## Tracking

[Milestone v0.1](https://github.com/kajuyerim/code-llm-sizing/milestone/1) and issues [#1](https://github.com/kajuyerim/code-llm-sizing/issues/1), [#2](https://github.com/kajuyerim/code-llm-sizing/issues/2), [#3](https://github.com/kajuyerim/code-llm-sizing/issues/3), [#4](https://github.com/kajuyerim/code-llm-sizing/issues/4), [#5](https://github.com/kajuyerim/code-llm-sizing/issues/5) predate the completed pilots. They remain open for reconciliation and human review; publication of this code does not complete their checkboxes.

## Team

- Kerem Haktan Kurt - 2021400150
- Barış Öksüz - 2021400099

**Advisor:** Assoc. Prof. Atay Özgövde

The historical repository name remains `code-llm-sizing` until a replacement is selected.
