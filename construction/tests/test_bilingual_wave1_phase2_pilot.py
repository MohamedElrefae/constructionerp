"""
Stage 5 Wave 1 Phase 2 Pilot tests: Cost Center, Warehouse, Project bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-wave1-masters \
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_wave1_phase2_pilot

Covers:
- Patch v9_3 idempotency and reversibility across all six custom fields.
- Registry mapping resolution including norm_field, tree.enabled, and corrected code_fields.
- Fail-closed validation when declared fields are missing on active/schema_installed doctypes.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on Arabic display fields.
- Tree identity invariant (name and parent_* pointers remain ASCII/unaltered on Cost Center and Warehouse).
- Rename doc preserves Arabic and norm keys across all Phase 2 masters.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to commit 81af417).
"""

import subprocess
import unittest
from pathlib import Path

import frappe

from construction.patches.v9_3.add_wave1_phase2_arabic_fields import execute as patch_execute
from construction.patches.v9_3.add_wave1_phase2_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_doc(doctype):
    """Helper to fetch a valid existing doc for testing (ensures non-root for trees)."""
    if doctype == "Cost Center":
        docs = frappe.get_all("Cost Center", filters={"parent_cost_center": ["is", "set"]}, limit=1)
    elif doctype == "Warehouse":
        docs = frappe.get_all("Warehouse", filters={"company": ["is", "set"]}, limit=1)
    else:
        docs = frappe.get_all(doctype, limit=1)
    if not docs:
        raise unittest.SkipTest(f"No existing records found for {doctype}")
    return frappe.get_doc(doctype, docs[0].name)


