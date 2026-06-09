# BOQ Item Stage Review

## Scope

This report reviews `BOQ Item Stage` as the operational progress breakdown for staged BOQ Items.

## Main Files

- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.py](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js)
- [/home/mohamed/frappe-bench/apps/construction/construction/services/boq_operational.py](/home/mohamed/frappe-bench/apps/construction/construction/services/boq_operational.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py](/home/mohamed/frappe-bench/apps/construction/construction/api/boq_link_queries.py)

## Implementation Overview

`BOQ Item Stage` validates its selection chain, fetches parent context from `BOQ Item`, and validates quantities.

On insert, it auto-assigns `stage_code` as `STG-001`, `STG-002`, and so on when a code is not manually provided. It checks for duplicate stage code per BOQ Item before insert. The DocType update hook also adds a unique constraint on `(boq_item, stage_code)` and indexes for lookup performance.

The parent context fetch makes the stage inherit:

- `boq_header` from the selected item.
- `boq_structure` from the selected item structure.
- `project` from the selected BOQ Header.

Quantity validation enforces:

- `planned_qty`, `measured_executed_qty`, and `certified_qty` must be non-negative.
- `certified_qty` cannot exceed measured executed quantity.
- `percent_complete` must be between 0 and 100.
- Draft/Pricing total planned quantity cannot exceed parent item quantity.
- Frozen/Locked total planned quantity must equal parent item quantity within tolerance.

The client script filters BOQ Header, Structure, and Item links and clears downstream fields when upstream selections change.

## Strengths

- Stage records are strongly anchored to their parent item/header/structure/project.
- Quantity rules are simple and domain-appropriate.
- The `FOR UPDATE` lock in planned distribution validation helps avoid concurrent over-allocation on the same item.
- Auto stage code generation improves usability while still allowing manual codes.
- Server-side unique index protects against duplicate stage codes beyond client validation.

## Risks and Gaps

- `assign_stage_code_if_missing()` is count/max based. Two concurrent inserts can choose the same next code; the unique index will protect data, but one user may see a save failure.
- There is no status enforcement in the stage controller itself beyond distribution rules. In Frozen/Locked states, exact distribution is required, but edits to existing stage names/status/progress may still be possible unless blocked elsewhere.
- The stage client filters do not include all scope/cascade gates used by transaction child rows.
- Stage percentage and measured/certified values do not appear to roll up into BOQ Item progress yet.
- Stage validation runs before `fetch_parent_context()`. The selection chain is checked first, then parent fields are overwritten. That works, but future validators must remember this order.

## Review Opinion

The stage feature is implemented with good parent integrity and quantity discipline. It is ready for controlled use, but it needs a clearer lifecycle policy: are stages editable in Frozen/Locked BOQs for progress tracking, or should commercial freeze also lock stage planning while allowing execution fields?

## Recommended Next Steps

1. Define edit policy by field group: planning fields, execution fields, certification fields.
2. Add explicit status enforcement for stage edits rather than relying only on distribution rules.
3. Add tests for concurrent duplicate code handling, exact distribution in Frozen/Locked, over-planning in Draft/Pricing, and parent context overwrite.
4. Consider showing parent item quantity and total planned quantity on the stage form/list.
5. Add roll-up progress metrics if stage execution is intended to drive BOQ progress.
