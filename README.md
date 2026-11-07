# Context Ops

Context Ops is a CMPE 492 senior project at Boğaziçi University studying how agents maintain shared knowledge as software evolves. After application development, maintenance reads a separate application's source revision, Git diff, and developer-agent conversation, then proposes updates to this knowledge repository.

## Start here

1. **Understand:** read [How Our Knowledge Maintenance System Works](docs/walkthrough/README.md). Download its [interactive HTML](docs/walkthrough/index.html) and open it locally for original evidence and A/B comparisons.
2. **Install and test:** follow [setup](setup.md). Deterministic tests use fake responses and temporary repositories, with no account, model call, or API charge.
3. **Run on your application:** select a strategy, committed revision range, and Claude Code conversation sessions. Real runs use your own private Claude authentication.
4. **Inspect:** review the local proposals, knowledge patch, report, and knowledge branch before deciding what to keep.

## Quickstart

You need Python 3.11 or newer, Git, a Claude Code login, and an application repository of your own that you have worked on with Claude Code.

```sh
git clone https://github.com/kajuyerim/code-llm-sizing.git && cd code-llm-sizing
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r runtime/requirements-lock.txt && python -m pip install --no-deps -e runtime
python -m unittest discover -s runtime/tests        # no account, no model calls

contextops sessions --repo /path/to/your/app        # pick the Claude Code sessions to learn from
contextops sweep --repo /path/to/your/app --kb . \
  --base <commit before the work> --head <commit after it> \
  --strategy sweeper-first --session <session id>   # real model calls; output stays local
```

The last line prints a report path. The proposed knowledge changes are in `knowledge.patch` next to it and on a local branch of this checkout. Nothing is pushed or merged. [Setup](setup.md) covers each step in detail.

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
