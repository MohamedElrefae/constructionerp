# Senior Engineer Status Report — In-Progress Features

> **To:** Mohamed Elrefae, Construction ERP Lead  
> **From:** Senior Engineering Review  
> **Date:** 2026-05-31  
> **Branch:** `feature/vite-ui-v1` (HEAD `087d3f5`)  
> **Scope:** Form Layout Engine Phase 3+ & BOQ Accounting Integration  

---

## Executive Summary

Two features are currently flagged **In Progress** on branch `feature/vite-ui-v1`. This report provides a forensic audit of what is **COMPLETE**, what is **MISSING**, what is **BLOCKED**, and the **individual delivery plan** required to move each feature to a stable, production-ready state before any next-stage work begins.

| Feature | Status | Completeness | Risk Level |
|---------|--------|-------------|------------|
| **Form Layout Engine — Phase 3+** | 🟡 In Progress | Phase 1+2 done (~65%). Phase 3+ scattered, no tests. | **HIGH** — stale presets, duplicate attach, zero test coverage, disconnected React system |
| **BOQ Accounting Integration** | 🟡 In Progress | Phase 1 (Attribution Layer) done (~80%). Phase 2+ (GL/Invoice/Cost Tracking) not started. | **MEDIUM** — solid foundation, well-tested, but critical gaps in actual accounting flow |

---

## Part A — Form Layout Engine (Phase 3+)

### A.1 Feature Overview

A database-backed form layout system that allows role-based, workflow-first rearrangement of Frappe form fields without modifying DocType JSON. Two independent systems currently coexist in the codebase:

1. **Database-backed Frappe Overlay** (`Form Layout Profile` → `layout_api.py` → `vfc_layout_engine.js`)
2. **React Modern Form** (`modern_form_api.py` → `UnifiedCRUDForm.jsx` → `FormLayoutControls.jsx`) — stored in `localStorage`, not wired to the database profile system

### A.2 What Is COMPLETE (Phase 1+2) ✅

| Component | File(s) | Lines | Evidence |
|-----------|---------|-------|----------|
| Form Layout Profile DocType | `doctype/form_layout_profile/` | 160 | 12 fields, validation, guards |
| REST API (CRUD + validation) | `api/layout_api.py` | 274 | 5 endpoints |
| Modern Form API (parallel) | `api/modern_form_api.py` | 431 | 7 endpoints |
| Runtime Layout Engine | `public/js/vfc_layout_engine.js` | 847 | Re-parents native Frappe wrappers |
| Form Config Panel | `public/js/vite_layout_controls.js` | 1,314 | 4-tab slide-in panel |
| React Modern Form | `components/UnifiedCRUDForm.jsx` | 307 | Hybrid create/edit/view |
| React Layout Controls | `components/FormLayoutControls.jsx` | 294 | Columns, visibility, drag-drop |
| React Field Renderer | `components/FormField.jsx` | 293 | Searchable selects |
| Draggable Panel | `components/DraggablePanel.jsx` | 263 | Generic drag/resize |
| Section Card CSS | `public/css/vfc_sections.css` | 177 | Scoped `.vfc-le-*` styles |
| Vite Form Override CSS | `public/css/vite_form_override.css` | 935 | Full UI skin |
| Hooks Registration | `hooks.py` | — | JS/CSS assets registered |

**Total frontend code:** ~4,283 lines JS/JSX + ~1,112 lines CSS  
**Total backend code:** ~865 lines Python

### A.3 What Is MISSING / BROKEN / TODO (Phase 3+) 🟡🔴