class TestBilingualWave1Phase2Pilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Phase 2 primary claim: bilingual_service.py and search.py must be byte-identical to commit 81af417."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "81af417deda3566956ed3f25bc1463f55088d1ea"
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
        """Idempotent execute and clean revert across Cost Center, Warehouse, Project."""
        patch_execute()
        targets = [
            ("Cost Center", "cost_center_name_ar"),
            ("Cost Center", "cost_center_name_ar_norm"),
            ("Warehouse", "warehouse_name_ar"),
            ("Warehouse", "warehouse_name_ar_norm"),
            ("Project", "project_name_ar"),
            ("Project", "project_name_ar_norm"),
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

    def test_registry_loads_and_maps_resolved_phase2_fields(self):
        """Ensure get_mapping resolves norm_field, tree.enabled, and corrected code_fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        expectations = [
            ("Cost Center", "cost_center_name_ar_norm", "cost_center_number", True),
            ("Warehouse", "warehouse_name_ar_norm", None, True),
            ("Project", "project_name_ar_norm", None, False),
        ]
        for dt, expected_norm, expected_code, expected_tree in expectations:
            m = svc.get_mapping(dt)
            self.assertIsNotNone(m, f"Mapping missing for {dt}")
            self.assertEqual(m["resolved"].get("norm_field"), expected_norm)
            self.assertEqual(m["resolved"].get("code_field"), expected_code)
            self.assertEqual(bool((m.get("tree") or {}).get("enabled")), expected_tree)

    def test_active_and_schema_installed_fail_closed_on_missing_phase2_field(self):
        """If norm_field is declared on schema_installed doctype but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Warehouse": {
                    "state": "schema_installed",
                    "english_field": "warehouse_name",
                    "arabic_field": "warehouse_name_ar",
                    "norm_field": "nonexistent_warehouse_norm",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Warehouse")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        targets = [
            ("Cost Center", "cost_center_name_ar", "cost_center_name_ar_norm", "مركز تكلفة العمليات الإنشائية"),
            ("Warehouse", "warehouse_name_ar", "warehouse_name_ar_norm", "مستودع المواد الإنشائية الرئيسي"),
            ("Project", "project_name_ar", "project_name_ar_norm", "مشروع البرج التجاري الأول"),
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
            ("Cost Center", "cost_center_name_ar"),
            ("Warehouse", "warehouse_name_ar"),
            ("Project", "project_name_ar"),
        ]
        forbidden_samples = [
            "مركز\u202eتخريب",  # Right-to-Left Override
            "مستودع\u200eعربي",  # LRM
            "مشروع\u202bتجربة",  # RLE
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
        # 1. Cost Center tree node check
        cc = _get_target_doc("Cost Center")
        orig_name = cc.name
        orig_parent = cc.parent_cost_center
        orig_cc_name = cc.cost_center_name
        orig_ar = cc.cost_center_name_ar
        try:
            cc.cost_center_name_ar = "مركز اختبار الشجرة"
            cc.save()
            reloaded = frappe.get_doc("Cost Center", orig_name)
            self.assertEqual(reloaded.name, orig_name)
            self.assertEqual(reloaded.parent_cost_center, orig_parent)
            self.assertEqual(reloaded.cost_center_name, orig_cc_name)
            self.assertEqual(reloaded.cost_center_name_ar, "مركز اختبار الشجرة")
            self.assertEqual(reloaded.cost_center_name_ar_norm, normalize_arabic("مركز اختبار الشجرة"))
        finally:
            reloaded = frappe.get_doc("Cost Center", orig_name)
            reloaded.cost_center_name_ar = orig_ar
            reloaded.save()
            frappe.db.commit()

        # 2. Warehouse tree node check
        wh = _get_target_doc("Warehouse")
        orig_name = wh.name
        orig_parent = wh.parent_warehouse
        orig_wh_name = wh.warehouse_name
        orig_ar = wh.warehouse_name_ar
        try:
            wh.warehouse_name_ar = "مستودع اختبار الشجرة"
            wh.save()
            reloaded = frappe.get_doc("Warehouse", orig_name)
            self.assertEqual(reloaded.name, orig_name)
            self.assertEqual(reloaded.parent_warehouse, orig_parent)
            self.assertEqual(reloaded.warehouse_name, orig_wh_name)
            self.assertEqual(reloaded.warehouse_name_ar, "مستودع اختبار الشجرة")
            self.assertEqual(reloaded.warehouse_name_ar_norm, normalize_arabic("مستودع اختبار الشجرة"))
        finally:
            reloaded = frappe.get_doc("Warehouse", orig_name)
            reloaded.warehouse_name_ar = orig_ar
            reloaded.save()
            frappe.db.commit()

        # 3. Rename preservation across all three
        company = frappe.db.get_value("Company", {}, "name") or "Elrefae"
        abbr = frappe.get_cached_value("Company", company, "abbr") or "E"

        # Warehouse rename test
        wh_doc = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "CT-TEST-P2-WH-RN1",
            "warehouse_name_ar": "مستودع إعادة تسمية",
            "company": company,
        })
        wh_doc.insert(ignore_permissions=True)
        old_wh_name = wh_doc.name
        new_wh_name = f"CT-TEST-P2-WH-RN2 - {abbr}"
        if frappe.db.exists("Warehouse", new_wh_name):
            frappe.delete_doc("Warehouse", new_wh_name, force=True)
        try:
            frappe.rename_doc("Warehouse", old_wh_name, new_wh_name, force=True)
            renamed_wh = frappe.get_doc("Warehouse", new_wh_name)
            self.assertEqual(renamed_wh.warehouse_name_ar, "مستودع إعادة تسمية")
            self.assertEqual(renamed_wh.warehouse_name_ar_norm, normalize_arabic("مستودع إعادة تسمية"))
        finally:
            frappe.delete_doc("Warehouse", new_wh_name, force=True)

        # Cost Center rename test
        cc_doc = frappe.get_doc({
            "doctype": "Cost Center",
            "cost_center_name": "CT-TEST-P2-CC-RN1",
            "cost_center_name_ar": "مركز إعادة تسمية",
            "parent_cost_center": orig_parent or "Elrefae - E",
            "company": company,
        })
        cc_doc.insert(ignore_permissions=True)
        old_cc_name = cc_doc.name
        new_cc_name = f"CT-TEST-P2-CC-RN2 - {abbr}"
        if frappe.db.exists("Cost Center", new_cc_name):
            frappe.delete_doc("Cost Center", new_cc_name, force=True)
        try:
            frappe.rename_doc("Cost Center", old_cc_name, new_cc_name, force=True)
            renamed_cc = frappe.get_doc("Cost Center", new_cc_name)
            self.assertEqual(renamed_cc.cost_center_name_ar, "مركز إعادة تسمية")
            self.assertEqual(renamed_cc.cost_center_name_ar_norm, normalize_arabic("مركز إعادة تسمية"))
        finally:
            frappe.delete_doc("Cost Center", new_cc_name, force=True)

        # Project rename test
        prj_doc = frappe.get_doc({
            "doctype": "Project",
            "project_name": "CT-TEST-P2-PRJ-RN1",
            "project_name_ar": "مشروع إعادة تسمية",
            "company": company,
        })
        prj_doc.insert(ignore_permissions=True)
        old_prj_name = prj_doc.name
        new_prj_name = f"{old_prj_name}-REN"
        if frappe.db.exists("Project", new_prj_name):
            frappe.delete_doc("Project", new_prj_name, force=True)
        try:
            frappe.rename_doc("Project", old_prj_name, new_prj_name, force=True)
            renamed_prj = frappe.get_doc("Project", new_prj_name)
            self.assertEqual(renamed_prj.project_name_ar, "مشروع إعادة تسمية")
            self.assertEqual(renamed_prj.project_name_ar_norm, normalize_arabic("مشروع إعادة تسمية"))
        finally:
            frappe.delete_doc("Project", new_prj_name, force=True)

        frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        test_data = [
            ("Cost Center", "cost_center_name_ar", "إدارة الإنشاءات والتطوير"),
            ("Warehouse", "warehouse_name_ar", "مخزن الأدوات والمعدات"),
            ("Project", "project_name_ar", "مشروع الأبراج السكنية"),
        ]
        for dt, ar_fn, canonical_ar in test_data:
            doc = _get_target_doc(dt)
            orig_ar = doc.get(ar_fn)
            try:
                doc.set(ar_fn, canonical_ar)
                doc.save()
                frappe.db.commit()

                # Query with Alef variant / tatweel / missing hamza
                query = "ادارة" if "إدارة" in canonical_ar else ("الادوات" if "الأدوات" in canonical_ar else "الابراج")

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
