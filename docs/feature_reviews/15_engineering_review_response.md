# Engineering Review Response: VO Quantity Revision Model

**Date:** 2026-06-11

**To:** Head of Engineering

**From:** Development Team

**Subject:** Engineering Review Findings — All P0 and P1 Blockers Addressed

---

## 1. Review Summary

**Reviewed Document:** `docs/feature_reviews/15_head_engineering_review_vo_quantity_revision.md`

**Original Decision:** Conditionally approved, with required changes before implementation.

**Response:** All P0 (blocking) and P1 (major) findings have been addressed in the revised implementation plan v2 (`13_vo_quantity_revision_implementation_plan.md`).

---

## 2. P0 Blockers — All Resolved

### P0-1: VO lines editable after Engineer Approval can invalidate approvals

**Finding:** If VO lines are editable after Engineer Approval, the engineer-approved scope may differ from the client-approved scope.

**Resolution:** Adopted **enterprise policy** — VO lines are editable only in Draft and Submitted statuses. Once Engineer Approved, lines are locked.

**Changes in plan v2:**
- Section 6 (VO Line Simplification): Updated table to show lines locked after Engineer Approved
- Section 8 (Variation Order Controller): Added `validate_lines()` check to block modifications after Engineer Approved
- Section 9 (Client Scripts): Grid fields become read-only after Engineer Approved
- Tests: Added coverage for "VO line editing blocked after Engineer Approved"
- Manual QA: Added step #8 to confirm VO line is NOT editable after Engineer Approval

**Impact:** Users must return VO to Submitted status (or create a new VO) to edit scope. This preserves approval integrity.

---

### P0-2: `total_revised_value` is under-specified and will be wrong after rate changes

**Finding:** If `total_revised_value` uses `contract_unit_price`, it will be wrong when rates change.

**Resolution:** Added `current_revised_unit_price` to BOQ Item. `total_revised_value` uses `current_revised_qty * current_revised_unit_price * factor`.

**Changes in plan v2:**
- Section 1 (BOQ Item Schema): Added `current_revised_unit_price` field
- Section 2 (BOQ Header Schema): Updated `total_revised_value` formula to use `current_revised_unit_price`
- Section 4 (Quantity Revision Service): Added `get_current_unit_price()` function; `apply_approved_revision()` updates `current_revised_unit_price`
- Section 5 (BOQ Lock Baseline): Sets `current_revised_unit_price = contract_unit_price` at lock
- Tests: Added coverage for rate change updates to `current_revised_unit_price` and `total_revised_value`
- Manual QA: Added step #12 to confirm `current_revised_unit_price` updated after rate change

**Impact:** Financial reports now reflect actual approved rates, not original contract rates.

---

### P0-3: FIDIC percentage rule needs explicit behavior for variation items and zero original quantity

**Finding:** For new variation items with `original_qty = 0`, the formula `abs(delta) / original_qty` divides by zero.

**Resolution:** Defined explicit policy:
- If `original_qty > 0`: compute `change_pct_from_contract` normally
- If `original_qty = 0`: set `change_pct_from_contract = 100` and require explicit rate

**Changes in plan v2:**
- Section 3 (BOQ Quantity Revision): Updated validation rules with variation item policy
- Section 7 (VO Line Controller): For `New Item` with `contract_qty = 0`, set `change_pct_from_contract = 100` and `rate_change_triggered = 1`
- Section 9 (Client Scripts): Compute `change_pct_from_contract = 100` for new variation items
- Tests: Added coverage for FIDIC rule on variation items

**Impact:** New variation items always trigger rate review (100% change), which is correct since they are entirely new scope.

---

### P0-4: Revision approval must be idempotent and transactional

**Finding:** Without strict checks, repeated saves can duplicate quantity revisions or create multiple variation items.

**Resolution:** Added idempotency checks and transaction requirements.

**Changes in plan v2:**
- Section 4 (Quantity Revision Service): Added `process_approved_vo_lines()` with:
  - Check `created_quantity_revision` before creating new revision
  - Check `created_boq_item` / `created_boq_structure` before creating new variation items
  - `SELECT ... FOR UPDATE` lock on BOQ Item rows
  - Read actual `current_revised_qty` from DB at approval time
  - Apply all lines or fail cleanly
