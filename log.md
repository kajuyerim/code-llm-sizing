# Knowledge Change History

## 2026-11-01

- Renamed the current products knowledge area to tools, including role, maintenance guide, routing, scopes, and writer permissions. Historical evidence retains its original paths and labels.
- Added the approved English walkthrough as a path-sanitized derivative, an English Markdown companion, architecture, evaluation, provenance, and public setup guidance.
- Reconciled shared specialist definitions and made strategy/session selection explicit. Conversations are frozen before inference, and state is separated by strategy.
- Added deterministic credential-free checks and publication scans. The integrated configuration has not been evaluated by rerunning historical experiments; the production hook remains unverified.
- This branch exposes fresh specialists. Sweeper-first integration is a dependent PR. Existing issues and human review checkboxes remain unchanged.

The dated entries below describe their implementation-time state. Completed historical pilot evidence is summarized in docs/evaluation.md.

## 2026-10-20

- Added `init.md` as the run configuration and `runtime/`, a Python orchestrator on the Claude Agent SDK with a background pre-push hook. Experiment B runs as the `fresh-specialists` mode. The runtime has not yet been run.
- Added shared rules for agents, a pitfalls maintainer, a cartographer that proposes new documents from unowned findings, and a writer that applies accepted records on a branch.
- Added frontmatter to agent definitions, Look for, Ignore, Deciding, and Example sections to the specialists, and relevance hints to the Firebase and Dataform READMEs.
- Added [Pitfalls](core/pitfalls.md) as a sixth specialist assignment, TERM-009 to TERM-014, and the STACK and PIT ID prefixes in NAME-004.

## 2026-10-19

- Established the core, maintenance, products, agents, and skills layout.
- Added initial Context Ops terminology and repository naming guidance. Application stack standards remain to be established from approved evidence.
- Added Firebase and Dataform knowledge entry points without importing application-specific claims.
- Defined five specialist assignments and the sweeper-first versus fresh-specialist manual workflows.
- Added setup guidance and repository-local setup and GitHub issue creation skills.
- Created the [v0.1 milestone](https://github.com/kajuyerim/code-llm-sizing/milestone/1) and [five linked issues](README.md#tracking) through kajuyerim's GitHub account. Only the structure issue is initially assigned; Baris can self-assign later.
- Updated navigation and repository scope. Team review, manual pilots, and automated hook integration are pending.
