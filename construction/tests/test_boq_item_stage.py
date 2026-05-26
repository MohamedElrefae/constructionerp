import frappe
from frappe.tests.utils import FrappeTestCase


class TestBOQItemStage(FrappeTestCase):
	def setUp(self):
		self._clear_scope_defaults()
		self.project = self._make_project()
		self.header = frappe.get_doc(
			{
				"doctype": "BOQ Header",
				"project": self.project,
				"title": "Test BOQ Item Stage",
				"status": "Draft",
				"boq_type": "Tender",
			}
		).insert(ignore_permissions=True)

		self.structure = frappe.get_doc(
			{
				"doctype": "BOQ Structure",
				"boq_header": self.header.name,
				"title": "Stage Test Item",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

		self.item = frappe.get_doc(
			"BOQ Item",
			frappe.db.get_value("BOQ Item", {"structure": self.structure.name}, "name"),
		)
		self.item.quantity = 10
		self.item.has_stages = 1
		self.item.save(ignore_permissions=True)

	def _clear_scope_defaults(self):
		for key in ("branch", "company", "cost_center", "project", "department"):
			frappe.defaults.clear_user_default(key, "Administrator")

	def _make_project(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "_Test BOQ Company",
					"default_currency": "USD",
					"country": "United States",
				}
			).insert(ignore_permissions=True).name

		project_name = "_Test BOQ Project"
		project = frappe.db.get_value("Project", {"project_name": project_name}, "name")
		if project:
			return project

		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project_name,
				"company": company,
				"naming_series": "PROJ-.####",
			}
		).insert(ignore_permissions=True).name

	def _stage(self, **overrides):
		doc = frappe.get_doc(
			{
				"doctype": "BOQ Item Stage",
				"boq_item": self.item.name,
				"stage_code": "S001",
				"stage_name": "Ground Floor",
				"planned_qty": 5,
				"measured_executed_qty": 2,
				"certified_qty": 1,
				"percent_complete": 40,
				"stage_status": "In Progress",
			}
		)
		doc.update(overrides)
		return doc

	def test_valid_stage_fetches_parent_context(self):
		stage = self._stage().insert(ignore_permissions=True)

		self.assertEqual(stage.boq_header, self.header.name)
		self.assertEqual(stage.project, self.project)

	def test_pricing_allows_has_stages_when_quantity_posts_as_zero(self):
		header = frappe.get_doc(
			{
				"doctype": "BOQ Header",
				"project": self.project,
				"title": "Pricing Has Stages",
				"status": "Draft",
				"boq_type": "Tender",
			}
		).insert(ignore_permissions=True)
		structure = frappe.get_doc(
			{
				"doctype": "BOQ Structure",
				"boq_header": header.name,
				"title": "Pricing Has Stages Item",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		item = frappe.get_doc(
			"BOQ Item",
			frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name"),
		)

		header.status = "Pricing"
		header.save(ignore_permissions=True)

		item.reload()
		item.quantity = 0
		item.has_stages = 1
		item.save(ignore_permissions=True)

		self.assertEqual(item.has_stages, 1)

	def test_duplicate_stage_code_rejected(self):
		self._stage().insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			self._stage(stage_name="Duplicate").insert(ignore_permissions=True)

	def test_quantity_guards(self):
		for fieldname in ("planned_qty", "measured_executed_qty", "certified_qty"):
			with self.assertRaises(frappe.ValidationError):
				self._stage(stage_code=f"NEG-{fieldname}", **{fieldname: -1}).insert(
					ignore_permissions=True
				)

		with self.assertRaises(frappe.ValidationError):
			self._stage(stage_code="CERT", measured_executed_qty=2, certified_qty=3).insert(
				ignore_permissions=True
			)

	def test_percent_complete_bounds(self):
		with self.assertRaises(frappe.ValidationError):
			self._stage(stage_code="LOW", percent_complete=-1).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			self._stage(stage_code="HIGH", percent_complete=101).insert(ignore_permissions=True)

	def test_draft_total_planned_cannot_exceed_parent_quantity(self):
		self._stage(stage_code="S001", planned_qty=6).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			self._stage(stage_code="S002", planned_qty=5).insert(ignore_permissions=True)

	def test_frozen_requires_exact_distribution(self):
		self.header.status = "Pricing"
		self.header.save(ignore_permissions=True)
		self.header.status = "Frozen"
		self.header.save(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			self._stage(stage_code="F001", planned_qty=5).insert(ignore_permissions=True)
