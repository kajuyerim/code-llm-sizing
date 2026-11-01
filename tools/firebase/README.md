---
type: Tool
title: Firebase Knowledge
fileMatchPattern:
  - "**/firebase.json"
  - "**/.firebaserc"
  - "**/firestore.rules"
  - "**/firestore.indexes.json"
  - "**/storage.rules"
  - "**/database.rules.json"
  - "**/google-services.json"
  - "**/GoogleService-Info.plist"
  - "**/functions/**"
keywords: [firebase, firestore, crashlytics, remote config, cloud messaging, fcm]
---

# Firebase Knowledge

Scope: Firebase-specific guidance learned from supported source application evidence and accepted developer decisions. Status: initial entry point; no application-specific facts have been imported.

## What belongs here

- Scoped Firebase usage conventions and architecture decisions.
- Reusable implementation patterns supported by inspected source code.
- Tool-specific terminology, limitations encountered, and approved exceptions.

For each admitted finding, retain a stable ID, its scope, and revision-specific source or conversation evidence. Add focused documents when supported content needs them, and link them from this entry point. Do not infer a required application stack from this folder's existence.

Use [tool maintenance guidance](../../maintenance/tools.md). The [tool maintainer definition](../../agents/tool-maintainer.md) is instantiated with the Firebase path for this assignment. Shared definitions and policies belong in [core](../../core/terminology.md) when their scope warrants it.
