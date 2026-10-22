"""Non-admin native document/list and parent boundary regressions."""

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.api.boq_api import require_boq_access
from construction.tests.test_boq_helpers import get_or_create_test_project


class TestBOQParentPermissions(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Prove assigned permissions survive disabling the working-context
        # filter. The UI selector is not the authorization boundary.
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 0)
        self.projects = [
            get_or_create_test_project("_Test Permission Project " + suffix)
            for suffix in ("Allowed", "Denied")
        ]
        self.headers = []
        self.items = []
        for project in self.projects:
            header = frappe.get_doc(
                {
                    "doctype": "BOQ Header",
                    "title": "Parent permission test",
                    "project": project,
                    "status": "Draft",
                    "boq_type": "Tender",
                }
            ).insert(ignore_permissions=True)
            structure = frappe.get_doc(
                {
                    "doctype": "BOQ Structure",
                    "boq_header": header.name,
                    "title": "Permission line",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)
            self.headers.append(header)
            self.items.append(frappe.get_doc("BOQ Item", {"structure": structure.name}))
        self.user = "boq-parent-" + frappe.generate_hash(length=8) + "@example.invalid"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": self.user,
                "first_name": "BOQ permission test",
                "send_welcome_email": 0,
                "user_type": "System User",
                "roles": [{"role": "Project Manager"}],
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": self.user,
                "allow": "Project",
                "for_value": self.projects[0],
                "apply_to_all_doctypes": 1,
            }
        ).insert(ignore_permissions=True)
        frappe.clear_cache(user=self.user)
        frappe.set_user(self.user)
        self.assertNotEqual(self.projects[0], self.projects[1])
        self.assertEqual(
            [p.doc for p in frappe.permissions.get_user_permissions(self.user).get("Project", [])],
            [self.projects[0]],
        )

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.clear_cache(user=self.user)

    def test_native_document_access_inherits_header_user_permission(self):
        self.assertTrue(frappe.has_permission("BOQ Header", "read", doc=self.headers[0]))
        self.assertFalse(frappe.has_permission("BOQ Header", "read", doc=self.headers[1]))
        for doctype, allowed, denied in (
            ("BOQ Item", self.items[0], self.items[1]),
            (
                "BOQ Structure",
                frappe.get_doc("BOQ Structure", self.items[0].structure),
                frappe.get_doc("BOQ Structure", self.items[1].structure),
            ),
        ):
            self.assertTrue(frappe.has_permission(doctype, "read", doc=allowed))
            self.assertTrue(frappe.has_permission(doctype, "write", doc=allowed))
            self.assertFalse(frappe.has_permission(doctype, "read", doc=denied))
            self.assertFalse(frappe.has_permission(doctype, "write", doc=denied))
        require_boq_access(self.headers[0].name)
        with self.assertRaises(frappe.PermissionError):
            require_boq_access(self.headers[1].name)

    def test_native_list_omits_children_of_forbidden_header(self):
        for doctype, names in (
            ("BOQ Item", [item.name for item in self.items]),
            ("BOQ Structure", [item.structure for item in self.items]),
        ):
            listed = frappe.get_list(doctype, filters={"name": ["in", names]}, pluck="name")
            self.assertEqual(listed, [names[0]])

    def test_standard_save_and_parent_reassignment_are_denied(self):
        allowed = frappe.get_doc("BOQ Item", self.items[0].name)
        allowed.quantity = 3
        allowed.save()
        denied = frappe.get_doc("BOQ Item", self.items[1].name)
        denied.quantity = 9
        with self.assertRaises(frappe.PermissionError):
            denied.save()
        denied.boq_header = self.headers[0].name
        denied.structure = self.items[0].structure
        with self.assertRaises(frappe.PermissionError):
            denied.save()
        self.assertEqual(frappe.db.get_value("BOQ Item", denied.name, "quantity"), self.items[1].quantity)

    def test_guest_cannot_read_either_child(self):
        frappe.set_user("Guest")
        for item in self.items:
            self.assertFalse(frappe.has_permission("BOQ Item", "read", doc=item))

    def test_new_structure_requires_allowed_parent_write(self):
        denied = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.headers[1].name,
                "title": "Forbidden create",
                "is_group": 1,
            }
        )
        with self.assertRaises(frappe.PermissionError):
            denied.insert()
        allowed = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.headers[0].name,
                "title": "Allowed create",
                "is_group": 1,
            }
        )
        allowed.insert()
        self.assertTrue(allowed.name)

    def test_analysis_revision_stage_and_vo_follow_same_project_boundary(self):
        frappe.set_user("Administrator")
        code = "Permission resource " + frappe.generate_hash(length=8)
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": code,
                "item_name": code,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0,
            }
        ).insert(ignore_permissions=True)
        records = {}
        for header, item in zip(self.headers, self.items, strict=True):
            company = frappe.db.get_value("Project", header.project, "company")
            analysis = frappe.get_doc(
                {
                    "doctype": "BOQ Cost Analysis",
                    "title": "Permission fixture",
                    "boq_item": item.name,
                    "company": company,
                    "analysis_status": "Draft",
                    "analysis_qty": 1,
                    "analysis_uom": "Nos",
                    "currency": "EGP",
                    "details": [
                        {
                            "cost_stream": "M",
                            "item_code": code,
                            "resource_uom": "Nos",
                            "qty_per_boq_unit": 1,
                            "cost_rate": 1,
                        }
                    ],
                }
            ).insert(ignore_permissions=True)
            revision = frappe.get_doc(
                {
                    "doctype": "BOQ Quantity Revision",
                    "boq_header": header.name,
                    "boq_structure": item.structure,
                    "boq_item": item.name,
                    "revision_date": frappe.utils.today(),
                    "revision_type": "Increase Within 25%",
                    "previous_qty": 0,
                    "revised_qty": 1,
                    "contract_unit_price": 0,
                    "revised_unit_price": 0,
                    "rate_change_justification": "Permission fixture",
                    "status": "Draft",
                }
            ).insert(ignore_permissions=True)
            stage = frappe.get_doc(
                {
                    "doctype": "BOQ Item Stage",
                    "boq_item": item.name,
                    "stage_name": "Access fixture",
                    "planned_qty": 0,
                }
            ).insert(ignore_permissions=True)
            frappe.db.set_value("BOQ Header", header.name, "status", "Locked")
            vo = frappe.get_doc(
                {"doctype": "Variation Order", "boq_header": header.name, "status": "Draft"}
            ).insert(ignore_permissions=True)
            for doc in (analysis, revision, stage, vo):
                records.setdefault(doc.doctype, []).append(doc.name)
        frappe.set_user(self.user)
        for doctype, names in records.items():
            with self.subTest(doctype=doctype):
                self.assertTrue(frappe.has_permission(doctype, "read", doc=names[0]))
                self.assertFalse(frappe.has_permission(doctype, "read", doc=names[1]))
                self.assertFalse(frappe.has_permission(doctype, "write", doc=names[1]))
                self.assertEqual(
                    frappe.get_list(doctype, filters={"name": ["in", names]}, pluck="name"), [names[0]]
                )
