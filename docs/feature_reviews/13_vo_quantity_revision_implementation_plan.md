# AI Agent Handoff: VO Quantity Revision Model Implementation (v2)

Date: 2026-06-11

Version: 2.0

Reviewed by: Head of Engineering

Status: Approved for implementation after addressing P0 and P1 findings.

Workspace: `/home/mohamed/frappe-bench`

Primary app: `/home/mohamed/frappe-bench/apps/construction`

Target site for verification: `v16.localhost`

## Handoff Purpose

This is the revised implementation plan (v2) addressing all engineering review findings (P0 and P1). The plan is approved for implementation.

## Engineering Review Summary

**Reviewed:** `docs/feature_reviews/15_head_engineering_review_vo_quantity_revision.md`

**Decision:** Conditionally approved. All blockers have been addressed in this v2 plan.

**Blockers addressed:**
- P0-1: VO line editing locked after Engineer Approved (enterprise policy)
- P0-2: `current_revised_unit_price` added to BOQ Item for rate-aware value computation
- P0-3: FIDIC rule for variation items with `original_qty = 0` defined
- P0-4: Idempotent and transactional VO approval with strict line-level checks
- P1-1: Migration/backfill strategy for existing data documented
- P1-2: Null-safe transaction selector filtering with opt-in flag
- P1-3: `BOQ Quantity Revision` status model clarified
- P1-4: Standalone `Rate Change` removed from revision types

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
   - quantity (total revised quantity),
   - unit price,
   - owner/client references where available,
   - reason/reference.
5. System creates normal BOQ Structure and BOQ Item records under the selected parent group.
6. System marks the BOQ Item as variation:
   - `is_variation_item = 1`
   - `variation_order = <VO name>`
7. System creates an approved quantity revision after VO Client approval.

### Quantity Increase or Decrease

Expected UX:

1. User selects existing BOQ Item.
2. System shows current approved quantity as `previous_qty` (reference).
3. System shows original contract quantity as `contract_qty`.
4. User enters total `revised_qty`.
5. System computes:
   - `delta_qty = revised_qty - previous_qty` (change from current revised),
   - `delta_from_contract_qty = revised_qty - contract_qty` (change from contract),
   - `change_pct_from_contract = abs(delta_from_contract_qty) / contract_qty * 100` (FIDIC threshold for original items),
   - value impact,
   - rate-change trigger based on `change_pct_from_contract`.
6. On approval, system records a quantity revision with actual `previous_qty` from DB and updates the BOQ Item `current_revised_qty`.

### Omission

Expected UX:

1. User selects existing BOQ Item.
2. User chooses `Omission`.
3. System sets `revised_qty = 0`.
4. System computes `delta_qty = -previous_qty`.
5. On approval, system records omission in quantity history.
6. Omitted item is not deleted.

### VO Line Editing Policy (P0-1 Resolution)

**Enterprise Policy:** VO lines are editable only in Draft and Submitted statuses.

| VO Status | Can Add Lines? | Can Edit Lines? | Can Delete Lines? |
|---|---|---|---|
| **Draft** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Submitted** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Approved by Engineer** | ❌ No | ❌ No | ❌ No |
| **Approved by Client** | ❌ No | ❌ No | ❌ No |
| **Rejected** | ❌ No | ❌ No | ❌ No |

**Rationale:** If a user needs to change scope after Engineer Approval, the VO must be returned to Submitted status (or a new VO must be created). This preserves approval integrity.

**Validation:** `variation_order.py` must enforce that line edits cannot occur when `status in ['Approved by Engineer', 'Approved by Client', 'Rejected']`.

## Implementation Requirements

### 1. BOQ Item Schema

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.json`

Add fields:

- `original_qty` Float, read-only
- `current_revised_qty` Float, read-only
- `current_revised_unit_price` Currency, read-only *(P0-2 Resolution)*
- `last_quantity_revision` Link to `BOQ Quantity Revision`, read-only

Semantic rules:

- For original BOQ items, `quantity` remains the original/contract quantity.
- `original_qty` is captured when BOQ becomes Locked.
- `current_revised_qty` is the latest approved revised quantity.
- `current_revised_unit_price` is the latest approved unit price (P0-2).
- For variation BOQ items, `original_qty = 0` and `current_revised_qty = quantity`.
- For variation BOQ items, `current_revised_unit_price` is set at creation time.

### 2. BOQ Header Schema

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.json`

