# Local web console

Run `./start-ui.sh` from the project checkout after installing the runtime
with [setup](../setup.md). The script uses the checkout's virtual environment
or the installed command. From an installed package, run `contextops ui`.
Both open an authenticated loopback-only page. Keep the launcher running while
using the browser. The console uses the existing private provider login.

## Set up a project

Choose the application and knowledge checkouts under **Setup**. Use the header project menu to switch projects. Use an
existing knowledge baseline or initialize a new branch, review the local
changes, and commit them from the page. The project list is stored locally
under `~/.contextops`; the binding is read from the application's Git
configuration. The default connection leaves the pre-push hook disabled.

Scan the committed application snapshot for broad knowledge categories. The
scan can include selected Claude Code sessions. The strongest recommendations
are selected by default. Open any category to see what it collects and why it
was suggested, then adjust the selection or add a category of your own.
Save the profile on the application or team scope and review and commit the
configuration. An application override takes precedence over the team default.
The sweep freezes its profile against the committed knowledge baseline. A
proposal for a disabled category is recorded as rejected. An unclassified
proposal is deferred. A checkout with no profile uses its existing policy.
The editable category discovery role is in `agents/profile-discovery.md`.

## Run and review

Open **New sweep** under **Agents** and choose an application branch and the
development sessions. The console previews the range before starting. For a
new branch or unavailable checkpoint, it uses the latest branch change.
After a successful sweep, it resumes from the last confirmed commit for the
branch and profile. If the sweep wrote knowledge, its commit must be present
in the selected knowledge checkout's history. **Sweep defaults** under
**Setup** holds the strategy, backend and optional model override. Both maintenance backends still read selected
Claude Code development sessions. The console records user-visible agent
events in the run directory and replays them when a run is reopened. Raw
provider logs and reasoning stay outside the browser stream. **Agents** shows
the outcome and the evidence behind the decisions. Browser-started sweeps
retain output locally.

In **Agents**, **Review changes** opens that sweep's knowledge diff in a
dialog. Choose a changed file to see its additions and deletions. Use **Open
full review** to carry the selected sweep and file to **Review**, or select
a sweep directly from **Review**. The optional application lint or test
proposal has its own section there. Review its patch, pass the exact
verification command as an argument array, and explicitly stage the reviewed
patch. The command runs with your local permissions in a disposable
worktree. See [application checks](application-checks.md).

## Browser acceptance

The deterministic browser acceptance uses a separate checkout of
[MarkupSafe 3.0.2](https://github.com/pallets/markupsafe/releases/tag/3.0.2)
at `28ace20b140d15c083e1cbc163ee6b7778ba098c` plus a local documentation
commit. A synthetic session states a compatibility decision for the exercise.
The browser connects both repositories, initializes the knowledge branch,
scans categories, saves the profile, runs a sweep, and opens the knowledge
diff. A second candidate from an unselected category is rejected. Replaying
this fixture with simulated model messages establishes UI and runtime wiring.
Provider authentication and live generated output require a separate run.

## Inspect a finding

The evidence graph links a cited source to the specialist who proposed the
record and to its review outcome. Select an agent, evidence type, or verdict
to filter the findings. Open a finding to read its text, the decision reason,
and the cited excerpt. The writer consumes accepted records. A written record
is linked to a file diff when the writer receipt and the patch both support
the link. **Review** also shows recorded diffs from older runs without a
writer receipt.
