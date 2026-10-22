# F26 — Deprecated paths and scaffolds (classification)

Date: 2026-10-14 · Method: source + site reads. **No legacy data deleted in this review.**
Candidate question for F31: what ships, what stays in the repo, what goes.

## 1. Legacy DocTypes: CostItem / PlantResource

| Fact | Value |
|---|---|
| Source JSON | `construction/doctype/costitem/cost_item.json`, `construction/doctype/plantresource/plant_resource.json` — present |
| Installed on `v16rehearsal.localhost` | **not installed** (`tabDocType` has no such rows; F03-D001) |
| Site tables | `tabCostItem` / `tabPlantResource` exist with **0 rows each** |
| Deprecation patch | `construction/patches/v8_1/deprecate_costitem_plantresource.py` — verifies counts, logs, marks records deprecated; does NOT drop tables |
| Remaining code refs | `cleanup_old_refs.py`, `cleanup_doctypes.py`, `hooks.py:474` (`translated_doctypes` lists both for `ar`), `check_arabic_localization.py` |

**Classification: deliberately retained scaffold, not removable yet.** Tables are empty so
there is no customer-data impact today, but the patch's own contract is "safe rollback if
needed" — dropping tables would break that. F31 decision: keep tables + JSON through the
foundation gate; revisit removal (with a migration that proves zero rows on the target)
after F31, not before it.

## 2. React assets and API (`modern_form_api.py`)

| Item | State |
|---|---|
| 8 JSX files (`ExportButtons`, `UltimateButton`, `TreeView`, `FormLayoutControls`, `DraggablePanel`, `FormField`, `Sidebar`, `UnifiedCRUDForm`) | present in `construction/public/js/components/`; only `index.js` references them internally |
| `components/index.js` | **not loaded** — zero references in `hooks.py` (removed per ADR-008, 2026-06-21) |
| `construction/api/modern_form_api.py` (13 functions, 7 whitelisted endpoints) | live but **System Manager only** (`_require_system_manager`) |

**Classification: deliberately retained, unadvertised (ADR-008 respected).** No reachable
ordinary-role mutation: the bundle is not loaded and the API refuses non-System-Managers.
Customer-data impact: none — the React path writes through the same DocTypes when used by a
System Manager, and no such use is part of any accepted flow. F31 decision: ship the files
(they are already tracked; removal saves nothing and breaks the ADR's "available for
reference" promise). Revisit isolation only after references/tests prove safe, per the plan.

## 3. Guarded compatibility code

| Item | State | Classification |
|---|---|---|
| `patchSidebarWorkspaceNavigation` (`frappe_compat_patches.js`) | targets `SidebarHeader.prototype.setup_select_options` / `add_app_item`, **absent** at vendor rev `2871914` | **retained guarded dead code** — creates methods the vendor never calls; kept to avoid churn inside the F38 batch; F25 bump rule covers re-check. NOT removed in F30 (lives inside a loaded file; removal is behavior-adjacent) |
| `patchWorkspaceMenuNavigation` | targets `frappe.ui.create_menu`, **absent** anywhere in installed public JS | same as above |
| `theme_loader_v16.js` | documented no-op safety net (CSS handles styling) | **deliberately retained** — costs one no-op load, protects if the v24 loader path changes |
| `switch_theme.py` (older override, superseded by `switch_theme_simple.py`) | present in `overrides/` | **RETAINED — reclassified in F30:** a security test (`test_legacy_switch_theme_route_enforces_strict_contract`) pins its strict-shim contract, so it is referenced, not unreferenced. Removal would break the suite; revisit only with the test |

## 4. Must-preserve items (explicitly not touched)

- **Direct Labor Designation** (`tabDirect Labor Designation` holds 1 row) and
  `Construction Settings.direct_labor_designations`: active progress-billing flag per the
  plan's Done-when. Untouched.
- Approved Quantity Revisions / approved history: permanent by design (F24-D002).
- `tabCostItem` / `tabPlantResource` tables: not dropped (see §1).

## 5. Stale fixtures (F30 outcome)

- `construction/fixtures/workspace_sidebar-construction.json.bak` and
  `workspace_sidebar_construction.json.bak` (917 bytes each, May 2025): no code references
  either file; the live Sidebar ships from
  `construction/construction/sidebar/construction_home/construction_home.json`.
  **REMOVED in F30** (this review).

## 6. Status

F26 **classified, no deletions performed**. Removals (`switch_theme.py`, the two `.bak`
files, and later the two dead patches) belong to F30 bounded refactoring with an ADR where
the plan requires one. F31 can proceed: nothing classified here blocks a clean install —
empty legacy tables migrate silently, the React path is unloaded, and dead guards no-op.