Add field:

- `total_revised_value` Currency, read-only/computed

Semantic rules:

- `total_contract_value` remains original contract value (from `quantity` of non-variation items).
- `total_revised_value` is computed from `current_revised_qty * current_revised_unit_price * factor` for all items (contract + variation) *(P0-2 Resolution)*.
- If `current_revised_unit_price` is null (migration), fall back to `contract_unit_price`.

### 3. New DocType: BOQ Quantity Revision

Create:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_quantity_revision/`

Required files:

- `boq_quantity_revision.json`
- `boq_quantity_revision.py`
- `__init__.py`

**DocType Configuration (P1-3 Resolution):**

- `is_submittable`: 0 (non-submittable)
- `custom_status` field drives approval state
- `track_changes`: 1
- `read_only_onload`: 1 (for Approved records)

Required fields:

- `boq_header` Link to `BOQ Header`, required
- `boq_structure` Link to `BOQ Structure`, required
- `boq_item` Link to `BOQ Item`, required
- `variation_order` Link to `Variation Order`
- `revision_date` Date, required
- `revision_type` Select, required, auto-computed
- `previous_qty` Float, required
- `revised_qty` Float, required
- `delta_qty` Float, read-only/computed
- `delta_from_contract_qty` Float, read-only/computed *(P2-3 Naming consistency)*
- `change_pct` Percent, read-only/computed
- `change_pct_from_contract` Percent, read-only/computed
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

Recommended `revision_type` options (auto-computed by system, 7 types *(P1-4 Resolution)*):

```text
Original Lock
New Variation Item
Increase Within 25%
Decrease Within 25%
Increase Above 25%
Decrease Above 25%
Omission
```

**Validation rules:**

- `revised_qty >= 0`
- `delta_qty = revised_qty - previous_qty`
- `delta_from_contract_qty = revised_qty - original_qty` (read from BOQ Item)
- `change_pct = abs(delta_qty) / previous_qty * 100` when `previous_qty > 0`
- `change_pct_from_contract`:
  - If `original_qty > 0`: `abs(delta_from_contract_qty) / original_qty * 100`
  - If `original_qty = 0`: set to `100` (new variation item) *(P0-3 Resolution)*
- `rate_change_triggered = 1` if `change_pct_from_contract > 25`
- `previous_value = previous_qty * contract_unit_price`
- `revised_value = revised_qty * revised_unit_price`
- `delta_value = revised_value - previous_value`
- Omission requires `revised_qty = 0`
- New Variation Item requires `previous_qty = 0`
- Original Lock must be system-generated
- **Approved revisions cannot be edited** (controller validation)

**Revision type auto-computation logic:**

```python
if previous_qty == 0 and revised_qty > 0:
    type = "New Variation Item"
elif revised_qty == 0:
    type = "Omission"
elif revised_qty > previous_qty:
    type = "Increase Above 25%" if change_pct_from_contract > 25 else "Increase Within 25%"
elif revised_qty < previous_qty:
    type = "Decrease Above 25%" if change_pct_from_contract > 25 else "Decrease Within 25%"
else:
    type = "Increase Within 25%"  # qty unchanged, price changed (rare)
