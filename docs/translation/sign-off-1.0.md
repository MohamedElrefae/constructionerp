# Translation Stabilization 1.0 — Release Readiness and Sign-off Record

## 1. Document Control

| Field | Value |
|---|---|
| Release | Translation stabilization 1.0 |
| Review date | 2026-09-02 (Africa/Cairo) |
| Environment reviewed | `v16.localhost` |
| Application scope | Frappe 16.18.1, ERPNext 16.18.3, Construction 0.0.5 |
| Catalog snapshot | 15,106 Arabic source strings |
| Glossary | v2.0, schema v2, 47 terms |
| Candidate commit | `9011767ba57ef161edfc17e6bc03e8bf5a3ee398` |
| Remote baseline | `338baba7a6cd248742019195a401546b7933aef4` |
| Release decision | **NOT APPROVED — mandatory gates remain open** |

This record replaces the earlier optimistic template. A generated artifact, a passing smoke test, or a role label is evidence for only that specific check; none of them constitutes production approval by itself.

## 2. Executive Verdict

The runtime loader, catalog/runtime separation, migration execution, cache-aware import path, and three existing regression tests are working on the reviewed site. The release is nevertheless **not ready for production sign-off** because the database does not enforce digest uniqueness, packaged provenance does not match the release payload, the P0 recovery archive is incomplete, reviewer identities are not evidenced, the full linguistic review is unfinished, and the candidate commits have not been pushed.

Technical stabilization and linguistic completion remain separate tracks:

- Technical release may proceed only after every P0/P1 gate in this record passes.
- Full linguistic completion may continue in batches, but unresolved high-risk or globally scoped terminology must not be released.
- The phrase “full ERP, 15,106 strings” describes review coverage, not completed translation or approval.

## 3. Mandatory Release Blockers

