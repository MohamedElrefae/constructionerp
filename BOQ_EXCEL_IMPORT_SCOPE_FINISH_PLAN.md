# BOQ Excel Import Scope Finish Plan

Date: 2026-06-16
Repo: `/home/mohamed/frappe-bench/apps/construction`
Phase: Finish BOQ Excel Import Scope
Audience: Software consultant / engineering review
Revision: 2026-06-16 (revised against live repo)

## Revision Notes (2026-06-16)

The original plan was written from memory and missed four facts that exist in
the current code:

1. **`enable_boq_excel_import_preview` is declared in
   `construction/services/feature_flags.py` and in `Construction Settings`
   DocType JSON, but it is never checked at runtime.** The original plan
   treats it as the gate for the preview API. The service currently runs
   preview and commit code paths with no preview-flag check at all. The
   finish scope must decide whether to enforce the preview flag now or
   remove it from the runtime contract.

2. **`get_import_status()` is not wired to any API endpoint, the BOQ
   Header JS, the error report API, or the import batch list view.** The
   plan should be honest about this. It is currently a dead public method
   on the service. Either expose it as `@frappe.whitelist()` in
   `construction/api/boq_api.py` (and add a UI surface) or remove it.

3. **`create_import_template()` is also not wired anywhere.** No API
   method exists, no UI button exists, no test calls it. It is also a dead
   public method on the service.

4. **The current BOQ Header JS dialog is much simpler than the plan
   implies.** It only collects a file URL and posts to
   `import_boq_excel` with `dry_run=1` (the default). There is no preview
   step in the UI, no row resolution UI, no mode confirmation UI, and no
   commit button toggle. The plan must reflect this and decide whether
   the UI should be brought up to the preview-first contract or whether
   the current "import = preview-only in practice" UI is acceptable for
   this phase.

5. **`BOQ Import Batch` already has the fields the original plan
   recommended adding.** `boq_header`, `project` (fetched), `status`
   (`Preview` / `Committed` / `Failed` / `Cancelled`), `import_mode`,
   `source_file`, `source_file_name`, `sheet_name`, count fields, and
   the JSON review payloads. There is no need to add
   `started_at` / `finished_at` / `error_message` to the DocType for
   this phase. Failed-batch preservation is a code concern, not a schema
   concern, since `status="Failed"` is already a valid value.

6. **`is_enabled()` on unknown flags throws.** The preview flag must be
   either enforced or removed from the `IMPROVE_NOW_FLAGS` set before
   `get_import_status()` or any new API starts consulting it; otherwise
   preview code paths that fall back to `is_enabled` will start
   throwing for users who already use the flag today.

7. **Async block message is already user-facing.** The current message
   is `"This BOQ Excel import exceeds the synchronous row threshold and
   must use async import."` The plan's suggested improvement
   (`"This file is too large for synchronous import..."`) is good and
   should be applied as a small copy-only change.

8. **The "stale evidence" the original plan called out is
   `EV-026-wp2-parser-normalizer.md` and the
   `evidence_log.md` "Pending" row for it.** `EV-030-wp2-commit-import.md`
   already documents that commit is implemented behind the flag, so the
   "commit not implemented" story in `EV-026` was a snapshot in time,
   not the current truth. The finish phase should add a superseding
   evidence entry, not rewrite history.

## Executive Summary

The BOQ Excel import module is close to a shippable state, but the current
code contains contradictory product signals:

- A real synchronous commit path exists and is covered by smoke tests
  (`run_boq_excel_commit_smoke`,
  `run_boq_excel_duplicate_import_smoke`).
- `get_import_status()` still returns `preview-only` and
  `"Commit import not implemented yet"`. It is not wired to any API or
  UI surface.
- `create_import_template()` still returns a placeholder string. It is
  not wired to any API or UI surface.
- Async-sized imports are detected and blocked, but no async queue/status
  implementation exists.
- `enable_boq_excel_import_preview` is declared but not enforced.
- The BOQ Header JS dialog calls `import_boq_excel` with
  `dry_run=True` only and does not surface a commit action.

The recommended release scope for this phase is:

> Ship **BOQ Excel preview + synchronous commit for small files** behind
> the `enable_boq_excel_import_commit` feature flag. Explicitly block
> async-sized imports with the new product-approved message. Rewrite or
> remove `get_import_status()` and `create_import_template()`. Decide
> whether to enforce `enable_boq_excel_import_preview` at runtime or
> drop the runtime promise. Keep the current preview-only BOQ Header
> dialog behavior for this phase and document the gap.

