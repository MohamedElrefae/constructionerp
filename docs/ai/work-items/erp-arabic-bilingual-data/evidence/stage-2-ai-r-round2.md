# Stage 2 Round 2 — Independent AI-R Verification

## Verification identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 2 verifier |
| Agent/session | `/root/stage2_ai_r_round2` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-04T21:56:18Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; changes remain uncommitted |
| Vendor commits | Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`; ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5` |
| Independence | This agent was not the Builder or an earlier reviewer. It did not modify implementation, catalogs, payload, database values, runtime translations, Git index/history, or existing evidence. This report is its only write. |

The mandatory repository memory recall was attempted after reading `AGENTS.md`; it failed because the local MemoryGraph environment lacks `pydantic_core._pydantic_core`. Live repository and site evidence were therefore used as authority.

## Exact reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `a77d33efcf2eb7a5df34c00f4ea2e22e9f8c76af25faa6d333d7caf05c3bc80b` |
| Stage 2 inventory narrative | `cb46a12c5c84223558380804713096b1a5fe8b1020c8346ca1bbd839da856b6d` |
| Stage 2 remediation record | `181e5867b5546fe087fe9958f72098ab107054419bace4d17087d1eee2d3c0ce` |
| Previous AI-R rerun | `449cae46d693d39dbf08d0dd96fb179a3f36bf74ae4b3919503b8319a4dd03a8` |
| Localization checker | `e88f6f5c7d5c767e20918dca8944d739681996d52c9d2a70d7c20f224f924f3a` |
| Adversarial tests | `a43b9ede80965a2abaf8af72ed371b2427850a253c6523d0e0bead0374e53b23` |
| CI workflow | `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Vendor delta tool | `d6651c86f96b76aba08fdeca71937e088028d6bac8dffc664e17e5216518f30f` |
| Freshness collector | `91b23bac5a36e8f6568bdaf3e71faa610243486044d452440f632a2d6254579d` |
| Construction PO | `3e9f7077b9b5155057b596b37f3d44559f3b8bd90ca58b9dcb5bb6fca7c3eeaf` |
| Released payload | `c81b41afc7a44d6e73045587091d544de486dab0d3a87325e60d1ceb1e7591cc` |
| Vendor baseline | `298876f2ef94af1ef6ecfb5ab0fb8c0100a484c9f50028da7fd62ac01d09aa54` |
| Localization manifest | `2f2dd89c1ed8cf274131e782262764f117e82c675b138e6572edca915ac3d25f` |
| Freshness evidence | `1bee1988eb8808f821ccf5ac5c8e21cac189096ff4942ccf485986fdba489112` |
| Stage 2 inventory manifest | `2635f6fbca7c7385bc177a8560b4a48030b0dc7e43fdc0bf79ba4ac6e44aa4d0` |

Durable Round 2 log hashes: full gate `557697c0...`, gate tests `a9a81ba6...`, scoped gate `5d555c3d...`, vendor audit `e3ea4f7c...`, sync `fedbbeb6...`, Merkle `6a4365ed...`, and freshness JSON `1bee1988...`.

## Independent execution and observations

- Full checker: exit `0`; Construction PO identities `720`; payload rows `34`; reported extraction `247` files / `591` unique wrapped literals / `0` missing.
- Standalone adversarial suite: 30 tests, `OK`; one `ResourceWarning` from an unclosed test fixture.
- Bench adversarial suite on `v16.localhost`: 30 tests, `OK`.
- `git diff --check`: exit `0` before this report.
- Vendor self-delta at the pinned Frappe commit reports `added=0`, `removed=0`, `changed=0`.
- Current dry-run, independently executed: `total=34`, `created=0`, `updated=0`, `skipped=34`, `drift=0`, `dry_run=true`.
- Current authenticated-site collector, independently executed, binds payload `c81b41af...` and PO `3e9f7077...`, reports `packaged_rows=34`, critical Arabic values 6/6, no health drift, and runtime digest `ce8e729f2f735dc745cf95cc9d2a59172a5bd15e11c6ce003456ca5b638ac843`.
- Frappe and ERPNext `ar.po` files have no local diff. No forbidden vendor edit was found.

The zero-drift dry-run and unchanged runtime digest do genuinely show that the payload's Round 2 metadata changes did not change the effective packaged runtime rows on the authorized test site. This live verification is valid, but the supplied durable `final-dryrun.txt` still records the superseded payload `7ba7902c...`, not `c81b41af...`.

## Seven-item closure matrix

| # | Required closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Reproducible GitHub CI with pinned Frappe/ERPNext siblings and correct path/ref behavior | **CLOSED by inspection** | `.github/workflows/linter.yml` checks Construction out at `bench/apps/construction` and sparse-checks the two sibling locale trees at the exact baseline commits. The checker fails if a vendor tree, Git HEAD, commit, or catalog hash differs. This corrects the prior single-checkout topology. A hosted workflow run is not supplied, so actual GitHub execution remains a residual risk rather than a local architecture blocker. |
| 2 | Full-class extraction, raw sinks, and reproducible `591 + JSON labels / 0 / 720` | **NOT CLOSED** | Full scan does reproduce `720`, `591`, and `0`, but the output does not count JSON labels at all; `wrapped=591` covers wrapper calls only. Unwrapped HTML/template text is not detected, Python user-facing sinks are not guarded, and JSON strings containing markup/code are explicitly deferred to later waves. More importantly, `SOURCE_SUFFIXES` is defined first with `.html/.vue` and immediately overwritten with `{.py,.js}`. Consequently `--files construction/www/login.html` fails as unhandled rather than checking it, while a workspace JSON is classified as a skipped non-localizable artifact and only fails because the resulting target set is empty. This is not the claimed changed-file coverage for templates/workspaces/reports/print/email. |
| 3 | Governed vendor add/change/remove/context-shift delta with commit pinning and dispositions | **NOT CLOSED** | Commit pinning and add/remove/translation-change calculation exist. There is no `context_shift` output or matching logic; a context move merely appears as unrelated add/remove rows. No governed vendor delta artifact or disposition is checked into the candidate. `--update-baselines` can replace both vendor baselines directly without requiring a completed delta or reviewed disposition, and the checker validates only the new snapshot. The self-delta proves parser execution, not upgrade governance. |
| 4 | Manifest v2 binds every source input to authenticated runtime/boot/live evidence | **NOT CLOSED** | The live collector provides useful PO/payload hashes, packaged count, runtime digest, six values, and health. However, `localization_manifest.json` contains only PO hash, payload hash, and timestamp; it does not contain the freshness-evidence hash, runtime digest, expected packaged count, expected critical mappings, site classification, or boot dictionary digest. The checker only matches two input hashes, trusts a boolean `critical_pass`, and checks `has_drift`; it does not validate the six values against expected Arabic, `packaged_rows`, runtime digest, loader/constraint/duplicate/null status, or evidence age/site. The artifact therefore can be altered or replaced without invalidating the manifest. The v16 decision not to use `.mo` age remains acceptable, but this contract is not the claimed end-to-end substitute. |
| 5 | `decision_ref` quorum/content/proposal binding and invalidation | **NOT CLOSED** | CSV schema, nonblank quorum fields, timestamp parsing, reviewer-name sanity, and referenced-file existence are enforced. `decision_ref` is only split and checked with `Path.exists()`. No referenced artifact hash, exact row identity/source/context/Arabic mapping, role-specific decision, confidence, proposal hash, or invalidation token is verified. Editing a referenced decision or changing a released row while retaining existing paths can pass. The six new rows point at review files that discuss the mappings, but the checker does not establish that binding. |
| 6 | Fail-closed changed/deleted/renamed/unsupported relevant-path routing | **NOT CLOSED** | Traversal and unapproved absent paths fail, and the empty checkable set fails. But the overwritten `SOURCE_SUFFIXES` breaks scoped HTML/Vue handling; workspace/report/print JSON outside `construction/data` is classified through the general `.json` skip path rather than as a localizable source; and `retired_sources.txt` is an unstructured path list with no enforced reviewer, reason, evidence hash, or expiry. Full scan and scoped scan therefore do not apply equivalent coverage to relevant source classes. |
| 7 | Thirty adversarial tests cover every gate; durable commands/timestamps/exit codes and coherent hashes | **NOT CLOSED** | Thirty tests pass, but they do not test CI checkout/ref behavior, context shifts/disposition enforcement, manifest-to-freshness evidence binding, expected runtime values/digest/count, decision content/proposal invalidation, HTML/Vue scoped routing, workspace JSON routing, raw template text, or a current payload dry-run. The Merkle and sync files are console transcripts without embedded command/start/end/exit fields, and freshness is raw JSON without command/exit metadata. `final-dryrun.txt` is stale at payload `7ba7902c...`. Evidence is also internally inconsistent: `stage2_inventory_manifest.json` records Construction PO hash `3aeb7203...`, while the current PO, localization manifest, and freshness input use `3e9f7077...`; its structured Construction category remains `729`, while `refresh_note` says `742`. |

## Findings by severity

### P0 — release blockers

1. **Extraction/routing false negatives remain.** The duplicate `SOURCE_SUFFIXES` assignment removes HTML/Vue from changed-file routing, and changed workspace/report/print JSON is skipped rather than analyzed under the source gate.
2. **Review evidence is not cryptographically or semantically bound to Released rows.** File existence is not decision/content/proposal binding and does not implement approval invalidation.
3. **Freshness manifest v2 is not actually an evidence manifest.** It does not bind the authenticated evidence artifact or its runtime/critical assertions, so CI cannot prove which live result was approved.
4. **Vendor delta governance is incomplete.** Context shifts and reviewed dispositions are neither represented nor enforced before baseline replacement.

### P1 — evidence and test blockers

5. **The 30-test claim overstates coverage.** Multiple mandatory gates above have no adversarial fixture.
6. **Current durable evidence is incomplete/incoherent.** The current `c81b41af...` zero-drift result is not durably logged, three evidence artifacts lack the required command/UTC/exit envelope, and the inventory manifest carries a stale PO hash and stale structured count.
7. **The advertised extraction count is underspecified.** `591` is unique wrapped literals, not “591 literals plus JSON labels”; the checker emits no JSON label count, preventing exact reconciliation.

### P2 — residual quality issue

8. The standalone tests emit an unclosed-file `ResourceWarning`. This does not invalidate test results but should be corrected.

## Decision

**BLOCKED — Stage 2 Round 2 is not verified.**

The candidate closes the CI sibling-checkout topology and independently passes its current local gate and 30 tests. The `c81b41af...` payload is runtime-inert on the authorized test site, the runtime digest remains `ce8e729f...`, and vendor POs are clean. Those facts do not close the Stage 2 release gate because items 2 through 7 remain materially incomplete or incorrectly evidenced. Stage 1C remains valid. Stage 3 must not begin under the locked sequence.

## Exact next gate

1. Remove the suffix-routing overwrite and add equivalent full/scoped tests for HTML, Vue, workspace/report/print/email JSON, and governed raw visible sinks; emit separate wrapped-literal and JSON-label counts.
2. Add explicit context-shift classification and require a hashed, reviewed delta/disposition before any vendor baseline update can pass.
3. Make manifest v2 hash the freshness artifact and bind expected site/environment, packaged count, runtime/boot digest, exact critical mappings, required health flags, and collection age; validate all fields fail closed.
4. Bind every Released row to immutable decision hashes and exact proposal/row identities, with role decisions and automatic invalidation after source/context/translation changes.
5. Make retired/deleted dispositions structured, reviewed, and hashed; ensure changed-file CI supplies rename/deletion paths and tests them.
6. Add adversarial fixtures for every item above; save durable standalone/Bench/CI-equivalent logs plus current `c81b41af...` dry-run/freshness/Merkle/sync records with command, UTC start/end, and exit code.
7. Regenerate the inventory manifest from one deterministic command so its PO hash, structured counts, Merkle root, narrative, and runtime counts agree, then request a fresh AI-R rerun.

Owner authorization remains separately required for commit, push, merge, deployment, or production mutation.
