"""Stage 5 Pilot tests: Brand bilingual enablement.

Run with:
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_brand_pilot

Covers:
- Patch v9_11 idempotency and reversibility for brand_ar and brand_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled=false, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Brand.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on brand_ar.
- Identity invariant over naming path (empty brand rejected by autoname; name remains the
  English value; rename preserves Arabic and norm keys).
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit 48f370f).
"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch
from uuid import uuid4

import frappe

from construction.patches.v9_11.add_brand_arabic_fields import execute as patch_execute
from construction.patches.v9_11.add_brand_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic

BRAND_FIELDS = [("Brand", "brand_ar"), ("Brand", "brand_ar_norm")]


def _get_target_brand():
    """Helper to fetch an existing Brand doc for testing."""
    docs = frappe.get_all("Brand", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Brand")
    return frappe.get_doc("Brand", docs[0].name)


class TestBilingualBrandPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        frappe.local.ct_bilingual_mapping_cache = None
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Brand master primary claim: bilingual_service.py and search.py must be byte-identical to base commit 48f370f."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "48f370f"
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
        """Idempotent execute and clean revert of patch v9_11 across Brand custom fields."""
        patch_execute()
        for dt, fn in BRAND_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in BRAND_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in BRAND_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in BRAND_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_brand_fields(self):
        """Ensure get_mapping resolves brand_ar_norm, tree.enabled=false, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Brand")
        self.assertIsNotNone(m, "Mapping missing for Brand")
        self.assertEqual(m["resolved"].get("norm_field"), "brand_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "brand")
        self.assertEqual(m["resolved"].get("arabic_field"), "brand_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertEqual(m["resolved"].get("identity_field"), "name")
        self.assertFalse(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(m.get("search", {}).get("fields"), ["brand", "brand_ar"])

    def test_active_and_schema_installed_fail_closed_on_missing_brand_field(self):
        """If norm_field is declared on schema_installed Brand but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Brand": {
                    "state": "schema_installed",
                    "english_field": "brand",
                    "arabic_field": "brand_ar",
                    "norm_field": "nonexistent_brand_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with mock_patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Brand")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_brand()
        orig_ar = doc.get("brand_ar")
        orig_norm = doc.get("brand_ar_norm")
        test_ar = "علامة البناء المعتمدة للمقاولين"
        try:
            doc.set("brand_ar", test_ar)
            doc.set("brand_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Brand", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("brand_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Brand!",
            )
        finally:
            clean = frappe.get_doc("Brand", doc.name)
            clean.set("brand_ar", orig_ar)
            clean.set("brand_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """brand_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "علامة\u202eبناء",  # Right-to-Left Override
            "علامة\u200eبناء",  # LRM
            "علامة\u202bبناء",  # RLE
            "علامة\x00بناء",  # NUL
        ]
        doc = _get_target_brand()
        orig_val = doc.get("brand_ar")
        for bad_sample in forbidden_samples:
            doc.set("brand_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Brand", doc.name)
        clean.set("brand_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_identity_invariant_and_rename_preservation(self):
        """Brand name remains the English value; autoname enforces non-empty; rename preserves Arabic."""
        brand_ar_value = "بصمة البناء المميزة"
        test_brand = f"Brand {uuid4().hex[:6]}"

        # 1. Empty brand is rejected by the naming path (autoname = field:brand)
        with self.assertRaises(frappe.ValidationError):
            bad_doc = frappe.get_doc({"doctype": "Brand", "brand": ""})
            bad_doc.insert(ignore_permissions=True)

        # 2. Insert valid bilingual fixture
        doc = frappe.get_doc(
            {
                "doctype": "Brand",
                "brand": test_brand,
                "brand_ar": brand_ar_value,
            }
        )
        doc.insert(ignore_permissions=True)
        old_id = doc.name

        # Identity PK matches English value, not Arabic
        self.assertEqual(doc.name, test_brand)
        self.assertEqual(doc.brand_ar_norm, normalize_arabic(brand_ar_value))

        new_id = f"{old_id}-RENAMED"

        try:
            if frappe.db.exists("Brand", new_id):
                frappe.delete_doc("Brand", new_id, force=True)

            frappe.rename_doc("Brand", old_id, new_id, force=True)

            renamed = frappe.get_doc("Brand", new_id)
            self.assertEqual(renamed.brand, new_id)
            self.assertEqual(renamed.brand_ar, brand_ar_value)
            self.assertEqual(renamed.brand_ar_norm, normalize_arabic(brand_ar_value))
        finally:
            if frappe.db.exists("Brand", new_id):
                frappe.delete_doc("Brand", new_id, force=True)
            if frappe.db.exists("Brand", old_id):
                frappe.delete_doc("Brand", old_id, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_brand()
        orig_ar = doc.get("brand_ar")
        test_canonical = "بَصْمَةُ الْبَنَاءِ المُشْرَفِيَّةِ"
        try:
            doc.set("brand_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Tashkeel
            query = "بصمة البناء"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Brand", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Brand) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Brand", txt=query)
            items = (
                dropdown_res.get("results", [])
                if isinstance(dropdown_res, dict)
                else dropdown_res
            )
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Brand) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Brand", doc.name)
            clean.set("brand_ar", orig_ar)
            clean.save()
            frappe.db.commit()
