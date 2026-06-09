# EV-026: WP2 Parser and Normalizer

Date: 2026-06-09

Task: `WP2.3`

## Implementation

Implemented BOQ Excel parser/normalizer preview support in:

```text
/home/mohamed/frappe-bench/apps/construction/construction/services/boq_import_service.py
```

Updated API wrapper:

```text
/home/mohamed/frappe-bench/apps/construction/construction/api/boq_api.py
```

Added parser smoke tests:

```text
/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_excel_parser.py
```

## Scope

This is preview/parser work only.

It does **not** create BOQ Structure or BOQ Item records.

Commit remains blocked until:

- `WP2.2B` traceability/import batch decision is complete.
- `WP2.6` Draft-only commit implementation is reached.

## Supported Preview Capabilities

- Reads Excel workbooks with `openpyxl`.
- Selects `BOQ`, `Bill of Quantities`, `جدول الكميات`, or `مقايسة` worksheet when present.
- Expands merged-cell top-left values during parsing.
- Auto-detects header row within first 20 rows.
- Recognizes English and Arabic header aliases.
- Detects import mode:
  - `Structured`
  - `Semi-Structured`
  - `Flat`
- Supports user-confirmed import mode input.
- Classifies rows as:
  - `Section`
  - `Item`
  - `Ambiguous`
  - `Ignored`
- Builds preview rows with:
  - `row_no`
  - `sheet_name`
  - `raw_values`
  - `normalized`
  - `detected_type`
  - `confidence`
  - `reason_codes`
  - `display_reason`
  - `proposed_parent`
  - `proposed_wbs_code`
  - `blocking`
- Generates default root preview for flat import:

```text
Imported BOQ Items / بنود مستوردة
```

- Blocks unresolved ambiguous rows.
- Blocks structured WBS collisions with existing BOQ Structures.
- Blocks `dry_run=False` with a clear message because commit is not implemented yet.

## Verification Commands

Parser smoke:

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Result summary:

- `structured`: success, mode `Structured`, 1 section, 1 item, 0 errors.
- `semi_structured`: success, mode `Semi-Structured`, 1 section, 2 items, generated preview WBS `01`, `01.001`, `01.002`.
- `flat`: success, mode `Flat`, generated default root plus items `01.001`, `01.002`, Arabic headers accepted.
- `ambiguous`: blocked with `ambiguous_row_unresolved`.
- `structured_collision`: blocked with `wbs_collision_existing_boq`.

Syntax check:

```bash
./env/bin/python -m py_compile apps/construction/construction/services/boq_import_service.py apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

## Review Conclusion

`WP2.3` is verified for parser/normalizer preview scope. Next work should continue to `WP2.4` dry-run validation using an in-memory parent tree; database commit remains out of scope.
