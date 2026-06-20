# BOQ Excel Import — Manual UI Test Plan (Pre-Commit)

Date: 2026-06-16
Site: `v16.localhost`
Repo: `/home/mohamed/frappe-bench/apps/construction`
Audience: Mohamed (manual tester) before commit
Pre-req: Read `BOQ_EXCEL_IMPORT_SCOPE_FINISH_PLAN.md` (revised 2026-06-16)
         and `CONSULTANT_REVIEW_RESPONSE_BOQ_EXCEL_FINISH.md`.

## Goal

Verify, in a real browser against `v16.localhost`, that every user-visible
piece of the BOQ Excel import scope ships correctly. The 15-check
`test_boq_import_status_smoke.run` and the parser regression smoke already
cover the server side. This plan covers the **UI** surface the smoke
harness cannot reach.

## What the User Sees (Recap)

The finish phase ships these user-visible touchpoints:

1. Two new buttons on the **BOQ Header** form (Actions group, Draft only):
   - **Import Excel** — preview-only dialog.
   - **Download Excel Template** — generates and opens a private xlsx.
2. Both buttons only appear if `enable_boq_excel_import_preview = 1`.
3. The dialog title is "Import BOQ from Excel (Preview)" with a description
   field explaining preview-only behavior and a "Run Preview" button.
4. After preview, the dialog shows error/warning counts and the form
   re-loads only if a real commit was requested (which it never is from
   the dialog).
5. New whitelisted API methods exist for `get_boq_import_status`,
   `create_boq_import_template`, `is_boq_excel_import_enabled`. They are
   server-side only in this phase — no UI calls them.

## Pre-Test Setup

### A. Create a fresh test Project

The scope-context check in `_assert_boq_header_access` only passes for
projects in the caller's `get_user_scope_hierarchy().projects` set.

1. Log in as Administrator.
2. **Project** → New.
3. Set Project Name `UI Test 2026-06-16`, Status `Open`, save.
4. Note the project name (e.g. `PROJ-00xx`).

### B. Create a fresh test BOQ Header

1. **BOQ Header** → New.
2. Set Project to the one above.
3. Set Title `UI Test BOQ 2026-06-16`.
4. Set Status `Draft`, BOQ Type `Tender`, save.
5. Note the BOQ Header name (e.g. `BOQ-2026-0xxx`).

### C. Prepare test xlsx files

Use `python3` from the bench to generate three small workbooks. Save them
to `private/files/` so the dialog can attach them, or attach from a
downloads folder.

**File 1 — `ui_test_preview.xlsx` (Flat mode, clean):**

```python
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "BOQ"
ws.append(["Description", "Unit", "Quantity", "Unit Price"])
ws.append(["Excavation", "m3", 100, 50])
ws.append(["Backfill", "m3", 80, 40])
ws.save("/tmp/ui_test_preview.xlsx")
```

**File 2 — `ui_test_async.xlsx` (Flat, > 2000 rows triggers async block):**

```python
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "BOQ"
ws.append(["Description", "Unit", "Quantity", "Unit Price"])
for i in range(2500):
    ws.append([f"Item {i}", "m3", 1, 10])
wb.save("/tmp/ui_test_async.xlsx")
```

**File 3 — `ui_test_ambiguous.xlsx` (Ambiguous row):**

```python
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "BOQ"
ws.append(["Description", "Unit", "Quantity", "Unit Price"])
ws.append(["General Notes", "", "", ""])  # ambiguous
ws.append(["Excavation", "m3", 10, 50])
wb.save("/tmp/ui_test_ambiguous.xlsx")
```

### D. Start state: both flags OFF

1. **Construction Settings** → set both:
   - `Enable BOQ Excel Import Preview` = 0
   - `Enable BOQ Excel Import Commit` = 0
2. Save.

## Test Cases

### TC-1: Buttons hidden when preview flag is OFF (D from setup)

