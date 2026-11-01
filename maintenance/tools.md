# Maintaining Tool Knowledge

This guide explains how to maintain documents under tools. Begin with the assigned tool entry point and examine the source repository, Git diff, and developer-agent conversation at the supplied revisions and cutoff.

## Placement and evidence

- Put tool-specific conventions, supported decisions, and reusable implementation patterns under the appropriate tool folder.
- Record the application or environment scope when a finding is not universal. Do not present one application's configuration as a tool-wide requirement.
- Check related core knowledge before adding an entry. Propose a core change to its owner when the concept is shared; do not independently duplicate or rewrite that document.
- Use repository evidence for implemented behavior and developer conversation references for intent, domain definitions, or accepted decisions. Check later corrections and distinguish rejected approaches from the final decision.
- A tool dependency alone does not prove active use. Lack of a change in the diff alone does not prove a stored fact remains correct.

## Update procedure

1. Locate existing knowledge for the changed component, terminology, or pattern and check its evidence.
2. Compare it with the current source snapshot, diff, and conversation. Preserve still-valid behavior when only one aspect changes.
3. Select ADD, UPDATE, DELETE, MERGE, NO_CHANGE, or NEEDS_REVIEW using the [operation definitions](core.md#choosing-an-operation).
4. Return the same [change record](core.md#change-record), with the exact assigned tool path as the target. Identify uncertainty and conflicting evidence explicitly.
5. Have the final writer combine proposals, preserve entry links and IDs, and update navigation/history where necessary.

When a new supported tool area is needed, propose a folder and entry point rather than moving unrelated knowledge into an existing tool. Avoid empty categories that have no concrete scope. Firebase and Dataform are the initial planned tool areas; their presence does not establish that a source application uses either one.

## Review

Check for duplicates, inappropriate generalization, stale examples, broken links, and claims based only on an agent's completion message. Defer unsupported new claims. Flag unresolved existing claims visibly, and do not label agent-generated changes as human-verified.

These procedures maintain tool knowledge. Agent assignments are defined in [the agent directory](../agents/README.md); setup is described in [the root walkthrough](../setup.md).
