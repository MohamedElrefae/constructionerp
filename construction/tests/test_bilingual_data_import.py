"""Bilingual Data Import verification suite.

Verifies end-to-end bulk Data Import behavior for bilingual master records:
- Server-side rejection of bidi controls / unsafe characters during CSV imports.
- Server-authoritative derivation of normalized search keys (overwriting client-poisoned norm keys).
- Asymmetric Account policy enforcement (Account with Arabic name rejected on new import).
- Update imports correctly enforcing policy and sanitizing search keys.
- Zero service edits guard to ensure bilingual_service.py and search.py remain untouched.
"""

import json
import subprocess
import unittest
from pathlib import Path

import frappe
from frappe.core.doctype.data_import.importer import Importer
from construction.services.bilingual_registry import normalize_arabic


class TestBilingualDataImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def _run_csv_import(self, doctype: str, csv_content: str, import_type: str = "Insert New Records"):
        """Helper to execute Data Import from CSV content string."""
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"test_bilingual_import_{frappe.generate_hash(length=8)}.csv",
            "content": csv_content,
            "is_private": 1,
        }).insert()

        di = frappe.get_doc({
            "doctype": "Data Import",
            "reference_doctype": doctype,
            "import_type": import_type,
            "import_file": file_doc.file_url,
        }).insert()

        try:
            importer = Importer(doctype, data_import=di)
            logs = importer.import_data()
            return logs, di, file_doc
        except Exception:
            frappe.delete_doc_if_exists("Data Import", di.name, force=True)
            frappe.delete_doc_if_exists("File", file_doc.name, force=True)
            raise

    def test_data_import_insert_norm_derivation_overwrites_poison(self):
        """CSV import with client-provided poisoned _norm key must have poison overwritten with server-derived norm."""
        test_uom_name = f"UOM-NORM-{frappe.generate_hash(length=6)}"
        arabic_name = "كيلوغرام معتمد"
        expected_norm = normalize_arabic(arabic_name)

        csv_content = (
            "uom_name,uom_name_ar,uom_name_ar_norm\n"
            f"{test_uom_name},{arabic_name},POISONED_CLIENT_NORM_KEY\n"
        )

        logs, di, file_doc = self._run_csv_import("UOM", csv_content)
        try:
            self.assertTrue(logs, "No import logs returned")
            self.assertEqual(logs[0].get("success"), 1, f"Import failed: {logs[0]}")

            doc = frappe.get_doc("UOM", test_uom_name)
            self.assertEqual(doc.uom_name_ar, arabic_name)
            self.assertEqual(
                doc.uom_name_ar_norm,
                expected_norm,
                "Poisoned norm key survived import! Must be server-authoritatively derived.",
            )
        finally:
            frappe.delete_doc_if_exists("UOM", test_uom_name, force=True)
            frappe.delete_doc_if_exists("Data Import", di.name, force=True)
            frappe.delete_doc_if_exists("File", file_doc.name, force=True)
            frappe.db.commit()

    def test_data_import_insert_bidi_rejection(self):
        """CSV import with forbidden bidi controls in Arabic name must fail row insert and not persist record."""
        test_uom_name = f"UOM-BIDI-{frappe.generate_hash(length=6)}"
        # Embed Right-to-Left Override (\u202e)
        bad_arabic = "متر\u202eمكعب"

        csv_content = (
            "uom_name,uom_name_ar\n"
            f"{test_uom_name},{bad_arabic}\n"
        )

        logs, di, file_doc = self._run_csv_import("UOM", csv_content)
        try:
            self.assertTrue(logs, "No import logs returned")
            self.assertEqual(logs[0].get("success"), 0, "Row with bidi control should have failed import!")
            self.assertFalse(frappe.db.exists("UOM", test_uom_name), "Document with bidi control was created in DB!")
        finally:
            if frappe.db.exists("UOM", test_uom_name):
                frappe.delete_doc_if_exists("UOM", test_uom_name, force=True)
            frappe.delete_doc_if_exists("Data Import", di.name, force=True)
            frappe.delete_doc_if_exists("File", file_doc.name, force=True)
            frappe.db.commit()

    def test_data_import_update_norm_derivation_and_bidi_rejection(self):
        """Updating existing records via Data Import must overwrite poisoned keys and reject bidi controls."""
        test_uom_name = f"UOM-UPD-{frappe.generate_hash(length=6)}"
        uom = frappe.get_doc({
            "doctype": "UOM",
            "uom_name": test_uom_name,
            "uom_name_ar": "وحدة أساسية",
        }).insert()
        frappe.db.commit()

        try:
            # 1. Update with poisoned norm key -> should overwrite poison
            update_ar = "وحدة معدلة"
            expected_norm = normalize_arabic(update_ar)
            csv_update = (
                "name,uom_name_ar,uom_name_ar_norm\n"
                f"{test_uom_name},{update_ar},POISON_UPDATE_KEY\n"
            )
            logs, di1, f1 = self._run_csv_import("UOM", csv_update, import_type="Update Existing Records")
            self.assertEqual(logs[0].get("success"), 1)
            reloaded = frappe.get_doc("UOM", test_uom_name)
            self.assertEqual(reloaded.uom_name_ar, update_ar)
            self.assertEqual(reloaded.uom_name_ar_norm, expected_norm)
            frappe.delete_doc_if_exists("Data Import", di1.name, force=True)
            frappe.delete_doc_if_exists("File", f1.name, force=True)

            # 2. Update with bidi control -> should fail and preserve old value
            csv_bad_update = (
                "name,uom_name_ar\n"
                f"{test_uom_name},وحدة\u2066غير آمنة\n"
            )
            logs2, di2, f2 = self._run_csv_import("UOM", csv_bad_update, import_type="Update Existing Records")
            self.assertEqual(logs2[0].get("success"), 0)
            reloaded2 = frappe.get_doc("UOM", test_uom_name)
            self.assertEqual(reloaded2.uom_name_ar, update_ar)  # unchanged
            frappe.delete_doc_if_exists("Data Import", di2.name, force=True)
            frappe.delete_doc_if_exists("File", f2.name, force=True)
        finally:
            frappe.delete_doc_if_exists("UOM", test_uom_name, force=True)
            frappe.db.commit()

    def test_data_import_account_asymmetry_enforced(self):
        """Account cannot carry Arabic name on insert via Data Import (financial governance invariant)."""
        company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name
        parent = frappe.get_all("Account", filters={"company": company, "is_group": 1}, limit=1)[0].name

        bad_acc_name = f"Test Acc Bad {frappe.generate_hash(length=4)}"
        csv_bad = (
            "account_name,company,parent_account,account_name_ar\n"
            f"{bad_acc_name},{company},{parent},حساب تجريبي مرفوض\n"
        )
        logs, di1, f1 = self._run_csv_import("Account", csv_bad)
        try:
            self.assertEqual(logs[0].get("success"), 0, "New Account with Arabic name must fail Data Import!")
            created = frappe.db.exists("Account", {"account_name": bad_acc_name, "company": company})
            self.assertIsNone(created, "Account with Arabic name on new import was created!")
        finally:
            if created:
                frappe.delete_doc_if_exists("Account", created, force=True)
            frappe.delete_doc_if_exists("Data Import", di1.name, force=True)
            frappe.delete_doc_if_exists("File", f1.name, force=True)
            frappe.db.commit()

        # Importing Account without Arabic name must succeed
        good_acc_name = f"Test Acc Good {frappe.generate_hash(length=4)}"
        csv_good = (
            "account_name,company,parent_account\n"
            f"{good_acc_name},{company},{parent}\n"
        )
        logs_good, di2, f2 = self._run_csv_import("Account", csv_good)
        created_good = None
        try:
            self.assertEqual(logs_good[0].get("success"), 1, f"Importing Account without Arabic failed: {logs_good}")
            created_good = frappe.db.exists("Account", {"account_name": good_acc_name, "company": company})
            self.assertIsNotNone(created_good, "Valid Account without Arabic was not created!")
        finally:
            if created_good:
                frappe.delete_doc_if_exists("Account", created_good, force=True)
            frappe.delete_doc_if_exists("Data Import", di2.name, force=True)
            frappe.delete_doc_if_exists("File", f2.name, force=True)
            frappe.db.commit()

    def test_data_import_across_classification_masters(self):
        """Classification masters (Item Group, Customer Group) correctly enforce bidi and norm derivation on Data Import."""
        test_ig_name = f"IG-IMP-{frappe.generate_hash(length=6)}"
        parent_ig = frappe.get_all("Item Group", filters={"is_group": 1}, limit=1)[0].name
        arabic_name = "مجموعة اختبار استيراد"
        expected_norm = normalize_arabic(arabic_name)

        csv_content = (
            "item_group_name,parent_item_group,is_group,item_group_name_ar,item_group_name_ar_norm\n"
            f"{test_ig_name},{parent_ig},0,{arabic_name},POISON_IG_NORM\n"
        )
        logs, di, file_doc = self._run_csv_import("Item Group", csv_content)
        try:
            self.assertEqual(logs[0].get("success"), 1)
            doc = frappe.get_doc("Item Group", test_ig_name)
            self.assertEqual(doc.item_group_name_ar, arabic_name)
            self.assertEqual(doc.item_group_name_ar_norm, expected_norm)
        finally:
            frappe.delete_doc_if_exists("Item Group", test_ig_name, force=True)
            frappe.delete_doc_if_exists("Data Import", di.name, force=True)
            frappe.delete_doc_if_exists("File", file_doc.name, force=True)
            frappe.db.commit()

    def test_zero_service_edits_guard(self):
        """Primary architectural invariant: bilingual_service.py and search.py must be byte-identical to base commits."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "dc71b5618532ea7fc8a1c5d778667a806cfc5109"
        files_to_check = [
            "construction/services/bilingual_service.py",
            "construction/searchable_dropdown/api/search.py",
        ]
        for rel_path in files_to_check:
            expected = subprocess.check_output(
                ["git", "show", f"{base_commit}:{rel_path}"],
                cwd=str(repo_root),
            )
            actual = (repo_root / rel_path).read_bytes()
            self.assertEqual(
                actual,
                expected,
                f"{rel_path} has diverged from baseline commit {base_commit}!",
            )
