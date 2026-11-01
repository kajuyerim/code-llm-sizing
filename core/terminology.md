# Terminology

Scope: vocabulary shared across this knowledge bundle. Basis: the team's project design discussion on 19 October 2026. These definitions describe the project design, not findings from a pilot application. Initial human review is pending.

| ID | Term | Meaning |
| --- | --- | --- |
| TERM-001 | Context Ops | Maintaining useful shared knowledge as an application's implementation and development decisions evolve |
| TERM-002 | Shared knowledge | Persistent terminology, standards, conventions, and tool guidance that developers and agents can reuse |
| TERM-003 | Source application | An external application repository inspected as evidence for knowledge maintenance |
| TERM-004 | Tool | A technology-specific knowledge area, such as Firebase or Dataform, under the tools folder |
| TERM-005 | Maintenance run | A documentation-only inspection of the source repository, its diff, and the developer-agent conversation that produces knowledge change proposals |
| TERM-006 | Sweeper | The agent in experiment A that inspects all three evidence sources before handing its context to specialists |
| TERM-007 | Specialist | An agent assigned a specific part of core or tool knowledge to maintain |
| TERM-008 | Knowledge baseline | The recorded starting revision of this knowledge bundle, shared by both experiments before their states diverge |
| TERM-009 | Initializer | The deterministic first step of a maintenance run that reads init.md and decides which specialists start |
| TERM-010 | Evidence pack | The frozen copy of a push's diff, developer-agent conversation, and memory that every agent in a run reads |
| TERM-011 | Cartographer | The agent that proposes new core documents or tool folders from findings no existing document owns |
| TERM-012 | Writer | The only agent that edits knowledge files; it applies accepted change records on a branch for review |
| TERM-013 | Unowned finding | A supported finding that no specialist's assigned document can hold; input for the cartographer |
| TERM-014 | Pitfall | A non-obvious failure with its trigger and the way to avoid it |

Use [core maintenance guidance](../maintenance/core.md) when changing definitions, adding synonyms, or introducing supported domain terms. Tool-specific meanings belong in the appropriate tool section unless they apply more broadly.
