import frappe
from frappe.tests.utils import FrappeTestCase

from construction.install import BOQ_TRANSACTION_CHILD_DOCTYPES, setup_boq_integration


class TestBOQAccountingDimension(FrappeTestCase):
	def test_setup_is_idempotent(self):
		setup_boq_integration()
		setup_boq_integration()

		dimensions = frappe.get_all(
			"Accounting Dimension",
			filters={"document_type": "BOQ Item"},
			fields=["name", "fieldname"],
		)
		self.assertEqual(len(dimensions), 1)
		self.assertEqual(dimensions[0].fieldname, "boq_item")

	def test_operational_custom_fields_exist_once(self):
		setup_boq_integration()

		for doctype in BOQ_TRANSACTION_CHILD_DOCTYPES:
			if not frappe.db.exists("DocType", doctype):
				continue
			meta = frappe.get_meta(doctype, cached=False)
			self.assertTrue(meta.has_field("boq_item"))
			self.assertTrue(meta.has_field("boq_item_stage"))
			self.assertTrue(meta.has_field("expense_category"))

			for fieldname in ("boq_item", "boq_item_stage", "expense_category"):
				count = frappe.db.count("Custom Field", {"dt": doctype, "fieldname": fieldname})
				self.assertLessEqual(count, 1)
