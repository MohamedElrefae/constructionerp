import frappe
from frappe import _


TRANSACTION_CHILD_DOCTYPES = (
	"Purchase Order Item",
	"Purchase Receipt Item",
	"Purchase Invoice Item",
	"Stock Entry Detail",
	"Timesheet Detail",
	"Journal Entry Account",
	"Sales Invoice Item",
	"Material Request Item",
)


def before_delete_boq_item_stage(doc, method=None):
	for doctype in TRANSACTION_CHILD_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.get_meta(doctype).has_field("boq_item_stage"):
			continue
		if frappe.db.exists(doctype, {"boq_item_stage": doc.name}):
			frappe.throw(
				_("Cannot delete BOQ Item Stage {0}: it is referenced by {1}").format(
					doc.name, doctype
				)
			)
