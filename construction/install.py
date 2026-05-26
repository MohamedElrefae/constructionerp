# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import json
import os

import frappe


# ---------------------------------------------------------------------------
# BOQ Integration Setup
# ---------------------------------------------------------------------------

BOQ_DIMENSION_NAME = "BOQ Item"
BOQ_DIMENSION_DOCTYPE = "BOQ Item"

BOQ_TRANSACTION_CHILD_DOCTYPES = (
	"Purchase Order Item",
	"Purchase Receipt Item",
	"Purchase Invoice Item",
	"Stock Entry Detail",
	"Timesheet Detail",
	"Journal Entry Account",
	"Sales Invoice Item",
	"Material Request Item",
)

BOQ_CASCADE_INSERT_AFTER = {
	"Purchase Order Item": "expense_category",
	"Purchase Receipt Item": "expense_category",
	"Purchase Invoice Item": "expense_category",
	"Stock Entry Detail": "expense_category",
	"Timesheet Detail": "activity_type",
	"Journal Entry Account": "account",
	"Sales Invoice Item": "is_progress_billing",
	"Material Request Item": "expense_category",
}

BOQ_EXPENSE_CATEGORY_INSERT_AFTER = {
	"Purchase Order Item": "item_code",
	"Purchase Receipt Item": "item_code",
	"Purchase Invoice Item": "cost_center",
	"Stock Entry Detail": "item_code",
	"Journal Entry Account": "account",
	"Material Request Item": "item_code",
}

BOQ_CASCADE_DEPENDS_ON = {
	"Purchase Order Item": "eval:doc.expense_category == 'Direct'",
	"Purchase Receipt Item": "eval:doc.expense_category == 'Direct'",
	"Purchase Invoice Item": "eval:doc.expense_category == 'Direct'",
	"Stock Entry Detail": "eval:doc.expense_category == 'Direct'",
	"Journal Entry Account": "eval:doc.expense_category == 'Direct'",
	"Material Request Item": "eval:doc.expense_category == 'Direct'",
	"Sales Invoice Item": "eval:doc.is_progress_billing",
	"Timesheet Detail": (
		"eval:frappe.boot.direct_labor_designations "
		"&& frappe.boot.direct_labor_designations.includes(doc.designation)"
	),
}

BOQ_EXPENSE_CATEGORY_DOCTYPES = {
	"Purchase Order Item",
	"Purchase Receipt Item",
	"Purchase Invoice Item",
	"Stock Entry Detail",
	"Journal Entry Account",
	"Material Request Item",
}

BOQ_LEGACY_EXPENSE_CATEGORY_HIDE_DOCTYPES = {
	"Sales Invoice Item",
	"Timesheet Detail",
}

BOQ_CASCADE_FIELDNAMES = (
	"boq_header",
	"boq_structure",
	"boq_item",
	"boq_item_stage",
	"boq_selection_scope_type",
)

DIRECT_LABOR_DESIGNATION_DEFAULTS = (
	("Site Worker", "Mandatory"),
	("Mason", "Mandatory"),
	("Carpenter", "Mandatory"),
	("Steel Fixer", "Mandatory"),
	("Operator", "Mandatory"),
	("Electrician", "Mandatory"),
	("Plumber", "Mandatory"),
	("Site Engineer", "Optional"),
	("Site Supervisor", "Optional"),
	("Foreman", "Optional"),
	("Project Manager", "Not Applicable"),
)


def setup_boq_integration():
	"""Idempotently provision BOQ accounting and operational fields."""
	setup_boq_accounting_dimension()
	setup_boq_custom_fields()
	setup_boq_indexes()
	setup_boq_rollout_mode()
	setup_direct_labor_designations()


def setup_boq_accounting_dimension():
	if not frappe.db.exists("DocType", BOQ_DIMENSION_DOCTYPE):
		return
	if not frappe.db.exists("DocType", "Accounting Dimension"):
		return

	dimension_name = frappe.db.get_value(
		"Accounting Dimension", {"document_type": BOQ_DIMENSION_DOCTYPE}, "name"
	)

	if dimension_name:
		dimension = frappe.get_doc("Accounting Dimension", dimension_name)
		if dimension.disabled:
			dimension.disabled = 0
			dimension.save(ignore_permissions=True)
	else:
		dimension = frappe.new_doc("Accounting Dimension")
		dimension.document_type = BOQ_DIMENSION_DOCTYPE
		dimension.label = BOQ_DIMENSION_NAME
		dimension.insert(ignore_permissions=True)

	_sync_boq_dimension_fields(dimension)


