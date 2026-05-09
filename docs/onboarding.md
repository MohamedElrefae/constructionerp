# Onboarding Guide

## Construction ERP White-Label Theming System

Welcome! This guide will get you up and running with the theming system.

---

## Quick Start (5 minutes)

### 1. Verify Installation

```bash
cd frappe-bench
bench --site your-site.com console
```

```python
# Check DocTypes exist
print(frappe.db.table_exists("Construction Theme"))  # Should be True
print(frappe.db.table_exists("User Desk Theme"))     # Should be True

# Check system themes
print(frappe.db.count("Construction Theme", {"is_system_theme": 1}))  # Should be 4
```

### 2. Check Your Current Theme

Open browser console on your ERPNext instance:

```javascript
// Check current theme
document.documentElement.getAttribute("data-theme");        // "light" or "dark"
document.documentElement.getAttribute("data-modern-theme"); // "construction_light" or "construction_dark"

// Check tokens are applied
getComputedStyle(document.documentElement).getPropertyValue("--primary");  // Should be "#2563eb"
```

### 3. Test Theme Switch

```javascript
// Switch to dark mode
ConstructionTheme.setMode("dark");

// Verify
console.log(ConstructionTheme.currentMode);  // "dark"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Light Mode  │  │  Dark Mode   │  │   Custom     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 CONFIGURATION LAYER                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Construction Theme DocType                 │  │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐ │  │
│  │  │ System     │ │ System     │ │ Custom Themes    │ │  │
│  │  │ Light      │ │ Dark       │ │ (Your Brand)     │ │  │
│  │  └────────────┘ └────────────┘ └──────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         User Desk Theme (Per-User Override)          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   DELIVERY LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Static CSS   │  │ Dynamic CSS  │  │  JS Loader   │      │
│  │ (Tokens)     │  │ (API)        │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. CSS Token System

54 design tokens control all visual aspects:

```css
/* Colors */
--primary, --accent, --danger, --success
--bg, --surface, --text

/* Effects */
--shadow-sm, --shadow, --shadow-lg
--radius-sm, --radius, --radius-lg

/* Animation */
--t-fast, --t, --t-slow
```

### 2. Theme Resolution Order

1. User's last choice (localStorage)
2. User Desk Theme override (if enabled)
3. Site default Construction Theme
4. Modern Theme Settings default
5. Frappe default (Light/Dark)

### 3. Shadow DOM Handling

Web Components get tokens via `pierceShadowDOM()`:

```javascript
// Injected into every shadow root
:host {
  --primary-color: var(--primary, #2563eb);
  --text-color: var(--text, #f8fafc);
  /* ... */
}
```

---

## Configuration Tasks

### Set Site Default Theme

```python
# Make "Construction Dark" the default for new users
frappe.db.set_value("Construction Theme", "Construction Dark", {
    "is_default_dark": 1
})
frappe.db.commit()
```

### Create Custom Brand Theme

1. Go to **Construction > Theme Configuration**
2. Click **New**
3. Fill in:
   - **Theme Name:** "My Brand"
   - **Theme Type:** "Custom Light" or "Custom Dark"
   - **Colors:** Set your brand colors
   - **Feature Toggles:** Optional UI customizations
4. Check **Is Active**
5. Set as default if desired

### Enable User Customization

1. Go to **Modern Theme Settings**
2. Check **Allow User Override**
3. Save

Users can now set personal themes via **User Desk Theme**.

---

## File Locations

```
frappe-bench/apps/construction/construction/
├── hooks.py                          # All hook declarations
├── api/
│   └── theme_api.py                  # Backend API functions
├── doctype/
│   ├── construction_theme/           # Theme definitions
│   └── user_desk_theme/              # User preferences
├── public/
│   ├── css/
│   │   ├── modern_theme_tokens.css   # 54 CSS variables
│   │   ├── modern_theme_base.css     # Component styles
│   │   └── modern_theme_*.css        # Theme-specific
│   └── js/
│       ├── theme_loader.js           # Main loader
│       └── login_theme_toggle.js     # Login page
└── templates/
    └── includes/
        ├── navbar_brand.html         # Brand template
        ├── pdf_header.html           # PDF header
        └── pdf_footer.html           # PDF footer
```

---

## Common Customizations

### Change Navbar Brand

Edit `templates/includes/navbar_brand.html`:

```html
<a class="navbar-brand" href="/app">
  <img src="/assets/construction/images/your-logo.svg" height="24">
  <span>Your Brand Name</span>
</a>
```

### Change Login Page

Edit CSS in `public/css/login_theme.css`:

```css
.login-content {
  background: linear-gradient(135deg, #0b1020 0%, #1e293b 100%);
}

.login-logo {
  content: url('/assets/construction/images/your-logo.svg');
}
```

### Hide Frappe Elements

Use feature toggles in Construction Theme:

- Hide Help Button
- Hide Search Bar
- Hide Like/Comment
- Mobile Card View

Or add custom CSS to `modern_theme_base.css`:

```css
/* Hide specific elements */
.dropdown-help,
.footer-powered {
  display: none !important;
}
```

---

## Testing Checklist

Before going live:

- [ ] All 4 system themes exist and are active
- [ ] Default themes are set (light and dark)
- [ ] Theme switcher appears in navbar
- [ ] Light mode looks correct
- [ ] Dark mode looks correct
- [ ] Sidebar text is readable in both modes
- [ ] PDF export uses correct styling
- [ ] Email templates render correctly
- [ ] Login page shows custom branding
- [ ] Mobile view works correctly
- [ ] Cache is cleared after changes

---

## Next Steps

1. **Review ADR.md** for architectural decisions
2. **Read runbook.md** for operational procedures
3. **Check troubleshooting.md** when issues arise
4. **Consult hook_matrix.md** for hook reference

---

## Support

| Resource | Location |
|----------|----------|
| Architecture Decisions | `ADR.md` |
| Operations Guide | `docs/runbook.md` |
| Troubleshooting | `docs/troubleshooting.md` |
| Hook Reference | `docs/hook_matrix.md` |

---

*Welcome to the Construction ERP Theming System!*

*Last Updated: 2026-05-05*
