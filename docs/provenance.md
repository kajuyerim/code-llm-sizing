# Walkthrough provenance

The approved source was the English meeting walkthrough `2026-10-30-ContextOps-Test-Akisi.html`, preserved outside this repository. The published [HTML](walkthrough/index.html) retains its continuous 12-scene presentation and embedded evidence. The [English companion](walkthrough/README.md) adapts the embedded English reading text with corrected Markdown tables and portable navigation.

| Item | Value |
| --- | --- |
| Original SHA-256 | `1a09311a979a6edb58dfd68ecfa07da5a0083f97824fdf560ed5ffd81714946e` |
| Published SHA-256 | `ad025eb6fc8366342a58b190f5c136d0e244dba4bcd539bc6bac8b8e7a627e17` |
| Case | Actual Budget P3 |
| Source base | `855b028a1d290be3b4dd028e1f9a7cd9a9bb9d05` |
| Source head | `339775346c57a10565768453233860a4f7c669fc` |
| Conversation | 53 normalized messages |
| Conditions | Claude A, Claude B, GPT A, GPT B |
| Human sign-off | Not recorded |

Publication replaces the original personal absolute workspace prefix with `/workspace/contextops-eval` everywhere it occurs. That path is an anonymized evidence label, not an installation path. No messages, IDs, ordering, source revisions, judgments, accepted records, or patches were otherwise changed. The approved original is unchanged. The HTML also preserves the original Turkish prose as archival data; the displayed reading companion and standalone companion are English.

The canonical external evaluation export is `contextops-gpt-eval/report/data.json`. The walkthrough's four accepted-record arrays, patches, judgments, and base/head match its Actual P3 case, subject only to the documented path transformation. The full export, full report, raw runs, application stores, and evaluation fixtures are deliberately not imported.

The pilot used `products/` and `product:`. Current code uses `tools/` and `tool:`. Archived paths and scope labels are historical evidence and must not be silently migrated. The integrated shared specialist prompts are a new configuration; these old scores do not evaluate the new revision.

Original runtime branch checkpoints are B `7ca68b207a76e10769d6403ce18f7deb4fb7a72d` and A `536144fba5a186847fba5ad0c764c4bbc9cd9137`, both based on foundation `fdecc8273f2cff6b4c6c6477e7cd4c505a271354`. The GPT replay used a separate adapter. It is not bundled as a supported backend here.
