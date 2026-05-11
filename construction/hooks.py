from . import __version__ as app_version

app_name = "construction"
app_title = "Construction ERP"
app_publisher = "Mohamed Elrefae"
app_description = "Construction ERP App for BOQ, Cost Estimation, and Project Management"
app_email = "melrefa3@hotmail.com"
app_license = "MIT"

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
			"name": "User Scope Context",
			"label": "User Scope Context",
			"description": "Manage user company, branch, project scope",
		},
	]
}

# Doctype-specific JavaScript files
# Paths are relative to the app module folder (construction/construction/)
doctype_js = {"BOQ Header": "construction/doctype/boq_header/boq_header.js"}

doctype_tree_js = {"BOQ Structure": "construction/doctype/boq_structure/boq_structure_tree.js"}

# CSS includes for authenticated users (desk)
# Load order is critical: tokens → variables_v16 → base → adapter
app_include_css = [
	"/assets/construction/css/modern_theme_tokens.css?v=20",
	"/assets/construction/css/modern_theme_variables_v16.css?v=2",
	"/assets/construction/css/modern_theme_base.css?v=30",
	"/assets/construction/css/modern_theme_v16_adapter.css?v=25",
]

# Global JS includes (raw asset path — loaded directly, not bundled)
# CSS-only theming: theme_loader handles sync/navbar dropdown; theme_loader_v16 is a no-op safety net
app_include_js = [
	"/assets/construction/js/print_settings_dialog.js",
	"/assets/construction/js/construction_export_menu.js",
	"/assets/construction/js/theme_loader.js?v=28",
	"/assets/construction/js/components/index.js?v=4.5",
	# Searchable Dropdown Module (Week 1)
	"/assets/construction/js/searchable_dropdown/utils.js",
	"/assets/construction/js/searchable_dropdown/searchable_dropdown.js",
	# Searchable Dropdown Form Scripts (Week 2/3)
	"/assets/construction/js/searchable_dropdown/config/journal_entry.js",
	"/assets/construction/js/searchable_dropdown/config/sales_invoice.js",
	"/assets/construction/js/searchable_dropdown/config/customer_supplier.js",
	# v16 runtime safety net — no-op (CSS handles all styling)
	"/assets/construction/js/theme_loader_v16.js?v=2",
]

# CSS includes for unauthenticated pages (login, etc.)
# Both light and dark themes loaded - JS toggles between them
web_include_css = [
	"/assets/construction/css/login_theme_light.css",
	"/assets/construction/css/email_theme.css"
]

# Add JS to handle login page theme toggle
web_include_js = "/assets/construction/js/login_theme_toggle.js"

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

# Fixtures - Phase 2: Construction Theme records
fixtures = [
	{"doctype": "Construction Theme", "filters": [["is_system_theme", "=", 1]]},
]

# Note: Workspace Sidebar is created via after_migrate hook, not fixture
# (DocType may not exist in all Frappe versions)

# After install - create system themes
after_install = "construction.install.create_system_themes"

# After migrate - ensure system themes and workspace sidebar exist
# Order matters: themes first, then sidebar, then health check
after_migrate = [
	"construction.api.theme_api.whitelabel_patch",
	"construction.install.create_system_themes",
	"construction.install.setup_workspace_sidebar",
	"construction.install.setup_construction_workspace_page",
	"construction.install.verify_workspace_visibility",
]
