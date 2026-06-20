# Consultant Review Request — BOQ Excel Import Scope Finish

To: codex-ai consultant
From: Mohamed Elrefae
Date: 2026-06-16
Repo: `/home/mohamed/frappe-bench/apps/construction`
Branch: current local worktree (not yet committed)
Plan: `BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md` (revised 2026-06-16)
Evidence: `docs/feature_reviews/evidence/EV-068-wp2-finish-scope.md`

## What I'm Asking You to Review

Please review the BOQ Excel Import Scope Finish work for code quality,
correctness, and consultant-grade evidence. The plan, the code, and the
evidence are all in this repo.

The finish phase shipped six work packages (WP2, WP3, WP4, WP5, WP7,
WP8) that together remove the contradictions between implemented
commit behavior and stale preview-only / placeholder messaging, and
expose the status and template endpoints that the service code has
always implied.

## What Shipped

1. **WP2 — `get_import_status()` rewrite + whitelisted API**
   - `construction/services/boq_import_service.py:254-322` —
     replaced the stale "preview-only" stub with a real implementation
     that reads `BOQ Import Batch` and derives committed counts from
     `BOQ Structure` / `BOQ Item` rows.
   - `construction/api/boq_api.py` — added
     `@frappe.whitelist() get_boq_import_status(import_id)` with
     project-scope enforcement that mirrors
     `get_boq_header_scope_context`.

2. **WP3 — Real template endpoint**
   - `construction/services/boq_import_service.py:250-345` — replaced
     the placeholder string with a real `openpyxl`-based generator
     using the existing `TEMPLATE_COLUMNS`, plus data validation and
     an Instructions sheet. Saves as a private `File`.
   - `construction/api/boq_api.py` — added
     `@frappe.whitelist() create_boq_import_template()`.

3. **WP4 — Async block message**
   - `construction/services/boq_import_service.py:316-323` — replaced
     "must use async import" with the product-approved
     "This file is too large for synchronous import..." message.

4. **WP5 — Preview flag enforcement**
   - `construction/services/boq_import_service.py` — added
     `is_enabled("enable_boq_excel_import_preview")` checks at the
     top of `import_from_excel`, `generate_import_error_report`, and
     `create_import_template`.
   - `construction/construction/doctype/construction_settings/construction_settings.json`
     — updated help text on the flag.

5. **WP7 — UI honesty**
   - `construction/api/boq_api.py` — added
     `@frappe.whitelist() is_boq_excel_import_enabled()`.
   - `construction/construction/doctype/boq_header/boq_header.js` —
     wrapped the Import button in the helper, renamed the dialog to
     "Import BOQ from Excel (Preview)", added a description field,
     added a "Download Excel Template" button.

6. **WP8 — Failed batch + `error_message` field**
   - `construction/construction/doctype/boq_import_batch/boq_import_batch.json`
     — added `error_message` (Long Text) field.
   - `construction/services/boq_import_service.py` — wrapped the
     structure/item insert loop in `try/except`; on failure the
     batch is set to `Failed` with the error message and the
     exception is re-raised.

## What Was Deferred (per plan)

- Async queue, status polling, retry/cancel/resume.
- A full preview-then-commit UI inside the BOQ Header form (the
  current dialog runs the preview API and surfaces a one-line alert).
- `get_boq_import_status` UI surface.

## Verification

15-check manual smoke at
`construction/tests/test_boq_import_status_smoke.py`:

```bash
bench --site v16.localhost execute construction.tests.test_boq_import_status_smoke.run
```

Result: passed on `v16.localhost`. All 15 checks green, including
the preview-flag enforcement matrix and the failed-batch
`error_message` round-trip.

Syntax + migration + regression:

```bash
python3 -m py_compile \
  construction/services/boq_import_service.py \
  construction/api/boq_api.py \
  construction/tests/test_boq_import_status_smoke.py
# OK

node --check construction/construction/doctype/boq_header/boq_header.js
# OK

bench --site v16.localhost migrate
# OK (added error_message field; help text updated)

bench --site v16.localhost execute \
  construction.tests.test_boq_excel_parser.run_boq_excel_parser_smoke
# OK (regression)
```

## Specific Questions for You

1. **WP5 enforcement decision** — is enforcing
   `enable_boq_excel_import_preview` at runtime the right call, or
   should the flag have stayed informational? I picked enforcement
   because the field's promise (`EV-021`) and the existing
   `enable_boq_excel_import_commit` precedent both point that way,
   and the existing smokes bypass the flag by calling
   `parse_workbook` directly.

