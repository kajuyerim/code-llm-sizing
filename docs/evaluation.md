# Historical local evaluation

The 16 November report audit checked expected criterion IDs against all 533 development judge files for 367 evaluated sessions. Nine files omit 61 judgments: three feature-sequence files omit 20 and six persona files omit 41. Three additional team-learning sessions are separate. Original judgments are preserved. This verifies coverage and arithmetic, not the correctness of every model verdict. Rates below describe judged applicable checks; missing checks are explicitly unjudged, while recorded inapplicable checks remain excluded. Missing-judgment sensitivity bounds treat every omitted check as failing or passing in turn. They are not confidence intervals or rescored results. The team-rule and ready-made downstream studies have complete expected-ID coverage.

## Team decisions across repositories (15 November 2026)

This experiment tests the setup the repository recommends: one team knowledge repository shared by several applications. A tech lead persona asked for three small Linkwarden changes and said in passing that four rules apply to all of the team's repositories:

- no new third-party package for small things;
- no personal data or secrets in logs;
- explicit timeouts of at most 10 seconds on outbound calls, whose failure never breaks the user's action;
- Conventional Commits.

Each push ran maintenance through the real hook into the team repository, and the result was merged. All four rules were stored with `company` scope. Teammate personas then asked for five new changes in Actual Budget, Maybe and Linkwarden without stating any rule; the code of Actual Budget and Maybe does not show them. There were 40 sessions, with no knowledge or with the team knowledge attached, four repetitions each.

| | No knowledge | Team knowledge |
| --- | --- | --- |
| Decision checks, first commit | 60% (29/48) | 88% (42/48) |
| Decision checks, final | 71% | 88% |
| Code checks, first commit | 80% | 74% |
| Review rounds per session | 0.25 | 0.05 |

These pooled results include all three repositories, including Linkwarden where the rules were learned. The first-commit pooled difference is 27.1 percentage points; the original task-weighted difference is 30.0 points (p = 0.0002, permutation within task). Conventional Commits accounts for 12 of the 13 additional decision passes: 4/16 without knowledge against 16/16 with it. Other decision checks improve from 25/32 to 26/32. Privacy checks pass 11/12 without knowledge and 12/12 with it. The timeout checks were stricter than the learned rule. Every team-knowledge session set an explicit timeout, while no Maybe exchange-rate client without knowledge did. Review rounds are simulated teammate rounds. Limitations: five tasks, four repetitions, decisions designed for the test, and a result that rests mainly on one decision.

## Maintenance rerun and persona-driven development (15 November 2026)

**Rerun.** The four v2 conditions ran again on exactly the v2 inputs (same push, same six conversations per application, same seed knowledge, same budgets) with runtime `fbe12b8`. One blind judge scored the v3 and v2 runs together as eight anonymous labels; it scored v2 within one required fact of the v2 report.

| Run | Required facts | Traps | Noise or unsupported | Cost per run |
| --- | --- | --- | --- | --- |
| A, Sonnet: v2 / v3 | 16 / 16 of 21 | 1 / 0 of 19 | 6 / 2 | $1.40 / $1.42 |
| B, Sonnet: v2 / v3 | 9 / 8 of 21 | 0 / 0 | 2 / 0 | $1.09 / $0.92 |
| A, Haiku: v2 / v3 | 13 / 15 of 21 | 3 / 1 | 12 / 5 | $0.99 / $1.09 |
| B, Haiku: v2 / v3 | 10 / 11 of 21 | 2 / 3 | 9 / 11 | $0.37 / $0.54 |

The v3 A-Sonnet result contains 16 full and three partial required facts, zero predefined traps, eight supported extras, one noisy extra and one judge-flagged unsupported extra. Zero predefined traps does not mean zero wrong rules. These jointly rescored v2 counts differ from the original v2 scoring reported below. Costs are mean client-side list-price estimates, not invoices.

**Development with personas.** Each v3 result became a knowledge base for Claude Code (Sonnet 5.5), connected with `contextops attach`. Six new tasks (two per application) touched facts from the v2 conversations. A simulated teammate opened with a natural request, answered questions, and reviewed the diff after the commit (at most two review rounds). A blind judge scored the first commit and the final diff. There were 126 sessions in seven conditions, three repetitions each.