| ID | Priority | Finding | Evidence | Required correction and acceptance test |
|---|---:|---|---|---|
| B-01 | P0 | Digest uniqueness is not enforced. `ct_key_digest_index` is non-unique (`Non_unique = 1`), although the health endpoint reports `constraint_present: true`. | Live `SHOW INDEX` result; `get_translation_health()` treats any digest index as a constraint. | Replace or supplement the non-unique index with a verified unique index. Health must explicitly assert `Non_unique = 0` and the expected index name/columns. Add a test proving that a duplicate digest insert fails. |
| B-02 | P0 | The release payload and live packaged rows disagree: CSV = 28 rows; live version-1.0 packaged rows = 29. The extra live key is `Chart Of Accounts`. | `approved_ar_overrides.csv`; live `tabTranslation` query. | Reconcile by exact `(language, source_text, context)` identity, deprecate/remove orphan packaged rows through the supported release path, and assert payload count/hash equals live released count/hash. |
| B-03 | P0 | Packaged provenance is incomplete: 21 of 29 live packaged rows have blank `ct_app`. | Live `tabTranslation` query. | Make idempotent imports repair metadata even when the translated value is already equal. Verify all packaged rows retain the payload `ct_app`, release version, origin, releaser, and release timestamp. |
| B-04 | P0 | The importer trusts `release_status=Released` without enforcing complete A1/A2/A3 quorum. | `import_released_overrides()` filter logic. | Validate named A1, named A2 or explicit approved N/A, named A3, approval timestamps, and non-empty evidence before any write. Add negative tests for every missing quorum field. |
| B-05 | P0 | The required P0 recovery set is incomplete. The timestamped folder contains only `manifest.json` and `frappe_ar_po.diff`; the targeted Arabic Translation export is absent, and the referenced database backup is dated 2026-08-21. | `sites/v16.localhost/private/backups/translation-stabilization-20260902_000042/`. | Take a current full database backup, create the complete targeted Translation export with custom/audit fields, parse-test both, and record checksums plus restore instructions without committing sensitive data. |
| B-06 | P1 | `has_drift` is not a real health result: the function executes a count and then always assigns `False`; `last_drift_checked_at` is never populated. | `get_translation_health()` and live response. | Implement a deterministic payload-versus-live drift comparison and timestamp it. Health assertion must fail for extra, missing, altered, or metadata-incomplete packaged rows. |
| B-07 | P1 | Independent human quorum is not evidenced. The CSV stores the role placeholders `A1`, `A2`, and `A3` as reviewer names for all 28 rows. | `approved_ar_overrides.csv`. | Replace placeholders with accountable reviewer identities and dated evidence. A2 must be a qualified Egyptian construction accountant/QS for domain terms. A3 must disposition every relevant structural/forbidden-term flag. |
| B-08 | P1 | Batch artifacts show only 12 Released rows, while the packaged payload contains 28. Sixteen payload rows therefore lack a matching Released row in the generated batch evidence. | Eight batch CSVs and `review-summary.csv`. | Rebuild the release payload only from batch rows that pass quorum, or add a traceable exception record for keys absent from the catalog. Re-run summary and payload reconciliation. |
| B-09 | P1 | Review artifacts are stale relative to the live site: generated snapshot missing count = 7,338; current live blank catalog count = 7,332 after the later import. | `qa-report.json`, batch CSVs, and live query. | Regenerate all review artifacts after the final import or bind every artifact to an immutable pre-import snapshot and document the expected delta. Counts must reconcile. |
| B-10 | P1 | The candidate is local only: Construction is two commits ahead of `origin/develop`. | Git status on 2026-09-02. | Push the approved candidate through the normal review workflow and record the deployed commit/tag. Do not sign a local-only commit. |
| B-11 | P1 | Version reporting is inconsistent: the Frappe source reports 16.18.1 while `bench version` labels it `15.x.x-develop`. | `frappe/__init__.py` and `bench version --format plain`. | Confirm the installed Frappe provenance and record one authoritative version/commit pair before deployment. |
| B-12 | P1 | Automated QA and conflict queues are not dispositioned: 1,517 rows carry one or more QA flags; the QA report records 37 cross-app conflict groups, represented by 74 flagged batch rows. | `qa-report.json` and batch CSVs. | A3 must mark each flag as corrected or false positive with evidence. Cross-app conflicts must be context-scoped or block release; never solve them by a dishonest global relabeling. |
| B-13 | P1 | Test coverage proves only three legacy behaviors. It does not prove migration uniqueness, quorum enforcement, metadata repair, orphan retirement, rollback, semantic version ordering, or health/drift failure behavior. | `construction.tests.test_translation_catalog`: 3 tests passed. | Add targeted automated tests for all listed release controls, then run the complete Construction test suite and record results. |
| B-14 | P1 | UI/runtime acceptance is not evidenced after a fresh Arabic boot. | No signed browser smoke record is attached. | Clear server/user/merged/boot caches, restart as required, hard-refresh a fresh Arabic session, and verify representative Frappe, ERPNext, and Construction screens with screenshots or a signed test log. |
| B-15 | P0 | Catalog list values, runtime values, and immutable `.po` baselines are not synchronized correctly. Live examples: `Payment Entry` retains the old catalog value while runtime uses the packaged value; `Submit` is blank/Pending in the catalog while runtime is Released; `Add Child.ct_po_translation` contains `إضافة فرع` although the clean Frappe `.po` `msgstr` is blank. | Live catalog/runtime queries and clean `frappe/locale/ar.po`. | On approved import, update the matching catalog display/review fields and the one runtime row while preserving the current upstream `.po` value in `ct_po_translation`. Re-sync polluted baselines from clean vendor catalogs. Add regression tests for all three layers and for context/app-specific rows. |
| B-16 | P1 | Release versions are ordered with plain string comparison, which is unsafe for versions such as `2.0` and `10.0`. | Packaged-release checks in `upsert_runtime_translation()` and `import_released_overrides()`. | Parse and compare a defined semantic version format, or replace ordering with an immutable monotonically increasing release sequence. Add boundary tests. |
| B-17 | P1 | The install/migrate release hook catches all import errors, logs them, and returns an error object; deployment can therefore appear successful while packaged import failed. | `import_released_overrides_hook()`. | Make deployment fail closed for mandatory release imports, or add a separate mandatory post-migrate assertion that fails the deployment when the expected payload is not present exactly. Test the failure path. |

## 4. Verified Technical Evidence

