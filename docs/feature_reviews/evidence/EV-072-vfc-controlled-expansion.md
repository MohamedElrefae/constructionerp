# EV-072 — VFC Controlled Expansion (WP4)

**Date:** 2026-06-21
**WP:** WP4 — Controlled Expansion
**Branch:** `feat/vfc-phase3-stabilization`

## Changes Applied

### 1. BLOCKED_DOCTYPES Audit
- **File:** `vfc_layout_engine.js:46-96`
- All 35 blocked doctypes now have per-category comments:
  - Frappe core metadata (5)
  - Client/Server scripting (2)
  - Reports, Pages, Print (4)
  - System/internal logs (6)
  - Communication/Notification (3)
  - File/Attachment (1)
  - Workflow (3)
  - Tags (2)
  - Email (2)
  - ToDo (1)
  - i18n (2)
  - System Configuration (6)
- No doctypes added or removed — only documentation improved.

### 2. Seed Verification — BOQ Item Stage
- Verified `DEFAULT_BOQ_ITEM_STAGE_LAYOUT` fieldnames against current `boq_item_stage.json` schema:
  - Identity: `project`, `boq_header`, `boq_structure`, `boq_item`, `stage_code`, `stage_name`, `stage_status` — all confirmed
  - Quantities: `planned_qty`, `percent_complete`, `measured_executed_qty`, `certified_qty` — all confirmed
  - Notes: `description` — confirmed
- All 12 seed fieldnames are valid. No stale references.

### 3. DEFAULT_PROJECT_LAYOUT Added
- **File:** `install.py` (new dict + seed registration)
- Sections:
  - Project Identity (4 fields): `project_name`, `status`, `project_type`, `percent_complete`
  - Schedule (2 fields): `expected_start_date`, `expected_end_date`
  - Costing (4 fields): `estimated_costing`, `total_sales_amount`, `total_purchase_cost`, `gross_margin`
- Registered in `seed_form_layout_profiles()` with `is_system=1`
- Will be skipped if the `Project` DocType is not registered on the target site (graceful fallback via `frappe.db.exists` check)

### 4. Native Fallback Verified
- No code change needed — the engine already returns `None` from `get_active_layout` and `_fetchProfile` when no profile is configured, resulting in a no-op (`vfc_layout_engine.js:185-204`).