2. **WP8 boundary** — is wrapping just the structure/item insert
   loop in `try/except` sufficient, or should the batch
   `status="Preview" → "Committed"` transition also be wrapped
   (i.e. should a save failure on the batch itself be reflected as
   `Failed`)? I went with the narrower boundary because the
   `_validate_commit_wbs_uniqueness` `for update` lock runs before
   the batch is created, so uniqueness errors don't produce orphan
   batches; the remaining failure surface is the insert loop.

3. **WP7 button visibility** — I made
   `is_boq_excel_import_enabled` return
   `enabled = preview_enabled AND commit_enabled`. That means
   admins who only enable preview (e.g. for read-only QA) won't see
   the button at all, even though the preview API would still work.
   Is hiding the button the right call, or should the dialog
   surface be available whenever preview is on, and the commit
   failure surface itself be the gate?

4. **Scope-safety of `get_boq_import_status`** — I reused the
   `get_boq_header_scope_context` pattern. Is the project-scope
   check correct, or should I also enforce `BOQ Import Batch.read`
   permission separately? The current code throws
   `frappe.PermissionError` if the project is not in the user's
   scope, regardless of Frappe's role-based permission on the
   `BOQ Import Batch` DocType.

5. **Template data validation** — I added a `DataValidation` list
   for the `Type` column with values
   `Section,Item,Ignored`. The service's
   `_normalize_type` accepts a broader set
   (`section, group, header, قسم, مجموعة, بند رئيسي, item,
   measured item, بند, بند مقاس`). Should the template's data
   validation list be the broader set, or is restricting it to the
   three canonical values a deliberate UX improvement?

6. **Failed-batch rollback** — currently, if the structure/item
   insert loop fails partway, the batch is set to `Failed` and the
   exception is re-raised, but partial structures/items that were
   already inserted are not rolled back. The pre-existing
   `select ... for update` lock on the BOQ Header reduces the
   window for this, but a true atomic boundary would need a savepoint
   or an explicit rollback. Is the current "best-effort rollback
   by status flag" acceptable for this phase, or should I add a
   savepoint and explicit rollback of inserted structures/items
   on failure?

7. **`create_import_template` runtime cost** — it generates a new
   workbook on every call and saves a new `File` record. Is that
   acceptable, or should the template be generated once and cached
   as a singleton `File`? I picked "always fresh" for the MVP, but
   want a second opinion.

8. **Plan revision** — the plan was originally written from memory
   and missed four live-repo facts (`enable_boq_excel_import_preview`
   declared but not enforced, `get_import_status` / `create_import_template`
   not wired anywhere, BOQ Header JS preview-only in practice,
   `BOQ Import Batch` already has most fields). The 2026-06-16
   revision added a "Revision Notes" section at the top. Is the
   revised plan structure acceptable, or should the original plan
   have been deleted and replaced with a clean v2?

## Files Changed (Untracked or Modified in Current Worktree)

- `BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md` — untracked, revised plan.
- `construction/services/boq_import_service.py` — WP2, WP3, WP4, WP5,
  WP8.
- `construction/api/boq_api.py` — WP2, WP3, WP5, WP7.
- `construction/construction/doctype/boq_header/boq_header.js` — WP7.
- `construction/construction/doctype/boq_import_batch/boq_import_batch.json`
  — WP8 (`error_message` field).
- `construction/construction/doctype/construction_settings/construction_settings.json`
  — WP5 (help text).
- `construction/tests/test_boq_import_status_smoke.py` — new,
  15-check manual smoke.
- `docs/feature_reviews/evidence/EV-068-wp2-finish-scope.md` — new,
  finish-phase evidence.
- `docs/feature_reviews/evidence/evidence_log.md` — `EV-068` row.
- `docs/feature_reviews/evidence/EV-026-wp2-parser-normalizer.md`
  — superseding note appended.

## What I Want From You

1. A line-by-line read of the plan revision (especially the
   "Revision Notes" and "Recommended Release Scope" sections) and
   the six code changes above.
2. Direct answers to the eight specific questions.
3. A verdict on whether `EV-068` is sufficient to move
   `WP2 finish-scope` from `Pending` to `VER`, or what additional
   evidence you want before approving.
4. Any consultant-grade concerns I missed — security, performance,
   multi-tenant, edge cases.

Please reply in the same consultant-review style as `EV-023` and
`EV-024` (clear verdict, conditions if any, action items).

Thanks,
Mohamed
