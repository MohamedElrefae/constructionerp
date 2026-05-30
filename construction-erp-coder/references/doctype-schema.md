# DocType Schema Reference

> **Canonical source:** `docs/ai/SCHEMA_FACTS.md`  
> This file provides quick lookups. For full verified schemas, read the canonical file.

---

## Critical Schema Warning

**BOQ Item does NOT have `item_code` or `item_name`.**  
It uses `cost_item` (Data — free text field).  
BOQ items are specification lines, not ERPNext Items.

---

## Quick Reference Table

| DocType | Fields | Key Identifier | Status |
|---------|--------|----------------|--------|
| BOQ Item | 33 | `cost_item` (Data) | ✅ Complete |
| BOQ Structure | 16 | `wbs_code` (Data), NestedSet `lft`/`rgt` | ✅ Complete |
| BOQ Header | 11 | `project` (Link), `boq_type`, `status` | ✅ Complete |
| BOQ Item Stage | 16 | — | ✅ Complete |
| CostItem | 9 | `cost_item_code` (Data) | 🔶 Partial |
| PlantResource | 5 | `resource_code` (Data) | 🔶 Partial |
| User Scope Context | 10 | `user` (Link), `scope_version` | ✅ Complete |
| Construction Theme | 94 | `theme_name`, `is_active`, `primary_color` | ✅ Complete |
| User Desk Theme | 25 | `user` (Link), theme + typography prefs | ✅ Complete |
| Modern Theme Settings | 10 | `default_theme` | ✅ Complete |
| Form Layout Profile | 12 | `reference_doctype`, `sections_json` | ✅ Complete |
| Construction Settings | 13 | scope context toggles | ✅ Complete |
| Direct Labor Designation | 2 | — | ✅ Complete |
| Journal Entry (override) | — | JS override only | 🔶 Stub |

---

## Important Field Notes

### BOQ Item (33 fields)
- `structure` → Link to BOQ Structure (WBS node)
- `cost_item` → Data (free text, **not** Link to Item)
- `item_type` → Select: Measured Work / Provisional Sum / Prime Cost / Daywork / Contingency / TBD
- `unit` → Link to UOM
- `est_unit_cost`, `est_unit_price`, `contract_unit_price` → Currency
- `overhead_pct`, `profit_pct` → Percent
- `quantity_executed`, `quantity_certified` → Float (progress tracking)

### BOQ Structure (16 fields)
- `parent_structure` → self-referential Link
- `lft`, `rgt` → Int (NestedSet)
- `old_parent` → Link (NestedSet bookkeeping)
- `is_group` → Check
- `wbs_code` → Data

### CostItem (9 fields)
- `cost_item_code` → Data (**not** `item_code`)
- `category` → Link
- `base_productivity` → Float
- `default_wastage_pct` → Percent
- `total_direct_cost` → Currency

### PlantResource (5 fields)
- `resource_code` → Data
- `equipment_type` → Data
- `ownership_cost_hourly`, `operating_cost_hourly`, `mobilization_cost` → Currency

---

## Schema Validation

Before acting on schema assumptions, confirm with:

```bash
cd /home/mohamed/frappe-bench/apps/construction
python3 scripts/ai_context_check.py
```

This validates that critical fields (`cost_item`, `lft`/`rgt`, etc.) match expectations.

---

*For full JSON-derived schema details, see `docs/ai/SCHEMA_FACTS.md`.*
