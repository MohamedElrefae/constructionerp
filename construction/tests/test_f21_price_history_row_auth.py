"""F21-D002: price_history rows must carry document identity and pass per-row authorization.

F19's ``report_view`` promises "Every returned row is separately permission-checked". The
price_history path could not keep that promise: the service selected no ``name`` column, and
``_readable_rph`` treated a row with no identity as authorized. A buyer with no Resource Price
History rights therefore received nine rate rows (observed on the UAT persona f20-store,
2026-10-14). These tests pin both halves of the fix: the service emits ``name``, and a row
without identity is refused.
"""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.api.construction_reports import _readable_rph, report_view
from construction.services.boq_report_service import get_resource_price_history


def clear_request_cache():
    """Frappe caches role/user permissions per request; switching user mid-test must not
    reuse the previous user's answer (this silently corrupted earlier F21 measurements)."""
    cache = getattr(frappe.local, "request_cache", None)
    if cache:
        cache.clear()
    frappe.local._boq_perm_scope_dims = {}


class TestPriceHistoryRowAuthorization(FrappeTestCase):
    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name") or "Test Quality Company"
        self.item = self._make_item()
        self.rph_names = []
        for rate in (100, 110):
            self.rph_names.append(self._make_rph(rate))
        self._created_users = []

    def tearDown(self):
        for email in self._created_users:
            self._drop_user(email)
        for name in self.rph_names:
            if frappe.db.exists("Resource Price History", name):
                frappe.delete_doc("Resource Price History", name, ignore_permissions=True, force=True)
        if frappe.db.exists("Item", self.item):
            frappe.delete_doc("Item", self.item, ignore_permissions=True, force=True)
        frappe.set_user("Administrator")

    # helpers ---------------------------------------------------------------

    def _make_item(self):
        code = "F21-RPH-TEST-ITEM"
        if frappe.db.exists("Item", code):
            return code
        doc = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": code,
                "item_name": "F21 RPH Test Item",
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0,
            }
        )
        doc.insert(ignore_permissions=True)
        return code

    def _make_rph(self, rate):
        doc = frappe.get_doc(
            {
                "doctype": "Resource Price History",
                "naming_series": "RPH-.YYYY.-",
                "item_code": self.item,
                "price_date": "2026-01-15",
                "rate": rate,
                "currency": "EGP",
                "uom": "Nos",
                "company": self.company,
                "status": "Active",
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_persona(self, label, roles):
        """A user holding only native `roles`, scoped to self.company by User Permission."""
        email = f"f21-rph-{label}@example.com"
        if not frappe.db.exists("User", email):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": f"F21 {label}",
                    "enabled": 1,
                    "send_welcome_email": 0,
                    "new_password": "F21rph#2026!",
                }
            )
            for role in roles:
                u.append("roles", {"role": role})
            u.insert(ignore_permissions=True)
        else:
            u = frappe.get_doc("User", email)
        if not frappe.db.exists("User Permission", {"user": email, "allow": "Company"}):
            frappe.get_doc(
                {
                    "doctype": "User Permission",
                    "user": email,
                    "allow": "Company",
                    "for_value": self.company,
                    "apply_to_all_doctypes": 1,
                }
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("User Scope Context", {"user": email}):
            frappe.get_doc({"doctype": "User Scope Context", "user": email, "company": self.company}).insert(
                ignore_permissions=True
            )
        self._created_users.append(email)
        return email

    def _drop_user(self, email):
        for name in frappe.get_all("User Scope Context", filters={"user": email}, pluck="name"):
            # Protected contexts remain immutable in product flows; remove
            # only the exact fixture row for this tracked test user.
            frappe.db.delete("User Scope Context", {"name": name, "user": email})
        for up in frappe.get_all("User Permission", filters={"user": email}, pluck="name"):
            frappe.delete_doc("User Permission", up, ignore_permissions=True, force=True)
        for role_row in frappe.get_all("Has Role", filters={"parent": email}, pluck="name"):
            frappe.db.delete("Has Role", {"name": role_row})
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, ignore_permissions=True, force=True)

    # tests -----------------------------------------------------------------

    def test_row_without_identity_is_not_readable(self):
        """No name means the row cannot be authorized, so it must not pass."""
        self.assertFalse(_readable_rph({"item_code": self.item}))
        self.assertFalse(_readable_rph({}))

    def test_service_returns_document_identity(self):
        rows = get_resource_price_history(item_code=self.item)
        self.assertTrue(rows, "fixture should have produced price history rows")
        for row in rows:
            self.assertTrue(row.get("name"), f"row without identity: {row}")

    def test_price_history_withheld_from_user_without_rph_read(self):
        """Stock User reads Company natively but holds no Resource Price History rights."""
        stock = self._make_persona("stock", ["Stock User"])
        self.assertFalse(frappe.has_permission("Resource Price History", "read", user=stock))
        frappe.set_user(stock)
        clear_request_cache()
        data = report_view("price_history", company=self.company)
        self.assertEqual(data["row_count"], 0, "nameless/unauthorized rows must not reach the caller")
        self.assertEqual(data["rows"], [])

    def test_price_history_visible_to_user_with_rph_read(self):
        """System Manager holds Resource Price History read, so the same rows are returned."""
        sm = self._make_persona("sm", ["System Manager"])
        self.assertTrue(frappe.has_permission("Resource Price History", "read", user=sm))
        frappe.set_user(sm)
        clear_request_cache()
        data = report_view("price_history", company=self.company, item_code=self.item)
        self.assertGreater(data["row_count"], 0)
        self.assertTrue(all(r.get("name") for r in data["rows"]))