Evidence captured on 2026-09-02 against `v16.localhost`:

| Check | Result | Release interpretation |
|---|---|---|
| Runtime loader installed | Pass (`true`) | Loader hook is active. |
| Safe fallback active | Pass (`false`) | Catalog-aware path is in use. |
| Duplicate digest groups currently present | Pass (`false`) | Current data is deduplicated; future duplicates are not prevented until B-01 is fixed. |
| Null/blank Arabic digests | Pass (`false`) | Current Arabic rows are populated. |
| Health `constraint_present` | **False positive** | A non-unique index exists; no UNIQUE constraint exists. |
| `chk_ct_origin` database CHECK | Pass | MariaDB reports the named CHECK constraint. |
| Migration `construction.patches.v8_6.add_translation_identity_and_dedup` | Pass | Patch Log contains the patch. |
| Health assertion command | Command returned successfully | Not a release pass until B-01 and B-06 correct the assertion. |
| Translation write lint | Pass | `Translation write lint PASSED`. |
| Translation catalog tests | Pass | 3 tests ran and passed. Coverage remains limited by B-13. |
| Import dry run | Pass for idempotent values | `total: 28, created: 0, updated: 0, skipped: 28, drift: 0`; this does not detect metadata drift. |
| Technical `Child` rows containing `طفل`/`أطفال` | Pass | Live runtime query returned zero. |
| Vendor Frappe `ar.po` worktree | Pass | Frappe repository is clean; `Add Child` is no longer an uncommitted vendor edit. |
| Review batches generated | Pass | Eight CSV files, QA report, and summary exist. |

Latest reported health timestamps:

- Catalog sync: `2026-09-01 16:04:02.102489`
- Release import: `2026-09-02 02:35:15.663292`
- Drift check: not recorded (`null`)

## 5. Review Batch Status

`QA-flagged rows` counts rows with at least one non-empty `qa_flags` value; one row can contain more than one flag. `Released` is the row status in the generated batch, not proof of named human approval.

| Batch | Strings | Translated | Missing | Released | QA-flagged rows | Cross-conflict rows |
|---|---:|---:|---:|---:|---:|---:|
| 01 — Construction accounting | 1,378 | 695 | 683 | 6 | 216 | 2 |
| 02 — Contracts, subcontractors, certificates | 124 | 25 | 99 | 2 | 35 | 0 |
| 03 — BOQ, estimation, project costing | 257 | 133 | 124 | 0 | 54 | 2 |
| 04 — Purchasing, inventory, site materials | 1,453 | 706 | 747 | 1 | 271 | 2 |
| 05 — Core actions and errors | 897 | 390 | 507 | 1 | 150 | 2 |
| 06 — Payroll and labor | 72 | 46 | 26 | 0 | 10 | 0 |
| 07 — Manufacturing | 137 | 76 | 61 | 0 | 15 | 0 |
| 08 — Technical and administration | 10,788 | 5,697 | 5,091 | 2 | 766 | 66 |
| **Total** | **15,106** | **7,768** | **7,338** | **12** | **1,517** | **74** |

Additional QA totals from `qa-report.json`:

- Placeholder mismatch flags: 1,208
- HTML imbalance flags: 311
- Whitespace flags: 77
- Cross-app conflict groups: 37

These are review-queue signals, not automatically confirmed defects. They require recorded A3 disposition before affected rows can be released.

## 6. Egyptian Construction and Accounting Terminology Review

### 6.1 Terms suitable to retain, subject to named quorum

The following choices align with common Egyptian professional usage or unambiguous software hierarchy usage:

| English | Arabic | Consultant note |
|---|---|---|
| Add Child | إضافة فرع | Correct for a software tree; never use `طفل`. |
| Child Account | حساب فرعي | Standard accounting hierarchy term. |
| Child Company | شركة تابعة | Appropriate for a subsidiary-company relationship. |
| Journal Entry | قيد يومية | Standard accounting term. |
| Chart of Accounts | دليل الحسابات | Standard accounting term. Preserve exact source capitalization as separate keys only when the application truly emits both. |
| Cost Center | مركز التكلفة | Standard accounting term. |
| Advance Payment | دفعة مقدمة | Consistent with Egyptian contracting usage. |
| Bill of Quantities | جدول الكميات | Standard construction/QS term. |
| Variation Order | أمر تغيير | Appropriate construction-contract term. |
| Progress Billing | مستخلص جاري | Appropriate Egyptian construction usage when the context is interim work valuation. |
| Payment Certificate | مستخلص | Appropriate in Egyptian construction context; scope it if the English key is reused outside construction. |
| Mobilization Cost | تكلفة تجهيز الموقع | Suitable when the source means site mobilization. |
| Subcontract / Subcontracting | عقد مقاولات باطن / مقاولات الباطن | Common industry phrasing; the formal legal wording should also be recorded as `عقد/مقاولة من الباطن`. |

### 6.2 Terms that must be context-scoped or re-approved before release

| English | Current Arabic | Risk | Required decision |
|---|---|---|---|
| Submit | ترحيل | `ترحيل` is accounting-specific, while Frappe Submit is a global document-lifecycle action. | Remove the contextless global override or use a lifecycle term such as `اعتماد` only after UI review. Keep `ترحيل` for a genuinely accounting-specific context. |
| Save and Submit | حفظ وترحيل | Same global-scope problem as Submit. | Scope by context or align with the approved generic Submit decision. |
| Handover | التسليم الابتدائي | The generic English key does not say initial/provisional; the Arabic narrows the legal/contractual meaning. | Use a neutral `التسليم` or add an exact initial/provisional context. Distinguish provisional/initial and final handover. |
| Payment Entry | سند قبض / سند صرف | A single UI label contains two transaction directions and may be confusing in menus, reports, and links. | Validate the actual ERPNext use cases. Prefer a neutral label or context-specific receipt/payment labels. |
| Retention / Retention Money | محتجزات ضمان | Plausible industry term, but the two English keys may require different grammar or accounting presentation. | A2 must verify field-level screens, reports, and whether `مبالغ محتجزة` is clearer in any context. |
| Voucher | السند | Broadly correct but context-sensitive across journal, payment, and stock documents. | Retain only after cross-screen A2 review; do not force a narrower accounting meaning onto technical voucher identifiers. |

Authoritative Egyptian references to use during A2 review:

