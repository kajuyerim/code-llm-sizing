# Set Up Shared Knowledge

Use this walkthrough to connect an existing application repository to this knowledge bundle and prepare manual maintenance. Application code stays in its own repository. The [setup skill](skills/setup-shared-knowledge/SKILL.md) provides an agent entry point to this guide.

## 1. Inspect the existing setup

Identify the application repository and this knowledge checkout. Read their current agent instructions and inspect Git status before changing documentation. Reuse paths and choices already supplied by the developer. Preserve unrelated work and existing integration settings.

Read the [knowledge index](index.md). The initial product areas are [Firebase](products/firebase/README.md) and [Dataform](products/dataform/README.md); their presence is not evidence that the application uses either one.

## 2. Choose the applicable knowledge

Select relevant core documents and product areas from the application's evidence and the developer's stated scope. Record unknowns rather than choosing technologies for the application. Add a new product entry only when an actual maintained scope calls for it.

## 3. Reference the bundle from the application

For initial manual use, use the existing separate local knowledge checkout. Preserve a Git subtree integration when the application already uses one. A new subtree integration is a separate explicit setup choice, not an automatic pull, merge, or push.

When setup is requested for an identified application, add or update a short shared-knowledge section in its existing agent instructions. Record:

- The resolved local knowledge location and index entry point.
- The applicable product areas and core guidance.
- Maintenance timing: after development, before push.
- Required evidence: source repository, explicit diff, and developer-agent conversation.
- The selected strategy, or that selection is pending.
- Integration status: manual workflow available; automated runner/hook pending unless an actual implementation has been verified.

Preserve unrelated application instructions. This repository's own AGENTS.md describes the knowledge destination and must not be replaced with application setup details.

## 4. Prepare evidence inputs

Record the source repository identity, base/head commit IDs, knowledge baseline revision, and explicit diff. Locate the relevant local conversation export and declare a cutoff before maintenance starts. Preserve speaker roles, message order, session/message references, and any known exclusions or truncation.

Ask for a missing repository path or conversation export when needed for an actual run. Do not silently omit the conversation, invent an export path, or claim that a Git hook supplies conversation history automatically.

## 5. Select roles and strategy

This branch configures six [specialist assignments](agents/README.md#initial-specialist-assignments) for sweeper-first maintenance. Four core workers always run; product workers are selected by relevance. Record model configuration and resource limits before future measured work.

- Invoke the sweeper on original evidence, then fork its successfully completed session independently for selected specialists.
- Record parent and child IDs, coverage, omissions, and raw plus incremental resources. Do not replace a failed fork with a fresh session or summary.

Use the [change record](maintenance/core.md#change-record). This runtime implements only sweeper-first behavior and has no comparison integration.

## 6. Run manually and report integration status

For a manual run, supply the frozen evidence and role instructions through the chosen local agent. Have specialists return proposals, then use one final writer to reconcile them in the appropriate knowledge checkout. Keep the source application read-only during maintenance and retain local run artifacts outside this bundle.

The [runtime source](runtime/README.md) implements a manual command and background pre-push adapter, but is not run or verified. Installation, hook activation, model calls, tests, and pilots were excluded from the current implementation. Operational commands in that guide are for a later authorized setup, not instructions to execute while reading this walkthrough.

## 7. Finish with a setup report

Report the application and knowledge paths, selected guidance, reference-document changes, available evidence inputs, strategy and role assignments, and remaining work. Distinguish documentation setup from a completed maintenance run and from working hook automation.

Repository-local skills are available by reading their [SKILL.md entry points](index.md#skills). Automatic skill discovery has not been configured. Use the [issue creation skill](skills/create-github-issue/SKILL.md) when the developer requests GitHub tracking for follow-up work.
