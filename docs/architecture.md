# Architecture and the A/B boundary

Context Ops observes application development after it finishes. The application and its explicit diff are evidence; only the separate knowledge destination can receive maintenance changes.

```text
Application revision + explicit diff + selected frozen conversation
                       |
          shared collection and tool relevance selection
                       |
           A                         B
      sweeper investigates      fresh specialists
      independent session forks independent investigation
           |                         |
           +--- scoped proposals ----+
                       |
              deterministic checks
                       |
           optional cartographer proposals
                       |
              one knowledge writer
                       |
       local patch, branch, report and resource records
```

This branch registers B (`fresh-specialists`). The dependent A PR registers `sweeper-first` in the same pipeline. A's historical evaluation used real session forks, not a pasted summary. Its sweeper completion is a prerequisite; there is no fresh-session fallback.

## Shared contract

Manual runs require an explicit strategy and Claude Code session selection. Source refs and the committed knowledge baseline are frozen in `run.json`; the normalized selected conversation is copied and hashed. The source and knowledge snapshots use those commits. Configuration and role definitions must be committed before preparation. New output directories and branches include the strategy. Cutoff state and unowned findings cannot cross that boundary.

Four core specialists handle terminology, stack, conventions, and pitfalls. One tool maintainer is instantiated for each relevant folder under `tools/`; relevance comes from that folder's frontmatter. Both strategies receive the same selected roster and raw evidence. Neither receives future evidence, evaluator answers, or the other strategy's outputs. The public command does not select or score comparison cases.

Shared prompts use the stricter evidence and scope rules from A. They are a new integrated configuration, not the archived pilot prompts. Developer statements can establish intent and definitions; source can establish implementation. Dependency declarations or completion messages alone do not demonstrate runtime use. Observed application choices do not establish company policy.

## Writing and boundaries

Specialists have Read/Grep/Glob capabilities. Only the writer has Edit/Write. SDK pre-tool checks resolve paths and restrict evidence reads; writes are limited to Markdown beneath `core/` and `tools/`, plus exact `index.md` and `log.md`. Traversal, escaping symlinks, repository internals, and credential files are excluded. Grep content searches require a specific permitted file after Glob discovery, so recursive search cannot bypass filename restrictions. Deterministic checks and post-write inspection provide additional checks, not a claim of operating-system sandbox isolation.

The writer preserves existing frontmatter. Structural expansion and relevance-hint changes are proposals for human review. Agent definitions, skills, maintenance instructions, runtime source, and walkthroughs are not maintenance outputs. A failed writer does not create a commit. Inspect the actual patch separately from its structured self-report.

`tools/` means knowledge about technologies. It is distinct from the SDK capabilities the agent can invoke. Historical `products/` paths and `product:` scopes remain unchanged in archived evidence. Legacy manifests and worker metadata can be read; legacy runs lacking frozen selections must be prepared anew for execution.

## Limits

Conversation parsing depends on Claude Code's internal format. Tool results and thinking are omitted, retained messages can be truncated, and unavailable history cannot be reconstructed. Optional auto-memory is disabled by default. Cost limits are estimates and a concurrent run can exceed its aggregate threshold. The pre-push adapter is experimental; local pilots do not establish production hook behavior. See [evaluation](evaluation.md) for the historical results and [runtime operations](../runtime/README.md) for the public interface.