1. Open the Draft BOQ Header from setup step B.
2. Open the **Actions** dropdown.
3. **Expect**: "Import Excel" and "Download Excel Template" are **NOT**
   present.
4. **Pass criteria**: only the existing buttons (Advance Status, Variation
   Orders, Revised BOQ View) are visible.

### TC-2: Buttons appear when preview flag is ON, commit OFF

1. Construction Settings → `Enable BOQ Excel Import Preview` = 1.
   Leave `Enable BOQ Excel Import Commit` = 0.
2. Save.
3. **Reload** the BOQ Header form (Frappe doctype_js is per-form).
4. Open Actions dropdown.
5. **Expect**: Both buttons appear.
6. **Pass criteria**: "Import Excel" and "Download Excel Template" are
   visible. This is the P2.2 fix — preview-only access should still
   surface the buttons.

### TC-3: Download Excel Template — preview flag ON, commit OFF

1. From TC-2 state, click **Download Excel Template**.
2. **Expect**: a freeze overlay "Generating template..." appears briefly,
   then a new browser tab opens with the xlsx download.
3. Open the downloaded xlsx.
4. **Expect**:
   - Sheet `BOQ Import Template` exists with header row matching
     `TEMPLATE_COLUMNS` (WBS Code, Parent WBS, Title / Description,
     Type, Unit, Quantity, Unit Price, Factor, Notes, Owner Page,
     Owner Ref No, Owner File Ref).
   - Sheet `Instructions` exists with the three-mode explanation.
   - First row is frozen.
5. **Pass criteria**: workbook opens, both sheets present, header row
   matches the constant.

### TC-4: Import Excel dialog — preview flag ON, commit OFF

1. From TC-2 state, click **Import Excel**.
2. **Expect**: dialog titled "Import BOQ from Excel (Preview)" with a
   single Attach field whose description reads roughly
   "This dialog runs a preview only. To commit, call the API with
   dry_run=0 and a confirmed import mode, or wait for the
   preview-then-commit UI."
3. **Pass criteria**: title includes "(Preview)", description field is
   visible, primary button reads "Run Preview".

### TC-5: Preview succeeds — clean file

1. In the TC-4 dialog, attach `/tmp/ui_test_preview.xlsx`.
2. Click **Run Preview**.
3. **Expect**:
   - Freeze overlay "Parsing workbook..." appears.
   - On success: green alert with text
     "Preview complete. Errors: 0, Warnings: 0." (or similar).
   - Dialog stays open so the user can attach another file or close.
4. **Pass criteria**: no red msgprint, alert indicator is green, the
   count of 0 errors and 0 warnings is correct.

### TC-6: Preview surfaces errors — ambiguous file

1. Attach `/tmp/ui_test_ambiguous.xlsx`, click **Run Preview**.
2. **Expect**:
   - Orange (not green) alert:
     "Preview complete. Errors: 1, Warnings: 0."
3. **Pass criteria**: alert indicator is orange, error count = 1.

### TC-7: Status API via Frappe console (server-only, no UI)

This is the closest UI proxy for the status endpoint: open the
Frappe desk console (Settings → Developer → Console, or
`/app/web-page/console` if available) and run:

```python
frappe.call(
    "construction.api.boq_api.get_boq_import_status",
    {"import_id": "BOQIMP-FAKE"}
)
# Expected: {"success": False, "status": "not_found", ...}

frappe.call(
    "construction.api.boq_api.get_boq_import_status",
    {"import_id": "BOQIMP-20260616-XXXXXXXX"}
)
# Expected: real batch dict with status / summary / counts
```

**Pass criteria**: not_found shape for unknown id, real shape for a
real id, `error_message` present when the batch is `Failed`.

### TC-8: Full commit path via the API (preview OFF → commit ON)

1. Construction Settings → `Enable BOQ Excel Import Preview` = 1,
   `Enable BOQ Excel Import Commit` = 1.
2. From the Frappe console:

```python
result = frappe.call(
    "construction.api.boq_api.import_boq_excel",
    {
        "file_url": "/private/files/ui_test_preview.xlsx",
        "boq_header": "BOQ-2026-0xxx",  # from setup B
        "dry_run": 0,
        "confirmed_import_mode": "Flat",
    },
)
# Expected: {"success": True, "import_batch": "BOQIMP-...", "created_structures": [...], ...}
```

3. **Pass criteria**: success, `import_batch` is non-empty, 3 structures
   (1 root + 2 items) and 2 items created.
4. Open the BOQ Header Tree view and confirm 3 rows under
   `Imported BOQ Items / بنود مستوردة`.

### TC-9: Permission denial — restricted user

This is the P1.2 fix verification.

1. As Administrator, create a new user `ui_test_restricted` with role
   `Project Manager` (read-only on `BOQ Header` is the default).
2. Restrict that user's project scope to a **different** project (not
   the UI Test one from setup A).
3. Log out, log in as `ui_test_restricted`.
4. From the console, try to import against the test BOQ Header:

```python
frappe.call(
    "construction.api.boq_api.import_boq_excel",
    {
        "file_url": "/private/files/ui_test_preview.xlsx",
        "boq_header": "BOQ-2026-0xxx",
        "dry_run": 1,
    },
)
```

5. **Expect**: error in the response. The exact shape depends on
   whether `_assert_boq_header_access` raises `PermissionError`
   (re-raised) or `ValidationError` (caught and returned as
   `{"success": False, "error": "..."}`). The message should mention
   authorization / scope.

**Pass criteria**: the call does not commit anything; an authorization
error is returned or raised.

### TC-10: Savepoint rollback — failed mid-import leaves no rows

This is the P1.1 fix verification, easiest to exercise through the
smoke runner, but a manual sanity check is worthwhile.

1. Re-enable both flags as Administrator.
2. Confirm there is a Draft BOQ Header (the test one or a fresh one)
   with no existing structures.
3. From the console, simulate a commit with a file that will pass
   preview but fail mid-insert. The simplest way is to inject failure
   by monkey-patching the service before calling it:

```python
from construction.services.boq_import_service import BOQImportService
orig = BOQImportService._insert_structure_from_import_row
def fail_on_second(*args, **kwargs):
    if not fail_on_second.called:
        fail_on_second.called = True
        return orig(*args, **kwargs)
    raise RuntimeError("Simulated mid-import failure")
fail_on_second.called = False
BOQImportService._insert_structure_from_import_row = staticmethod(fail_on_second)

result = frappe.call(
    "construction.api.boq_api.import_boq_excel",
    {
        "file_url": "/private/files/ui_test_preview.xlsx",
        "boq_header": "BOQ-2026-0xxx",
        "dry_run": 0,
        "confirmed_import_mode": "Flat",
    },
)
# Expected: success=False, error="... Simulated mid-import failure"
```

4. After the call, list structures and items for the test BOQ:

```python
frappe.get_all("BOQ Structure", filters={"boq_header": "BOQ-2026-0xxx"})
frappe.get_all("BOQ Item", filters={"boq_header": "BOQ-2026-0xxx"})
# Expected: empty lists (savepoint rolled back)

frappe.get_all(
    "BOQ Import Batch",
    filters={"boq_header": "BOQ-2026-0xxx", "status": "Failed"},
    fields=["name", "error_message"],
)
# Expected: at least one Failed batch with the simulated error text
```

**Pass criteria**: zero structures, zero items, one Failed batch with
`error_message` populated.

### TC-11: Re-import protection (existing test, manual confirmation)

1. With the test BOQ Header now empty (TC-10 rolled back), re-run TC-8.
2. **Expect**: success — the rollback truly wiped the partial state.
3. **Pass criteria**: commit succeeds, 3 structures + 2 items.

### TC-12: Async block message — preview + commit ON, large file

1. Both flags on. From the console:

