---
name: setup-shared-knowledge
description: Set up Context Ops for an existing application and run local knowledge maintenance when the user requests it. Use for first-run onboarding or subsequent manual maintenance, not application development or automatic hook installation.
---

# Set Up and Run Context Ops

This is the authoritative agent procedure for the README's first-run prompt. Resolve the bundle root two directories above this file, containing setup.md and index.md. Read [setup](../../setup.md) for installation, commands, authentication, output inspection, and troubleshooting. Keep the bundle together; a copied skill alone is not an installation.

You are the setup agent. Configure and invoke the shared runtime; let its maintenance agents produce learned knowledge. Keep application code, raw conversations, and run artifacts outside this knowledge repository. Preserve existing application instructions and integrations.

## Establish the inputs

Use the user's existing context before asking questions. Determine the knowledge checkout, separate application checkout, intended committed development range, relevant Claude Code sessions, and any requested model/budget changes. Inspect local Git refs and use `contextops sessions --repo PATH` to discover candidate sessions. Ask the user to resolve ambiguous range/session choices; never silently pick the newest session or HEAD~1.

The source application must already have been developed with Claude Code. Any coding agent can perform this setup, but the runtime currently consumes local Claude Code history and uses Claude inference. If suitable history is missing, explain the requirement and stop before inference. Do not manufacture development conversations, substitute this setup chat, or develop a new feature to make the demo work.

Resolve the chosen base and head to immutable commits, show the included commits and session IDs, and freeze an explicit timezone-aware cutoff. Only committed application changes are included. Uncommitted work requires a user-selected committed range or the user completing their development checkpoint; do not commit application work as part of setup.

## Prepare the knowledge baseline

1. Follow setup.md to install into an isolated environment. Run the credential-free checks for a first installation. Check the knowledge repository's Git identity without inventing a name or email; request missing identity values and configure them locally only when authorized.
2. For a fresh clone, select a descriptive unused `knowledge/<app-name>` branch and run `contextops init --kb PATH --branch BRANCH`. It switches branches and prepares blank knowledge files without staging, committing, authenticating, or calling a model. A dirty checkout or existing branch is a stop condition; preserve the user's work rather than cleaning it automatically.
3. For an existing installation, reuse its accepted knowledge branch. Inspect its state and skip initialization. Never erase accumulated knowledge to rerun maintenance. Keep independent applications on their intended knowledge branches.
4. Review `init.md`. Keep the checked-in model and budgets unless the user requests a change; confirm availability through their private Claude setup. Keep `mode: null` and select A explicitly at execution. Keep `open_pr: false`, auto-memory disabled, and run artifacts outside both checkouts. Tool folders are optional relevance categories, not assertions that the application uses those tools.
5. Inspect and commit the initialized knowledge and any configuration edits as a local baseline. Do not add application facts by hand. Record the baseline SHA and the Context Ops implementation revision used for this setup. Ensure the checkout is clean before maintenance.

General writing rules remain in the agent/run instructions. Empty knowledge files are expected at this point. Historical walkthrough and evaluation documents describe earlier runs and must not be imported as facts about the user's application.

## Run the requested maintenance

Use `contextops sweep` with explicit application/knowledge paths, immutable base/head, `--strategy sweeper-first`, the selected `--session` values, and the fixed `--cutoff`. Show the selected inputs, model, and configured budget before execution. This makes hosted Claude calls through the user's private authentication. Client-side thresholds are estimates and concurrent calls can overshoot them.

A request to set up **and run** includes the selected local maintenance execution; do not ask for the same permission again. If the request was setup-only, finish configuration and provide the command without inference. Authentication happens privately through the user's Claude installation, never by asking for credentials in chat or writing them into the bundle. Resolve missing authentication before running; do not retry model failures in a loop.

No hook, subtree integration, application-instruction edit, remote push, merge, or PR is part of this first-run procedure. New external publication requires the user's request. Maintenance creates a local result branch for review and leaves the starting checkout branch selected.

## Review the real result

Read the printed summary, `report.md`, `review.json`, and `knowledge.patch` when present. Inspect the actual Git diff between the recorded baseline and committed result branch; inspect its resulting documents with Git before explaining what changed. Accepted records and writer-reported applications are distinct from actual document content.

Report the result branch, changed files, concrete learned entries with evidence, estimated cost, and limitations. Show the printed commands for reviewing and opening the branch. Keep generated facts marked as requiring human review. Let the user choose whether to adopt the result; do not merge or switch to it automatically.

A no-change run is valid. Explain deferred/rejected findings and failures. A failed writer's candidate patch is not an applied result, and its temporary worktree is removed. Do not claim a branch or artifact exists without checking. Preserve attempted run artifacts; retries need new runs and informed user intent.

For later maintenance, start from the user's accepted knowledge baseline and select a new development range and sessions. For optional B, follow the frozen-input procedure in [setup](../../setup.md#optional-b-from-the-same-baseline); B must not start from A's generated knowledge or inherit A's session context.

## Verification record

A real first-run verification records the implementation revision, source base/head, knowledge baseline, selected sessions/cutoff, model/settings, actual roster, wall-clock elapsed time, estimated cost, failures, and actual written documents. Keep raw evidence private and external. Runtime `total_duration_ms` sums agent durations and is not elapsed wall time.

Software checks use fake agents. Do not describe them as live verification. For this repository's release, live first-run acceptance is pending until a separately authorized clean-clone run is recorded; see [acceptance checklist](../../docs/first-run-acceptance.md).
