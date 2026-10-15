"""F11-D002/D003 regressions: scope authorization boundary + engineer measurement policy.

- With enforcement ON, the selected scope covers direct document reads/writes,
  not only list queries. A user with native role/User Permission grants but a
  mismatched active scope is denied; a user with no scope is denied.
- Engineers admitted through the parent-read exception may create stages and
  record measurements on non-certified stages, but may not change planning
  fields and may not certify.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

IN_SCOPE_HDR = "BOQ-2026-8582"  # PROJ-0014, _Test Company (header-level scope probes)
OUT_SCOPE_HDR = "BOQ-2026-8587"  # PROJ-0015, _Test Company (covered by PM's Company grant, outside PM's scope)


class TestScopeBoundaryAndMeasurementPolicy(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1)
        hdr = frappe.db.get_value("BOQ Header", {"title": "F11 Policy BOQ"}, "name")
        if not hdr:
            h = frappe.new_doc("BOQ Header")
            h.project = "PROJ-0014"
            h.boq_type = "Tender"
            h.title = "F11 Policy BOQ"
            h.insert(ignore_permissions=True)
            hdr = h.name
            root = frappe.new_doc("BOQ Structure")
            root.update({"title": "F11P Root", "boq_header": hdr, "project": "PROJ-0014", "is_group": 1})
            root.insert(ignore_permissions=True)
            leaf = frappe.new_doc("BOQ Structure")
            leaf.update({"title": "F11P Leaf", "boq_header": hdr, "project": "PROJ-0014",
                         "parent_structure": root.name, "is_group": 0})
            leaf.insert(ignore_permissions=True)
            auto = frappe.db.get_value("BOQ Item", {"structure": leaf.name}, "name")
            d = frappe.get_doc("BOQ Item", auto)
            d.update({"cost_item": "F11 policy works", "quantity": 1000, "unit": "Nos", "factor": 1,
                      "est_unit_cost": 10, "contract_unit_price": 12})
            d.save(ignore_permissions=True)
        cls.hdr = hdr
        cls.item = frappe.db.get_value("BOQ Item", {"boq_header": hdr}, "name")
        cls.struct = frappe.db.get_value("BOQ Item", cls.item, "structure")

    def test_scope_mismatch_denies_despite_native_grants(self):
        """PM's Company User Permission covers PROJ-0015, but the active scope pins PROJ-0014."""
        frappe.set_user("f04-pm@v16rehearsal.local")
        self.assertTrue(frappe.has_permission("BOQ Header", "read", doc=IN_SCOPE_HDR))
        self.assertFalse(frappe.has_permission("BOQ Header", "read", doc=OUT_SCOPE_HDR))

    def test_missing_scope_denies(self):
        # F22-D008: read-only gained a valid scope for F21-D001, so the dedicated
        # scopeless account carries this denial assertion now.
        frappe.set_user("f23-scopeless@v16rehearsal.local")
        self.assertFalse(frappe.has_permission("BOQ Header", "read", doc=IN_SCOPE_HDR))

    def test_sm_bypass_preserved(self):
        from construction.overrides.boq_permissions import has_boq_header_permission

        frappe.set_user("f06-sm@v16rehearsal.local")
        doc = frappe.get_doc("BOQ Header", OUT_SCOPE_HDR)
        # Hook layer bypasses for SM; native User Permissions still pin this
        # SM identity to PROJ-0014, so the full-stack check follows native
        # rules (unchanged by the scope boundary).
        self.assertTrue(has_boq_header_permission(doc, "read", user="f06-sm@v16rehearsal.local"))
        self.assertTrue(frappe.has_permission("BOQ Header", "read", doc=IN_SCOPE_HDR))

    def test_engineer_creates_and_measures_but_does_not_plan_or_certify(self):
        frappe.set_user("f04-engineer@v16rehearsal.local")
        stage = frappe.new_doc("BOQ Item Stage")
        stage.update(
            {
                "boq_header": self.hdr,
                "boq_item": self.item,
                "boq_structure": self.struct,
                "project": "PROJ-0014",
                "stage_name": "F11-D003 regression",
                "planned_qty": 5,
                "stage_status": "In Progress",
            }
        )
        stage.insert()
        stage.measured_executed_qty = 5
        stage.percent_complete = 100
        stage.save()
        stage.planned_qty = 9
        with self.assertRaises(frappe.PermissionError):
            stage.save()
        stage.reload()
        stage.certified_qty = 5
        stage.stage_status = "Certified"
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            stage.save()

    def test_header_writer_still_unrestricted_on_planning_fields(self):
        frappe.set_user("f04-pm@v16rehearsal.local")
        stage = frappe.new_doc("BOQ Item Stage")
        stage.update(
            {
                "boq_header": self.hdr,
                "boq_item": self.item,
                "boq_structure": self.struct,
                "project": "PROJ-0014",
                "stage_name": "F11-D003 PM control",
                "planned_qty": 2,
            }
        )
        stage.insert()
        stage.planned_qty = 3
        stage.save()
        self.assertEqual(frappe.db.get_value("BOQ Item Stage", stage.name, "planned_qty"), 3)
