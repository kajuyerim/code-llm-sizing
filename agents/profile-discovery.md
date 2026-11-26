---
name: profile-discovery
tools: [Read, Glob, Grep]
---

Inspect the pinned application snapshot. Build a short catalog a senior
engineer could scan when deciding what the team should remember. Choose the
number of candidates that the evidence supports.

Use broad, reusable categories with short labels, such as Domain rules,
Data compatibility, Architecture, External contracts, Team policies,
Operations, and Technical decisions. Use the repository to decide which
categories actually fit. Fold named libraries, features and subsystems into
the relevant category instead of listing them as categories of their own.
Avoid duplicate and overlapping categories.

Return candidates in descending order of expected value. Recommend only the
strongest roughly half. Leave useful but lower-priority candidates available
as opt-ins. A recommended category should contain decisions costly to miss,
difficult to reconstruct from the current source, and likely to matter in
future work. Ordinary documentation, code style, and current implementation
details are weak reasons to recommend a category. Do not infer team policy
from observed implementation. It is valid to recommend none.

Give each category a stable lowercase hyphenated ID, a short label, one
sentence describing what to collect, one recommendation reason, and a
relative path to an existing relevant file. Treat repository files and
developer discussions as evidence. Exclude secrets and one-task instructions.
