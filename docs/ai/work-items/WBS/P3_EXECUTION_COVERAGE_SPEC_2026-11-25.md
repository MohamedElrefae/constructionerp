# WBS P3 Specification — Execution Coverage, Navigation & Authorized Export

**Status:** APPROVED SPECIFICATION (Slice 1 Authorized)  
**Baseline:** `develop` @ `559b763` (`origin/develop` synced; CI run `45507614367` green)  
**Depends On:** WBS P1 (`Execution Breakdown Node`) + WBS P2 (`BOQ Item.planned_execution_node`, `BOQ Item Stage.execution_node`, `Execution Mapping Audit`)  
**Requirements Covered:** `W12`, `W13`, `W14`, `W15`, `W17`, `D09` (`01_MASTER_SCOPE.md`, `05_VERIFICATION_MATRIX.csv`)

---

## 1. Approved Decisions (1–4)

| # | Decision | Approved Rule |
|---|---|---|
| **1. Disabled locations** | **Option A** | Count disabled leaf (`disabled_node`) and disabled ancestor (`disabled_ancestor`) links on existing Stages under **Needs Review (`link_issues`)**. Expose an explicit sub-breakdown distinguishing `disabled_links` (`disabled_node`, `disabled_ancestor`) from `integrity_issues` (`missing_node`, `project_mismatch`, `group_node`) so planners can separate retired branches from broken assignments. |
| **2. Coverage and export access** | **Option A** | Enforce existing `BROWSE_ROLES` (`System Manager`, `Project Manager`, `Construction Owner`, `Site Engineer`) + `execution_tree_access.authorize(project, "read")`, followed by native BOQ read checks across the `BOQ Header -> BOQ Item -> BOQ Item Stage` chain. Apply the identical rule to screen data and both CSV and XLSX exports. `Accountant` and `Read-Only` remain denied. |
| **3. Default BOQ population** | **Option A** | Include all readable `BOQ Header`s in the selected `project` (Contract and Tender — plus Variation if present — across `Draft`, `Pricing`, `Frozen`, and `Locked`). Display `header_type` (`boq_type`) and `header_status` (`status`) on every row and in filter options so teams distinguish tender planning from live contract work. |
| **4. Verification & localization site** | **Disposable non-production lab** | Use a disposable non-production lab site for synthetic test records, Desk acceptance, and Stage-2 localization freshness evidence (including a real packaged override import so `last_release_import_at` and `last_drift_checked_at` preserve their distinct semantics). Never treat `v16.localhost` as a non-production lab in `site_classification.json`. |

---

## 2. Core Product Rules & Binding Invariants

1. **Frozen P2 Forward Rule (Zero Fallback & Label Contract):**
   - A Stage with blank/NULL `execution_node` always classifies under API key `unlinked` and visible label **`Unmapped`** — **never** falling back to `BOQ Item.planned_execution_node`.
   - `BOQ Item.planned_execution_node` appears only as a clearly labelled read-only *Item Planning Default* reference column and is never counted toward Stage coverage.
2. **Count-Based Completeness Only (`D09`, `W13`):**
   - `coverage_pct = round((healthy_linked / total_stages) * 100.0, 1)` when `total_stages > 0`, else **`None`** (displayed as **`N/A`**).
   - Visible UI & export disclaimer: *"Mapping completeness reflects Stage-to-location link counts only — it does not represent quantity balance, physical execution, certification, or financial completion."*
3. **No Unit-Confused Totals (`W14`):**
   - Never sum quantities across different BOQ Items or mixed UOMs; no cross-item quantity grand totals, no quantity-weighted coverage percentages, and no capacity comparison.
   - Stage rows carry `planned_qty` (numeric) + `uom` (from `BOQ Item.unit`); Item rows carry single-Item `item_quantity` + `uom` and single-Item `stage_planned_qty_sum` strictly within that one Item.
