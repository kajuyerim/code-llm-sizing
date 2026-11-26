# Propose an application check from a sweep

Context Ops can propose one lint or test patch after either maintenance
strategy. A fresh, read-only check proposer uses the current sweep's validated
`ADD`, `UPDATE`, or `MERGE` records and their evidence. It can inspect the
application at the frozen revision and returns a Git diff. Context Ops checks
that diff in a disposable application worktree. The knowledge repository is
still the destination for the underlying decision.

## Choose when to run

Commit these settings to the knowledge baseline used by the sweep:

```yaml
checks:
  automatic: false
  agent: agents/check-proposer.md
```

Set `automatic: true` to run after the maintenance review and writer stage,
within the remaining sweep budget. Auto mode prepares the proposal even when
the sweep runs in the background. It does not run generated commands or apply
the patch to the developer's checkout. When automatic mode skips because of
cost, an explicit manual run can use a separate per-agent budget.

With automatic mode off, pass the completed run directory printed by
`contextops sweep` or `contextops run`:

```sh
contextops checks propose "$RUN_DIR"
```

The manual command uses the committed configuration from that run. Baselines
created before this feature need the agent and configuration before preparing a
new sweep. A sweep with no eligible decision produces a no-candidate record
without a model call. The check proposer uses the existing Claude runtime and
the selected authentication mode.

## Review, test, and stage a proposal

Inspect `check-proposals/proposal.json` and `check-proposals/check.patch` in
the run directory. The record includes the base revision, decision and
evidence locators, patch digest, passing and failing examples, and a suggested
verification command. The Git patch validation covers whether it applies
cleanly at the frozen revision. It does not establish that the check is correct.

Review the generated code and choose the exact trusted test command to run.
Verification applies the reviewed patch in a new disposable worktree and
executes only the command you supply. The subprocess runs with your local
permissions. Provide a command available in that worktree, with any necessary
dependencies already installed. The proposal's suggested command is never
executed automatically. The exit code and patch digest are recorded in
`verification.json`.

```sh
# Substitute the digest from the proposal you reviewed.
contextops checks verify "$RUN_DIR" "$PATCH_SHA256" -- python check_timeout.py
contextops checks apply "$RUN_DIR" "$PATCH_SHA256"
```

The verification command above is specific to the timeout example. The
`apply` command stages the exact reviewed patch in the original application
checkout. It requires a clean checkout at the frozen revision and refuses a
modified patch. Inspect `git diff --cached` before committing. Proposal
artifacts stay local and are excluded from knowledge review requests.

## Example decisions and expected behavior

| Decision | Proposed check | Passing example | Failing example |
| --- | --- | --- | --- |
| Set an explicit timeout on outbound calls through a known client | A lint rule scoped to direct calls through that client | `client.get(url, timeout=5)` | `client.get(url)` |
| Follow Conventional Commits | Configure a commit-subject linter already used by the application | `fix(api): handle timeout` | `handle timeout` |
| Keep user email out of logs | Detect an email field passed directly to the application's logger | `logger.info("Login completed")` | `logger.info({ email: user.email }, "Login completed")` |

A direct-call rule does not prove failure isolation or follow data through
arbitrary wrappers. Use a behavior test for failure isolation and extend a
lint rule's scope only with examples from the target application. The runtime
tests exercise the timeout proposal end to end with a deterministic agent
reply. The other examples illustrate the role's input and expected output.