```

### 4. Quantity Revision Service

Create:

`/home/mohamed/frappe-bench/apps/construction/construction/services/quantity_revisions.py`

Required functions:

- `create_lock_baseline(boq_header)`
- `get_current_qty(boq_item)`
- `get_current_unit_price(boq_item)` *(P0-2)*
- `create_quantity_revision(...)`
- `approve_quantity_revision(revision_name)`
- `apply_approved_revision(revision)` *(P0-4)*
- `create_variation_item_revision(...)`

**Service requirements:**

- Use DB row locking (`SELECT ... FOR UPDATE`) where needed to avoid stale quantity approval.
- Make `create_lock_baseline` idempotent.
- Update `BOQ Item.current_revised_qty` **only when a revision is approved**.
- Update `BOQ Item.current_revised_unit_price` **only when a revision is approved** *(P0-2)*.
- Update `BOQ Item.last_quantity_revision` when a revision is approved.
- Do not update original quantity after lock except controlled migration/correction.

**Transactional Approval Requirements (P0-4 Resolution):**

```python
def process_approved_vo_lines(vo):
    """Process all VO lines atomically on Client Approval.
    
    Requirements:
    1. Check created_quantity_revision before creating new revision.
    2. Check created_boq_item / created_boq_structure before creating new variation items.
    3. Lock BOQ Item row during approval.
    4. Validate actual DB current_revised_qty matches expected.
    5. Apply all lines or fail cleanly (no partial approval).
    """
    for line in vo.lines:
        if line.created_quantity_revision:
            continue  # Skip already processed lines
        
        # Lock BOQ Item row
        frappe.db.sql("SELECT name FROM `tabBOQ Item` WHERE name = %s FOR UPDATE", line.boq_item)
        
        # Read actual current values from DB
        actual_previous_qty = frappe.db.get_value("BOQ Item", line.boq_item, "current_revised_qty")
        actual_unit_price = frappe.db.get_value("BOQ Item", line.boq_item, "current_revised_unit_price")
        
        # Create revision with actual values
        revision = create_quantity_revision(
            boq_item=line.boq_item,
            previous_qty=actual_previous_qty,
            revised_qty=line.revised_qty,
            contract_unit_price=actual_unit_price or line.contract_unit_price,
            revised_unit_price=line.revised_unit_price,
            variation_order=vo.name,
            status="Approved",
        )
        
        # Apply revision
        apply_approved_revision(revision)
        
        # Link back to VO line
        line.db_set("created_quantity_revision", revision.name, update_modified=False)
```

### 5. BOQ Lock Baseline

Modify BOQ Header lock behavior:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.py`

On BOQ lock:

1. For every BOQ Item under the header:
   - set `original_qty = quantity`
   - set `current_revised_qty = quantity`
   - set `current_revised_unit_price = contract_unit_price` *(P0-2)*
2. Create one approved `BOQ Quantity Revision`:
   - `revision_type = Original Lock`
   - `previous_qty = 0`
   - `revised_qty = quantity`
   - `delta_qty = quantity`
   - `status = Approved`
3. Do not duplicate baseline rows if operation runs again.

### 6. VO Line Simplification

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.json`

Required changes:

- Remove `item_code` field completely.
- Add `previous_qty` Float, read-only.
- Make `revised_qty` editable.
- Add `delta_from_contract_qty` Float, read-only/computed *(P2-3)*.
- Add `change_pct_from_contract` Percent, read-only/computed.
- Add `created_quantity_revision` Link to `BOQ Quantity Revision`.
- Keep owner reference fields:
  - `owner_page`
  - `owner_ref_no`
  - `owner_file_ref`

VO Line behavior:

- `New Item`: user enters normal item details and total `revised_qty`. `previous_qty = 0`. `contract_qty = 0`.
- `Quantity Change`: user selects existing BOQ Item and enters total `revised_qty`. `previous_qty` shows reference value from `current_revised_qty`. `contract_qty` shows original `quantity`.
- `Omission`: system forces `revised_qty = 0`. `previous_qty` shows reference value.
- `rate_change_triggered` computed from `change_pct_from_contract` (FIDIC rule).
- `delta_qty` computed from `revised_qty - previous_qty`.
- `delta_from_contract_qty` computed from `revised_qty - contract_qty`.

### 7. VO Line Controller

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.py`

Required changes:

- Remove `item_code` requirement.
- Primary input is `revised_qty` (user enters total surveyed quantity).
- `delta_qty` is computed: `revised_qty - previous_qty`.
- `previous_qty` is fetched from `BOQ Item.current_revised_qty` as a **reference display value**.
- `contract_qty` is fetched from `BOQ Item.quantity` (original contract quantity).
- For `Quantity Change` and `Omission`: `rate_change_triggered` computed from `abs(delta_from_contract_qty) / contract_qty * 100`.
- For `New Item`: `rate_change_triggered = 1` (always a new rate, explicit rate required).
- Validation: `revised_qty >= 0`. For `Omission`: `revised_qty` must be `0`. For `New Item`: `revised_qty > 0`.
- **FIDIC rule for variation items (P0-3)**: if `contract_qty = 0` (new variation item), `change_pct_from_contract = 100` and `rate_change_triggered = 1`.

