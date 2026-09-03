from . import __version__ as app_version

app_name = "construction"
app_title = "Construction ERP"
app_publisher = "Mohamed Elrefae"
app_description = "Construction ERP App for BOQ, Cost Estimation, and Project Management"
app_email = "melrefa3@hotmail.com"
app_license = "MIT"

# Hard install-time dependency: UOM fixtures, Item/Company custom fields,
# ERPNext standard filters, and accounting dimensions all require ERPNext.
# Declaring it makes install-app fail with a clear message instead of a
# cryptic missing-table error (e.g. tabUOM) on frappe-only sites.
required_apps = ["erpnext"]

# Module registration (fixes DocType import resolution)
modules = [
    {
        "module_name": "Construction",
        "color": "#3498db",
        "icon": "octicon octicon-file-directory",
        "type": "module",
        "label": "Construction",
    }
]

# v16 Desktop icon registration
# Displays the Construction app icon on the Desktop grid and in the Apps screen
add_to_apps_screen = [
    {
        "name": "construction",
        "logo": "/assets/construction/images/construction_logo.svg",
        "title": "Construction",
        "route": "/app/construction",
    }
]

module_app = {
    "construction": "construction",
}

# Module configuration - makes DocTypes visible in the Construction module menu
# These will appear in the Construction module's left sidebar
desk_links = {
    "Construction": [
        {
            "type": "doctype",
            "name": "Variation Order",
            "label": "Variation Order",
            "description": "Manage post-lock BOQ scope changes (Variation Orders)",
        },
        {
            "type": "doctype",
            "name": "Construction Theme",
            "label": "Theme Configuration",
            "description": "Manage construction themes and colors",
        },
        {
            "type": "doctype",
            "name": "Modern Theme Settings",
            "label": "Theme Settings",
            "description": "Configure site-wide theme settings",
        },
        {
            "type": "doctype",
            "name": "User Desk Theme",
            "label": "User Desk Theme",
            "description": "Manage per-user Desk theme and typography settings",
        },
        {
            "type": "doctype",
            "name": "User Scope Context",
            "label": "User Scope Context",
            "description": "Manage user company, cost center, project scope",
        },
        {
            "type": "doctype",
            "name": "Construction Settings",
            "label": "Scope Context Settings",
            "description": "Enable/disable scope context feature",
        },
        {
            "type": "doctype",
            "name": "BOQ Cost Analysis",
            "label": "BOQ Cost Analysis",
            "description": "Resource-based unit-rate analysis for BOQ Items",
        },
        {
            "type": "doctype",
            "name": "Resource Price History",
            "label": "Resource Price History",
            "description": "Auditable price ledger for construction resources",
        },
    ]
}

# Doctype-specific JavaScript files
# Paths are relative to the app module folder (construction/construction/)
doctype_js = {
    "BOQ Header": "construction/construction/doctype/boq_header/boq_header.js",
    "BOQ Item": "construction/construction/doctype/boq_item/boq_item.js",
    "BOQ Item Stage": "construction/construction/doctype/boq_item_stage/boq_item_stage.js",
    "Construction Settings": "construction/construction/doctype/construction_settings/construction_settings.js",
    "Scope Report Access Log": "construction/construction/doctype/scope_report_access_log/scope_report_access_log.js",
    "User Desk Theme": "construction/construction/doctype/user_desk_theme/user_desk_theme.js",
    "Variation Order": "construction/construction/doctype/variation_order/variation_order.js",
}

doctype_list_js = {
    "Item": "construction/public/js/item_list.js",
    "BOQ Item": "construction/construction/doctype/boq_item/boq_item_list.js",
    "BOQ Structure": "construction/construction/doctype/boq_structure/boq_structure_list.js",
    "Variation Order": "construction/construction/doctype/variation_order/variation_order_list.js",
}

doctype_tree_js = {"BOQ Structure": "construction/construction/doctype/boq_structure/boq_structure_tree.js"}

# CSS includes for authenticated users (desk)
# v2.2: Single-file theme — tokens + 1,180 selectors, html.ct-enterprise[data-theme] namespace
app_include_css = [
    "/assets/construction/css/modern_theme.css?v=2.5.8",
    "/assets/construction/css/scope_context.css?v=2",
    # ─── Vite UI — MUST load LAST to win cascade ───
    # Phase 1: Visual Foundation
    "/assets/construction/css/vite_extensions.css?v=1.3",
    "/assets/construction/css/vite_form_override.css?v=1.5",
    "/assets/construction/css/vite_list_override.css?v=1.3",
    # Phase 2: Form Layout Engine section card styles
    "/assets/construction/css/vfc_sections.css?v=1.6",
]

