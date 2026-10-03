"""Stage 5 Pilot tests: Terms and Conditions bilingual enablement.

Run with:
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_terms_conditions_pilot

Covers:
- Patch v9_12 idempotency and reversibility for title_ar and title_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled=false, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Terms and Conditions.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on title_ar.
- Identity invariant over naming path (empty title rejected by autoname; name remains the
  English value; rename preserves Arabic and norm keys).
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit 0f3bd24).
"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch
from uuid import uuid4

import frappe

from construction.patches.v9_12.add_terms_and_conditions_arabic_fields import execute as patch_execute
from construction.patches.v9_12.add_terms_and_conditions_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic

TERMS_FIELDS = [("Terms and Conditions", "title_ar"), ("Terms and Conditions", "title_ar_norm")]


def _get_target_terms():
    """Helper to fetch an existing Terms and Conditions doc for testing."""
    docs = frappe.get_all("Terms and Conditions", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Terms and Conditions")
    return frappe.get_doc("Terms and Conditions", docs[0].name)


class TestBilingualTermsConditionsPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        frappe.local.ct_bilingual_mapping_cache = None
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Terms and Conditions master primary claim: bilingual_service.py and search.py must be byte-identical to base commit 0f3bd24."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "0f3bd24"
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
                f"Candidate violated zero-service-edits invariant for {rel_path}!",
            )

    def test_norm_field_patch_idempotent_and_reversible(self):
        """Idempotent execute and clean revert of patch v9_12 across Terms and Conditions custom fields."""
        patch_execute()
        for dt, fn in TERMS_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in TERMS_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in TERMS_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in TERMS_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_terms_conditions_fields(self):
        """Ensure get_mapping resolves title_ar_norm, tree.enabled=false, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Terms and Conditions")
        self.assertIsNotNone(m, "Mapping missing for Terms and Conditions")
        self.assertEqual(m["resolved"].get("norm_field"), "title_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "title")
        self.assertEqual(m["resolved"].get("arabic_field"), "title_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertEqual(m["resolved"].get("identity_field"), "name")
        self.assertFalse(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(m.get("search", {}).get("fields"), ["title", "title_ar"])

    def test_active_and_schema_installed_fail_closed_on_missing_terms_conditions_field(self):
        """If norm_field is declared on schema_installed Terms and Conditions but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Terms and Conditions": {
                    "state": "schema_installed",
                    "english_field": "title",
                    "arabic_field": "title_ar",
                    "norm_field": "nonexistent_terms_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with mock_patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Terms and Conditions")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_terms()
        orig_ar = doc.get("title_ar")
        orig_norm = doc.get("title_ar_norm")
        test_ar = "شروط وأحكام عقود المقاولات المعتمدة"
        try:
            doc.set("title_ar", test_ar)
            doc.set("title_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Terms and Conditions", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("title_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Terms and Conditions!",
            )
        finally:
            clean = frappe.get_doc("Terms and Conditions", doc.name)
            clean.set("title_ar", orig_ar)
            clean.set("title_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """title_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "شروط\u202eعقد",  # Right-to-Left Override
            "شروط\u200eعقد",  # LRM
            "شروط\u202bعقد",  # RLE
            "شروط\x00عقد",  # NUL
        ]
        doc = _get_target_terms()
        orig_val = doc.get("title_ar")
        for bad_sample in forbidden_samples:
            doc.set("title_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Terms and Conditions", doc.name)
        clean.set("title_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_identity_invariant_and_rename_preservation(self):
        """Terms and Conditions name remains the English value; autoname enforces non-empty; rename preserves Arabic."""
        title_ar_value = "الشروط والأحكام القياسية للبناء"
        test_title = f"Terms {uuid4().hex[:6]}"

        # 1. Empty title is rejected by the naming path (autoname = field:title)
        with self.assertRaises(frappe.ValidationError):
            bad_doc = frappe.get_doc({"doctype": "Terms and Conditions", "title": ""})
            bad_doc.insert(ignore_permissions=True)

        # 2. Insert valid bilingual fixture
        doc = frappe.get_doc(
            {
                "doctype": "Terms and Conditions",
                "title": test_title,
                "title_ar": title_ar_value,
            }
        )
        doc.insert(ignore_permissions=True)
        old_id = doc.name

        # Identity PK matches English value, not Arabic
        self.assertEqual(doc.name, test_title)
        self.assertEqual(doc.title_ar_norm, normalize_arabic(title_ar_value))

        new_id = f"{old_id}-RENAMED"

        try:
            if frappe.db.exists("Terms and Conditions", new_id):
                frappe.delete_doc("Terms and Conditions", new_id, force=True)

            frappe.rename_doc("Terms and Conditions", old_id, new_id, force=True)

            renamed = frappe.get_doc("Terms and Conditions", new_id)
            self.assertEqual(renamed.title, new_id)
            self.assertEqual(renamed.title_ar, title_ar_value)
            self.assertEqual(renamed.title_ar_norm, normalize_arabic(title_ar_value))
        finally:
            if frappe.db.exists("Terms and Conditions", new_id):
                frappe.delete_doc("Terms and Conditions", new_id, force=True)
            if frappe.db.exists("Terms and Conditions", old_id):
                frappe.delete_doc("Terms and Conditions", old_id, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_terms()
        orig_ar = doc.get("title_ar")
        test_canonical = "شُرُوطُ وَأَحْكَامُ الْعُقُودِ الإِنْشَائِيَّةِ"
        try:
            doc.set("title_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Tashkeel
            query = "شروط واحكام العقود"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Terms and Conditions", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Terms and Conditions) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Terms and Conditions", txt=query)
            items = (
                dropdown_res.get("results", [])
                if isinstance(dropdown_res, dict)
                else dropdown_res
            )
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Terms and Conditions) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Terms and Conditions", doc.name)
            clean.set("title_ar", orig_ar)
            clean.save()
            frappe.db.commit()


if __name__ == "__main__":
    unittest.main()