- [Financial Regulatory Authority — Egyptian accounting standards and current standard framework](https://fra.gov.eg/services_forms_compa/%D9%85%D8%B9%D8%A7%D9%8A%D9%8A%D8%B1-%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D8%B3%D8%A8%D8%A9-%D8%A7%D9%84%D8%AF%D9%88%D9%84%D9%8A%D8%A9/)
- [Egyptian Tax Authority — Civil Code articles 661–662 using “مقاول من الباطن”](https://www.eta.gov.eg/sites/default/files/2024-10/law-131-1948.pdf)
- [Ministry of Finance — contract execution guidance using “المستخلص”, provisional/final acceptance, advance payment, and final guarantee terminology](https://assets.mof.gov.eg/files/d1370200-4d23-11ec-96fc-a7f429c97fa6.pdf)

The glossary must cite the precise source and paragraph/page where a regulatory or standards claim is made. A generic note such as `EAS` or `ETA guide` is insufficient release evidence.

## 7. Quorum Record

No role is approved until a real person signs below and the corresponding row-level evidence is traceable.

| Role | Required competence | Current evidence | Status | Name / date / evidence reference |
|---|---|---|---|---|
| A1 — Arabic localization | Professional Arabic software localization; grammar, consistency, and UI clarity | CSV contains only placeholder `A1` | **Open** |  |
| A2 — Egyptian construction accounting/QS | Egyptian construction accountant, quantity surveyor, or equivalent domain reviewer | CSV contains only placeholder `A2` | **Open** |  |
| A3 — Structural QA | Placeholder/HTML/whitespace preservation, forbidden terms, exact-key/context checks | CSV contains only placeholder `A3`; QA flags remain | **Open** |  |
| Technical owner | Loader, migration, importer, constraints, rollback, and test evidence | Partial automated evidence | **Open** |  |
| Release authority | Confirms all gates, deployed commit, backup, and smoke test | No evidence | **Open** |  |

Required quorum per released row:

1. A1 = Approved with reviewer identity, timestamp, and notes/reference.
2. A2 = Approved with reviewer identity, or explicit `Not Applicable` approved under the documented policy.
3. A3 = Approved with reviewer identity after all QA flags are corrected or dispositioned.
4. Exact source text, context, and `ct_app` provenance are preserved.
5. The row is generated into the release payload; it is not manually inserted as an untraceable exception.

## 8. Deployment and Acceptance Checklist

### 8.1 Completed evidence

- [x] Migration v8_6 appears in Patch Log.
- [x] Runtime loader is installed and not using the pre-migration fallback.
- [x] Current Arabic rows have no duplicate digest groups and no blank digests.
- [x] `chk_ct_origin` exists.
- [x] Frappe `ar.po` worktree is clean.
- [x] Eight review batches, QA report, and review summary were generated.
- [x] Three translation catalog regression tests pass.
- [x] Translation write lint passes.
- [x] Repeated payload dry run performs no value writes.
- [x] Technical `Child` runtime translations contain no `طفل` or `أطفال`.

### 8.2 Open mandatory gates

- [ ] B-01: enforce and independently verify a UNIQUE digest index.
- [ ] B-02/B-03: reconcile 28 payload rows to exactly 28 live rows with complete `ct_app` provenance.
- [ ] B-04: enforce quorum in code and tests.
- [ ] B-05: verify a current full database backup and complete targeted Arabic Translation archive.
- [ ] B-06: implement real drift detection and make health fail on drift.
- [ ] B-07: obtain named A1/A2/A3 approvals.
- [ ] B-08/B-09: regenerate and reconcile batches, summary, payload, and live counts.
- [ ] B-10/B-11: push the reviewed candidate and reconcile Frappe version provenance.
- [ ] B-12: resolve or disposition QA flags and cross-app conflicts.
- [ ] B-13: pass the expanded automated test suite.
- [ ] B-14: complete fresh-session Arabic UI smoke testing.
- [ ] B-15: reconcile catalog display, effective runtime value, and immutable upstream `.po` baseline.
- [ ] B-16: implement safe release-version ordering.
- [ ] B-17: make mandatory packaged-import failures block deployment.
- [ ] Verify cache invalidation, process restart, and hard refresh after final import.
- [ ] Record whether `.mo` compilation is required for this release and attach resulting checksums when applicable.
- [ ] Record rollback rehearsal or a verified restore test.
- [ ] Record the deployed commit/tag and deployment timestamp.

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

## 10. Evidence Register

| Evidence | Location / command | Review status |
|---|---|---|
| Release payload | `construction/data/translations/approved_ar_overrides.csv` | Exists; reconciliation and reviewer identity blocked |
| QA report | `construction/data/translations/qa-report.json` | Exists; flags not dispositioned |
| Batch summary | `construction/data/translations/review-summary.csv` | Exists; stale relative to live import |
| Eight review batches | `construction/data/translations/review/` | Exist; linguistic review incomplete |
| Glossary | `construction/data/glossary/egyptian_construction_glossary.json` | Exists; references need page-level evidence |
| Committed non-sensitive manifest | `docs/evidence/translation-stabilization-20260902_000042-manifest.json` | Exists; points to incomplete private recovery set |
| Private recovery folder | `sites/v16.localhost/private/backups/translation-stabilization-20260902_000042/` | Incomplete |
| Patch evidence | Patch Log query for `construction.patches.v8_6.add_translation_identity_and_dedup` | Present |
| Database constraints | `SHOW INDEX` and `information_schema.TABLE_CONSTRAINTS` | CHECK present; UNIQUE digest constraint absent |
| Automated tests | `construction.tests.test_translation_catalog` | 3 passed; expansion required |

## 11. Sign-off Decision

**Current decision: REJECTED FOR PRODUCTION RELEASE.**

Re-evaluate only when every open mandatory gate is checked, every blocker has linked evidence, all required reviewers are named, and the deployed commit is traceable. At that point update this section with the release authority’s name, approval timestamp, deployed tag/commit, and evidence-bundle checksum; do not replace evidence with a bare word such as “Approved”.