- The study did not demonstrate a first-commit improvement: observed fact rates were 64% to 73% with knowledge against 71% without. Original exploratory tests had p > 0.05; this does not establish equivalence, and some judgments are missing.
- Citation frequency was 22/36 sessions with the session-start digest versus 29/72 without it. This is a citation proxy, not proof of comprehensive reading or better development quality. Digest conditions were added after the first analysis.
- The hardest check (keep a data backfill manual) failed even when agents read and cited the matching entry, because nobody had said the decisive part in the conversations the knowledge was learned from.
- After simulated review, observed judged-applicable fact rates were about 90% to 94%; incomplete judgments prevent claiming that all conditions exceed 90% on their full checklists.

Affected fact rows are listed below. Explicitly inapplicable checks are excluded from the bounds.

| Stage and condition | Pass / fail / unjudged / inapplicable | Missing-judgment bounds |
| --- | --- | --- |
| First, none | 41 / 17 / 3 / 14 | 67.2%-72.1% |
| First, A Haiku | 41 / 20 / 2 / 12 | 65.1%-68.3% |
| Final, none | 59 / 4 / 2 / 10 | 90.8%-93.8% |
| Final, A Haiku | 58 / 5 / 2 / 10 | 89.2%-92.3% |
| Final, A Sonnet digest | 59 / 5 / 2 / 9 | 89.4%-92.4% |
| Final, B Sonnet digest | 53 / 6 / 4 / 12 | 84.1%-90.5% |

Benefits varied by task and available information. These studies do not establish that knowledge helps only when code is silent. The protocol, its amendment, and the raw sessions stay in the evaluation workspace. The [results page](../reports/2026-11-15-results/context-ops-results.html) shows the conversations, complete coverage disclosures, and retrieval diagnostics within this study.

## Feature-sequence experiment (15 November 2026)

This experiment runs the whole day-to-day loop: `contextops attach`, the pre-push hook, a maintenance run (A, Sonnet) on the pushed commits and the sessions since the last run, the result branch pushed to the knowledge remote, and a merge before the next feature. Each of three applications (Actual Budget, Linkwarden, Maybe) has a chain of three features developed in order in fresh Claude Code sessions (Sonnet 5.5). F1's prompt states two team decisions in passing (Linkwarden: also a commit-message convention), F2's prompt states two more, and F3's states none. Hidden checks on F2 and F3 test whether earlier decisions are followed. Every decision was chosen so that the existing code does not settle it.

Conditions, three repetitions each (81 features, 36 maintenance runs):

- none: no knowledge;
- repo: one empty knowledge repository per application (`scope: repository`);
- team: one empty knowledge repository shared by the three applications (`scope: team`).

The remotes were local bare repositories, and a simulated reviewer merged every result branch unchanged. A blind judge (Opus 5.5) scored 7 to 9 checks per feature from the diff and commit messages. The protocol was frozen before the runs.

| | none | repo | team |
| --- | --- | --- | --- |
| Earlier decisions followed (F2, F3) | 71.7% (43/60) | 58/58 judged; 2 unjudged; bounds 96.7%-100% | 100% (60/60) |
| Decisions stated in the same prompt | 34/34 judged; 5 unjudged; bounds 87.2%-100% | 37/37 judged; 2 unjudged; bounds 94.9%-100% | 100% (39/39) |
| Code-based checks | 89/98 judged; 7 unjudged; bounds 84.8%-91.4% | 94/102 judged; 3 unjudged; bounds 89.5%-92.4% | 90.5% (95/105) |
| Linkwarden's commit rule absent elsewhere | 100% (12/12) | 11/11 judged; 1 unjudged; bounds 91.7%-100% | 100% (12/12) |
| Development cost per feature | $0.164 | $0.190 | $0.196 |
| Maintenance per push | none | $0.41, 106 s | $0.39, 98 s |

