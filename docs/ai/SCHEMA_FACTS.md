# Schema Facts — Verified DocType Schemas

> **Rule:** This file is generated from live DocType JSON. If a schema changes, update this file.
> 
> Last verified: 2026-05-31 by `ai_context_check.py`

---

## BOQ Item (`boq_item.json`) — 33 fields

**CRITICAL WARNING:** BOQ Item has **NO** `item_code` or `item_name`. It uses `cost_item` (Data — free text).

| Field | Type | Notes |
|-------|------|-------|
| `structure` | Link → BOQ Structure | WBS node |
| `boq_header` | Link → BOQ Header | Master document |
| `item_type` | Select | Measured Work / Provisional Sum / Prime Cost / Daywork / Contingency / TBD |
| `cost_item` | Data | **Free text, NOT Link→Item** |
| `owner_page` | Data | |
| `owner_ref_no` | Data | |
| `owner_file_ref` | Data | |
| `quantity` | Float | |
| `unit` | Link → UOM | |
| `factor` | Float | |
| `has_stages` | Check | |
| `est_unit_cost` | Currency | |
| `est_unit_price` | Currency | |
| `contract_unit_price` | Currency | |
| `line_total` | Currency | |
| `overhead_pct` | Percent | |
| `profit_pct` | Percent | |
| `overhead_amount` | Currency | |
| `profit_amount` | Currency | |
| `calculated_sell_price` | Currency | |
| `est_line_total` | Currency | |
| `quantity_executed` | Float | |
| `quantity_certified` | Float | |

---

## BOQ Structure (`boq_structure.json`) — 16 fields

NestedSet tree node for WBS.

| Field | Type | Notes |
|-------|------|-------|
| `title` | Data | |
| `wbs_code` | Data | |
| `parent_structure` | Link → BOQ Structure | |
| `boq_header` | Link → BOQ Header | |
| `project` | Link → Project | |
| `is_group` | Check | |
| `description` | Text | |
| `owner_page` | Data | |
| `owner_ref_no` | Data | |
| `owner_file_ref` | Data | |
| `lft` | Int | NestedSet |
| `rgt` | Int | NestedSet |
| `old_parent` | Link → BOQ Structure | |

---

## BOQ Header (`boq_header.json`) — 11 fields

| Field | Type | Notes |
|-------|------|-------|
| `project` | Link → Project | |
| `boq_type` | Select | Tender / Contract / Variation |
| `status` | Select | Draft / Pricing / Frozen / Locked |
| `version` | Data | |
| `total_contract_value` | Currency | |
| `total_estimated_value` | Currency | |
| `total_budgeted_cost` | Currency | |
| `locked_by` | Link → User | |
| `locked_date` | Datetime | |

---

## CostItem (`cost_item.json`) — 9 fields

| Field | Type | Notes |
|-------|------|-------|
| `cost_item_code` | Data | |
| `category` | Link | |
| `title` | Data | |
| `description` | Text | |
| `unit` | Link → UOM | |
| `base_productivity` | Float | |
| `default_wastage_pct` | Percent | |
| `status` | Select | |
| `total_direct_cost` | Currency | |

---

## PlantResource (`plant_resource.json`) — 5 fields

| Field | Type | Notes |
|-------|------|-------|
| `resource_code` | Data | |
| `equipment_type` | Data | |
| `ownership_cost_hourly` | Currency | |
| `operating_cost_hourly` | Currency | |
| `mobilization_cost` | Currency | |

---

## User Scope Context (`user_scope_context.json`) — 10 fields

| Field | Type | Notes |
|-------|------|-------|
| `user` | Link → User | reqd, unique, autoname |
| `company` | Link → Company | reqd |
| `cost_center` | Link → Cost Center | |
| `project` | Link → Project | |
| `department` | Link → Department | |
| `branch` | Link → Branch | |
| `scope_version` | Int | auto-incremented on save |
| `last_active_at` | Datetime | |
| `client_id` | Data | multi-tab support |

---

## Construction Theme (`construction_theme.json`) — 94 fields

- `theme_name`, `is_active`, `theme_type`
- `primary_color`, `accent_color`
- 40+ color fields across tabs: General / Login / Buttons / Tables / Widgets / Input / Navbar / Footer / Semantic / Preview / Advanced
- `custom_css` (Code field)

---

## Form Layout Profile (`form_layout_profile.json`) — 12 fields

| Field | Type | Notes |
|-------|------|-------|
| `reference_doctype` | Link → DocType | |
| `profile_name` | Data | |
| `enabled` | Check | |
| `is_default` | Check | |
| `is_system` | Check | |
| `for_role` | Link → Role | |
| `priority` | Int | |
| `layout_version` | Int | |
| `sections_json` | Code | JSON blob of sections |

---

## Other DocTypes (Field Counts)

| DocType | Fields | Status |
|---------|--------|--------|
| BOQ Item Stage | 16 | Complete |
| Construction Settings | 13 | Complete |
| Direct Labor Designation | 2 | Complete |
| Modern Theme Settings | 10 | Complete |
| User Desk Theme | 25 | Complete |

---

## Schema Validation Checklist

Before seeding any AI memory, confirm:
- [ ] BOQ Item has `cost_item` (Data) and **no** `item_code`
- [ ] BOQ Structure has `lft`, `rgt`, `old_parent`, `is_group`, `wbs_code`
- [ ] CostItem has `cost_item_code` (not `item_code`)
- [ ] PlantResource has `resource_code`, `equipment_type`, `ownership_cost_hourly`
- [ ] User Scope Context has `scope_version`, `last_active_at`, `client_id`
