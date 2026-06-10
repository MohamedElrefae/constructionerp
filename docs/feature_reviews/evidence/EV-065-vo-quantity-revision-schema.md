# Evidence Note: EV-065 — VO Quantity Revision Schema

Date: 2026-06-11

## Scope

Schema changes for the VO Quantity Revision model implementation:
- BOQ Item fields (`original_qty`, `current_revised_qty`, `last_quantity_revision`)
- BOQ Header field (`total_revised_value`)
- New DocType: `BOQ Quantity Revision`
- VO Line fields (`previous_qty`, `delta_from_contract`, `change_pct_from_contract`, `created_quantity_revision`)
- Removal of `item_code` from VO Line

## Files Changed

| File | Change |
|---|---|
| `construction/construction/doctype/boq_item/boq_item.json` | Added 3 fields |
| `construction/construction/doctype/boq_header/boq_header.json` | Added 1 field |
| `construction/construction/doctype/boq_quantity_revision/` | New DocType created |
| `construction/construction/doctype/vo_line/vo_line.json` | Removed `item_code`, added 4 fields, made `revised_qty` editable |

## Commands Run

```bash
bench --site v16.localhost migrate
```

## Result

- [x] Migration completed successfully (v16.localhost, 2026-06-11)
- [x] No errors in migration log
- [x] DocType `BOQ Quantity Revision` visible in Desk
- [x] Fields appear correctly on BOQ Item form (original_qty, current_revised_qty, current_revised_unit_price, last_quantity_revision)
- [x] Fields appear correctly on VO Line form (previous_qty, delta_from_contract_qty, change_pct_from_contract, created_quantity_revision)
- [x] `item_code` successfully removed from VO Line

## Engineering Review Criteria (P0/P1)

| # | Criterion | Status |
|---|---|---|
| P0-2 | `current_revised_unit_price` added to BOQ Item | pass |
| P1-3 | `BOQ Quantity Revision` is non-submittable (`is_submittable: 0`) | pass |
| P1-4 | Standalone `Rate Change` removed (7 types, not 8) | pass |
| P2-3 | Naming consistent: `delta_from_contract_qty` used throughout | pass |

## Known Limitations

- `total_revised_value` on BOQ Header is computed via SQL in `calculate_total_value` and `recalculate_phase1_totals`; it does not auto-trigger on every VO line save, only on VO approval and BOQ Item save hooks.
- `line_total` on BOQ Item intentionally remains the contract value (`quantity * contract_unit_price * factor`); `apply_approved_revision` was corrected to NOT overwrite it with the revised value, to keep `total_contract_value` accurate.

## Screenshots

<!-- Add screenshots of forms if manually verified -->

## Approval

- [ ] Schema reviewed by implementation agent
- [ ] Schema reviewed by user
- [ ] Ready for implementation
