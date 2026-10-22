from uuid import uuid4

import frappe
import frappe.translate as frappe_translate
from frappe.tests.utils import FrappeTestCase

from construction.api.translation_tools import (
    _update_catalog_review_value,
    upsert_runtime_translation,
)


class TestTranslationCatalogRuntime(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.source_text = f"Translation Catalog Test {uuid4().hex}"
        frappe_translate.clear_cache()

    def tearDown(self):
        frappe_translate.clear_cache()
        super().tearDown()

    def _insert_translation(self, value, *, is_catalog, po_translation=None):
        doc = frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "ar",
                "source_text": self.source_text,
                "translated_text": value,
                "context": "",
                "ct_is_catalog_entry": is_catalog,
                "ct_app": "construction" if is_catalog else None,
                "ct_po_translation": po_translation,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def test_runtime_loader_skips_catalog_and_resolves_duplicates_deterministically(self):
        self._insert_translation("قيمة الكتالوج", is_catalog=1, po_translation="قيمة الكتالوج")
        first = self._insert_translation("قيمة قديمة", is_catalog=0)
        if frappe.db.has_column("Translation", "ct_key_digest"):
            from construction.translation_service import upsert_runtime_translation

            upsert_runtime_translation(self.source_text, "قيمة أحدث", language="ar", ignore_permissions=True)
            runtime_rows = frappe.get_all(
                "Translation",
                filters={"language": "ar", "source_text": self.source_text, "ct_is_catalog_entry": 0},
                fields=["name", "translated_text"],
            )
            self.assertEqual(len(runtime_rows), 1)
            self.assertEqual(runtime_rows[0].translated_text, "قيمة أحدث")
            frappe_translate.clear_cache()
            self.assertEqual(
                frappe_translate.get_user_translations("ar").get(self.source_text),
                "قيمة أحدث",
            )
        else:
            newest = self._insert_translation("قيمة أحدث", is_catalog=0)
            frappe.db.set_value(
                "Translation",
                newest.name,
                "modified",
                "2099-01-01 00:00:00",
                update_modified=False,
            )
            frappe_translate.clear_cache()
            self.assertEqual(
                frappe_translate.get_user_translations("ar").get(self.source_text),
                "قيمة أحدث",
            )

    def test_catalog_edit_upserts_one_runtime_row_and_preserves_catalog(self):
        catalog = self._insert_translation(
            "الترجمة الأساسية",
            is_catalog=1,
            po_translation="الترجمة الأساسية",
        )

        catalog.translated_text = "الترجمة المعتمدة"
        catalog.save(ignore_permissions=True)
        catalog.reload()

        self.assertEqual(catalog.ct_is_catalog_entry, 1)
        if frappe.db.has_column("Translation", "ct_proposed_translation"):
            self.assertEqual(catalog.ct_proposed_translation, "الترجمة المعتمدة")
            self.assertEqual(catalog.ct_review_status, "Pending")
            runtime_rows = frappe.get_all(
                "Translation",
                filters={
                    "language": "ar",
                    "source_text": self.source_text,
                    "ct_is_catalog_entry": 0,
                },
                fields=["name", "translated_text"],
            )
            self.assertEqual(len(runtime_rows), 0)
            catalog.translated_text = "الترجمة المعتمدة الثانية"
            catalog.save(ignore_permissions=True)
            catalog.reload()
            self.assertEqual(catalog.ct_proposed_translation, "الترجمة المعتمدة الثانية")
            runtime_rows = frappe.get_all(
                "Translation",
                filters={
                    "language": "ar",
                    "source_text": self.source_text,
                    "ct_is_catalog_entry": 0,
                },
                fields=["translated_text"],
            )
            self.assertEqual(len(runtime_rows), 0)
            frappe_translate.clear_cache()
            self.assertIsNone(frappe_translate.get_user_translations("ar").get(self.source_text))
        else:
            runtime_rows = frappe.get_all(
                "Translation",
                filters={
                    "language": "ar",
                    "source_text": self.source_text,
                    "ct_is_catalog_entry": 0,
                },
                fields=["name", "translated_text"],
            )
            self.assertEqual(len(runtime_rows), 1)
            self.assertEqual(runtime_rows[0].translated_text, "الترجمة المعتمدة")
            catalog.translated_text = "الترجمة المعتمدة الثانية"
            catalog.save(ignore_permissions=True)
            runtime_rows = frappe.get_all(
                "Translation",
                filters={
                    "language": "ar",
                    "source_text": self.source_text,
                    "ct_is_catalog_entry": 0,
                },
                fields=["translated_text"],
            )
            self.assertEqual(len(runtime_rows), 1)
            self.assertEqual(runtime_rows[0].translated_text, "الترجمة المعتمدة الثانية")
            frappe_translate.clear_cache()
            self.assertEqual(
                frappe_translate.get_user_translations("ar").get(self.source_text),
                "الترجمة المعتمدة الثانية",
            )

    def test_approved_review_updates_list_value_but_preserves_po_baseline(self):
        catalog = self._insert_translation(
            "ترجمة حرفية غير مناسبة",
            is_catalog=1,
            po_translation="ترجمة حرفية غير مناسبة",
        )

        upsert_runtime_translation(
            self.source_text,
            "ترجمة مهنية معتمدة",
            language="ar",
            app="construction",
            ignore_permissions=True,
        )
        _update_catalog_review_value(
            "ar",
            self.source_text,
            "ترجمة مهنية معتمدة",
            app="construction",
        )

        catalog.reload()
        self.assertEqual(catalog.translated_text, "ترجمة مهنية معتمدة")
        self.assertEqual(catalog.ct_po_translation, "ترجمة حرفية غير مناسبة")
        self.assertEqual(catalog.ct_review_status, "Approved")