This plan avoids pretending async import exists, removes stale
preview-only messaging from the surface that is actually shipped,
keeps the already-tested synchronous commit path, and does not invent
UI that the JS does not have.

## Current State (Verified Against Live Repo)

### Implemented (verified)

`construction/services/boq_import_service.py` supports:

- Excel file parsing (openpyxl, merged-cell aware).
- Header detection by anchor scoring in the first 20 rows.
- Structured, Semi-Structured, and Flat import modes.
- Row classification into Section, Item, Ambiguous, Ignored.
- Adjacent-duplicate warning.
- Parent WBS tree validation (self-reference, parent-after-child,
  parent-not-section, parent-not-found, existing-not-section).
- Proposed WBS code generation (Flat root injection, Semi-Structured
  auto-numbering, Structured passthrough).
- `BOQ Structure.flags.ignore_wbs_generation = True` during insert to
  prevent the WBS hook from overriding imported codes.
- `wbs_generated_by_system` flagging for Flat / Semi-Structured.
- `source_row_no`, `source_sheet_name`, `source_wbs_code`,
  `source_item_ref` traceability on both Structure and Item.
- `import_batch` and `import_mode` on Structure and Item.
- Feature-flagged synchronous commit through `_commit_import()`.
- Draft-only commit guard (`BOQ Header.status == "Draft"`).
- Duplicate WBS protection:
  - file-level duplicate (parsed_rows loop)
  - target-Draft collision (final `_validate_commit_wbs_uniqueness`
    with `select ... for update` on the BOQ Header)
  - stale-preview collision (same final guard, raised after a manual
    insert between preview and commit; covered by
    `run_boq_excel_duplicate_import_smoke`).
- Ambiguous-row blocking and row-resolution handling.
- Preview response with `summary`, `errors`, `warnings`,
  `import_policy`, `proposed_creates`, `preview_rows`, `preview_tree`.
- Error report generation through `generate_import_error_report()`
  with private `File` storage and a two-sheet workbook (`Import Review`
  + `Summary`).
- Import traceability through `BOQ Import Batch` (autoname
  `BOQIMP-YYYYMMDD-xxxxxxxx`).
- WBS health check after commit.
- File-size hard limit (25 MB) and row-count hard limit (10,000) with
  distinct error codes.
- Async threshold (2,000 rows) with `requires_async=True`,
  `async_import_required` warning, and a hard commit block.

### Contradictions / Gaps (verified)

| Area | Current Behavior | Problem | Wired? |
| --- | --- | --- | --- |
| Commit status | `_commit_import()` creates BOQ records | `get_import_status()` says preview-only and commit not implemented | Service method exists, **not** called by any API or UI |
| Template | `TEMPLATE_COLUMNS` exists | `create_import_template()` returns placeholder text | Service method exists, **not** called by any API or UI |
| Async policy | Parser marks `requires_async=True` above threshold; commit throws "must use async import" | No queue/status/worker implementation exists | Throw is in service, message is user-facing |
| Preview flag | `enable_boq_excel_import_preview` exists in settings and feature_flags | Never checked at runtime; preview always runs | Flag declared, **not** enforced |
| API contract | `import_boq_excel()` supports `dry_run=False` | No `get_boq_import_status` or `create_boq_import_template` API exists | Only `import_boq_excel` and `generate_boq_import_error_report` are whitelisted |
| UI contract | BOQ Header JS dialog calls `import_boq_excel` with `dry_run=True` only | No preview step, no mode confirmation, no commit button toggle, no template button | Dialog is a single Attach field + Import button |
| Tests | Commit, duplicate, error report, policy, file/row limits are covered as smoke functions | No tests for `get_import_status` or `create_import_template` (no callers exist) | Smoke functions exist for the wired paths |

## Current Code Evidence

### Commit Path Exists (verified, `boq_import_service.py:288-377`)

`BOQImportService.import_from_excel(..., dry_run=False)` calls
`_commit_import()`.

`_commit_import()`:

- Requires `enable_boq_excel_import_commit`
  (`feature_flags.is_enabled`, line 298).
- Requires `confirmed_import_mode` and validates it is in
  `IMPORT_MODES` (lines 301-305).
- Requires target BOQ Header exists (line 307).
- Requires BOQ Header status is `Draft` (lines 310-312).
- Blocks previews with errors (lines 314-315).
- Blocks previews that require async (lines 316-319).
- Requires proposed structures (line 322-324).
- Validates proposed WBS uniqueness in a `select ... for update`
  transaction boundary on the BOQ Header (lines 326, 380-414).
