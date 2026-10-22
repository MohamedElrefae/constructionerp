# Existing-feature UAT — defect register

**Scope clarification — 12 October 2026:** The [foundation remediation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) now governs the full program: existing gaps, required enhancements, maintainability, operations and owner acceptance before new business modules. Track execution in the [foundation work register](construction_foundation_work_register_2026-10-12.md). The UI plan is one workstream; its earlier backend-only classifications describe current availability, while master tasks F18/F19 plan completion of those interfaces and require additional owner tests.

**Created:** 12 October 2026  
**Status:** Planning; source findings below have not yet been reproduced on a deployed UI.

Related: [plan](existing_features_owner_ui_acceptance_plan_2026-10-12.md) · [results](owner_ui_test_results_2026-10-12.md).

## Issue index

| ID | Issue | Origin / status | Proposed severity | Cases | Owner / next action |
|---|---|---|---|---|---|
| UAT-D001 / K-01 | Import button can report success for preview without committing BOQ | Static source finding; awaiting deployed UI reproduction | S1 if confirmed for promised import workflow | UI-50,51,53 | Engineering: inspect current route and reproduce with three-row fixture |
| UAT-D002 / K-02 | Old cost-analysis guide states incorrect item cost projection | Documentation discrepancy; awaiting correction | S2 documentation; any wrong-money runtime behavior is S1 | UI-16–23 | Engineering + Finance: correct guide using confirmed direct-cost rule |
| UAT-D003 / K-03 | August role UAT overgeneralizes PM permissions and setup rights | Documentation discrepancy; awaiting effective-role review | S2 documentation; any access leak is S0 | UI-01,02,15,19,26,30,31 | Engineering: provide current role matrix and distinct identities |
| UAT-D004 / K-04 | UI availability and VFC applicability need explicit inventory | Coverage finding; awaiting inventory | Triage after inventory | UI-50,54,57,63–65; T-04,06 | Engineering: classify actual screens/services and supported forms |
| UAT-D005 (new) | MCP bridge `get_boq_header` always returns empty items (reads a non-existent `items` child field) | **Source-level reproduction 2026-10-12 at `c9e6803c`**; runtime symptom on deployed tooling not yet reproduced | S1 for the tooling contract (tool returns wrong data silently); S2 for the related unfiltered tree helper | Tooling only | Engineering: repair with scoped BOQ Item lookup (F27); reproduce exact runtime symptom before closing |

Severity is provisional until business impact is confirmed. No issue is marked fixed by producing this register. “Not reproduced” requires the candidate, actual steps and contrary evidence.

## UAT-D001 — source evidence and reproduction request

At inspected source `c9e6803c5ac63073aeb0b166c779844d29051d8d`, `boq_header.js` calls `construction.api.boq_api.import_boq_excel` with file URL and header but no `dry_run`. The API defaults `dry_run=1`. The service returns a successful preview for valid input; the button handler then displays “Import successful.” This indicates a likely gap between UI messaging and saved business records. Another deployed interface/customization could change the actual path; inspect before diagnosing the deployed outcome.

Reproduce on a fresh Draft header using a three-row workbook. Record counts before, click the actual Import button, capture message, refresh lists/header and record counts afterwards. Inspect any preview/commit controls and Import Batch. Expected: a clear preview followed by explicit supported commit with saved records, or an accurately labelled preview-only capability. A successful preview message alone is insufficient evidence of completed import. Do not execute an API manually and record the owner UI case as passed.

**Source-level reproduction record — 12 October 2026 (F01, candidate `c9e6803c5ac63073aeb0b166c779844d29051d8d`, inspection only; no site, suite or UI execution):**

| Field | Record |
|---|---|
| Origin | Static source finding |
| Candidate / method | `c9e6803c…`; file inspection; SHA-256 `113193ffda62922b373a6de94806786a23e7e5dba05192ac3808794653908cec` |
| Confirmed current behavior | Single live Desk route reproduced in source: Dialog "Import BOQ from Excel" has one Attach field and primary action "Import"; the call passes only `{file_url, boq_header}`. API `import_boq_excel(file_url, boq_header, dry_run=1, …)` (SHA `76d61daacd401b85328d0d1bbe1cad631faa1eea2ce7877cebf9110d7f73fc43`) defaults dry_run to 1 and `cint`s it; `import_from_excel` returns the parse preview unchanged when `dry_run` (SHA `4d3bb3a80e6e56fce2e5ee01d05d0619d1ae52ce9b1261c58413b7accffe08e9`). Preview returns `success: not errors`, `dry_run: True`, `requires_user_confirmation: True`. On `success` the handler hides the dialog, reloads the doc and shows "Import successful". No other current caller of `import_boq_excel` exists in tracked source (only this dialog). |
| Consequence | For a valid workbook the user sees a green success message while **zero** BOQ Item/Structure records are committed and no Import Batch exists (commit path returns `dry_run: False` with `import_batch`, `created_items`; not reached). |
| Still owed before closure | Deployed-UI reproduction on the F16 candidate (steps above); repair of preview/commit/messaging; retry/duplicate-safety; owner UI-50/51/53 retest. |
| Root cause / bounded correction proposal | Client never passes `dry_run` and never distinguishes preview from commit. Correction direction: preview step + explicit commit (`dry_run=0`) with persisted counts and batch traceability; keep administrator/`require_boq_access` write checks unchanged. Fix design belongs to F16 with F04 fixtures. |
| Linked gate / package | G14 → F16 (P0); defects loop F38 |