| # | Issue | Severity | File(s) | Details |
|---|-------|----------|---------|---------|
| 1 | **Stale BOQ Item Presets** | 🔴 High | `vite_layout_controls.js` | Preset references `wbs_code`, `title`, `type`, `stage` — actual DocType uses `structure`, `item_type`, `cost_item`, etc. |
| 2 | **Stale BOQ Item Stage Presets** | 🔴 High | `vite_layout_controls.js` | References `completion_percentage`, `remarks` — actual fields are `percent_complete`, `description` |
| 3 | **Duplicate Attachment Path** | 🟡 Medium | `boq_header.js`, `boq_item.js`, `vite_layout_controls.js` | Global attach via `frappe.ui.form.on("*")` AND manual `frappe.require` in DocType controllers. Choose one. |
| 4 | **No Unknown-Field Guard** | 🟡 Medium | `vite_layout_controls.js` | Presets reference non-existent fields silently. Should log once and skip. |
| 5 | **Pilot Gate Still Active** | 🟡 Medium | `vfc_layout_engine.js:32` | Hard-coded to `BOQ Header` and `BOQ Item` only. Comment says "Phase 5: remove gate". |
| 6 | **No Tests** | 🔴 High | *None exist* | Zero test coverage for Form Layout Profile, layout_api, or vfc_layout_engine. |
| 7 | **No Seeded Role Profiles** | 🟡 Medium | — | Team letter Step 3 (Manager, Engineer, Accountant views) not implemented. |
| 8 | **Missing `for_user` Field** | 🟡 Medium | `form_layout_profile.json` | Team letter recommended personal overrides; not in schema. |
| 9 | **Disconnected React System** | 🟡 Medium | `UnifiedCRUDForm.jsx`, `modern_form_api.py` | React form stores layout in `localStorage`, never reads/writes `Form Layout Profile`. Two parallel universes. |
| 10 | **Ghost File Reference** | 🟢 Low | `layout_api.py:6-7` | Docstring references `vfc_sections_tab.js` which does not exist. |
| 11 | **No `is_progress_billing` Logic** | 🟡 Medium | `hooks.py` custom fields | Field exists on Sales Invoice Item but no code consumes it. *(Overlaps with BOQ Accounting)* |

### A.4 Root Cause Analysis

The core problem is **technical debt accumulation between two parallel systems**:

- The **Frappe Overlay** system (database-backed, pilot-gated, no tests) was built first.
- The **React Modern Form** system (localStorage-backed, more polished UI, also no tests) was built second without integrating with the first.
- Both systems have stale presets because BOQ Item schema evolved after presets were written.
- Neither system has automated validation that would catch stale field references.

### A.5 Individual Delivery Plan — Form Layout Engine

**Goal:** Stabilize the existing system, choose ONE architecture, and make it production-ready before expanding to new DocTypes.

#### Phase A.5.1 — Stabilization (Days 1–3)
*Prerequisite for everything else. Do NOT skip.*

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 1 | Fix stale presets | Updated `vite_layout_controls.js` | BOQ Item preset uses actual fieldnames from `boq_item.json`. BOQ Item Stage preset uses actual fieldnames from `boq_item_stage.json`. |
| 1 | Add unknown-field guard | Updated `vite_layout_controls.js` | Non-existent preset fields are logged once to console (not thrown) and skipped. Form still renders. |
| 2 | Resolve duplicate attach | Updated `boq_header.js`, `boq_item.js`, `vite_layout_controls.js` | Single attachment path chosen (recommend: global from `hooks.py` + registry-based DocType behavior). No duplicate UI. |
| 2–3 | Write tests for layout engine | New test files | `test_form_layout_profile.py` — validation rules, `is_system` guard, `is_default` uniqueness. `test_layout_api.py` — CRUD endpoints, permission checks. Minimum 80% coverage on Python. |

#### Phase A.5.2 — Architecture Decision (Day 4)
*Choose one system. Do NOT maintain two.*

| Decision | Option A: Frappe Overlay | Option B: React Modern Form |
|----------|--------------------------|----------------------------|
| **Pros** | Native Frappe controls preserved; permissions/validation/mandatory rules work automatically; database persistence; role-based targeting | Better UX; modern React; cleaner component model; already has drag-drop |
| **Cons** | DOM manipulation is brittle; MutationObserver overhead; harder to test | Must re-implement Frappe field behaviors (permissions, mandatory, link queries, child tables); localStorage persistence is user-local only |
| **Recommendation** | **Choose Option A** for production. Deprecate React system or re-implement it as a *reader* of Form Layout Profile (not a parallel writer). |

**Deliverable:** ADR documenting the decision and deprecation plan for the non-chosen system.

#### Phase A.5.3 — Pilot Gate Removal + Expansion (Days 5–7)

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 5 | Remove pilot gate | Updated `vfc_layout_engine.js` | `PILOT_DOCTYPES` array removed or made configurable. Engine activates for ANY DocType that has an active `Form Layout Profile`. |
| 5 | Add `for_user` field | Updated `form_layout_profile.json` + controller | Personal override profiles work. Priority: `for_user` > `for_role` > `is_default`. |
| 6 | Add fallback for missing profiles | Updated `vfc_layout_engine.js` | If no profile matches, form renders natively (no overlay). No console errors. |
| 6–7 | Expand to 3+ new DocTypes | New `Form Layout Profile` records | Create and test profiles for: `Project`, `Cost Item`, `Purchase Order` (or other high-priority DocType). |

