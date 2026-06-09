# EV-055 - WP6 Variation Order Foundation

Date: 2026-06-10

## Scope

Implemented and verified the server-side Variation Order foundation for Egypt/Gulf construction ERP commercial control:

- Contract BOQ remains immutable after `Locked`.
- Post-lock changes are raised through `Variation Order`.
- VO numbering is sequential per BOQ Header.
- VO approval chain is `Draft` -> `Submitted` -> `Approved by Engineer` -> `Approved by Client`.
- Signed client PDF is required before final client approval.
- VO line types support `Quantity Change`, `New Item`, and `Omission`.
- FIDIC-style 25 percent quantity-change rate trigger is enforced server-side.
- Approved VOs affect revised quantity.
- New approved VO items create BOQ Structure and BOQ Item records marked as variation items.
- Stage distribution validation uses revised quantity after approved VOs.
- Revised BOQ view and Excel/PDF export surfaces include VO delta and revised values.

## Implemented Files

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/variation_order.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/vo_line.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/variation_orders.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_variation_orders.py`

Related integration changes:

- `BOQ Structure` and `BOQ Item` now have `is_variation_item` and `variation_order` fields.
- `boq_operational` reads revised quantities for stage distribution validation.
- BOQ export includes revised BOQ columns:
  - `VO Qty Delta`
  - `Revised Qty`
  - `VO Value Delta`
  - `Revised Value`

## Verification

Migration completed successfully:

```bash
bench --site v16.localhost migrate
```

Syntax verification passed:

```bash
python -m py_compile construction/tests/test_variation_orders.py construction/services/variation_orders.py construction/services/boq_export_service.py
```

VO-focused verification command:

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_variation_orders --skip-before-tests --lightmode
```

Target VO suite result:

```text
construction.tests.test_variation_orders.TestVariationOrders
   ✔  test_client_approval_requires_signed_pdf_and_affects_revised_qty
   ✔  test_excel_export_includes_revised_boq_columns
   ✔  test_fidic_25_percent_rate_rule
   ✔  test_new_item_creates_variation_boq_structure_and_item
   ✔  test_omission_sets_revised_qty_to_zero
   ✔  test_pdf_export_accepts_revised_boq_columns
   ✔  test_revised_boq_view_and_export_tree_include_approved_vo_delta
   ✔  test_stage_distribution_uses_revised_quantity_after_approved_vo
   ✔  test_variation_order_requires_locked_boq_header
   ✔  test_vo_numbering_is_sequential_per_boq_header
```

Full lightmode runner summary:

```text
Ran 214 tests in 52.229s
FAILED (failures=15, errors=27)
```

The remaining failures are the previously deferred Construction Theme and v6.0 migration test debt recorded in `EV-054`; they are not VO failures.

## Status

WP6.1 through WP6.11 have server-side and export verification evidence.

WP6.12 remains open for manual UI demo/screenshots and manager acceptance because this turn verified behavior through server tests and generated export files, not browser walkthrough screenshots.