def _sync_boq_dimension_fields(dimension):
	try:
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			make_dimension_in_accounting_doctypes,
		)
	except Exception:
		frappe.log_error(
			"ERPNext Accounting Dimension sync function could not be imported",
			"BOQ Integration Setup",
		)
		return

	make_dimension_in_accounting_doctypes(doc=dimension)


def setup_boq_custom_fields():
	if not frappe.db.exists("DocType", "Custom Field"):
		return

	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field
	except Exception:
		frappe.log_error("Custom Field API could not be imported", "BOQ Integration Setup")
		return

	for doctype in BOQ_TRANSACTION_CHILD_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		meta = frappe.get_meta(doctype, cached=False)
		for field in _get_boq_custom_fields_for_doctype(doctype):
			field_def = field.copy()
			field_def["insert_after"] = _resolve_insert_after(meta, field_def.get("insert_after"))
			_sync_custom_field(doctype, field_def, create_custom_field)
			frappe.clear_cache(doctype=doctype)
			meta = frappe.get_meta(doctype, cached=False)
		_hide_legacy_expense_category_field(doctype)


def _get_boq_custom_fields_for_doctype(doctype):
	fields = []
	if doctype in BOQ_EXPENSE_CATEGORY_DOCTYPES:
		fields.append(
			{
				"fieldname": "expense_category",
				"fieldtype": "Select",
				"options": "\nDirect\nIndirect\nOverhead\nCapital",
				"label": "Expense Category",
				"default": "" if doctype == "Journal Entry Account" else "Direct",
				"insert_after": BOQ_EXPENSE_CATEGORY_INSERT_AFTER.get(doctype),
				"hidden": 0,
				"read_only": 0,
				"description": "Set to Direct to unlock BOQ attribution fields.",
			}
		)
	elif doctype == "Sales Invoice Item":
		fields.append(
			{
				"fieldname": "is_progress_billing",
				"fieldtype": "Check",
				"label": "Progress Billing",
				"default": "0",
				"insert_after": "item_code",
				"hidden": 0,
				"read_only": 0,
			}
		)
	elif doctype == "Timesheet Detail":
		fields.append(
			{
				"fieldname": "designation",
				"fieldtype": "Data",
				"label": "Employee Designation",
				"insert_after": "activity_type",
				"hidden": 1,
				"read_only": 1,
				"no_copy": 1,
			}
		)

	base_gate = BOQ_CASCADE_DEPENDS_ON.get(doctype, "eval:doc.expense_category == 'Direct'")
	base_expr = _strip_eval(base_gate)

	fields.extend(
		[
			{
				"fieldname": "boq_header",
				"fieldtype": "Link",
				"options": "BOQ Header",
				"label": "BOQ Header",
				"insert_after": BOQ_CASCADE_INSERT_AFTER.get(doctype),
				"depends_on": None,
				"read_only_depends_on": f"eval:!({base_expr})",
				"hidden": 0,
				"read_only": 0,
				"description": "Locked until the row is applicable for direct BOQ attribution.",
			},
			{
				"fieldname": "boq_structure",
				"fieldtype": "Link",
				"options": "BOQ Structure",
				"label": "BOQ Structure",
				"insert_after": "boq_header",
				"depends_on": None,
				"read_only_depends_on": f"eval:!doc.boq_header || !({base_expr})",
				"hidden": 0,
				"read_only": 0,
				"description": "Locked until a BOQ Header is selected.",
			},
			{
				"fieldname": "boq_item",
				"fieldtype": "Link",
				"options": "BOQ Item",
				"label": "BOQ Item",
				"insert_after": "boq_structure",
				"depends_on": None,
				"read_only_depends_on": f"eval:!doc.boq_header || !doc.boq_structure || !({base_expr})",
				"hidden": 0,
				"read_only": 0,
				"description": "Locked until BOQ Header and BOQ Structure are selected.",
			},
			{
				"fieldname": "boq_item_stage",
				"fieldtype": "Link",
				"options": "BOQ Item Stage",
				"label": "BOQ Item Stage",
				"insert_after": "boq_item",
				"depends_on": None,
				"read_only_depends_on": f"eval:!doc.boq_item || !({base_expr})",
				"hidden": 0,
				"read_only": 0,
				"description": "Locked until a BOQ Item is selected.",
			},
			{
				"fieldname": "boq_selection_scope_type",
				"fieldtype": "Select",
				"options": "\nProject-Scoped\nCompany-CostCenter-Scoped",
				"label": "BOQ Selection Scope Type",
				"insert_after": "boq_item_stage",
				"hidden": 1,
				"read_only": 1,
				"no_copy": 1,
			},
		]
	)
	return fields


