"""F16: BOQ import preview/commit contract and duplicate-commit suppression (K-01)."""

import io

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from construction.services.boq_import_service import BOQImportService


def _workbook(rows):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Title / Description", "Type", "Unit", "Quantity", "Unit Price", "Factor"])
    for title, qty in rows:
        ws.append([title, "Item", "Nos", qty, 20, 1])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestBOQImportIdempotency(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        hdr = frappe.db.get_value("BOQ Header", {"title": "F16 Regression BOQ"}, "name")
        if not hdr:
            h = frappe.new_doc("BOQ Header")
            h.project = "PROJ-0014"
            h.boq_type = "Tender"
            h.title = "F16 Regression BOQ"
            h.insert(ignore_permissions=True)
            hdr = h.name
        cls.hdr = hdr

    def _upload(self, content, name):
        f = save_file(name, content, "BOQ Header", self.hdr, folder=None, decode=False, is_private=0)
        frappe.db.commit()
        return f.file_url

    def _preview_commit(self, file_url, dry_run, mode="Flat"):
        return BOQImportService.import_from_excel(
            file_url=file_url, boq_header=self.hdr, dry_run=dry_run, confirmed_import_mode=mode
        )

    def test_preview_writes_nothing_then_commit_persists(self):
        frappe.set_user("Administrator")
        before = frappe.db.count("BOQ Item", {"boq_header": self.hdr})
        furl = self._upload(_workbook([("F16 reg A", 5)]), "f16-reg-a.xlsx")
        preview = self._preview_commit(furl, True)
        self.assertTrue(preview.get("success"))
        self.assertTrue(preview.get("dry_run"))
        self.assertEqual(frappe.db.count("BOQ Item", {"boq_header": self.hdr}), before)
        result = self._preview_commit(furl, False)
        self.assertTrue(result.get("success"))
        self.assertFalse(result.get("dry_run"))
        self.assertEqual(frappe.db.count("BOQ Item", {"boq_header": self.hdr}), before + 1)
        self.assertTrue(frappe.db.exists("BOQ Import Batch", result.get("import_batch")))

    def test_duplicate_commit_suppressed(self):
        """Same attachment committed twice yields one batch and one item set (fails before fix)."""
        frappe.set_user("Administrator")
        furl = self._upload(_workbook([("F16 reg dup", 7)]), "f16-reg-dup.xlsx")
        first = self._preview_commit(furl, False)
        self.assertTrue(first.get("success"))
        self.assertFalse(first.get("duplicate_suppressed", False))
        before = frappe.db.count("BOQ Item", {"boq_header": self.hdr})
        second = self._preview_commit(furl, False)
        self.assertTrue(second.get("success"))
        self.assertTrue(second.get("duplicate_suppressed"))
        self.assertEqual(second.get("import_batch"), first.get("import_batch"))
        self.assertEqual(frappe.db.count("BOQ Item", {"boq_header": self.hdr}), before)

    def test_committed_items_carry_description(self):
        """F17: imported items must carry their specification text (fails before fix)."""
        frappe.set_user("Administrator")
        furl = self._upload(_workbook([("F16 reg spec", 4)]), "f16-reg-spec.xlsx")
        result = self._preview_commit(furl, False)
        self.assertTrue(result.get("success"))
        for row in result.get("created_items") or []:
            self.assertTrue(
                (frappe.db.get_value("BOQ Item", row["name"], "cost_item") or "").strip(),
                f"item {row['name']} has blank cost_item",
            )

    def test_recommit_after_deletion_proceeds(self):
        """Suppression keys on live items: deleting the import allows a fresh commit."""
        frappe.set_user("Administrator")
        furl = self._upload(_workbook([("F16 reg redel", 3)]), "f16-reg-redel.xlsx")
        first = self._preview_commit(furl, False)
        self.assertTrue(first.get("success"))
        for name in frappe.db.get_list(
            "BOQ Item",
            filters={"boq_header": self.hdr, "import_batch": first.get("import_batch")},
            pluck="name",
        ):
            frappe.delete_doc("BOQ Item", name, ignore_permissions=True)
        second = self._preview_commit(furl, False)
        self.assertTrue(second.get("success"))
        self.assertFalse(second.get("duplicate_suppressed", False))
        self.assertNotEqual(second.get("import_batch"), first.get("import_batch"))
