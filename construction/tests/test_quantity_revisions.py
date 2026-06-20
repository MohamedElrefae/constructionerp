import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from construction.services.quantity_revisions import (
    apply_approved_revision,
    approve_quantity_revision,
    create_lock_baseline,
    create_quantity_revision,
    create_variation_item_revision,
    get_current_qty,
    get_current_unit_price,
    update_boq_header_totals,
)
from construction.services.revised_boq_queries import (
    get_omitted_items,
    get_original_boq,
    get_quantity_history,
    get_revised_boq,
    get_variation_items,
    get_vo_impact,
)
from construction.tests.test_boq_helpers import get_or_create_test_project


class TestQuantityRevisions(FrappeTestCase):
    def setUp(self):
        self.project = get_or_create_test_project()
        frappe.db.delete("User Scope Context", {"user": "Administrator"})

    def tearDown(self):
        frappe.db.rollback()

    def _make_boq_item(self, title, quantity=100, rate=50):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": title,
                "project": self.project,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} Item",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = quantity
        item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        item.contract_unit_price = rate
        item.save(ignore_permissions=True)
        return header, item

    def _move_header_to_locked(self, header_name):
        header = frappe.get_doc("BOQ Header", header_name)
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        # Explicitly create baseline for tests
        from construction.services.quantity_revisions import create_lock_baseline

        create_lock_baseline(header_name)
        return header

    def _make_vo(
        self, header_name, item_name, revised_qty=None, revised_rate=None, line_type="Quantity Change"
    ):
        item = frappe.get_doc("BOQ Item", item_name)
        line = {
            "doctype": "VO Line",
            "line_type": line_type,
            "boq_item": item_name if line_type != "New Item" else None,
        }
        if revised_qty is not None:
            line["revised_qty"] = revised_qty
        if revised_rate:
            line["revised_unit_price"] = revised_rate
        return frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header_name,
                "status": "Draft",
                "lines": [line],
            }
        )

    def _approve_to_engineer(self, vo):
        vo.status = "Submitted"
        vo.save(ignore_permissions=True)
        vo.status = "Approved by Engineer"
        vo.save(ignore_permissions=True)
        vo.reload()
        return vo

    def _approve_by_client(self, vo):
        vo.status = "Approved by Client"
        vo.client_approval_document = "/private/files/signed-vo.pdf"
        vo.save(ignore_permissions=True)
        vo.reload()
        return vo

    def test_locking_boq_creates_baseline_revisions(self):
        header, item = self._make_boq_item("Baseline Test", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # Reload header to check if on_update fired
        header.reload()
        self.assertIsNotNone(header.locked_by)
        self.assertIsNotNone(header.locked_date)

        # Check baseline revision exists
        revisions = frappe.get_all(
            "BOQ Quantity Revision",
            filters={"boq_item": item.name, "revision_type": "Original Lock"},
            fields=["name", "previous_qty", "revised_qty", "status"],
        )
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0].previous_qty, 0)
        self.assertEqual(revisions[0].revised_qty, 100)
        self.assertEqual(revisions[0].status, "Approved")

        # Check BOQ Item has original and current qty
        item.reload()
        self.assertEqual(item.original_qty, 100)
        self.assertEqual(item.current_revised_qty, 100)
        self.assertEqual(item.current_revised_unit_price, 50)

    def test_re_saving_locked_boq_does_not_duplicate_baseline(self):
        header, item = self._make_boq_item("Baseline Dup", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # Count baseline revisions using SQL
        count1 = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabBOQ Quantity Revision` WHERE boq_header = %s AND revision_type = 'Original Lock'",
            header.name,
        )[0][0]

        # Save header again
        header = frappe.get_doc("BOQ Header", header.name)
        header.save(ignore_permissions=True)

        count2 = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabBOQ Quantity Revision` WHERE boq_header = %s AND revision_type = 'Original Lock'",
            header.name,
        )[0][0]

        self.assertEqual(count1, count2)
        self.assertEqual(count1, 1)

    def test_original_qty_unchanged_after_revisions(self):
        header, item = self._make_boq_item("Original Unchanged", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=125, revised_rate=60)
        vo.lines[0].rate_change_justification = "Quantity changed beyond 25%."
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        item.reload()
        self.assertEqual(item.original_qty, 100)
        self.assertEqual(item.current_revised_qty, 125)

    def test_current_revised_qty_updates_after_approved_revision(self):
        header, item = self._make_boq_item("Current Qty Update", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=110)
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        item.reload()
        self.assertEqual(item.current_revised_qty, 110)
        self.assertEqual(
            item.last_quantity_revision,
            frappe.db.get_value(
                "BOQ Quantity Revision",
                {"boq_item": item.name, "revision_type": "Increase Within 25%"},
                "name",
            ),
        )

    def test_draft_revision_does_not_update_current_revised_qty(self):
        header, item = self._make_boq_item("Draft No Update", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        revision = create_quantity_revision(
            boq_item=item.name,
            previous_qty=100,
            revised_qty=120,
            contract_unit_price=50,
            revised_unit_price=50,
            status="Draft",
        )

        item.reload()
        self.assertEqual(item.current_revised_qty, 100)  # Unchanged
        self.assertNotEqual(item.last_quantity_revision, revision.name)

    def test_quantity_increase_computes_correct_delta_and_value(self):
        header, item = self._make_boq_item("Increase Qty", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=126, revised_rate=60)
        vo.lines[0].rate_change_justification = "Quantity changed beyond 25%."
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        revision = frappe.get_doc(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "Increase Above 25%"}
        )

        self.assertEqual(revision.previous_qty, 100)
        self.assertEqual(revision.revised_qty, 126)
        self.assertEqual(revision.delta_qty, 26)
        self.assertEqual(revision.delta_from_contract_qty, 26)
        self.assertEqual(revision.change_pct_from_contract, 26)
        self.assertEqual(revision.rate_change_triggered, 1)
        self.assertEqual(revision.previous_value, 100 * 50)
        self.assertEqual(revision.revised_value, 126 * 60)
        self.assertEqual(revision.delta_value, 126 * 60 - 100 * 50)

    def test_quantity_decrease_computes_correct_delta_and_value(self):
        header, item = self._make_boq_item("Decrease Qty", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=75)
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        revision = frappe.get_doc(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "Decrease Within 25%"}
        )

        self.assertEqual(revision.previous_qty, 100)
        self.assertEqual(revision.revised_qty, 75)
        self.assertEqual(revision.delta_qty, -25)
        self.assertEqual(revision.delta_from_contract_qty, -25)
        self.assertEqual(revision.change_pct_from_contract, 25)
        self.assertEqual(revision.rate_change_triggered, 0)
        self.assertEqual(revision.previous_value, 100 * 50)
        self.assertEqual(revision.revised_value, 75 * 50)
        self.assertEqual(revision.delta_value, 75 * 50 - 100 * 50)

    def test_rate_change_triggered_computed_from_contract_pct(self):
        header, item = self._make_boq_item("Rate Change Trigger", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # 26% increase from contract = rate change triggered
        vo = self._make_vo(header.name, item.name, revised_qty=126, revised_rate=60)
        vo.lines[0].rate_change_justification = "Quantity changed beyond 25%."
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        revision = frappe.get_doc(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "Increase Above 25%"}
        )

        self.assertEqual(revision.change_pct_from_contract, 26)
        self.assertEqual(revision.rate_change_triggered, 1)

        # Current unit price updated
        item.reload()
        self.assertEqual(item.current_revised_unit_price, 60)

    def test_omission_sets_revised_qty_to_zero(self):
        header, item = self._make_boq_item("Omission", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=0, line_type="Omission")
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        revision = frappe.get_doc(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "Omission"}
        )

        self.assertEqual(revision.revised_qty, 0)
        self.assertEqual(revision.previous_qty, 100)
        self.assertEqual(revision.delta_qty, -100)

        item.reload()
        self.assertEqual(item.current_revised_qty, 0)

    def test_new_variation_item_creates_structure_and_item(self):
        header, _ = self._make_boq_item("New Variation", quantity=100, rate=50)
        group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Group Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "New Item",
                        "boq_structure": group.name,
                        "title": "New variation item",
                        "unit": frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos",
                        "revised_qty": 20,
                        "revised_unit_price": 80,
                        "rate_change_justification": "New item.",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        line = vo.lines[0]
        self.assertTrue(line.created_boq_structure)
        self.assertTrue(line.created_boq_item)
        self.assertTrue(line.created_quantity_revision)

        item = frappe.get_doc("BOQ Item", line.created_boq_item)
        self.assertEqual(item.original_qty, 0)
        self.assertEqual(item.current_revised_qty, 20)
        self.assertEqual(item.is_variation_item, 1)

        revision = frappe.get_doc("BOQ Quantity Revision", line.created_quantity_revision)
        self.assertEqual(revision.revision_type, "New Variation Item")
        self.assertEqual(revision.previous_qty, 0)
        self.assertEqual(revision.revised_qty, 20)

    def test_normal_post_lock_boq_item_creation_blocked(self):
        header, _ = self._make_boq_item("Lock Block", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # Try to create a new BOQ Structure directly after lock
        with self.assertRaises(Exception):
            frappe.get_doc(
                {
                    "doctype": "BOQ Structure",
                    "boq_header": header.name,
                    "title": "New Item",
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)

    def test_controlled_variation_item_creation_after_lock_allowed(self):
        header, _ = self._make_boq_item("Controlled Variation", quantity=100, rate=50)
        group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Group Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "New Item",
                        "boq_structure": group.name,
                        "title": "Controlled variation",
                        "unit": frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos",
                        "revised_qty": 15,
                        "revised_unit_price": 70,
                        "rate_change_justification": "Controlled variation.",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        # Should have created the variation item
        self.assertTrue(vo.lines[0].created_boq_item)

    def test_omitted_item_hidden_from_transaction_selectors(self):
        header, item = self._make_boq_item("Hide Omitted", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=0, line_type="Omission")
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        # Item should be hidden with exclude_zero_revised filter
        from construction.api.boq_link_queries import get_boq_items

        items = get_boq_items(
            "BOQ Item", "", "name", 0, 10, {"boq_header": header.name, "exclude_zero_revised": True}
        )
        self.assertNotIn(item.name, [i[0] for i in items])

        # But should be visible without the filter
        items_all = get_boq_items(
            "BOQ Item",
            "",
            "name",
            0,
            10,
            {
                "boq_header": header.name,
            },
        )
        self.assertIn(item.name, [i[0] for i in items_all])

    def test_quantity_history_reconstructs_item_timeline(self):
        header, item = self._make_boq_item("History", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # First VO: increase to 120
        vo1 = self._make_vo(header.name, item.name, revised_qty=120)
        vo1.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo1))

        # Second VO: decrease to 90
        vo2 = self._make_vo(header.name, item.name, revised_qty=90)
        vo2.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo2))

        # Get history
        history = get_quantity_history(item.name)
        self.assertEqual(len(history), 3)  # Original Lock + 2 changes

        # Check types
        types = [h.revision_type for h in history]
        self.assertIn("Original Lock", types)
        self.assertIn("Increase Within 25%", types)
        self.assertIn("Decrease Within 25%", types)

        # Check values
        increase_rev = next(h for h in history if h.revision_type == "Increase Within 25%")
        self.assertEqual(increase_rev.delta_qty, 20)

        decrease_rev = next(h for h in history if h.revision_type == "Decrease Within 25%")
        self.assertEqual(decrease_rev.delta_qty, -30)

    def test_no_item_code_required_for_new_item(self):
        header, _ = self._make_boq_item("No Item Code", quantity=100, rate=50)
        group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Group Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "New Item",
                        "boq_structure": group.name,
                        "title": "No item code needed",
                        "unit": frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos",
                        "revised_qty": 10,
                        "revised_unit_price": 60,
                        "rate_change_justification": "No item code.",
                    }
                ],
            }
        )
        # Should not throw about item_code
        vo.insert(ignore_permissions=True)

        line = vo.lines[0]
        self.assertIsNone(line.get("item_code"))
        self._approve_by_client(self._approve_to_engineer(vo))

    def test_vo_line_editing_blocked_after_engineer_approved(self):
        header, item = self._make_boq_item("Block Edit", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=110)
        vo.insert(ignore_permissions=True)

        # Approve to Engineer
        vo = self._approve_to_engineer(vo)

        # Try to edit a line
        vo.lines[0].revised_qty = 120
        with self.assertRaises(Exception):
            vo.save(ignore_permissions=True)

    def test_re_saving_approved_vo_does_not_duplicate_revisions(self):
        header, item = self._make_boq_item("No Dup", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=110)
        vo.insert(ignore_permissions=True)
        vo = self._approve_by_client(self._approve_to_engineer(vo))

        # Count revisions
        count1 = frappe.db.count("BOQ Quantity Revision", {"boq_item": item.name})

        # Re-save the approved VO
        vo.save(ignore_permissions=True)

        count2 = frappe.db.count("BOQ Quantity Revision", {"boq_item": item.name})

        self.assertEqual(count1, count2)

    def test_total_revised_value_computed_correctly(self):
        header, item = self._make_boq_item("Revised Value", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # At lock, total_revised_value should equal total_contract_value
        header.reload()
        self.assertEqual(header.total_revised_value, header.total_contract_value)

        # Create VO with rate change (>25% to trigger rate change)
        vo = self._make_vo(header.name, item.name, revised_qty=126, revised_rate=60)
        vo.lines[0].rate_change_justification = "Rate change."
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        # total_revised_value should now include the new rate
        header.reload()
        self.assertEqual(header.total_revised_value, 126 * 60)
        self.assertNotEqual(header.total_revised_value, header.total_contract_value)

    def test_revision_type_auto_computed_correctly(self):
        header, item = self._make_boq_item("Type Auto", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # Within 25%: 100 -> 124 (24% change)
        vo1 = self._make_vo(header.name, item.name, revised_qty=124)
        vo1.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo1))

        revision1 = frappe.get_doc(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "Increase Within 25%"}
        )
        self.assertEqual(revision1.change_pct_from_contract, 24)

        # Above 25%: 124 -> 130 (30% from original)
        vo2 = self._make_vo(header.name, item.name, revised_qty=130, revised_rate=60)
        vo2.lines[0].rate_change_justification = "Above 25%."
        vo2.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo2))

        revision2 = frappe.get_doc(
            "BOQ Quantity Revision", {"boq_item": item.name, "revision_type": "Increase Above 25%"}
        )
        self.assertEqual(revision2.change_pct_from_contract, 30)

    def test_fidic_rule_for_variation_items_with_zero_original_qty(self):
        header, _ = self._make_boq_item("Var FIDIC", quantity=100, rate=50)
        group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Group Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "New Item",
                        "boq_structure": group.name,
                        "title": "Variation FIDIC",
                        "unit": frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos",
                        "revised_qty": 10,
                        "revised_unit_price": 80,
                        "rate_change_justification": "New item.",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        line = vo.lines[0]
        revision = frappe.get_doc("BOQ Quantity Revision", line.created_quantity_revision)
        self.assertEqual(revision.change_pct_from_contract, 100)
        self.assertEqual(revision.rate_change_triggered, 1)

    def test_revised_boq_query_returns_correct_data(self):
        header, item = self._make_boq_item("Revised Query", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=126, revised_rate=60)
        vo.lines[0].rate_change_justification = "Rate change."
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        rows = get_revised_boq(header.name)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.revised_value, 126 * 60)
        self.assertEqual(row.delta_value, 126 * 60 - 100 * 50)

    def test_vo_impact_query_groups_by_vo(self):
        header, item = self._make_boq_item("VO Impact", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo1 = self._make_vo(header.name, item.name, revised_qty=110)
        vo1.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo1))

        vo2 = self._make_vo(header.name, item.name, revised_qty=90)
        vo2.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo2))

        impact = get_vo_impact(header.name)
        self.assertEqual(len(impact), 2)
        # VO1: delta = +10 * 50 = +500
        # VO2: delta = (90 - 110) * 50 = -1000
        # Total = -500
        total_delta = sum(row.total_delta_value for row in impact)
        self.assertEqual(total_delta, -500)

    def test_omitted_items_report(self):
        header, item = self._make_boq_item("Omitted Report", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = self._make_vo(header.name, item.name, revised_qty=0, line_type="Omission")
        vo.insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        omitted = get_omitted_items(header.name)
        self.assertEqual(len(omitted), 1)
        self.assertEqual(omitted[0].boq_item, item.name)
        self.assertEqual(omitted[0].original_qty, 100)

    def test_original_boq_query_excludes_variation_items(self):
        header, _ = self._make_boq_item("Original BOQ", quantity=100, rate=50)
        group = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Group Section",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "New Item",
                        "boq_structure": group.name,
                        "title": "Variation",
                        "unit": frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos",
                        "revised_qty": 20,
                        "revised_unit_price": 80,
                        "rate_change_justification": "New item.",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._approve_by_client(self._approve_to_engineer(vo))

        original = get_original_boq(header.name)
        self.assertEqual(len(original), 1)  # Only original item
        self.assertEqual(original[0].contract_qty, 100)

        revised = get_revised_boq(header.name)
        self.assertEqual(len(revised), 2)  # Original + variation


class TestQuantityRevisionService(FrappeTestCase):
    def setUp(self):
        self.project = get_or_create_test_project()

    def tearDown(self):
        frappe.db.rollback()

    def _make_boq_item(self, title, quantity=100, rate=50):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "title": title,
                "project": self.project,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} Item",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = quantity
        item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        item.contract_unit_price = rate
        item.save(ignore_permissions=True)
        return header, item

    def _move_header_to_locked(self, header_name):
        header = frappe.get_doc("BOQ Header", header_name)
        for status in ("Pricing", "Frozen", "Locked"):
            header.status = status
            header.save(ignore_permissions=True)
        # Explicitly create baseline for tests
        from construction.services.quantity_revisions import create_lock_baseline

        create_lock_baseline(header_name)
        return header

    def test_create_lock_baseline_idempotent(self):
        header, item = self._make_boq_item("Baseline", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        # Count after first (implicit) baseline creation
        count_before = frappe.db.count(
            "BOQ Quantity Revision", {"boq_header": header.name, "revision_type": "Original Lock"}
        )

        result1 = create_lock_baseline(header.name)
        self.assertTrue(result1["success"])
        self.assertEqual(result1.get("message"), "Baseline already exists.")

        result2 = create_lock_baseline(header.name)
        self.assertTrue(result2["success"])
        self.assertEqual(result2.get("message"), "Baseline already exists.")

        # Count should not change
        count_after = frappe.db.count(
            "BOQ Quantity Revision", {"boq_header": header.name, "revision_type": "Original Lock"}
        )
        self.assertEqual(count_before, count_after)

    def test_approve_revision_updates_current_revised_unit_price(self):
        header, item = self._make_boq_item("Unit Price", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        revision = create_quantity_revision(
            boq_item=item.name,
            previous_qty=100,
            revised_qty=110,
            contract_unit_price=50,
            revised_unit_price=60,
            status="Draft",
        )

        approve_quantity_revision(revision.name)

        item.reload()
        self.assertEqual(item.current_revised_unit_price, 60)
        self.assertEqual(item.current_revised_qty, 110)

    def test_get_current_qty_and_unit_price(self):
        header, item = self._make_boq_item("Get Current", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        qty = get_current_qty(item.name)
        price = get_current_unit_price(item.name)

        self.assertEqual(qty, 100)
        self.assertEqual(price, 50)

    def test_variation_item_revision_creates_approved_revision(self):
        header, item = self._make_boq_item("Var Revision", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        revision = create_variation_item_revision(
            boq_item=item.name,
            quantity=20,
            unit_price=80,
            variation_order=None,
            rate_change_justification="New variation item.",
        )

        self.assertEqual(revision.status, "Approved")
        self.assertEqual(revision.revision_type, "New Variation Item")
        self.assertEqual(revision.previous_qty, 0)
        self.assertEqual(revision.revised_qty, 20)
        self.assertEqual(revision.revised_unit_price, 80)

    def test_update_boq_header_totals(self):
        header, item = self._make_boq_item("Header Totals", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        update_boq_header_totals(header.name)

        header.reload()
        self.assertEqual(header.total_revised_value, 100 * 50)

        # Create a revision
        revision = create_quantity_revision(
            boq_item=item.name,
            previous_qty=100,
            revised_qty=110,
            contract_unit_price=50,
            revised_unit_price=60,
            status="Draft",
        )
        apply_approved_revision(revision)

        header.reload()
        self.assertEqual(header.total_revised_value, 110 * 60)

    def test_process_approved_vo_lines_idempotent(self):
        header, item = self._make_boq_item("Process Idempotent", quantity=100, rate=50)
        self._move_header_to_locked(header.name)

        vo = frappe.get_doc(
            {
                "doctype": "Variation Order",
                "boq_header": header.name,
                "status": "Draft",
                "lines": [
                    {
                        "doctype": "VO Line",
                        "line_type": "Quantity Change",
                        "boq_item": item.name,
                        "revised_qty": 110,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

        # Approve to Engineer
        vo.status = "Submitted"
        vo.save(ignore_permissions=True)
        vo.status = "Approved by Engineer"
        vo.save(ignore_permissions=True)

        # Approve by Client
        vo.status = "Approved by Client"
        vo.client_approval_document = "/private/files/test.pdf"
        vo.save(ignore_permissions=True)

        line = vo.lines[0]
        self.assertTrue(line.created_quantity_revision)

        # Re-save should not create duplicate
        vo.save(ignore_permissions=True)

        count = frappe.db.count("BOQ Quantity Revision", {"boq_item": item.name})
        self.assertEqual(count, 2)  # Original Lock + 1 change
