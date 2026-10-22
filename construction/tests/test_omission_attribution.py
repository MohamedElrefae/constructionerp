"""Bounded omitted-item attribution correction (UI-33) regression tests.

Covers the native save path for all eight transaction parents, parent-bound
historical identity, the VO/transaction dropdown-form query parity, canonical
zero/NULL quantity semantics, and portable ordinary-role scope controls.

The suite is portable: it creates every fixture it needs (projects, BOQ header,
items, VO approval, files) and cleans them up including on-disk artefacts.
No required control may skip: the suite contains no skipTest() calls.
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate

from construction.api.boq_link_queries import get_boq_items, get_vo_line_boq_items
from construction.services.boq_accounting import (
    is_new_or_changed_attribution,
    validate_transaction_row,
)
from construction.services.boq_lookups import effective_boq_quantity, is_omitted_boq_item
from construction.services.boq_transaction_validation import (
    CHILD_TABLE_BY_DOCTYPE,
    validate_document,
)
from construction.tests.test_boq_helpers import get_or_create_test_project

OMISSION_REFUSAL = "Omitted BOQ Item"


class TestOmittedItemAttribution(FrappeTestCase):
    """Ordinary-role authorization controls and native save-path refusals."""

    def setUp(self):
        self._created_files = []
        self.project = get_or_create_test_project()
        self.company = frappe.db.get_value("Project", self.project, "company")
        self.other_project = self._make_owned_project("Scope")
        self.header, self.live_item, self.omitted_item = self._make_locked_header_with_two_items()
        self._omit(self.omitted_item)
        self.stock_item = self._ensure_stock_item()
        self.second_stock_item = self._ensure_stock_item(index=2)
        self.warehouse = self._ensure_warehouse()
        self.qty_state_before = self._quantity_state(self.omitted_item.name)

    def tearDown(self):
        frappe.set_user("Administrator")
        for file_doc in getattr(self, "_created_files", []):
            try:
                path = file_doc.get_full_path()
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            try:
                frappe.db.delete("File", {"name": file_doc.name})
            except Exception:
                pass
        self._created_files = []
        frappe.db.rollback()

    # ---------------------------------------------------------------- fixtures

    def _make_owned_project(self, suffix):
        """A second project owned by this suite (portable, no site dependency)."""
        doc = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": f"_Test Omission {suffix} {frappe.generate_hash(length=5)}",
                "company": self.company,
                "naming_series": "PROJ-.####",
            }
        ).insert(ignore_permissions=True)
        return doc.name

    def _make_pdf(self, attached_to_name):
        """Owned approval attachment built through the native File lifecycle."""
        import io

        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buffer = io.BytesIO()
        writer.write(buffer)
        doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"omission_ctl_{frappe.generate_hash(length=6)}.pdf",
                "attached_to_doctype": "Variation Order",
                "attached_to_name": attached_to_name,
                "is_private": 1,
                "content": buffer.getvalue(),
            }
        )
        doc.insert(ignore_permissions=True)
        self._created_files.append(doc)
        return doc

    def _make_locked_header_with_two_items(self):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": f"Omission Attribution {frappe.generate_hash(length=6)}",
                "project": self.project,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

        items = []
        for title, quantity in (("Live", 40), ("To Omit", 60)):
            structure = frappe.get_doc(
                {
                    "doctype": "BOQ Structure",
                    "boq_header": header.name,
                    "title": f"{title} Structure",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)
            item = frappe.get_doc("BOQ Item", {"structure": structure.name})
            item.quantity = quantity
            item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
            item.contract_unit_price = 25
            item.save(ignore_permissions=True)
            items.append(item)

        header = frappe.get_doc("BOQ Header", header.name)
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        from construction.services.quantity_revisions import create_lock_baseline

        create_lock_baseline(header.name)
        return header, items[0], items[1]

    def _omit(self, item):
        """Omit through the supported VO approval lifecycle (no raw field edits)."""
        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": self.header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "Omission",
                        "boq_item": item.name,
                        "revised_qty": 0,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        for status in ("Submitted", "Approved by Engineer"):
            vo.status = status
            vo.save(ignore_permissions=True)
        pdf = self._make_pdf(vo.name)
        vo.status = "Approved by Client"
        vo.client_approval_document = pdf.name
        vo.save(ignore_permissions=True)
        item.reload()
        return item

    def _ensure_stock_item(self, index=1):
        existing = frappe.get_all(
            "Item", filters={"is_stock_item": 1, "disabled": 0}, fields=["name"], limit=index
        )
        if len(existing) >= index:
            return existing[index - 1].name
        uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        doc = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": f"OMI-CTL-{index}-{frappe.generate_hash(length=6)}",
                "item_name": f"Omission Control Item {index}",
                "is_stock_item": 1,
                "item_group": group,
                "stock_uom": uom,
            }
        ).insert(ignore_permissions=True)
        return doc.name

    def _ensure_warehouse(self):
        existing = frappe.db.get_value("Warehouse", {"company": self.company, "is_group": 0}, "name")
        if existing:
            return existing
        doc = frappe.get_doc(
            {
                "doctype": "Warehouse",
                "warehouse_name": f"Omission Control {frappe.generate_hash(length=4)}",
                "company": self.company,
            }
        ).insert(ignore_permissions=True)
        return doc.name

    def _quantity_state(self, item_name):
        return frappe.db.get_value(
            "BOQ Item",
            item_name,
            ["quantity", "current_revised_qty", "last_quantity_revision"],
            as_dict=True,
        )

    def _mr_rows(self, boq_item, item_code=None):
        item_code = item_code or self.stock_item
        row = {
            "item_code": item_code,
            "qty": 1,
            "uom": frappe.db.get_value("Item", item_code, "stock_uom") or "Nos",
            "conversion_factor": 1,
            "schedule_date": add_days(nowdate(), 1),
            "warehouse": self.warehouse,
            "project": self.project,
            "expense_category": "Direct",
        }
        if boq_item:
            row.update(
                {
                    "boq_item": boq_item,
                    "boq_header": frappe.db.get_value("BOQ Item", boq_item, "boq_header"),
                    "boq_structure": frappe.db.get_value("BOQ Item", boq_item, "structure"),
                }
            )
        return row

    def _new_material_request(self, boq_item):
        return frappe.get_doc(
            {
                "doctype": "Material Request",
                "material_request_type": "Purchase",
                "transaction_date": nowdate(),
                "company": self.company,
                "items": [self._mr_rows(boq_item)],
            }
        )

    def _assert_insert_refused(self, doc, message=OMISSION_REFUSAL):
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.insert(ignore_permissions=True)
        self.assertIn(message, str(ctx.exception))

    def _assert_save_refused(self, doc, message=OMISSION_REFUSAL):
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)
        self.assertIn(message, str(ctx.exception))

    # -------------------------------------------------------------- save path

    def test_new_omitted_attribution_refused_for_all_eight_parents(self):
        for doctype, table_field in sorted(CHILD_TABLE_BY_DOCTYPE.items()):
            with self.subTest(parent=doctype):
                row = frappe._dict(
                    {
                        "idx": 1,
                        "project": self.project,
                        "boq_item": self.omitted_item.name,
                        "boq_header": self.header.name,
                    }
                )
                doc = frappe._dict({"doctype": doctype, table_field: [row]})
                with self.assertRaises(frappe.ValidationError) as ctx:
                    validate_document(doc)
                self.assertIn(OMISSION_REFUSAL, str(ctx.exception))

    def test_new_valid_attribution_still_allowed_for_all_eight_parents(self):
        for doctype, table_field in sorted(CHILD_TABLE_BY_DOCTYPE.items()):
            with self.subTest(parent=doctype):
                row = frappe._dict(
                    {
                        "idx": 1,
                        "project": self.project,
                        "boq_item": self.live_item.name,
                        "boq_header": self.header.name,
                    }
                )
                validate_document(frappe._dict({"doctype": doctype, table_field: [row]}))

    def test_optional_attribution_still_allowed_without_boq_fields(self):
        validate_transaction_row(
            frappe._dict({"idx": 1, "expense_category": "Direct"}),
            frappe._dict({"doctype": "Material Request"}),
        )

    def test_native_material_request_save_refuses_new_omitted_attribution(self):
        self._assert_insert_refused(self._new_material_request(self.omitted_item.name))
        # Nothing was persisted by the refused native insert.
        self.assertEqual(frappe.db.count("Material Request Item", {"boq_item": self.omitted_item.name}), 0)

    def test_refusal_creates_no_revisions_and_changes_nothing(self):
        revisions_before = frappe.db.count("BOQ Quantity Revision", {"boq_header": self.header.name})
        header_row_before = frappe.db.sql(
            "SELECT * FROM `tabBOQ Header` WHERE name=%s", (self.header.name,), as_dict=True
        )

        self._assert_insert_refused(self._new_material_request(self.omitted_item.name))

        self.assertEqual(
            frappe.db.count("BOQ Quantity Revision", {"boq_header": self.header.name}),
            revisions_before,
        )
        self.assertEqual(self._quantity_state(self.omitted_item.name), self.qty_state_before)
        self.assertEqual(
            frappe.db.sql("SELECT * FROM `tabBOQ Header` WHERE name=%s", (self.header.name,), as_dict=True),
            header_row_before,
        )
        self.assertEqual(frappe.db.count("Variation Order", {"boq_header": self.header.name}), 1)

    def test_added_and_changed_attribution_on_existing_document_refused(self):
        # (a) a row added to an existing document
        mr = self._new_material_request(None)
        mr.insert(ignore_permissions=True)
        self.assertEqual(mr.docstatus, 0)

        mr.append("items", self._mr_rows(self.omitted_item.name, item_code=self.second_stock_item))
        self._assert_save_refused(mr)
        self.assertEqual(frappe.db.count("Material Request Item", {"boq_item": self.omitted_item.name}), 0)

        # (b) an existing row's item link changed to the omitted item
        mr = self._new_material_request(self.live_item.name)
        mr.insert(ignore_permissions=True)
        stored_row = mr.items[0].name
        mr.items[0].boq_item = self.omitted_item.name
        mr.items[0].boq_structure = self.omitted_item.structure
        self._assert_save_refused(mr)
        self.assertEqual(
            frappe.db.get_value("Material Request Item", stored_row, "boq_item"),
            self.live_item.name,
        )

    def test_historical_reference_keeps_saving_submitting_and_cancelling(self):
        mr = self._new_material_request(self.live_item.name)
        mr.insert(ignore_permissions=True)
        row_name = mr.items[0].name

        # The item is omitted AFTER the transaction already references it.
        self._omit(self.live_item)
        self.assertEqual(flt(self.live_item.current_revised_qty), 0)

        # Draft re-save (row unchanged) still works.
        mr.reload()
        mr.items[0].qty = 3
        mr.save(ignore_permissions=True)

        # The stored reference is unchanged and still readable.
        self.assertEqual(
            frappe.db.get_value("Material Request Item", row_name, "boq_item"),
            self.live_item.name,
        )

        mr.reload()
        mr.submit()
        self.assertEqual(mr.docstatus, 1)

        mr.reload()
        mr.cancel()
        self.assertEqual(mr.docstatus, 2)

    # ------------------------------------------------- parent-bound identity

    def test_historical_exception_requires_current_parent_identity(self):
        """A child row of another parent must never qualify for the historical exception."""
        other_mr = self._new_material_request(self.live_item.name)
        other_mr.insert(ignore_permissions=True)
        other_row_name = other_mr.items[0].name

        current_mr = self._new_material_request(self.live_item.name)
        current_mr.insert(ignore_permissions=True)

        forged = frappe._dict(
            {
                "name": other_row_name,
                "doctype": "Material Request Item",
                "idx": 1,
                "project": self.project,
                "boq_item": self.omitted_item.name,
                "boq_header": self.header.name,
            }
        )
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_transaction_row(forged, current_mr, "items")
        self.assertIn(OMISSION_REFUSAL, str(ctx.exception))

    def test_new_parent_never_qualifies_for_historical_exception(self):
        other_mr = self._new_material_request(self.live_item.name)
        other_mr.insert(ignore_permissions=True)
        other_row_name = other_mr.items[0].name

        new_parent = frappe._dict(
            {
                "doctype": "Material Request",
                "name": f"new-material-request-{frappe.generate_hash(length=8)}",
            }
        )
        forged = frappe._dict(
            {
                "name": other_row_name,
                "doctype": "Material Request Item",
                "idx": 1,
                "project": self.project,
                "boq_item": self.omitted_item.name,
                "boq_header": self.header.name,
            }
        )
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_transaction_row(forged, new_parent, "items")
        self.assertIn(OMISSION_REFUSAL, str(ctx.exception))

    def test_child_doctype_mismatch_is_never_historical(self):
        other_mr = self._new_material_request(self.live_item.name)
        other_mr.insert(ignore_permissions=True)
        current_mr = self._new_material_request(self.live_item.name)
        current_mr.insert(ignore_permissions=True)

        forged = frappe._dict(
            {
                "name": other_mr.items[0].name,
                "doctype": "Purchase Order Item",
                "idx": 1,
                "project": self.project,
                "boq_item": self.omitted_item.name,
                "boq_header": self.header.name,
            }
        )
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_transaction_row(forged, current_mr, "items")
        self.assertIn(OMISSION_REFUSAL, str(ctx.exception))

    def test_new_or_changed_attribution_detection(self):
        # No persisted identity -> new.
        self.assertTrue(is_new_or_changed_attribution(frappe._dict({"idx": 1, "boq_item": "X"})))

        mr = self._new_material_request(self.live_item.name)
        mr.insert(ignore_permissions=True)
        identity = {
            "name": mr.items[0].name,
            "doctype": "Material Request Item",
            "boq_item": self.live_item.name,
        }

        # Persisted row of THIS parent with the same value -> historical reference.
        self.assertFalse(is_new_or_changed_attribution(frappe._dict(identity), mr, "items"))
        # Persisted row of THIS parent with a different value -> changed.
        changed = frappe._dict({**identity, "boq_item": self.omitted_item.name})
        self.assertTrue(is_new_or_changed_attribution(changed, mr, "items"))
        # Persisted row gaining an attribution -> new.
        frappe.db.set_value("Material Request Item", mr.items[0].name, "boq_item", None)
        added = frappe._dict({**identity, "boq_item": self.live_item.name})
        self.assertTrue(is_new_or_changed_attribution(added, mr, "items"))

    # ------------------------------------------------------- quantity semantics

    def test_zero_and_null_quantity_semantics(self):
        self.assertEqual(
            effective_boq_quantity(frappe._dict({"current_revised_qty": None, "quantity": 10})), 10
        )
        self.assertFalse(is_omitted_boq_item(frappe._dict({"current_revised_qty": None, "quantity": 10})))

        self.assertEqual(
            effective_boq_quantity(frappe._dict({"current_revised_qty": None, "quantity": 0})), 0
        )
        self.assertTrue(is_omitted_boq_item(frappe._dict({"current_revised_qty": None, "quantity": 0})))

        # Canonical omission: approved Omission revision stores zero current qty.
        self.assertTrue(is_omitted_boq_item(frappe._dict({"current_revised_qty": 0, "quantity": 60})))
        self.assertTrue(is_omitted_boq_item(None))
        self.assertFalse(is_omitted_boq_item(frappe._dict({"current_revised_qty": 5, "quantity": 10})))

        # The DB item omitted through the VO lifecycle reads as omitted.
        self.assertTrue(is_omitted_boq_item(self._quantity_state(self.omitted_item.name)))

    def test_never_revised_item_uses_original_quantity(self):
        """Effective quantity falls back to the original quantity when never revised."""
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": f"Null Current Qty {frappe.generate_hash(length=6)}",
                "project": self.project,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"

        zero_item = None
        positive_item = None
        for title, quantity in (("Zero Quantity", 0), ("Never Revised", 5)):
            structure = frappe.get_doc(
                {
                    "doctype": "BOQ Structure",
                    "boq_header": header.name,
                    "title": title,
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)
            item = frappe.get_doc("BOQ Item", {"structure": structure.name})
            item.quantity = quantity
            item.unit = uom
            item.save(ignore_permissions=True)
            if quantity:
                positive_item = item
            else:
                zero_item = item

        header = frappe.get_doc("BOQ Header", header.name)
        header.status = "Pricing"
        header.save(ignore_permissions=True)
        header.status = "Frozen"
        header.save(ignore_permissions=True)

        # COALESCE(current_revised_qty, quantity) drives the contract: a never-revised
        # zero-quantity item is non-selectable, a never-revised positive item is not.
        self.assertEqual(effective_boq_quantity(self._quantity_state(zero_item.name)), 0.0)
        self.assertTrue(is_omitted_boq_item(self._quantity_state(zero_item.name)))
        self.assertFalse(is_omitted_boq_item(self._quantity_state(positive_item.name)))

        # The SQL link filter must agree with the Python contract.
        visible = [
            row[0]
            for row in get_boq_items(
                "BOQ Item",
                "",
                "name",
                0,
                50,
                {"boq_header": header.name, "exclude_zero_revised": True},
            )
        ]
        self.assertNotIn(zero_item.name, visible)
        self.assertIn(positive_item.name, visible)

        zero_row = frappe._dict(
            {"idx": 1, "project": self.project, "boq_item": zero_item.name, "boq_header": header.name}
        )
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_transaction_row(zero_row, frappe._dict({"project": self.project}))
        self.assertIn(OMISSION_REFUSAL, str(ctx.exception))

        positive_row = frappe._dict(
            {
                "idx": 1,
                "project": self.project,
                "boq_item": positive_item.name,
                "boq_header": header.name,
            }
        )
        validate_transaction_row(positive_row, frappe._dict({"project": self.project}))

    # ------------------------------------------------------- dropdown/form parity

    def test_vo_dropdown_and_form_query_agree_on_omitted_item(self):
        header_filter = {"boq_header": self.header.name}

        vo_form_query = get_boq_items(
            "BOQ Item",
            "",
            "name",
            0,
            50,
            {**header_filter, "is_variation_item": 0, "exclude_zero_revised": True},
        )
        vo_dropdown_query = get_vo_line_boq_items(
            "BOQ Item", "", "name", 0, 50, {**header_filter, "exclude_zero_revised": True}
        )

        form_names = [row[0] for row in vo_form_query]
        dropdown_names = [row[0] for row in vo_dropdown_query]

        self.assertNotIn(self.omitted_item.name, form_names)
        self.assertNotIn(self.omitted_item.name, dropdown_names)
        self.assertIn(self.live_item.name, form_names)
        self.assertIn(self.live_item.name, dropdown_names)
        # Exact parity between the two queries for this header.
        self.assertEqual(sorted(form_names), sorted(dropdown_names))

    def test_transaction_dropdown_filter_matches_form_query(self):
        """Cascade args and buildItemFilters both pass exclude_zero_revised."""
        cascade_filters = {
            "boq_header": self.header.name,
            "structure": self.live_item.structure,
            "project": self.project,
            "require_boq_header": True,
            "require_structure": True,
            "allowed_statuses": ["Frozen", "Locked"],
            "exclude_zero_revised": True,
        }
        names = [row[0] for row in get_boq_items("BOQ Item", "", "name", 0, 50, cascade_filters)]
        self.assertNotIn(self.omitted_item.name, names)
        self.assertIn(self.live_item.name, names)

    def test_opt_in_filter_keeps_other_callers_unchanged(self):
        """Without exclude_zero_revised the queries keep offering every item."""
        vo_all = [
            row[0]
            for row in get_vo_line_boq_items("BOQ Item", "", "name", 0, 50, {"boq_header": self.header.name})
        ]
        transaction_all = [
            row[0]
            for row in get_boq_items(
                "BOQ Item", "", "name", 0, 50, {"boq_header": self.header.name, "is_variation_item": 0}
            )
        ]
        self.assertIn(self.omitted_item.name, vo_all)
        self.assertIn(self.omitted_item.name, transaction_all)

    # --------------------------------------------------- scope / role controls

    def test_foreign_scope_attribution_still_denied(self):
        """Mandatory coverage: the owned second project is out of the BOQ's scope."""
        row = frappe._dict({"idx": 1, "project": self.other_project, "boq_item": self.live_item.name})
        with self.assertRaises(frappe.ValidationError) as ctx:
            validate_transaction_row(
                row, frappe._dict({"project": self.other_project, "doctype": "Material Request"})
            )
        self.assertIn("Project mismatch", str(ctx.exception))

    def test_ordinary_user_scope_negative_and_authorized_positive(self):
        """Real ordinary users: scope denial (doctype AND record) + native saves."""
        ordinary = self._make_ordinary_user(("Purchase User",))
        authorized = self._make_ordinary_user(("Purchase User", "Site Engineer", "Projects User"))
        # The authorised representative carries the same Company-A/Project-A scope as the
        # accepted positive fixtures; a missing scope is not a wildcard.
        self._make_scope_context(ordinary, self.company, self.project)
        self._make_scope_context(authorized, self.company, self.project)
        try:
            # --- negative: the ordinary transaction persona has no BOQ scope at all ---
            frappe.set_user(ordinary)
            self.assertFalse(frappe.has_permission("BOQ Header", "read"))
            self.assertFalse(frappe.has_permission("BOQ Header", "read", doc=self.header.name))
            self.assertFalse(frappe.has_permission("BOQ Item", "read"))
            self.assertFalse(frappe.has_permission("BOQ Item", "read", doc=self.live_item.name))
            self.assertTrue(frappe.has_permission("Material Request", "create"))

            # A native save (no ignore_permissions) that reaches outside the scoped
            # project is refused for the ordinary user too.
            foreign_row = self._mr_rows(self.live_item.name)
            foreign_row["project"] = self.other_project
            foreign_doc = frappe.get_doc(
                {
                    "doctype": "Material Request",
                    "material_request_type": "Purchase",
                    "transaction_date": nowdate(),
                    "company": self.company,
                    "items": [foreign_row],
                }
            )
            with self.assertRaises(frappe.ValidationError) as ctx:
                foreign_doc.insert()
            self.assertIn("Project mismatch", str(ctx.exception))

            # --- positive: the authorised bundle reads the BOQ scope and can save ---
            frappe.set_user(authorized)
            self.assertTrue(frappe.has_permission("BOQ Header", "read"))
            self.assertTrue(frappe.has_permission("BOQ Header", "read", doc=self.header.name))
            self.assertTrue(frappe.has_permission("BOQ Item", "read"))
            self.assertTrue(frappe.has_permission("BOQ Item", "read", doc=self.live_item.name))

            doc = self._new_material_request(self.live_item.name)
            doc.insert()
            self.assertEqual(doc.docstatus, 0)
            self.assertEqual(doc.items[0].boq_item, self.live_item.name)
            self.assertEqual(
                frappe.db.get_value("Material Request Item", doc.items[0].name, "boq_item"),
                self.live_item.name,
            )
        finally:
            frappe.set_user("Administrator")

    def test_correction_does_not_change_role_permissions(self):
        """The bounded fix must not widen or narrow any permission grant."""
        select_permissions = "SELECT parent, role, `read`, `write`, `create`, `submit`, permlevel FROM `tabDocPerm` ORDER BY parent, role, permlevel"
        select_custom = "SELECT parent, role, `read`, `write`, `create`, `submit`, permlevel FROM `tabCustom DocPerm` ORDER BY parent, role, permlevel"
        docperm_before = frappe.db.sql(select_permissions)
        custom_before = frappe.db.sql(select_custom)

        self._assert_insert_refused(self._new_material_request(self.omitted_item.name))

        self.assertEqual(docperm_before, frappe.db.sql(select_permissions))
        self.assertEqual(custom_before, frappe.db.sql(select_custom))

    @staticmethod
    def _make_scope_context(user, company, project):
        """Owned scope assignment (Company-A/Project-A) for a representative user."""
        doc = frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": user,
                "company": company,
                "project": project,
            }
        ).insert(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _make_ordinary_user(roles):
        email = f"omission-ctl-{frappe.generate_hash(length=8)}@example.invalid"
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Omission Control",
                "send_welcome_email": 0,
                "roles": [{"role": role} for role in roles],
            }
        ).insert(ignore_permissions=True)
        return doc.name
