# EV-056 - WP6.12 Browser QA and Manual VO Demo

Date: 2026-06-10

## Scope

Performed browser-level manual QA for Variation Order workflow using Playwright headless Chromium against `v16.localhost`.

## Test Data Setup

Created persistent QA dataset:

- **BOQ Header**: `BOQ-2026-0274` — `VO Browser QA BOQ` (Locked)
- **BOQ Item**: `BOQI-BOQ-2026-0274-0275` — `Concrete Slab Item` (quantity 100, rate 50)
- **VO 1**: `BOQ-2026-0274-VO-001` — Quantity Change (+25 qty, rate 55) — `Approved by Engineer`
- **VO 2**: `BOQ-2026-0274-VO-002` — New Item (`Waterproofing membrane`, 200 qty, rate 35) — `Approved by Client`
- **VO 3**: `BOQ-2026-0274-VO-003` — Omission (full omission of Concrete Slab Item) — `Draft`

## Screenshots Captured

All screenshots saved to:
`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp6_browser_qa/`

| File | Content |
|------|---------|
| `01_login_desk.png` | Frappe desk after Administrator login |
| `02_vo_list.png` | Variation Order list view |
| `03_vo1_quantity_change_form.png` | VO-001 form: Quantity Change, Approved by Engineer |
| `03b_vo1_lines_section.png` | VO-001 VO Lines child table |
| `04_vo2_new_item_form.png` | VO-002 form: New Item, Approved by Client, signed PDF attached |
| `04b_vo2_lines_section.png` | VO-002 VO Lines child table showing `VO-002-01` WBS code |
| `05_vo3_omission_form.png` | VO-003 form: Omission, Draft status |
| `05b_vo3_lines_section.png` | VO-003 VO Lines child table showing revised qty 0 |
| `06_boq_header_locked.png` | BOQ Header `BOQ-2026-0274` in Locked status |
| `07_boq_structure_list.png` | BOQ Structure list showing original and variation rows |
| `08_original_structure.png` | Original `Concrete Slab Item` structure (is_variation_item = 0) |
| `09_variation_structure.png` | Variation `Waterproofing membrane` structure (is_variation_item = 1, WBS `VO-002-01`) |
| `10_boq_item_list.png` | BOQ Item list showing both original and variation items |
| `11_original_boq_item.png` | Original BOQ Item form |
| `12_variation_boq_item.png` | Variation BOQ Item form (quantity 200, value 7,000) |

## Verification Summary

- [x] VO list view renders without errors.
- [x] VO form shows all header fields: BOQ Header, project, VO number, VO date, status, engineer/client approval fields.
- [x] VO Lines child table displays line type, BOQ item reference, delta qty, revised qty, unit price, and WBS code.
- [x] Quantity Change line shows positive delta and revised quantity.
- [x] New Item line shows created WBS code `VO-002-01` and links to new BOQ Structure/Item.
- [x] Client-approved VO shows signed PDF attachment (`private/files/signed-vo2.pdf`).
- [x] Omission line shows negative delta and zero revised quantity.
- [x] BOQ Header remains Locked and is not editable.
- [x] Variation BOQ Structure is marked `is_variation_item = 1` and links to originating VO.
- [x] Variation BOQ Item carries correct quantity and contract unit price.
- [x] BOQ Item list shows both contract and variation items together.

## Status

WP6.12 browser QA evidence is complete. Manager/reviewer acceptance (`ACC`) is pending.
