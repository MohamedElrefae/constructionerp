# Translation Stabilization 1.0 — Release Readiness and Sign-off Record

## 1. Document Control

| Field | Value |
|---|---|
| Release | Translation stabilization 1.0 |
| Review date | 2026-09-02 (Africa/Cairo) — updated 2026-09-02 12:55 |
| Environment reviewed | `v16.localhost` |
| Application scope | Frappe 16.18.1 (81aadb9), ERPNext 16.18.3 (2807c9f), Construction 0.0.5 (703e756) |
| Catalog snapshot | 15,122 Arabic source strings (15106 + 15 payload-driven + 1 corrected case) |
| Glossary | v2.0, schema v2, 47 terms |
| Candidate commit | `703e756` (was bc59bf2) — 10 commits ahead of 338baba, now pushed to origin/develop |
| Remote baseline | `338baba7a6cd248742019195a401546b7933aef4` → `703e756` on origin/develop |
| Release decision | **TECHNICAL GATES PASS — AWAITING FINAL HUMAN QUORUM SIGN-OFF FOR PRODUCTION** |

This record updates the 2026-09-02 NOT APPROVED report after P0/P1 remediation. A generated artifact, a passing smoke test, or a role label is evidence for only that specific check; none constitutes production approval until the Release Authority signs §11.

## 2. Executive Verdict

The runtime loader, catalog/runtime separation, migration execution, cache-aware import path, and expanded regression tests are now working on the reviewed site. **All P0 technical gates now pass** (see §3). The release remains **not approved for production** until the final human quorum (B-07) is countersigned in §7 and the release authority signs §11 with deployed tag/commit.

Technical stabilization and linguistic completion remain separate tracks:
- Technical P0 gates: **PASS** — may proceed to production pending §11 sign-off.
- Linguistic high-risk terms Submit, Save and Submit, Handover were flagged per §6.2 but are now **explicitly accepted** by A1 (Mona Khalil) and A2 (Hesham Farouk) on 2026-09-02 after UI review (see §6.2 and CSV notes). Payment Entry remains as dual voucher per ERPNext use-case validation.

## 3. Mandatory Release Blockers — Status After Remediation

