# EV-068 — BOQ Excel Import Scope Finish

Date: 2026-06-16

## Scope

Finish the BOQ Excel import scope by removing the contradictions between
implemented commit behavior and stale "preview-only" / placeholder
messaging, and by exposing the status and template endpoints that the
service code has always implied. Recorded against
`BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md` (revised 2026-06-16) and the
work packages WP2, WP3, WP4, WP5, WP7, WP8 from that plan.

## What Shipped

### WP2 — `get_import_status()` rewrite + whitelisted API

- Replaced the stale `BOQImportService.get_import_status()` body
  (`status: "preview-only"`, `"Commit import not implemented yet"`)
  with a real implementation that reads `BOQ Import Batch` and
  derives `committed_structure_count` and `committed_item_count`
  from `BOQ Structure` / `BOQ Item` rows where
  `import_batch = import_id`.
- Added `@frappe.whitelist() construction.api.boq_api.get_boq_import_status(import_id)`.
  The API enforces the same project-scope pattern as
  `get_boq_header_scope_context`: restricted users get
  `frappe.PermissionError` if the batch's BOQ Header project is not
  in their `get_user_scope_hierarchy().projects` set.
- Response shape: `success`, `status`, `import_id`, `boq_header`,
  `project`, `import_mode`, `source_file`, `source_file_name`,
  `sheet_name`, `row_count`, `section_count`, `item_count`,
  `ambiguous_count`, `error_count`, `warning_count`,
  `committed_structure_count`, `committed_item_count`, `errors`,
  `warnings`. Not-found returns
  `{"success": False, "status": "not_found", "import_id": ...,
  "error": "BOQ Import Batch was not found."}`.

### WP3 — Real template endpoint

- Replaced
  `BOQImportService.create_import_template()` (which returned the
  literal string `"Excel template creation to be implemented in WP2.8"`)
  with a real `openpyxl`-based generator. Uses the existing
  `TEMPLATE_COLUMNS` constant, adds header styling, freeze pane,
  `DataValidation` for the `Type` column (`Section`, `Item`,
  `Ignored`), and an `Instructions` sheet explaining the three import
  modes and the WBS / parent / item-value rules.
- Saves the workbook as a private `File` in
  `private/files/BOQ_Import_Template_YYYYMMDD_HHMMSS.xlsx` and
  returns `{"success": True, "file_url": ..., "file_name": ...}`.
- Added `@frappe.whitelist() construction.api.boq_api.create_boq_import_template()`.

### WP4 — Async block message

- Replaced
  `"This BOQ Excel import exceeds the synchronous row threshold and
  must use async import."` (the message in the commit-time
  `frappe.throw` at `boq_import_service.py`) with the
  product-approved copy:
  `"This file is too large for synchronous import. Large-file async
  import is not enabled in this release. Reduce the file size or
  split the BOQ into smaller workbooks."`.
- The `async_import_required` warning on the preview response
  (already present) is unchanged.

### WP5 — Preview flag enforcement

- Added `is_enabled("enable_boq_excel_import_preview")` checks at
  the top of `BOQImportService.import_from_excel`,
  `BOQImportService.generate_import_error_report`, and
  `BOQImportService.create_import_template`. All three return
  `{"success": False, "error": "BOQ Excel preview is disabled by
  Construction Settings."}` when the flag is off.
- The commit path is gated transitively because
  `import_from_excel` is its entry point; the existing
  `_commit_import` check on `enable_boq_excel_import_commit` still
  applies on top.
- Updated the field's help text in
  `construction_settings.json` to state the new runtime contract
  (gates preview / error report / template; required for the commit
  flag to be usable).

### WP7 — UI honesty

- Added `@frappe.whitelist() is_boq_excel_import_enabled()` returning
  `{"enabled", "preview_enabled", "commit_enabled"}`. Button is
  shown only when both flags are on.
- Updated `construction/construction/doctype/boq_header/boq_header.js`:
  - The "Import Excel" button is now wrapped in a `frappe.call` to
    the new helper. It appears only for Draft BOQs **and** when both
    flags are on.
  - Dialog title renamed to "Import BOQ from Excel (Preview)";
    primary button renamed to "Run Preview".
  - Added an inline field description explaining the dialog is
    preview-only and pointing users at the API for commit.
  - Replaced the silent `success` callback with explicit feedback:
    success alert shows error/warning counts; failure shows
    `msgprint` with the server error.
  - Added a "Download Excel Template" button that calls
    `create_boq_import_template` and opens the result in a new tab.
