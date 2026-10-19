---
name: create-github-issue
description: Create GitHub issues from requested work or an agreed plan, checking duplicates and applying the requested milestone, assignees, and dependency links. For planning or draft-only requests, prepare drafts without posting them.
---

# Create a GitHub Issue

Use the target repository named by the developer or resolve it from the working checkout's Git remote. Follow its agent instructions and writing conventions. Do not hardcode a repository, team, milestone, labels, or assignees from an earlier task.

## Inspect before creating

Verify the authenticated GitHub username with `gh api user --jq .login` when authorship matters. A requested author must match the account actually used; issue creation cannot impersonate another user.

Read existing issues, including closed ones, and available milestones. Search candidate duplicates by title and purpose, using pagination when needed. Reuse an equivalent record. Report a materially different existing scope rather than silently rewriting it or posting another copy.

Resolve requested assignees against the repository's eligible users. Leave issues unassigned when requested. If an assignee is unavailable, report that fact and follow any existing fallback instruction; do not invite collaborators or substitute an account automatically. Record requested issue reviewers as named body checkboxes rather than claim that pull-request review requests were created.

## Draft the issue

Keep the title concrete. Include the problem or goal, scoped deliverables, acceptance criteria, and dependencies. Preserve the requested flat issue versus parent/sub-issue structure. Use no em dashes in text authored for this bundle.

Apply only the requested milestone, labels, and assignees. Creating a new milestone is included only when the developer requests it; otherwise use the selected existing milestone or leave it unset. A batch request should create exactly the requested records.

## Create and verify

A request to create issues authorizes posting the specified issues. A planning or draft-only request produces drafts without external mutation. Existing authorization does not require a second confirmation. Do not implement issue contents or change unrelated repository settings.

Preserve multiline Markdown with a structured tool argument or a temporary body file passed to `gh issue create --body-file`. Avoid embedding issue bodies in shell command text. Use the authenticated CLI when the developer requests their own account as author.

Create dependencies using returned issue numbers rather than guessed numbers. If some target issues do not exist yet, add the exact links after their creation. If creation times out or its outcome is uncertain, reread the target repository before retrying so a successful first attempt is not duplicated.

Read back the resulting author, title, body, milestone, labels, and assignees. Report created or reused links and any metadata that remains unresolved. Remove no existing records as part of duplicate checking.
