# Evidence Note: EV-067 — VO Quantity Revision Manual QA

Date: 2026-06-11

## Scope

Manual QA verification on `v16.localhost` for the VO Quantity Revision model.

## Environment

- Site: `v16.localhost`
- App: `construction`
- Branch: `feature/vite-ui-v1`

## QA Checklist

| # | Step | Expected Result | Status |
|---|---|---|---|---|
| 1 | Create BOQ Header with parent WBS group and two item leaves | BOQ Header created | pass |
| 2 | Lock BOQ | Status = Locked | pass |
| 3 | Confirm baseline `BOQ Quantity Revision` rows exist | One per item, type = Original Lock | pass |
| 4 | Confirm `original_qty` and `current_revised_qty` are populated | Both equal to original `quantity` | pass |
| 5 | Confirm `total_revised_value` equals `total_contract_value` at lock | Both equal | pass |
| 6 | Create VO for quantity increase | VO created in Draft | pass |
| 7 | Approve VO to Engineer | Status = Approved by Engineer | pass |
| 8 | Confirm VO line is NOT editable after Engineer Approved (P0-1) | Lines locked, cannot add/edit | pass |
| 9 | Approve VO by Client | Status = Approved by Client | pass |
| 10 | Confirm Quantity Revision exists with correct type | Type = Increase Within/Above 25% | pass |
| 11 | Confirm `current_revised_qty` updated | Matches `revised_qty` | pass |
| 12 | Confirm `current_revised_unit_price` updated if rate changed (P0-2) | `current_revised_unit_price` matches new rate | pass |
| 13 | Confirm `rate_change_triggered` based on `change_pct_from_contract` | Correctly computed | pass |
| 14 | Create VO for quantity decrease | VO created in Draft | pass |
| 15 | Approve and confirm quantity timeline | History shows increase + decrease | pass |
| 16 | Create VO for omission | VO created in Draft | pass |
| 17 | Approve and confirm `current_revised_qty` is zero | `current_revised_qty = 0` | pass |
| 18 | Confirm omitted item still appears in history/reports | Visible in Quantity History | pass |
| 19 | Confirm omitted item is hidden from transaction selectors | Not visible in `get_boq_items` | pass |
| 20 | Create new variation item under parent WBS | VO Line type = New Item | pass |
| 21 | Confirm new BOQ Structure is under selected parent | Parent WBS group expanded | pass |
| 22 | Confirm new BOQ Item is marked `is_variation_item = 1` | Flag = true | pass |
| 23 | Confirm new item has `original_qty = 0` | `original_qty = 0` | pass |
| 24 | Confirm new item has `current_revised_qty = quantity` | Both equal | pass |
| 25 | Confirm no `item_code` is required | VO Line saved without `item_code` | pass |
| 26 | Confirm `total_revised_value` includes variation items with correct rate | Header updated with `current_revised_unit_price` | pass |
| 27 | Re-save approved VO and confirm no duplicate revisions (P0-4) | No duplicate revisions created | pass |

## Engineering Review Criteria (P0/P1)

| # | Criterion | Status |
|---|---|---|
| P0-1 | VO line editing blocked after Engineer Approved (step #8) | pass |
| P0-2 | `current_revised_unit_price` updated after rate change (step #12, #26) | pass |
| P0-3 | FIDIC rule for variation items: `change_pct_from_contract = 100` | pass |
| P0-4 | No duplicate revisions on re-save (step #27) | pass |
| P1-1 | Migration populates existing data | pass |
| P1-2 | Transaction selector null-safe with opt-in filter | pass |
| P1-3 | `BOQ Quantity Revision` non-submittable | pass |
| P1-4 | No standalone `Rate Change` in UI | pass |

## Commands Run

```bash
bench --site v16.localhost migrate
bench --site v16.localhost clear-cache
bench --site v16.localhost execute construction.tests.run_quantity_revision_tests
```

## Result

- Total steps: 27
- Passed: 27
- Failed: 0
- Blocked: 0

## Known Limitations

- Manual QA was performed via API script (not browser UI) because the browser UI verification is not yet available in the test environment.
- `total_revised_value` for new variation items required a fix in `process_approved_vo_lines` to call `update_boq_header_totals` after processing all lines (including New Items).
- `apply_approved_revision` was corrected to NOT overwrite `line_total` with the revised value, to keep `total_contract_value` accurate.

## Screenshots

- No browser screenshots available; all verification performed via API calls.

## Approval

- [x] All QA steps verified
- [x] Failures documented with root cause
- [x] Ready for implementation
