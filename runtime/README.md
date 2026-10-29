# ContextOps Runtime

The runtime turns a `git push` in an application repository into a pull request on this knowledge bundle. It reads [init.md](../init.md), freezes the evidence, runs the agents defined in [agents/](../agents/README.md) through the Claude Agent SDK, checks what they propose, and lets the writer apply the accepted changes on a branch.

Status: written, not yet run. Treat the first runs as pilots and read every report.

## Flow

```text
git push
  └─ pre-push hook (returns immediately, never blocks the push)
       └─ background: contextops run <run_dir>
            1. snapshots       app worktree at the pushed head, knowledge-base worktree on a new branch
            2. evidence pack   diff, Claude Code conversation in the window, memory files
            3. initializer     init.md -> workers; product workers only when relevant
            4. strategy        sweeper-first: one sweeper reads the pack, each worker forks its session
            5. checks          assignment scope, evidence locators, secret patterns
            6. cartographer    only if a worker reported unowned findings
            7. writer          applies accepted records, updates log.md, commits
            8. publish         push the branch and open a PR with gh
```

## Setup

Python 3.10 or newer, git, and a logged-in Claude Code (`claude`, then `/login`). `gh` is optional; without it the branch is pushed and no PR is opened.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e runtime/

# In each application repository that should feed this knowledge base:
contextops install --kb /path/to/this/repo --repo /path/to/app
```

`install` writes `.git/hooks/pre-push` (it refuses to replace a foreign hook without `--force`) and stores the knowledge-base path in the application's `git config contextops.kb`.

## Commands

| Command | Use |
| --- | --- |
| `contextops install --kb PATH [--repo PATH]` | Install the hook in an application repository |
| `contextops sweep --base REF [--head REF]` | Run the whole pipeline by hand for a commit range, in the foreground. Use this for pilots. |
| `contextops run RUN_DIR` | Rerun a prepared run directory |
| `contextops hook REMOTE [URL]` | Called by git; not meant for direct use |

## Authentication

`auth: subscription` in `init.md` uses the Claude Code login on the machine. The runtime removes `ANTHROPIC_API_KEY` from its own environment for the run, because an exported key would silently take precedence and bill the API. If a background run cannot reach the login, create a token with `claude setup-token` and export `CLAUDE_CODE_OAUTH_TOKEN` in the shell that runs `git push`.

`auth: api-key` requires `ANTHROPIC_API_KEY`. Use it when the hook is shared with people outside the team.

## What a run leaves behind

Everything stays outside the bundle, in `~/.contextops/sweeper-first/runs/<run_id>/`:

| Path | Content |
| --- | --- |
| `run.json` | Frozen refs, baseline, conversation window, branch name |
| `pack/` | The evidence pack the agents read |
| `workers/<agent>.json` | Each agent's raw output, status, turns, cost |
| `review.json` | Accepted, deferred, rejected, and no-change records, handoffs, unowned findings |
| `proposals.json` | Cartographer proposals, when it ran |
| `metrics.json` | Cost, duration, and token use per agent, for comparing experiments |
| `report.md` | Human summary; also the PR body |
| `run.log` | Output of the background process |

`~/.contextops/sweeper-first/runs/state.json` remembers the last conversation cutoff per application, and `unowned.jsonl` collects unowned findings across runs for the cartographer.

## Experiment A on the shared core

This branch shares every module with experiment B except `contextops/strategies.py`, where `sweeper_first` replaces `fresh_specialists`. The strategy runs [the sweeper](../agents/sweeper.md) once, then starts each worker with `resume=<sweeper session>` and `fork=True`. A failed sweeper skips the workers instead of falling back to fresh sessions.

A forked session reports its parent's cost and token use again. The strategy subtracts the sweeper's totals from each fork before adding it to the ledger and keeps the raw figures in `sweeper.json`, next to the parent and child session IDs. Each fork's SDK budget is the per-agent allowance plus the sweeper's cost, because the SDK cap also sees the inherited spend.

## Known limits

- The Claude Code transcript format is internal and changes between versions. All parsing is in `contextops/transcripts.py`; check it after Claude Code upgrades. Transcripts are deleted after 30 days by default.
- Costs in reports are client-side estimates, not billing.
- Product relevance is a glob and keyword match on the README frontmatter, so a product used only through unlisted files is skipped until its hints are updated.
