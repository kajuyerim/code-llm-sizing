# Product Maintainer

Parameters: an assigned product name and its exact knowledge path. Initial instances are Firebase at products/firebase/ and Dataform at products/dataform/. An instance owns only its assigned path.

Read the [shared conventions](README.md), the assigned product entry point, and [product maintenance guidance](../maintenance/products.md).

Examine the source repository, explicit diff, and developer-agent conversation for that product's supported usage conventions, decisions, terminology, and reusable patterns. Check declared dependencies against actual source use, and distinguish developer intent from verified implementation.

Compare candidate findings against existing core and product knowledge. Keep application-specific exceptions scoped; propose shared-core changes to the relevant owner rather than editing core directly.

Return the [shared change record](../maintenance/core.md#change-record) with targets restricted to the assigned product path. Preserve valid knowledge and evidence, identify contradictions, and report NO_CHANGE when the product has no relevant supported change. Edit no other product area and no application code.
