# WBS P2 Specification — BOQ Item Planned Execution Location & Stage Mapping

**Status:** OWNER-APPROVED SPECIFICATION (Slice 1 Authorized)  
**Baseline:** `develop` @ `47bad26` (`origin/develop` synced)  
**Unified Bench / Site:** `/home/mohamed/frappe-bench` · `wbs-p1-lab.localhost` (`v16.localhost` untouched)  
**Model:** **Choice B — BOQ Item Planned Execution Location (`BOQ Item.planned_execution_node`) with one-time inheritance to newly created `BOQ Item Stage.execution_node`**

---

## 1. Frozen Product Rule & Owner Decisions

> **Visible UI Product Rule:** *"Changing the BOQ Item's planned location affects future Stages only; existing Stage locations remain unchanged."*

| Decision | Approved Rule |
|---|---|
| **Choice B** | `BOQ Item.planned_execution_node` is a planning default; `BOQ Item Stage.execution_node` is the operational assignment. One-time copy on Stage creation only; never retroactively updates existing Stages. |
| **#1 Disabled parent default** | If the Item's `planned_execution_node` (or any ancestor) is disabled when a Stage is created, allow an otherwise valid Stage to save with `execution_node = NULL`. Show warning on save and unmapped state when reopened. Planners may explicitly select another eligible leaf on creation. |
| **#2 Site Engineer creates a Stage** | Show the proposed inherited location as a preview. The Site Engineer submits without supplying a node; the server reads the Item's current default at save time, applies it if effectively enabled, and records `inherit_on_create`. Any manual node supply/override/relink/clear by a Site Engineer is rejected (`PermissionError`). |
| **#3 Execution-locked Stages (Alt B + A1)** | Evaluated against **current persisted Stage state** ("while any execution-lock condition holds"): `measured_executed_qty > 0`, OR `certified_qty > 0`, OR `stage_status IN ("Completed", "Certified")`, OR any reference in any of the 8 `TRANSACTION_CHILD_DOCTYPES` (including draft or cancelled parent docs). While any lock condition holds: allow only first-time `NULL → eligible leaf` via a labelled **Historical assignment** with mandatory reason and recorded `historical_trigger` + qty/status snapshots; block relink and clear. |
| **#4 Reasons** | Optional on initial `set` (`NULL → leaf`) of an Item default or unlocked Stage, and not required on `inherit_on_create`. Mandatory non-blank on `change`, `clear`, and `initial_historical_map`. Unchanged saves are no-ops with zero audit rows. |
| **#5 Titles of referenced nodes** | Allow `title` edits on referenced nodes/ancestors; `ebs_code` remains immutable globally; audit rows persist full path snapshots (`old_path_snapshot` / `new_path_snapshot`). |
| **B Permissions & Deletion** | Add `Construction Owner` to `BROWSE_ROLES` **only** (`WRITE_ROLES` stays `Project Manager` + `System Manager`; `DELETE_ROLES` stays `System Manager` only, with subtree protection applying to System Manager too). Within authorized project and scope, single-role `Construction Owner` can browse the picker, set/change/clear BOQ mappings, and read mapping audit history, and **cannot** create/update/move/disable/delete Execution Tree nodes. |
| **P3 Contract** | Unmapped Stages (`execution_node IS NULL`) always report as `Unmapped` in P3 — never fall back to `BOQ Item.planned_execution_node`. |

---

## 2. Schema (Nullable, Single Index per Link, Immutable Audit)

1. **`BOQ Item.planned_execution_node`**: `Link` → `Execution Breakdown Node`, `read_only: 1`, `no_copy: 1`, `search_index: 1`, nullable on upgrade, zero backfill.
2. **`BOQ Item Stage.execution_node`**: `Link` → `Execution Breakdown Node`, `read_only: 1`, `no_copy: 1`, `search_index: 1`, nullable on upgrade, zero backfill.
   - **Duplication guarantee boundary:** `no_copy: 1` strips `execution_node` / `planned_execution_node` on **Frappe Desk UI Duplicate** (`frappe.model.copy_doc` in `create_new.js:291`) and on Python `frappe.copy_doc(doc, ignore_no_copy=False)`, so saving the duplicated Stage inherits the Item's current `planned_execution_node` with `inherit_on_create`. Callers using Frappe REST v2 `copy_doc` (`frappe/api/v2.py:183`) or Python `frappe.copy_doc(doc)` without `ignore_no_copy=False` receive the copied field by Frappe default (a `Site Engineer` saving that unstripped copy is rejected with `PermissionError`; a planner must pass `ignore_no_copy=False` or clear `execution_node` before insert).
