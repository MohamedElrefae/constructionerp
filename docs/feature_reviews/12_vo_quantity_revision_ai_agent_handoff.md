# AI Agent Handoff: VO Quantity Revision Model Implementation

Date: 2026-06-10

Workspace: `/home/mohamed/frappe-bench`

Primary app: `/home/mohamed/frappe-bench/apps/construction`

Target site for verification: `v16.localhost`

## Handoff Purpose

This document is a handoff letter for an implementation AI agent, such as OpenCode, to execute the approved simplified Variation Order and Quantity Revision plan end to end.

The agent must implement the plan, run tests, fix regressions, and leave evidence of what was changed and verified. After the agent finishes, the user will ask another reviewer to inspect the implementation.

## Canonical Plan

The canonical implementation plan is:

`/home/mohamed/.gemini/antigravity/brain/7aa0849d-6ef1-496b-b74e-91816b9e488f/implementation_plan.md`

This handoff document summarizes that plan and adds execution instructions. If there is conflict, follow the simplified Quantity Revision architecture described here and in the canonical plan.

Important: do not follow the older material-request/item-code VO design. That older direction is superseded.

## Product Decision

The approved architecture is:

> BOQ Item is the work item. Variation Order is the approval/change document. BOQ Quantity Revision is the historical measurement record.

Do not turn `VO Line` into a second BOQ item model.

Do not add `item_code` for this phase.

Do not implement procurement or Material Request behavior for this phase.

## Business Goal

After the BOQ is locked, the original BOQ baseline must remain protected, but the project team must still be able to:

- add new variation items under the correct WBS group,
- revise quantities for original BOQ items,
- revise quantities for variation BOQ items,
- omit items by revising their quantity to zero,
- record every quantity movement historically,
- report original quantity, current revised quantity, and full quantity timeline.

This must support Egypt/Gulf quantity surveying practice where the QS enters the total revised surveyed quantity and the system computes the variation delta.

## Required User Experience

### New Variation Item

When BOQ is Locked, the user should be able to add a variation item through a controlled variation workflow.

Expected UX:

1. User opens a Locked BOQ or Variation Order.
2. User chooses `Add Variation Item`.
3. User selects parent WBS group.
4. User enters normal BOQ item data:
   - title,
   - unit,
   - quantity,
   - unit price,
   - owner/client references where available,
   - reason/reference.
5. System creates normal BOQ Structure and BOQ Item records.
6. System marks the BOQ Item as variation:
   - `is_variation_item = 1`
   - `variation_order = <VO name>`
7. System creates an approved quantity revision after VO approval.

### Quantity Increase or Decrease

Expected UX:

1. User selects existing BOQ Item.
2. System shows current approved quantity as `previous_qty`.
3. User enters total `revised_qty`.
4. System computes:
   - `delta_qty`,
   - `change_pct`,
   - value impact,
   - rate-change trigger.
5. On approval, system records a quantity revision and updates the BOQ Item current revised quantity.

### Omission

Expected UX:

1. User selects existing BOQ Item.
2. User chooses `Omission`.
3. System sets `revised_qty = 0`.
4. System computes `delta_qty = -previous_qty`.
5. On approval, system records omission in quantity history.
6. Omitted item is not deleted.

## Implementation Requirements

### 1. BOQ Item Schema

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.json`

Add fields:

- `original_qty` Float, read-only
- `current_revised_qty` Float, read-only
- `last_quantity_revision` Link to `BOQ Quantity Revision`, read-only

Semantic rules:

- For original BOQ items, `quantity` remains the original/contract quantity.
- `original_qty` is captured when BOQ becomes Locked.
- `current_revised_qty` is the latest approved revised quantity.
- For variation BOQ items, `original_qty = 0` and `current_revised_qty = quantity`.

### 2. New DocType: BOQ Quantity Revision

Create:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_quantity_revision/`

Required files:

- `boq_quantity_revision.json`
- `boq_quantity_revision.py`
- `__init__.py`

Required fields:

- `boq_header` Link to `BOQ Header`, required
- `boq_structure` Link to `BOQ Structure`, required
- `boq_item` Link to `BOQ Item`, required
- `variation_order` Link to `Variation Order`
- `revision_date` Date, required
- `revision_type` Select, required
- `previous_qty` Float, required
- `revised_qty` Float, required
- `delta_qty` Float, read-only/computed
- `change_pct` Percent, read-only/computed
- `contract_unit_price` Currency
- `revised_unit_price` Currency
- `previous_value` Currency, read-only/computed
- `revised_value` Currency, read-only/computed
- `delta_value` Currency, read-only/computed
- `rate_change_triggered` Check, read-only/computed
- `rate_change_justification` Small Text
- `reason` Small Text
- `owner_page` Data
- `owner_ref_no` Data
- `owner_file_ref` Data
- `status` Select: `Draft`, `Submitted`, `Approved`, `Rejected`
- `approved_by` Link to `User`
- `approved_on` Datetime

