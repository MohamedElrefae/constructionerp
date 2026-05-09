# Troubleshooting Guide

## Construction ERP White-Label Theming System

---

## Common Issues & Solutions

### Issue #1: Theme Switch Not Working

**Symptoms:**
- Clicking theme toggle does nothing
- Dropdown opens but theme doesn't change
- Console error: "ModernThemeLoader not found"

**Diagnosis Steps:**

1. Check JS files loaded:
```javascript
// In browser console
console.log(window.ConstructionTheme);
console.log(window.ModernThemeLoader);
```

**Expected:** Both should return objects.

2. Check API availability:
```javascript
// Test API call
frappe.call({
    method: "construction.api.theme_api.get_effective_desk_theme",
    args: { current_mode: "dark" },
    callback: (r) => console.log(r.message)
});
```

**Fixes:**
- If `ConstructionTheme` is undefined: Check `app_include_js` in hooks.py
- If API returns 404: Run `bench migrate` to install DocTypes
- If permission error: Check user has "Construction Theme" read permission

---

### Issue #2: Dark Mode Shows White Background

**Symptoms:**
- Dark mode selected but background stays white
- Sidebar appears light instead of dark

**Diagnosis:**

1. Check data attributes:
```javascript
// Should show "dark"
document.documentElement.getAttribute("data-theme");

// Should show "construction_dark" 
document.documentElement.getAttribute("data-modern-theme");
```

2. Check CSS loaded:
```javascript
// Verify stylesheets present
Array.from(document.styleSheets).map(s => s.href).filter(h => h && h.includes('construction'));
```

**Root Causes:**

| Cause | Fix |
|-------|-----|
| CSS file 404 | Check `bench build` output |
| data-theme not set | Check `theme_loader.js` init() |
| CSS specificity lost | Add `!important` to rules |
| Frappe override | Check `modern_theme_dark.css` exists |

**Immediate Fix:**
```css
/* Inject via DevTools console */
const style = document.createElement('style');
style.textContent = `
  html[data-theme="dark"] body {
    background: #0b1020 !important;
  }
`;
document.head.appendChild(style);
```

---

### Issue #3: Sidebar Text Invisible/Wrong Color

**Symptoms:**
- Sidebar links appear white on white background
- Text color doesn't match theme
- Selected item not highlighted

**Diagnosis:**

```javascript
// Check computed color
const link = document.querySelector('.desk-sidebar .item-anchor');
console.log('Computed color:', getComputedStyle(link).color);
console.log('Computed background:', getComputedStyle(link).backgroundColor);
```

**Expected Dark Mode:**
- Color: `rgb(232, 245, 233)` (light green-white)
- Background: `rgb(13, 31, 18)` (dark green)

**Fixes:**

1. **Force color override:**
```css
.desk-sidebar a, .layout-side-section a {
  color: var(--ct-text-primary) !important;
}
```

2. **Check CSS variable defined:**
```javascript
getComputedStyle(document.documentElement).getPropertyValue('--ct-text-primary');
// Should return: #e8f5e9 (for dark)
```

3. **Diagnostic mode:**
Enable in browser console:
```javascript
// The diagnostic runs automatically in v5.4+
// Check console for "[Theme Diagnostic]" messages
```

---

### Issue #4: Theme Resets on Page Navigation

**Symptoms:**
- Theme changes when clicking between pages
- Returns to light mode after navigation
- localStorage values disappear

**Diagnosis:**

1. Check localStorage persistence:
```javascript
localStorage.setItem('test_persistence', 'value');
localStorage.clear();  // Simulate Frappe clear
console.log('After clear:', localStorage.getItem('test_persistence'));
// Should still show 'value' due to interceptor
```

2. Check interceptor active:
```javascript
// Look for console message:
// "[Theme System] Defensive localStorage protection active"
```

**Root Causes:**

| Cause | Solution |
|-------|----------|
| Interceptor not loaded | Check `modern_theme_loader_v2.js` loads first |
| Backup keys missing | Check `THEME_KEYS` array includes your keys |
| Frappe clearing differently | Check for `removeItem` calls |

**Fix:** Verify interceptor in `modern_theme_loader_v2.js`:
```javascript
// Lines 17-80 should include:
(function() {
    var THEME_KEYS = ['construction_active_theme', 'construction_theme', 'construction_mode'];
    // ... interceptor code
})();
```

---

### Issue #5: Theme Dropdown Missing