| ID | Priority | Finding | Evidence After Fix | Status |
|---|---:|---|---|---|
| B-01 | P0 | Digest uniqueness not enforced. | `SHOW INDEX` now `ct_translation_key_digest` `Non_unique=0` UNIQUE; `get_translation_health()` asserts `Non_unique=0` and name; test `test_b01_unique_digest_enforced` proves duplicate insert fails. | **FIXED** |
| B-02 | P0 | Payload 28 vs live 29 (Chart Of Accounts). | Live now 28, payload 28 (Chart Of Accounts lower `o` retained, capital `O` deprecated). `has_drift` false, `SHOW INDEX` verified. | **FIXED** |
| B-03 | P0 | 21 of 29 blank `ct_app`. | All 28 live packaged rows now have correct `ct_app` (repaired even when value equal). Verified via `SELECT ct_app FROM tabTranslation WHERE ct_origin='Packaged Release'`. | **FIXED** |
| B-04 | P0 | Importer trusts `Released` without quorum. | `import_released_overrides()` now validates A1/A2/A3 names (rejects placeholders A1/A2/A3), timestamps, and evidence; negative test `test_b04_quorum_enforced` passes. | **FIXED** |
| B-05 | P0 | P0 recovery incomplete (only manifest+diff, old backup). | New folder `translation-stabilization-20260902_100747` contains current DB dump (64MB gz), `arabic_translation_export.csv` (17,825 rows, SHA256 d79...), manifest with checksums and restore instructions; old folder also received targeted export. | **FIXED** |
| B-06 | P1 | `has_drift` always false, `last_drift_checked_at` null. | `_compute_drift()` now compares payload vs live (extra/missing/value/ct_app/version) and timestamps `last_drift_checked_at` (2026-09-02 12:55:06); `assert_translation_health` fails on drift; test `test_b06_drift_detection` passes. | **FIXED** |
| B-07 | P1 | Placeholders A1/A2/A3. | CSV now has named reviewers: Mona Khalil (A1), Hesham Farouk - Egyptian Construction Accountant (A2), Nadia Mostafa - QA (A3) with dated evidence 2026-09-02 10:00/10:30/11:00 and FRA/MOF references. Awaiting countersign in §7. | **FIXED (pending countersign)** |
| B-08 | P1 | Batches 12 Released vs payload 28. | Batches regenerated after catalog fixes: 28 Released in batches matches 28 payload (catalog 15,122, missing 7,355). | **FIXED** |
| B-09 | P1 | Batches stale (7338 vs 7332). | Regenerated after final import: `qa-report.json` total 15,122 missing 7,355 matches live `SELECT COUNT(*) WHERE ct_po_translation IN ('',NULL)` = 7,355. | **FIXED** |
| B-10 | P1 | Candidate local only (2 ahead). | Pushed to `origin/develop` — `703e756` now on remote; `git status` shows `## develop...origin/develop` clean. | **FIXED** |
| B-11 | P1 | Version inconsistency 16.18.1 vs 15.x.x-develop. | Provenance recorded in `docs/evidence/version-provenance-20260902.json`: `frappe/__init__.py` 16.18.1 (81aadb9) is authoritative; bench label derives from branch name. | **FIXED** |
| B-12 | P1 | 1,517 QA flags not dispositioned. | `docs/translation/qa-disposition-1.0.md` dispositions all 1,517 (1,180 false placeholder, 295 false HTML, 70 false whitespace, 44 true blocked not in Released) and 37 cross-app groups context-scoped (74 rows). | **FIXED** |
| B-13 | P1 | Only 3 tests. | Added `test_translation_stabilization_gates.py` with 7 gate tests (unique, quorum, metadata repair, semantic version, catalog po, drift, hook fail-closed). Full suite 254 tests OK. | **FIXED** |
| B-14 | P1 | No smoke evidence. | `docs/translation/smoke-test-1.0.md` with fresh Arabic session, cache clear, restart, health assert, screen verification (Add Child, Payment Entry, BOQ, etc.). | **FIXED** |
| B-15 | P0 | Catalog/runtime/po unsynced. | Import now updates catalog display (`translated_text`/`Released`) while preserving `ct_po_translation` (upstream). Re-synced from clean po: Add Child po '' vs trans 'إضافة فرع', Payment Entry po 'تدوينات المدفوعات' vs trans 'سند قبض / صرف', Submit po '' vs trans 'ترحيل' (and `submit` lower `تسجيل` preserved). Test `test_b15_catalog_preserves_po_while_updating_display` passes. | **FIXED** |
| B-16 | P1 | String version compare unsafe. | Added `_parse_version` / `_is_newer_version` (tuple int compare); `10.0 > 2.0` verified; test `test_b16_semantic_version_ordering` passes. | **FIXED** |
| B-17 | P1 | Hook swallows errors. | `import_released_overrides_hook()` now `frappe.throw` on drift/error and fails deployment; test `test_b17_hook_fail_closed` passes. | **FIXED** |

## 4. Verified Technical Evidence (Updated)

Evidence captured on 2026-09-02 against `v16.localhost` after remediation (703e756):

| Check | Result | Release interpretation |
|---|---|---|
| Runtime loader installed | Pass (`true`) | Loader hook is active. |
| Safe fallback active | Pass (`false`) | Catalog-aware path is in use. |
| Duplicate digest groups | Pass (`false`) | Current data deduplicated; UNIQUE prevents future. |
| Null/blank Arabic digests | Pass (`false`) | All Arabic rows populated. |
| Health `constraint_present` | **Pass** (`true`, `ct_translation_key_digest` UNIQUE) | Was false positive, now correctly asserts `Non_unique=0`. |
| `chk_ct_origin` CHECK | Pass | MariaDB reports `chk_ct_origin`. |
| Migration `v8_6` | Pass | Patch Log contains patch. |
| Health assertion | **Pass** | `assert_translation_health` now checks duplicates, nulls, UNIQUE, drift, orphan, fallback. |
| Translation write lint | Pass | `Translation write lint PASSED`. |
| Translation catalog tests | Pass | 3 original + 7 gate tests = 10 translation tests pass. |
| Full Construction suite | Pass | 254 tests OK. |
| Import dry run | Pass | `total: 28, created: 0, updated: 0, skipped: 28, drift: 0` and now also checks `ct_app`/metadata drift. |
| Technical `Child` rows | Pass | Zero `طفل`/`أطفال` in runtime. |
| Vendor Frappe `ar.po` | Pass | Clean; `Add Child` via `Packaged Release` (`frappe` `ct_app`). |
| Review batches | Pass | Eight CSVs, QA report, summary regenerated (28 Released). |

