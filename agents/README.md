# Agent Definitions and Experiment Conventions

These files define the roles of a maintenance run. Each specialist receives an explicit assignment and reads the applicable maintenance guide. The same files serve manual pilots and the [runtime](../runtime/README.md): the runtime reads each definition's frontmatter (name, tools, optional model) and uses its body as the agent's instructions, after the [shared rules](shared-rules.md) and the run notes in [init.md](../init.md).

## Run stages

| Stage | Definition | What it does |
| --- | --- | --- |
| Initializer | [init.md](../init.md), implemented in the runtime | Freezes the evidence pack and picks the specialists for this push |
| Specialists | The assignments below | Sweep the evidence for their own document and return change records |
| Checks | Runtime code | Reject records outside an assignment or with evidence that does not resolve |
| Cartographer | [Cartographer](cartographer.md) | Proposes new core documents or product folders from unowned findings |
| Writer | [Writer](writer.md) | Applies accepted records on a branch and opens the pull request |

## Shared inputs

Both strategies inspect the same source application revision, Git diff, and developer-agent conversation export. Also provide the knowledge baseline revision, transcript cutoff, allowed output path, and the task instructions. Preserve source/session identifiers, speaker roles, message order, and any recorded exclusions or truncation.

An export of the development conversation is evidence available to both strategies. It does not give B an inherited sweeper interpretation. Keep independent sessions and knowledge states for each strategy, and keep evaluator answers and future evidence outside agent access.

## Initial specialist assignments

| Assignment | Definition | Allowed knowledge target |
| --- | --- | --- |
| Terminology | [Terminology maintainer](terminology-maintainer.md) | core/terminology.md |
| Stack standards | [Stack maintainer](stack-maintainer.md) | core/tech-stack-standards.md |
| Naming conventions | [Conventions maintainer](conventions-maintainer.md) | core/naming-conventions.md |
| Pitfalls | [Pitfalls maintainer](pitfalls-maintainer.md) | core/pitfalls.md |
| Firebase | [Product maintainer](product-maintainer.md) | products/firebase/ |
| Dataform | [Product maintainer](product-maintainer.md) | products/dataform/ |

The product role is instantiated once per product folder. In automated runs a product instance starts only when the diff or conversation matches the relevance hints in its README frontmatter. Both experiments use these six specialist assignments. Changes outside an assignment are handoffs to the relevant owner, not permission to edit another specialist's documents.

## Experiment A: Sweeper first

Start the [sweeper](sweeper.md) with the shared inputs. It examines all three evidence sources broadly before the same six specialist roles begin. Transfer its gathered context together with the original evidence references.

Record whether the handoff is a literal session fork, copied history, or a summary. Record truncation or omitted context. A summary-based run must not be reported as a literal fork. Include sweeper calls, inherited context, and any final reconciliation calls in total resource use.

## Experiment B: Fresh specialists

Start fresh specialist sessions, one per assignment, with the same knowledge baseline and raw evidence inputs. Each inspects the repository, diff, and conversation for its assignment. Supply no sweeper summary, A-generated knowledge, or inherited session memory. Record each agent's actual evidence reads and context truncation.

## Outputs and final writing

Each specialist returns the [shared change record](../maintenance/core.md#change-record), including NO_CHANGE or NEEDS_REVIEW when appropriate. Treat the application as read-only. Do not create application code or change maintenance rules, agent definitions, or skills as a maintenance output.

One final [writer](writer.md) combines proposals in the corresponding strategy's knowledge checkout, resolves overlaps or defers conflicts, and updates the root index/history only as necessary. Keep the source application unchanged. Retain proposals and run records outside this bundle alongside the local experiment artifacts; the runtime keeps them under `~/.contextops/runs/`.

Findings that fit no assigned document are returned as unowned. The [cartographer](cartographer.md) reads them across runs and proposes new documents or product folders. Its proposals go to the pull request for a human decision and are never applied automatically.

## Manual pilot record

Before running, freeze source base/head revisions, the knowledge baseline, conversation export and cutoff, model configuration, and resource limits. Both strategies use the same declared settings. Record actual inputs, coverage, outputs, failures, elapsed time, and reported token use; mark unavailable measurements as unavailable.

Pilot preparation and evaluation remain tracked in GitHub issues. The first pilot cases should cover a relevant update, an irrelevant diff, a conversation-only term, a rejected proposal, a later correction, and an implementation claim contradicted by the source. Keep expected answers outside the agents' accessible workspace.
