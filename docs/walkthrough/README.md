# How Our Knowledge Maintenance System Works

## The difference between A and B

A runs a sweeper first. Each specialist then forks the completed sweeper session and inherits the investigation, while retaining access to the original evidence. The forks are separate sessions.

B starts the same specialists in fresh sessions immediately. They receive their assignments and access to the same raw evidence, and each builds its own understanding. No sweeper session is supplied.

Both methods use the same original knowledge baseline, assignments, checks and writer process, and preserve independent knowledge outputs. Actual P3 has five specialists per method. The archived GPT run contains seven agent calls for A (one sweeper, five specialists and one writer) and six for B (five specialists and one writer). Evaluation calls are separate.


This companion explains the completed Actual Budget P3 experiment. [Download and open the interactive walkthrough](index.html) for all 53 archived messages, source excerpts, specialist decisions, session lineage, and full patches. GitHub displays HTML source; open the downloaded file locally.

The current repository uses `tools/`. The pilot used `products/`; historical paths, scopes, and patches retain their original spelling. The integrated runtime and shared prompts are a new configuration, not a rerun of these results.


## The same change. Four maintenance outputs.

We prepared five development checkpoints in each of three applications. At every checkpoint, we gave A and B the same source code, diff, conversation, and starting knowledge base. Running both methods with Claude and GPT produced 60 maintenance outputs.

We will follow one checkpoint: Actual Budget P3. The application change was generated once. Both model suites examined that same change.

The knowledge base resets to its original baseline at each checkpoint. This pilot measures responses to individual changes.

## The decision evolves through the conversation.

The persona, acting as the developer, asked the coding agent to move the donut graph helpers into separate files. The coding agent did the work but left one helper inside the original file.

The persona corrected that omission and added a decision about how donut-specific files should be named.

These are shortened English summaries of real archived messages. The interactive walkthrough provides the original messages alongside these summaries.

## The tool changes. So does its usage.

The next task was downloading a report snapshot. The persona requested snapdom instead of html-to-image. The coding agent initially used snapdom.download.

The persona corrected this: use snapdom.toPng and retain the existing anchor download flow. The final code assigned the returned image’s src to the download link.

The coding agent also explicitly stated that it had not tested the change in Firefox.

## Check the conversation against the code.

Once development finished, we froze the conversation and source revision. The maintenance workflows started from those records.

For this case, we tracked whether three required facts reached the knowledge base: the donut file layout, the new snapshot tool, and how its returned image should be used.

The Donut filename prefix was treated as a supported additional fact. It did not increase the count of three required facts.

## First, one agent examines the whole change.

In A, the sweeper read the conversation, diff, relevant source files, and existing knowledge. Its findings identified the file extraction, the new tool, and the use of image.src.

Five specialists then continued from forks of that completed session. Each specialist decided which findings should become knowledge in its assigned area. The interactive walkthrough includes the archived sweeper findings.

## Some findings stop before the documents.

The stack specialist accepted the library change. The Recharts specialist treated the file extraction as a local refactor, while the conventions specialist treated the Donut prefix as a choice specific to this task.

The pitfalls specialist declined to add an entry because Firefox verification was missing. In the accepted proposal, the src detail became a more general instruction to “download the returned image using an anchor.”

One required fact reached the final documents in full. Another was captured partially.

## The same evidence. A fresh start.

In B, the same five specialists started in fresh sessions. Each examined the conversation, diff, source code, and starting knowledge for its own assignment, without inheriting the sweeper’s history or interpretation.

Both paths received the same original knowledge baseline. B did not inherit the documents produced by A.

## The same conversation. Different accepted records.

The stack specialist in B recorded the new tool. The conventions specialist accepted the Donut prefix as a rule scoped to this report-graph area.

The pitfalls specialist recorded the reported failure and the download flow implemented in the source. It preserved the instruction to use the returned image source without claiming that Firefox success had been verified.

Three proposals were accepted. They covered two required facts and one additional naming fact.

## Knowledge now lives beyond the conversation.

Proposals that passed the shared checks were sent to the writer. The writer applied them to the appropriate documents and recorded the changes in log.md.

A updated the stack document. B also added naming and pitfall entries. We evaluated accepted proposals and the actual written documents separately.

The interactive walkthrough embeds the original records and full patches for comparison.

## Compare proposals with final documents.

Claude also examined this checkpoint with A and B. We evaluated all four outputs against the same three required facts.

The accepted rationale from Claude A incorrectly claimed that the old package had been removed. That claim did not enter the final document, so proposal coverage and document coverage received different scores.

These are AI assessments after the Sol evaluation and additional Astra review. Human sign-off is not recorded. Despite full required coverage, part of an additional typing recommendation from Claude B was judged unsupported.

## The decision to preserve a fact changes the outcome.

The sweeper in A had found the relevant details. But the specialists’ decision about what counts as lasting knowledge, and the level of detail retained in the final wording, changed the result.

A retained a general anchor-download description. B also preserved image-source handling and a scoped filename prefix. Neither GPT method recorded the donut file layout.

This example helps us identify the stage where the difference arose. It does not establish an overall winner.

## What was actually written

GPT A updated STACK-105 in core/tech-stack-standards.md and recorded the change in log.md. Its accepted text names snapdom.toPng and the anchor download, but omits the explicit src detail.

GPT B updated STACK-105, added NAME-104 for donut-specific filenames, added PIT-001 describing the reported Firefox problem and implemented image-source handling, and updated log.md. Neither GPT method recorded the required donut-helper extraction as architecture knowledge.

## Required fact coverage after additional Astra review

| Condition | Accepted proposals | Final documents |
| --- | --- | --- |
| Claude A | 1/3 | 2/3 |
| Claude B | 3/3 | 3/3 |
| GPT A | 1/3 | 1/3 |
| GPT B | 2/3 | 2/3 |

Claude A had an incorrect package-removal claim in the accepted rationale, absent from its final document. Claude B also produced an additional typing claim that was partly unsupported. These scores measure required coverage, not the correctness of every additional claim.

The original English messages, specialist outputs, accepted records, patches, and assessment reasons are embedded in the interactive HTML file and can be opened from the relevant scene.

The old html-to-image dependency remained declared. Firefox success was not demonstrated. See the [evaluation summary](../evaluation.md) for all 60 outputs and limitations, and [provenance](../provenance.md) for exact revisions and publication transformations.