3. **`Execution Mapping Audit`**: `InnoDB`, `autoname: EMA-.#######` (dedicated `tabSeries` key `'EMA-'` so audit naming never collides with Frappe's shared empty-key `format:` series used by `BOQ-STG-`), `permissions: []`, `allow_rename: 0`, `allow_import: 0`, `track_changes: 0`, immutable after guarded insert, plain `Data` snapshots (`target_doctype`, `target_name`, `project`, `boq_header`, `boq_item`, `action`, `is_historical_assignment`, `historical_trigger`, `stage_status_snapshot`, `measured_qty_snapshot`, `certified_qty_snapshot`, `old_node`/`old_ebs_code`/`old_title`/`old_path_snapshot`, `new_node`/`new_ebs_code`/`new_title`/`new_path_snapshot`, `reason`, `changed_by`, `changed_on`).
   - **Display vs Audit Confidentiality:** `get_mapping_display_context` returns only location display fields, effective disabled state, and minimal attribution (`action`, `is_historical_assignment`, `mapped_by`, `mapped_on`). Free-text `reason`, `historical_trigger`, and audit record IDs are returned **exclusively** by `get_execution_mapping_audit`.

---

## 3. Unified Lock Order & Delivery Slices

Deterministic lock order across Tree mutations, Item assignment, and Stage inheritance:
1. `tabProject` (`FOR UPDATE`)
2. `tabExecution Breakdown Node` (`ORDER BY name FOR UPDATE`)
3. `tabBOQ Item` (`FOR UPDATE NOWAIT` / `LOCK IN SHARE MODE`) — and `tabBOQ Item Stage` where applicable.

- **Slice 1 (Active):** `BROWSE_ROLES` update (`Construction Owner`), `BOQ Item.planned_execution_node` + `BOQ Item Stage.execution_node` schema & controller guards (direct-edit block, reverse parent-chain check, `no_copy: 1`), `Execution Mapping Audit` DocType, `execution_mapping.py` & `execution_mapping_api.py` (`set_item_planned_execution_node`, `get_eligible_execution_nodes`, `get_mapping_display_context`, `get_new_stage_default_preview`, `get_execution_mapping_audit`), Stage creation `inherit_on_create` / `set_on_create` with disabled-ancestor eligibility, and **referenced-subtree protection** in `execution_tree.py` (`delete_node`, `move_node`, `update_node(is_group=1)`). Existing-Stage mapping RPC (`set_stage_execution_node`) is **deferred to Slice 2**.
- **Slice 2 (Next):** Existing-Stage mapping RPC (`set_stage_execution_node`), A1 execution-lock evaluation across the 8 `TRANSACTION_CHILD_DOCTYPES` + `historical_trigger`, `boq_accounting.py` `FOR UPDATE` Stage lock coordination, and 2-session concurrency tests.
- **Slice 3 (Final):** Bilingual EN/AR form UX (`boq_item.js`, `boq_item_stage.js`, `ar.po`) + full hostile-user & release acceptance suite.

---

## 4. Owner Amendment — D-A1 Option 3: Strict Exclusivity Between BOQ Item & Stage Locations (2026-11-25)

**Decision:** Approved by owner (`Option 3 — Strict Exclusivity`). Amends Choice B so that a `BOQ Item` and its child `BOQ Item Stage` records never simultaneously hold execution locations:

1. **Item-Level Mapping Allowed Only Without Stages:** `set_item_planned_execution_node` rejects `set` and `change` (`new_node is not None`) with `frappe.ValidationError` while any `BOQ Item Stage` exists for that `BOQ Item` (verified under lock: `Project → Execution Breakdown Nodes → BOQ Item FOR UPDATE NOWAIT → BOQ Item Stage LOCK IN SHARE MODE`). Clearing a legacy value (`new_node is None`) remains permitted with mandatory reason.
2. **Atomic Parent Default Clear on Stage Creation & Draft Stage Reparenting:** When any new `BOQ Item Stage` is inserted for a `BOQ Item` that currently holds a `planned_execution_node`, or when an existing Draft `BOQ Item Stage` is moved onto a different `BOQ Item` that holds a `planned_execution_node`:
   - On creation with blank `execution_node`, the existing one-time inheritance rule applies (inherits if eligible leaf with `inherit_on_create`, or saves unmapped with disabled warning per Decision #1/#2). On reparenting an existing Draft Stage, the Stage's own `execution_node` is preserved unchanged.
   - In the same DB transaction (`after_insert` / `on_update`), the destination `BOQ Item.planned_execution_node` is automatically cleared to `NULL` (proving zero mutation on commercial fields) and recorded as an immutable `Execution Mapping Audit` row (`action = "clear"`).
   - Subsequent Stages created on the same Item start without a parent default so planners assign each Stage explicitly.
3. **Least-Privilege Display Eligibility:** `get_mapping_display_context("BOQ Item", name)` never returns raw Stage counts. It checks `BOQ Item Stage` existence only for authorized mapping planners who also have `BOQ Item Stage` read permission, returning only minimal booleans (`can_assign_location`, `stage_managed`); non-planners receive `False` with zero Stage-table queries.
4. **Fail-Closed Repeat-Safe Existing Data Cleanup:** `execute:frappe.get_attr("construction.services.execution_mapping.clear_dual_mapped_boq_item_locations")()` (in `patches.txt`) verifies before updating any row that `Execution Mapping Audit` exists and every candidate `BOQ Item` has valid `BOQ Header` and `Project` context, failing closed if missing so no Item is ever cleared without an audit record. When valid, it clears `BOQ Item.planned_execution_node` on any pre-existing BOQ Item that already has Stages, recording `Execution Mapping Audit` (`action = "clear"`) while leaving all Stage `execution_node` values and commercial fields untouched.
