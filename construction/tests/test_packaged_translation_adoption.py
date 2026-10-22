"""Native integration coverage for explicit matching-translation adoption."""

import csv
import unittest
from pathlib import Path

import frappe

from construction.translation_service import (
    adopt_matching_packaged_translation,
    get_runtime_rows,
    invalidate_translation_caches,
    upsert_runtime_translation,
)


class TestPackagedTranslationAdoption(unittest.TestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.addCleanup(self.cleanup)
        path = Path(frappe.get_app_path("construction", "data", "translations", "approved_ar_overrides.csv"))
        with path.open(encoding="utf-8") as handle:
            self.payload = next(
                row for row in csv.DictReader(handle) if row.get("release_status") == "Released"
            )
        self.source = self.payload["source_text"].strip()
        self.language = self.payload.get("language") or "ar"
        self.context = (self.payload.get("context") or "").strip()
        upsert_runtime_translation(
            self.source,
            self.payload["translated_text"],
            language=self.language,
            context=self.context,
            app=self.payload.get("ct_app") or None,
            origin="Site Override",
            reason="Isolated adoption integration fixture",
        )
        self.name = get_runtime_rows(self.language, self.source, self.context)[0].name

    def cleanup(self):
        frappe.db.rollback()
        invalidate_translation_caches(self.language)
        frappe.set_user(self.previous_user)

    def adopt(self, reference="F31 owner-authorized matching adoption"):
        return adopt_matching_packaged_translation(
            self.source,
            reference,
            language=self.language,
            context=self.context,
        )

    def test_preserves_identity_text_and_audits_operator(self):
        result = self.adopt()
        doc = frappe.get_doc("Translation", self.name)
        self.assertTrue(result["changed"])
        self.assertEqual(doc.name, self.name)
        self.assertEqual(doc.translated_text, self.payload["translated_text"])
        self.assertEqual(doc.ct_origin, "Packaged Release")
        self.assertEqual(doc.ct_release_version, self.payload["release_version"])
        self.assertEqual(doc.ct_released_by, "Administrator")
        self.assertTrue(
            frappe.db.exists("Comment", {"reference_doctype": "Translation", "reference_name": self.name})
        )

    def test_repeated_adoption_is_noop(self):
        self.adopt()
        before = frappe.db.count("Comment", {"reference_doctype": "Translation", "reference_name": self.name})
        self.assertFalse(self.adopt()["changed"])
        self.assertEqual(
            frappe.db.count("Comment", {"reference_doctype": "Translation", "reference_name": self.name}),
            before,
        )

    def test_conflicting_text_is_refused_without_adoption(self):
        upsert_runtime_translation(
            self.source,
            "F31 deliberate conflicting text",
            language=self.language,
            context=self.context,
            app=self.payload.get("ct_app") or None,
            origin="Site Override",
        )
        with self.assertRaises(frappe.ValidationError):
            self.adopt()
        doc = frappe.get_doc("Translation", self.name)
        self.assertEqual(doc.ct_origin, "Site Override")
        self.assertEqual(doc.translated_text, "F31 deliberate conflicting text")

    def test_missing_decision_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.adopt("")
        self.assertEqual(frappe.get_doc("Translation", self.name).ct_origin, "Site Override")

    def test_unreleased_key_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            adopt_matching_packaged_translation("F31 absent release key", "Owner decision")

    def test_ordinary_role_cannot_adopt(self):
        user = "f31-adoption-denied@qualification.invalid"
        if not frappe.db.exists("User", user):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": user,
                    "first_name": "F31 Denied",
                    "send_welcome_email": 0,
                    "roles": [{"role": "Project Manager"}],
                }
            ).insert()
        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.PermissionError):
                self.adopt()
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.get_doc("Translation", self.name).ct_origin, "Site Override")
