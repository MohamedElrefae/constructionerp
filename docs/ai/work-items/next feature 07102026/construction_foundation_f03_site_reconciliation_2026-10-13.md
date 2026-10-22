# F03 — Installed-site reconciliation (v16rehearsal.localhost, 2026-10-13)

**Candidate:** construction `1e46488` · frappe `2871914` (16.51.1) · erpnext `7474d9e` (16.50.0)
**Site:** v16rehearsal.localhost (F02 UAT target, re-baselined 2026-10-13)
**Supplements:** [source inventory](construction_foundation_feature_route_inventory_2026-10-12.md)
**Method:** read-only `tabDocType`/`tabDocPerm`/`tabSingles`/workspace/sidebar/print/page/role queries; no mutations, no suite runs.

## 1. Installed versions

frappe 16.51.1, erpnext 16.50.0, construction 0.0.5 @ `1e46488`. Vendor worktrees clean (`git diff` empty on frappe/erpnext). App has one uncommitted source change (sidebar config title, held for F38).

## 2. DocTypes: 19 installed vs 21 source owners

Installed `module IN (construction, Construction)`: 19. Missing vs source: **CostItem, PlantResource** — source JSON present (`doctype/costitem`, `doctype/plantresource`) but no `tabDocType` rows. Cause: `patches.v8_1.deprecate_costitem_plantresource` (applied). Logged as F03-D001: source JSON retained for deprecated scaffolds that are not installed; F26 must decide retain-archive vs remove-source.

**Module case divergence (F03-D002):** installed rows mix `Construction` (7) and `construction` (12). Source JSON declares lowercase `construction` throughout. Effect today: none observed on routing/permissions (queries use exact DocType names, not module case); risk is future app-side tooling that filters by module string. F26/F31 to normalize or pin the convention; no data fix in this task.

## 3. Permissions (source vs installed)

`tabDocPerm` snapshot for BOQ doctypes matches the source inventory's role/rights shape (Construction Owner / PM / Site Engineer / Accountant / Read-Only / System Manager with the same read/write/create/delete/submit/cancel pattern sampled across BOQ Cost Analysis, Header, Import Batch, Item, Item Stage, Quantity Revision, Structure). Full matrix diff is F11 work; no widening observed in the sample. Effective User Permissions: 55 `tabDefaultValue` rows; 7 `User Scope Context` records exist.

**Critical (F03-D003):** `tabSingles` `Construction Settings.enable_scope_context = 0` on this site vs source default 1. Scope enforcement (wildcard `permission_query_conditions`, `doc_events` containment) is therefore **inactive** on the UAT target. F11/F12 must record this as the starting condition: deny-path evidence gathered with enforcement off does not prove the enforced posture. Engineering decision recorded below: primary UAT runs with enforcement ON. The observed OFF snapshot remains the starting condition; no setting change is claimed here.

Other flags vs source defaults: `enable_boq_excel_import_preview = 1` (source 0), `enable_boq_excel_import_commit = 1` (source 0), `enable_stage_measurement_ui = 1` (source 0), `enable_option_b_report_access_bypass = 1` (matches source 1). Import/commit paths are therefore enabled on UAT — consistent with F16 testing, but F14 must qualify bounds under the enabled state.

## 4. Navigation, prints, pages

- Workspace `Construction` (module `construction`) present. Workspace Sidebar `Construction Home` present (ENV-D001 fix applied; config uncommitted, held for F38). Legacy `Sidebar` record also `Construction Home`.
- Print formats active (disabled=0): BOQ Print Format + 4 bilingual commercial formats. Page `bilingual-report-viewer` present.
- No `tabReport` rows under construction modules — consistent with source (no query-report definitions shipped; F19 builds views).

## 5. Schema note

`tabBOQ Header` has **no `company` column** (earlier `SELECT company` → unknown column; header carries `project` link). Any company scoping resolves via project → company, never a direct header field. F11/F19 designs must preserve this.

## 6. Custom fields and integration surface

19 `tabCustom Field` rows touching Account/Item/Company/Project or construction modules — install-created integration surface present. Enumeration of each field is F20/F31 detail; presence confirmed.

## 7. Assets

Login page renders (200 + title, verified 2026-10-13 during F13); auth boundary denies guests. Per-file asset resolution (37 hook entries) remains F25 browser work; no asset failure observed at page level.

## 8. Close-out

Installed inventory complete for F03's seven reconciliation steps except: full per-field DocType diff (F31 detail), per-user effective permission matrix (F11), and per-asset HTTP/hash check (F25). F03 moves to **Engineering verified** with F03-D001–D003 feeding F26/F31/F11/F12. No site data changed by this task.

## 9. Engineering decision — primary UAT enforcement ON (2026-10-13)

Use `enable_scope_context = 1` on **v16rehearsal.localhost** for the primary foundation qualification and final owner UI block. This qualifies the intended enforced posture and prevents scope-dependent acceptance from relying on the disabled configuration. Native role/User Permission denials observed while OFF remain evidence of those native controls only; they do not establish the app's scope boundary.

**F04 execution order:**

1. Preserve the OFF baseline above. Prepare financial fixtures in two companies, with at least two projects in one company and a project in the other, plus applicable cost-center/branch/department relationships. Record expected quantities and totals independently.
2. Prepare distinct ordinary-role accounts for the relevant workflows, approval actors and read-only persona. Record native rights, User Permissions and valid active scope contexts. Include missing-scope and out-of-scope cases. Administrator/System Manager may perform setup; their exempt behavior cannot prove ordinary-user containment.
3. Apply ON to the named UAT site, record persisted readback, timestamp, candidate and related scope settings/exclusions/bypass flags, and refresh affected sessions/caches. This is an operator step still pending, not a mutation performed by this decision review.
4. Verify ordinary-role login and allowed operations, then F11/F12 denied operations across company/project boundaries and missing scopes. Check persisted state after denied writes and coverage of lists, reports, files and exports where applicable. BOQ Header company must resolve through its project link.
5. Label any OFF-mode diagnostics separately, then restore and verify ON before returning to primary qualification. Re-run any previously collected scope-dependent evidence obtained while OFF.

**Closure boundary:** F03-D003 remains open until ON readback and the mapped F04/F11/F12 evidence exist. This decision removes the planning choice blocker; it does not mark F04 fixtures or permission tests complete. Mohamed's personal UI acceptance remains the consolidated final block after engineering completion and F43 preparation.
