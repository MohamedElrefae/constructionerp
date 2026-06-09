# BOQ Header Review

## Scope

This report reviews the `BOQ Header` implementation as the parent commercial document for BOQ status, project context, roll-up totals, import/export entry points, and navigation into structure/item views.

## Main Files

- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.py](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.js](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_header/boq_header.js)
- [/home/mohamed/frappe-bench/apps/construction/construction/api/boq_api.py](/home/mohamed/frappe-bench/apps/construction/construction/api/boq_api.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/hooks.py](/home/mohamed/frappe-bench/apps/construction/construction/hooks.py)

## Implementation Overview

`BOQ Header` owns the BOQ lifecycle. The server-side controller defines one-way status movement from `Draft` to `Pricing` to `Frozen` to `Locked`. The transition check runs during validation, and locked metadata is written in `on_update` when the status reaches `Locked`.

The header calculates three roll-up values from related `BOQ Item` rows:

- `total_contract_value` from `SUM(line_total)`.
- `total_estimated_value` from `SUM(est_line_total)`.
- `total_budgeted_cost` from `SUM(quantity * est_unit_cost * COALESCE(factor, 1.0))`.

The same SQL aggregation exists in `calculate_total_value()` and `recalculate_phase1_totals()`. `BOQ Item` calls `recalculate_phase1_totals()` on update and delete, so totals are refreshed without forcing a full header save cycle.

The client script adds:

- View menu for tree/table BOQ Structure navigation.
- Export menu for header-only and full BOQ Excel/PDF.
- Print options.
- Advance Status action.
- Draft-only Excel import action.

The hook layer registers the BOQ Header form script in `doctype_js`, and globally includes the print/export/menu infrastructure used by the form.

## Strengths

- Status transitions are enforced server-side, not only in the UI.
- Header totals are calculated from authoritative item rows, avoiding manual total entry.
- The item-to-header roll-up uses `db_set(update_modified=False)`, which avoids unnecessary save loops.
- Export/import behavior is integrated into the form and API rather than being hidden in separate pages.
- The UI correctly hides import behind `Draft` status, matching the idea that frozen/locked BOQs should not be structurally altered.

## Risks and Gaps

- The transition map is duplicated in Python and JavaScript. Python is authoritative, but the UI can drift if new states are added.
- New BOQ headers always get totals reset to zero during validation. That is fine for new documents, but any future inline child/import behavior before insert should account for this.
- `advance_boq_status()` returns structured failure instead of throwing for invalid transitions. That is easy for UI handling, but integrations may silently proceed if they do not inspect `success`.
- Header roll-up SQL is duplicated in two methods. This is not dangerous now, but future formula changes could be applied to one method and missed in the other.
- The export menu depends on global constructors (`PrintSettingsDialog`, `ConstructionExportMenu`, `ConstructionViewMenu`) being loaded before the form script runs.
- The browser URL check confirmed login/theme assets, but I did not execute import/export flows because that would create files and require deeper fixture setup.

## Review Opinion

The BOQ Header implementation is production-shaped and business-readable. The biggest improvement is centralization: one server-side transition helper and one total aggregation helper should be reused by the API and controller. The feature is ready to build on, provided tests cover state progression and total recomputation.

## Recommended Next Steps

1. Extract the status transition map into a shared server helper and expose allowed-next-status through API for the client.
2. Deduplicate the total aggregation SQL into a private method.
3. Add tests for Draft -> Pricing -> Frozen -> Locked, invalid backward jumps, locked metadata population, and item update/delete roll-ups.
4. Update export/import API responses to consistently throw or consistently return a documented result shape.
