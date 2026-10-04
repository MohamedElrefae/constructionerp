import unittest
from unittest.mock import patch as mock_patch

import frappe
from frappe.desk.search import build_for_autosuggest, search_link as vendor_search_link

from construction.api import desk_link_search as desk_link_module
from construction.api.desk_link_search import (
    as_autosuggest_rows,
    dispatcher,
    search_link,
    vendor_search_fields,
)
from construction.services.transaction_link_search import search_transactions

OVERRIDE_TARGET = "frappe.desk.search.search_link"
OVERRIDE_PATH = "construction.api.desk_link_search.search_link"
NO_PERM_USER = "ct-desk-dispatch-noperm@example.com"
ITEM_CODE = "CT-DISP-ITEM-A6"
ITEM_ARABIC_DESCRIPTION = "وصف عربي للاختبار"

UOM_A = "CT-DISPATCH-UOM-A"
UOM_B = "CT-DISPATCH-UOM-B"
ARABIC_SHARED = "وحدة اختبارية"
ARABIC_A = ARABIC_SHARED + " واحدة"
ARABIC_B = ARABIC_SHARED + " اثنتان"
CODE_A = "CTA"
CODE_B = "CTB"


class TestDeskLinkDispatch(unittest.TestCase):
    def setUp(self):
        self.fixtures = []
        for name, arabic, code in (
            (UOM_A, ARABIC_A, CODE_A),
            (UOM_B, ARABIC_B, CODE_B),
        ):
            doc = frappe.get_doc(
                {
                    "doctype": "UOM",
                    "uom_name": name,
                    "uom_name_ar": arabic,
                    "common_code": code,
                }
            ).insert(ignore_permissions=True)
            self.fixtures.append(doc.name)

    def tearDown(self):
        for name in self.fixtures:
            if frappe.db.exists("UOM", name):
                frappe.delete_doc("UOM", name, force=True, ignore_permissions=True)

    def test_override_hook_binding_resolves_to_dispatcher(self):
        self.assertEqual(frappe.override_whitelisted_method(OVERRIDE_TARGET), OVERRIDE_PATH)

    def test_latin_query_is_vendor_passthrough(self):
        ours = search_link("UOM", UOM_A, filters=None, page_length=10)
        theirs = vendor_search_link("UOM", UOM_A, filters=None, page_length=10)
        self.assertEqual(ours, theirs)
        self.assertEqual(ours, vendor_search_link("UOM", UOM_A, filters=None, page_length=10))

    def test_unregistered_doctype_is_vendor_passthrough(self):
        ours = search_link("Contact", "شركة", filters=None, page_length=10)
        theirs = vendor_search_link("Contact", "شركة", filters=None, page_length=10)
        self.assertEqual(ours, theirs)

    def test_registry_unreadable_fails_closed(self):
        with mock_patch(
            "construction.api.desk_link_search.load_registry",
            return_value=(None, ["bilingual-registry-parse: boom"]),
        ):
            ours = search_link("UOM", "وحدة", filters=None, page_length=10)
        theirs = vendor_search_link("UOM", "وحدة", filters=None, page_length=10)
        self.assertEqual(ours, theirs)

    def test_non_active_registry_entry_fails_closed(self):
        data, errors = frappe.get_attr(
            "construction.services.bilingual_registry.load_registry"
        )()
        self.assertFalse(errors)
        data["doctypes"]["UOM"]["state"] = "schema_installed"
        with mock_patch(
            "construction.api.desk_link_search.load_registry",
            return_value=(data, []),
        ):
            ours = search_link("UOM", "وحدة", filters=None, page_length=10)
        theirs = vendor_search_link("UOM", "وحدة", filters=None, page_length=10)
        self.assertEqual(ours, theirs)

    def test_dispatcher_canonical_positional_order_keeps_filters(self):
        rows = frappe.call(
            dispatcher,
            "UOM",
            ARABIC_SHARED,
            "name",
            0,
            20,
            {"common_code": CODE_A},
            as_dict=False,
            reference_doctype=None,
            ignore_user_permissions=False,
            link_fieldname=None,
        )
        values = [row[0] for row in rows]
        self.assertEqual(values, [UOM_A])
        self.assertIsInstance(rows[0], tuple)

    def test_dict_rows_satisfy_build_for_autosuggest(self):
        raw = frappe.get_attr("construction.searchable_dropdown.api.search.searchable_link_search")(
            doctype="UOM",
            txt=ARABIC_SHARED,
            filters={},
            search_fields=["name", "uom_name", "uom_name_ar"],
            page_length=20,
        )
        self.assertTrue(raw)
        self.assertIsInstance(raw[0], dict)
        rows = as_autosuggest_rows(raw)
        built = build_for_autosuggest(rows, doctype="UOM")
        self.assertTrue(built)
        self.assertEqual(
            [row["value"] for row in built],
            sorted(row["value"] for row in built),
        )
        for row in built:
            self.assertIn("value", row)

    def test_sidecar_rows_satisfy_build_for_autosuggest(self):
        raw = search_transactions("Sales Order", txt="abc", page_length=5)
        self.assertIsInstance(raw, list)
        if raw:
            self.assertIsInstance(raw[0], dict)
        rows = as_autosuggest_rows(raw)
        build_for_autosuggest(rows, doctype="Sales Order")

    def test_genuine_entry_point_arabic_and_latin(self):
        original_request = getattr(frappe.local, "request", None)
        original_form_dict = getattr(frappe.local, "form_dict", None)
        try:
            frappe.local.request = frappe._dict(
                method="GET", path="/api/method/" + OVERRIDE_TARGET
            )
            frappe.local.form_dict = frappe._dict(
                cmd=OVERRIDE_TARGET,
                doctype="UOM",
                txt=ARABIC_SHARED,
                query=None,
                filters=None,
                page_length=10,
                searchfield=None,
                reference_doctype=None,
                ignore_user_permissions=False,
                link_fieldname=None,
            )
            arabic = frappe.handler.execute_cmd(OVERRIDE_TARGET)
            self.assertIn(UOM_A, [row["value"] for row in arabic])
            self.assertIn(UOM_B, [row["value"] for row in arabic])

            frappe.local.form_dict["txt"] = UOM_A
            latin = frappe.handler.execute_cmd(OVERRIDE_TARGET)
        finally:
            frappe.local.request = original_request
            frappe.local.form_dict = original_form_dict
        self.assertEqual(latin, vendor_search_link("UOM", UOM_A, filters=None, page_length=10))

    def test_arabic_path_enforces_permissions_via_get_list(self):
        seen = []
        real_get_list, real_get_all = frappe.get_list, frappe.get_all

        def spy_list(*args, **kwargs):
            seen.append(("get_list", args[0] if args else kwargs.get("doctype")))
            return real_get_list(*args, **kwargs)

        def spy_all(*args, **kwargs):
            seen.append(("get_all", args[0] if args else kwargs.get("doctype")))
            return real_get_all(*args, **kwargs)

        with mock_patch.object(frappe, "get_list", spy_list), mock_patch.object(
            frappe, "get_all", spy_all
        ):
            search_link("UOM", ARABIC_SHARED, filters=None, page_length=10)

        self.assertIn(("get_list", "UOM"), seen)
        self.assertNotIn(("get_all", "UOM"), seen)

    def _spy_vendor(self):
        """Patch the module-level vendor import, returning (calls, restore_cm)."""
        calls = []
        real = desk_link_module._vendor_search_link

        def spy(doctype, txt, **kwargs):
            calls.append(doctype)
            return real(doctype, txt, **kwargs)

        return calls, mock_patch.object(desk_link_module, "_vendor_search_link", spy)

    def test_arabic_query_skips_vendor_baseline(self):
        calls, patcher = self._spy_vendor()
        with patcher:
            search_link("UOM", ARABIC_SHARED, filters=None, page_length=10)
            self.assertEqual(calls, [], "A6 must not pay for the vendor baseline on Arabic")
            search_link("UOM", UOM_A, filters=None, page_length=10)
            self.assertEqual(calls, ["UOM"], "Latin query must stay a literal passthrough")
            search_link("Contact", ARABIC_SHARED, filters=None, page_length=10)
            self.assertEqual(
                calls, ["UOM", "Contact"], "unregistered doctype must stay on the vendor path"
            )

    def test_vendor_search_fields_folded_into_registry_query(self):
        captured = {}

        def spy(**kwargs):
            captured.update(kwargs)
            return []

        with mock_patch(
            "construction.searchable_dropdown.api.search.searchable_link_search", spy
        ):
            search_link("Item", ITEM_ARABIC_DESCRIPTION, filters=None, page_length=10)

        self.assertTrue(captured, "Arabic query must reach the registry half")
        folded = captured.get("search_fields") or []
        self.assertEqual(folded, vendor_search_fields("Item"))
        for field in ("name", "item_name", "description", "item_group", "customer_code"):
            self.assertIn(field, folded, "vendor search field must be folded into the query")
        self.assertEqual(
            captured.get("search_fields"), folded, "folded fields must travel as search_fields"
        )

    def test_enabled_disabled_constraints_mirrored(self):
        captured = {}

        def spy(**kwargs):
            captured.update(kwargs)
            return []

        with mock_patch(
            "construction.searchable_dropdown.api.search.searchable_link_search", spy
        ):
            search_link("UOM", ARABIC_SHARED, filters=None, page_length=10)
            uom_filters = dict(captured.get("filters") or {})
            search_link("Account", ARABIC_SHARED, filters=None, page_length=10)
            account_filters = dict(captured.get("filters") or {})

        self.assertEqual(uom_filters.get("enabled"), 1, "UOM.enabled must be mirrored")
        self.assertIsNone(uom_filters.get("disabled"))
        self.assertEqual(account_filters.get("disabled"), ["!=", 1])
        self.assertIsNone(account_filters.get("enabled"))

    def test_arabic_path_returns_row_matched_only_on_vendor_field(self):
        item_groups = frappe.get_all("Item Group", pluck="name", limit=1)
        stock_uoms = frappe.get_all("UOM", pluck="name", limit=1)
        if not item_groups or not stock_uoms:
            self.skipTest("site has no Item Group / UOM to build an Item fixture")
        frappe.db.delete("Item", {"item_code": ITEM_CODE})
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": ITEM_CODE,
                "item_name": ITEM_CODE,
                "item_group": item_groups[0],
                "stock_uom": stock_uoms[0],
                "description": ITEM_ARABIC_DESCRIPTION,
            }
        ).insert(ignore_permissions=True)
        try:
            vendor_rows = vendor_search_link(
                "Item", ITEM_ARABIC_DESCRIPTION, filters=None, page_length=20
            )
            self.assertIn(
                ITEM_CODE,
                [row["value"] for row in vendor_rows],
                "the stock endpoint must find the row via Item.description",
            )
            ours = search_link("Item", ITEM_ARABIC_DESCRIPTION, filters=None, page_length=20)
            self.assertIn(
                ITEM_CODE,
                [row["value"] for row in ours],
                "A6 must return a row matched only on a vendor field it does not declare",
            )
        finally:
            frappe.db.delete("Item", {"item_code": ITEM_CODE})

    def test_explicit_searchfield_keeps_vendor_ownership(self):
        calls, patcher = self._spy_vendor()
        with patcher:
            ours = search_link(
                "UOM", ARABIC_SHARED, filters=None, page_length=10, searchfield="uom_name"
            )
        self.assertEqual(calls, ["UOM"], "searchfield must fall back to the vendor path")
        theirs = vendor_search_link(
            "UOM", ARABIC_SHARED, filters=None, page_length=10, searchfield="uom_name"
        )
        self.assertEqual(ours, theirs, "no Arabic merge may broaden an explicit field search")

    def test_unusable_filters_return_vendor_result_unchanged(self):
        list_filters = [["UOM", "common_code", "=", CODE_A]]
        calls, patcher = self._spy_vendor()
        with patcher:
            ours = search_link("UOM", ARABIC_SHARED, filters=list_filters, page_length=10)
        self.assertEqual(calls, ["UOM"], "list-shaped filters must stay on the vendor path")
        theirs = vendor_search_link(
            "UOM", ARABIC_SHARED, filters=list_filters, page_length=10
        )
        self.assertEqual(ours, theirs, "unfiltered Arabic rows must never widen a filtered query")

    def test_arabic_path_denies_records_for_non_admin(self):
        if not frappe.db.exists("User", NO_PERM_USER):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": NO_PERM_USER,
                    "first_name": "CT",
                    "new_password": "ct-test-pw-123",
                    "user_type": "System User",
                    "send_welcome_email": 0,
                    "roles": [],
                }
            ).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.set_user(NO_PERM_USER)
        try:
            rows = search_link("UOM", ARABIC_SHARED, filters=None, page_length=10)
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", NO_PERM_USER):
                frappe.delete_doc("User", NO_PERM_USER, force=True, ignore_permissions=True)
            frappe.db.commit()
        # The registry half fail-closes to an empty result when the user has no
        # read permission (search.py:220), so the assertion is on the outcome:
        # nothing readable must leak, and the same query must work for a
        # permitted user.
        self.assertEqual(
            rows, [], "no record may appear through the Arabic path without read permission"
        )
        control = search_link("UOM", ARABIC_SHARED, filters=None, page_length=10)
        self.assertTrue(control, "control: the same query must return rows for a permitted user")