```python
result = frappe.call(
    "construction.api.boq_api.import_boq_excel",
    {
        "file_url": "/tmp/ui_test_async.xlsx",
        "boq_header": "BOQ-2026-0xxx",
        "dry_run": 0,
        "confirmed_import_mode": "Flat",
    },
)
# Expected: success=False, error contains "too large for synchronous import"
```

2. **Pass criteria**: the error string is the new WP4 copy, not
   "must use async import".

### TC-13: Template download — preview ON, commit OFF, the full flow

1. Reset Construction Settings: preview ON, commit OFF.
2. Click **Download Excel Template** again.
3. **Expect**: works the same as TC-3.
4. **Pass criteria**: template still generated, private file, both
   sheets, headers match.

### TC-14: Buttons hidden when commit is ON but preview is OFF

1. Construction Settings → preview OFF, commit ON.
2. Reload BOQ Header form.
3. **Expect**: Buttons are hidden.
4. **Pass criteria**: nothing in the Actions group for Excel/template.
   The `enabled = preview_enabled` helper returns false in this state.

### TC-15: After-commit — `get_boq_import_status` returns real data

1. With both flags ON, after TC-8 succeeded, capture the
   `import_batch` value from the result.
2. From the console:

```python
status = frappe.call(
    "construction.api.boq_api.get_boq_import_status",
    {"import_id": "BOQIMP-..."},
)
# Expected: success=True, status="Committed",
#   committed_structure_count=3, committed_item_count=2
```

3. **Pass criteria**: status = `Committed`, counts > 0, `error_message`
   absent or empty.

## Reset / Cleanup

After all tests pass:

1. Delete the test Project and BOQ Header.
2. Delete the test files from `private/files/` and `tabFile`.
3. Reset Construction Settings: `Enable BOQ Excel Import Preview` = 0,
   `Enable BOQ Excel Import Commit` = 0.
4. Remove the `ui_test_restricted` user if you created one.

## Pass / Fail Summary

| TC | Title | Pass | Notes |
| --- | --- | --- | --- |
| 1 | Buttons hidden — preview OFF | ☐ | |
| 2 | Buttons appear — preview ON, commit OFF | ☐ | P2.2 fix |
| 3 | Template download — preview ON, commit OFF | ☐ | |
| 4 | Dialog copy — preview-only | ☐ | |
| 5 | Preview success — clean file | ☐ | |
| 6 | Preview success — ambiguous file | ☐ | |
| 7 | Status API via console | ☐ | |
| 8 | Full commit — preview + commit ON | ☐ | |
| 9 | Permission denial — restricted user | ☐ | P1.2 fix |
| 10 | Savepoint rollback — no partial rows | ☐ | P1.1 fix |
| 11 | Re-import after rollback | ☐ | |
| 12 | Async block message | ☐ | WP4 |
| 13 | Template still works — preview only | ☐ | |
| 14 | Buttons hidden — preview OFF, commit ON | ☐ | |
| 15 | Status API after commit | ☐ | P2.1 fix |

All 15 must pass before commit. If any fail, the matching work
package is not actually shipped and must be revisited before staging
the change.

## After All Pass

- Update `EV-068-wp2-finish-scope.md` with the manual UI test
  results (link this file as `EV-068-attachment.md` or paste the
  filled table).
- Update `evidence_log.md` EV-068 row: change `Pending` → `User`
  (the reviewer who ran the tests) or `Manager` if a manager
  verifies.
- Commit the work in the order suggested in the consultant response
  conversation (one commit per major concern, or one combined
  commit).
- Stage deploy per `EV-061-frappe-cloud-deployment-plan.md`.

## What This Plan Does NOT Cover

- Browser compatibility (only test in the browser you usually use;
  EV-064 has a Playwright pass for reference).
- Load testing of the template endpoint.
- Multi-user concurrent commit on the same BOQ Header (covered by
  the existing duplicate-import protection, not the finish phase).
- Arabic UI / RTL — out of scope for the finish phase per the plan.