- Creates a `BOQ Import Batch` with status `Preview` (lines 329-336,
  631-662).
- Inserts `BOQ Structure` rows with `ignore_wbs_generation` flag and
  full traceability (lines 343-355, 664-698).
- Updates linked `BOQ Item` rows with quantity, unit, factor,
  contract_unit_price, owner fields, and traceability
  (lines 357-361, 700-724).
- Sets batch status to `Committed` (line 363).
- Runs WBS health check (line 365).

### Status Endpoint Is Stale And Unwired (verified)

Current `get_import_status(import_id)` at lines 254-260:

```python
return {
    "status": "preview-only",
    "import_id": import_id,
    "message": "Commit import not implemented yet",
}
```

This is no longer true for small synchronous imports. It is also
**not called by any whitelisted API method or UI**, so its staleness is
not user-visible today but is misleading to future agents and
contributors who search the code.

### Template Endpoint Is Placeholder And Unwired (verified)

Current `create_import_template()` at lines 250-252:

```python
return "Excel template creation to be implemented in WP2.8"
```

Also **not called by any whitelisted API method or UI**.

### Async Imports Are Not Implemented (verified)

The parser sets
`policy["requires_async"] = data_row_count > ASYNC_IMPORT_ROW_THRESHOLD`
at line 443. Synchronous commit then throws the user-facing message at
lines 316-319:

```text
This BOQ Excel import exceeds the synchronous row threshold and must use async import.
```

That message is acceptable for the blocked case but should be
rephrased per the "Suggested improvement" block in the original plan.

### Preview Flag Is Declared But Not Enforced (verified)

`IMPROVE_NOW_FLAGS` in `construction/services/feature_flags.py:3-13`
includes `enable_boq_excel_import_preview`, but the only runtime
check is on `enable_boq_excel_import_commit` at
`boq_import_service.py:298`. The preview code path runs unconditionally
today. The Construction Settings DocType already exposes the field
(`construction_settings.json:103`).

This means the service contract already violates the flag's
"preview / dry run" promise defined in
`docs/feature_reviews/evidence/EV-021-boq-excel-template-spec.md:19`.
The finish phase must either:

- Enforce `enable_boq_excel_import_preview` at the top of
  `import_from_excel()` and `generate_import_error_report()`, **or**
- Document that the flag is informational and remove the runtime
  promise.

### BOQ Header JS Is Preview-Only In Practice (verified)

`construction/construction/doctype/boq_header/boq_header.js:468-507`
defines the "Import Excel" button. It:

- Opens a dialog with a single `Attach` field (`file_url`).
- Calls `frappe.call` to
  `construction.api.boq_api.import_boq_excel` with
  `boq_header=frm.doc.name` and `file_url=values.file_url`.
- Does **not** pass `dry_run=0`, so the service runs in preview-only
  mode by default.
- Does **not** show the preview tree, errors, warnings, or proposed
  creates.
- Does **not** ask for `confirmed_import_mode`.
- Does **not** show a "Commit" button or surface a `BOQ Import Batch`
  ID back to the user.
- Reloads the form on `r.message.success` and shows
  "Import successful" alert.

For a Draft BOQ with no records, this means the user attaches a file,
sees a green alert, and the form re-loads with no visible change. This
is the actual shipped UX today and the plan must be honest about it.

## Recommended Release Scope

### Chosen Scope: Preview + Small Synchronous Commit, Honest UI

Ship now:

1. Dry-run preview and validation (already implemented).
2. Error report generation (already implemented).
3. Synchronous commit for files below the async threshold (already
   implemented).
4. Feature flag enforcement through
   `enable_boq_excel_import_commit` (already implemented).
5. Clear, product-approved block for async-sized files (small copy
   change to the throw message).
6. Replace `get_import_status()` with a real implementation that
   reads from `BOQ Import Batch`, **and** expose it through a
   whitelisted API method.
7. Either implement `create_import_template()` with `openpyxl` and
   expose it, or remove the public method.
8. Decide and document the `enable_boq_excel_import_preview` runtime
   behavior.
9. Add tests for the new status endpoint and the template endpoint
   (or for the explicit "not available" response if the alternative
   path is taken).
10. Keep the current BOQ Header JS dialog as the supported UI for this
    phase. Do not invent a preview/confirmation/commit UI in this
    phase; record the gap as a known follow-up.

Defer:

1. Async queue job.
2. Background worker progress tracking.
3. Async retry/cancel/resume.
4. Upload-session persistence for large files.
5. A preview-then-commit UI inside the BOQ Header form.
6. A "Download template" button in the BOQ Header dialog.

