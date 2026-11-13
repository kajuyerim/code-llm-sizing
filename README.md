# Context Ops

Context Ops is a CMPE 492 senior project at Boğaziçi University studying how agents maintain shared knowledge as software evolves. After application development, maintenance reads a separate application's source revision, Git diff, and developer-agent conversation, then proposes updates to this knowledge repository.

## Set up with your agent

Clone this repository into a directory separate from your application, then open the clone in your coding agent:

```sh
git clone https://github.com/kajuyerim/code-llm-sizing.git
cd code-llm-sizing
```

You need **Python 3.11+, Git, private Claude authentication, and an existing application with committed development changes and local Claude Code development sessions**. Your setup agent can be any coding agent; maintenance currently uses the Claude backend and Claude Code history. Inference runs on the configured Claude service.

Give your agent this prompt:

> Read this repository’s README and setup skill. Configure Context Ops for my existing application, prepare an empty knowledge branch, run the sweeper-first workflow using my relevant Claude Code development sessions, and show me the resulting knowledge changes. Ask for missing inputs and keep the result local for review.

The [setup skill](skills/setup-shared-knowledge/SKILL.md) is the authoritative procedure. It helps your agent select the application, committed range and sessions, prepare blank knowledge on a new local branch, configure and commit the baseline, and run **A, sweeper first**. The setup agent invokes Context Ops; the maintenance runtime writes learned knowledge. Existing installations reuse their accepted knowledge rather than resetting it.

A successful writer creates a local result branch. The command shows changed files, the report and patch, and Git commands to review and open that branch. Your starting branch remains selected. Some runs correctly produce no changes; incomplete runs and candidate patches are identified. Nothing is pushed or merged by the default configuration.

## Manual setup and evidence

Follow [setup](setup.md) for the equivalent manual commands, authentication details, troubleshooting, and optional B execution. Installation and deterministic tests need no model account or inference; running maintenance uses your private Claude authentication.

For an explanation of the system, read [How Our Knowledge Maintenance System Works](docs/walkthrough/README.md), or download the [interactive walkthrough](docs/walkthrough/index.html) and open it locally. These are historical evaluation evidence. The new first-run path has credential-free software checks; a separately authorized live acceptance run remains [pending](docs/first-run-acceptance.md).

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

Both strategies and the shared runtime are merged into `master` through [PR #7](https://github.com/kajuyerim/code-llm-sizing/pull/7) and [PR #8](https://github.com/kajuyerim/code-llm-sizing/pull/8). [PR #9](https://github.com/kajuyerim/code-llm-sizing/pull/9) adds fork cache reuse, MCP-free maintenance execution, conversation-session discovery, and the v2 evaluation summary.

**Experiment v2 (5 November 2026).** Three applications, each replayed as one long push of five tasks done by three simulated teammates (18 sessions, 53k to 96k characters of conversation per push), maintained by A and B with Sonnet 5.5 and Haiku 5.5. There was one run per application and condition. A blind reviewer model scored accepted proposals against 21 required facts across the three applications; final writer fidelity was not scored.

| Condition | Required facts found | Traps | Cost per run | Wall time per run |
| --- | --- | --- | --- | --- |
| A, Sonnet | 17 / 21 | 1 / 19 | $1.40 | 3m 53s |
| B, Sonnet | 10 / 21 | 0 / 19 | $1.09 | 1m 55s |
| A, Haiku | 13 / 21 | 4 / 19 | $0.99 | 9m 57s |
| B, Haiku | 11 / 21 | 3 / 19 | $0.37 | 5m 38s |

Cost and wall time are averages per run; costs are client-side list-price estimates, not invoices. In these runs, A's forked specialists were cheaper than fresh specialists, while the sweeper added cost and latency. B's incomplete conversation reading and search friction are relevant to the observed coverage difference. Changed conversations and configuration prevent attributing the difference from the October pilot solely to caching. These limited trials do not establish a general winner. See [evaluation](docs/evaluation.md) for method and limits.

**October pilot.** The [evaluation summary](docs/evaluation.md) also covers 60 archived maintenance outputs from three applications and five checkpoints. It separates proposals from applied documents and records execution limitations. Knowledge reset to the original baseline at each checkpoint, so this was not cumulative knowledge evolution. The GPT results came from a separate evaluation adapter, not a supported backend in this package. V2 is a separate experiment, not a rerun of the October conditions.

The public automated checks use no model inference. PR #9 separately records live fork-cache verification and v2 runs; these do not establish production readiness. The optional pre-push adapter remains experimental and unverified in production. Publication is disabled by default; the runtime can create a local knowledge commit, but does not merge automatically.

## Tracking

Issues [#1](https://github.com/kajuyerim/code-llm-sizing/issues/1), [#2](https://github.com/kajuyerim/code-llm-sizing/issues/2), [#3](https://github.com/kajuyerim/code-llm-sizing/issues/3), [#4](https://github.com/kajuyerim/code-llm-sizing/issues/4), and [#5](https://github.com/kajuyerim/code-llm-sizing/issues/5), grouped under [milestone v0.1](https://github.com/kajuyerim/code-llm-sizing/milestone/1), are closed for their delivered foundation, preparation, and exploratory pilot scopes. Their closing comments preserve the evidence and limitations; closure does not imply unrecorded human-review sign-offs.

The immediate priorities from the 6 November meeting are:

- [#10: Evaluate development with and without Context Ops knowledge](https://github.com/kajuyerim/code-llm-sizing/issues/10). Prepare a controlled comparison of quality, cost, time, and clarification rounds on the same feature task, without putting the tested knowledge into the task prompt.
- [#11: Prepare the midterm report and report index](https://github.com/kajuyerim/code-llm-sizing/issues/11). Explain completed work, results, limitations, and planned research, and make current and previous reports easy to find.
- [#12: Deliver a reproducible template-to-populated-knowledge demo](https://github.com/kajuyerim/code-llm-sizing/issues/12). Show a clean starting knowledge state, a manual run against a separate application, and the actual written result.

These are planned deliverables. The downstream comparison studies whether generated knowledge helps application development; A/B maintenance evaluation studies how that knowledge is maintained. Application development remains outside the knowledge repository and outside maintenance-agent responsibilities.

[#6: Codex runtime backend](https://github.com/kajuyerim/code-llm-sizing/issues/6) remains separate future work. The current package supports Claude; historical GPT evaluation results do not establish an installable Codex backend.

## Team

- Kerem Haktan Kurt - 2021400150
- Barış Öksüz - 2021400099

**Advisor:** Assoc. Prof. Atay Özgövde

The historical repository name remains `code-llm-sizing` until a replacement is selected.
