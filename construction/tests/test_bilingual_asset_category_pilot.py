"""Stage 5 Wave 2 Pilot tests: Asset Category bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-asset-category-master \\
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_asset_category_pilot

Covers:
- Patch v9_9 idempotency and reversibility for asset_category_name_ar and asset_category_name_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled=false, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Asset Category.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on asset_category_name_ar.
- Identity invariant (name remains English value/ASCII; Arabic occupies only _ar and _norm).
- Rename doc preserves Arabic and norm keys.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit 04dfe35).
"""

import subprocess
import unittest
from pathlib import Path
from uuid import uuid4

import frappe

from construction.patches.v9_9.add_asset_category_arabic_fields import execute as patch_execute
from construction.patches.v9_9.add_asset_category_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_asset_category():
    """Helper to fetch an existing Asset Category doc for testing."""
    docs = frappe.get_all("Asset Category", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Asset Category")
    return frappe.get_doc("Asset Category", docs[0].name)


class TestBilingualAssetCategoryPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Asset Category master primary claim: bilingual_service.py and search.py must be byte-identical to base commit 04dfe35."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "04dfe35"
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
        """Idempotent execute and clean revert of patch v9_9 across Asset Category custom fields."""
        patch_execute()
        targets = [
            ("Asset Category", "asset_category_name_ar"),
            ("Asset Category", "asset_category_name_ar_norm"),
        ]
        for dt, fn in targets:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in targets:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in targets:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in targets:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_asset_category_fields(self):
        """Ensure get_mapping resolves asset_category_name_ar_norm, tree.enabled=false, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Asset Category")
        self.assertIsNotNone(m, "Mapping missing for Asset Category")
        self.assertEqual(m["resolved"].get("norm_field"), "asset_category_name_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "asset_category_name")
        self.assertEqual(m["resolved"].get("arabic_field"), "asset_category_name_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertFalse(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(m.get("search", {}).get("fields"), ["asset_category_name", "asset_category_name_ar"])

    def test_active_and_schema_installed_fail_closed_on_missing_asset_category_field(self):
        """If norm_field is declared on schema_installed Asset Category but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Asset Category": {
                    "state": "schema_installed",
                    "english_field": "asset_category_name",
                    "arabic_field": "asset_category_name_ar",
                    "norm_field": "nonexistent_ac_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Asset Category")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_asset_category()
        orig_ar = doc.get("asset_category_name_ar")
        orig_norm = doc.get("asset_category_name_ar_norm")
        test_ar = "فئة المعدات الثقيلة والآلات"
        try:
            doc.set("asset_category_name_ar", test_ar)
            doc.set("asset_category_name_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Asset Category", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("asset_category_name_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Asset Category!",
            )
        finally:
            clean = frappe.get_doc("Asset Category", doc.name)
            clean.set("asset_category_name_ar", orig_ar)
            clean.set("asset_category_name_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """asset_category_name_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "فئة\u202eالأصول",  # Right-to-Left Override
            "فئة\u200eالأصول",  # LRM
            "فئة\u202bالأصول",  # RLE
            "فئة\x00الأصول",  # NUL
        ]
        doc = _get_target_asset_category()
        orig_val = doc.get("asset_category_name_ar")
        for bad_sample in forbidden_samples:
            doc.set("asset_category_name_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Asset Category", doc.name)
        clean.set("asset_category_name_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_identity_invariant_and_rename_preservation(self):
        """Asset Category name remains English value; rename preserves Arabic and norm keys."""
        existing = frappe.get_doc("Asset Category", "Computers")
        cat_ar = "فئة المركبات والشاحنات"
        test_cat_name = f"Vehicles {uuid4().hex[:6]}"

        cat = frappe.get_doc({
            "doctype": "Asset Category",
            "asset_category_name": test_cat_name,
            "asset_category_name_ar": cat_ar,
            "accounts": [
                {
                    "company_name": existing.accounts[0].company_name,
                    "fixed_asset_account": existing.accounts[0].fixed_asset_account,
                    "accumulated_depreciation_account": existing.accounts[0].accumulated_depreciation_account,
                    "depreciation_expense_account": existing.accounts[0].depreciation_expense_account,
                }
            ],
        })
        cat.insert(ignore_permissions=True)
        old_id = cat.name

        # Verify name PK matches English value, not Arabic
        self.assertEqual(cat.name, test_cat_name)
        self.assertEqual(cat.asset_category_name_ar_norm, normalize_arabic(cat_ar))

        new_id = f"{old_id}-RENAMED"

        try:
            if frappe.db.exists("Asset Category", new_id):
                frappe.delete_doc("Asset Category", new_id, force=True)

            frappe.rename_doc("Asset Category", old_id, new_id, force=True)

            renamed = frappe.get_doc("Asset Category", new_id)
            self.assertEqual(renamed.asset_category_name, new_id)
            self.assertEqual(renamed.asset_category_name_ar, cat_ar)
            self.assertEqual(renamed.asset_category_name_ar_norm, normalize_arabic(cat_ar))
        finally:
            if frappe.db.exists("Asset Category", new_id):
                frappe.delete_doc("Asset Category", new_id, force=True)
            if frappe.db.exists("Asset Category", old_id):
                frappe.delete_doc("Asset Category", old_id, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_asset_category()
        orig_ar = doc.get("asset_category_name_ar")
        test_canonical = "فِئَةُ الأَجْهِزَةِ الإِلِكْتُرُونِيَّةِ"
        try:
            doc.set("asset_category_name_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Tashkeel
            query = "فئة الاجهزة"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Asset Category", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Asset Category) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Asset Category", txt=query)
            items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Asset Category) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Asset Category", doc.name)
            clean.set("asset_category_name_ar", orig_ar)
            clean.save()
            frappe.db.commit()