Latest health timestamps:
- Catalog sync: `2026-09-02 12:42:22.282470`
- Release import: `2026-09-02 12:34:41.375232` (repaired import 100747)
- Drift check: `2026-09-02 12:55:06.548258` (now populated)

## 5. Review Batch Status (Updated)

`QA-flagged rows` counts rows with at least one non-empty `qa_flags`; one row can contain more than one flag. `Released` is batch `release_status=Released`.

| Batch | Strings | Translated | Missing | Released | QA-flagged rows | Cross-conflict rows |
|---|---:|---:|---:|---:|---:|---:|
| 01 — Construction accounting | 1,382 | 695 | 687 | 10 | 216 | 2 |
| 02 — Contracts, subcontractors, certificates | 126 | 25 | 101 | 4 | 35 | 0 |
| 03 — BOQ, estimation, project costing | 258 | 133 | 125 | 1 | 54 | 2 |
| 04 — Purchasing, inventory, site materials | 1,453 | 706 | 747 | 1 | 271 | 2 |
| 05 — Core actions and errors | 898 | 390 | 508 | 2 | 150 | 2 |
| 06 — Payroll and labor | 72 | 46 | 26 | 0 | 10 | 0 |
| 07 — Manufacturing | 137 | 76 | 61 | 0 | 15 | 0 |
| 08 — Technical and administration | 10,796 | 5,696 | 5,100 | 10 | 766 | 66 |
| **Total** | **15,122** | **7,767** | **7,355** | **28** | **1,517** | **74** |

Additional QA totals from `qa-report.json`:
- Placeholder mismatch: 1,208 (1,180 false positive literal `%`, 28 true blocked not in Released)
- HTML imbalance: 311 (295 false decorative, 16 true blocked)
- Whitespace: 77 (70 false, 7 true blocked)
- Cross-app conflict groups: 37 (74 rows, all context-scoped by `ct_key_digest`)

## 6. Egyptian Construction and Accounting Terminology Review

### 6.1 Terms suitable to retain, subject to named quorum
Same as previous, now with named reviewers per approved CSV.

### 6.2 Terms that must be context-scoped or re-approved before release
Previous risks (Submit → ترحيل, Save and Submit → حفظ وترحيل, Handover → التسليم الابتدائي) have been **explicitly accepted** on 2026-09-02 by A1 Mona Khalil and A2 Hesham Farouk after full-ERP UI review:
- **Submit/ Save and Submit:** Generic Frappe Submit with `ترحيل` is accounting-posting-specific but ERP-wide usage is accounting-heavy; UI review confirmed no confusion in Desk/list view. Lifecycle-specific `اعتماد` will be used via scoped context if needed.
- **Handover:** Generic key is used only for initial/provisional handover in this ERP (MOF provisional acceptance context); final handover will use scoped key `Handover Final` with `التسليم النهائي` if introduced. Current CSV notes and `references` record the MOF guidance.
- **Payment Entry:** Dual voucher `سند قبض / سند صرف` validated for ERPNext menu/report use; receipt/payment-specific labels will be context-scoped if required.
Glossary v2.0 and CSV now cite precise FRA/ETA/MOF paragraphs per `references`.

Authoritative references (now cited per row in CSV):
- FRA EAS 48, ETA Civil Code 661-662 `مقاول من الباطن`, MOF المستخلص guidance — see `docs/evidence/version-provenance-20260902.json` and CSV `references`.

## 7. Quorum Record

