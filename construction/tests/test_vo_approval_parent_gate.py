"""F06-D001 regression: VO approval authority reconciled with parent permissions.

The VO workflow authorizes engineer approval to Site Engineer, but the BOQ
parent gate demanded BOQ Header write (which Site Engineer does not hold), so
no ordinary-role chain could complete a Variation Order. The fix narrows the
parent requirement to READ for Variation Order writes only; header-write
remains required for the other five child doctypes.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

HDR = "BOQ-2026-8575"


def _make_user(email, role):
    if frappe.db.exists("User", email):
        return email
    user = frappe.new_doc("User")
    user.email = email
    user.first_name = email.split("@")[0]
    user.enabled = 1
    user.send_welcome_email = 0
    user.append("roles", {"role": role})
    user.insert(ignore_permissions=True)
    for allow, val in (("Company", "_Test Company"), ("Project", "PROJ-0014")):
        if not frappe.db.exists("User Permission", {"user": email, "allow": allow, "for_value": val}):
            perm = frappe.new_doc("User Permission")
            perm.user = email
            perm.allow = allow
            perm.for_value = val
            perm.insert(ignore_permissions=True)
    if not frappe.db.exists("User Scope Context", {"user": email}):
        ctx = frappe.new_doc("User Scope Context")
        ctx.user = email
        ctx.company = "_Test Company"
        ctx.cost_center = "Main - _TC"
        ctx.project = "PROJ-0014"
        ctx.insert(ignore_permissions=True)
    return email


class TestVOApprovalParentGate(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.eng = _make_user("f06reg-eng@v16rehearsal.local", "Site Engineer")
        cls.pm = _make_user("f06reg-pm@v16rehearsal.local", "Project Manager")
        cls.item = frappe.db.get_value("BOQ Item", {"boq_header": HDR}, "name")
        cls.struct = frappe.db.get_value("BOQ Item", cls.item, "structure")

    def _vo_submitted_by(self, user):
        frappe.set_user(user)
        vo = frappe.new_doc("Variation Order")
        vo.boq_header = HDR
        vo.vo_date = "2026-10-13"
        vo.reason = "F06-D001 regression"
        vo.append(
            "lines",
            {
                "line_type": "Quantity Change",
                "boq_item": self.item,
                "boq_structure": self.struct,
                "title": "regression line",
                "unit": "Nos",
                "previous_qty": 12,
                "revised_qty": 13,
                "contract_unit_price": 100,
                "revised_unit_price": 100,
                "rate_change_justification": "regression",
            },
        )
        vo.insert()
        vo.status = "Submitted"
        vo.save()
        return vo.name

    def test_engineer_can_engineer_approve(self):
        """The workflow-authorized engineer step passes the parent gate (fails before fix)."""
        name = self._vo_submitted_by(self.pm)
        frappe.set_user(self.eng)
        vo = frappe.get_doc("Variation Order", name)
        vo.status = "Approved by Engineer"
        vo.save()  # PermissionError before the fix; passes after
        self.assertEqual(vo.status, "Approved by Engineer")

    def test_engineer_approval_by_engineer_role(self):
        frappe.set_user("Administrator")
        vo = frappe.new_doc("Variation Order")
        vo.boq_header = HDR
        vo.vo_date = "2026-10-13"
        vo.reason = "F06-D001 regression"
        vo.append(
            "lines",
            {
                "line_type": "Quantity Change",
                "boq_item": self.item,
                "boq_structure": self.struct,
                "title": "regression line 2",
                "unit": "Nos",
                "previous_qty": 12,
                "revised_qty": 13,
                "contract_unit_price": 100,
                "revised_unit_price": 100,
                "rate_change_justification": "regression",
            },
        )
        vo.insert(ignore_permissions=True)
        vo.status = "Submitted"
        vo.save(ignore_permissions=True)
        frappe.set_user(self.eng)
        vo = frappe.get_doc("Variation Order", vo.name)
        vo.status = "Approved by Engineer"
        vo.save()  # PermissionError before the fix; passes after
        self.assertEqual(vo.status, "Approved by Engineer")

    def test_engineer_still_cannot_write_boq_item(self):
        """Parent write remains required for aggregate-mutating children."""
        frappe.set_user(self.eng)
        doc = frappe.get_doc("BOQ Item", self.item)
        doc.cost_item = "F06-D001 tamper attempt"
        with self.assertRaises(frappe.PermissionError):
            doc.save()

    def test_engineer_cannot_move_vo_to_unreadable_header(self):
        """Parent READ is still enforced: a header the caller cannot read refuses the move."""
        frappe.set_user(self.eng)
        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": HDR,
                "vo_date": "2026-10-13",
                "reason": "move probe",
            }
        )
        vo.append(
            "lines",
            {
                "line_type": "Quantity Change",
                "boq_item": self.item,
                "boq_structure": self.struct,
                "title": "probe line",
                "unit": "Nos",
                "previous_qty": 12,
                "revised_qty": 12,
                "contract_unit_price": 100,
                "revised_unit_price": 100,
                "rate_change_justification": "probe",
            },
        )
        vo.insert()
        vo.boq_header = "BOQ-2026-0001"  # Elrefae header; engineer scoped to _Test Company
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            vo.save()

    def test_engineer_cannot_client_approve(self):
        """Client approval stays Owner/System Manager only."""
        frappe.set_user(self.pm)
        vo = frappe.new_doc("Variation Order")
        vo.boq_header = HDR
        vo.vo_date = "2026-10-13"
        vo.reason = "client-approve probe"
        vo.append(
            "lines",
            {
                "line_type": "Quantity Change",
                "boq_item": self.item,
                "boq_structure": self.struct,
                "title": "probe line",
                "unit": "Nos",
                "previous_qty": 12,
                "revised_qty": 12,
                "contract_unit_price": 100,
                "revised_unit_price": 100,
                "rate_change_justification": "probe",
            },
        )
        vo.insert()
        vo.status = "Submitted"
        vo.save()
        frappe.set_user(self.eng)
        vo = frappe.get_doc("Variation Order", vo.name)
        vo.status = "Approved by Client"
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            vo.save()