## UAT-D005 — source evidence and reproduction record

**Source-level reproduction — 12 October 2026 (F01, candidate `c9e6803c5ac63073aeb0b166c779844d29051d8d`, inspection only):**

| Field | Record |
|---|---|
| Origin | Static source finding (original analysis item E11, MCP BOQ retrieval) |
| Candidate / method | `c9e6803c…`; file inspection + live DocType JSON schema read; SHA-256 `8aa457c8fe23a3d5436a1face699de169cb7962a14f091a38d2112826e75629b` |
| Confirmed current behavior | `tool_get_boq_header` builds its response from `doc.get("items", [])`. The BOQ Header DocType JSON at this candidate contains **no child-table fields** (fields: project, project_name, boq_type, status, version, title, total_contract_value, total_estimated_value, total_budgeted_cost, total_revised_value, locked_by, locked_date). BOQ Items are separate documents; the BOQ Item JSON carries both `structure` (Link→BOQ Structure) and `boq_header` (Link→BOQ Header). The schema mismatch is confirmed. **F03 correction:** the local Frappe `BaseDocument.get` signature uses `filters` as its second argument; empty `[]` is falsy and does not set `default`. With no `items` attribute the expression returns `None`, and iteration raises `TypeError` in the isolated source-method probe. The deployed bridge outcome remains Not Run. |
| Consequence | The bridge cannot retrieve the separately stored BOQ lines through this expression; on the probed local method it fails during iteration. Other deployed runtimes/configurations need actual bridge reproduction. |
| Related observation (same file) | `tool_get_boq_structure_tree` (lines 187–197) runs `get_all("BOQ Structure", filters={"boq_header": …})` guarded only by the `guard_doctype` allowlist — no per-user authorization or scope check. Needs review as part of F27. |
| Still owed before closure | Reproduce the exact runtime symptom through the bridge on the F02/F27 target (the old report's exception text is not assumed); then repair, add meaningful tests (allowed header returns items; forbidden scope returns none; no-items/missing-header handling; bounded result size), and review the tree helper's authorization. |
| Root cause / bounded correction proposal | Use bounded retrieval of separate BOQ Item documents after explicit parent/read/scope authorization, preferably permission-aware `get_list` with the caller identity. `get_all` bypasses Frappe permissions; a Header filter alone is insufficient. Any lower-level query must follow independently verified authorization. Preserve response shape and handle empty/missing/forbidden headers; no Header schema change. |
| Linked gate / package | G14 → F27 (P1); defects loop F38 |

### UAT-D005 interpretation correction — F03 follow-up

The earlier F01 handoff claimed “always returns empty items”; that interpretation is superseded. Local vendor checkout `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`, `frappe/model/base_document.py:327`, was read. An isolated Python probe executed only that extracted method with a stub object: `get(stub, "items", [])` returned `None`; iteration raised `'NoneType' object is not iterable`. No Frappe import, bridge call, site connection or business suite occurred. See the [F03 source inventory](construction_foundation_feature_route_inventory_2026-10-12.md) and JSON probe/hash record. Full bridge and denied-scope reproductions remain owed in F27-R/F27.

## Defect detail template — copy for each new issue

### UAT-D___ — short title

| Field | Record |
|---|---|
| Origin: source finding / observed UI / engineering test | |
| Status / severity / business impact | |
| First observed date / reporter | |
| Candidate, site, browser, language | |
| Role / company / project / record IDs | |
| Related case and exact subcase | |
| Preconditions and minimal reproduction steps | |
| Expected result / independent calculation | |
| Actual result / saved state / evidence | |
| Affected workflows / scope of testing to stop | |
| Safe workaround, if any | |
| Assigned engineer / target date | |
| Root cause / proposed bounded correction | |
| Fix commit/assets/settings and code review evidence | |
| Engineering regression result and candidate | |
| Owner retest attempt/evidence and candidate | |
| Neighboring/denied-path regressions | |
| Closure decision / Mohamed confirmation / date | |
| If deferred: reason / business impact / owner / deadline | |

## Triage and closure rules

1. Record one root issue with all affected cases; keep case-level failures visible.
2. S0/S1 blocks acceptance; continue only unrelated safe sessions.
3. Keep financial fixes separate from cosmetic batches where useful for review.
4. A fix candidate requires technical regression evidence before owner retest.
5. Only the owner's successful retest plus relevant technical evidence closes a UI failure.
6. Retain rejected/failed attempts; never overwrite evidence to make counts look better.
7. Do not implement an unrelated new feature as part of defect repair. Record new needs in a separate post-acceptance backlog.
