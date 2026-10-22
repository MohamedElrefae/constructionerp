# Scope Descriptor — bilingual-uom-phase2c-catalog-closure

**Work item:** `bilingual-uom-phase2c-catalog-closure`  
**Branch:** `develop`  
**Base commit:** `3e871f0` (concurrent with Tier 5J `5933c0d`)  
**Site:** `v16.localhost`  
**Date:** 2026-10-05  
**Status:** `COMPLETE` — zero-usage safety check PASS (0 hits across 105 table/column pairs); 204 non-construction vendor units formally classified and permanently excluded; formal ratification document published; tests (20/20 + 17/17) and 6 lints + reconciler 19/19 green; manifest #31 pinned.  

---

## 1. Authority & Strategic Intent

Following the completion of:
- **Phase 1 (Tier 5F, `9ccb4cd`):** 15 core units populated (12 app fixtures in `uom.json` + 3 active stock units: `Nos`, `Tonne`, `Box`).
- **Phase 2A & 2B (Tier 5I, `3e871f0`):** 30 physical engineering and handling units populated (`Meter`, `Kilogram`, `Joule`, `Pair`, etc.).
- **Fixture Exclusions:** 2 vendor fixtures (`_Test UOM`, `_Test UOM 1`) and 2 draft test units (`Pint (US)`, `Acre`).

The remaining **204 vendor units** (obscure imperial, theoretical physics, radiological, astronomical, and non-construction measures) require definitive lifecycle termination. 

Per the **Golden Rule** established in the UOM triage charter:
> *Do NOT bulk-translate blindly. ERPNext ships hundreds of obscure scientific and obsolete imperial units. Translating them introduces translation maintenance debt, clutters desk pickers, and degrades search relevance.*

This work item executes the final step in the UOM localization lifecycle: proving zero operational usage, establishing the immutable exclusion taxonomy, and formally ratifying catalog closure.

---

## 2. Definitive Scope Accounting (253 Total Rows)

| Category | Count | Status | Notes |
|---|---|---|---|
| Phase 1 App Fixtures | 12 | Populated | Finalized in `construction/fixtures/uom.json` (`enabled: 1`, `uom_name_ar`) |
| Phase 1 In-Use Units | 3 | Populated | `Nos`, `Tonne`, `Box` |
| Phase 2A Physical Units | 29 | Populated | Dimensional, area, volume, mass, time, energy |
| Phase 2B Handling Units | 1 | Populated | `Pair` |
| Vendor Fixtures | 2 | Excluded | `_Test UOM`, `_Test UOM 1` (never translated) |
| F4-Pruned Units | 2 | Excluded | `Pint (US)`, `Acre` (draft test BOQs only) |
| **Phase 2C Exclusions** | **204** | **Ratified Excluded** | Formally closed and sealed in this work item |
| **Total UOM Catalog** | **253** | **45 Populated** | Reconciled 100% across all catalog subsets |

---

## 3. Strict Rules & Architectural Invariants (R1–R7)

- **R1 (Zero Translation Writes):** Absolute prohibition on translating Phase 2C units. No `doc.save()`, no SQL `UPDATE`. Audit scripts are read-only with explicit database rollback.
- **R2 (Fail-Closed Zero-Usage Gate):** Any operational reference in any database table referencing a Phase 2C unit immediately halts ratification.
- **R3 (Server-Derived Norm Invariant):** All 45 populated units retain server-derived `uom_name_ar_norm`. Normalization is never manually injected or overwritten.
- **R4 (Confidentiality & Privacy):** Local execution only. No push to public or external remotes. Transmitting hooks disabled per `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`.
- **R5 (Frozen Surfaces Intact):** `uom.json` (`d6e27a01...`), `hooks.py`, `bilingual_service.py`, `searchable_dropdown/api/search.py`, `bilingual_registry.json`, and all vendor files under `apps/frappe` / `apps/erpnext` are byte-frozen and untouched.
- **R6 (Two-Tier SLA Protection):** Search queries for active bilingual units adhere strictly to the $\le 1.50\text{ ms}$ P95 latency ceiling.
- **R7 (Ephemeral Redis Protocol):** Redis ports 11000/13000 are brought up exclusively for the test execution window and terminated immediately after. `dump.rdb` is never tracked or staged.

---

## 4. Execution Sequence & Causal Order

```
[1. Baseline State Audit]
       │
       ▼
[2. Read-Only Zero-Usage Safety Audit (check_phase2c_zero_usage.py)]
  ├── Assert 45 populated / 253 total
  ├── Derive 204 unpopulated minus fixtures/pruned
  ├── Assert 100% match vs inventory-triage.log:78-281
  ├── Enumerate 105 table/column pairs in information_schema
  ├── Query all candidate tables with parameterized SQL IN
  └── Assert 0 references found (PASS)
       │
       ▼
[3. Publish PHASE2C_EXCLUSION_TAXONOMY.md (Categorized 204 Catalog)]
       │
       ▼
[4. Publish UOM_CATALOG_CLOSURE_RATIFICATION.md (Final Declaration)]
       │
       ▼
[5. Run Test Gates (Ephemeral Redis 11000/13000)]
  ├── test_transaction_link_search (20/20 PASS)
  ├── test_bilingual_desk_link_dispatch (17/17 PASS)
  └── Immediate Redis Teardown & Verify Closed
       │
       ▼
[6. Run Lint Gates & Reconciler (lint-gates.log)]
  ├── lint_scope_metadata (PASS)
  ├── ai_context_check (11/11 PASS)
  ├── lint_translation_writes (PASS)
  ├── schema_drift_checker (PASS)
  ├── py_compile (PASS)
  ├── bash -n (PASS)
  └── ADR reconciler (19/19 PASS)
       │
       ▼
[7. Finalize SCOPE.md & Generate MANIFEST.json (#31)]
       │
       ▼
[8. Local Commit Only (core.hooksPath=/dev/null)]
```

---

## 5. Verification Results Table

| Gate / Check | Expected | Actual Result | Status |
|---|---|---|---|
| Total UOM Rows | 253 | 253 | **PASS** |
| Populated Arabic UOMs | 45 | 45 | **PASS** |
| Derived Phase 2C vs `inventory-triage.log` | Exact 204 match | 204/204 byte equality | **PASS** |
| Information Schema UOM Columns Scanned | $\ge 26$ mandatory | 105 table/column pairs | **PASS** |
| Operational References Found | 0 | 0 references | **PASS** |
| Database Mutation Guard | 0 writes | 0 writes (byte-identical) | **PASS** |
| Test: `test_transaction_link_search` | 20/20 | 20/20 PASS (0.397s) | **PASS** |
| Test: `test_bilingual_desk_link_dispatch` | 17/17 | 17/17 PASS (1.954s) | **PASS** |
| Scope Metadata Lint | PASS | PASS (19 DocTypes) | **PASS** |
| AI Context Check | 11/11 | 11/11 PASS | **PASS** |
| Translation Write Lint | PASS | PASS | **PASS** |
| Schema Drift Checker | PASS | PASS (21 DocTypes) | **PASS** |
| Python Compilation (`py_compile`) | 0 errors | 0 errors | **PASS** |
| Shell Syntax Check (`bash -n`) | 0 errors | 0 errors | **PASS** |
| ADR Reconciler | 19/19 | 19/19 PASS | **PASS** |
| Manifest Verification | 0 bad | Manifest #31 pinned | **PASS** |
