import frappe


def get_header_for_item(boq_item_name):
	return frappe.db.get_value("BOQ Item", boq_item_name, "boq_header")


def get_project_for_header(boq_header_name):
	return frappe.db.get_value("BOQ Header", boq_header_name, "project")


def get_status_for_header(boq_header_name):
	return frappe.db.get_value("BOQ Header", boq_header_name, "status")


def get_stages_for_item(boq_item_name, exclude_name=None):
	filters = {"boq_item": boq_item_name, "docstatus": ["!=", 2]}
	if exclude_name:
		filters["name"] = ["!=", exclude_name]

	return frappe.get_all("BOQ Item Stage", filters=filters, fields=["name", "planned_qty"])
