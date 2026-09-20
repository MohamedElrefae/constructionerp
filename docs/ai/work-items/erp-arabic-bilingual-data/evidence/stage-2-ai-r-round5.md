# Stage 2 Round 5 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 5 verifier |
| Agent/session | `/root/stage2_ai_r_round5` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-05T09:18:15Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; changes remain uncommitted |
| Authority | Read-only/local-negative-fixture verification plus this report only. No code, catalog, payload, DB/runtime value, Git index/history, commit, push, deployment, or production state was intentionally modified. The standalone suite unexpectedly exercised the baseline writer; the verifier restored the two timestamp-only changes and confirmed both original hashes exactly. |

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `96a6175e753e24710e0d5c5b9b5f3756bdeff97f6124aa23b84142aa5e2456b2` |
| Round 5 remediation record | `52d26ea6e66acfbd277b6263c5837624f842f998a7ede058589dd26431cccbab` |
| Prior Round 4 AI-R | `00a958bc298c682acfba5855ff1a7df960923ea91cb9abd385ffc2484b611d8f` |
| Checker | `d821af1088699e302a697a5bba5d8ef0b7018a3fabbc94cd505310834cc9917d` |
| Vendor delta tool | `1a2fd009894afecb58db0437794e277c6fac5ca2dcf799cab078cbc33d61e2d5` |
| Adversarial tests | `c6847740ab1404ba4834adef00f71932abce16c8409cb136ab01da7299a00388` |
| Construction PO | `eec4078fda0c185777b768566225f5e574633ac846243d88e5d14b56edd046af` |
| Released payload | `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Release decisions | `b1e0c46a0b56f8b585ef1ff6982f65f239024537a835243bf8e247b1e7ff8638` |
| Legacy batch record | `fbbc5182789813f808476c09600e091beb7c7cdca180d0569d67cb8f84665c64` |
| Retired lifecycle | `52fa8e40a7c8131fc54b01e68805232e37bdd1cc427a26e6080e30e734ba3fb6` |
| Localization manifest | `9bd8af82e7af49bb6a97e3d14377e3c9a8a97ebb56fae522e0e435e69216df7c` |
| Freshness evidence | `7f4852f3192933e79745bdbad12660f871b4a0e2f09707da1dad6e6b97778d78` |
| Site classification | `0182069096821435f995338206b1030043413f14a69a01bd8609bb35e7a05b50` |
| Vendor baseline | `1017d21ddbb29f4848eff2e58f436b2782e6feedbc8585938dc1b2fc43cb5ac4` |
| Inventory manifest | `3bab6c2a963767dfa62d595c6f49acae8f25466d223e368716c397af469617ce` |
| CI workflow | `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |

Vendor commits match their pins: Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`, ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`. Both vendor Arabic PO paths are Git-clean.

## Independent execution and reconciliation

- Full gate: exit `0`; catalog `770`; source files `247`; wrapped `630`; JSON labels `21`; missing `0`; raw-template files `7`, raw texts `2`, raw missing `0`.
- Vendor coverage audit: exit `0`.
- Standalone adversarial suite: `54` tests, exit `0`.
- `git diff --check`: exit `0` before this report.
- Independent test-site payload dry-run: `total=34`, `created=0`, `updated=0`, `skipped=34`, `drift=0`.
- Saved Bench evidence reports the same `54` tests green and the six-module aggregate as `89` tests, zero failures. It was not accepted as sufficient proof of a side-effect-free verification suite because one test invokes `--update-baselines` against the real checkout.
- Inventory Merkle prefix is correct: `7f15e19e…`. However, the manifest contains `18,411` rows (and its category totals also sum to `18,411`), not the remediation record's claimed `18,455` rows.
- Ten files exist under `evidence/raw-logs/stage2/`; their hashes were recomputed. They are not ten complete command/UTC/exit/hash envelopes: `freshness.json` has no command/start/finish/exit envelope, `lints-diffcheck.txt` has no `EXIT_CODE`, and `merkle.txt` contains a truncated `INV5` line and no manifest/artifact hash. Most remaining files do not bind the material artifact hashes they claim to evidence.

## Round 5 closure matrix