### 8. Variation Order Controller

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.py`

**Idempotent Approval Requirements (P0-4 Resolution):**

```python
def on_update(self):
    if self.status == CLIENT_APPROVED_STATUS:
        self.process_approved_vo_lines()

def process_approved_vo_lines(self):
    """Atomic, idempotent VO line processing.
    
    Rules:
    - Skip lines that already have created_quantity_revision.
    - Skip lines that already have created_boq_item / created_boq_structure.
    - Lock BOQ Item rows.
    - Read actual current_revised_qty from DB (not reference from VO line).
    - Create one revision per line.
    - Apply all revisions or fail cleanly.
    """
    for line in self.lines:
        # Idempotency check
        if line.created_quantity_revision:
            continue
        
        if line.line_type == "New Item":
            if line.created_boq_item:
                continue
            # Create variation item and revision
            # ... (see existing create_variation_structure_and_item)
        elif line.line_type in ("Quantity Change", "Omission"):
            # Read actual current values from DB
            actual_qty = frappe.db.get_value("BOQ Item", line.boq_item, "current_revised_qty")
            actual_price = frappe.db.get_value("BOQ Item", line.boq_item, "current_revised_unit_price")
            
            # Create revision with actual values
            revision = create_quantity_revision(
                boq_item=line.boq_item,
                previous_qty=actual_qty,
                revised_qty=line.revised_qty,
                contract_unit_price=actual_price,
                revised_unit_price=line.revised_unit_price,
                variation_order=self.name,
                status="Approved",
            )
            
            # Apply revision
            apply_approved_revision(revision)
            
            # Link back to VO line
            line.db_set("created_quantity_revision", revision.name, update_modified=False)
```

**Approval Integrity (P0-1 Resolution):**

```python
def validate_lines(self):
    # ... existing validation ...
    
    # P0-1: Block line edits after Engineer Approved
    if self.status in (ENGINEER_APPROVED_STATUS, CLIENT_APPROVED_STATUS, REJECTED_STATUS):
        # Check if any lines were modified from DB state
        for line in self.lines:
            if line.name and frappe.db.exists("VO Line", line.name):
                db_line = frappe.get_doc("VO Line", line.name)
                # Compare key fields
                if (line.revised_qty != db_line.revised_qty or
                    line.revised_unit_price != db_line.revised_unit_price or
                    line.line_type != db_line.line_type):
                    frappe.throw(_("Cannot modify VO lines after Engineer Approval. Return to Submitted status to edit."))
```

### 9. Client Scripts

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.js`

Required behavior:

- Remove `item_code` references.
- When `boq_item` is selected, fetch and show:
  - `current_revised_qty` (shown as `previous_qty` reference),
  - `quantity` (shown as `contract_qty`),
  - contract unit price,
  - title/unit/WBS context.
- Make `revised_qty` the primary input.
- Compute `delta_qty = revised_qty - previous_qty`.
- Compute `delta_from_contract_qty = revised_qty - contract_qty`.
- Compute `change_pct_from_contract`:
  - If `contract_qty > 0`: `abs(delta_from_contract_qty) / contract_qty * 100`
  - If `contract_qty = 0`: `100` (new variation item)
- For omission, set `revised_qty = 0`.
- **Lock all VO lines after Engineer Approved** (P0-1 Resolution):
  - Draft: editable
  - Submitted: editable
  - Engineer Approved: read-only
  - Client Approved: read-only
  - Rejected: read-only

### 10. Link Queries

Modify:

`/home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py`

Required behavior:

- Support selecting parent WBS groups for New Item.
- Support selecting existing BOQ Items for quantity change/omission.
- Hide fully omitted items from transaction selectors by using `COALESCE(current_revised_qty, quantity) > 0` *(P1-2 Resolution)*.
- **Opt-in filter**: Only apply `current_revised_qty > 0` when `filters.get("exclude_zero_revised")` is True.
- Do not hide omitted items from audit, revised BOQ, or history reports.
- Replace `quantity + SUM(delta)` subquery with `COALESCE(current_revised_qty, quantity) > 0`.