4. **Strictly Read-Only (`W14`):**
   - Querying, filtering, navigating, and exporting never insert, update, or delete any database record (including `File` records — downloads stream directly via `frappe.response["type"] = "download"`).
5. **No `hooks.py` Mutation:**
   - P3 adds no `hooks.py` entries, keeping the P1 hook seal and Semgrep review ledger untouched.

---

## 3. Denominator vs. Stage Filters & Disjoint Reconciliation (`W12`, `W13`)

### 3.1 Two-Stage Filter Boundary
1. **BOQ Population Filters (define the authorized BOQ denominator):**
   - `project` (required), `boq_header` (optional), `boq_structure` (optional NestedSet `lft`/`rgt` subtree), `boq_item` (optional).
   - All explicit filter IDs are authorized against `project` and native Frappe read permissions before any aggregation.
2. **Stage Result Filters (applied to authorized Stages within the BOQ population):**
   - `execution_node` (optional subtree via `execution_tree_rules.collect_subtree`), `mapping_state` (`all`, `healthy_linked`, `unlinked`, `link_issues`), `stage_status` (`Not Started`, `In Progress`, `Completed`, `Certified`, `On Hold`), and `search` (case-insensitive substring match across stage/item/header/node fields).

### 3.2 Stage Partition (Reconciling Over Matching Stages)
Every matching authorized Stage belongs to **exactly one** category:
- `healthy_linked` (**Healthy Linked**): `execution_node` is set, node exists in `project`, `is_group == 0`, and `is_effectively_enabled` (`disabled == 0` on self and all ancestors).
- `unlinked` (**Unmapped**): `execution_node` is NULL/blank.
- `link_issues` (**Needs Review**): `execution_node` is set, with one deterministic `issue_code`:
  - `disabled_links` sub-bucket: `disabled_node` (self disabled) or `disabled_ancestor` (ancestor disabled).
  - `integrity_issues` sub-bucket: `missing_node`, `project_mismatch`, or `group_node`.
- Invariants:
  - `total_stages == healthy_linked + unlinked + link_issues`
  - `link_issues == disabled_links + integrity_issues`

### 3.3 BOQ Item Grouping (Zero-Stage Integrity Under Filters)
Every authorized BOQ Item in the BOQ population belongs to **exactly one** group in `filtered_group`:
- **`no_stages`** (`"No Stages"`, or **`"No visible Stages"`** when caller has partial visibility): Item has `0` authorized Stages in the BOQ population (`total_item_stages == 0`).
- **`filtered_out`** (`"Zero Matching Stages"`): Item has `>= 1` authorized Stage in the BOQ population (`total_item_stages > 0`), but `0` Stages match the active Stage filters (`matching_stages == 0`). **An Item with existing Stages NEVER becomes `no_stages` merely because Stage filters hid its Stages.**
- **`needs_review`** (`"Needs Review"`): `matching_stages >= 1` and `link_issues >= 1`.
- **`full`** (`"Full"`): `matching_stages >= 1`, `link_issues == 0`, `unlinked == 0`.
- **`partial`** (`"Partial"`): `matching_stages >= 1`, `link_issues == 0`, `healthy_linked >= 1`, `unlinked >= 1`.
- **`unmapped`** (`"Unmapped"`): `matching_stages >= 1`, `link_issues == 0`, `healthy_linked == 0`.
- Invariants:
  - `sum(item_group_counts.values()) == population_summary["total_items"] == len(all_item_rows)`
  - `item_group_counts["no_stages"] == population_summary["items_without_stages"] == len(all_no_stages_rows)`
  - `sum(item["matching_stages"] for item in all_item_rows) == summary["total_stages"] == len(all_stage_rows)`

### 3.4 Incompatible Filter Rule (`execution_node` + `mapping_state == "unlinked"`)
- Returns an explicit `filter_conflict` object (`code: "node_with_unlinked"`, localized explanation) with empty matching Stages (`summary.total_stages == 0`, `coverage_pct == None`, `coverage_pct_display == "N/A"`). Items with Stages in the BOQ population report `filtered_group == "filtered_out"` (never `no_stages`).