## Alternatives Considered

### Alternative A: Preview-Only

Pros:

- Lowest risk.
- Avoids commit-side data mutation.

Cons:

- Regresses already-implemented and verified commit work
  (`EV-030-wp2-commit-import.md`,
  `EV-031-wp2-duplicate-import-protection.md`).
- Conflicts with the evidence log row for `EV-030`, which already says
  commit is implemented and verified.
- Leaves `BOQ Import Batch` commit traceability underused.

Recommendation: Do not choose this unless management wants to delay
all import mutation.

### Alternative B: Full Sync + Async Import

Pros:

- Complete long-term UX.
- Large files can be imported in background.

Cons:

- Requires queue design, status polling, failure recovery,
  idempotency, and cancellation behavior.
- Higher risk than needed for current phase.

Recommendation: Defer async to a later dedicated phase.

### Alternative C: Small Sync Commit Now, Async Deferred (chosen)

Pros:

- Matches current implementation.
- Keeps large imports safe.
- Removes stale messaging from the parts of the API we actually
  ship.
- Can be verified quickly with existing smoke patterns.

Cons:

- Large imports remain blocked until async phase.
- BOQ Header UI is still preview-only; users must use the API or a
  future UI change to actually commit.

Recommendation: Adopt this scope, and explicitly accept the BOQ
Header UI gap as a follow-up rather than expanding the phase.

## Target Product Behavior

### Preview

Input:

- Excel file URL/path.
- BOQ Header.
- Optional `confirmed_import_mode`.
- Optional `row_resolutions`.

Output (unchanged):

- `success`
- `dry_run=True`
- detected and confirmed mode fields
- errors/warnings
- preview rows/tree
- proposed creates
- import policy

No database mutation except optional logs/file reads.

### Commit

Allowed only when:

- `enable_boq_excel_import_commit = 1`
- `dry_run=False`
- target BOQ Header exists
- target BOQ Header status is `Draft`
- `confirmed_import_mode` is supplied
- preview has no blocking errors
- import policy does not require async
- proposed WBS codes do not collide with the current Draft BOQ

Output (unchanged):

- `success=True`
- `dry_run=False`
- `boq_header`
- `import_batch`
- `confirmed_import_mode`
- `summary`
- `created_structures`
- `created_items`
- `health`

### Async-Sized Files

For this phase:

- Preview may still succeed.
- Preview must include `import_policy.requires_async=True`.
- Warnings must include `async_import_required`.
- Commit must return a clear failure with the new message:

  ```text
  This file is too large for synchronous import. Large-file async import is not enabled in this release. Reduce the file size or split the BOQ into smaller workbooks.
  ```

  Apply this to the `frappe.throw` at
  `boq_import_service.py:316-319`.

### Import Status (new)

Replace the body of `get_import_status(import_id)` so it returns the
real `BOQ Import Batch` state. The recommended response shape is the
one in the original plan, with one adjustment: include
`committed_structure_count` and `committed_item_count` only if a
follow-up commit run adds those fields. For this phase, derive
`created_structures` and `created_items` from the imported
`BOQ Structure` and `BOQ Item` rows where `import_batch = import_id`,
which already works.

If the batch is not found, return:

```python
{
    "success": False,
    "status": "not_found",
    "import_id": import_id,
    "error": "BOQ Import Batch was not found.",
}
```

Expose this through a new whitelisted method
`construction.api.boq_api.get_boq_import_status(import_id)`.

### Template Endpoint (new)

Pick exactly one of the two paths below. Do not ship placeholder text
in either case.

#### Preferred: Implement `create_import_template()`

Generate an `.xlsx` workbook with `openpyxl` using the same
`TEMPLATE_COLUMNS` already defined on the service. The workbook
should include a header row, a freeze pane on row 1, data validation
for the `Type` column (`Section`, `Item`, `Ignored`), and an
`Instructions` sheet that explains the three modes. Save as a
private `File` and return:

```python
{
    "success": True,
    "file_url": "...",
    "file_name": "BOQ_Import_Template.xlsx",
}
```

Expose through
`construction.api.boq_api.create_boq_import_template()`. Optionally
gate on the existing `enable_boq_excel_import_preview` flag for
consistency.

#### Alternative: Remove `create_import_template()`

If template implementation is deferred:

- Delete the `create_import_template` method on the service.
- Do not expose any template API.
- Do not add a template button to the BOQ Header UI.