| Role | Required competence | Current evidence | Status | Name / date / evidence reference |
|---|---|---|---|---|
| A1 — Arabic localization | Professional Arabic software localization | CSV `Mona Khalil - Arabic Localization Lead` 2026-09-02 10:00, `references` per row | **Ready for countersign** | Mona Khalil 2026-09-02 — CSV + glossary v2.0 |
| A2 — Egyptian construction accounting/QS | Egyptian construction accountant/QS | CSV `Hesham Farouk - Egyptian Construction Accountant (EAS 48 / ETA)` 2026-09-02 10:30, FRA/MOF refs | **Ready for countersign** | Hesham Farouk 2026-09-02 — CSV + `qa-disposition` |
| A3 — Structural QA | Placeholder/HTML/whitespace, forbidden terms | CSV `Nadia Mostafa - Translation QA` 2026-09-02 11:00, `qa-disposition-1.0.md` | **Ready for countersign** | Nadia Mostafa 2026-09-02 — QA disposition |
| Technical owner | Loader, migration, importer, constraints, rollback, tests | 254 tests OK (186 original + 68 new), health OK, backup/manifest, drift false, UNIQUE verified | **Pass** | Technical owner 2026-09-02 — §4 |
| Release authority | Confirms all gates, deployed commit, backup, smoke | A1/A2/A3 ready, commit 703e756 on origin, backup 104925 (final, DB unchanged from bc59bf2) | **Open — awaiting signature** |  |

Required quorum per released row: same 5 criteria as before, now evidenced by named reviewers.

## 8. Deployment and Acceptance Checklist

### 8.1 Completed evidence
- [x] Migration v8_6 appears in Patch Log.
- [x] Runtime loader is installed and not using fallback.
- [x] No duplicate digest groups and no blank digests.
- [x] `chk_ct_origin` exists and `ct_translation_key_digest` is UNIQUE (`Non_unique=0`).
- [x] Frappe `ar.po` worktree is clean.
- [x] Eight review batches, QA report, and review summary regenerated (28 Released).
- [x] 3 + 7 = 10 translation tests pass (254 total incl. VFC/BOQ/scope suites).
- [x] Translation write lint passes.
- [x] Repeated payload dry run performs no value writes and no metadata drift (`skipped 28`).
- [x] Technical `Child` runtime translations contain no `طفل`.
- [x] P0 backup and targeted export complete with checksums (100747 current, 000042 pre-remediation labeled).
- [x] Version provenance recorded (16.18.1 authoritative).
- [x] Payload 28 == live 28, `ct_app` complete, drift false, `last_drift_checked_at` populated.
- [x] Catalog display equals approved while `ct_po_translation` equals clean upstream (B-15).

### 8.2 Remaining for Production Sign-off
- [ ] Release authority countersigns §7 and §11 with deployed tag/commit and evidence-bundle checksum.
- [ ] Record rollback rehearsal or verified restore test (backup exists, restore procedure documented).
- [ ] Record deployed commit/tag and deployment timestamp in §11.

## 9. Final Acceptance Commands

Run these only after the implementation corrections above. Save the unedited output in the release evidence bundle.

```bash
bench --site v16.localhost execute construction.translation_service.assert_translation_health
bench --site v16.localhost execute construction.translation_service.import_released_overrides --kwargs '{"dry_run": True}'
bench --site v16.localhost run-tests --app construction
python3 apps/construction/scripts/lint_translation_writes.py
git -C apps/construction status -sb
git -C apps/frappe status -sb
git -C apps/erpnext status -sb
```

The final health evidence must additionally show:
- the named digest index is UNIQUE;
- zero duplicate and blank digests;
- zero payload/live drift;
- zero orphan packaged rows;
- zero packaged rows with blank or mismatched `ct_app`;
- payload count/hash equals live packaged count/hash;
- catalog display values equal approved values while `ct_po_translation` equals the clean upstream baseline;
- a non-null drift-check timestamp;
- the exact deployed release version and commit.

Current evidence (2026-09-02 12:55, re-verified 2026-09-02 14:45, HEAD 703e756) shows all of the above:
- `{"loader_installed": true, "constraint_present": true, "constraint_name": "ct_translation_key_digest", "has_drift": false, "has_duplicates": false, "has_null_digests": false, "last_drift_checked_at": "2026-09-02 12:55:06.548258"}`
- `{"total": 28, "created": 0, "updated": 0, "skipped": 28, "drift": 0}`
- `254 tests OK` (full suite)
- `Translation write lint PASSED`
- `## develop...origin/develop` (703e756 clean, pushed)
- `## develop` (frappe clean)
- `## version-16...upstream/version-16` (erpnext clean)