**Symptoms:**
- No theme toggle in navbar
- Can't switch themes
- Navbar shows only user menu

**Diagnosis:**

1. Check dropdown element:
```javascript
document.getElementById('construction-theme-dropdown');
// or
document.getElementById('theme-dropdown');
```

2. Check injection script loaded:
```javascript
// Look for navbar_theme_dropdown.js in sources
```

**Fixes:**

1. **Manual injection:**
```javascript
// Run in console
const li = document.createElement('li');
li.id = 'construction-theme-dropdown';
li.className = 'nav-item dropdown';
li.innerHTML = `
  <a class="nav-link" href="#" data-toggle="dropdown">
    <span>🎨 Theme</span>
  </a>
  <div class="dropdown-menu">
    <a class="dropdown-item" onclick="ConstructionTheme.setMode('light')">Light</a>
    <a class="dropdown-item" onclick="ConstructionTheme.setMode('dark')">Dark</a>
  </div>
`;
document.querySelector('.navbar-nav').prepend(li);
```

2. **Check hooks.py** includes navbar dropdown JS:
```python
app_include_js = [
    # ... other files ...
    "/assets/construction/js/navbar_theme_dropdown.js",
]
```

---

### Issue #6: FOUC (Flash of Unstyled Content)

**Symptoms:**
- White flash before dark theme loads
- Brief moment of wrong colors on page load

**Diagnosis:**

1. Check timing:
```javascript
// Add to console
performance.mark('theme-start');
// ... wait for theme to apply ...
performance.mark('theme-end');
performance.measure('theme-load', 'theme-start', 'theme-end');
console.log(performance.getEntriesByName('theme-load')[0].duration);
```

**Target:** < 50ms from HTML parse to theme application

2. Check render blocking:
```html
<!-- In <head>, CSS should be before JS -->
<link rel="stylesheet" href="/assets/construction/css/modern_theme_tokens.css">
<script src="/assets/construction/js/theme_loader.js"></script>
```

**Fixes:**

1. **Inline critical CSS** in HTML head:
```html
<style>
  html[data-theme="dark"] { background: #0b1020 !important; }
</style>
```

2. **Preload theme CSS:**
```html
<link rel="preload" href="/assets/construction/css/modern_theme_tokens.css" as="style">
```

3. **Use `display: none` until ready:**
```css
body { visibility: hidden; }
body.theme-ready { visibility: visible; }
```

---

### Issue #7: PDF Export Shows Wrong Colors

**Symptoms:**
- PDF has white background in dark mode
- Print preview shows Frappe branding
- PDF header/footer missing

**Diagnosis:**

1. Check PDF hooks configured:
```python
# In hooks.py
pdf_header_html = "construction.api.theme_api.get_pdf_header"
pdf_footer_html = "construction.api.theme_api.get_pdf_footer"
print_css = "/assets/construction/css/print_theme.css"
```

2. Check print CSS exists:
```bash
ls -la frappe-bench/apps/construction/construction/public/css/print_theme.css
```

**Fix:**

1. **Force light mode for PDF:**
```css
/* In print_theme.css */
@media print {
  body {
    background: white !important;
    color: black !important;
  }
}
```

2. **Check wkhtmltopdf** version:
```bash
wkhtmltopdf --version
# Should be 0.12.5 or higher
```

---

### Issue #8: Email Templates Broken

**Symptoms:**
- Emails show wrong colors
- Outlook/Gmail display issues
- CSS not applied in email clients

**Diagnosis:**

Email CSS rules violated:
```css
/* Check email_theme.css has NO: */
- CSS variables (var(--primary))
- Flexbox (display: flex)
- Grid (display: grid)
- rgba() with opacity
- @media queries
```

**Fix:**

Use inline styles or table-based layouts:
```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background-color: #0b1020; padding: 24px;">
      <!-- Content -->
    </td>
  </tr>
</table>
```

---

### Issue #9: Cache Not Clearing

**Symptoms:**
- Theme changes don't reflect
- Old CSS persists after update
- Users see different versions

**Fixes:**

1. **Version bump in hooks.py:**
```python
# Change ?v=X to new number
app_include_css = [
    "/assets/construction/css/modern_theme_tokens.css?v=4",  # was v=3
]
```

2. **Force cache clear:**
```bash
bench --site [site] clear-cache
bench clear-cache
systemctl restart supervisor  # or your process manager
```

