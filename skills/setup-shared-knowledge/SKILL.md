---
name: setup-shared-knowledge
description: Connect an existing application repository to this shared-knowledge bundle and prepare manual documentation maintenance. Use when asked to set up or onboard an application with the bundle.
---

# Set Up Shared Knowledge

Resolve the bundle root from this repository-local skill: it is two directories above this file and contains setup.md and index.md. Read the [setup walkthrough](../../setup.md) and follow its applicable steps. Keep the bundle together; if the skill was copied alone, locate the intended knowledge checkout before proceeding.

Use existing session context for the application path, knowledge path, selected products, evidence export, and strategy. Ask only for missing choices that affect the requested setup. Do not add a second approval step when the developer has already requested the relevant documentation setup.

Preserve existing source-project agent instructions and knowledge integrations. A new subtree integration or external publication is not implied by a request for local documentation setup. Keep application source unchanged; setup may add the authorized knowledge reference to the application's instructions.

Report configured references, selected knowledge/roles, evidence availability, and unfinished integration. The current bundle supports manual procedures, not a maintenance runner or automatic pre-push hook. Reading this skill does not itself configure automatic discovery or authorize changes to an unspecified application.