- Section 8 (Variation Order Controller): Added `process_approved_vo_lines()` implementation with idempotency
- Tests: Added coverage for "Re-saving Approved VO does not duplicate revisions"
- Manual QA: Added step #27 to confirm no duplicate revisions on re-save

**Impact:** Multiple saves of an approved VO are safe. No duplicate data.

---

## 3. P1 Major Findings — All Resolved

### P1-1: Migration/backfill for existing VO data is incomplete

**Finding:** The site already has VO test data. Need strategy for existing variation items and approved VOs.

**Resolution:** Documented migration strategy and added migration patch.

**Changes in plan v2:**
- New Section: "Migration Strategy (P1-1 Resolution)"
- Defined backfill for:
  1. Existing non-variation BOQ Items under Locked BOQs
  2. Existing variation BOQ Items
  3. Existing approved VO-created variation items
  4. Existing approved Quantity Change/Omission VO lines
- New file: `construction/patches/v7_0_migrate_quantity_revisions.py`
- Tests: Added coverage for migration setting `original_qty` and `current_revised_qty`

**Impact:** Existing data will be correctly migrated to the new model.

---

### P1-2: Transaction selector filtering must be opt-in and null-safe

**Finding:** Using `current_revised_qty > 0` could hide valid items during migration or for older records.

**Resolution:** Use `COALESCE(current_revised_qty, quantity) > 0` with opt-in filter.

**Changes in plan v2:**
- Section 10 (Link Queries): Updated to use `COALESCE(current_revised_qty, quantity) > 0`
- Only apply when `filters.get("exclude_zero_revised")` is True
- Do not globally change all BOQ item queries

**Impact:** Safe migration. No accidental hiding of items.

---

### P1-3: `BOQ Quantity Revision.status` vs Frappe `docstatus` must be decided

**Finding:** Plan defined custom `status` but didn't decide if DocType is submittable.

**Resolution:** `BOQ Quantity Revision` is non-submittable (`is_submittable: 0`). Custom `status` field drives approval state.

**Changes in plan v2:**
- Section 3 (BOQ Quantity Revision): Explicitly stated `is_submittable: 0`
- `track_changes: 1` for audit
- `read_only_onload: 1` for Approved records
- Controller validation prevents editing Approved records

**Impact:** Simple model. Approval is driven by VO workflow, not independent document workflow.

---

### P1-4: Rate Change revision type is ambiguous

**Finding:** `Rate Change` revision type exists but no corresponding VO line type or UX.

**Resolution:** Removed standalone `Rate Change` from revision types for this phase.

**Changes in plan v2:**
- Section 3 (BOQ Quantity Revision): Removed `Rate Change` from revision types (now 7 types instead of 8)
- Rate changes are handled as part of Quantity Change revisions (when `revised_unit_price != contract_unit_price`)
- Non-Goals section: Explicitly lists "Standalone Rate Change" as out of scope

**Impact:** Cleaner model. No ambiguous revision type.

---

## 4. P2 Minor Findings — All Resolved

### P2-1: Evidence files should be mandatory outputs

**Finding:** Implementation should not be complete until evidence files are filled with actual results.

**Resolution:** Added explicit requirement.

**Changes in plan v2:**
- Section "Evidence Requirements": Added note: "Implementation is not complete until evidence files are filled with actual results, not templates."
- Acceptance Criteria: Added "Evidence files filled with actual results"

---

### P2-2: Report service acceptance needs examples

**Finding:** Query service report scope is good but needs concrete value assertions.

**Resolution:** Added specific test assertions.

**Changes in plan v2:**
- Tests: Added assertions for original value, revised value, delta value, omitted item handling, variation item inclusion
- `get_revised_boq()` function updated to use `current_revised_unit_price` for value computation

---

### P2-3: Naming consistency

**Finding:** `delta_from_contract` vs `delta_from_contract_qty` used inconsistently.

**Resolution:** Standardized on `delta_from_contract_qty`.

