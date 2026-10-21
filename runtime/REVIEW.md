# Static Implementation Review

Status: **implemented, not run or verified**, 21 October 2026. Review means source inspection and manual control-flow walkthroughs. No runtime imports, dependencies, hooks, model calls, executable mocks, test files, automated tests, or smoke runs were used.

## Inspection performed

- Parsed Python source with the standard-library AST parser without importing or executing runtime modules; inspected internal named imports.
- Inspected configuration fields, role tool lists, schemas, canonical-path boundaries, evidence quote resolution, and Markdown links.
- Compared SDK option names and hook shapes against official SDK 0.2.170 source and its declared bundled CLI 2.1.306. This does not establish live compatibility.
- Inspected local Git changes and writing conventions, including metadata preservation and the absence of em dashes in modified project text.

## Manual walkthroughs

| Case | Source path reviewed and intended behavior |
| --- | --- |
| Relevant supported update | Specialist supplies an exact row and resolving evidence; structural review admits it; successful writer output must match the row before commit. Semantic support still needs human review. |
| Irrelevant change | Role instructions call for NO_CHANGE; an all-NO_CHANGE run does not invoke the writer or create a PR. |
| Conversation-only definition | Session/message UUID and exact quote can support a developer definition without requiring a matching source identifier. |
| Rejected proposal or later correction | Role instructions require reading retained sessions through the cutoff; code preserves role and order but does not classify acceptance or supersession semantically. |
| Completion claim contradicted by source | Instructions require checking source, preserving disagreement, and deferring uncertainty. This model behavior has not been evaluated. |
| Missing conversation | No retained session marks the pack incomplete before any SDK session starts. |
| Failed sweeper or missing parent ID | Specialist scheduling stops; no fresh-session or summary fallback exists. |
| Fork isolation | Calls use the same completed parent with fork enabled; IDs must differ from parent and siblings. Actual inherited history and concurrent SDK behavior are unverified. |
| Invalid locator or fact ID | Path, quote, line, UUID, existing ID, prefix, and merge-membership checks reject the record. Conflicting fact operations are deferred. |
| Budget unavailable or exhausted | Full call allowances are reserved before launch; writer allowance is protected; skipped workers and unknown costs make the run incomplete. In-flight SDK requests may overshoot estimates. |
| Forbidden write or changed metadata | Tool guards deny out-of-scope paths before edits; final checks reject undeclared targets, protected frontmatter changes, unrelated fact rows, or unsuccessful writer output. |
| Publication or cleanup failure | Reports and artifacts retain failure details; commits remain local when publication fails; only complete runs advance conversation checkpoints. |

These are descriptions of source-level intent and inspected branches, not executed cases or measured results.

## Deferred verification and limits

Installation, imports against installed dependencies, authentication, structured-output delivery, parallel fork behavior, system-prompt replacement, inherited-history completeness, tool enforcement, Git worktree behavior, transcript compatibility, budget calibration, and publication all need a separately authorized live check. No claim of operational readiness follows from static parsing.

Transcript selection uses a coarse repository/time window. Tool results and thinking are filtered; older messages may be truncated; custom transcript or memory locations are not inferred. Auto memory is collected later than the conversation cutoff. Product hints may skip actual usage. These omissions are recorded where known, but full evidence coverage is not established.

The model remains responsible for interpreting evidence appropriately, and human review remains responsible for admitting knowledge. Secret scanning uses patterns and is incomplete. Locator resolution, schema validation, and exact row reproduction cannot establish semantic truth.

The fixed estimated budget may not cover every selected specialist plus sweeper, cartographer, and writer at their maximum allowances. Reports retain skipped work rather than claiming a complete inspection. Failed or interrupted runs require inspection before another attempt; ambiguous PR responses require checking the remote.

Issue #2 and issue #3 have not been edited or closed. No application fixtures, hidden evaluation answers, pilot results, comparison infrastructure, or imported implementation from another branch were added.