| # | Required closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Raw Jinja/HTML/template and Python user-visible sinks fail closed; service internals narrowly dispositioned | **NOT CLOSED** | Current governed templates pass, but `construction/print_format/...json` and workspace markup are explicitly skipped. A temporary fixture containing `frappe.throw(\n "Raw multiline visible error"\n)` produced `hits=0`, `errors=[]`. Thus a real multiline literal sink still bypasses the gate. Dispositions are Builder-authored mutable text, duplicated in places, and not hash-bound to locations/content. |
| 2 | Vendor add/change/remove/context-shift deltas are recomputed from immutable inputs; every baseline write requires exact reviewed evidence, including same-commit/direct overwrite | **NOT CLOSED (P0)** | A temporary isolated fixture reproduced the bypass. With vendor commit unchanged, working-tree PO hash changed, and a reviewed artifact claiming an empty same-ref transition, `update_baselines()` returned `0` and wrote the altered baseline. The recomputation reads `git show SAME:SAME`, so it cannot see the changed working-tree PO being blessed. The reviewed artifact's `old_po_sha/new_po_sha` strings are compared but not derived from immutable old/new blobs plus the current file. |
| 3 | Decisions bind canonical row identity, source/context/app/proposal/translation/verdict/artifact hashes and auto-invalidate | **PARTIALLY CLOSED** | The decision key now binds language/app/context/source/translation/reviewers/timestamps/version and referenced artifact SHA; payload or evidence edits invalidate the key. However, no independently signed/root-pinned decision artifact exists, the stored decision object is not validated against its key, and verdict/domain/reference semantics are not part of the canonical identity. This is materially stronger than Round 4 but does not satisfy the stated complete binding claim. |
| 4 | Legacy migration is hash-pinned, count-correct, immutable, and cannot authorize altered rows | **CLOSED for current 28 rows, with governance residual** | The record pins the historical sign-off SHA and lists exactly 28 source rows; `34 - 6 = 28`. Current release-decision keys prevent altered payload rows from matching. Residual: the legacy scope is source-only and the record itself has no external immutable root, but current row decisions compensate for payload identity changes. |
| 5 | Freshness enforces site classification, future/stale evidence, exact inputs/runtime digest/count/critical values and complete health policy | **PARTIALLY CLOSED** | Current evidence and manifest match; critical mappings and required health booleans pass. Remaining fail-closed gaps: up to five minutes in the future is accepted; the manifest does not bind `site_classification.json`; `production_mutation_authorized` is not checked; `packaged_rows` is not reconciled to current CSV Released-row count; and health timestamps/constraint identity are not required. |
| 6 | Versioned retired lifecycle enforces delete/rename/replacement/evidence transitions | **NOT CLOSED** | The seven-field parser validates useful basics, but the active registry is empty. A temporary fixture `delete | <existing old file> | arbitrary-new-value | ...` was accepted with no errors. Delete does not require `new_path=-` or old-path absence; rename chain validation is order-dependent; evidence hash pins remain optional; reviewer/evidence semantics are not content-bound. |

## Severity findings

### P0

1. **Same-commit vendor PO overwrite can still be re-baselined with a misleading empty reviewed delta.** This directly reopens the Round 4 critical bypass and means vendor additions/changes/removals/context shifts can be hidden from triage.

### P1

2. **Raw Python multiline user messages still bypass detection; embedded print/workspace markup is explicitly skipped.** The Stage 2 acceptance statement therefore remains false-negative.
3. **Retired lifecycle accepts invalid delete transitions.** It does not yet prove delete/rename/replacement governance end to end.
4. **Durable evidence is internally inconsistent/incomplete.** The inventory is `18,411`, not `18,455`; three of ten files are visibly incomplete envelopes; the claimed exact envelope gate is not met.
5. **The adversarial suite mutates baseline/manifest timestamps in the actual checkout.** `test_baseline_refuses_without_delta` calls the writer on live paths and merely accepts either return code. This is not a valid negative assertion and makes a verification run stateful. The verifier restored hashes `1017d21…` and `9bd8af82…` exactly after observing this behavior.

### P2 / residual design risks

6. Decision and freshness binding are improved but do not fully cover verdict semantics, decision-root immutability, site-classification hash, exact future rejection, and CSV/runtime count reconciliation.

## Decision

**BLOCKED — Stage 2 Round 5 is not independently verified.**

The live headline counts (`770`, `630 + 21`, zero reported missing), current payload dry-run, vendor cleanliness, and the existing green tests are real. They do not close the reproduced P0 vendor re-baseline bypass, multiline/raw-source bypass, invalid retirement transitions, or evidence-integrity failures. Stage 1C remains valid. Stage 3 must not begin.

## Exact next gate

1. Recompute the vendor delta against immutable baseline content (stored blob/object hash or pinned old PO artifact) **and the exact candidate PO bytes**, not merely old/new Git refs. Require exact per-item dispositions and a hash-bound reviewed artifact for every PO-byte change, including dirty/same-commit candidates.
2. Replace line/regex-only Python sink checking with AST/token-aware call inspection covering multiline literals, concatenation, aliases, variables and f-strings; either scan embedded print/workspace markup or govern each exclusion with location/content hash-bound evidence and a fail-closed test.
3. Enforce delete (`new_path=-`, old absent), rename/replacement linkage, evidence SHA, order-independent chains, reviewer/date/content binding, and real routing fixtures.
4. Make all localization tests temporary-root/read-only. A negative baseline test must assert refusal and must never write candidate files.
5. Regenerate the inventory and exactly ten complete envelopes with full command, UTC start/finish, exit code, and relevant artifact hashes; reconcile `18,411` versus `18,455` and rerun the 54 standalone/Bench tests plus the 89 aggregate.
6. Bind and validate the site-classification hash, strict non-future timestamp, CSV Released count, full health identity/timestamps, and canonical decision/verdict record. Then request a fresh independent AI-R rerun.

Owner authorization remains separately required for commit, push, merge, deployment, or production mutation.
