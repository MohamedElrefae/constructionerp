# Coding Patterns — Construction ERP

> Canonical patterns derived from the live codebase. Use these as starting templates.

---

## 1. Python Patterns

### 1.1 API Endpoint (Whitelisted)

```python
import frappe
from frappe import _


@frappe.whitelist()
def my_api_endpoint(param: str | None = None) -> dict:
    """Docstring describing what this does."""
    param = param or frappe.session.user
    # ... logic ...
    return {"status": "ok", "data": result}
```

### 1.2 Parameterized SQL Query (Mandatory)

```python
# ✅ CORRECT — parameterized
results = frappe.db.sql(
    """
    SELECT name, cost_item, quantity, unit
    FROM `tabBOQ Item`
    WHERE boq_header = %(boq_header)s
      AND docstatus < 2
    ORDER BY cost_item
    """,
    {"boq_header": boq_header},
    as_dict=True,
)

# ❌ WRONG — never do this
results = frappe.db.sql(
    f"SELECT * FROM `tabBOQ Item` WHERE boq_header = '{boq_header}'",
    as_dict=True,
)
```

### 1.3 BOQ Item Creation (Correct Schema)

```python
import frappe
from frappe import _


@frappe.whitelist()
def create_boq_item(boq_header: str, structure: str, item_data: dict) -> str:
    """Create a BOQ Item under the given Structure node."""
    doc = frappe.new_doc("BOQ Item")
    doc.boq_header = boq_header
    doc.structure = structure              # Link → BOQ Structure
    doc.cost_item = item_data.get("cost_item", "")  # Data — free text!
    doc.item_type = item_data.get("item_type", "Measured Work")
    doc.quantity = item_data.get("quantity", 0.0)
    doc.unit = item_data.get("unit")       # Link → UOM
    doc.est_unit_cost = item_data.get("est_unit_cost", 0.0)
    doc.contract_unit_price = item_data.get("contract_unit_price", 0.0)
    doc.overhead_pct = item_data.get("overhead_pct", 0.0)
    doc.profit_pct = item_data.get("profit_pct", 0.0)
    doc.insert(ignore_permissions=False)
    return doc.name
```

### 1.4 BOQ Subtree Query (NestedSet)

```python
def get_boq_subtree(structure_name: str) -> list[dict]:
    """Get all BOQ Items under a WBS node using NestedSet."""
    structure = frappe.get_doc("BOQ Structure", structure_name)
    return frappe.db.sql(
        """
        SELECT
            bi.name, bi.cost_item, bi.quantity, bi.unit,
            bi.est_unit_cost, bi.contract_unit_price, bi.line_total,
            bs.wbs_code, bs.title AS wbs_title
        FROM `tabBOQ Item` bi
        JOIN `tabBOQ Structure` bs ON bi.structure = bs.name
        WHERE bs.lft >= %(lft)s
          AND bs.rgt <= %(rgt)s
          AND bi.docstatus < 2
        ORDER BY bs.lft, bi.cost_item
        """,
        {"lft": structure.lft, "rgt": structure.rgt},
        as_dict=True,
    )
```

### 1.5 Theme Write (Avoid TimestampMismatchError)

```python
# ✅ CORRECT — bypass optimistic locking for high-frequency updates
frappe.db.set_value(
    "User Desk Theme",
    user,
    "theme",
    new_theme,
    update_modified=False,
)

# ❌ WRONG for hot-path updates — causes TimestampMismatchError
# doc = frappe.get_doc("User Desk Theme", user)
# doc.theme = new_theme
# doc.save()
```

### 1.6 Scope Context Query Injection Pattern

```python
# In overrides/scope_query.py
def add_scope_conditions(user: str, doctype: str) -> str:
    """Inject scope WHERE clause. Called via permission_query_conditions hook."""
    if user == "Administrator":
        return ""  # Admin bypass — always first check
    if doctype in SYSTEM_DOCTYPES:
        return ""
    # ... rest of logic ...
```

### 1.7 Bootinfo Extension

```python
# In boot.py
def extend_bootinfo(bootinfo):
    """Extend frappe.boot with scope context data."""
    user = frappe.session.user
    scope = get_user_scope_context(user)
    if scope:
        bootinfo["scope_context"] = {
            "current": scope.as_dict(),
            "hierarchy": get_user_scope_hierarchy(user),
        }
```

---

## 2. JavaScript Patterns

### 2.1 DOM Selector (Dual v15/v16 Compatible)

```javascript
// ✅ CORRECT — works on both versions
const navbar = document.querySelector('.navbar') || document.querySelector('[data-page-route] .navbar');

// After any DOM change, run: node verify_v16_selectors.js
```

### 2.2 CSS Variable Override

```css
/* Always use !important for cascade victory over Frappe */
html.ct-enterprise[data-theme="dark"] {
    --primary: #3498db !important;
    --bg: #1a1a1a !important;
}
```

### 2.3 Async Module Loading

```javascript
frappe.require("/assets/construction/js/vite_layout_controls.js?v=1.8").then(() => {
    // Module loaded — safe to use
});
```

---

## 3. CSS Patterns

### 3.1 Adding a New CSS File

```python
# In hooks.py — append to app_include_css
app_include_css = [
    # ... existing files ...
    "/assets/construction/css/my_new_feature.css?v=1.0",  # always add ?v= param
]
```

```bash
# After adding/changing CSS registration:
cd /home/mohamed/frappe-bench
bench build --app construction
# OR for dev mode:
bench clear-cache
```

### 3.2 Three-Layer Theme Cascade

```
Layer 1 (tokens):    modern_theme_tokens.css    (284 lines, 54 variables)
Layer 2 (base):      modern_theme_base.css      (5,101 lines, overrides)
Layer 3 (adapter):   modern_theme_v16_adapter.css (2,144 lines, v16 DOM)
Combined (loaded):   modern_theme.css           (4,258 lines)
```

**Important:** `hooks.py` only loads `modern_theme.css` and a few Vite/VFC files. Do not add all 22 CSS files to `app_include_css`.

---

## 4. Frappe Hook Patterns

### 4.1 DocType Event Hook

```python
# In hooks.py
doc_events = {
    "*": {"validate": "construction.overrides.scope_enforcement.validate"},
    "Purchase Order": {
        "validate": "construction.services.boq_transaction_validation.validate_document"
    },
}
```

### 4.2 Permission Query Condition

```python
# In hooks.py
permission_query_conditions = {
    "*": "construction.overrides.scope_query.add_scope_conditions",
}
```

### 4.3 Boot Session Hook

```python
# In hooks.py
boot_session = "construction.api.theme_api.add_theme_to_boot"
extend_bootinfo = "construction.boot.extend_bootinfo"
```

---

## 5. Anti-Patterns (Never Do This)

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| `f"SELECT ... WHERE x = '{var}'"` | SQL injection | Parameterized queries only |
| `doc.save()` for theme preference updates | TimestampMismatchError | `frappe.db.set_value(..., update_modified=False)` |
| Adding CSS file without `hooks.py` registration | File never loads | Register in `app_include_css` |
| Assuming BOQ Item has `item_code` | Schema mismatch — no such field | Use `cost_item` (Data) |
| Testing scope features as Administrator | Admin bypasses all filters | Create non-admin test user |
| Adding all 22 CSS files to `app_include_css` | Generated/test files will conflict | Only register the 6 production files + your new file |
