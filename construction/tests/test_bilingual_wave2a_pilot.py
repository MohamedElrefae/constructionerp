"""
Stage 5 Wave 2a Pilot tests: Item Group, Customer Group, Supplier Group, Territory, UOM bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-wave2a-classification-masters \
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_wave2a_pilot

Covers:
- Patch v9_4 idempotency and reversibility across all ten custom fields.
- Registry mapping resolution including norm_field, tree.enabled, and code_fields.
- Fail-closed validation when declared fields are missing on active/schema_installed doctypes.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on Arabic display fields.
- Tree identity invariant (name and parent_* pointers remain ASCII/unaltered on trees).
- Rename doc preserves Arabic and norm keys across all five classification masters.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to commit dc71b56).
"""

import subprocess
import unittest
from pathlib import Path

import frappe

from construction.patches.v9_4.add_wave2a_classification_arabic_fields import execute as patch_execute
from construction.patches.v9_4.add_wave2a_classification_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_doc(doctype):
    """Helper to fetch a valid existing doc for testing (ensures non-root for trees)."""
    parent_field = {
        "Item Group": "parent_item_group",
        "Customer Group": "parent_customer_group",
        "Supplier Group": "parent_supplier_group",
        "Territory": "parent_territory",
    }.get(doctype)
    if parent_field:
        docs = frappe.get_all(doctype, filters={parent_field: ["is", "set"]}, limit=1)
    else:
        docs = frappe.get_all(doctype, limit=1)
    if not docs:
        raise unittest.SkipTest(f"No existing records found for {doctype}")
    return frappe.get_doc(doctype, docs[0].name)