Recommended `revision_type` options:

```text
Original Lock
New Variation Item
Quantity Increase
Quantity Decrease
Omission
Rate Change
```

Validation rules:

- `revised_qty >= 0`
- `delta_qty = revised_qty - previous_qty`
- `change_pct = abs(delta_qty) / previous_qty * 100` when `previous_qty > 0`
- `previous_value = previous_qty * contract_unit_price`
- `revised_value = revised_qty * revised_unit_price`
- `delta_value = revised_value - previous_value`
- Omission requires `revised_qty = 0`
- New Variation Item requires `previous_qty = 0`
- Original Lock must be system-generated
- Approved revisions should not be casually editable

### 3. Quantity Revision Service

Create:

`/home/mohamed/frappe-bench/apps/construction/construction/services/quantity_revisions.py`

Required functions:

- `create_lock_baseline(boq_header)`
- `get_current_qty(boq_item)`
- `create_quantity_revision(...)`
- `approve_quantity_revision(revision_name)`
- `apply_approved_revision(revision)`
- `create_variation_item_revision(...)`

Service requirements:

- Use DB row locking where needed to avoid stale quantity approval.
- Make `create_lock_baseline` idempotent.
- Update `BOQ Item.current_revised_qty` only when a revision is approved.
- Update `BOQ Item.last_quantity_revision` when a revision is approved.
- Do not update original quantity after lock except controlled migration/correction.

### 4. BOQ Lock Baseline

Modify BOQ Header lock behavior:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.py`

Current code has lock transition logic. Hook baseline creation when status changes to `Locked`.

On BOQ lock:

1. For every BOQ Item under the header:
   - set `original_qty = quantity`
   - set `current_revised_qty = quantity`
2. Create one approved `BOQ Quantity Revision`:
   - `revision_type = Original Lock`
   - `previous_qty = 0`
   - `revised_qty = quantity`
   - `delta_qty = quantity`
   - `status = Approved`
3. Do not duplicate baseline rows if operation runs again.

### 5. VO Line Simplification

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.json`

Required changes:

- Add `boq_structure` if not present.
- Add `previous_qty`.
- Make `revised_qty` editable.
- Add `created_quantity_revision` Link to `BOQ Quantity Revision`.
- Add owner reference fields if needed:
  - `owner_page`
  - `owner_ref_no`
  - `owner_file_ref`
- Do not add `item_code`.
- If `item_code` already exists from a partial attempt, remove/hide it for this phase unless migration constraints require keeping it hidden.

VO Line behavior:

- `New Item`: user enters normal item details and total quantity.
- `Quantity Change`: user selects existing BOQ Item and enters total revised quantity.
- `Omission`: system forces revised quantity to zero.

### 6. Variation Order Controller

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.py`

Required behavior:

- Validate VO lines against current revised quantities.
- On `Approved by Client`, create quantity revisions for each line.
- For New Item:
  - create BOQ Structure under selected parent group,
  - create BOQ Item,
  - mark it as variation item,
  - create approved Quantity Revision,
  - link revision back to VO Line.
- For Quantity Change:
  - create approved Quantity Revision for existing BOQ Item,
  - update current revised quantity through service,
  - link revision to VO Line.
- For Omission:
  - create approved Quantity Revision with `revised_qty = 0`,
  - update current revised quantity to zero through service,
  - link revision to VO Line.

Important:

- Keep existing BOQ lock protection.
- Use existing `ignore_boq_status_for_variation` only for controlled variation item creation.
- Do not allow normal post-lock BOQ edits.

### 7. Client Scripts

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.js`

Required behavior:

- When `boq_item` is selected, fetch and show:
  - previous/current revised quantity,
  - contract/or current unit price,
  - title/unit/WBS context.
- Make `revised_qty` the primary input.
- Compute `delta_qty = revised_qty - previous_qty`.
- For omission, set `revised_qty = 0`.
- Add a small sync guard if both `delta_qty` and `revised_qty` remain editable.
- Lock all VO lines after Draft status.

### 8. Link Queries

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py`

Required behavior:

- Support selecting parent WBS groups for New Item.
- Support selecting existing BOQ Items for quantity change/omission.
- Hide fully omitted items from transaction selectors only by using `current_revised_qty > 0`.
- Do not hide omitted items from audit, revised BOQ, or history reports.

### 9. Reports

Implement or update reports/services/templates for:

1. Original BOQ
   - uses `original_qty`
   - shows original contract value

2. Current Revised BOQ
   - uses `current_revised_qty`
   - shows original qty, revised qty, delta qty, original value, revised value, delta value

3. Quantity Revision History
   - full timeline per item from `BOQ Quantity Revision`

4. VO Impact Report
   - commercial impact grouped by VO

5. Omitted Items Report
   - items whose latest approved current revised quantity is zero

If full UI reports are too large for one pass, implement query/service foundations and add tests first, then document remaining UI report work clearly.

## Required Tests

Add or update tests in:

- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_variation_orders.py`
- optionally `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_link_queries.py`
- optionally create `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_quantity_revisions.py`

