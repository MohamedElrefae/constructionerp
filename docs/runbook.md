# Operations Runbook

## Construction ERP White-Label Theming System

---

## Quick Reference

| Task | Command/Location |
|------|------------------|
| Check theme status | `bench --site [site] console` → `check_themes.py` |
| Clear theme cache | `bench --site [site] clear-cache` |
| Rebuild assets | `bench build` |
| Force theme re-apply | Delete `construction_theme` from localStorage |
| View error logs | `bench --site [site] show-logs` |

---

## 1. Daily Operations

### 1.1 Verify System Themes Exist

```bash
cd frappe-bench
bench --site construction.local console
```

```python
# In console
import frappe
themes = frappe.db.sql("""
    SELECT name, is_system_theme, is_active, 
           is_default_light, is_default_dark, theme_type
    FROM `tabConstruction Theme`
""", as_dict=True)

for t in themes:
    print(f"{t['name']}: system={t['is_system_theme']}, active={t['is_active']}")
```

**Expected Output:**
```
Light: system=1, active=1
Dark: system=1, active=1
Construction Light: system=1, active=1
Construction Dark: system=1, active=1
```

### 1.2 Check Default Themes Set

```python
# In console
has_default_light = frappe.db.exists("Construction Theme", 
    {"is_system_theme": 1, "is_default_light": 1})
has_default_dark = frappe.db.exists("Construction Theme", 
    {"is_system_theme": 1, "is_default_dark": 1})

print(f"Default Light: {has_default_light}")
print(f"Default Dark: {has_default_dark}")
```

**If missing:**
```python
frappe.db.set_value("Construction Theme", "Construction Light", "is_default_light", 1)
frappe.db.set_value("Construction Theme", "Construction Dark", "is_default_dark", 1)
frappe.db.commit()
```

---

## 2. Troubleshooting

### 2.1 Theme Not Applying

**Symptoms:** White background in dark mode, sidebar wrong color

**Checklist:**
1. ✅ CSS files loading (Network tab → look for 200 on modern_theme_*.css)
2. ✅ data-theme attribute set (DevTools → Elements → `<html>`)
3. ✅ data-modern-theme attribute set
4. ✅ No CSS 404 errors

**Quick Fix:**
```javascript
// In browser console
localStorage.removeItem("construction_active_theme");
localStorage.removeItem("construction_theme");
localStorage.removeItem("construction_mode");
location.reload();
```

### 2.2 Sidebar Text Invisible

**Symptoms:** Sidebar links not visible or wrong color

**Diagnosis:**
```javascript
// Check computed styles
const link = document.querySelector('.desk-sidebar .item-anchor');
console.log(getComputedStyle(link).color);
```

**Expected:** `rgb(232, 245, 233)` (light green-white for dark theme)

**Fix:**
```javascript
// Force color fix
document.querySelectorAll('.desk-sidebar a, .layout-side-section a').forEach(a => {
    a.style.color = '#e8f5e9';
});
```

**Permanent Fix:** Check `modern_theme_dark.css` has sidebar selectors.

### 2.3 Theme Resets After Page Change

**Symptoms:** Theme switches back to light when navigating

**Causes:**
1. localStorage cleared by Frappe (fixed in modern_theme_loader_v2.js with interceptor)
2. API returning wrong theme
3. MutationObserver conflict

**Diagnosis:**
```javascript
// Check interceptor is working
localStorage.setItem("test_key", "test_value");
localStorage.clear();
console.log("test_key after clear:", localStorage.getItem("test_key"));
// Should still exist due to interceptor
```

### 2.4 TimestampMismatchError

**Symptoms:** Error when switching themes rapidly

**Status:** Fixed in `save_user_mode()` using direct DB update

**If still occurring:**
```python
# Check user record
doc = frappe.get_doc("User", "user@example.com")
print(doc.modified)  # Should not change on theme switch
```

### 2.5 FOUC (Flash of Unstyled Content)

**Symptoms:** White flash before dark theme loads

**Fix:** Check `boot_session` is injecting theme early:
```python
# Verify boot injection
from construction.api.theme_api import add_theme_to_boot
bootinfo = {}
add_theme_to_boot(bootinfo)
print(bootinfo.get("construction_theme"))
```

---

## 3. Configuration Management

### 3.1 Change Default Site Theme

```python
# Set site-wide default
from frappe.utils import now

# For light mode default
frappe.db.set_value("Construction Theme", "Construction Light", {
    "is_default_light": 1,
    "modified": now()
})

# For dark mode default  
frappe.db.set_value("Construction Theme", "Construction Dark", {
    "is_default_dark": 1,
    "modified": now()
})

frappe.db.commit()
```

### 3.2 Create Custom Theme