class TestCompanyReadGrantIsNarrow(FrappeTestCase):
    """F21-D001: Company read for the estimation audience grants nothing else.

    The grant exists so `report_view`'s Company scope gate can pass for the roles the
    estimation views are for. It must not become a wider door: Company write/create/delete/
    submit/cancel/report/export/print/email/share stay off, and Company read alone must not
    confer Resource Price History or BOQ Cost Analysis record access.
    """

    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name") or "Test Quality Company"
        self._users = []

    def tearDown(self):
        for email in self._users:
            self._drop_user(email)
        frappe.set_user("Administrator")

    def _persona(self, label, roles):
        email = f"f21-d001-{label}@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": f"D001 {label}",
                    "enabled": 1,
                    "send_welcome_email": 0,
                    "roles": [{"role": r} for r in roles],
                }
            ).insert(ignore_permissions=True)
        self._users.append(email)
        return email

    def _drop_user(self, email):
        for up in frappe.get_all("User Permission", filters={"user": email}, pluck="name"):
            frappe.delete_doc("User Permission", up, ignore_permissions=True, force=True)
        for role_row in frappe.get_all("Has Role", filters={"parent": email}, pluck="name"):
            frappe.db.delete("Has Role", {"name": role_row})
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, ignore_permissions=True, force=True)

    def test_estimation_roles_hold_company_read_only(self):
        """Each audience role: read yes, every other right no."""
        for role in ("Project Manager", "Construction Owner", "Site Engineer", "Read-Only"):
            email = self._persona(role.lower().replace(" ", "-"), [role])
            frappe.set_user(email)
            clear_request_cache()
            self.assertTrue(
                frappe.has_permission("Company", "read"),
                f"{role} should hold Company read after the F21-D001 grant",
            )
            for ptype in (
                "write",
                "create",
                "delete",
                "submit",
                "cancel",
                "amend",
                "report",
                "export",
                "print",
                "email",
                "share",
                "import",
            ):
                self.assertFalse(
                    frappe.has_permission("Company", ptype),
                    f"{role} must not hold Company {ptype}",
                )
            frappe.set_user("Administrator")

    def test_company_read_does_not_grant_price_history(self):
        """A role with Company read but no Resource Price History read gets no RPH access."""
        email = self._persona("no-rph", ["Site Engineer"])
        frappe.set_user(email)
        clear_request_cache()
        self.assertTrue(frappe.has_permission("Company", "read"))
        self.assertFalse(
            frappe.has_permission("Resource Price History", "read"),
            "Company read must not confer Resource Price History read",
        )
        self.assertFalse(
            frappe.has_permission("BOQ Cost Analysis", "write"),
            "Company read must not confer analysis write",
        )
        frappe.set_user("Administrator")

    def test_company_read_is_restricted_by_user_permission(self):
        """Company read is scoped per company by native User Permission, not by role."""
        email = self._persona("scoped", ["Project Manager"])
        if not frappe.db.exists("User Permission", {"user": email, "allow": "Company"}):
            frappe.get_doc(
                {
                    "doctype": "User Permission",
                    "user": email,
                    "allow": "Company",
                    "for_value": self.company,
                    "apply_to_all_doctypes": 1,
                }
            ).insert(ignore_permissions=True)
        other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
        frappe.set_user(email)
        clear_request_cache()
        self.assertTrue(
            frappe.has_permission("Company", "read", doc=self.company),
            "permitted company must stay readable",
        )
        if other:
            self.assertFalse(
                frappe.has_permission("Company", "read", doc=other),
                "a company outside the user's permission must be refused",
            )
        frappe.set_user("Administrator")


