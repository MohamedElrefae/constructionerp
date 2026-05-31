# Coding Patterns — Quick Reference

> **Canonical source:** `docs/ai/CODING_PATTERNS.md`  
> This file provides quick-start templates. For full anti-patterns and detailed explanations, read the canonical file.

---

## 1. API Endpoint

```python
import frappe
from frappe import _

@frappe.whitelist()
def my_endpoint(param: str | None = None) -> dict:
    """Docstring."""
    param = param or frappe.session.user
    return {"status": "ok", "data": result}
```

## 2. Parameterized SQL (Mandatory)

```python
# ✅ CORRECT
results = frappe.db.sql(
    """
    SELECT name, cost_item, quantity
    FROM `tabBOQ Item`
    WHERE boq_header = %(boq_header)s
      AND docstatus < 2
    """,
    {"boq_header": boq_header},
    as_dict=True,
)

# ❌ NEVER
results = frappe.db.sql(
    f"SELECT * FROM `tabBOQ Item` WHERE boq_header = '{boq_header}'",
    as_dict=True,
)
```

## 3. BOQ Item Creation

```python
doc = frappe.new_doc("BOQ Item")
doc.boq_header = boq_header
doc.structure = structure              # Link → BOQ Structure
doc.cost_item = item_data.get("cost_item", "")  # Data — free text!
doc.item_type = item_data.get("item_type", "Measured Work")
doc.quantity = item_data.get("quantity", 0.0)
doc.unit = item_data.get("unit")       # Link → UOM
doc.est_unit_cost = item_data.get("est_unit_cost", 0.0)
doc.contract_unit_price = item_data.get("contract_unit_price", 0.0)
doc.insert(ignore_permissions=False)
```

## 4. NestedSet Subtree Query

```python
structure = frappe.get_doc("BOQ Structure", structure_name)
return frappe.db.sql("""
    SELECT bi.name, bi.cost_item, bi.quantity, bi.unit,
           bi.est_unit_cost, bi.contract_unit_price, bi.line_total,
           bs.wbs_code, bs.title AS wbs_title
    FROM `tabBOQ Item` bi
    JOIN `tabBOQ Structure` bs ON bi.structure = bs.name
    WHERE bs.lft >= %(lft)s
      AND bs.rgt <= %(rgt)s
      AND bi.docstatus < 2
    ORDER BY bs.lft, bi.cost_item
""", {"lft": structure.lft, "rgt": structure.rgt}, as_dict=True)
```

## 5. Theme Write (Avoid TimestampMismatchError)

```python
# ✅ CORRECT
frappe.db.set_value(
    "User Desk Theme",
    user,
    "theme",
    new_theme,
    update_modified=False,
)

# ❌ WRONG for hot-path
# doc = frappe.get_doc("User Desk Theme", user)
# doc.theme = new_theme
# doc.save()
```

## 6. Scope Query Injection

```python
def add_scope_conditions(user: str, doctype: str) -> str:
    if user == "Administrator":
        return ""  # Admin bypass — always first
    if doctype in SYSTEM_DOCTYPES:
        return ""
    # ... rest of logic
```

## 7. Adding a CSS File

```python
# In hooks.py
app_include_css = [
    # ... existing ...
    "/assets/construction/css/my_feature.css?v=1.0",
]
```

```bash
cd /home/mohamed/frappe-bench
bench build --app construction
# OR
bench clear-cache
```

**Important:** Only 6 CSS files are currently in `app_include_css`. Generated/login/email/print themes load conditionally — do not add them blindly.

## 8. JS DOM Selector (Dual v15/v16)

```javascript
const navbar = document.querySelector('.navbar')
    || document.querySelector('[data-page-route] .navbar');
```

## 9. CSS Variable Override

```css
html.ct-enterprise[data-theme="dark"] {
    --primary: #3498db !important;
    --bg: #1a1a1a !important;
}
```

---

## Anti-Patterns

| Don't | Why | Do Instead |
|-------|-----|------------|
| `f"SELECT ... WHERE x = '{var}'"` | SQL injection | Parameterized queries only |
| `doc.save()` for theme prefs | TimestampMismatchError | `frappe.db.set_value(..., update_modified=False)` |
| Add CSS without `hooks.py` | File never loads | Register in `app_include_css` + bump `?v=` |
| Assume `item_code` on BOQ Item | Schema mismatch — field doesn't exist | Use `cost_item` (Data) |
| Test scope as Administrator | Admin bypasses all filters | Use non-admin test user |
| Register all 22 CSS files | Generated files conflict | Only register production files (currently 6) |

---

*For full explanations and more patterns, see `docs/ai/CODING_PATTERNS.md`.*