#### Phase A.5.4 — Sections Editor Hardening (Days 8–11)

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 8–9 | Sections Tab drag-drop reliability | Updated `vite_layout_controls.js` | Drag-drop works on Chrome, Firefox, Safari. Mobile: up/down buttons as fallback. No data loss on save. |
| 10 | Per-section column count | Updated schema + engine | `column_count` (1–3) respected per section. CSS grid/flex adapts correctly. |
| 11 | Collapsible sections persistence | Updated engine + API | `collapsed_by_default` stored in profile. User toggle state remembered per session (localStorage). |

#### Phase A.5.5 — Seeded Profiles + Documentation (Days 12–14)

| Day | Task | Deliverable |
|-----|------|-------------|
| 12 | Seed role profiles | JSON fixtures or patch: BOQ Header (Default, Manager, Engineer), BOQ Item (Default, Engineer Workflow, Accountant View), BOQ Item Stage (Default) |
| 13 | User guide | Update `docs/ai/USER_GUIDE.md` with Form Layout section |
| 14 | Final regression | All existing BOQ tests + new layout tests pass. No console errors on form load. |

#### Phase A.5.6 — Summary Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Stabilization | 3 days | Day 3 |
| Architecture Decision | 1 day | Day 4 |
| Pilot Gate Removal + Expansion | 3 days | Day 7 |
| Sections Editor Hardening | 4 days | Day 11 |
| Seeded Profiles + Docs | 3 days | Day 14 |
| **Total** | **14 working days** | |

**Critical Path:** Stabilization → Architecture Decision → Pilot Removal. Everything else depends on these three.

---

## Part B — BOQ Accounting Integration

### B.1 Feature Overview

Integrates the Construction BOQ module with ERPNext accounting. The current implementation is a **Phase 1 Attribution Layer**: ERPNext transactions can be *tagged* with `boq_item` (via Accounting Dimension) and `boq_item_stage` (via custom fields), but the app does not *create* transactions from BOQ nor *read back* financial actuals into BOQ progress/cost tracking.

### B.2 What Is COMPLETE (Phase 1 — Attribution Layer) ✅

| Component | File(s) | Lines | Evidence |
|-----------|---------|-------|----------|
| BOQ Header lifecycle | `boq_header.py` | — | Draft→Pricing→Frozen→Locked with `VALID_TRANSITIONS` |
| BOQ Structure WBS tree | `boq_structure.py`, `wbs_generator.py` | — | NestedSet, auto-WBS codes |
| BOQ Item auto-creation | `boq_structure.py` | — | Leaf structures auto-create BOQ Items |
| BOQ Item pricing/cost | `boq_item.py` | — | 7-step validation pipeline |
| BOQ Header rollups | `boq_header.py` | — | SQL SUM queries |
| BOQ Item Stage DocType | `doctype/boq_item_stage/` | 166 | Full validation, quantity guards |
| Accounting Dimension setup | `install.py::setup_boq_accounting_dimension()` | — | Idempotent, auto-runs on install/migrate |
| Native `boq_item` fields on accounting doctypes | ERPNext `make_dimension_in_accounting_doctypes()` | — | Fields injected into GL Entry, Journal Entry, Sales/Purchase Invoice, etc. |
| Operational custom fields | `install.py::setup_boq_custom_fields()` | — | `boq_item_stage`, `expense_category`, `is_progress_billing`, cascade Link fields on 8 child doctypes |
| Transaction validation hooks | `services/boq_transaction_validation.py` | 185 | 8 doctypes validated on `validate` event |
| BOQ lifecycle guards | `services/boq_lifecycle.py` | — | Prevents deletion of referenced stages |
| Scope filters | `services/boq_scope_filters.py` | — | SQL-aware scope builders |
| Idempotent install/migrate | `hooks.py` | — | `after_install`, `after_migrate` |
| Direct labor designations | `install.py::setup_direct_labor_designations()` | — | — |
| BOQ cascade filtering | `construction_settings.js` | — | Off/On/Strict modes |
| **Tests** | | | |
| Transaction validation tests | `tests/test_transaction_validation.py` | 185 | Valid/invalid rows, status blocking, project mismatch, stage ownership |
| Accounting dimension tests | `tests/test_accounting_dimension.py` | 33 | Idempotency, field existence, no duplicates |
| BOQ Item Stage tests | `tests/test_boq_item_stage.py` | 166 | Creation, quantity guards, percent bounds, distribution rules |
| Hook regression tests | `tests/test_hook_regression.py` | 31 | Wildcard scope preserved, 8 doctypes hooked |
| BOQ integration tests | `tests/test_boq_integration.py` | 278 | Tree creation, auto-creation, rollups, WBS, import/export |
| Property tests | `doctype/boq_item/test_boq_item_properties.py` | — | Property-based validation |
| ADR | `docs/ADR-001-accounting-dimension.md` | — | Design rationale, Phase 2 migration path |

