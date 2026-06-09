# BOQ Item Review

## Scope

This report reviews `BOQ Item` as the pricing, costing, and quantity row created from leaf BOQ Structure nodes.

## Main Files

- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.py](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.js](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.js)
- [/home/mohamed/frappe-bench/apps/construction/construction/services/boq_operational.py](/home/mohamed/frappe-bench/apps/construction/construction/services/boq_operational.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/services/boq_accounting.py](/home/mohamed/frappe-bench/apps/construction/construction/services/boq_accounting.py)

## Implementation Overview

`BOQ Item` validates through a named step list. The step list makes the validation sequence explicit:

1. Verify the linked structure is a leaf.
2. Enforce BOQ Header status.
3. Validate non-negative quantity/cost/price/factor inputs and percentage ranges.
4. Validate stage distribution when stages are enabled.
5. Fetch cost item data.
6. Calculate overhead, profit, sell price, and estimated line total.
7. Calculate contract line total.
8. Validate computed outputs.

The status model is:

- `Locked`: no edits.
- `Frozen`: no edits.
- `Pricing`: only pricing-related fields can change.
- `Draft`: normal editing.

The cost model calculates:

- `overhead_amount = est_unit_cost * overhead_pct / 100`
- `profit_amount = (est_unit_cost + overhead_amount) * profit_pct / 100`
- `calculated_sell_price = est_unit_cost + overhead_amount + profit_amount`
- `est_line_total = quantity * est_unit_cost * factor`
- `line_total = quantity * contract_unit_price * factor`

After update or delete, the BOQ Item triggers parent header roll-up totals.

The client script is light: it adds `View Stages` and `Add Stage` buttons and hides the native dashboard.

## Strengths

- The validation flow is easy to audit because it is declared in `PHASE1_STEPS`.
- Pricing mode field-level restrictions are server-side and compare old/new values by field type.
- The item model defensively validates both inputs and computed outputs.
- CostItem lookup is graceful if the `CostItem` DocType is not deployed.
- Header roll-up is triggered from the item lifecycle, which keeps totals in sync with edits.
- Stage validation is delegated into a service rather than embedded directly in the controller.

## Risks and Gaps

- New BOQ Items are allowed in `Pricing` status. That may be intentional, but it conflicts with the usual idea that `Pricing` should only price an already-built structure.
- `fetch_cost_item_data()` swallows all exceptions and sets cost to zero. That prevents crashes, but can silently erase cost data if a database or permission issue occurs.
- The server allows `has_stages` as a pricing-editable field. Turning stages on/off during Pricing can materially change operational tracking.
- The client only adds stage navigation and does not surface stage distribution completeness or warnings.
- There is no direct check here for existing downstream transactions before changing quantities/prices. Transaction validation protects rows at transaction save time, but historical attribution risk remains.

## Review Opinion

`BOQ Item` is one of the cleanest server implementations in the app. The explicit validation pipeline is a good pattern to keep. The main concern is silent fallback behavior and the business meaning of allowing new items or stage toggles during Pricing.

## Recommended Next Steps

1. Confirm whether new BOQ Items should be allowed after Draft.
2. Replace broad exception swallowing in `fetch_cost_item_data()` with logging plus specific fallback cases.
3. Add UI indicators for stage total completeness when `has_stages` is enabled.
4. Add tests for Pricing field restrictions, negative guards, percentage guards, cost buildup, line totals, and header roll-up.
5. Define whether quantity changes after transaction attribution should be blocked, warned, or versioned.