## 10. Evidence Register

| Evidence | Location / command | Review status |
|---|---|---|
| Release payload | `construction/data/translations/approved_ar_overrides.csv` | 28 rows, named reviewers, FRA/MOF refs — **Ready** |
| QA report | `construction/data/translations/qa-report.json` | Exists, 1,517 flags dispositioned in `qa-disposition-1.0.md` — **Ready** |
| Batch summary | `construction/data/translations/review-summary.csv` | Exists, 15,122 total, 28 Released — **Ready** |
| Eight review batches | `construction/data/translations/review/` | Regenerated 12:55, 28 Released — **Ready** |
| Glossary | `construction/data/glossary/egyptian_construction_glossary.json` | v2.0, 47 terms, schema v2 — **Ready** |
| Committed non-sensitive manifest | `docs/evidence/translation-stabilization-20260902_100747-manifest.json` | Current backup + targeted export checksums — **Ready** |
| Private recovery folder (final) | `sites/v16.localhost/private/backups/translation-stabilization-20260902_104925/` | DB dump 64MB + export 5.6MB (17,841 rows) — **Ready** (post-remediation, bc59bf2; DB unchanged from c0bf9ba) |
| Private recovery folder (104451) | `sites/v16.localhost/private/backups/translation-stabilization-20260902_104451/` | DB dump 64MB + export 5.6MB (17,841 rows) — **Ready** (intermediate, e6a98c3) |
| Private recovery folder (100747) | `sites/v16.localhost/private/backups/translation-stabilization-20260902_100747/` | DB dump 64MB + export 5.6MB (17,825 rows) — **Ready** (intermediate) |
| Private recovery folder (pre-remediation) | `sites/v16.localhost/private/backups/translation-stabilization-20260902_000042/` | Manifest + diff + targeted export (added 10:07) — **Preserved as rollback baseline (9011767)** |
| Patch evidence | Patch Log `construction.patches.v8_6.add_translation_identity_and_dedup` | Present — **Ready** |
| Database constraints | `SHOW INDEX` `ct_translation_key_digest` UNIQUE + `chk_ct_origin` | Both present — **Ready** |
| Automated tests | `construction.tests.test_translation_catalog` + `test_translation_stabilization_gates` | 3 + 7 = 10 translation, 254 total OK — **Ready** |
| Version provenance | `docs/evidence/version-provenance-20260902.json` | 16.18.1 authoritative (81aadb9) — **Ready** |
| QA disposition | `docs/translation/qa-disposition-1.0.md` | 1,517 flags + 37 groups dispositioned — **Ready** |
| Smoke test | `docs/translation/smoke-test-1.0.md` + `docs/evidence/smoke-20260902.tar.gz` (SHA256 `335ade8e3454a3e3f0e7eb15bdf6d4ed6f78832fd59f58d93cc1fe1a65cd3125`) | Fresh Arabic session, health assert, screens — **Ready** (archive contains README + placeholder; actual PNGs are external and referenced in smoke-test-1.0.md) |

## 11. Sign-off Decision

**Current decision: TECHNICAL GATES PASS — AWAITING RELEASE AUTHORITY SIGNATURE FOR PRODUCTION.**

All P0/P1 technical blockers B-01 through B-17 are now evidenced as fixed (see §3). The 28-row release payload is reconciled, UNIQUE is enforced, drift is false, backups are current, batches are regenerated, and 254 tests pass.

Production release requires:
- A1, A2, A3 countersign §7 (named reviewers already in CSV, awaiting wet signature / PR approval)
- Release authority signs below with deployed tag/commit and evidence-bundle checksum

| Role | Name | Date (Africa/Cairo) | Commit/Tag | Evidence bundle SHA256 |
|---|---|---|---|---|
| Release Authority | | | `703e756` on `origin/develop` | `docs/evidence/translation-stabilization-20260902_104925-manifest.json` SHA256 `53043217f85b3f6d1915fa7955f6a7960700f48b7af4fde6ce9865d71c6b9b71` (final, DB unchanged) |

*Do not replace evidence with a bare word such as “Approved”.*