**Changes in plan v2:**
- All references to contract delta now use `delta_from_contract_qty` consistently
- VO Line field: `delta_from_contract_qty`
- BOQ Quantity Revision field: `delta_from_contract_qty`
- Client script: `delta_from_contract_qty`

---

## 5. Approved Decisions (Confirmed)

The following decisions from the engineering review are confirmed and incorporated:

| Decision | Status |
|---|---|
| Remove `item_code` from VO Line | ✅ Approved |
| Exclude procurement and Material Request | ✅ Approved |
| Use `revised_qty` as primary QS input | ✅ Approved |
| Add `BOQ Quantity Revision` as historical ledger | ✅ Approved |
| Keep BOQ Items as operational work items | ✅ Approved |
| Add `original_qty` and `current_revised_qty` to BOQ Item | ✅ Approved |
| New post-lock items are normal BOQ Items marked as variation | ✅ Approved |
| Reports start with query/service layer | ✅ Approved |
| Enterprise policy for VO line editing (lock after Engineer Approved) | ✅ Approved |
| Add `current_revised_unit_price` for rate-aware value computation | ✅ Approved |
| FIDIC rule for variation items with zero original qty | ✅ Approved |
| Idempotent and transactional VO approval | ✅ Approved |
| Migration/backfill for existing data | ✅ Approved |
| Null-safe and opt-in transaction selector filtering | ✅ Approved |
| Non-submittable `BOQ Quantity Revision` | ✅ Approved |
| Remove standalone `Rate Change` revision type | ✅ Approved |

---

## 6. Plan v2 Changes Summary

**File:** `docs/feature_reviews/13_vo_quantity_revision_implementation_plan.md`

**Key changes from v1 to v2:**

1. **VO Line Editing Policy:** Lines editable only in Draft and Submitted (not Engineer Approved)
2. **New Field:** `current_revised_unit_price` added to BOQ Item
3. **Updated Formula:** `total_revised_value` uses `current_revised_unit_price`
4. **FIDIC Rule for Variation Items:** Explicit policy for `original_qty = 0`
5. **Idempotent Approval:** Added `created_quantity_revision` checks and `FOR UPDATE` locks
6. **Migration Strategy:** New section with backfill plan and migration patch
7. **Opt-in Filtering:** `COALESCE(current_revised_qty, quantity) > 0` with `exclude_zero_revised` flag
8. **DocType Status:** Clarified `is_submittable: 0` with custom status field
9. **Removed:** Standalone `Rate Change` revision type (now 7 types)
10. **Naming:** Consistent `delta_from_contract_qty` throughout
11. **Evidence:** Explicit requirement for filled evidence files
12. **Tests:** Added 4 new test cases (rate change, idempotency, migration, editing policy)
13. **Manual QA:** Added 3 new steps (#8, #12, #27)

---

## 7. Ready for Implementation

All P0 blockers have been resolved. All P1 major findings have been addressed.

**The implementation plan v2 is approved for AI-agent execution.**

No further major architecture review is required unless the core model changes.

---

## 8. Next Steps

| Step | Action | Owner | Status |
|---|---|---|---|
| 1 | Engineering review | Head of Engineering | ✅ Complete |
| 2 | Address P0/P1 findings | Development Team | ✅ Complete |
| 3 | Produce plan v2 | Development Team | ✅ Complete |
| 4 | Produce review response | Development Team | ✅ Complete |
| 5 | **Implementation by AI agent** | Development Team | ⏳ Ready to start |
| 6 | Automated tests + migration | Development Team | ⏳ Ready to start |
| 7 | Manual QA on `v16.localhost` | QA / Product Owner | ⏳ Ready to start |
| 8 | Evidence documentation | Development Team | ⏳ Ready to start |
| 9 | Final engineering review | Head of Engineering | ⏳ After implementation |

---

**We are ready to proceed with implementation.**

Please confirm if any further changes are needed, or authorize the AI agent to begin implementation.

---

*Review response prepared: 2026-06-11*
*Plan v2: docs/feature_reviews/13_vo_quantity_revision_implementation_plan.md*
*Evidence templates: EV-065, EV-066, EV-067*