def _sync_custom_field(doctype, field_def, create_custom_field):
	meta = frappe.get_meta(doctype, cached=False)
	fieldname = field_def["fieldname"]
	custom_field_name = frappe.db.get_value(
		"Custom Field", {"dt": doctype, "fieldname": fieldname}, "name"
	)

	if not custom_field_name and meta.has_field(fieldname):
		return

	if not custom_field_name:
		create_custom_field(doctype, field_def, ignore_validate=True)
		return

	doc = frappe.get_doc("Custom Field", custom_field_name)
	changed = False
	for key, value in field_def.items():
		if getattr(doc, key, None) != value:
			setattr(doc, key, value)
			changed = True
	if changed:
		doc.save(ignore_permissions=True)


def _hide_legacy_expense_category_field(doctype):
	if doctype not in BOQ_LEGACY_EXPENSE_CATEGORY_HIDE_DOCTYPES:
		return

	custom_field_name = frappe.db.get_value(
		"Custom Field", {"dt": doctype, "fieldname": "expense_category"}, "name"
	)
	if not custom_field_name:
		return

	doc = frappe.get_doc("Custom Field", custom_field_name)
	changed = False
	for key, value in {
		"hidden": 1,
		"read_only": 1,
		"no_copy": 1,
		"description": "Legacy BOQ expense gate hidden; this DocType uses its own BOQ cascade gate.",
	}.items():
		if getattr(doc, key, None) != value:
			setattr(doc, key, value)
			changed = True
	if changed:
		doc.save(ignore_permissions=True)


def _default_insert_anchor(doctype):
	return BOQ_CASCADE_INSERT_AFTER.get(doctype) or "project"


def _strip_eval(expression):
	return (expression or "").replace("eval:", "", 1)


def _resolve_insert_after(meta, preferred_field):
	if preferred_field and meta.has_field(preferred_field):
		return preferred_field

	for fallback in ("project", "item_code", "account", "activity_type"):
		if meta.has_field(fallback):
			return fallback

	fields = meta.get("fields") or []
	return fields[-1].fieldname if fields else None


def setup_boq_indexes():
	indexes = (
		("BOQ Header", ["project"], "idx_boq_header_project"),
		("BOQ Structure", ["boq_header", "is_group"], "idx_boq_structure_header_group"),
		("BOQ Item", ["boq_header", "structure"], "idx_boq_item_header_structure"),
		("BOQ Item Stage", ["boq_item"], "idx_boq_item_stage_item"),
	)
	for doctype, fields, index_name in indexes:
		if not frappe.db.table_exists(doctype):
			continue
		if not all(frappe.db.has_column(doctype, field) for field in fields):
			continue
		if _index_exists(doctype, index_name):
			continue
		try:
			frappe.db.add_index(doctype, fields, index_name)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Failed to add BOQ cascade index {index_name}",
			)


def _index_exists(doctype, index_name):
	return bool(
		frappe.db.sql(
			"""
			SELECT 1
			FROM information_schema.statistics
			WHERE table_schema = DATABASE()
			  AND table_name = %(table_name)s
			  AND index_name = %(index_name)s
			LIMIT 1
			""",
			{"table_name": f"tab{doctype}", "index_name": index_name},
		)
	)


def setup_direct_labor_designations():
	if not frappe.db.exists("DocType", "Construction Settings"):
		return
	if not frappe.db.table_exists("Direct Labor Designation"):
		return
	if not frappe.get_meta("Construction Settings", cached=False).has_field("direct_labor_designations"):
		return

	settings = frappe.get_single("Construction Settings")
	existing = {
		row.designation for row in (settings.get("direct_labor_designations") or []) if row.designation
	}
	available_designations = {
		row.name
		for row in frappe.get_all(
			"Designation",
			filters={"name": ["in", [item[0] for item in DIRECT_LABOR_DESIGNATION_DEFAULTS]]},
			fields=["name"],
		)
	}
	changed = False
	for designation, requirement in DIRECT_LABOR_DESIGNATION_DEFAULTS:
		if designation in existing or designation not in available_designations:
			continue
		settings.append(
			"direct_labor_designations",
			{"designation": designation, "boq_requirement": requirement},
		)
		changed = True
	if changed:
		settings.save(ignore_permissions=True)


