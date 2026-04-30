# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_children(doctype, parent="", boq_header=None, is_root=False, **filters):
	"""Get children for BOQ Structure tree view."""
	conditions = "AND `boq_header` = %(boq_header)s" if is_root else ""
	parent_value = "" if is_root else parent

	parent_fields = ", `parent_structure` as parent" if not is_root else ""

	nodes = frappe.db.sql(
		f"""
		SELECT
			`name` as value,
			CONCAT(IFNULL(`wbs_code`,''), ' — ', `title`) as title,
			`is_group` as expandable
			{parent_fields}
		FROM `tabBOQ Structure`
		WHERE IFNULL(`parent_structure`, '') = %(parent)s
		AND `docstatus` < 2
		{conditions}
		ORDER BY `lft`
	""",
		{"parent": parent_value, "boq_header": boq_header},
		as_dict=True,
	)

	return nodes


@frappe.whitelist()
def add_node():
	"""Add a new BOQ Structure node from the tree view."""
	from frappe.desk.treeview import make_tree_args

	args = frappe.local.form_dict
	args.doctype = "BOQ Structure"
	args = make_tree_args(**args)

	parent = args.get("parent_structure") or args.get("parent") or ""
	if parent and frappe.db.exists("BOQ Structure", parent):
		args.parent_structure = parent
	else:
		args.parent_structure = ""

	doc = frappe.new_doc("BOQ Structure")
	doc.update(args)
	doc.old_parent = ""
	doc.insert()
	return doc.name


@frappe.whitelist()
def create_boq_node(boq_header, parent_structure=None, title=None, is_group=0):
	"""Create a new BOQ Structure node from the tree view."""
	try:
		# Get the parent structure if provided
		parent = parent_structure if parent_structure else ""

		# Create the BOQ Structure node
		doc = frappe.new_doc("BOQ Structure")
		doc.boq_header = boq_header
		doc.parent_structure = parent if parent else None
		doc.title = title or "New Node"
		doc.is_group = 1 if is_group else 0
		doc.insert()

		return {"success": True, "name": doc.name}
	except Exception as e:
		frappe.log_error(f"Error creating BOQ node: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def advance_boq_status(boq_header, target_status):
	"""Advance BOQ status to next state."""
	try:
		doc = frappe.get_doc("BOQ Header", boq_header)

		# Define valid transitions
		transitions = {"Draft": "Pricing", "Pricing": "Frozen", "Frozen": "Locked"}

		current_status = doc.status
		allowed_next = transitions.get(current_status)

		if target_status != allowed_next:
			return {
				"success": False,
				"error": f"Invalid status transition from {current_status}. Next status should be {allowed_next}",
			}

		# Update status
		doc.status = target_status
		doc.save()

		return {"success": True, "message": f"Status updated to {target_status}"}
	except Exception as e:
		frappe.log_error(f"Error advancing BOQ status: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def export_boq_excel(boq_header):
	"""Export BOQ to Excel."""
	try:
		from construction.services.boq_export_service import BOQExportService

		# Generate Excel file
		result = BOQExportService.export_to_excel(boq_header)

		if result.get("success"):
			return {
				"success": True,
				"message": "BOQ exported successfully",
				"file_url": result.get("file_url"),
				"file_name": result.get("file_name"),
			}
		else:
			return result

	except Exception as e:
		frappe.log_error(f"Excel export error: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def import_boq_excel(file_url, boq_header):
	"""Import BOQ from Excel."""
	try:
		from construction.services.boq_import_service import BOQImportService

		result = BOQImportService.import_from_excel(file_url, boq_header)

		return result
	except Exception as e:
		frappe.log_error(f"Excel import error: {e!s}")
		return {"success": False, "error": str(e)}