**Total backend code:** ~2,500+ lines Python (services + controllers + tests)  
**Total test code:** ~693 lines

### B.3 What Is MISSING / TODO (Phase 2+) 🟡🔴

| # | Issue | Severity | File(s) | Details |
|---|-------|----------|---------|---------|
| 1 | **`cost_item` is Data, not Link** | 🟡 Medium | `boq_item.json` | Free text placeholder. Comment says: *"Will be converted to Link when CostItem DocType is deployed."* CostItem exists but is a skeleton. |
| 2 | **CostItem DocType is incomplete** | 🟡 Medium | `doctype/cost_item/` | Has fields (`total_direct_cost`, `base_productivity`, `default_wastage_pct`) but no controller logic, no accounting integration. |
| 3 | **`quantity_executed` / `quantity_certified` hidden, unwritten** | 🔴 High | `boq_item.json` | Fields exist (`hidden: 1`, `read_only: 1`). **No code writes to them** from transactions. Core metric for cost tracking is dead data. |
| 4 | **`is_progress_billing` field exists, no logic** | 🟡 Medium | `hooks.py` custom fields on `Sales Invoice Item` | Field added to Sales Invoice Item. No backend code creates invoices or links them to BOQ progress. |
| 5 | **NO GL Entry generation from BOQ** | 🔴 High | *None exist* | No code creates GL Entries. No cost posting. No budget-vs-actual. |
| 6 | **NO Invoice creation from BOQ** | 🔴 High | *None exist* | No code creates Sales Invoice, Purchase Invoice, or Journal Entry from BOQ data. |
| 7 | **NO Cost tracking / actuals vs budget** | 🔴 High | *None exist* | No service queries `tabGL Entry` or transaction tables to aggregate actual costs against `boq_item`. |
| 8 | **NO BOQ Cost Variance Report** | 🟡 Medium | Deferred per plan | Implementation plan Stage 8 says: *"Do not build reports in first implementation."* |
| 9 | **NO IPC / Progress Billing** | 🟢 Low | Out of scope per requirements | Explicitly listed as out of scope. |
| 10 | **NO Budget overrun blocking** | 🟡 Medium | — | Requirements say: *"First implementation should avoid blocking budget overruns. Checks should be warnings only unless a later setting makes them blocking."* |
| 11 | **NO Cost Code dimension (Phase 2)** | 🟢 Low | Deferred per ADR-001 | ADR-001: Phase 2 if performance degrades with thousands of BOQ Items. |
| 12 | **NO automatic progress updates** | 🟢 Low | Explicitly forbidden | Requirements: *"Stock Entry quantities must not be written directly into BOQ executed quantity."* |
| 13 | **BOQ Item mandatory on transactions — UNRESOLVED** | 🟡 Medium | — | Open decision from implementation plan Stage 10, item 6. Currently optional. |
| 14 | **Accounting Dimension mandatory rules — UNRESOLVED** | 🟡 Medium | — | Open decision from implementation plan Stage 10, item 7. Currently deferred. |

### B.4 Root Cause Analysis

The BOQ Accounting Integration is **architecturally sound but functionally incomplete**. The Phase 1 attribution layer was designed correctly (idempotent setup, server-side validation, proper hooks), but the team stopped at "transactions can reference BOQ" without building "BOQ can drive transactions or track their results."

The missing pieces form a natural Phase 2 pipeline:

```
BOQ Item (budget)  →  Transaction creation  →  GL Entry posting  →  Actual cost reading  →  Variance calculation
        ✅ Done             ❌ Missing            ❌ Missing           ❌ Missing              ❌ Missing
```

### B.5 Individual Delivery Plan — BOQ Accounting Integration

**Goal:** Complete the accounting loop: BOQ drives transactions, transactions post to GL, GL actuals are read back into BOQ for variance tracking.

