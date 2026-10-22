# EV-064: Comprehensive UI Test Plan — Pre-Production Gate

Date: 2026-06-10

## Purpose

This plan documents every UI test required before the BOQ/VO release v6.8.0 can move from staging to production. Tests cover all six work packages (WP1–WP6) through the browser interface on the Frappe Desk.

## Test Environment

- **Site**: v16.localhost (`http://v16.localhost:8000`)
- **User**: Administrator
- **Browser**: Chromium (Playwright headless)
- **Feature flags**: All disabled by default; some tests toggle specific flags

## Test Inventory

| # | Area | WP | Test Name | Automated | Screenshot |
|---|------|----|-----------|-----------|------------|
| 1 | Auth | G0 | Login to Frappe Desk | ✅ | `01_login_desk.png` |
| 2 | Module | G0 | Construction module navigation renders | ✅ | `02_construction_module.png` |
| 3 | Settings | G0 | Feature flags visible in Construction Settings | ✅ | `03_feature_flags.png` |
| 4 | BOQ Header | WP1 | BOQ Header list view renders all records | ✅ | `04_boq_header_list.png` |
| 5 | BOQ Header | WP1 | BOQ Header form (Frozen status, Arabic data) | ✅ | `05_boq_header_form.png` |
| 6 | BOQ Header | WP1 | BOQ Header form (Locked with VO data) | ✅ | `06_boq_header_locked.png` |
| 7 | BOQ Structure | WP1 | BOQ Structure tree view renders WBS hierarchy | ✅ | `07_boq_structure_tree.png` |
| 8 | BOQ Structure | WP1 | BOQ Structure form with WBS code | ✅ | `08_boq_structure_form.png` |
| 9 | BOQ Structure | WP1 | Variation BOQ Structure (is_variation_item) | ✅ | `09_variation_structure.png` |
| 10 | BOQ Item | WP1 | BOQ Item form with Arabic cost_item | ✅ | `10_boq_item_arabic.png` |
| 11 | BOQ Item | WP1 | BOQ Item form with numeric data | ✅ | `11_boq_item_numeric.png` |
| 12 | BOQ Item | WP1 | Variation BOQ Item form | ✅ | `12_variation_boq_item.png` |
| 13 | WBS | WP1 | WBS health check via server (baseline) | ✅ | N/A |
| 14 | Stage | WP3 | BOQ Item Stage list view | ✅ | `14_stage_list.png` |
| 15 | Stage | WP3 | BOQ Item Stage form with measurements | ✅ | `15_stage_form.png` |
| 16 | Stage | WP3 | Stage progress indicators | ✅ | `16_stage_progress.png` |
| 17 | Import | WP2 | BOQ Excel import preview (flag on) | ✅ | `17_import_preview.png` |
| 18 | Import | WP2 | BOQ Excel import commit (flag on) | ✅ | `18_import_commit.png` |
| 19 | Export | WP2 | BOQ Excel export generates file | ✅ | `19_export_excel.png` |
| 20 | Print | WP5 | BOQ Print Format renders (Arabic) | ✅ | `20_print_format.png` |
| 21 | VO | WP6 | Variation Order list view | ✅ | `21_vo_list.png` |
| 22 | VO | WP6 | VO form - Quantity Change, Approved by Engineer | ✅ | `22_vo_quantity_change.png` |
| 23 | VO | WP6 | VO form - New Item, Approved by Client | ✅ | `23_vo_new_item.png` |
| 24 | VO | WP6 | VO form - Omission, Draft | ✅ | `24_vo_omission.png` |
| 25 | VO | WP6 | VO Lines child table rendering | ✅ | `25_vo_lines.png` |
| 26 | VO | WP6 | Revised BOQ report view | ✅ | `26_revised_boq.png` |

## Pass/Fail Criteria

Each test **passes** when:
1. Page loads without HTTP errors (no 4xx/5xx in console)
2. Expected Frappe DocType form/list renders without JS errors
3. Key data fields display correct values
4. Feature-flagged features are hidden when flag is off, visible when flag is on

Each test **fails** when:
1. Page returns 500, 404, or other server error
2. Frappe error dialog appears
3. Expected data is missing or incorrect
4. Console shows JS exceptions

## Evidence Collection

All screenshots saved to:
`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/ev_063_ui_tests/`

Test results recorded in evidence log after execution.

## Test Execution Order

Tests must run serially (not in parallel) to avoid Frappe session conflicts.

1. Check server is up → login
2. Test module navigation and settings
3. Test BOQ Headers (list + 3 form variants)
4. Test BOQ Structures (tree + 2 form variants)
5. Test BOQ Items (3 form variants)
6. Test BOQ Item Stages (list + form)
7. Toggle feature flags → test import/export
8. Restore feature flags → test VO forms
9. Test print format
10. Capture final evidence
