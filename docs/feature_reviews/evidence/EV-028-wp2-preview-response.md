# EV-028: WP2 Preview Response Contract

Date: 2026-06-09

Task: `WP2.5`

## Implementation

Enhanced BOQ Excel dry-run preview response in:

```text
/home/mohamed/frappe-bench/apps/construction/construction/services/boq_import_service.py
```

The preview response now includes:

- summary counts,
- errors,
- warnings,
- proposed creates,
- preview rows,
- preview tree.

## Fixture

Saved fixture:

```text
/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/EV-028-wp2-preview-response-fixture.json
```

The fixture includes these cases:

- structured success,
- semi-structured success,
- flat success with default root,
- ambiguous row blocked,
- missing parent blocked,
- parent is item blocked,
- parent after child blocked,
- structured WBS collision blocked.

## Verification Commands

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke > apps/construction/docs/feature_reviews/evidence/EV-028-wp2-preview-response-fixture.json
```

```bash
./env/bin/python -m json.tool apps/construction/docs/feature_reviews/evidence/EV-028-wp2-preview-response-fixture.json
```

```bash
./env/bin/python -m py_compile apps/construction/construction/services/boq_import_service.py apps/construction/construction/tests/test_boq_excel_parser.py
```

Results:

- fixture JSON is valid,
- `proposed_creates`, `summary`, and `preview_tree` are present,
- syntax check passed.

## Review Conclusion

`WP2.5` is verified for the preview API response contract. This remains dry-run only; commit is still blocked by `WP2.2B` and `WP2.6`.