The original plan's "hide/disable" option is rejected because there
is currently no caller, so "hide" is moot. Removal is the cleaner
choice.

### `enable_boq_excel_import_preview` Decision (new)

Pick exactly one:

- **Enforce** at the top of `import_from_excel()` and
  `generate_import_error_report()`. Throw the same
  "BOQ Excel preview is disabled by Construction Settings." copy as
  the commit flag.
- **Document as informational** in the Construction Settings field
  help text and do not enforce at runtime.

The original plan is silent on this. The recommended default is
**enforce**, because the field exists, the user-facing spec
(`EV-021`) calls it the preview gate, and the field help text in
`construction_settings.json` should be aligned with the runtime
behavior. If a release manager wants to keep the current "always
preview" behavior, document it explicitly in
`construction_settings.json` help text and in the evidence log.

## Required Work Packages

### WP1: Freeze Release Scope

Decision:

> Release preview + synchronous commit for small files. Defer async
> commit. Replace `get_import_status()` and either implement or
> remove `create_import_template()`. Decide and apply
> `enable_boq_excel_import_preview` enforcement. Keep the BOQ
> Header JS dialog as the supported UI; record the UI gap as a
> follow-up.

Actions:

1. Record the decision in this plan (revised section above).
2. Update stale docs that still say commit is not implemented:
   - Add a superseding note to
     `docs/feature_reviews/evidence/EV-026-wp2-parser-normalizer.md`
     stating that commit is implemented behind the flag (see
     `EV-030`).
   - Add a row to `docs/feature_reviews/evidence/evidence_log.md`
     summarizing the WP2 finish phase.
3. Confirm threshold values stay at:
   - `ASYNC_IMPORT_ROW_THRESHOLD = 2000`
   - `MAX_IMPORT_ROW_COUNT = 10000`
   - `MAX_IMPORT_FILE_SIZE_BYTES = 25 * 1024 * 1024`

Acceptance:

- Team agrees the BOQ Header JS gap is a known follow-up, not part
  of this phase.

### WP2: Replace `get_import_status()` And Expose It

Current method at `boq_import_service.py:254-260` is stale. It must
be rewritten, and a whitelisted API must be added.

Recommended service behavior:

1. Look up `BOQ Import Batch` by `name = import_id`.
2. If not found, return the `not_found` shape above.
3. If found, derive counts from the batch's JSON review payloads
   and from `BOQ Structure` / `BOQ Item` rows where
   `import_batch = import_id`.
4. Return a dict matching the "Status Response" block in the
   original plan.

API exposure:

1. Add `get_boq_import_status(import_id)` to
   `construction/api/boq_api.py` with `@frappe.whitelist()`.
2. Read from the service, return the dict directly.
3. Wrap the call with the same `try/except` shape used by the
   other import endpoints, returning
   `{"success": False, "error": "..."}` on failure.
4. Do not add this endpoint to the BOQ Header JS in this phase;
   it is server-side only until the UI gap is closed.

Acceptance:

- No service method or API method returns
  `"Commit import not implemented yet"`.
- Status reflects the real `BOQ Import Batch.status` value.
- Tests cover committed batch, preview batch, and not-found.

### WP3: Implement Or Remove `create_import_template()`

Pick one path. Default: implement.

If implementing:

1. Replace the body of `create_import_template()` at
   `boq_import_service.py:250-252` with an `openpyxl` workbook
   generation that uses the existing `TEMPLATE_COLUMNS` constant.
2. Save as a private `File` in `private/files/`, mirroring the
   `_write_import_error_report` pattern at
   `boq_import_service.py:468-620`.
3. Return the `success` / `file_url` / `file_name` shape from the
   original plan.
4. Add `create_boq_import_template()` to
   `construction/api/boq_api.py` with `@frappe.whitelist()` and
   the standard try/except wrapper.
5. Optionally enforce `enable_boq_excel_import_preview` here too.

If removing:

1. Delete the `create_import_template` method on the service.
2. Confirm no API method, no test, and no JS file references it
   (current grep confirms there are no callers).

Acceptance:

- No method returns the placeholder text.
- Either the template is a real downloadable file or the method
  does not exist.

### WP4: Tighten Async Block Message

Single copy change in `boq_import_service.py:316-319`. Replace the
current `frappe.throw` message with:

> This file is too large for synchronous import. Large-file async
> import is not enabled in this release. Reduce the file size or
> split the BOQ into smaller workbooks.

The error code stays the same. The `async_import_required` warning
on the preview response already includes the threshold count, so
users will see both the warning and the new commit-time message.

Acceptance:

- The new message is what `run_boq_excel_import_policy_smoke` and
  any new tests assert on.

### WP5: Decide `enable_boq_excel_import_preview` Enforcement

Pick one path. Default: enforce.

If enforcing:

1. Add `is_enabled("enable_boq_excel_import_preview")` checks at
   the top of `import_from_excel()` and
   `generate_import_error_report()`.
2. Throw the same "disabled by Construction Settings" copy used
   by commit.
3. The commit path inherits the preview check because
   `import_from_excel` is the entry point; no separate check is
   needed.
4. Update the smoke tests that currently call
   `parse_workbook` directly (which bypasses the flag check) so
   the smoke tests still pass: either set the flag during the
   test, or call `parse_workbook` directly and keep the service
   entry point as the only gated surface.

If documenting as informational:

1. Update the `help` text on the field in
   `construction_settings.json` to state "informational; preview
   always runs".
2. Add a note in the evidence log entry.

Acceptance:

- The flag's runtime contract is consistent with the help text
  and the EV-021 spec.

### WP6: API Contract Review

Required review of `construction/api/boq_api.py`:

1. Confirm `dry_run` is parsed consistently as boolean at
   `boq_api.py:218-234` (currently `frappe.utils.cint(dry_run)`,
   which is correct for the way the JS sends it).
2. Confirm `row_resolutions` parsing handles invalid JSON
   gracefully at `boq_api.py:228`. The current code passes the
   parsed result directly; a malformed string would raise
   `frappe.parse_json` failure inside the service. Add a
   `try/except` around `frappe.parse_json` and treat parse failure
   as `row_resolutions=None` to keep the contract stable.
3. Confirm the error shape is stable:
   `{"success": False, "error": "..."}`.
4. Add the two whitelisted methods decided in WP2 and WP3.

Acceptance:

- API methods expose the actual release scope.
- No API endpoint implies async import exists.

### WP7: BOQ Header UI Review

Required review of
`construction/construction/doctype/boq_header/boq_header.js:468-507`:

1. Document the current behavior in the docstring or a comment:
   "This dialog triggers a preview-only import. To commit, use the
   whitelisted API with `dry_run=0` and a confirmed import mode, or
   use the future preview-then-commit UI (tracked as a follow-up)."
2. Do not expand the dialog into a preview-then-commit flow in this
   phase. The work required (rendering the preview tree, the
   row-resolution UI, the import-mode picker, the commit button
   toggle, the result surface with batch ID and WBS health) is
   substantial and is out of scope for "finish the existing scope."
3. Confirm the dialog only appears for `frm.doc.status === "Draft"`
   (already correct at line 468).
4. Confirm the dialog greys out or hides when
   `enable_boq_excel_import_commit` is off, by adding a
   `frappe.call` to `is_variation_orders_enabled`-style helper, or
   by a new helper `is_boq_excel_import_commit_enabled()`. If
   enforcement is added in WP5, this is a small UX nicety; if
   enforcement is not added, this is a required guard.

Acceptance:

- The dialog matches what the service actually does (preview
  only) or is replaced with a documented "API only" message.
- The UI does not promise async import.

### WP8: Status Field Hygiene

The `BOQ Import Batch.status` field already has the values
`Preview`, `Committed`, `Failed`, `Cancelled`. The current commit
path sets `Preview` at insert and `Committed` at the end. There is
no current path that sets `Failed` or `Cancelled`.

For this phase:

1. Wrap the body of `_commit_import()` after batch creation in a
   `try/except` that, on failure, sets the batch to `Failed` and
   stores the error message in a new `error_message` field.
2. Add the `error_message` field to `boq_import_batch.json` (Data
   field, long enough for a sentence). Do not add `started_at` or
   `finished_at` for this phase; `creation` and `modified` are
   sufficient.
3. The duplicate-import and stale-preview blocks already throw
   before the batch is inserted, so they do not need to set
   `Failed`. Only commit-mutation failures need this treatment.

Acceptance:

- A successfully committed import ends in `Committed`.
- An import whose batch was created but whose commit mutation
  failed ends in `Failed` with a non-empty `error_message`.
- The status endpoint reports the final state.

### WP9: Stale Evidence Documentation

1. Add a new evidence file
   `docs/feature_reviews/evidence/EV-068-wp2-finish-scope.md` that
   summarizes:
   - what is shipping (preview + small sync commit),
   - what is deferred (async),
   - the BOQ Header UI gap,
   - the `enable_boq_excel_import_preview` decision.
2. Add a row to `docs/feature_reviews/evidence/evidence_log.md`
   referencing `EV-068`.