# Global JS includes (raw asset path — loaded directly, not bundled)
# CSS-only theming: theme_loader handles sync/navbar dropdown; theme_loader_v16 is a no-op safety net
app_include_js = [
    # Shared BOQ column definitions — must load before doctype JS that uses window.BOQ_EXPORT_COLUMNS
    "/assets/construction/js/boq_export_columns.js?v=1",
    "/assets/construction/js/print_settings_dialog.js",
    "/assets/construction/js/construction_export_menu.js",
    "/assets/construction/js/generic_export_menu.js?v=1",
    "/assets/construction/js/theme_loader_v24.js?v=2.6.1",
    "/assets/construction/js/typography_settings.js?v=21",
    # Searchable Dropdown Module — base class (must load before overrides)
    "/assets/construction/js/searchable_dropdown/utils.js",
    "/assets/construction/js/searchable_dropdown/searchable_dropdown.js",
    # Phase 2: Global ControlSelect override — searchable themed dropdown for all <select> fields
    # Replaces native HTML <select> app-wide (forms + report filters confirmed by diagnostic)
    "/assets/construction/js/overrides/ct_select_control.js?v=2",
    # Phase 3: Global ControlLink auto-enhancer — replaces 3 manual config files
    # Auto-applies SearchableDropdownEnhancer to all Link fields on every page
    "/assets/construction/js/overrides/ct_link_control.js?v=16",
    # v16 runtime safety net — no-op (CSS handles all styling)
    "/assets/construction/js/theme_loader_v16.js?v=2",
    # Scope Context — core class for managing user company/cost_center/project/dept scope
    "/assets/construction/js/scope_context.js?v=3",
    # Frappe Desk compatibility fixes that must run before list views initialize
    "/assets/construction/js/frappe_compat_patches.js?v=2",
    # Scope Context — navbar UI selectors (cascading company/cost_center/project/dept dropdowns)
    "/assets/construction/js/scope_context_ui.js?v=5",
    # Scope Context — list view auto-filtering
    "/assets/construction/js/scope_context_list_filter.js?v=3",
    # Scope Context — form default population for new documents
    "/assets/construction/js/scope_context_form_defaults.js?v=3",
    # Scope Context — report filter lock and dynamic sync
    "/assets/construction/js/vfc_config.js?v=1",
    # VFC debug log gating — must load BEFORE vite_layout_controls and vfc_layout_engine
    "/assets/construction/js/scope_context_report_filters.js?v=4",
    # CT List View Config — hides like column, collapses level-right, fixes dropdown z-index
    # Must load AFTER list view initializes but BEFORE user interaction
    "/assets/construction/js/ct_list_view_config.js?v=1",
    # Sidebar accordion — only one section stays expanded at a time
    "/assets/construction/js/sidebar_accordion.js?v=1",
    # Translation workflow helpers (Arabic backlog + filters + catalog workbench)
    "/assets/construction/js/translation_list_tools.js?v=6",
    # BOQ integration filters for transaction child rows
    "/assets/construction/js/boq_filters.js?v=8",
    # Filter fix — injected AFTER Frappe bundle to win cascade order
    "/assets/construction/js/filter_fix.js?v=11",
    # Must load last: native Frappe affordances remain available after theme styling
    "/assets/construction/js/native_frappe_controls_compat.js?v=9",
    # ─── Vite UI Phase 2: Form Config — auto-attaches to every form. MUST load LAST ───
    "/assets/construction/js/vite_layout_controls.js?v=1.21",
    # Phase 2: Generic Layout Engine — re-parents field wrappers per Form Layout Profile.
    # Must load AFTER vite_layout_controls.js (engine fires at 250ms, controls at 150ms).
    "/assets/construction/js/vfc_layout_engine.js?v=1.44",
]


# CSS includes for unauthenticated pages (login, etc.)
# v2.4-r3: modern_theme.css handles all theming including login
web_include_css = [
    "/assets/construction/css/modern_theme.css?v=2.5.8",
    "/assets/construction/css/email_theme.css",
]

# v2.4-r3: theme_loader_v24 handles namespace injection and theming for all pages
web_include_js = "/assets/construction/js/theme_loader_v24.js?v=2.6.1"

# ─── BRAND OVERRIDES & WEBSITE CONTEXT ───
brand_html = "construction/templates/includes/navbar_brand.html"
login_page_title = "Construction ERP — Login"
homepage = "index"

website_context = {
    "favicon": "/assets/construction/images/construction_logo.svg",
    "splash_image": "/assets/construction/images/construction_logo.svg",
    "brand_html": brand_html,
}

email_css = ["/assets/construction/css/email_theme.css"]

# ─── PDF & PRINT STYLING ───
print_css = "/assets/construction/css/print_theme.css"
pdf_header_html = "construction.api.theme_api.get_pdf_header"
pdf_footer_html = "construction.api.theme_api.get_pdf_footer"


# Override Frappe's theme switcher for custom integration
# Using simplified SQL-based version to avoid Python controller import issues
override_whitelisted_methods = {
    "frappe.core.doctype.user.user.switch_theme": "construction.overrides.switch_theme_simple.switch_theme",
    "frappe.utils.change_log.show_update_popup": "construction.api.theme_api.ignore_update_popup",
    "frappe.translate.update_translations_for_source": "construction.api.translation_tools.update_translations_for_source_safe",
}

