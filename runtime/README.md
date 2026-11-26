# Runtime operations

Start with [setup](../setup.md) for installation and tests without credentials. The supported first-use path is a manual run against a separate application. The shared pipeline registers both `fresh-specialists` and `sweeper-first` with explicit selection.

## Commands

| Command | Purpose |
| --- | --- |
| `contextops init --kb PATH --branch knowledge/APP_NAME [--scope team\|repository] [--application NAME]` | Prepare blank knowledge on a new local branch, without committing or inference. `--scope` sets who the knowledge serves; `--application` binds a repository-scoped knowledge base to one application. |
| `contextops attach --repo APP --kb PATH --strategy MODE [--name NAME] [--no-hook] [--no-refresh]` | Connect an application checkout: its Claude Code sessions read the knowledge, and its pushes start maintenance. Writes only untracked local files. No model calls. |
| `contextops refresh --kb PATH [--digest] [--no-fetch]` | Fast-forward a clean knowledge checkout to its upstream; with `--digest`, print one line per entry. Attached applications run it at session start. |
| `contextops sweep --repo PATH --kb PATH --base REF --head REF --strategy MODE [--backend BACKEND] --session ID [--session ID] [--cutoff ISO_TIME]` | Freeze selected evidence and run locally. Real model calls occur. |
| `contextops sessions --repo PATH [--limit N]` | List the application's Claude Code sessions (ID, last message, opening line) to choose `--session` values. No model calls. |
| `contextops export-session --repo PATH --session ID --out FILE` | Write a shareable copy of one session: developer and agent messages, text, and tool calls, with the application root and home directory replaced by placeholders. Thinking, tool results, and other records are dropped. Message text is unchanged, so review it before sharing. |
| `contextops import-session --repo PATH FILE...` | Install exported sessions for another checkout of the application so `sessions` lists them and `--session` can select them. Refuses to overwrite a different session with the same ID. |
| `contextops run RUN_DIR` | Execute an unattempted prepared run with its recorded inputs. |
| `contextops install --kb PATH --repo PATH` | Install only the pre-push hook (older path; prefer `attach`). |
| `contextops hook REMOTE [URL]` | Internal pre-push hook entry point. |

The [setup skill](../skills/setup-shared-knowledge/SKILL.md) guides first-run setup. `init` requires a clean checkout and an unused branch, preserves the original branch, resets core/tool knowledge to empty templates while retaining frontmatter, refreshes the index/log, and leaves edits uncommitted. Additional learned Markdown under core/tools is removed on the new branch. Non-Markdown knowledge files and symlinks are rejected. Configure and commit the baseline before sweeping; subsequent runs do not initialize again.

There is no implicit strategy. The checked-in `init.md` has `mode: null`; the manual command requires an explicit mode. Unknown or unimplemented modes fail before inference. Sessions come from Claude Code's local JSONL history. Missing/ambiguous sessions, invalid refs, dirty knowledge checkouts, and invalid settings fail before model calls. Cutoffs require a timezone and cannot be in the future.

The selected conversation is copied before inference, with a SHA-256 recorded in `run.json`. Later messages cannot change it. A changed frozen copy fails integrity validation. Explicit sessions include retained history through the cutoff, independently of the old last-run window. Tool results and thinking are excluded; truncation and sidechain policy are recorded. Legacy manifests remain readable, but cannot execute without the new frozen-input contract. Attempted runs are never overwritten; create a new attempt.

## Configuration and authentication

`init.md` supplies model, budgets, common instructions, role paths, and output settings. Commit configuration/role changes before running so the snapshot matches the settings you reviewed. Specialist tools are Read/Grep/Glob (Grep requires a specific file after Glob discovery); the writer additionally receives scoped Edit/Write. These SDK capabilities are unrelated to the `tools/` knowledge taxonomy.

Claude subscription mode uses the user's private Claude Code authentication and removes `ANTHROPIC_API_KEY` from the runtime process. API-key mode requires that environment variable. No credential value belongs in this repository or its chats, examples, logs, screenshots, or published evidence. No authentication is required for the deterministic tests. Inference uses the configured provider, not a local model.

