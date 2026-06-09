# EV-009: Variation Order Architecture

Date: 2026-06-08

Status: Ready for `WP1.1` policy approval and `WP6` scoping

Replaces: `EV-008` WBS-only policy input

## Product Owner Answers

| Question | Answer |
| --- | --- |
| VO approval | Both Engineer and Client. Client currently approves on a printed/PDF copy; user uploads the signed PDF and changes status to `Approved by Client`. |
| VO numbering | Per BOQ Header. One project can have many BOQ Headers, and each BOQ Header has its own VO sequence. |
| Rate change rule | Three VO types: Quantity Change with possible rate change if quantity changes more than 25%, Item Cancelled/Omission, and New Item Added. |
| Omission policy | Items are omitted before execution starts. No partial certification for omitted items. |
| Procurement linkage | All POs, Stock Entries, and payments link to actual work done. The same transaction link mechanism applies whether the item is original or VO-created. |
| Multiple BOQs per project | Confirmed. One project can have many BOQ Headers, and each BOQ Header manages its own VOs independently. |

## Variation Types

### Type 1: Quantity Change

Used when an existing BOQ Item scope stays the same but the quantity changes.

Rule:

- If the absolute quantity change is less than or equal to 25 percent of contract quantity, the original unit rate applies.
- If the absolute quantity change is more than 25 percent of contract quantity, a new agreed unit rate is required.

Cancelled item as quantity change:

- A full cancellation is `delta_qty = -contract_qty`.
- Revised quantity becomes zero.
- Revised unit price becomes zero.
- The original BOQ Item remains unchanged for audit.

### Type 2: New Item

Used when new scope is added after the contract BOQ is locked.

New item behavior:

- The VO line gets a VO-prefixed WBS code, such as `VO-001-01`.
- On final client approval, the system creates a BOQ Structure and BOQ Item marked as variation items.
- Existing transaction child rows keep using the same universal `boq_item` field.

### Type 3: Omission

Used when an item is removed before execution starts.

Omission behavior:

- `delta_qty = -contract_qty`.
- `revised_qty = 0`.
- Original BOQ Item remains in the system with original contract quantity.
- The VO line records the omission.
- No certified-stage reversal policy is needed because omitted items are omitted before execution.

## FIDIC 25 Percent Rate Trigger

```text
contract_qty   = BOQ Item.quantity
delta_qty      = VO Line.delta_qty
abs_change_pct = abs(delta_qty) / contract_qty * 100

if abs_change_pct > 25:
    rate_change_required = True
    revised_unit_price is mandatory
    rate_change_justification is mandatory
else:
    rate_change_required = False
    revised_unit_price = contract_unit_price
```

This must be enforced server-side on VO Line validation.

## Variation Order DocType

Autoname recommendation: `VO-{boq_header}-{####}` with sequence per BOQ Header.

| Field | Type | Notes |
| --- | --- | --- |
| `boq_header` | Link to BOQ Header | Required. BOQ Header must be `Locked`. |
| `project` | Link to Project | Fetched from BOQ Header, read-only. |
| `vo_number` | Data | Auto-generated `VO-001`, `VO-002`, per BOQ Header. |
| `vo_date` | Date | VO issue date. |
| `description` | Small Text | Scope change summary. |
| `reason` | Small Text | Cause such as design change, site condition, or client instruction. |
| `status` | Select | `Draft`, `Submitted`, `Approved by Engineer`, `Approved by Client`, `Rejected`. |
| `engineer_name` | Data | Engineer who approved. |
| `engineer_approval_date` | Date | Engineer approval date. |
| `client_approval_document` | Attach | Signed PDF. Required before `Approved by Client`. |
| `client_approval_ref` | Data | Client approval reference number. |
| `client_approval_date` | Date | Client approval date. |
| `total_contract_delta` | Currency | Computed sum of VO line value deltas. |
| `notes` | Text Editor | Internal notes. |

## VO Line Child DocType

| Field | Type | Notes |
| --- | --- | --- |
| `line_type` | Select | `Quantity Change`, `New Item`, `Omission`. |
| `boq_item` | Link to BOQ Item | Required for `Quantity Change` and `Omission`; blank for `New Item`. |
| `wbs_code` | Data | Existing item WBS or VO-prefixed WBS for new item. |
| `title` | Data | Existing item title or user-entered title for new item. |
| `unit` | Link to UOM | Existing item unit or user-entered unit for new item. |
| `contract_qty` | Float | Fetched from BOQ Item; zero for new item. |
| `delta_qty` | Float | Signed delta. Omission auto-sets to negative contract quantity. |
| `revised_qty` | Float | Computed contract quantity plus delta. |
| `abs_change_pct` | Percent | Computed absolute quantity change percentage. |
| `rate_change_triggered` | Check | Computed when change exceeds 25 percent; always true for new item. |
| `contract_unit_price` | Currency | Fetched from BOQ Item; zero for new item. |
| `revised_unit_price` | Currency | Mandatory when rate change is triggered. |
| `rate_change_justification` | Small Text | Mandatory when rate change is triggered. |
| `contract_line_value` | Currency | Contract quantity times contract unit price. |
| `revised_line_value` | Currency | Revised quantity times revised unit price. |
| `line_delta_value` | Currency | Revised line value minus contract line value. |
| `notes` | Small Text | Line-level notes. |

## Revised Quantity Service

Future service method:

```python
def get_revised_qty(boq_item_name):
    """Return contract quantity plus approved VO deltas."""
```

Rules:

- No approved VOs means return `BOQ Item.quantity`.
- Only `Approved by Client` VOs affect revised quantities.
- Quantity Change and Omission lines contribute delta quantities.
- New Item lines create BOQ Items on approval, then behave like normal BOQ Items for procurement and stage tracking.

## Final WBS Policy for WP1.1 Approval

1. Contract BOQ WBS codes are immutable from `Pricing` onward.
2. The Contract BOQ structure is fully frozen at `Locked` status.
3. Post-lock scope changes are handled exclusively through Variation Orders.
4. Variation Order new items get WBS codes in `VO-{vo_number}-{seq}` format, generated by the VO approval workflow.
5. VO new items, when approved, create BOQ Structure and BOQ Item records under the locked BOQ Header with `is_variation_item = 1`.
6. A unique `(boq_header, wbs_code)` constraint is approved for the Contract BOQ.
7. Revised quantities are computed on demand as contract quantity plus approved VO deltas.
8. Stage planned quantities are validated against revised quantities when approved VOs exist.
9. Draft-only resequence applies only to Contract BOQ WBS codes.
10. VO WBS codes are immutable once set.
11. Quantity changes more than 25 percent of contract quantity require a new agreed unit price and justification before VO approval.

## WP6 Scheduling

WP1-WP5 remain valid and should not be blocked by WP6. Variation Orders should be scheduled as WP6 after WP3 because VO quantity effects depend on stable WBS and stage measurement behavior.
