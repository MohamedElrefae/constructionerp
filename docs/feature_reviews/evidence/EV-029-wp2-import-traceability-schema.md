# EV-029: WP2 Import Traceability Schema

Date: 2026-06-09

Task: `WP2.2B`

## Implementation

Added a dedicated `BOQ Import Batch` DocType:

```text
/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_import_batch/
```

Added row-level import traceability fields to:

```text
/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.json
/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.json
```

## BOQ Import Batch

Purpose:

- target BOQ Header,
- project,
- import mode,
- source file,
- source sheet,
- preview/commit status,
- row/section/item/error/warning counts,
- JSON review payloads.

Autoname is controller-driven using:

```text
BOQIMP-YYYYMMDD-<8 hex chars>
```

Example verified:

```text
BOQIMP-20260609-492fd730
```

The suffix is generated with `secrets.token_hex(4)`.

## BOQ Structure Trace Fields

- `import_batch`
- `import_batch_id`
- `import_mode`
- `source_sheet_name`
- `source_row_no`
- `source_wbs_code`
- `wbs_generated_by_system`

## BOQ Item Trace Fields

- `import_batch`
- `import_batch_id`
- `import_mode`
- `source_sheet_name`
- `source_row_no`
- `source_item_ref`

## Verification

JSON validation:

```bash
./env/bin/python -m json.tool apps/construction/construction/construction/doctype/boq_structure/boq_structure.json
./env/bin/python -m json.tool apps/construction/construction/construction/doctype/boq_item/boq_item.json
./env/bin/python -m json.tool apps/construction/construction/construction/doctype/boq_import_batch/boq_import_batch.json
```

Python compile:

```bash
./env/bin/python -m py_compile apps/construction/construction/construction/doctype/boq_import_batch/boq_import_batch.py
```

Migration:

```bash
bench --site v16.localhost migrate
```

Database schema verification:

```sql
SHOW TABLES LIKE 'tabBOQ Import Batch';
SHOW COLUMNS FROM `tabBOQ Structure` WHERE Field IN (...trace fields...);
SHOW COLUMNS FROM `tabBOQ Item` WHERE Field IN (...trace fields...);
```

Results:

- `tabBOQ Import Batch` exists.
- all BOQ Structure trace columns exist.
- all BOQ Item trace columns exist.
- smoke insert created `BOQIMP-20260609-492fd730`.
- smoke record was deleted after verification.

## Review Conclusion

`WP2.2B` is verified. Commit import can now use a dedicated import batch record and row-level traceability fields.
