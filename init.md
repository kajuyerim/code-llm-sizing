---
# Read by the initializer in runtime/contextops/initializer.py.
version: 0.1
mode: fresh-specialists        # experiment B; experiment A registers "sweeper-first"
auth: subscription             # subscription (Claude Code login) or api-key
model: claude-sonnet-5-5                  # default for agents whose definition sets no model
shared_rules: agents/shared-rules.md

evidence:
  conversation:
    source: claude-code
    since: last-run            # last-run, or base-commit
    include_sidechains: false  # subagent conversations of the development agent
    max_chars_per_session: 200000
  memory:
    repo_files: [CLAUDE.md, CLAUDE.local.md, .claude/CLAUDE.md, AGENTS.md]
    auto_memory: true

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
  - agent: agents/product-maintainer.md
    for_each: products/*/      # one instance per product folder
    run: when-relevant         # uses fileMatchPattern and keywords in the product README

after:
  cartographer: agents/cartographer.md
  writer: agents/writer.md

budget:
  per_agent_usd: 1.5
  total_usd: 10.0
  max_turns: 30
  max_parallel: 3

output:
  runs_dir: ~/.contextops/runs
  branch: contextops/{run_id}
  open_pr: false
---

# Run Notes

These notes are added to the instructions of every agent in a maintenance run.

- You are part of an automated maintenance run that started when a developer pushed work from an application repository. The run maintains this knowledge bundle only. The application is evidence and stays read-only.
- Most pushes change nothing worth remembering. A run where every specialist returns NO_CHANGE is a good run when the evidence is routine. Unnecessary records cost a human reviewer's time.
- Everything you return reaches a human through a pull request. When support or authority is unclear, NEEDS_REVIEW is the right answer, not a confident guess.
- Knowledge here must stay useful to developers and agents who never saw this conversation. Write each entry so it stands on its own.
- Write in English and use no em dashes (NAME-005).