---

## 4. Authorize Before Aggregation, Query Cost & Population Limits (`W15`)

1. **Chain Enforcement:** Require readable `BOQ Header` -> readable `BOQ Item` -> readable `BOQ Item Stage` via `frappe.get_list` (enforcing `permission_query_conditions`, `User Permission`, `DocShare`, `if_owner`, `boq_parent_query_conditions`, and `scope_query`) **followed by** native `frappe.has_permission(..., "read", doc=...)` on each candidate record before any aggregation, search, grouping, pagination, or export.
2. **Measured Query Cost & Latency:** Because `construction/overrides/boq_permissions.py` reloads stored children and checks parent Headers per document, P3 makes no "zero N+1" claim. Measured on `v16.localhost` (2 BOQ Headers, 21 BOQ Items, 57 Stages):
   - `Administrator`: **6 SQL queries / 167.8 ms**
   - Non-admin `Project Manager` (full project read): **752 SQL queries / 344.2 ms** (~9.6 SQL queries and ~4.4 ms per BOQ Item/Stage record)
   - Restricted `Project Manager` (1 allowed Header, 1 denied Header via `User Permission` on `BOQ Header`; 12 visible Items, 32 visible Stages): **431 SQL queries / 293.5 ms**
3. **Fail-Closed Population Caps (Sized to Measured Non-Admin Cost):**
   - `MAX_POPULATION_HEADERS = 500`, `MAX_POPULATION_STRUCTURES = 5000`, `MAX_POPULATION_ITEMS = 2000`, `MAX_POPULATION_STAGES = 3000`, `MAX_NODES = 10000`.
   - If any population cap is exceeded (including a `BOQ Structure` subtree exceeding `MAX_POPULATION_STRUCTURES`), `get_execution_coverage` returns an explicit fail-closed limit response (`ok: False, limit_exceeded: True, limit_type, limit, message`) asking the caller to narrow BOQ Header/Structure/Item filters — never returning silently incomplete counts — and `export_execution_coverage` refuses export with `ValidationError`.

---

## 5. Deterministic Ordering & Export Parity (`W15`)

- Both paginated views and exports use one deterministic total sort order:
  - Stages: `(boq_header, wbs_code_sort_key, boq_item, stage_code, name)`
  - Items / No Stages: `(boq_header, wbs_code_sort_key, name)`
- `export_execution_coverage` (`GET`, `export_format` in `{"csv", "xlsx"}`, `view_mode` in `{"stages", "items", "no_stages"}`):
  - Capped at `EXPORT_MAX = 2000` rows.
  - Embeds report metadata **inside both CSV and XLSX downloads**: Project, View, Exported Rows, Total Matching Rows, Truncated (`Yes`/`No`), Truncation Notice (when truncated), Summary counts + Mapping Completeness, and the non-financial disclaimer.
  - CSV and XLSX are generated from the exact same `build_export_table(...)` structure: identical rows, identical order, identical columns.
  - Text cells are sanitized via `sanitize_spreadsheet_value`; quantity and count cells remain numeric (`int`/`float` in XLSX, unquoted numeric formatting in CSV).
  - Streams directly via `frappe.response["type"] = "download"` — **zero `File` records created**.

---

## 6. Phased Delivery

- **Slice 1:** `execution_coverage_rules.py`, `execution_coverage.py`, `execution_coverage_api.py`, Slice 1 `ar.po` entries, `tests_offline/test_execution_coverage_rules.py`, and disposable-lab live verification (including mixed-permission parity, query cost/latency measurement, zero-write proof, and limit-exceeded proof).
- **Slice 2:** Bilingual EN/AR `execution-coverage` Frappe Page, P1 `execution_breakdown.js` **View Coverage** drilldown, Node JS UI tests, disposable-lab Frappe Desk acceptance, and Stage-2 localization evidence refresh.