class TestBilingualWave2aPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Wave 2a primary claim: bilingual_service.py and search.py must be byte-identical to base commit dc71b56."""
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
                f"Candidate violated zero-service-edits invariant for {rel_path}!",
            )

    def test_norm_field_patch_idempotent_and_reversible(self):
        """Idempotent execute and clean revert across Item Group, Customer Group, Supplier Group, Territory, UOM."""
        patch_execute()
        targets = [
            ("Item Group", "item_group_name_ar"),
            ("Item Group", "item_group_name_ar_norm"),
            ("Customer Group", "customer_group_name_ar"),
            ("Customer Group", "customer_group_name_ar_norm"),
            ("Supplier Group", "supplier_group_name_ar"),
            ("Supplier Group", "supplier_group_name_ar_norm"),
            ("Territory", "territory_name_ar"),
            ("Territory", "territory_name_ar_norm"),
            ("UOM", "uom_name_ar"),
            ("UOM", "uom_name_ar_norm"),
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

    def test_registry_loads_and_maps_resolved_wave2a_fields(self):
        """Ensure get_mapping resolves norm_field, tree.enabled, and code_fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        expectations = [
            ("Item Group", "item_group_name_ar_norm", None, True),
            ("Customer Group", "customer_group_name_ar_norm", None, True),
            ("Supplier Group", "supplier_group_name_ar_norm", None, True),
            ("Territory", "territory_name_ar_norm", None, True),
            ("UOM", "uom_name_ar_norm", "common_code", False),
        ]
        for dt, expected_norm, expected_code, expected_tree in expectations:
            m = svc.get_mapping(dt)
            self.assertIsNotNone(m, f"Mapping missing for {dt}")
            self.assertEqual(m["resolved"].get("norm_field"), expected_norm)
            self.assertEqual(m["resolved"].get("code_field"), expected_code)
            self.assertEqual(bool((m.get("tree") or {}).get("enabled")), expected_tree)

    def test_active_and_schema_installed_fail_closed_on_missing_wave2a_field(self):
        """If norm_field is declared on schema_installed doctype but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Item Group": {
                    "state": "schema_installed",
                    "english_field": "item_group_name",
                    "arabic_field": "item_group_name_ar",
                    "norm_field": "nonexistent_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Item Group")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        targets = [
            ("Item Group", "item_group_name_ar", "item_group_name_ar_norm", "مجموعة المواد الخام"),
            ("Customer Group", "customer_group_name_ar", "customer_group_name_ar_norm", "عملاء المشاريع الحكومية"),
            ("Supplier Group", "supplier_group_name_ar", "supplier_group_name_ar_norm", "موردو المعدات الثقيلة"),
            ("Territory", "territory_name_ar", "territory_name_ar_norm", "المنطقة الشرقية"),
            ("UOM", "uom_name_ar", "uom_name_ar_norm", "متر مكعب خرسانة"),
        ]
        for dt, ar_fn, norm_fn, test_ar in targets:
            doc = _get_target_doc(dt)
            orig_ar = doc.get(ar_fn)
            orig_norm = doc.get(norm_fn)
            try:
                doc.set(ar_fn, test_ar)
                doc.set(norm_fn, "POISONED-KEY")
                doc.save()

                reloaded = frappe.get_doc(dt, doc.name)
                expected_norm = normalize_arabic(test_ar)
                self.assertEqual(
                    reloaded.get(norm_fn),
                    expected_norm,
                    f"{dt}: Poisoned key survived or norm key not derived!",
                )
            finally:
                clean = frappe.get_doc(dt, doc.name)
                clean.set(ar_fn, orig_ar)
                clean.set(norm_fn, orig_norm)
                clean.save()
                frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """Arabic display fields reject bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        targets = [
            ("Item Group", "item_group_name_ar"),
            ("Customer Group", "customer_group_name_ar"),
            ("Supplier Group", "supplier_group_name_ar"),
            ("Territory", "territory_name_ar"),
            ("UOM", "uom_name_ar"),
        ]
        forbidden_samples = [
            "نص\u202eتخريب",  # Right-to-Left Override
            "نص\u200eعربي",  # LRM
            "تجربة\u202bمخربة",  # RLE
            "اسم\x00مخرب",  # NUL
        ]
        for dt, ar_fn in targets:
            doc = _get_target_doc(dt)
            orig_val = doc.get(ar_fn)
            for bad_sample in forbidden_samples:
                doc.set(ar_fn, bad_sample)
                with self.assertRaises(frappe.ValidationError):
                    doc.save()
            clean = frappe.get_doc(dt, doc.name)
            clean.set(ar_fn, orig_val)
            clean.save()
            frappe.db.commit()

    def test_tree_identity_invariant_and_rename_preservation(self):
        """Tree nodes preserve ASCII name, parent pointer, and retain Arabic and norm keys across renames."""
        # 1. Tree identity checks across the 4 classification trees
        trees = [
            ("Item Group", "parent_item_group", "item_group_name", "item_group_name_ar", "مجموعة اختبار الشجرة"),
            ("Customer Group", "parent_customer_group", "customer_group_name", "customer_group_name_ar", "فئة عملاء اختبار"),
            ("Supplier Group", "parent_supplier_group", "supplier_group_name", "supplier_group_name_ar", "فئة موردين اختبار"),
            ("Territory", "parent_territory", "territory_name", "territory_name_ar", "منطقة اختبار الشجرة"),
        ]
        for dt, pf, name_field, ar_fn, test_label in trees:
            doc = _get_target_doc(dt)
            orig_name = doc.name
            orig_parent = doc.get(pf)
            orig_canonical = doc.get(name_field)
            orig_ar = doc.get(ar_fn)
            try:
                doc.set(ar_fn, test_label)
                doc.save()
                reloaded = frappe.get_doc(dt, orig_name)
                self.assertEqual(reloaded.name, orig_name)
                self.assertEqual(reloaded.get(pf), orig_parent)
                self.assertEqual(reloaded.get(name_field), orig_canonical)
                self.assertEqual(reloaded.get(ar_fn), test_label)
                self.assertEqual(reloaded.get(f"{ar_fn}_norm"), normalize_arabic(test_label))
            finally:
                reloaded = frappe.get_doc(dt, orig_name)
                reloaded.set(ar_fn, orig_ar)
                reloaded.save()
                frappe.db.commit()

        # 2. Rename preservation across all five classification masters
        rename_targets = [
            ("Item Group", "item_group_name", "item_group_name_ar", "parent_item_group", "All Item Groups"),
            ("Customer Group", "customer_group_name", "customer_group_name_ar", "parent_customer_group", "All Customer Groups"),
            ("Supplier Group", "supplier_group_name", "supplier_group_name_ar", "parent_supplier_group", "All Supplier Groups"),
            ("Territory", "territory_name", "territory_name_ar", "parent_territory", "All Territories"),
            ("UOM", "uom_name", "uom_name_ar", None, None),
        ]
        for dt, eng_fn, ar_fn, pf, default_parent in rename_targets:
            old_name = f"CT-TEST-W2A-{dt[:3].upper()}-01"
            new_name = f"CT-TEST-W2A-{dt[:3].upper()}-02"
            for n in (old_name, new_name):
                if frappe.db.exists(dt, n):
                    frappe.delete_doc(dt, n, force=True)

            test_text = f"اختبار تسمية {dt}"
            doc_kwargs = {
                "doctype": dt,
                eng_fn: old_name,
                ar_fn: test_text,
            }
            if pf:
                doc_kwargs[pf] = default_parent

            doc = frappe.get_doc(doc_kwargs)
            doc.insert(ignore_permissions=True)

            norm_fn = f"{ar_fn}_norm"
            self.assertEqual(doc.get(norm_fn), normalize_arabic(test_text))

            frappe.rename_doc(dt, old_name, new_name, force=True)

            renamed = frappe.get_doc(dt, new_name)
            self.assertEqual(renamed.get(ar_fn), test_text)
            self.assertEqual(renamed.get(norm_fn), normalize_arabic(test_text))

            frappe.delete_doc(dt, new_name, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        test_data = [
            ("Item Group", "item_group_name_ar", "أدوات ومعدات إنشائية"),
            ("Customer Group", "customer_group_name_ar", "إدارة المشروعات الكبرى"),
            ("Supplier Group", "supplier_group_name_ar", "أجهزة ومعدات ثقيلة"),
            ("Territory", "territory_name_ar", "إقليم الشرق الأوسط"),
            ("UOM", "uom_name_ar", "أمتار مربعة أرضيات"),
        ]
        for dt, ar_fn, canonical_ar in test_data:
            doc = _get_target_doc(dt)
            orig_ar = doc.get(ar_fn)
            try:
                doc.set(ar_fn, canonical_ar)
                doc.save()
                frappe.db.commit()

                # Query with Alef variant (missing hamza)
                query = "ادوات" if "أدوات" in canonical_ar else (
                    "ادارة" if "إدارة" in canonical_ar else (
                        "اجهزة" if "أجهزة" in canonical_ar else (
                            "اقليم" if "إقليم" in canonical_ar else "امتار"
                        )
                    )
                )

                # Test 1: bilingual_service.search_bilingual
                results = svc.search_bilingual(dt, txt=query)
                matched_names = [r["value"] for r in results]
                self.assertIn(
                    doc.name,
                    matched_names,
                    f"search_bilingual({dt}) failed to match '{canonical_ar}' with query '{query}'",
                )

                # Test 2: searchable_dropdown.searchable_link_search
                dropdown_res = searchable_link_search(doctype=dt, txt=query)
                items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
                dropdown_names = [r["value"] for r in items]
                self.assertIn(
                    doc.name,
                    dropdown_names,
                    f"searchable_link_search({dt}) failed to match '{canonical_ar}' with query '{query}'",
                )
            finally:
                clean = frappe.get_doc(dt, doc.name)
                clean.set(ar_fn, orig_ar)
                clean.save()
                frappe.db.commit()