1. Go to **Construction Theme** list
2. Click **New**
3. Set:
   - Theme Name: "Client Brand"
   - Theme Type: "Custom Light" or "Custom Dark"
   - Colors per specification
4. Check **Is Active**
5. Set as default if desired

### 3.3 Enable User Theme Overrides

1. Go to **Modern Theme Settings**
2. Check **Allow User Override**
3. Save

Users can then set personal themes in User Desk Theme.

### 3.4 Disable User Theme Overrides

```python
# Force all users to site default
settings = frappe.get_doc("Modern Theme Settings")
settings.allow_user_override = 0
settings.save()

# Optional: Clear user preferences
frappe.db.sql("""
    UPDATE `tabUser Desk Theme` 
    SET inherit_from_site = 1
""")
frappe.db.commit()
```

---

## 4. Performance Optimization

### 4.1 Check CSS File Sizes

```bash
cd frappe-bench/apps/construction/construction/public

# Check raw sizes
ls -la css/

# Check gzipped sizes
gzip -c css/modern_theme_tokens.css | wc -c
gzip -c css/modern_theme_base.css | wc -c
gzip -c js/theme_loader.js | wc -c
```

**Targets:**
- CSS tokens: < 10KB gzipped
- CSS base: < 10KB gzipped
- JS loader: < 15KB gzipped

### 4.2 Clear Theme Cache

```python
# Clear all theme-related cache
frappe.cache().delete_key("construction_theme:*")
frappe.cache().delete_key("bootinfo")

# Clear per-user cache
for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
    frappe.cache().hdel("bootinfo", user)
```

### 4.3 Optimize CSS Delivery

If files are too large:
1. Split by component (already done)
2. Lazy-load non-critical CSS
3. Use `media` queries for conditional loading

---

## 5. Security Considerations

### 5.1 Sanitize User Input

Theme names are validated against allowed characters:
- Alphanumeric
- Spaces (converted to underscores)
- No HTML/script tags

### 5.2 XSS Prevention

CSS injection points:
- ✅ `injectCSS()` uses `textContent` (not `innerHTML`)
- ✅ API validates theme names
- ✅ No user-generated CSS allowed (only admin-defined themes)

### 5.3 Permission Checks

| Function | Permission Required |
|----------|-------------------|
| save_modern_theme_settings | Modern Theme Settings: write |
| save_user_theme_settings | Self-only (if_owner) |
| get_modern_theme_settings | Modern Theme Settings: read |

---

## 6. Monitoring

### 6.1 Key Metrics

| Metric | How to Check | Target |
|--------|--------------|--------|
| Theme load time | Performance API in browser | < 200ms |
| CSS file size | Network tab | < 50KB total |
| FOUC incidents | Visual inspection | 0 |
| API error rate | Error logs | < 1% |

### 6.2 Log Analysis

```bash
# View theme-related errors
bench --site construction.local show-logs | grep -i "theme\|construction"

# View API calls
bench --site construction.local console
```

```python
# Query error log
errors = frappe.get_all("Error Log", 
    filters={"method": ["like", "%theme%"]},
    fields=["method", "error"],
    order_by="creation desc",
    limit=10
)
```

---

## 7. Disaster Recovery

### 7.1 Theme System Broken

**Restore from fixtures:**
```bash
bench --site construction.local export-fixtures
bench --site construction.local import-fixtures
```

**Or recreate system themes:**
```python
from construction.install import create_system_themes
create_system_themes()
frappe.db.commit()
```

### 7.2 Complete Reset

```bash
# 1. Clear all theme data
bench --site construction.local console
```

```python
# Delete user preferences
frappe.db.sql("DELETE FROM `tabUser Desk Theme`")

# Reset to Frappe default
frappe.db.sql("UPDATE `tabUser` SET desk_theme = 'Light'")

# Clear cache
frappe.cache().flushall()
frappe.db.commit()
```

```bash
# 2. Rebuild
bench build
bench --site construction.local migrate
```

---

## 8. Upgrade Procedures

### 8.1 Before Frappe Update

```bash
# Export current themes
bench --site construction.local export-fixtures

# Backup custom themes
mysqldump -u root -p [database] --tables `tabConstruction Theme` > theme_backup.sql
```

### 8.2 After Frappe Update

```bash
# Run migration (applies whitelabel_patch)
bench --site construction.local migrate

# Verify themes still work
bench --site construction.local console
```

```python
# Verify
from construction.api.theme_api import get_effective_desk_theme
print(get_effective_desk_theme("dark"))
```

---

## 9. Contact & Escalation

| Issue | Contact |
|-------|---------|
| Theme not applying | Check this runbook → Clear cache |
| CSS bugs | Engineering Team |
| Feature requests | Product Team |
| Critical production issue | On-call engineer |

---

*Last Updated: 2026-05-05*