3. Do not rewrite `EV-026`; instead add a "Superseded by EV-068"
   footnote at the bottom. The current `EV-030`,
   `EV-031`, `EV-032`, and `EV-033` already describe the commit,
   duplicate, error-report, and threshold behaviors correctly.

Acceptance:

- The current docs do not contradict the current release behavior.

### WP10: Test Coverage

Existing smoke coverage already includes:

- `run_boq_excel_parser_smoke` (preview classification cases).
- `run_boq_excel_commit_smoke` (successful sync commit, flag block).
- `run_boq_excel_duplicate_import_smoke` (duplicate file, stale
  preview).
- `run_boq_excel_error_report_smoke` (error report file,
  private File record).
- `run_boq_excel_import_policy_smoke` (async block, row limit,
  file size limit).
- `TestBOQExcelParser` (unittest cases for Flat root generation
  and Structured parent passthrough).

Required additional tests:

1. `run_boq_excel_status_smoke`:
   - committed batch returns the right status fields,
   - preview batch returns `Preview`,
   - not-found returns the `not_found` shape,
   - permission is enforced (call as a restricted user, expect
     PermissionError or the equivalent JSON error).
2. `run_boq_excel_template_smoke` if implementing:
   - file exists at the returned path,
   - workbook opens,
   - expected columns are present in the header row,
   - `Type` column has data validation,
   - `File` record is private.
3. API contract tests for the new status and template endpoints
   (call directly through `@frappe.whitelist` API).
4. UI smoke/manual test:
   - preview only via the BOQ Header dialog (current behavior is
     acceptable; just record it).

