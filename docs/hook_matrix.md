# Hook Matrix Reference

Complete reference of all Frappe hooks used by Construction Theming System.

---

## Core Application Hooks

| Hook | File | Line | Value | Purpose |
|------|------|------|-------|---------|
| `app_name` | hooks.py | 3 | "construction" | App identifier |
| `app_title` | hooks.py | 4 | "Construction ERP" | Human-readable name |
| `app_publisher` | hooks.py | 5 | "Mohamed Elrefae" | Author |
| `app_description` | hooks.py | 6 | "Construction ERP App..." | Description |
| `app_email` | hooks.py | 7 | "melrefa3@hotmail.com" | Contact |
| `app_license` | hooks.py | 8 | "MIT" | License |

---

## Asset Inclusion Hooks

### JavaScript (Backend - Logged In Users)

| Hook | Path | Version | Size |
|------|------|---------|------|
| app_include_js[0] | /assets/construction/js/print_settings_dialog.js | - | 22KB |
| app_include_js[1] | /assets/construction/js/construction_export_menu.js | - | 5.7KB |
| app_include_js[2] | /assets/construction/js/theme_patch.js | ?v=9 | 7KB |
| app_include_js[3] | /assets/construction/js/theme_loader.js | ?v=11 | 16KB |
| app_include_js[4] | /assets/construction/js/components/index.js | ?v=4.5 | - |
| app_include_js[5] | /assets/construction/js/searchable_dropdown/utils.js | - | - |
| app_include_js[6] | /assets/construction/js/searchable_dropdown/searchable_dropdown.js | - | - |
| app_include_js[7] | /assets/construction/js/searchable_dropdown/config/journal_entry.js | - | - |
| app_include_js[8] | /assets/construction/js/searchable_dropdown/config/sales_invoice.js | - | - |
| app_include_js[9] | /assets/construction/js/searchable_dropdown/config/customer_supplier.js | - | - |

### CSS (Backend - Logged In Users)

| Hook | Path | Version | Purpose |
|------|------|---------|---------|
| app_include_css[0] | /assets/construction/css/modern_theme_dark.css | ?v=3 | Dark theme styles |
| app_include_css[1] | /assets/construction/css/modern_theme_light.css | ?v=3 | Light theme styles |
| app_include_css[2] | /assets/construction/css/modern_theme_tokens.css | ?v=4 | CSS variables |
| app_include_css[3] | /assets/construction/css/modern_theme_base.css | ?v=6 | Layout fixes |
| app_include_css[4] | /assets/construction/css/modern_theme_components_extra.css | ?v=1 | Extra components |
| app_include_css[5] | /assets/construction/css/searchable_dropdown.css | - | Dropdown styling |

### JavaScript (Frontend - Login Page)

| Hook | Path | Purpose |
|------|------|---------|
| web_include_js | /assets/construction/js/login_theme_toggle.js | Login page theme toggle |

### CSS (Frontend - Login Page)

| Hook | Path | Purpose |
|------|------|---------|
| web_include_css[0] | /assets/construction/css/login_theme.css | Login base styles |
| web_include_css[1] | /assets/construction/css/login_theme_light.css | Login light theme |
| web_include_css[2] | /assets/construction/css/email_theme.css | Email template styles |

---

## Branding Hooks

| Hook | Value | Purpose |
|------|-------|---------|
| `brand_html` | construction/templates/includes/navbar_brand.html | Navbar brand template |
| `login_page_title` | "Construction ERP — Login" | Browser tab title |
| `website_context` | {favicon, splash_image, brand_html} | Global website context |
| `email_css` | ["/assets/construction/css/email_theme.css"] | Email styling |
| `print_css` | /assets/construction/css/print_theme.css | Print/PDF styling |
| `pdf_header_html` | construction.api.theme_api.get_pdf_header | PDF header function |
| `pdf_footer_html` | construction.api.theme_api.get_pdf_footer | PDF footer function |

---

## Event Hooks

| Hook | Value | Trigger |
|------|-------|---------|
| `boot_session` | construction.api.theme_api.add_theme_to_boot | Every page load |
| `after_install` | construction.install.create_system_themes | App installation |
| `after_migrate[0]` | construction.api.theme_api.whitelabel_patch | After bench migrate |
| `after_migrate[1]` | construction.install.create_system_themes | After bench migrate |
| `after_migrate[2]` | construction.install.setup_workspace_sidebar | After bench migrate |
| `after_migrate[3]` | construction.install.setup_construction_workspace_page | After bench migrate |
| `after_migrate[4]` | construction.install.verify_workspace_visibility | After bench migrate |

---

## Override Hooks

| Hook | Original | Override | Purpose |
|------|----------|----------|---------|
| `override_whitelisted_methods` | frappe.core.doctype.user.user.switch_theme | construction.overrides.switch_theme_simple.switch_theme | Theme switching |
| `override_whitelisted_methods` | frappe.utils.change_log.show_update_popup | construction.api.theme_api.ignore_update_popup | Suppress updates |

---

## Desk Integration Hooks

| Hook | Value | Purpose |
|------|-------|---------|
| `add_to_apps_screen` | [{name, logo, title, route}] | Desktop app icon |
| `desk_links` | {Construction: [DocType links]} | Module sidebar links |
| `doctype_js` | {"BOQ Header": "path/to/file.js"} | Form scripts |
| `doctype_tree_js` | {"BOQ Structure": "path/to/tree.js"} | Tree view scripts |

---

## Data Hooks

| Hook | Value | Purpose |
|------|-------|---------|
| `fixtures` | Construction Theme (system themes) | Export system themes |
| `fixtures` | Workspace Sidebar (Construction) | Export sidebar config |

---

## Hook Dependency Graph

```
Page Load
    └── boot_session
        └── add_theme_to_boot
            ├── get_effective_desk_theme
            ├── get_user_theme_settings
            └── Injects: frappe.boot.construction_theme

Theme Switch
    ├── User Action
    │   └── ConstructionTheme.setMode()
    │       ├── save_user_mode() [API]
    │       └── fetchAndApplyCSS()
    └── System Action
        └── switch_theme [Override]
            └── set_user_theme() [API]

Migration
    └── after_migrate[]
        ├── whitelabel_patch (cleans Frappe branding)
        ├── create_system_themes (ensures 4 system themes exist)
        ├── setup_workspace_sidebar (reconciles sidebar items)
        ├── setup_construction_workspace_page (placeholder)
        └── verify_workspace_visibility (health check)
```

---

## Version History

| Date | Hook Changes |
|------|--------------|
| 2026-04-15 | Initial hook setup |
| 2026-04-20 | Added web_include_css/js for login page |
| 2026-04-25 | Added override_whitelisted_methods |
| 2026-05-01 | Added brand_html, website_context |
| 2026-05-03 | Bumped version strings v=120 for theme fixes |
| 2026-05-05 | Added print_css, pdf_header/footer_html |

---

*Last Updated: 2026-05-05*
