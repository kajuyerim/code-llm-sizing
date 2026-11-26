---
# Read by the initializer in runtime/contextops/initializer.py.
version: 0.1
mode: null                    # choose explicitly with --strategy
scope: team                   # team: shared by a team's applications; repository: one application
application: null             # with scope repository, the only application name accepted
backend: claude                  # claude or codex; sweep --backend overrides this
codex_model: gpt-6.1-terra        # used for every Codex maintenance role
auth: subscription             # subscription (provider login), or api-key for Claude
model: claude-sonnet-5-5                  # default for agents whose definition sets no model
shared_rules: agents/shared-rules.md
sweeper: agents/sweeper.md

evidence:
  conversation:
    source: claude-code
    since: last-run            # last-run, or base-commit
    include_sidechains: false  # subagent conversations of the development agent
    max_chars_per_session: 200000
  memory:
    repo_files: [CLAUDE.md, CLAUDE.local.md, .claude/CLAUDE.md, AGENTS.md]
    auto_memory: false

workers:
  - agent: agents/terminology-maintainer.md
    owns: core/terminology.md
    run: always
  - agent: agents/stack-maintainer.md
    owns: core/tech-stack-standards.md
    run: always
  - agent: agents/conventions-maintainer.md
    owns: core/naming-conventions.md
    run: always
  - agent: agents/pitfalls-maintainer.md
    owns: core/pitfalls.md
    run: always
  - agent: agents/tool-maintainer.md
    for_each: tools/*/      # one instance per tool folder
    run: when-relevant         # uses fileMatchPattern and keywords in the tool README

after:
  cartographer: agents/cartographer.md
  writer: agents/writer.md

checks:
  automatic: false
  agent: agents/check-proposer.md

budget:
  per_agent_usd: 1.5
  total_usd: 10.0
  max_turns: 30
  max_parallel: 3

output:
  runs_dir: ~/.contextops/runs
  branch: contextops/{strategy}/{run_id}
  open_pr: false               # true: push the result branch and open a pull or merge request
  remote: origin               # the knowledge repository's shared remote
  target_branch: null          # null: the remote's default branch
  forge: auto                  # auto (from the remote URL), github, gitlab, or none (push only)
---

# Run Notes

These notes are added to the instructions of every agent in a maintenance run.

## What this knowledge keeps

This knowledge is for things a developer or agent cannot learn from the repository in front of them, and that cost time or cause harm when missed. Teams can edit this list.

Keep:

- How the team does operational work: provisioning and deployment (for example, infrastructure only through Terraform, never by console or CLI), secrets, environments and regions, releases, and database migrations.
- How the team uses tools, products and internal services, including what not to use: Firebase, BigQuery, Dataform, gateways, shared libraries.
- Security, privacy and compliance rules.
- Rejected approaches and pitfalls, with the reason, so they are not tried again.
- Decisions that replace an earlier way of working. Record the old and the new way, because existing code still shows the old one.
- Contracts between repositories and teams: APIs, events, shared schemas, versioning and compatibility.
- Domain terms whose meaning is specific to the team.

Leave out, and return NO_CHANGE with the reason in your coverage notes:

- UI and styling conventions, such as where buttons go, colors, spacing, copy, and component structure, even when stated as a rule. They belong in the design system or the application's own documentation.
- Code style, file layout and patterns that the application's code, linters, formatters or type checks already show or enforce.
- Instructions for the current task only, implementation details of one feature, and personal preferences.

- You are part of a local maintenance run after development in a separate application repository. The run maintains this knowledge bundle only. The application is evidence and stays read-only.
- Most pushes change nothing worth remembering. A run where every specialist returns NO_CHANGE is a good run when the evidence is routine. Unnecessary records cost a human reviewer's time.
- Your proposals and applied changes are retained locally for human inspection. Publication is disabled by default. When support or authority is unclear, NEEDS_REVIEW is the right answer, not a confident guess.
- Knowledge here must stay useful to developers and agents who never saw this conversation. Write each entry so it stands on its own.
- Historical walkthroughs and evaluation documents describe other runs. They are not evidence about the selected source application; use this run's frozen source, diff, and conversation for learned facts.
- Write in English and use no em dashes. Preserve existing fact IDs; write new core IDs as a prefix, a hyphen, and three digits (`TERM-001`, `STACK-001`, `NAME-001`, `PIT-001`), continuing from the highest existing number.
- Use descriptive Markdown titles and relative links. Use lowercase file/folder names with hyphens, preserving conventional entry points such as README.md. Put tool-specific knowledge under its lowercase tools folder. These are bundle formatting rules, not application conventions.
