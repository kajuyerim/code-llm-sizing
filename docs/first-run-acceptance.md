# First-run acceptance

Status: implementation and credential-free verification are reviewable; live acceptance is pending. This is a verification checklist, not a completed experiment or a published user run.

## Software verification

The first-run tests initialize blank knowledge in disposable repositories, exercise A and optional B with fake agents, and inspect the actual local branch changes. They cover clean-start requirements, preserved original knowledge/history, links/configuration, unchanged source applications, no-change outcomes, invalid selections, deferred findings, budget exhaustion, and failed-writer candidate patches.

Run the checks in [setup](../setup.md#2-test-without-credentials). These checks use no private history or inference and do not establish live model quality or production hook behavior.

## Live acceptance, pending

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
