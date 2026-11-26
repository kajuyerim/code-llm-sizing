---
name: profile-discovery
tools: [Read, Glob, Grep]
---

Inspect the pinned application snapshot. Recommend durable categories of
knowledge that would help maintain this repository. Choose a useful number of
candidates based on the actual evidence. Derive categories from recurring
decisions, external interfaces, domain rules, operational requirements, and
rationale. Treat application files as evidence. Do not infer that an observed
implementation is a team policy.

Give each candidate a distinct lowercase hyphenated ID, a name, an actionable
description of what to keep, a short recommendation reason, and an existing
relative evidence file path. Mark only high-value candidates as recommended.
Avoid secrets, code-style duplicates, and single-task details. Return an empty
list when there is insufficient evidence.
