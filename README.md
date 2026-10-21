# Context Ops Shared Knowledge

A CMPE 492 senior project at Boğaziçi University studying how to maintain shared knowledge as software evolves. This repository is the knowledge destination for terminology, stack standards, conventions, and reusable development guidance. Its current repository name, `code-llm-sizing`, will change in the future.

Application code lives in separate repositories. After development, a local pre-push workflow will inspect the application repository, its Git diff, and the conversation between the developer and the local agent to maintain this knowledge base.

## Start here

- [Knowledge index](index.md): core guidance, product knowledge, maintenance guides, agent definitions, and skills.
- [Setup walkthrough](setup.md): connect an existing application to this bundle and prepare manual maintenance.
- [Repository instructions](AGENTS.md): scope and editing rules.
- [Change history](log.md): changes to the knowledge bundle.

## Repository layout

| Folder | Contents |
| --- | --- |
| `core/` | Shared terminology, stack standards, naming conventions, and pitfalls |
| `maintenance/` | Instructions for maintaining core and product knowledge |
| `products/` | Product-specific knowledge, starting with Firebase and Dataform |
| `agents/` | Sweeper, specialist, cartographer, and writer definitions |
| `init.md` | Run configuration and notes |
| `runtime/` | Standalone sweeper-first source and documentation |
| `skills/` | Reusable setup and GitHub issue creation procedures |

## Sweeper-first implementation

Status: **implemented, not run or verified**. This feature branch implements Experiment A independently from foundation commit fdecc82. One sweeper inspects frozen source, diff, conversation, and memory evidence; selected specialists inherit its completed session through literal SDK forks.

The six [assignments and input contract](agents/README.md) cover terminology, stack standards, naming, pitfalls, Firebase, and Dataform. Product roles run when configured relevance hints match. Specialists propose changes; one writer edits knowledge. Application development is outside this workflow.

The [runtime guide](runtime/README.md) documents the manual command, background pre-push adapter, evidence collection, validation, budgets, artifacts, and PR publication code. No dependencies or hooks were installed, no agents or tests were run, and no API charges were incurred during implementation. Live behavior and pilot evaluation remain pending. Read the [static review](runtime/REVIEW.md) for limitations.

## Tracking

Milestone: [v0.1 - Structure & First tests](https://github.com/kajuyerim/code-llm-sizing/milestone/1).

| Issue | Work |
| --- | --- |
| [#1](https://github.com/kajuyerim/code-llm-sizing/issues/1) | Shared structure and setup guidance, awaiting team review |
| [#2](https://github.com/kajuyerim/code-llm-sizing/issues/2) | Prepare sweeper-first maintenance |
| [#3](https://github.com/kajuyerim/code-llm-sizing/issues/3) | Run the sweeper-first pilot |
| [#4](https://github.com/kajuyerim/code-llm-sizing/issues/4) | Prepare fresh-specialist maintenance |
| [#5](https://github.com/kajuyerim/code-llm-sizing/issues/5) | Run the fresh-specialist pilot and compare results |

Issue #1 still records foundation review. Issue #2 tracks preparation, and issue #3 tracks future pilot execution. The issue descriptions predate this runtime work; no issue states, assignments, or review checkboxes were changed. This implementation adds no comparison infrastructure.

## Team

- Kerem Haktan Kurt - 2021400150
- Barış Öksüz - 2021400099

**Advisor:** Assoc. Prof. Atay Özgövde