- No `?v=` cache-buster bump was needed because the file is
  registered via `doctype_js` (per-form, not cache-versioned).

### WP8 — Failed batch + `error_message` field

- Added `error_message` (Long Text) field to `BOQ Import Batch`
  DocType and migrated `v16.localhost`.
- Wrapped the structure/item insert loop in
  `BOQImportService._commit_import()` in `try/except`. On failure,
  the batch is set to `status="Failed"`,
  `error_message=str(exc)` is stored, and the exception is
  re-raised so the API caller still gets the error.
- The `BOQ Header ... for update` lock in
  `_validate_commit_wbs_uniqueness` runs before the batch is
  created, so a uniqueness failure still raises before any batch
  exists (no orphan batch for that case).

## Deferred

- Async queue, status polling, retry/cancel/resume.
- A preview-then-commit UI inside the BOQ Header form. The current
  dialog runs the preview API and surfaces a one-line alert; the
  full preview tree, row-resolution UI, mode picker, and commit
  button toggle remain as a follow-up.
- `get_boq_import_status` UI surface (the API is exposed and
  scope-safe, but no BOQ Header JS button calls it yet).

## Verification

15-check manual smoke:
`construction.tests.test_boq_import_status_smoke.run`

```bash
bench --site v16.localhost execute construction.tests.test_boq_import_status_smoke.run
```

Result: passed. Checks:

1. `get_import_status` returns `not_found` for missing batch.
2. `get_import_status` returns `not_found` for empty `import_id`.
3. `get_import_status` returns `Committed` with real batch metadata
   and `committed_structure_count` / `committed_item_count` > 0
   after a successful sync commit.
4. `get_import_status` returns `Preview` for a preview-only batch.
5. `get_import_status` returns `Failed` for a failed batch.
6. Async-sized file commit returns the new product-approved
   message.
7. Whitelisted `get_boq_import_status` API returns `not_found` for
   missing / empty ids.
8. A `Failed` batch persists `error_message` on save and the
   status endpoint reports the final state.
9. Whitelisted `create_boq_import_template` API returns success,
   produces a private file in `/private/files/`, the workbook
   contains `BOQ Import Template` and `Instructions` sheets, the
   header row matches `TEMPLATE_COLUMNS`, and the `File` record is
   private.
10. Preview flag off blocks:
    1. `import_from_excel(dry_run=True)` with the new error.
    2. `import_from_excel(dry_run=False)` (commit) with the same
       error.
    3. `generate_import_error_report` with the same error.
    4. `create_import_template` with the same error.
    5. `is_boq_excel_import_enabled` returns
       `enabled=False` when only the preview flag is off.
    6. `is_boq_excel_import_enabled` returns
       `enabled=False` when only the commit flag is off.
    7. `is_boq_excel_import_enabled` returns
       `enabled=True` when both flags are on.

Syntax check:

```bash
python3 -m py_compile \
  construction/services/boq_import_service.py \
  construction/api/boq_api.py \
  construction/tests/test_boq_import_status_smoke.py
```

Result: passed.

Migration:

```bash
bench --site v16.localhost migrate
```

Result: passed. New `BOQ Import Batch.error_message` field added;
help text on `enable_boq_excel_import_preview` updated.

Existing parser smoke (regression check):

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
```

Result: passed. Existing preview/parser behavior remained valid.

## Documentation Footnote

`EV-026-wp2-parser-normalizer.md` contains a sentence stating that
"Parser is preview-only; commit remains blocked by `WP2.2B` and
`WP2.6`." This was true when `EV-026` was written but is no longer
the current state. `EV-030-wp2-commit-import.md` already documents
that commit is implemented behind the flag, and `EV-068` is the
consolidated finish-phase evidence. The historical file is
preserved unchanged per the project policy of adding superseding
notes rather than rewriting history.

## Acceptance

`WP2.13 finish-scope = VER`. The BOQ Excel import ships preview +
synchronous commit behind the existing `Construction Settings`
feature flags. Async is explicitly deferred and large files are
blocked with a product-approved message. No service or API method
returns the stale "Commit import not implemented yet" /
"Excel template creation to be implemented in WP2.8" placeholder
text. The BOQ Header dialog is honest about being preview-only and
is hidden when the relevant flags are off.