### 11. Reports (Query Service Layer)

Implement or update query service in:

`/home/mohamed/frappe-bench/apps/construction/construction/services/revised_boq_queries.py`

Required functions:

1. `get_original_boq(boq_header)`
   - uses `original_qty`
   - shows original contract value
   - filters `is_variation_item = 0`

2. `get_revised_boq(boq_header)` *(P0-2 Resolution)*
   - uses `current_revised_qty` and `current_revised_unit_price`
   - shows original qty, revised qty, delta qty, delta from contract, original value, revised value, delta value
   - includes both contract and variation items

3. `get_quantity_history(boq_item)`
   - full timeline per item from `BOQ Quantity Revision`
   - ordered by `revision_date`

4. `get_vo_impact(boq_header)`
   - commercial impact grouped by VO
   - sums `delta_value` per VO

5. `get_omitted_items(boq_header)`
   - items where `current_revised_qty = 0` and `is_variation_item = 0`

UI report templates are a follow-up task.

## Migration Strategy (P1-1 Resolution)

### Existing Data Backfill

1. **Existing non-variation BOQ Items under Locked BOQs:**
   - Set `original_qty = quantity`
   - Set `current_revised_qty = quantity`
   - Set `current_revised_unit_price = contract_unit_price`
   - Create `BOQ Quantity Revision` (type = Original Lock) if not exists

2. **Existing variation BOQ Items:**
   - Set `original_qty = 0`
   - Set `current_revised_qty = quantity`
   - Set `current_revised_unit_price = contract_unit_price`
   - Create `BOQ Quantity Revision` (type = New Variation Item) where possible

3. **Existing approved VO-created variation items:**
   - Create `BOQ Quantity Revision` (type = New Variation Item) for each
   - Link to VO Line

4. **Existing approved Quantity Change/Omission VO lines:**
   - Migrate to `BOQ Quantity Revision` where possible
   - Or explicitly mark as legacy and exclude from new revision totals
   - Document legacy items in migration log

**Migration patch:** `construction/patches/v7_0_migrate_quantity_revisions.py`

## Required Tests

Add or update tests in:

- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_variation_orders.py`
- optionally `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_link_queries.py`
- create `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_quantity_revisions.py`

Required automated coverage:

- Locking BOQ creates baseline quantity revisions.
- Re-saving locked BOQ does not duplicate baseline revisions.
- `original_qty` remains unchanged after approved revisions.
- `current_revised_qty` updates after approved revision.
- `current_revised_unit_price` updates after approved revision with rate change *(P0-2)*.
- Draft revision does not update `current_revised_qty`.
- Quantity increase computes correct delta and value (both `delta_qty` and `delta_from_contract_qty`).
- Quantity decrease computes correct delta and value.
- `rate_change_triggered` computed from `change_pct_from_contract` (FIDIC rule).
- **Rate change updates `total_revised_value` correctly** *(P0-2)*.
- Omission sets revised quantity to zero.
- New variation item after lock creates BOQ Structure, BOQ Item, and Quantity Revision.
- Normal post-lock BOQ item creation remains blocked.
- Controlled variation item creation after lock is allowed.
- Fully omitted item is hidden only from transaction selectors.
- Quantity history can reconstruct the item timeline.
- No `item_code` is required for New Item VO lines.
- VO line revision type auto-computed correctly (Increase/Decrease Above/Below 25%).
- **VO line editing blocked after Engineer Approved** *(P0-1)*.
- **Re-saving Approved VO does not duplicate revisions** *(P0-4)*.
- **Migration sets `original_qty` and `current_revised_qty` for existing items** *(P1-1)*.

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
3. Confirm baseline `BOQ Quantity Revision` rows exist (one per item, type = Original Lock).
4. Confirm `original_qty`, `current_revised_qty`, `current_revised_unit_price` are populated.
5. Confirm `total_revised_value` equals `total_contract_value` at lock.
6. Create VO for quantity increase.
7. Approve VO to Engineer.
8. **Confirm VO line is NOT editable** (P0-1).
9. Approve VO by Client.
10. Confirm Quantity Revision exists with correct type (Increase Within/Above 25%).
11. Confirm `current_revised_qty` updated.
12. Confirm `current_revised_unit_price` updated if rate changed (P0-2).
13. Confirm `rate_change_triggered` based on `change_pct_from_contract`.
14. Create VO for quantity decrease.
15. Approve and confirm quantity timeline.
16. Create VO for omission.
17. Approve and confirm `current_revised_qty` is zero.
18. Confirm omitted item still appears in history/reports.
19. Confirm omitted item is hidden from transaction selectors.
20. Create new variation item under parent WBS.
21. Confirm new BOQ Structure is under the selected parent.
22. Confirm new BOQ Item is marked `is_variation_item = 1`.
23. Confirm new item has `original_qty = 0` and `current_revised_qty = quantity`.
24. Confirm `current_revised_unit_price` set at creation.
25. Confirm no `item_code` is required.
26. Confirm `total_revised_value` on BOQ Header includes variation items with correct rates.
27. **Re-save approved VO and confirm no duplicate revisions** (P0-4).

## Evidence Requirements

Create evidence notes under:

`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/`

Required evidence files (implementation is not complete until these are filled):

- `EV-065-vo-quantity-revision-schema.md` *(P2-1 Resolution)*
- `EV-066-vo-quantity-revision-tests.md` *(P2-1 Resolution)*
- `EV-067-vo-quantity-revision-manual-qa.md` *(P2-1 Resolution)*

Each evidence note must include:

- date,
- files changed,
- command run,
- result,
- known limitations,
- screenshots only if UI was manually verified.

**Implementation is not complete until evidence files are filled with actual results, not templates.**

## Files Most Likely to Change

Expected files:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_quantity_revision/`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.js`
- `/home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/quantity_revisions.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/revised_boq_queries.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_variation_orders.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_link_queries.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_quantity_revisions.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/patches/v7_0_migrate_quantity_revisions.py` *(P1-1)*

Before editing, inspect existing implementation carefully. There is already a VO module, existing lock protection, and existing `ignore_boq_status_for_variation` behavior.

## Acceptance Criteria

The work is complete only when:

- `item_code` is not present in VO Line schema.
- BOQ lock creates original quantity snapshots (`original_qty`, `current_revised_qty`, `current_revised_unit_price`).
- `BOQ Quantity Revision` exists with 7 auto-computed revision types.
- `rate_change_triggered` computed from `change_pct_from_contract` (FIDIC rule from contract qty).
- **Rate change updates `current_revised_unit_price` and `total_revised_value`** (P0-2).
- Original quantity remains available after revisions.
- Current revised quantity reflects latest approved revision.
- Quantity increase, decrease, omission, and new variation item are supported.
- New items after lock are normal BOQ Items marked as variation items.
- Direct post-lock BOQ item edits remain blocked.
- Omitted items remain auditable.
- Transaction selectors can hide omitted items without hiding them from history/reporting.
- **VO line editing blocked after Engineer Approved** (P0-1).
- **Re-saving Approved VO does not duplicate revisions** (P0-4).
- **Migration handles existing data** (P1-1).
- Automated tests pass or failures are documented with root cause.
- Migration succeeds on `v16.localhost`.
- **Evidence files filled with actual results** (P2-1).
- `total_revised_value` added to BOQ Header.
- VO lines editable only in Draft and Submitted.

## Explicit Non-Goals

Do not implement in this phase:

- ERPNext Item mapping.
- Material Request creation.
- Purchase Order integration.
- Inventory/procurement valuation.
- Subcontractor IPC integration.
- Full claims module.
- UI report templates (HTML/CSS) — data layer only.
- Standalone `Rate Change` revision type (removed per P1-4).

These can be built later on top of the quantity revision history.

## Final Instruction to Implementation Agent

Please execute this plan end to end. Do not stop at schema changes. Implement the service layer, VO integration, UI behavior, tests, migration, and evidence notes.

When finished, provide:

1. Summary of implementation.
2. Files changed.
3. Test commands and results.
4. Migration result.
5. Evidence files created (with actual results).
6. Known limitations or follow-up work.

The user will later ask another reviewer to check your implementation against this handoff.
