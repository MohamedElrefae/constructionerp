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
| app_include_js[0] | /assets/construction/js/boq_export_columns.js | ?v=1 | 4.2KB |
| app_include_js[1] | /assets/construction/js/print_settings_dialog.js | - | 23.0KB |
| app_include_js[2] | /assets/construction/js/construction_export_menu.js | - | 5.9KB |
| app_include_js[3] | /assets/construction/js/generic_export_menu.js | ?v=1 | 14.2KB |
| app_include_js[4] | /assets/construction/js/theme_loader_v24.js | ?v=2.6.1 | 33.7KB |
| app_include_js[5] | /assets/construction/js/typography_settings.js | ?v=21 | 29.7KB |
| app_include_js[6] | /assets/construction/js/searchable_dropdown/utils.js | - | 2.6KB |
| app_include_js[7] | /assets/construction/js/searchable_dropdown/searchable_dropdown.js | - | 4.2KB |
| app_include_js[8] | /assets/construction/js/overrides/ct_select_control.js | ?v=2 | 13.0KB |
| app_include_js[9] | /assets/construction/js/overrides/ct_link_control.js | ?v=17 | 23.2KB |
| app_include_js[10] | /assets/construction/js/theme_loader_v16.js | ?v=2 | 834B |
| app_include_js[11] | /assets/construction/js/scope_context.js | ?v=3 | 11.0KB |
| app_include_js[12] | /assets/construction/js/frappe_compat_patches.js | ?v=2 | 6.8KB |
| app_include_js[13] | /assets/construction/js/scope_context_ui.js | ?v=5 | 9.0KB |
| app_include_js[14] | /assets/construction/js/scope_context_list_filter.js | ?v=3 | 4.1KB |
| app_include_js[15] | /assets/construction/js/scope_context_form_defaults.js | ?v=3 | 2.3KB |
| app_include_js[16] | /assets/construction/js/vfc_config.js | ?v=1 | 749B |
| app_include_js[17] | /assets/construction/js/scope_context_report_filters.js | ?v=4 | 13.8KB |
| app_include_js[18] | /assets/construction/js/ct_list_view_config.js | ?v=1 | 3.5KB |
| app_include_js[19] | /assets/construction/js/sidebar_accordion.js | ?v=1 | 1.0KB |
| app_include_js[20] | /assets/construction/js/translation_list_tools.js | ?v=6 | 8.4KB |
| app_include_js[21] | /assets/construction/js/boq_filters.js | ?v=8 | 21.2KB |
| app_include_js[22] | /assets/construction/js/filter_fix.js | ?v=11 | 21.6KB |
| app_include_js[23] | /assets/construction/js/native_frappe_controls_compat.js | ?v=9 | 20.5KB |
| app_include_js[24] | /assets/construction/js/vite_layout_controls.js | ?v=1.21 | 68.5KB |
| app_include_js[25] | /assets/construction/js/vfc_layout_engine.js | ?v=1.44 | 48.5KB |

### CSS (Backend - Logged In Users)

| Hook | Path | Version | Size |
|------|------|---------|------|
| app_include_css[0] | /assets/construction/css/modern_theme.css | ?v=2.5.8 | 142.2KB |
| app_include_css[1] | /assets/construction/css/scope_context.css | ?v=2 | 1.0KB |
| app_include_css[2] | /assets/construction/css/vite_extensions.css | ?v=1.3 | 2.5KB |
| app_include_css[3] | /assets/construction/css/vite_form_override.css | ?v=1.5 | 26.3KB |
| app_include_css[4] | /assets/construction/css/vite_list_override.css | ?v=1.3 | 10.6KB |
| app_include_css[5] | /assets/construction/css/vfc_sections.css | ?v=1.6 | 10.6KB |

### JavaScript (Frontend - Login Page)

| Hook | Path | Version | Size |
|------|------|---------|------|
| web_include_js | /assets/construction/js/theme_loader_v24.js | ?v=2.6.1 | 33.7KB |

### CSS (Frontend - Login Page)

| Hook | Path | Version | Size |
|------|------|---------|------|
| web_include_css[0] | /assets/construction/css/modern_theme.css | ?v=2.5.8 | 142.2KB |
| web_include_css[1] | /assets/construction/css/email_theme.css | - | 1.7KB |

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

## Known Gaps (Scope B Follow-Up)

The following sections reflect early-stage documentation and require complete regeneration against `hooks.py`:
- `override_whitelisted_methods`: `hooks.py` defines 4 entries (including `get_all_tags` and `get_tags`), whereas Section "Override Hooks" currently documents only 2.
- `doc_events`: `hooks.py` defines 29 document lifecycle hooks (validations, custom status transitions, and bilingual policies), which are currently unlisted in Section "Event Hooks".

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
| 2026-10-03 | Synchronized Asset Inclusion tables with hooks.py (26 JS, 6 CSS, web includes) |

---

*Last Updated: 2026-10-03*