class TestPriceHistoryWithheldInEveryForm(FrappeTestCase):
    """F21-D002: a forbidden persona receives no restricted data in any form.

    An empty displayed list is not enough: totals, counts, column names and the exported
    file must all be free of Resource Price History identifiers.
    """

    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name") or "Test Quality Company"
        self.item = "F21-RPH-LEAK-ITEM"
        if not frappe.db.exists("Item", self.item):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": self.item,
                    "item_name": "F21 RPH Leak Item",
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                }
            ).insert(ignore_permissions=True)
        self.rph = frappe.get_doc(
            {
                "doctype": "Resource Price History",
                "naming_series": "RPH-.YYYY.-",
                "item_code": self.item,
                "price_date": "2026-01-15",
                "rate": 100,
                "currency": "EGP",
                "uom": "Nos",
                "company": self.company,
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
        self.user = "f21-leak-check@example.com"
        if not frappe.db.exists("User", self.user):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.user,
                    "first_name": "Leak Check",
                    "enabled": 1,
                    "send_welcome_email": 0,
                    "roles": [{"role": "Stock User"}],
                }
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("User Permission", {"user": self.user, "allow": "Company"}):
            frappe.get_doc(
                {
                    "doctype": "User Permission",
                    "user": self.user,
                    "allow": "Company",
                    "for_value": self.company,
                    "apply_to_all_doctypes": 1,
                }
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("User Scope Context", {"user": self.user}):
            frappe.get_doc({"doctype": "User Scope Context", "user": self.user,
                            "company": self.company}).insert(ignore_permissions=True)
        frappe.set_user(self.user)
        clear_request_cache()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.delete_doc("Resource Price History", self.rph.name, ignore_permissions=True, force=True)
        if frappe.db.exists("Item", self.item):
            frappe.delete_doc("Item", self.item, ignore_permissions=True, force=True)
        frappe.db.rollback()

    def _assert_no_restricted_data(self, payload):
        self.assertEqual(payload["row_count"], 0, "total row count must be zero")
        self.assertEqual(payload["rows"], [], "no rows may be returned")
        self.assertEqual(payload["columns"], [], "no column names may leak")
        self.assertFalse(payload["has_more"], "has_more must not imply hidden rows")
        body = json.dumps(payload, default=str)
        for marker in ("RPH-", "source_name", "source_doctype", "Resource Price History"):
            self.assertNotIn(marker, body, f"restricted marker {marker} reached the caller")

    def test_view_returns_no_restricted_data(self):
        from construction.api.construction_reports import report_view

        payload = report_view("price_history", company=self.company, item_code=self.item)
        self._assert_no_restricted_data(payload)

    def test_export_returns_no_restricted_data(self):
        from construction.api.construction_reports import report_export

        result = report_export("price_history", company=self.company, item_code=self.item)
        self.assertEqual(result["row_count"], 0, "export must carry zero rows")
        self.assertFalse(result["truncated"], "export must not hint at withheld rows")
        path = frappe.get_site_path("private", "files", result["file_name"])
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            body = f.read()
        self.assertEqual(json.loads(body)["rows"], [])
        for marker in ("RPH-", "source_name", "source_doctype", "Resource Price History"):
            self.assertNotIn(marker, body, f"restricted marker {marker} reached the export")