`output.runs_dir` is the common parent, defaulting to `~/.contextops/runs`. Claude appends the strategy and run ID. Codex adds `codex/` before the strategy to isolate cutoff state and finding backlogs. `output.branch` must include `{strategy}` and `{run_id}`. `open_pr: false` is the default; no remote push occurs unless publication is explicitly enabled. A successful writer can create a local knowledge commit. Generated branches are never merged automatically.

With `open_pr: true`, a committed result branch is pushed to `output.remote` (default `origin`) and a review request is opened against `output.target_branch` (default: the remote's default branch). `output.forge: auto` reads the remote URL: GitHub uses `gh pr create`; GitLab uses `glab mr create` when installed and otherwise Git push options (`merge_request.create`), which need no extra CLI. Other remotes, and `forge: none`, receive the branch only. The report becomes the request body; it lists records and evidence locators, not conversation text. Push and CLI errors are summarized without echoing remote output.

`scope: team` (default) means the knowledge serves a team's applications: facts are scoped `app:<name>`, `company` is reserved for rules developers state for the whole team, and entries about other applications are left alone. `scope: repository` means one application; `application: NAME` makes runs and `attach` refuse any other name. The application name comes from `attach --name`, stored as Git config `contextops.app`, else the checkout folder name.

## Codex CLI

Install the runtime from this checkout as described in [setup](../setup.md#1-install-in-a-clean-environment). Install the Codex CLI on your PATH and sign in privately with ChatGPT. An existing CLI login works with `auth: subscription`, including a custom external `CODEX_HOME`. Check `codex login status` and `codex exec fork --help` locally. Keep the Codex home outside both repositories. [OpenAI Docs on non-interactive authentication](https://developers.openai.com/codex/noninteractive#authenticate-in-automation)

```sh
contextops sweep --backend codex --strategy sweeper-first \
  --repo /path/to/application --kb /path/to/knowledge \
  --base BASE_SHA --head HEAD_SHA --session CLAUDE_DEVELOPMENT_SESSION_ID
```

Choose `fresh-specialists` for B. To make Codex the default, commit `backend: codex` in the knowledge baseline's `init.md`. Set `codex_model` there to change the model for every Codex role. It defaults to `gpt-6.1-terra`. The command-line backend takes precedence and is frozen in the run manifest. Both backends collect the same selected Claude Code development history.

B starts a new `codex exec` for each specialist. A runs the sweeper to completion and invokes `codex exec fork PARENT_ID` separately for each specialist. A failed fork appears in the report and the manual command exits with status 1. The CLI uses a read-only sandbox and a scoped file-tool server. Only the writer receives knowledge editing tools. Codex keeps private session state for forks in its normal store.

Codex reports invocation token usage. The raw and incremental fork counts are the same. Subscription dollar costs are unavailable, and the Claude USD and turn limits do not apply. Each Codex call has a ten-minute timeout and uses the shared parallelism limit. The CLI transport and schema conversion derive from the historical GPT evaluation adapter, whose pilot scores belong to that earlier configuration.

On 21 November 2026, a five-call smoke test used ChatGPT sign-in, `gpt-6.1-terra`, and Codex CLI `0.167.0-alpha.3.2` at revision `a53e57a`. The sweeper completed a random marker in its final response. Both A specialists reproduced the exact marker from separate forks of that sweeper. Both B specialists reported it absent. Local CLI records confirmed five distinct threads, the model, the two fork parents, and two fresh B threads. This check used synthetic evidence and two specialists per strategy. Knowledge quality and writer behavior were outside its scope.

## Outputs

| Artifact | Meaning |
| --- | --- |
| `run.json`, `conversation.json` | Frozen selections and normalized conversation with integrity hash |
| `pack/manifest.json`, `pack/diff/`, `pack/conversation/` | Evidence, source refs, selected sessions, and filtering notes |
| `handoffs.json` | The handoff pass: which specialist received handoffs from whom, its status, cost, and records added |
| `workers/`, `review.json` | Raw specialist responses and accepted/deferred/rejected decisions |
| `proposals.json` | Optional cartographer suggestions, never automatically applied |
| `knowledge.patch` | Candidate or committed knowledge changes; inspect writer status |
| `report.md`, `metrics.json`, `completion.txt` | Detailed outcomes, client-reported resource estimates, and the CLI review summary |
| `started` | Prevents silently rerunning an attempted directory |

Cutoff state and unowned findings live under each strategy's directory. Raw evidence and run artifacts stay outside the repository. They are not guaranteed secret-free; the public credential scan is separate from the limited proposal validator. Do not publish raw directories.

Both `sweep` and `run` print a completion summary with actual changed files, report/patch locations when present, and commands to inspect a committed result branch. Candidate patches are identified as uncommitted; no-change or failed runs do not advertise a result branch. `completion.txt` preserves this summary. The selected checkout branch is unchanged by maintenance. `total_duration_ms` sums agent durations, so measure wall-clock elapsed time separately for acceptance records.

## Attached applications and the pre-push hook

`attach` writes three untracked files in the application and adds them to `.git/info/exclude`:

- `CLAUDE.local.md`: a marked block naming the knowledge checkout and telling the agent to read its `index.md` before a task. If the application relies on `AGENTS.md` without a `CLAUDE.md`, the block imports it, because a `CLAUDE.local.md` otherwise stops Claude Code from reading `AGENTS.md`. Existing personal notes are kept; rerunning replaces only the block.
- `.claude/settings.local.json`: the knowledge checkout in `permissions.additionalDirectories` (read without prompts) and a `SessionStart` hook that runs `contextops refresh --digest`. It fast-forwards the checkout, so new sessions read merged knowledge, and prints a digest with one line per entry (ID, content, scope; evidence left out), which Claude Code adds to the session's context. The digest stays under 9,000 characters, because Claude Code moves longer session-start output into a file. `--no-digest` and `--no-refresh` turn the parts off. Existing settings are kept.
- `pre-push` hook: unless `--no-hook`. It refuses to replace another hook without `--force`, and refuses when `core.hooksPath` is set; call `python -m contextops hook "$@"` from your hook manager instead.

The pointer is plain text with an absolute path, not an `@` import, so no external-import approval is needed. It is local to that checkout: Git worktrees need their own `attach`.

On `git push`, the hook fast-forwards the knowledge checkout, then prepares one run per pushed ref: the pushed range, the strategy chosen at `attach`, and every Claude Code session in this application with a message since the last run for it (or since the pushed base commit). `contextops.sessions` in the application's Git config pins sessions instead. Preparation happens inside the hook; the run continues in the background and never blocks or fails the push. No session, an unchanged range, or a dirty knowledge checkout skips the run with a one-line message. A knowledge commit created afterward is not part of the application push.

## Known limits

- Claude Code history is an internal format. Deleted history, malformed entries, or filtered tool results may hide evidence.
- Relevance uses globs and keywords; unknown usage paths may require human updates to hints.
- Cost estimates are not billing. Concurrent calls and the writer can exceed the aggregate scheduling threshold.
- Reports include agent claims; deterministic locator checks do not prove semantic correctness. Review actual document changes.
- Tests exercise fake calls, permissions, SDK option construction, Git remotes, and fake `gh`/GitLab push options. They do not prove live provider or forge behavior.

## A session lineage and accounting

A retains the completed parent and each child in `sweeper.json`. Every specialist forks the same parent session ID. Claude uses `fork_session=True`. A missing, reused, or parent-equal child ID fails lineage validation and its proposals are withheld. A failed sweeper skips specialists without a B fallback.

Raw child usage remains available beside the incremental estimate and the validated result. For Claude, cost and model token counters subtract the parent when the reported values permit it; smaller reports are retained rather than forced negative. This follows the historical cumulative-report interpretation, and live SDK billing semantics remain unverified by the deterministic tests. Timing and turn counts are retained as reported.

Forks reuse the sweeper's prompt cache only when the cached prefix (tools and output schema, then the system prompt, then the inherited messages) is unchanged. The runtime therefore gives the sweeper and every specialist the same role-free system prompt and output schema, and sends each role as a user message. `sweeper.json` stores the parent's prefix fingerprint and a `shares_cache_prefix` flag per child. In a live run, a fork's first turn should report the inherited history as `cacheReadInputTokens`, not `cacheCreationInputTokens`.