3. **Browser hard refresh:**
```javascript
// In browser console
location.reload(true);
```

---

### Issue #10: After Migrate Hook Fails

**Symptoms:**
- `bench migrate` shows error
- "Module has no attribute" message
- Themes not created after migration

**Diagnosis:**

Check error log:
```bash
bench --site [site] show-logs | tail -50
```

Common errors:
```
ModuleNotFoundError: No module named 'construction.construction.utils.scope_validation'
AttributeError: module 'construction.install' has no attribute 'setup_construction_workspace_page'
```

**Fixes:**

1. **Create missing function:**
```python
# In construction/install.py
def setup_construction_workspace_page():
    """Placeholder for workspace page setup."""
    pass
```

2. **Create missing module:**
```bash
touch construction/construction/utils/__init__.py
touch construction/construction/utils/scope_validation.py
```

3. **Skip problematic hooks temporarily:**
```python
# In hooks.py, comment out failing hook
after_migrate = [
    "construction.install.create_system_themes",
    # "construction.install.setup_construction_workspace_page",  # Disabled
]
```

---

## Debug Mode

Enable verbose logging:

```javascript
// In browser console
localStorage.setItem('construction_debug', 'true');
location.reload();
```

This enables:
- Detailed console logging
- Performance timing output
- API call tracing
- MutationObserver diagnostics

---

## Getting Help

If issue persists:

1. **Collect information:**
   - Frappe version: `frappe.__version__`
   - ERPNext version: `erpnext.__version__`
   - Browser console errors (screenshot)
   - Network tab 404s (screenshot)

2. **Check environment:**
   ```bash
   bench --site [site] console
   ```
   ```python
   # Run diagnostics
   import construction
   print(construction.__version__)
   
   # Check DocTypes exist
   print(frappe.db.table_exists("Construction Theme"))
   print(frappe.db.table_exists("User Desk Theme"))
   ```

3. **Generate report:**
   ```javascript
   // In browser console
   ConstructionTheme.verifyLabCompliance();
   ```

---

## Quick Fixes Cheat Sheet

| Problem | Quick Fix Code |
|---------|----------------|
| White background | `document.body.style.background = '#0b1020'` |
| Wrong text color | `document.querySelectorAll('a').forEach(a => a.style.color = '#e8f5e9')` |
| Missing dropdown | `ConstructionTheme.renderNavbarDropdown('dark')` |
| Theme not sticking | `localStorage.setItem('construction_active_theme', 'construction_dark')` |
| Cache issues | `location.reload(true)` |
| FOUC | Add `<style>body{visibility:hidden}</style>` to head |

---

## Resolved Technical Debt (Kimi K 2.6 Fixes)

The following issues identified in the Kimi K 2.6 review have been **resolved** in v5.3:

| Issue | Original Status | Fix Applied | Date |
|-------|-----------------|-------------|------|
| MutationObserver not disconnected | ⚠️ Accepted | Added `disconnectObservers()` method + `beforeunload` handler | 2026-05-05 |
| pierceShadowDOM on every mutation | ⚠️ Accepted | Now uses `_shadowRootsInjected` WeakSet to track injected roots | 2026-05-05 |
| No jQuery check | ⚠️ Accepted | Added `typeof $ === 'undefined'` guard in `hideFrappeBranding()` | 2026-05-05 |
| Duplicate dropdown possible | ⚠️ Accepted | Added `_navbarDropdownPending` flag + race condition protection | 2026-05-05 |

### Technical Details

**1. MutationObserver Lifecycle Management**
- Observers now stored in `_mutationObserver`, `_themeObserver`, `_cascadeGuard`
- `disconnectObservers()` method cleans up all observers
- Automatic cleanup on `beforeunload` event for SPA navigation

**2. Shadow DOM Injection Optimization**
- `_shadowRootsInjected` WeakSet tracks which roots have tokens
- Only new shadow roots get injected (not all on every mutation)
- `injectShadowTokens()` handles deduplication

**3. jQuery Dependency Safety**
- `hideFrappeBranding()` now checks `typeof $` before using jQuery
- Graceful fallback with console warning if jQuery unavailable
- Wrapped in try-catch for additional safety

**4. Navbar Dropdown Duplication Guard**
- `_navbarDropdownPending` flag prevents concurrent retry attempts
- Double-check after navbar acquisition (race condition protection)
- Updates existing dropdown instead of creating duplicate

---

*Last Updated: 2026-05-05*
