import frappe
from frappe import _
from frappe.utils import flt

from construction.services.boq_lookups import get_stages_for_item


TOLERANCE = 0.001


def validate_stage_quantities(doc):
	for fieldname in ("planned_qty", "measured_executed_qty", "certified_qty"):
		value = flt(doc.get(fieldname))
		if value < 0:
			frappe.throw(_("Field '{0}' must be non-negative").format(doc.meta.get_label(fieldname)))

	if flt(doc.certified_qty) > flt(doc.measured_executed_qty):
		frappe.throw(_("Certified quantity cannot exceed measured executed quantity"))

	percent_complete = flt(doc.percent_complete)
	if percent_complete < 0 or percent_complete > 100:
		frappe.throw(_("Percent complete must be between 0 and 100"))

	_validate_planned_distribution(doc)


def validate_boq_item_stage_distribution(boq_item):
	if not boq_item.get("has_stages") or not boq_item.name:
		return

	parent_qty = flt(boq_item.quantity)
	total_planned = sum(flt(stage.planned_qty) for stage in get_stages_for_item(boq_item.name))
	header_status = frappe.db.get_value("BOQ Header", boq_item.boq_header, "status")
	_enforce_distribution_rule(total_planned, parent_qty, header_status)


def _validate_planned_distribution(doc):
	parent_qty = flt(frappe.db.get_value("BOQ Item", doc.boq_item, "quantity"))
	header_status = frappe.db.get_value("BOQ Header", doc.boq_header, "status")

	frappe.db.sql(
		"SELECT name, quantity FROM `tabBOQ Item` WHERE name = %s FOR UPDATE",
		(doc.boq_item,),
	)

	total_planned = sum(
		flt(stage.planned_qty) for stage in get_stages_for_item(doc.boq_item, exclude_name=doc.name)
	)
	total_planned += flt(doc.planned_qty)

	_enforce_distribution_rule(total_planned, parent_qty, header_status)


def _enforce_distribution_rule(total_planned, parent_qty, header_status):
	if header_status in ("Draft", "Pricing"):
		if total_planned > parent_qty:
			frappe.throw(
				_("Total planned quantity ({0}) exceeds BOQ Item quantity ({1})").format(
					total_planned, parent_qty
				)
			)
	elif header_status in ("Frozen", "Locked"):
		if abs(total_planned - parent_qty) > TOLERANCE:
			frappe.throw(
				_(
					"Frozen/Locked BOQ requires exact stage distribution. Total: {0}, Expected: {1}"
				).format(total_planned, parent_qty)
			)
