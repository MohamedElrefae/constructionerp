from uuid import uuid4

import frappe
import frappe.translate as frappe_translate
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime


class TestTranslationStabilizationGates(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.src = f"Gate Test {uuid4().hex}"
        frappe_translate.clear_cache()

    def tearDown(self):
        frappe.db.delete("Translation", {"source_text": ["like", "Gate Test%"], "language": "ar"})
        frappe.db.delete("Translation", {"source_text": ["like", "Unique Test%"], "language": "ar"})
        frappe.db.delete("Translation", {"source_text": ["like", "Quorum%"], "language": "ar"})
        frappe.db.delete("Translation", {"source_text": ["like", "MetaRepair%"], "language": "ar"})
        frappe.db.delete("Translation", {"source_text": ["like", "CatalogPO%"], "language": "ar"})
        frappe.db.delete("Translation", {"source_text": ["like", "DriftOrphan%"], "language": "ar"})
        frappe.db.delete("Translation", {"source_text": "HookFail", "language": "ar"})
        frappe.db.commit()
        frappe_translate.clear_cache()
        super().tearDown()

    def _insert_catalog(self, source, app="construction", po_val="", translated=""):
        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "ar",
                "source_text": source,
                "translated_text": translated or po_val,
                "context": "",
                "ct_is_catalog_entry": 1,
                "ct_app": app,
                "ct_po_translation": po_val,
                "ct_review_status": "Approved" if po_val else "Pending",
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def _insert_runtime(self, source, translated, app=None, origin="Site Override", version=None):
        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "ar",
                "source_text": source,
                "translated_text": translated,
                "context": "",
                "ct_is_catalog_entry": 0,
                "ct_app": app,
                "ct_origin": origin,
                "ct_release_version": version,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def test_b01_unique_digest_enforced(self):
        idx = frappe.db.sql("SHOW INDEX FROM `tabTranslation` WHERE Column_name='ct_key_digest' AND Non_unique=0 AND Key_name='ct_translation_key_digest'", as_dict=True)
        self.assertTrue(idx, "UNIQUE ct_translation_key_digest must exist")
        src = f"Unique Test {uuid4().hex}"
        self._insert_runtime(src, "قيمة أولى")
        with self.assertRaises(Exception) as cm:
            doc2 = frappe.get_doc(
                {
                    "doctype": "Translation",
                    "language": "ar",
                    "source_text": src,
                    "translated_text": "قيمة ثانية",
                    "context": "",
                    "ct_is_catalog_entry": 0,
                    "ct_app": None,
                }
            )
            doc2.insert(ignore_permissions=True)
        self.assertIn("Duplicate", str(cm.exception) or "UNIQUE" in str(cm.exception) or "1062" in str(cm.exception))

    def test_b04_quorum_enforced(self):
        from construction.translation_service import import_released_overrides
        import csv, tempfile, pathlib

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["language","source_text","context","ct_app","translated_text","domain","release_status","release_version","a1_reviewer","a1_approved_at","a2_reviewer","a2_approved_at","a3_reviewer","a3_approved_at","references","notes"])
            w.writeheader()
            w.writerow({
                "language":"ar","source_text":f"Quorum {uuid4().hex}","context":"","ct_app":"construction","translated_text":"قيمة","domain":"test","release_status":"Released","release_version":"1.0",
                "a1_reviewer":"A1","a1_approved_at":"2026-09-02","a2_reviewer":"A2","a2_approved_at":"2026-09-02","a3_reviewer":"A3","a3_approved_at":"2026-09-02","references":"","notes":""
            })
            path = f.name
        frappe.set_user("Administrator")
        with self.assertRaises(Exception) as cm:
            import_released_overrides(path=path, dry_run=False)
        self.assertIn("Placeholder", str(cm.exception))
        pathlib.Path(path).unlink(missing_ok=True)

    def test_b03_metadata_repair_even_when_value_equal(self):
        from construction.translation_service import import_released_overrides
        import csv, tempfile, pathlib
        src = f"MetaRepair {uuid4().hex}"
        runtime = self._insert_runtime(src, "قيمة", app=None, origin="Packaged Release", version="1.0")
        self.assertIsNone(runtime.get("ct_app") or None)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["language","source_text","context","ct_app","translated_text","domain","release_status","release_version","a1_reviewer","a1_approved_at","a2_reviewer","a2_approved_at","a3_reviewer","a3_approved_at","references","notes"])
            w.writeheader()
            w.writerow({
                "language":"ar","source_text":src,"context":"","ct_app":"construction","translated_text":"قيمة","domain":"test","release_status":"Released","release_version":"1.0",
                "a1_reviewer":"Mona Khalil","a1_approved_at":"2026-09-02 10:00:00","a2_reviewer":"Hesham Farouk","a2_approved_at":"2026-09-02 10:30:00","a3_reviewer":"Nadia Mostafa","a3_approved_at":"2026-09-02 11:00:00","references":"test","notes":""
            })
            path = f.name
        frappe.set_user("Administrator")
        res = import_released_overrides(path=path, dry_run=False)
        self.assertEqual(res["updated"], 1)
        self.assertEqual(frappe.db.get_value("Translation", runtime.name, "ct_app"), "construction")
        pathlib.Path(path).unlink(missing_ok=True)

    def test_b16_semantic_version_ordering(self):
        from construction.translation_service import _is_newer_version
        self.assertTrue(_is_newer_version("10.0", "2.0"))
        self.assertFalse(_is_newer_version("2.0", "10.0"))
        self.assertTrue(_is_newer_version("1.0.1", "1.0"))
        self.assertFalse(_is_newer_version("1.0", "1.0"))
        self.assertTrue(_is_newer_version("2.0", "1.9.9"))

    def test_b15_catalog_preserves_po_while_updating_display(self):
        src = f"CatalogPO {uuid4().hex}"
        catalog = self._insert_catalog(src, app="construction", po_val="upstream po", translated="upstream po")
        catalog.reload()
        self.assertEqual(catalog.ct_po_translation, "upstream po")
        from construction.translation_service import import_released_overrides
        import csv, tempfile, pathlib
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["language","source_text","context","ct_app","translated_text","domain","release_status","release_version","a1_reviewer","a1_approved_at","a2_reviewer","a2_approved_at","a3_reviewer","a3_approved_at","references","notes"])
            w.writeheader()
            w.writerow({
                "language":"ar","source_text":src,"context":"","ct_app":"construction","translated_text":"قيمة معتمدة","domain":"test","release_status":"Released","release_version":"1.0",
                "a1_reviewer":"Mona Khalil","a1_approved_at":"2026-09-02 10:00:00","a2_reviewer":"Hesham Farouk","a2_approved_at":"2026-09-02 10:30:00","a3_reviewer":"Nadia Mostafa","a3_approved_at":"2026-09-02 11:00:00","references":"test","notes":""
            })
            path = f.name
        frappe.set_user("Administrator")
        import_released_overrides(path=path, dry_run=False)
        catalog.reload()
        self.assertEqual(catalog.ct_po_translation, "upstream po")
        self.assertEqual(catalog.translated_text, "قيمة معتمدة")
        self.assertEqual(catalog.ct_review_status, "Released")
        pathlib.Path(path).unlink(missing_ok=True)

    def test_b06_drift_detection(self):
        from construction.translation_service import get_translation_health
        h = get_translation_health()
        self.assertFalse(h["has_drift"])
        self.assertIsNotNone(h["last_drift_checked_at"])
        src = f"DriftOrphan {uuid4().hex}"
        self._insert_runtime(src, "قيمة orphan", origin="Packaged Release", version="1.0")
        h2 = get_translation_health()
        self.assertTrue(h2["has_drift"])
        self.assertIn("orphan", " ".join(h2["drift_details"]).lower())
        frappe.db.delete("Translation", {"source_text": src, "language": "ar"})
        frappe.db.commit()

    def test_b17_hook_fail_closed(self):
        from construction.translation_service import import_released_overrides_hook
        import csv, tempfile, pathlib
        orig_path = frappe.get_app_path("construction", "data", "translations", "approved_ar_overrides.csv")
        backup = pathlib.Path(orig_path).read_text(encoding="utf-8")
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["language","source_text","context","ct_app","translated_text","domain","release_status","release_version","a1_reviewer","a1_approved_at","a2_reviewer","a2_approved_at","a3_reviewer","a3_approved_at","references","notes"])
                w.writeheader()
                w.writerow({
                    "language":"ar","source_text":"HookFail","context":"","ct_app":"construction","translated_text":"قيمة","domain":"test","release_status":"Released","release_version":"1.0",
                    "a1_reviewer":"A1","a1_approved_at":"2026-09-02","a2_reviewer":"A2","a2_approved_at":"2026-09-02","a3_reviewer":"A3","a3_approved_at":"2026-09-02","references":"","notes":""
                })
                tmp = f.name
            pathlib.Path(orig_path).write_text(pathlib.Path(tmp).read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(Exception):
                import_released_overrides_hook()
            pathlib.Path(tmp).unlink(missing_ok=True)
        finally:
            pathlib.Path(orig_path).write_text(backup, encoding="utf-8")

