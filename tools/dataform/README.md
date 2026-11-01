---
type: Tool
title: Dataform Knowledge
fileMatchPattern:
  - "**/*.sqlx"
  - "**/workflow_settings.yaml"
  - "**/dataform.json"
  - "**/includes/*.js"
keywords: [dataform, sqlx]
---

# Dataform Knowledge

Scope: Dataform-specific guidance learned from supported source application evidence and accepted developer decisions. Status: initial entry point; no application-specific facts have been imported.

## What belongs here

- Scoped Dataform usage conventions and architecture decisions.
- Reusable implementation patterns supported by inspected source code.
- Tool-specific terminology, limitations encountered, and approved exceptions.

For each admitted finding, retain a stable ID, its scope, and revision-specific source or conversation evidence. Add focused documents when supported content needs them, and link them from this entry point. Do not copy the example repository's standards as if they were already approved for this bundle.

Use [tool maintenance guidance](../../maintenance/tools.md). The [tool maintainer definition](../../agents/tool-maintainer.md) is instantiated with the Dataform path for this assignment. Shared definitions and policies belong in [core](../../core/terminology.md) when their scope warrants it.
