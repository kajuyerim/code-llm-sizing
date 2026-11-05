# Historical local evaluation

## Experiment v2 (5 November 2026)

v2 tests the merged runtime with two fixes: forks share their sweeper's prompt cache prefix (one role-free system prompt and output schema, roles as user messages), and maintenance agents run without MCP servers, whose asynchronous connection had changed the tool list between calls. A live check confirmed that every fork call reads the inherited history from the cache.

Each application (Maybe, Actual Budget, Linkwarden) replays the five pilot tasks back to back as one push. Each task belongs to one of three teammate personas per application with their own seniority and voice; personas describe goals rather than dictate solutions, ask questions, iterate, and raise every planted fact in their own words before committing. The pushes have six development sessions each and 53k to 96k characters of conversation, two to three times the pilot's per-application total. Every condition received the same base, head, sessions and cutoff. A blind reviewer model scored accepted records against the pilot ground truth, excluding facts that never came up (two in Maybe).

| Condition | Required facts | Partial | Optional | Traps | Cost per run | Wall time per run |
| --- | --- | --- | --- | --- | --- | --- |
| A, Sonnet 5.5 | 17 / 21 | 1 | 3 / 7 | 1 / 19 | $1.40 | 233 s |
| B, Sonnet 5.5 | 10 / 21 | 1 | 1 / 7 | 0 / 19 | $1.09 | 115 s |
| A, Haiku 5.5 | 13 / 21 | 6 | 3 / 7 | 4 / 19 | $0.99 | 597 s |
| B, Haiku 5.5 | 11 / 21 | 2 | 3 / 7 | 3 / 19 | $0.37 | 338 s |

With Sonnet the cost gap fell from +118% in the pilot to +28%, and A's cost per required fact found ($0.25) is below B's ($0.33). The sweeper averages $0.54 per run; forked specialists average $0.11 each against $0.16 for fresh ones, because they read the inherited history from the cache and need 3 to 6 turns instead of 12 to 15. Every sweeper read all six sessions, while B-Sonnet specialists read 2.2 of six on average and six of 18 read none. A takes about twice as long because the sweeper runs first. With Haiku, the sweeper reads raw for 40 to 75 turns and each fork re-reads that history on every turn, so A-Haiku costs 2.7 times B-Haiku.

One run per condition on three applications does not establish a general winner. The simulation harness, conversations, runs and the full report live outside this repository in the local evaluation workspace.

## Pilot (October 2026)


We evaluated three applications, Maybe, Actual Budget, and Linkwarden, with five checkpoints each, including P5. Each checkpoint has Claude A, Claude B, GPT A, and GPT B outputs: 60 outputs total. Development and conversations were generated once and frozen. GPT reused those source checkpoints, diffs, conversations, and initial knowledge.

Application source advances across checkpoints, but knowledge resets to the original baseline for each checkpoint. This is not cumulative knowledge evolution. A uses a completed sweeper session and actual specialist forks; B uses fresh specialist sessions. Both can read the developer-agent conversation. Actual P3 has five specialists; that count is case-specific.

Eligibility was checked against the delivered source, conversation, and knowledge baseline before candidate scoring. There are 20 required facts, six optional facts, and three clean quiet cases.

| Condition | Required full proposal hits | Required partials | Required applied hits | Optional hits |
| --- | --- | --- | --- | --- |
| Claude A | 10/20 | 5 | 11/20 | 4/6 |
| Claude B | 9/20 | 4 | 9/20 | 2/6 |
| GPT A | 5/20 | 6 | 5/20 | 1/6 |
| GPT B | 5/20 | 8 | 3/20 | 1/6 |

These are fact-coverage measures, not overall accuracy or percentages of successful runs. Accepted proposals and applied documents are separate measurements. Nine GPT runs retained writer tool-routing failures, two A and seven B. They affect applied results but do not explain every missed proposal. Maybe P5 GPT A required an infrastructure-only writer retry and has incomplete total workflow timing.

Archived configuration identifies Claude maintenance, simulated developer, and development-agent models as `claude-sonnet-5-5`. An Opus advisor field does not identify the simulated developer. GPT maintenance used `gpt-6-luna` with High reasoning. Eligibility and primary evaluation used `gpt-6.1-sol` with High reasoning. `gpt-6-astra`, High, reviewed seven flagged cases and 28 outputs with prior judgments visible. That secondary audit was not an independent blind rescore or human sign-off; original judgments were preserved.

Actual P4 contains an explicit, source-supported oxfmt instruction. It remains in the suite but outside strict quiet scoring, without an invented new required target. Clean quiet cases are Maybe P4, Linkwarden P4, and Linkwarden P5. Replaying maintenance preserves the conversation; regenerating it produces a new scenario.

Claude resource totals are client-side list-price estimates, not subscription invoices. GPT monetary cost is unavailable. Runtime environments, prompt wording, limits, cache accounting, and execution failures differ. One trial per condition does not establish statistical significance, a general A/B winner, provider superiority, application correctness, or production readiness.

The [Actual P3 walkthrough](walkthrough/README.md) follows a concrete conversation through proposals and written knowledge. The [provenance page](provenance.md) records its source and transformations. The complete external evaluation workspace is not bundled. The integrated runtime and unified prompts have only deterministic software verification here; these historical scores must not be attributed to the new configuration.

Future work includes repetitions, cumulative knowledge, broader retirement/consolidation tests, reliable writer-tool verification, more realistic single-developer conversations with paraphrases, and a possible single-agent `/learn` baseline. Semantic storage, synonyms, ontologies, and SQLite remain possibilities, not implemented features. SQLite alone does not establish semantic consolidation.
