# Scope Descriptor — e2e-bilingual-commercial-uat (G14, G16)

**Work item:** `e2e-bilingual-commercial-uat`
**Branch:** `opencode/session-3c-uat`
**Worktree:** `/home/mohamed/frappe-bench/worktrees/session-3c-uat`
**Date:** 2026-10-06
**Authority:** Session 3C per `OPENCODE_PARALLEL_EXECUTION_MASTER.md` + the
Session 3C briefing (G14 end-to-end commercial UAT, G16 bilingual
verification gates).

## 1. Objective

Automate the end-to-end bilingual commercial workflow across the four
unified streams landed on develop (base commit `7cdb01d`):

1. BOQ & additive pricing lifecycle,
2. Variation Order & commercial integrity lifecycle,
3. Bilingual document rendering (4 transactional print formats),
4. Bilingual financial reporting (7 allowlisted reports).

## 2. Workflow lifecycle flow

```
BOQ Header (Draft)
  └─ BOQ Structure (NestedSet groups/leaves)
       └─ BOQ Item (factor > 0, contract_unit_price)
            └─ BOQ Cost Analysis (Draft → validate → submit)
                 │  pricing_rule_version = additive-direct-cost/v1
                 │  total_unit_cost = direct / qty; suggested_sell_rate =
                 │  cost × (1 + overhead + profit + tender_tax)
                 ▼
            BOQ Item (cost_basis=Approved Analysis,
                     active_cost_analysis, estimated cost locked)
                 │
                 ▼
            BOQ Quantity Revision (Draft → approve_quantity_revision)
                 │  APPROVAL_FROZEN_FIELDS immutability on save/delete
                 ▼
            Locked BOQ Header totals (total_contract_value rollup)
                 │  leaf item delete → after_delete() rollup
                 ▼
            Bilingual render (PO/SI/SE/MR) + Financial reports (ar/en/both)
```

## 3. Test cases

Suite: `construction/tests/test_e2e_bilingual_commercial_workflow.py`
(10 tests, all passing):

- `test_phase1_boq_header_groups_and_additive_pricing` — BOQ Header,
  NestedSet group + leaf structure, BOQ Item factor, draft
  `BOQ Cost Analysis` with 120%-style additive rule
  (`cost × (1 + overhead + profit + tender_tax)`), submit, approve,
  verify `pricing_rule_version = additive-direct-cost/v1`, estimated
  cost & pricing provenance locked on the BOQ Item (`cost_basis`,
  `active_cost_analysis` guarded by `has_column`).
- `test_phase2_variation_revision_frozen_fields_and_rollup` — revision
  created and approved via `approve_quantity_revision`; unmodified save
  succeeds; mutated `revised_qty` / `contract_unit_price` / `status` /
  `approved_by` raise `frappe.ValidationError`; frozen-field
  persistence asserted.
- `test_phase2_leaf_item_delete_rolls_up_header_totals` — BOQ Item
  delete recalculates `total_contract_value` via `after_delete()`.
- `test_phase2_positive_factor_enforced` — `factor = 0` raises
  `ValidationError` on BOQ Item save.
- `test_phase3_bilingual_print_formats` — renders PO / Sales Invoice /
  Stock Entry / Material Request through the four
  `Construction Bilingual *` print formats; asserts Arabic labels,
  `<bdi>` isolation tags, and drops HTML snapshots into
  `evidence/rendered-samples/`.
- `test_phase4_bilingual_reports_localized_headers` — all 7 allowlisted
  reports executed through `construction.api.bilingual_reports.
  localized_report` (vendor modules stubbed); `ar` localized headers,
  `both` mode uses the governed `Label — الحساب` format, `en` untouched.
- `test_phase4_unknown_report_fails_closed` — non-allowlisted report
  names raise `ValidationError`.
- `test_phase4_role_permission_barrier` — `frappe.only_for` denial
  raises `PermissionError` before vendor resolution.
- `test_phase4_global_defaults_company_fallback` — empty filters + no
  user default fall back to `Global Defaults.default_company`.
- `test_phase4_no_vendor_column_mutation` — repeated `both`-mode
  executions return identical column structures (no mutation).

## 4. Findings

- The briefing names `construction.api.bilingual_reports.
  execute_bilingual_report`; the implemented public API is
  `localized_report` (same contract: allowlist, permission barriers,
  mode normalization). Documented here; no code change required.
- `BOQ Item.cost_basis` is not a materialized column on the current
  v16.localhost schema, so the test guards reads with
  `frappe.db.has_column` and reads it via `frappe.db.get_value` — this
  is the documented schema-drift fallback pattern.
- `BOQ Item` cannot be deleted while approved revisions link to it
  (`LinkExistsError`); link validation is not bypassable for deletes on
  Frappe v16, so the rollup assertion uses a fresh leaf item (exercises
  the same `after_delete()` path).
- `both`-mode report labels render as `Label — الحساب` (em dash), not
  the `Label / الحساب` slash used by master-data pairs.

## 5. Gate results (G14/G16)

- `bench --site v16.localhost run-tests --module
  construction.tests.test_e2e_bilingual_commercial_workflow`: **10
  tests, OK** (`evidence/e2e-workflow-execution.log`).
- `scripts/lint_scope_metadata.py`: PASS.
- `scripts/ai_context_check.py`: PASS.
- `scripts/schema_drift_checker.py`: PASS.
- `scripts/lint_translation_writes.py`: PASS.
- `scripts/verify_manifest.py`: **RESULT: PASS** (`evidence/MANIFEST.json`
  self-verifies — all SHA-256 digests match).

## 6. Manifest reference

`evidence/MANIFEST.json` enumerates every deliverable and modified
file with SHA-256 digests. Regenerate with
`scripts/generate_manifest.py`; verify with `scripts/verify_manifest.py`.

## 7. Vendor / Redis / database invariants

- Zero edits under `apps/frappe/` or `apps/erpnext/` — the bench app
  checkout is mirrored from the worktree for test execution only.
- Ephemeral Redis 11000/13000 used for the test run; shut down at
  session end. System Redis (6379) untouched.
- All test writes are inside FrappeTestCase transactions and rolled
  back; zero permanent mutations on v16.localhost beyond rolled-back
  test scope.