#### Phase B.5.1 — Foundation Completion (Days 1–4)
*Close open decisions and fix placeholder fields before building on top.*

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 1 | Resolve open decisions | Updated `docs/boq_integration_requirements.md` | Document final decisions: (a) BOQ Item mandatory? (b) Accounting Dimension mandatory rules? (c) Budget overrun warnings vs blocking? |
| 1–2 | Convert `cost_item` to Link | Updated `boq_item.json` + migration | `cost_item` is Link → `CostItem`. Existing Data values migrated or flagged for manual cleanup. |
| 2–3 | Complete CostItem DocType | Updated `doctype/cost_item/` | Controller validates `total_direct_cost` ≥ 0, `default_wastage_pct` 0–100. Link from BOQ Item works. Tests added. |
| 4 | Populate `quantity_executed` from transactions | Updated `services/boq_transaction_validation.py` + new service | When a transaction with `boq_item` is submitted, `quantity_executed` on BOQ Item is updated (Sum of Stock Entry + Purchase Receipt + Timesheet quantities). Read-only, server-side only. |

#### Phase B.5.2 — Transaction Creation from BOQ (Days 5–9)

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 5–6 | Purchase Order from BOQ | New `services/boq_procurement.py` | Button on BOQ Item: "Create Purchase Order". PO created with `boq_item` dimension populated. Line total must not exceed BOQ line total (warning, not block). |
| 6–7 | Sales Invoice (Progress Billing) from BOQ | Updated `services/boq_accounting.py` | Button on BOQ Item / Stage: "Create Progress Invoice". Uses `is_progress_billing` flag. Invoice amount = certified quantity × contract unit price. |
| 7–8 | Journal Entry for overhead/profit adjustment | New `services/boq_journal.py` | Button on BOQ Header: "Post Overhead/Profit Adjustment". JE created distributing overhead and profit amounts to configured accounts. |
| 8–9 | Stock Entry for material issue | Updated `services/boq_procurement.py` | Button on BOQ Item: "Issue Materials". Stock Entry (Material Issue) created with `boq_item` dimension. |

#### Phase B.5.3 — GL Entry Reading + Cost Tracking (Days 10–13)

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 10–11 | Actual cost aggregation service | New `services/boq_cost_tracking.py` | Function `get_actual_cost_for_boq_item(boq_item)` queries `tabGL Entry` filtered by `boq_item` dimension. Returns: actual cost, actual revenue, WIP balance. |
| 11–12 | Populate `quantity_certified` | Updated `services/boq_cost_tracking.py` | When a Sales Invoice with `is_progress_billing` is submitted, `quantity_certified` on BOQ Item is updated from invoice quantities. |
| 12–13 | Budget variance calculation | New `services/boq_cost_tracking.py` | Function `get_boq_variance(boq_item)` returns: budgeted cost, actual cost, variance amount, variance %. No UI yet — service only. |

#### Phase B.5.4 — Reporting + UI (Days 14–17)

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 14–15 | BOQ Cost Variance Report | New report `boq_cost_variance` | ERPNext Report or Script Report. Columns: BOQ Item, Budgeted Cost, Actual Cost, Variance, Variance %. Filterable by Project, BOQ Header, Date Range. |
| 15–16 | BOQ Stage Operational Report | New report `boq_stage_operational` | Columns: Stage, Planned Qty, Executed Qty, Certified Qty, Percent Complete. Filterable by BOQ Item, Project. |
| 16–17 | Dashboard cards on BOQ Header | Updated `boq_header.js` + `boq_header_dashboard.py` | Cards showing: Total Contract Value, Total Actual Cost, Overall Variance %, Progress %. Refreshes on load. |

#### Phase B.5.5 — Hardening + Tests (Days 18–20)

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| 18 | Budget overrun warnings | Updated `services/boq_transaction_validation.py` | When transaction would cause actual cost > budgeted cost, frappe.msgprint warning (not block). Configurable: `construction_settings.boq_budget_overrun_block` (default: warn). |
| 18–19 | Write tests for new services | New test files | `test_boq_procurement.py`, `test_boq_accounting.py`, `test_boq_cost_tracking.py`. Minimum 80% coverage on new Python. |
| 19–20 | Regression run | All tests | All existing tests pass. New tests pass. No duplicate custom fields after migrate. |

