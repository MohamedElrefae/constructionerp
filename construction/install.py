# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import json
import os

import frappe


# ---------------------------------------------------------------------------
# System Themes
# ---------------------------------------------------------------------------

SYSTEM_THEMES = [
	{
		"theme_name": "Light",
		"theme_type": "Custom Light",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2076FF",
		"emoji_icon": "☀️",
		"navbar_bg": "#FFFFFF",
		"sidebar_bg": "#F8FAFC",
		"surface_bg": "#FFFFFF",
		"body_bg": "#F5F6FA",
		"text_primary": "#2C3E50",
		"text_secondary": "#7F8C8D",
		"border_color": "#D5DADF",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
	{
		"theme_name": "Dark",
		"theme_type": "Custom Dark",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2076FF",
		"emoji_icon": "🌙",
		"navbar_bg": "#1E1E1E",
		"sidebar_bg": "#2D2D2D",
		"surface_bg": "#3A3A3A",
		"body_bg": "#1A1A1A",
		"text_primary": "#E8E8E8",
		"text_secondary": "#A8A8A8",
		"border_color": "#4A4A4A",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
	{
		"theme_name": "Construction Light",
		"theme_type": "Construction Light",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2E7D32",
		"emoji_icon": "🏗️",
		"navbar_bg": "#F0FDF4",
		"sidebar_bg": "#F0FDF4",
		"surface_bg": "#FFFFFF",
		"body_bg": "#F0FDF4",
		"text_primary": "#181C23",
		"text_secondary": "#6B7280",
		"border_color": "#E2E6ED",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
	{
		"theme_name": "Construction Dark",
		"theme_type": "Construction Dark",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#4CAF50",
		"emoji_icon": "🏗️",
		"navbar_bg": "#1A3A1E",
		"sidebar_bg": "#0D1F12",
		"surface_bg": "#1f2937",
		"body_bg": "#111A13",
		"text_primary": "#EDEDED",
		"text_secondary": "#9CA3AF",
		"border_color": "#393C43",
		"success_color": "#28a745",
		"warning_color": "#ffc107",
		"error_color": "#dc3545",
	},
]


def create_system_themes():
	"""Idempotent creation of the 4 system themes.

	Called by after_install and after_migrate hooks.
	Does NOT call frappe.db.commit() — Frappe manages the transaction.
	"""
	for theme_data in SYSTEM_THEMES:
		if not frappe.db.exists("Construction Theme", theme_data["theme_name"]):
			doc = frappe.get_doc({"doctype": "Construction Theme", **theme_data})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Workspace Sidebar Reconciler (v16+)
# ---------------------------------------------------------------------------


def setup_workspace_sidebar():
	"""Reconcile the Construction workspace sidebar to the desired state.

	Uses a reconciler pattern: always rebuilds the items child table to
	guarantee correct state, regardless of what currently exists in the DB.

	Loads configuration from fixtures/workspace_sidebar_items.json so that
	navigation structure changes don't require code deployments.

	Called by after_migrate hook. Does NOT call frappe.db.commit() —
	Frappe's migration runner manages the transaction boundary.

	Skips gracefully on Frappe versions that don't have Workspace Sidebar
	(v15 and earlier).
	"""
	# Feature detection: skip if Workspace Sidebar doesn't exist (v15)
	if not frappe.db.table_exists("Workspace Sidebar"):
		return

	# Load configuration from JSON fixture
	config_path = os.path.join(
		frappe.get_app_path("construction"), "fixtures", "workspace_sidebar_items.json"
	)
	if not os.path.exists(config_path):
		frappe.log_error(
			f"Workspace sidebar config not found: {config_path}",
			"Construction Setup",
		)
		return

	with open(config_path) as f:
		config = json.load(f)

	# Get or create the sidebar record
	# ignore_permissions is required because after_migrate runs as Administrator
	# but Workspace Sidebar may have restrictive permissions on custom apps
	if frappe.db.exists("Workspace Sidebar", config["title"]):
		sidebar = frappe.get_doc("Workspace Sidebar", config["title"])
	else:
		sidebar = frappe.new_doc("Workspace Sidebar")

	# Reconcile top-level fields
	sidebar.title = config["title"]
	sidebar.module = config["module"]
	sidebar.app = config["app"]
	sidebar.header_icon = config["header_icon"]
	sidebar.standard = 0  # standard=0 for custom apps to allow uninstallation

	# Reconcile items: clear and rebuild to guarantee correct state
	sidebar.items = []
	for item_data in config.get("items", []):
		sidebar.append("items", item_data)

	sidebar.save(ignore_permissions=True)

	# Invalidate workspace-related caches
	_invalidate_workspace_caches()


def _invalidate_workspace_caches():
	"""Clear workspace and sidebar caches after reconciliation.

	Frappe aggressively caches workspace sidebars and desktop metadata.
	Without explicit invalidation, changes may not be visible until
	server restart.
	"""
	try:
		frappe.cache().delete_key("workspace_sidebar")
		frappe.cache().delete_key("desktop_icons")
		# Clear user-specific bootinfo cache for all enabled users
		for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
			frappe.cache().hdel("bootinfo", user)
	except Exception:
		# Cache clearing is best-effort; don't fail the migration
		pass


# ---------------------------------------------------------------------------
# Post-Migrate Health Check
# ---------------------------------------------------------------------------


def verify_workspace_visibility():
	"""Post-migrate health check for workspace visibility.

	Logs errors if the Construction workspace is not properly configured.
	Does NOT raise exceptions — migration should not fail due to a
	visibility check.

	Skips gracefully on Frappe versions without Workspace Sidebar.
	"""
	errors = []

	# Check Workspace record exists
	if not frappe.db.exists("Workspace", "Construction"):
		errors.append("Workspace 'Construction' missing from tabWorkspace")
	else:
		ws = frappe.db.get_value(
			"Workspace",
			"Construction",
			["type", "public", "is_hidden", "module"],
			as_dict=True,
		)
		if not ws.get("type"):
			errors.append("Workspace 'Construction' has null type (must be 'Workspace' for v16)")
		if not ws.get("public"):
			errors.append("Workspace 'Construction' is not public")
		if ws.get("is_hidden"):
			errors.append("Workspace 'Construction' is hidden")

	# Check Workspace Sidebar (v16+)
	if frappe.db.table_exists("Workspace Sidebar"):
		if not frappe.db.exists("Workspace Sidebar", "Construction"):
			errors.append("Workspace Sidebar 'Construction' missing")
		else:
			item_count = frappe.db.count(
				"Workspace Sidebar Item",
				filters={"parent": "Construction"},
			)
			if item_count == 0:
				errors.append("Workspace Sidebar 'Construction' has no items")

	# Check add_to_apps_screen hook
	apps_screen = frappe.get_hooks("add_to_apps_screen") or []
	has_construction = any(
		app.get("name") == "construction" for app in apps_screen if isinstance(app, dict)
	)
	if not has_construction:
		errors.append("add_to_apps_screen missing 'construction' entry in hooks.py")

	if errors:
		frappe.log_error(
			"Workspace Visibility Health Check Failed:\n" + "\n".join(f"  - {e}" for e in errors),
			"Construction Workspace Health Check",
		)
	else:
		frappe.logger().info("Construction workspace health check: PASSED")
