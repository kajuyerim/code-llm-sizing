# Reports

Project reports in date order. Earlier reports are kept unchanged when a newer one appears; each one describes the configuration and data of its own date.

| Date | Report | What it covers |
| --- | --- | --- |
| 29 October 2026 | [Pilot report](2026-10-29-pilot/context-ops-pilot.html) (HTML) | October pilot: three applications, five checkpoints, Claude and GPT, strategies A and B, 60 maintenance outputs. |
| 30 October 2026 | [Walkthrough](../docs/walkthrough/README.md) ([HTML](../docs/walkthrough/index.html)) | One case, Actual Budget P3, followed from conversation to proposals and written knowledge. |
| 5 November 2026 | [Experiment v2 report](2026-11-05-v2/context-ops-v2.html) (HTML) | Longer multi-persona pushes, the prompt-cache fix, A and B with Sonnet and Haiku; conversations, per-fact proposals, cost and time, analysis. |
| 14 November 2026 | [First-run acceptance](../docs/first-run-acceptance.md) | Live run of the public demo from empty knowledge to a populated branch. |
| 15 November 2026 | [Results and usage](2026-11-15-results/context-ops-results.html) (HTML) | The v2 report brought up to date. It explains how a team uses the repository and covers the maintenance rerun on the v2 inputs, the three development experiments, and persona development chats alongside the conversations the knowledge was learned from. |
| 18 November 2026 | [Midterm report](2026-11-18-midterm/context-ops-midterm.pdf) (PDF, [LaTeX source](2026-11-18-midterm/main.tex)) | CMPE 492 midterm: problem, design, implementation, the pilot, v2, the downstream comparison with and without knowledge, the feature-sequence experiment with team and repository knowledge, the maintenance rerun and persona-driven development, the demo, and next steps. |

The written summary of every evaluation, with denominators and limits, is [docs/evaluation.md](../docs/evaluation.md).

Open the HTML reports locally; they are self-contained and work offline. In the published copies the original workspace path is replaced with `/workspace/contextops-eval` and personal user names are replaced; nothing else was changed. The conversations they show were produced by simulated developer personas talking to a real Claude Code agent. Application sources, raw run directories, and the evaluation harnesses stay in the private evaluation workspace.

## Building the midterm report

The report is LaTeX in the CMPE 492 template layout. With [Tectonic](https://tectonic-typesetting.github.io/):

```sh
cd reports/2026-11-18-midterm
tectonic -X compile main.tex && mv main.pdf context-ops-midterm.pdf
```

Tables and numbers of the downstream comparison in `generated/` are produced by the evaluation workspace's `analyze.py` and committed with the report.