#### Phase B.5.6 — Summary Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Foundation Completion | 4 days | Day 4 |
| Transaction Creation from BOQ | 5 days | Day 9 |
| GL Reading + Cost Tracking | 4 days | Day 13 |
| Reporting + UI | 4 days | Day 17 |
| Hardening + Tests | 3 days | Day 20 |
| **Total** | **20 working days** | |

**Critical Path:** Foundation Completion → Transaction Creation → GL Reading. Reports are useless without actual data flowing.

---

## Part C — Cross-Cutting Concerns & Dependencies

### C.1 Shared Risk: `quantity_executed` / `quantity_certified`

Both features touch these fields:
- **Form Layout Engine:** These fields are `hidden: 1` on BOQ Item. If Phase 3+ makes them visible, they need data.
- **BOQ Accounting:** These fields need to be populated from transactions.

**Recommendation:** BOQ Accounting Phase B.5.1 (Day 4) must complete before Form Layout Phase A.5.3 (Day 5–7) shows these fields. Sequence accordingly.

### C.2 Shared Risk: `is_progress_billing`

- Added as custom field by BOQ Accounting (Phase 1, done).
- Consumed by BOQ Accounting Phase B.5.2 (Day 6–7).
- **Form Layout Engine** may need to show/hide this field conditionally.

### C.3 Branch Strategy Recommendation

| Feature | Recommended Branch | Reason |
|---------|-------------------|--------|
| Form Layout Engine Phase 3+ | `feature/form-layout-phase3` | Isolated from accounting changes; can ship independently |
| BOQ Accounting Phase 2+ | `feature/boq-accounting-phase2` | Heavy ERPNext integration; needs separate QA cycle |

Both can merge back to `feature/vite-ui-v1` only after independent QA passes.

### C.4 QA Gate Criteria Before Next Stages

**Form Layout Engine may proceed to next stage ONLY when:**
1. All stale presets fixed
2. Unknown-field guard active
3. Duplicate attach resolved
4. Test coverage ≥ 80% on Python backend
5. Pilot gate removed OR replaced with configurable allowlist
6. Architecture ADR approved (Frappe Overlay vs React)

**BOQ Accounting may proceed to next stage ONLY when:**
1. `cost_item` is Link (not Data)
2. CostItem DocType has controller logic
3. `quantity_executed` populates from transactions
4. Open decisions documented (mandatory rules, budget overrun behavior)
5. All new services have tests ≥ 80% coverage
6. Existing tests still pass

---

## Part D — File Reference Quick Map

### Form Layout Engine

| Purpose | Path |
|---------|------|
| DocType | `construction/doctype/form_layout_profile/` |
| REST API | `construction/api/layout_api.py` |
| Modern Form API | `construction/api/modern_form_api.py` |
| Runtime Engine | `construction/public/js/vfc_layout_engine.js` |
| Config Panel | `construction/public/js/vite_layout_controls.js` |
| React Form | `construction/public/js/components/UnifiedCRUDForm.jsx` |
| React Controls | `construction/public/js/components/FormLayoutControls.jsx` |
| React Field | `construction/public/js/components/FormField.jsx` |
| Draggable Panel | `construction/public/js/components/DraggablePanel.jsx` |
| Section CSS | `construction/public/css/vfc_sections.css` |
| Override CSS | `construction/public/css/vite_form_override.css` |
| Team Letter | `docs/form_layout_engine_team_letter.md` |

### BOQ Accounting Integration

| Purpose | Path |
|---------|------|
| BOQ Header | `construction/doctype/boq_header/` |
| BOQ Item | `construction/doctype/boq_item/` |
| BOQ Structure | `construction/doctype/boq_structure/` |
| BOQ Item Stage | `construction/doctype/boq_item_stage/` |
| CostItem | `construction/doctype/cost_item/` |
| Accounting Dimension Setup | `construction/install.py` |
| Transaction Validation | `construction/services/boq_transaction_validation.py` |
| BOQ Accounting Service | `construction/services/boq_accounting.py` |
| BOQ Lifecycle Guards | `construction/services/boq_lifecycle.py` |
| Scope Filters | `construction/services/boq_scope_filters.py` |
| Requirements | `docs/boq_integration_requirements.md` |
| Implementation Plan | `docs/boq_integration_implementation.md` |
| ADR | `docs/ADR-001-accounting-dimension.md` |
| Tests | `construction/tests/test_*.py` |

---

*Report generated from live codebase audit. All file paths and line counts accurate as of commit `087d3f5`.*