# Override core Translation controller so edited catalog rows become runtime translations.
override_doctype_class = {
    "Translation": "construction.overrides.translation.CustomTranslation",
}

# Boot session hook - inject user's theme into frappe.boot
# This ensures the correct theme is available immediately on page load
boot_session = "construction.api.theme_api.add_theme_to_boot"

# Extend bootinfo with scope context data
extend_bootinfo = "construction.boot.extend_bootinfo"

# Server-side enforcement: branch-company integrity (always) + scope context (optional)
# validate runs on both insert AND update
doc_events = {
    "*": {"validate": "construction.overrides.scope_enforcement.validate"},
    "Purchase Order": {
        "validate": "construction.services.boq_transaction_validation.validate_document",
        "on_submit": "construction.services.resource_price_service.capture_price_from_purchase_document",
        "on_cancel": "construction.services.resource_price_service.cancel_price_history_for_document",
    },
    "Purchase Receipt": {"validate": "construction.services.boq_transaction_validation.validate_document"},
    "Purchase Invoice": {
        "validate": "construction.services.boq_transaction_validation.validate_document",
        "on_submit": "construction.services.resource_price_service.capture_price_from_purchase_document",
        "on_cancel": "construction.services.resource_price_service.cancel_price_history_for_document",
    },
    "Stock Entry": {"validate": "construction.services.boq_transaction_validation.validate_document"},
    "Timesheet": {"validate": "construction.services.boq_transaction_validation.validate_document"},
    "Journal Entry": {"validate": "construction.services.boq_transaction_validation.validate_document"},
    "Sales Invoice": {"validate": "construction.services.boq_transaction_validation.validate_document"},
    "Material Request": {"validate": "construction.services.boq_transaction_validation.validate_document"},
    "BOQ Item Stage": {"before_delete": "construction.services.boq_lifecycle.before_delete_boq_item_stage"},
}

# Server-side query injection: applies scope filters to ALL database queries
# Uses the wildcard '*' to fire for every doctype
permission_query_conditions = {
    "*": "construction.overrides.scope_query.add_scope_conditions",
}

# Fixtures - Phase 2: Construction Theme records
fixtures = [
    {"doctype": "Construction Theme", "filters": [["is_system_theme", "=", 1]]},
]

# Note: Workspace Sidebar is created via after_migrate hook, not fixture
# (DocType may not exist in all Frappe versions)

# After install - create system themes and setup Custom Fields
after_install = [
    "construction.install.setup_website_branding",
    "construction.install.create_system_themes",
    "construction.install.setup_boq_integration",
    "construction.install.setup_branch_company_field",
    "construction.install.setup_variation_order_custom_field",
    "construction.install.setup_erpnext_standard_filters",
    "construction.install.fix_select_permissions",
    "construction.install.fix_system_manager_permissions",
    "construction.install.seed_construction_roles",
    "construction.install.seed_form_layout_profiles",
    "construction.install.setup_item_construction_fields",
    "construction.setup.translation_catalog_fields.ensure_translation_identity",
    "construction.translation_service.import_released_overrides_hook",
]

# After migrate - ensure system themes and workspace sidebar exist
# Order matters: themes first, then sidebar, then health check
after_migrate = [
    "construction.api.theme_api.whitelabel_patch",
    "construction.install.setup_website_branding",
    "construction.install.create_system_themes",
    "construction.install.setup_workspace_sidebar",
    "construction.install.setup_construction_workspace_page",
    "construction.install.verify_workspace_visibility",
    "construction.install.setup_boq_integration",
    "construction.install.setup_branch_company_field",
    "construction.install.setup_variation_order_custom_field",
    "construction.install.setup_erpnext_standard_filters",
    "construction.install.fix_select_permissions",
    "construction.install.fix_system_manager_permissions",
    "construction.install.seed_construction_roles",
    "construction.install.seed_form_layout_profiles",
    "construction.install.setup_item_construction_fields",
    "construction.setup.translation_catalog_fields.ensure_translation_identity",
    "construction.translation_service.import_released_overrides_hook",
]

# Patches
patches = "construction.patches.txt"

# Translations
translated_doctypes = {
    "BOQ Header": ["ar"],
    "BOQ Item": ["ar"],
    "BOQ Item Stage": ["ar"],
    "BOQ Structure": ["ar"],
    "CostItem": ["ar"],
    "PlantResource": ["ar"],
    "BOQ Cost Analysis": ["ar"],
    "BOQ Cost Analysis Detail": ["ar"],
    "Resource Price History": ["ar"],
    "Construction Settings": ["ar"],
    "Construction Theme": ["ar"],
    "Direct Labor Designation": ["ar"],
    "Modern Theme Settings": ["ar"],
    "User Desk Theme": ["ar"],
    "User Scope Context": ["ar"],
    "Variation Order": ["ar"],
    "VO Line": ["ar"],
}
