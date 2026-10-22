# EV-027: WP2 Dry-Run Parent Tree Validation

Date: 2026-06-09

Task: `WP2.4`

## Implementation

Enhanced preview-only BOQ Excel parser validation in:

```text
/home/mohamed/frappe-bench/apps/construction/construction/services/boq_import_service.py
```

Updated smoke coverage in:

```text
/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_excel_parser.py
```

## Scope

`WP2.4` validates parent WBS references during dry-run using an in-memory file tree plus existing BOQ Structure lookup.

No BOQ records are created.

## Rules Verified

Structured import parent WBS can resolve to:

- a Section row earlier in the uploaded workbook,
- or an existing BOQ Structure in the target BOQ Header.

Blocking errors are returned when:

- parent WBS is missing from both uploaded file and target BOQ,
- parent WBS refers to an Item row,
- parent WBS appears after the child row,
- parent WBS self-references the same row WBS.

## Verification Commands

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Verified result cases:

- `structured`: success; parent WBS `99` resolved from uploaded file.
- `parent_missing`: blocked with `parent_wbs_not_found`.
- `parent_is_item`: blocked with `parent_wbs_not_section`.
- `parent_after_child`: blocked with `parent_wbs_after_child`.
- Existing prior parser cases still pass:
  - `semi_structured`
  - `flat`
  - `ambiguous`
  - `structured_collision`

Syntax check:

```bash
./env/bin/python -m py_compile apps/construction/construction/services/boq_import_service.py apps/construction/construction/tests/test_boq_excel_parser.py
```

Result: passed.

## Review Conclusion

`WP2.4` is verified for dry-run parent WBS validation using the uploaded workbook as the primary in-memory parent tree. Commit remains out of scope.