Required automated coverage:

- Locking BOQ creates baseline quantity revisions.
- Re-saving locked BOQ does not duplicate baseline revisions.
- `original_qty` remains unchanged after approved revisions.
- `current_revised_qty` updates after approved revision.
- Draft revision does not update `current_revised_qty`.
- Quantity increase computes correct delta/value.
- Quantity decrease computes correct delta/value.
- Omission sets revised quantity to zero.
- New variation item after lock creates BOQ Structure, BOQ Item, and Quantity Revision.
- Normal post-lock BOQ item creation remains blocked.
- Controlled variation item creation after lock is allowed.
- Fully omitted item is hidden only from transaction selectors.
- Quantity history can reconstruct the item timeline.
- No `item_code` is required for New Item VO lines.

Recommended commands:

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_variation_orders --skip-before-tests --lightmode
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_link_queries --skip-before-tests --lightmode
bench --site v16.localhost run-tests --app construction --module construction.tests.test_quantity_revisions --skip-before-tests --lightmode
```

If a module does not exist, create it or document why it was not needed.

Also run migration/schema sync:

```bash
bench --site v16.localhost migrate
```

## Manual Verification Required

Use `v16.localhost`.

Manual QA checklist:

1. Create BOQ Header with at least one parent WBS group and two item leaves.
2. Lock BOQ.
3. Confirm baseline `BOQ Quantity Revision` rows exist.
4. Confirm `original_qty` and `current_revised_qty` are populated.
5. Create VO for quantity increase.
6. Approve VO by Client.
7. Confirm Quantity Revision exists and current revised quantity updated.
8. Create VO for quantity decrease.
9. Approve and confirm quantity timeline.
10. Create VO for omission.
11. Approve and confirm current revised quantity is zero.
12. Confirm omitted item still appears in history/reports.
13. Confirm omitted item is hidden from transaction selectors if that selector uses transaction filter.
14. Create new variation item under parent WBS.
15. Confirm new BOQ Structure is under the selected parent.
16. Confirm new BOQ Item is marked `is_variation_item = 1`.
17. Confirm new item has `original_qty = 0` and `current_revised_qty = quantity`.
18. Confirm no `item_code` is required.

## Evidence Requirements

Create evidence notes under:

`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/`

Suggested evidence files:

- `EV-065-vo-quantity-revision-schema.md`
- `EV-066-vo-quantity-revision-tests.md`
- `EV-067-vo-quantity-revision-manual-qa.md`

Each evidence note should include:

- date,
- files changed,
- command run,
- result,
- known limitations,
- screenshots only if UI was manually verified.

## Files Most Likely to Change

Expected files:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_quantity_revision/`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.js`
- `/home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/quantity_revisions.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_variation_orders.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_link_queries.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_quantity_revisions.py`

Before editing, inspect existing implementation carefully. There is already a VO module, existing lock protection, and existing `ignore_boq_status_for_variation` behavior.

## Acceptance Criteria

The work is complete only when:

- `item_code` is not required or introduced for this VO quantity plan.
- BOQ lock creates original quantity snapshots.
- `BOQ Quantity Revision` exists and validates quantity/value calculations.
- Original quantity remains available after revisions.
- Current revised quantity reflects latest approved revision.
- Quantity increase, decrease, omission, and new variation item are supported.
- New items after lock are normal BOQ Items marked as variation items.
- Direct post-lock BOQ item edits remain blocked.
- Omitted items remain auditable.
- Transaction selectors can hide omitted items without hiding them from history/reporting.
- Automated tests pass or failures are documented with root cause.
- Migration succeeds on `v16.localhost`.
- Evidence files are created.

## Explicit Non-Goals

Do not implement in this phase:

- ERPNext Item mapping.
- Material Request creation.
- Purchase Order integration.
- Inventory/procurement valuation.
- Subcontractor IPC integration.
- Full claims module.

These can be built later on top of the quantity revision history.

## Final Instruction to Implementation Agent

Please execute this plan end to end. Do not stop at schema changes. Implement the service layer, VO integration, UI behavior, tests, migration, and evidence notes.

When finished, provide:

1. Summary of implementation.
2. Files changed.
3. Test commands and results.
4. Migration result.
5. Evidence files created.
6. Known limitations or follow-up work.

The user will later ask another reviewer to check your implementation against this handoff.
