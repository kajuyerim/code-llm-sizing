# Demo preparation verification

## Status

On 16 November 2026, the manual demo was prepared from a clean local clone of `feat/team-knowledge-loop` at `34f4d386fbc0684273ded7959e5894b567979e2c`, with a fresh virtual environment. This revision includes the report corrections and leaves the runtime and default configuration unchanged from `e7e095b`.

**Preparation passed without authentication or inference. No new knowledge was generated.** Historical live acceptance at `caf4bdb` and `b20f3f9` is documented in the [acceptance records](../first-run-acceptance.md). A fresh live run on the current policy, and acceptance on a user's own application, remain pending.

## Reproduction and observations

Follow [the demo guide](README.md#prepare-without-inference) through step 5. For this verification, the implementation was cloned locally because the report commits were not pushed. Public application source and pinned dependencies were fetched over the network. All writable fixtures, imported demo history, the virtual environment, and run artifacts were in a disposable parent outside both working repositories.

| Check | Observed result |
| --- | --- |
| Environment | macOS 26.7.1 arm64; Python 3.14.5 |
| Installation | Fresh virtual environment; lock-file install and editable runtime install succeeded; `pip check` reported no broken requirements; CLI help succeeded |
| Software tests | All 51 deterministic tests passed in 20.462 seconds in the fresh environment; fake agents only |
| Documentation | 36 Markdown documents checked, zero findings; historical patch hashes and cited message IDs independently verified |
| Public/history scan | Six PDF-only manual-review flags; no credential-pattern findings; unresolved publication check |
| Application reconstruction | All eight supplied commits applied to upstream `d9d15c12fa41a0bb8380fab09519e0180333e146`; seven development commits selected after the setup commit |
| Source base | `c9ec8e97da4d8eb96630fee0f7716389c8a061f5` |
| Source head | `8cece049fa39354313e70b8719c958b5d16755d8` |
| Source head tree | `f53804376c1c736b7dc20b2840f9a944a71c4232`, matching the recorded demo tree |
| Knowledge baseline | `66421071ccc7ac52ea873d510ee4e9039fd0ea8c`; four blank core templates, team scope, application label `actual` |
| Configuration | Existing default model `claude-sonnet-5-5`; estimated thresholds $1.50 per agent / $10 aggregate; `open_pr: false`; auto-memory disabled; external run directory |
| Conversation | Six explicitly selected sessions; cutoff `2026-11-05T18:40:03Z`; 445 normalized messages |
| Frozen conversation SHA-256 | `a8b827a32232e8df9fb9850b8dec85e6624d306c3d43015099b0416fbd5e10a7` |
| Preparation boundary | `run.json` and frozen conversation created; no `started` marker, completion report, or result branch |
| Preservation | Application HEAD/tree and working files unchanged; baseline still selected; original implementation branch preserved; supplied inputs unchanged |
| Authentication and history | No authentication stores read or copied; only the isolated demo history selected; no live model calls or hook installation |

The baseline and conversation hash identify this particular preparation, not universal expected values. The baseline includes local run-directory configuration and commit metadata; normalized conversation text includes reconstructed local paths. Other directories can therefore produce different hashes. The upstream tree and supplied evidence are the stable reconstruction checks.

The test suite covers initialization rejection, successful fake writing, legitimate no-change/deferred results, missing sessions, invalid refs, budget exhaustion, writer failure and candidate patches, unchanged source files, and preserved baseline checkout. These are software checks, not evidence of generated-knowledge quality. No dependency/model compatibility beyond this installation and these credential-free checks is claimed; live model access remains untested.

## Historical evidence and remaining checks

The [revision-specific patches](../first-run-acceptance.md#historical-patch-provenance) were recovered from their publication commits and checked byte-for-byte. The existing application patch, six exported sessions, and legacy second-result patch were preserved. The demo guide points to actual recorded knowledge rows and stable message IDs rather than promising that current policy will reproduce fifteen entries.

The documentation and public-file checks are run separately from inference. The public/history checker still requires manual review of the midterm and supplement PDF binaries, including historical versions. That is an unresolved report/publication check, not a credential detected in this preparation, and the check has not been bypassed. This record does not claim a green full CI run or production readiness.

The prepared `contextops run ...` command is retained with the private local verification artifacts. It has **not** been executed. The demo guide prints the corresponding exact command for each new preparation. Changes to authentication mode or other configuration require a new committed baseline and a fresh prepared run; no automatic retry or publication is part of this verification.
