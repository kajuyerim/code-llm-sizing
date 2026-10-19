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
| `core/` | Shared terminology, stack standards, and naming conventions |
| `maintenance/` | Instructions for maintaining core and product knowledge |
| `products/` | Product-specific knowledge, starting with Firebase and Dataform |
| `agents/` | Sweeper and specialist role definitions |
| `skills/` | Reusable setup and GitHub issue creation procedures |

## First experiments

- **Sweeper, then delegation:** one agent examines all three evidence sources, then forks into 5–6 specialists with the gathered context.
- **Immediate delegation:** 5–6 specialists start fresh and inspect the same evidence sources themselves.

Both workflows only maintain documentation. Their [shared assignments and input contract](agents/README.md) keep the comparison consistent. The initial documents are ready for team review; the experiments have not been run.

Version 0.1 covers the foundation and manual pilots. A maintenance runtime and automated hook integration are future work. The setup walkthrough reports those integrations as pending rather than installing a simulated hook.

## Tracking

Milestone: [v0.1 - Structure & First tests](https://github.com/kajuyerim/code-llm-sizing/milestone/1).

| Issue | Work |
| --- | --- |
| [#1](https://github.com/kajuyerim/code-llm-sizing/issues/1) | Shared structure and setup guidance, awaiting team review |
| [#2](https://github.com/kajuyerim/code-llm-sizing/issues/2) | Prepare sweeper-first maintenance |
| [#3](https://github.com/kajuyerim/code-llm-sizing/issues/3) | Run the sweeper-first pilot |
| [#4](https://github.com/kajuyerim/code-llm-sizing/issues/4) | Prepare fresh-specialist maintenance |
| [#5](https://github.com/kajuyerim/code-llm-sizing/issues/5) | Run the fresh-specialist pilot and compare results |

The foundation is prepared locally. Issue #1 remains open for publication and review by Kerem and Barış; the four experiment issues remain open for later work.

## Team

- Kerem Haktan Kurt - 2021400150
- Barış Öksüz - 2021400099

**Advisor:** Assoc. Prof. Atay Özgövde
