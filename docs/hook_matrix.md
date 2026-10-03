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

## Application Lifecycle & Session Hooks

| Hook | Value | Trigger | Purpose |
|------|-------|---------|---------|
| `boot_session` | construction.api.theme_api.add_theme_to_boot | Every page load | Injects theme config into boot session |
| `extend_bootinfo` | construction.boot.extend_bootinfo | Every page load | Extends bootinfo with user scope context |
| `after_install` | construction.install.create_system_themes | App installation | Initializes system themes |
| `after_migrate[0]` | construction.api.theme_api.whitelabel_patch | After bench migrate | Cleans Frappe branding |
| `after_migrate[1]` | construction.install.create_system_themes | After bench migrate | Ensures 4 system themes exist |
| `after_migrate[2]` | construction.install.setup_workspace_sidebar | After bench migrate | Reconciles sidebar items |
| `after_migrate[3]` | construction.install.setup_construction_workspace_page | After bench migrate | Configures workspace page |
| `after_migrate[4]` | construction.install.verify_workspace_visibility | After bench migrate | Verifies workspace access |

---

## Document Event Hooks (`doc_events`)

Complete mapping of server-side document lifecycle events declared in `hooks.py`:

| DocType | Event | Handler | Purpose |
|---------|-------|---------|---------|
| `*` | `validate` | `construction.overrides.scope_enforcement.validate` | Server-side branch-company integrity and scope context enforcement |
| `Purchase Order` | `validate` | `construction.services.boq_transaction_validation.validate_document` | Validates line items against active BOQ structure |
| `Purchase Order` | `on_submit` | `construction.services.resource_price_service.capture_price_from_purchase_document` | Records resource price history snapshot |
| `Purchase Order` | `on_cancel` | `construction.services.resource_price_service.cancel_price_history_for_document` | Cancels recorded resource price history |
| `Purchase Receipt` | `validate` | `construction.services.boq_transaction_validation.validate_document` | BOQ budget and transaction validation |
| `Purchase Invoice` | `validate` | `construction.services.boq_transaction_validation.validate_document` | BOQ transaction validation |
| `Purchase Invoice` | `on_submit` | `construction.services.resource_price_service.capture_price_from_purchase_document` | Records resource price history snapshot |
| `Purchase Invoice` | `on_cancel` | `construction.services.resource_price_service.cancel_price_history_for_document` | Cancels recorded resource price history |
| `Stock Entry` | `validate` | `construction.services.boq_transaction_validation.validate_document` | Material issue/transfer validation against BOQ |
| `Timesheet` | `validate` | `construction.services.boq_transaction_validation.validate_document` | Labor log validation against BOQ activity |
| `Journal Entry` | `validate` | `construction.services.boq_transaction_validation.validate_document` | Direct cost validation against BOQ accounts |
| `Sales Invoice` | `validate` | `construction.services.boq_transaction_validation.validate_document` | Billing validation against BOQ milestones |
| `Material Request` | `validate` | `construction.services.boq_transaction_validation.validate_document` | Procurement requisition validation against BOQ |
| `BOQ Item Stage` | `before_delete` | `construction.services.boq_lifecycle.before_delete_boq_item_stage` | Blocks deletion of committed stage records |
| `Account` | `validate` | `construction.services.bilingual_service.enforce_account_arabic_policy` | Enforces Arabic write gating and normalized key maintenance |
| `Item` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Arabic name policy + Tier 2 HTML / Tier 1 narrative sanitization |
| `Customer` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Arabic name policy + Tier 2 address narrative sanitization |
| `Supplier` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Arabic name policy + Tier 2 address narrative sanitization |
| `Cost Center` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual name normalization and policy enforcement |
| `Warehouse` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual name normalization and policy enforcement |
| `Project` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Arabic name policy + Tier 1/2 project narrative sanitization |
| `Item Group` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual classification master policy |
| `Customer Group` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual classification master policy |
| `Supplier Group` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual classification master policy |
| `Territory` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual classification master policy |
| `UOM` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Bilingual policy + Tier 1 UOM description sanitization |
| `Employee` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Bilingual policy + Tier 1 employee narrative sanitization |
| `Department` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual department policy and normalization |
| `BOQ Structure` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Bilingual policy + Tier 1 structure narrative sanitization |
| `BOQ Header` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual BOQ header policy and normalization |
| `Task` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Bilingual policy + Tier 1 task narrative sanitization |
| `Asset Category` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy` | Bilingual asset category policy |
| `Payment Terms Template` | `validate` | `construction.services.bilingual_service.enforce_bilingual_arabic_policy`<br>`construction.services.narrative_sanitizer.validate_narrative_fields` | Bilingual policy + Tier 1 detail description sanitization |
| `Payment Term` | `validate` | `construction.services.narrative_sanitizer.validate_narrative_fields` | Tier 1 payment term description sanitization |

---

## Override Hooks

### Method Overrides (`override_whitelisted_methods`)

| Target Whitelisted Method | Override Handler | Purpose |
|--------------------------|------------------|---------|
| `frappe.core.doctype.user.user.switch_theme` | `construction.overrides.switch_theme_simple.switch_theme` | Simplified SQL-based theme switching bypassing controller imports |
| `frappe.utils.change_log.show_update_popup` | `construction.api.theme_api.ignore_update_popup` | Suppresses update popup dialogs |
| `frappe.translate.update_translations_for_source` | `construction.api.translation_tools.update_translations_for_source_safe` | Safe translation catalog updates preserving system translations |
| `erpnext.accounts.doctype.account.account.update_account_number` | `construction.services.bilingual_service.governed_rename_account` | Governed atomic Account rename enforcing bilingual audit reason |

### DocType Class Overrides (`override_doctype_class`)

| DocType | Override Class | Purpose |
|---------|----------------|---------|
| `Translation` | `construction.overrides.translation.CustomTranslation` | Injects database catalog translations directly into runtime translation cache |

---

## Query & Template Hooks

| Hook | Value | Purpose |
|------|-------|---------|
| `permission_query_conditions` | `{"*": "construction.overrides.scope_query.add_scope_conditions"}` | Automatic company/cost center/project scope isolation across all database queries |
| `jinja` | `{"filters": ["construction.services.narrative_sanitizer.bdi_join"]}` | Directional isolation filter (`bdi_join`) for mixed Arabic/English print templates |

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

## Synchronization Status

All hook sections are synchronized against `construction/hooks.py`:
- `override_whitelisted_methods`: 4 active entries documented.
- `override_doctype_class`: 1 active entry documented.
- `doc_events`: 30 active DocType registrations (wildcard `*`, 8 transactional doctypes, 1 BOQ lifecycle, 19 bilingual masters, 1 payment term) documented.
- `permission_query_conditions` and `jinja.filters` documented.
- Asset Inclusion tables synchronized (26 JS, 6 CSS, web includes).

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
| 2026-10-03 | Synchronized Scope B: documented all 4 override_whitelisted_methods, override_doctype_class, query/Jinja filters, and 30 doc_events registrations |

---

*Last Updated: 2026-10-03*