Team knowledge passed all 60 carried checks; repository knowledge passed all 58 judged carried checks with two unjudged, versus 43/60 without knowledge. The original observed difference was about 29 points (permutation within application and feature, p < 0.001). That exploratory test uses incomplete returned judgments and does not account for dependence between linked features in evolving chains. Without knowledge, later features still followed decisions that the earlier code showed, such as Linkwarden's commit subjects. They lost the ones it shows weakly: Lookbook previews for new Maybe components (0 of 6), the optional mobile `auth` argument for new Linkwarden hooks (1 of 6), and Maybe's totals living in the model (1 of 3). The shared team repository scoped entries to their application (16 to 19 entries, no `company` entries); judged no-leak checks passed, with one repository-condition check unjudged.

Limitations:

- Team reached the observed ceiling; repository knowledge has two unjudged carried checks. The experiment does not establish a ranking between them.
- An agent working for the team designed the decisions and checks, and one model judged them.
- Each small push carried one short session, typically one commit. The measured $0.39-$0.41 and 98-106 seconds of maintenance do not establish typical costs for arbitrary pushes. Merges were automatic in the simulation, and the forge was local.
- In one chain, a decision was written into two documents.
- Most decisions were conventions inside one application (UI components, preference keys, hooks). The admission policy adopted afterwards ("What this knowledge keeps" in `init.md`) leaves such conventions out. The experiment shows that the loop carries decisions across sessions, not that these decisions belong in shared knowledge.

## Downstream comparison (14 November 2026)

This study asks whether knowledge maintained by Context Ops helps a development agent ([#10](https://github.com/kajuyerim/code-llm-sizing/issues/10)). It is separate from the A/B maintenance comparison below. Claude Code (Sonnet 5.5) implemented six feature tasks, two per application, on the v2 application heads under three original conditions and a post hoc B condition:

- none: no knowledge pointer;
- seed: the v2 baseline knowledge;
- maintained: the baseline plus the v2 A-Sonnet knowledge patch;
- maintained by B: the baseline plus the v2 B-Sonnet patch, added after the first three were analysed.

Each task and condition ran five times, 120 runs in total. Prompts were short teammate messages that never named the checked conventions. A blind model judge (Opus 5.5) scored 6 to 8 hidden review checks per task from the diff and commit messages; the checks were written before execution. The protocol, its three amendments, and the raw runs stay in the evaluation workspace.

| Condition | Checks passed | Completion (0 to 3) | Mean cost per task | Median time |
| --- | --- | --- | --- | --- |
| none | 78% | 2.33 | $0.202 | 44 s |
| seed | 77% | 2.37 | $0.224 | 42 s |
| maintained | 86% | 2.50 | $0.240 | 47 s |
| maintained by B (added later) | 81% | 2.40 | $0.233 | 41 s |

Maintained A knowledge improved pooled checks from 146/188 (77.7%) without knowledge to 161/188 (85.6%). Seed knowledge scored 146/190 (76.8%) and did not demonstrate a benefit. Original task-weighted contrasts were +8.2 points against none (p = 0.0209) and about +9 against seed (p = 0.001), using permutation within tasks. Routine-task checks improved from 82% to 97%, versus 74% to 76% for knowledge-task checks, so these data do not support an exclusively conversation-dependent explanation. The clearest individual case was the sync-server webhook task. All five A-maintained runs used `undici`'s `fetch` and mocked `undici` in tests, as decided in an earlier session; all ten none/seed runs used the global `fetch`.

Limitations:

- After the runs, three Maybe checks turned out to assume the wrong component namespace. Dropping them (post hoc) gives 83%, 83%, and 93%.
- One Actual Budget check about reports that must stay unchanged could not be confirmed from a diff, and it fell to 0% with maintained knowledge.
- The study covers six tasks and one development model, with knowledge learned from simulated developers.

Knowledge from B scored 152/188 (80.9%). The A-B pooled gap is 4.8 points; the original task-weighted gap is 6.1 points (p = 0.0129). B's original task-weighted gain over none was about 2 points (p = 0.58). This comparison observed lower performance with B's patch, without establishing a general causal relationship between maintenance coverage and development quality. The maintenance that produced A's patch cost $1.40 per application push, separately from development. Mean development cost rose from $0.202 to $0.240, median time from 44 to 47 seconds, and mean time from 75 to 96 seconds. Costs are client-side list-price estimates. The [midterm report](../reports/2026-11-18-midterm/context-ops-midterm.pdf) has the full tables.

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
