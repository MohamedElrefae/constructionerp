from . import __version__ as app_version

app_name = "construction"
app_title = "Construction ERP"
app_publisher = "Mohamed Elrefae"
app_description = "Construction ERP App for BOQ, Cost Estimation, and Project Management"
app_email = "melrefa3@hotmail.com"
app_license = "MIT"

module_app = {
    "Construction": "construction",
}

# Module configuration - makes DocTypes visible in the Construction module menu
# These will appear in the Construction module's left sidebar
desk_links = {
    "Construction": [
        {
            "type": "doctype",
            "name": "Construction Theme",
            "label": "Theme Configuration",
            "description": "Manage construction themes and colors"
        },
        {
            "type": "doctype",
            "name": "Modern Theme Settings",
            "label": "Theme Settings",
            "description": "Configure site-wide theme settings"
        }
    ]
}

# Doctype-specific JavaScript files
# Paths are relative to the app module folder (construction/construction/)
doctype_js = {
    "BOQ Header": "construction/doctype/boq_header/boq_header.js"
}

doctype_tree_js = {
    "BOQ Structure": "construction/doctype/boq_structure/boq_structure_tree.js"
}

# Global JS includes (raw asset path — loaded directly, not bundled)
# Phase 2: v3 is API-driven, v2 kept as fallback
app_include_js = [
    "/assets/construction/js/print_settings_dialog.js",
    "/assets/construction/js/construction_export_menu.js",
    "/assets/construction/js/modern_theme_loader_v2.js?v=52",  # v5.2 - Dark theme + layout fix
    "/assets/construction/js/components/index.js"
]

# Global CSS includes for Modern Theme
app_include_css = [
    "/assets/construction/css/modern_theme_tokens.css",
    "/assets/construction/css/modern_theme_light.css",
    "/assets/construction/css/modern_theme_dark.css",
    "/assets/construction/css/modern_theme_base.css",
    "/assets/construction/css/modern_theme_components.css",
    "/assets/construction/css/modern_theme_forms.css",
    "/assets/construction/css/modern_theme_tree.css",
    "/assets/construction/css/modern_theme_sidebar.css",
    "/assets/construction/css/modern_theme_layout.css",
    "/assets/construction/css/modern_theme_switcher.css",
    "/assets/construction/css/construction_theme_components.css"
]

# CSS includes for unauthenticated pages (login, etc.)
web_include_css = [
    "/assets/construction/css/login_theme.css"
]

# Override Frappe's theme switcher for custom integration
# Using simplified SQL-based version to avoid Python controller import issues
override_whitelisted_methods = {
    "frappe.core.doctype.user.user.switch_theme": "construction.overrides.switch_theme_simple.switch_theme"
}

# Fixtures - Phase 2: Construction Theme records
fixtures = [
    {
        "doctype": "Construction Theme",
        "filters": [["is_system_theme", "=", 1]]
    }
]

# After install - create system themes
after_install = "construction.install.create_system_themes"

# After migrate - ensure system themes exist
after_migrate = "construction.install.create_system_themes"