Recommended commands:

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_preview_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_commit_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_duplicate_import_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_error_report_smoke
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_excel_import_policy_smoke
```

Plus syntax/lint:

```bash
python3 -m py_compile construction/services/boq_import_service.py construction/api/boq_api.py
```

Plus Frappe runner (per the
`EV-048-wp4-final-qa-rollup.md` "formal runner remains blocked"
caveat, this may not work in this environment).

## Proposed API Response Contracts

### Preview Response (unchanged)

```json
{
  "success": true,
  "dry_run": true,
  "boq_header": "BOQ-...",
  "sheet_name": "Sheet1",
  "detected_import_mode": "Flat",
  "confirmed_import_mode": null,
  "allowed_import_modes": ["Structured", "Semi-Structured", "Flat"],
  "requires_user_confirmation": true,
  "summary": {},
  "errors": [],
  "warnings": [],
  "import_policy": {
    "requires_async": false,
    "data_row_count": 100
  },
  "proposed_creates": {},
  "preview_rows": [],
  "preview_tree": []
}
```

### Commit Response (unchanged)

```json
{
  "success": true,
  "dry_run": false,
  "boq_header": "BOQ-...",
  "import_batch": "BOQIMP-...",
  "confirmed_import_mode": "Flat",
  "summary": {},
  "created_structures": [],
  "created_items": [],
  "health": {}
}
```

### Async Block Response (changed message)

```json
{
  "success": false,
  "dry_run": false,
  "error": "This file is too large for synchronous import. Large-file async import is not enabled in this release. Reduce the file size or split the BOQ into smaller workbooks."
}
```

### Status Response (new)

```json
{
  "success": true,
  "status": "Committed",
  "import_id": "BOQIMP-...",
  "boq_header": "BOQ-...",
  "import_mode": "Flat",
  "row_count": 100,
  "section_count": 1,
  "item_count": 100,
  "ambiguous_count": 0,
  "error_count": 0,
  "warning_count": 0,
  "committed_structure_count": 3,
  "committed_item_count": 2
}
```

`committed_structure_count` and `committed_item_count` are derived
from `frappe.db.count("BOQ Structure", {"import_batch": import_id})`
and the equivalent for `BOQ Item`. They are only present when the
batch exists and the count query succeeds.

### Template Response (new, if implementing)

```json
{
  "success": true,
  "file_url": "/private/files/BOQ_Import_Template.xlsx",
  "file_name": "BOQ_Import_Template.xlsx"
}
```

## Data Integrity Requirements

Commit must preserve:

1. Draft-only mutation.
2. BOQ Header lock against concurrent imports
   (`select ... for update` on the BOQ Header row, already in
   `_validate_commit_wbs_uniqueness`).
3. Unique WBS enforcement.
4. No duplicate WBS from stale previews.
5. Correct parent-child WBS tree.
6. Correct item values:
   - quantity
   - unit
   - contract unit price
   - factor
   - line total (computed by the Item controller)
7. Traceability fields on BOQ Structure/BOQ Item:
   - import batch
   - import mode
   - source row no
   - source WBS code
   - generated WBS flag
   - source item ref
8. WBS health check after commit.

## Security / Permission Requirements

1. Import commit remains feature-flagged.
2. Commit should use server-side checks, not only UI checks.
3. Generated templates/error reports should be private files.
4. The new `get_boq_import_status` API must not leak batches
   outside permitted BOQ scope. Reuse the project-scope check
   pattern from `get_boq_header_scope_context` at
   `boq_api.py:540-575`:
   - Resolve the BOQ Header from the batch.
   - Check the header's `project` is in the caller's
     `get_user_scope_hierarchy` `projects` set.
   - Throw `frappe.PermissionError` otherwise.
5. Restricted users must not get generic Project/Company/Cost
   Center access through import APIs.

## Consultant Review Questions

1. Is the recommended scope acceptable: small synchronous commit
   now, async deferred?
2. Should the BOQ Header UI stay preview-only for this phase, or
   should the preview-then-commit UI be pulled into this phase?
3. Should `create_import_template()` be implemented in this phase
   or removed entirely?
4. Should `enable_boq_excel_import_preview` be enforced at runtime
   or kept as an informational flag?
5. Are current thresholds acceptable?
   - 2,000 rows async threshold
   - 10,000 max rows
   - 25 MB max file size
6. Is the new `error_message` field on `BOQ Import Batch`
   acceptable for marking failed imports, or should the failure
   state be encoded differently (e.g. in the existing
   `errors_json`)?
7. Should historical evidence docs be updated, or should we add
   only a superseding implementation note (`EV-068`)?
8. Should `get_boq_import_status` enforce project scope, or should
   it rely on the default Frappe `read` permission for
   `BOQ Import Batch`?

## Recommended Implementation Order

1. Freeze release scope (this plan).
2. Update async block message in
   `boq_import_service.py:316-319` (small, safe, immediate
   win).
3. Rewrite `get_import_status()` in `boq_import_service.py`.
4. Implement or remove `create_import_template()` in
   `boq_import_service.py`.
5. Decide and apply `enable_boq_excel_import_preview` runtime
   behavior.
6. Add `get_boq_import_status` (and optionally
   `create_boq_import_template`) to
   `construction/api/boq_api.py`.
7. Add `error_message` field to `BOQ Import Batch` and wrap
   `_commit_import` mutation in try/except that sets
   `status="Failed"`.
8. Update BOQ Header JS to be honest about preview-only behavior
   and to hide the dialog when the commit flag is off.
9. Add `EV-068` evidence file and log row.
10. Add `run_boq_excel_status_smoke` and (if implemented)
    `run_boq_excel_template_smoke` tests.
11. Run the full existing BOQ import smoke suite.
12. Write final implementation report.

## Definition of Done

This phase is complete when:

1. No service or API method returns
   `"Commit import not implemented yet"`.
2. `get_import_status()` returns real status from
   `BOQ Import Batch` and is exposed through a whitelisted API.
3. `create_import_template()` is either implemented and exposed,
   or removed.
4. Async-sized files are blocked with the new product-approved
   message.
5. `enable_boq_excel_import_preview` is either enforced at runtime
   or explicitly documented as informational in
   `construction_settings.json` help text.
6. Small synchronous commit remains feature-flagged and tested.
7. Duplicate/stale WBS protections remain tested.
8. Error report generation remains tested.
9. Failed imports create a `BOQ Import Batch` with
   `status="Failed"` and a populated `error_message`.
10. BOQ Header UI reflects actual release scope (preview only)
    and does not promise async or template behavior it does not
    have.
11. Consultant-approved implementation report `EV-068` is added.

## Final Recommendation

Proceed with **Preview + Small Synchronous Commit** as the finish
scope, with three honest adjustments to the original plan:

- The BOQ Header JS dialog is preview-only in practice today and
  should not be expanded in this phase. Document the gap and track
  it as a follow-up.
- `get_import_status` and `create_import_template` are not wired
  anywhere today. Either expose them as real APIs or remove the
  public methods; do not leave placeholder text on shipped service
  methods.
- `enable_boq_excel_import_preview` is declared but not enforced.
  Either enforce it or document the gap. Do not ship a service
  contract that contradicts the field's promise.

Do not implement async import in this phase. Async import deserves
a separate design because it requires queueing, status polling,
retry/failure handling, large-file lifecycle management, and
operator controls.