def setup_boq_rollout_mode():
	if not frappe.db.exists("DocType", "Construction Settings"):
		return
	if not frappe.get_meta("Construction Settings", cached=False).has_field(
		"enable_boq_cascade_filtering"
	):
		return

	current = frappe.db.sql(
		"""
		SELECT value
		FROM `tabSingles`
		WHERE doctype = %(doctype)s
		  AND field = %(field)s
		""",
		{
			"doctype": "Construction Settings",
			"field": "enable_boq_cascade_filtering",
		},
		as_dict=True,
	)
	current_value = current[0].value if current else None
	if current_value in {"Off", "On", "Strict"}:
		return
	if current:
		frappe.db.sql(
			"""
			UPDATE `tabSingles`
			SET value = %(value)s
			WHERE doctype = %(doctype)s
			  AND field = %(field)s
			""",
			{
				"value": "Off",
				"doctype": "Construction Settings",
				"field": "enable_boq_cascade_filtering",
			},
		)
	else:
		frappe.db.set_single_value(
			"Construction Settings", "enable_boq_cascade_filtering", "Off"
		)


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
		"accent_primary": "#2563EB",
		"emoji_icon": "🏗️",
		"navbar_bg": "#FFFFFF",
		"sidebar_bg": "#F8FAFC",
		"surface_bg": "#FFFFFF",
		"body_bg": "#F8FAFC",
		"text_primary": "#0F172A",
		"text_secondary": "#64748B",
		"border_color": "#E2E8F0",
		"success_color": "#16A34A",
		"warning_color": "#D97706",
		"error_color": "#DC2626",
	},
	{
		"theme_name": "Construction Dark",
		"theme_type": "Construction Dark",
		"is_system_theme": 1,
		"is_active": 1,
		"accent_primary": "#2563EB",
		"emoji_icon": "🏗️",
		"navbar_bg": "#1E293B",
		"sidebar_bg": "#0F172A",
		"surface_bg": "#1E293B",
		"body_bg": "#0F172A",
		"text_primary": "#F8FAFC",
		"text_secondary": "#94A3B8",
		"border_color": "#334155",
		"success_color": "#22C55E",
		"warning_color": "#F59E0B",
		"error_color": "#EF4444",
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
# Branch.company Custom Field (required for HR integrity)
# ---------------------------------------------------------------------------


def setup_branch_company_field():
	"""Create Branch.company Custom Field if missing.

	Called by after_install hook and by patch.
	Does NOT call frappe.db.commit() — caller manages the transaction.
	"""
	if not frappe.db.exists("DocType", "Branch"):
		return
	if not frappe.db.exists("Custom Field", {"dt": "Branch", "fieldname": "company"}):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Branch",
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"insert_after": "branch",
			"in_list_view": 1,
			"in_standard_filter": 1,
		}).insert()


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
		frappe.get_app_path("construction"), "config", "workspace_sidebar_items.json"
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


def setup_construction_workspace_page():
	"""Reconcile the Construction workspace page and sidebar.

	The Workspace document controls the main Construction home page. The
	Workspace Sidebar document controls the left navigation. Both must be
	reconciled from source files so cloud deployments do not depend on local
	database edits.
	"""
	workspace_path = os.path.join(
		frappe.get_app_path("construction"), "workspace", "construction", "construction.json"
	)
	if os.path.exists(workspace_path):
		with open(workspace_path) as f:
			workspace_data = json.load(f)

		if frappe.db.exists("Workspace", "Construction"):
			workspace = frappe.get_doc("Workspace", "Construction")
			for fieldname in (
				"label",
				"title",
				"module",
				"icon",
				"public",
				"is_hidden",
				"content",
				"parent_page",
			):
				if fieldname in workspace_data:
					workspace.set(fieldname, workspace_data[fieldname])
			for child_table in ("links", "shortcuts", "charts", "number_cards", "quick_lists", "custom_blocks"):
				if child_table in workspace_data:
					workspace.set(child_table, [])
					for row in workspace_data.get(child_table) or []:
						workspace.append(child_table, row)
		else:
			workspace = frappe.get_doc(workspace_data)

		workspace.save(ignore_permissions=True)

	if frappe.db.table_exists("Workspace Sidebar"):
		setup_workspace_sidebar()


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
		try:
			# Get available columns - Workspace schema varies by Frappe version
			ws = frappe.db.get_value(
				"Workspace",
				"Construction",
				["public", "is_hidden", "module"],
				as_dict=True,
			)
			if not ws.get("public"):
				errors.append("Workspace 'Construction' is not public")
			if ws.get("is_hidden"):
				errors.append("Workspace 'Construction' is hidden")
		except Exception as e:
			# Column may not exist in this Frappe version
			pass

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
