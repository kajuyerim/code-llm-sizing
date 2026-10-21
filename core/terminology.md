# Terminology

Scope: vocabulary shared across this knowledge bundle. Basis: the team's foundation discussion on 19 October 2026 and the standalone sweeper-first implementation authorized on 21 October 2026. These definitions describe project design, not findings from a pilot application. Human review is pending.

| ID | Term | Meaning |
| --- | --- | --- |
| TERM-001 | Context Ops | Maintaining useful shared knowledge as an application's implementation and development decisions evolve |
| TERM-002 | Shared knowledge | Persistent terminology, standards, conventions, and product guidance that developers and agents can reuse |
| TERM-003 | Source application | An external application repository inspected as evidence for knowledge maintenance |
| TERM-004 | Product | A technology-specific knowledge area, such as Firebase or Dataform, under the products folder |
| TERM-005 | Maintenance run | A documentation-only inspection of the source repository, its diff, and the developer-agent conversation that produces knowledge change proposals |
| TERM-006 | Sweeper | The agent in experiment A that inspects all three evidence sources before handing its context to specialists |
| TERM-007 | Specialist | An agent assigned a specific part of core or product knowledge to maintain |
| TERM-008 | Knowledge baseline | The recorded starting revision of this knowledge bundle, shared by both experiments before their states diverge |
| TERM-009 | Initializer | Deterministic code that reads the run configuration and selects specialist assignments before model calls |
| TERM-010 | Evidence pack | Locally retained diff, conversation, and memory copies with their manifest and immutable application and knowledge revision references |
| TERM-011 | Literal session fork | A new SDK session that inherits a completed parent conversation while subsequent specialist histories remain independent |
| TERM-012 | Cartographer | A read-only agent that proposes new knowledge structure from recurring validated unowned findings |
| TERM-013 | Writer | The only editing agent, applying accepted records before deterministic validation and human review |
| TERM-014 | Unowned finding | An evidence-backed candidate that no current specialist assignment can reasonably hold |
| TERM-015 | Pitfall | A non-obvious failure condition with its supported consequence and remedy |

Use [core maintenance guidance](../maintenance/core.md) when changing definitions, adding synonyms, or introducing supported domain terms. Product-specific meanings belong in the appropriate product section unless they apply more broadly.
