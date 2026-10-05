# SCOPE: BOQ Commercial Integrity G01, G02, G04

## Root Causes

### G01 — BOQ Item Deletion Rollup Defect
- **Location:** `construction/construction/doctype/boq_item/boq_item.py`
- **Problem:** Header rollup executed solely in `on_trash()`, which runs before the row is physically removed from MariaDB. A successful deletion left the header total stale (including the to-be-deleted row's value).
- **Fix:** Moved rollup execution to `after_delete()`, which fires after the row is deleted. `on_trash()` now only performs protection (no rollup). Added `after_delete()` hook that calls `_trigger_header_rollup()`.

### G02 — Approved Quantity Revision Mutability
- **Location:** `construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py`
- **Problem:** `validate_approval_integrity()` only compared statuses (Approved→Rejected allowed, Approved→Approved no-op) without checking whether commercial fields (quantities, rates, values, identity fields) had been modified. An approved record could be silently edited, undermining auditability.
- **Fix:** Enhanced `validate_approval_integrity()` to compare all immutable commercial fields between `doc_before_save()` and the current document when the old status is `Approved`. Fields prohibited from change include: `boq_header`, `boq_structure`, `boq_item`, `variation_order`, `revision_type`, `previous_qty`, `revised_qty`, `delta_qty`, `delta_from_contract_qty`, `contract_unit_price`, `revised_unit_price`, `previous_value`, `revised_value`, `delta_value`, `approved_by`, `approved_on`. Any change throws `frappe.ValidationError` suggesting a new revision record instead. Status transitions to anything other than `Approved` or `Rejected` are also blocked.

### G04 — Zero/Negative Factor Inconsistency
- **Location:** `construction/construction/doctype/boq_item/boq_item.py`
- **Problem:** Validation accepted `factor = 0` or `factor < 0`. Python controller used `flt(factor) or 1.0`, mapping zero to 1.0, while SQL aggregates used `COALESCE(factor, 1.0)`, creating divergent behavior (line total 100 with factor=0 vs factor treated as multiplier zero). Missing factor had undefined default across UI, imports, and SQL.
- **Fix:** 
  - `validate_input_guards()` now enforces `factor > 0`; factor of 0 or negative raises `frappe.ValidationError`.
  - Missing/empty factor defaults to `1.0` during validation, centralizing the default.
  - Import service already rejected `<=0` factors (unchanged).
  - Aggregated SQL uses `COALESCE(factor, 1.0)` which is now consistent since factor is never 0/negative in valid data.

## Code Changes

### `construction/construction/doctype/boq_item/boq_item.py`
1. **`on_trash()`** — rollup disabled; rollup deferred to `after_delete()`.
2. **`after_delete()`** — new hook that calls `_trigger_header_rollup()` after row removal.
3. **`validate_input_guards()`** — factor validation: `None`/empty → `1.0`; `<=0` → ValidationError. Removed `factor` from `non_negative_fields` list (handled separately).

### `construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.py`
1. **`APPROVED_IMMUTABLE_FIELDS`** — tuple listing all commercial/identity fields that cannot be modified on an approved revision.
2. **`validate_approval_integrity()`** — compares current document against `doc_before_save()` (or DB-fetched prior version) when old status is `Approved`; forbids changes to immutable fields; blocks status transitions other than `Approved`/`Rejected`.

### `construction/tests/test_boq_financial_integrity.py` (new)
- **`test_g01_delete_last_item_zeroes_totals`** — deletes the sole item; header total regresses to 0.
- **`test_g01_item_deletion_updates_header_totals`** — deletes one of two items; header total updates from 300 to 200.
- **`test_g02_approved_revision_blocks_commercial_edits`** — creates approved revision, attempts `revised_qty` and `revised_unit_price` changes (both raise `ValidationError`); metadata-only change (`reason`) permitted.
- **`test_g04_zero_or_negative_factor_rejected`** — factor=0 and factor=-2 both raise `ValidationError`.
- **`test_g04_missing_factor_defaults_to_one`** — factor=None saves with factor=1.0; line_total computed as 100 (quantity×rate×1.0).

## Test Results (Session 2)

| Test | Status |
|------|--------|
| test_g01_delete_last_item_zeroes_totals | PASS |
| test_g01_item_deletion_updates_header_totals | PASS |
| test_g02_approved_revision_blocks_commercial_edits | PASS |
| test_g04_zero_or_negative_factor_rejected | PASS |
| test_g04_missing_factor_defaults_to_one | PASS |

*All 5 regression tests passing (5/5 PASS). Test harness uses fresh get_doc instances per assertion to maintain clean isolation without broad rollbacks.*

## Verification Invariants
- Zero edits to `apps/frappe` or `apps/erpnext`.
- All 273 existing matrix tests preserved (to be validated in subsequent step).
- Working files `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, `dump.rdb` untouched.
- Ephemeral Redis ports 11000/13000 used only during test execution.