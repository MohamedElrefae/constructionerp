from . import __version__ as app_version

app_name = "construction"
app_title = "Construction ERP"
app_publisher = "Mohamed Elrefae"
app_description = "Construction ERP App for BOQ, Cost Estimation, and Project Management"
app_email = "melrefa3@hotmail.com"
app_license = "MIT"

# Module registration (fixes DocType import resolution)
modules = [
	{
		"module_name": "Construction",
		"color": "#3498db",
		"icon": "octicon octicon-file-directory",
		"type": "module",
		"label": "Construction"
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
	]
}

# Doctype-specific JavaScript files
# Paths are relative to the app module folder (construction/construction/)
doctype_js = {
    "BOQ Header": "construction/doctype/boq_header/boq_header.js",
    "Construction Settings": "construction/doctype/construction_settings/construction_settings.js",
    "User Desk Theme": "construction/doctype/user_desk_theme/user_desk_theme.js",
}

doctype_tree_js = {"BOQ Structure": "construction/doctype/boq_structure/boq_structure_tree.js"}

# CSS includes for authenticated users (desk)
# v2.2: Single-file theme — tokens + 1,180 selectors, html.ct-enterprise[data-theme] namespace
app_include_css = [
    "/assets/construction/css/modern_theme.css?v=2.5.3",
    "/assets/construction/css/scope_context.css?v=2",
]

# Global JS includes (raw asset path — loaded directly, not bundled)
# CSS-only theming: theme_loader handles sync/navbar dropdown; theme_loader_v16 is a no-op safety net
app_include_js = [
	"/assets/construction/js/print_settings_dialog.js",
	"/assets/construction/js/construction_export_menu.js",
	"/assets/construction/js/theme_loader_v24.js?v=2.5.2",
	"/assets/construction/js/typography_settings.js?v=3",
	"/assets/construction/js/components/index.js?v=4.6",
	# Searchable Dropdown Module — base class (must load before overrides)
	"/assets/construction/js/searchable_dropdown/utils.js",
	"/assets/construction/js/searchable_dropdown/searchable_dropdown.js",
	# Phase 2: Global ControlSelect override — searchable themed dropdown for all <select> fields
	# Replaces native HTML <select> app-wide (forms + report filters confirmed by diagnostic)
	"/assets/construction/js/overrides/ct_select_control.js?v=3",
	# Phase 3: Global ControlLink auto-enhancer — replaces 3 manual config files
	# Auto-applies SearchableDropdownEnhancer to all Link fields on every page
	"/assets/construction/js/overrides/ct_link_control.js?v=2",
	# v16 runtime safety net — no-op (CSS handles all styling)
	"/assets/construction/js/theme_loader_v16.js?v=2",
	# Scope Context — core class for managing user company/cost_center/project/dept scope
	"/assets/construction/js/scope_context.js?v=1",
	# Scope Context — navbar UI selectors (cascading company/cost_center/project/dept dropdowns)
	"/assets/construction/js/scope_context_ui.js?v=1",
	# Scope Context — list view auto-filtering
	"/assets/construction/js/scope_context_list_filter.js?v=1",
	# Scope Context — form default population for new documents
	"/assets/construction/js/scope_context_form_defaults.js?v=1",
	# Sidebar accordion — only one section stays expanded at a time
	"/assets/construction/js/sidebar_accordion.js?v=2",
	# Filter fix — injected AFTER Frappe bundle to win cascade order
	# Must be LAST to guarantee it loads after desk.bundle.css
	"/assets/construction/js/filter_fix.js?v=4.1",
]


# CSS includes for unauthenticated pages (login, etc.)
# v2.4-r3: modern_theme.css handles all theming including login
web_include_css = [
    "/assets/construction/css/modern_theme.css?v=2.5.3",
	"/assets/construction/css/email_theme.css"
]

# v2.4-r3: theme_loader_v24 handles namespace injection and theming for all pages
web_include_js = "/assets/construction/js/theme_loader_v24.js?v=2.5.2"

# ─── BRAND OVERRIDES & WEBSITE CONTEXT ───
brand_html = "construction/templates/includes/navbar_brand.html"
login_page_title = "Construction ERP — Login"

website_context = {
    "favicon": "/assets/construction/images/construction_logo.svg",
    "splash_image": "/assets/construction/images/construction_logo.svg",
    "brand_html": brand_html,
}

email_css = [
    "/assets/construction/css/email_theme.css"
]

# ─── PDF & PRINT STYLING ───
print_css = "/assets/construction/css/print_theme.css"
pdf_header_html = "construction.api.theme_api.get_pdf_header"
pdf_footer_html = "construction.api.theme_api.get_pdf_footer"



# Override Frappe's theme switcher for custom integration
# Using simplified SQL-based version to avoid Python controller import issues
override_whitelisted_methods = {
	"frappe.core.doctype.user.user.switch_theme": "construction.overrides.switch_theme_simple.switch_theme",
	"frappe.utils.change_log.show_update_popup": "construction.api.theme_api.ignore_update_popup"
}

# Boot session hook - inject user's theme into frappe.boot
# This ensures the correct theme is available immediately on page load
boot_session = "construction.api.theme_api.add_theme_to_boot"

# Extend bootinfo with scope context data
extend_bootinfo = "construction.boot.extend_bootinfo"

# Server-side enforcement: branch-company integrity (always) + scope context (optional)
# validate runs on both insert AND update
doc_events = {
    "*": {
        "validate": "construction.overrides.scope_enforcement.validate"
    }
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
	"construction.install.create_system_themes",
	"construction.install.setup_branch_company_field",
	"construction.insert_translations.execute",
]

# After migrate - ensure system themes and workspace sidebar exist
# Order matters: themes first, then sidebar, then health check
after_migrate = [
	"construction.api.theme_api.whitelabel_patch",
	"construction.install.create_system_themes",
	"construction.install.setup_workspace_sidebar",
	"construction.install.setup_construction_workspace_page",
	"construction.install.verify_workspace_visibility",
	"construction.install.setup_branch_company_field",
	"construction.insert_translations.execute",
]

# Translations
translated_doctypes = {
	"BOQ Header": ["ar"],
	"BOQ Item": ["ar"],
	"BOQ Structure": ["ar"],
	"CostItem": ["ar"],
	"PlantResource": ["ar"],
	"Construction Settings": ["ar"],
	"Construction Theme": ["ar"],
	"Modern Theme Settings": ["ar"],
	"User Desk Theme": ["ar"],
	"User Scope Context": ["ar"],
}
