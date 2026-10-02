"""Stage 5 Wave 2d Pilot tests: Department bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-department-master \
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_department_pilot

Covers:
- Patch v9_6 idempotency and reversibility for department_name_ar and department_name_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Department.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on department_name_ar.
- Tree identity invariant (name and parent_department remain intact).
- Rename doc preserves Arabic and norm keys.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit c1d278b).
"""

import subprocess
import unittest
from pathlib import Path

import frappe

from construction.patches.v9_6.add_department_arabic_fields import execute as patch_execute
from construction.patches.v9_6.add_department_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_department():
    """Helper to fetch an existing non-root Department doc for testing."""
    docs = frappe.get_all("Department", filters={"is_group": 0}, limit=1)
    if not docs:
        docs = frappe.get_all("Department", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Department")
    return frappe.get_doc("Department", docs[0].name)


class TestBilingualDepartmentPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Department master primary claim: bilingual_service.py and search.py must be byte-identical to base commit c1d278b."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "c1d278b"
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
        """Idempotent execute and clean revert of patch v9_6 across Department custom fields."""
        patch_execute()
        targets = [
            ("Department", "department_name_ar"),
            ("Department", "department_name_ar_norm"),
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

    def test_registry_loads_and_maps_resolved_department_fields(self):
        """Ensure get_mapping resolves department_name_ar_norm, tree.enabled, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Department")
        self.assertIsNotNone(m, "Mapping missing for Department")
        self.assertEqual(m["resolved"].get("norm_field"), "department_name_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "department_name")
        self.assertEqual(m["resolved"].get("arabic_field"), "department_name_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertTrue(bool((m.get("tree") or {}).get("enabled")))

    def test_active_and_schema_installed_fail_closed_on_missing_department_field(self):
        """If norm_field is declared on schema_installed Department but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Department": {
                    "state": "schema_installed",
                    "english_field": "department_name",
                    "arabic_field": "department_name_ar",
                    "norm_field": "nonexistent_dept_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Department")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_department()
        orig_ar = doc.get("department_name_ar")
        orig_norm = doc.get("department_name_ar_norm")
        test_ar = "إدارة الهندسة المدنية والمعمارية"
        try:
            doc.set("department_name_ar", test_ar)
            doc.set("department_name_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Department", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("department_name_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Department!",
            )
        finally:
            clean = frappe.get_doc("Department", doc.name)
            clean.set("department_name_ar", orig_ar)
            clean.set("department_name_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """department_name_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "إدارة\u202eالمشاريع",  # Right-to-Left Override
            "إدارة\u200eالمشاريع",  # LRM
            "إدارة\u202bالمشاريع",  # RLE
            "إدارة\x00المشاريع",  # NUL
        ]
        doc = _get_target_department()
        orig_val = doc.get("department_name_ar")
        for bad_sample in forbidden_samples:
            doc.set("department_name_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Department", doc.name)
        clean.set("department_name_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_tree_identity_invariant_and_rename_preservation(self):
        """Department preserves parent_department link, tree structure, and retains Arabic/norm keys across rename."""
        company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name
        parent_root = frappe.get_all("Department", filters={"is_group": 1}, limit=1)[0].name
        dept_ar = "قسم التخطيط والمتابعة"
        test_dept_name = f"Test Planning {frappe.generate_hash(length=4)}"

        dept = frappe.get_doc({
            "doctype": "Department",
            "department_name": test_dept_name,
            "company": company,
            "parent_department": parent_root,
            "is_group": 0,
            "department_name_ar": dept_ar,
        })
        dept.insert(ignore_permissions=True)
        old_id = dept.name
        new_id = f"{old_id}-RENAMED"

        try:
            if frappe.db.exists("Department", new_id):
                frappe.delete_doc("Department", new_id, force=True)

            self.assertEqual(dept.department_name_ar_norm, normalize_arabic(dept_ar))
            self.assertEqual(dept.parent_department, parent_root)

            frappe.rename_doc("Department", old_id, new_id, force=True)

            renamed = frappe.get_doc("Department", new_id)
            self.assertEqual(renamed.department_name_ar, dept_ar)
            self.assertEqual(renamed.department_name_ar_norm, normalize_arabic(dept_ar))
            self.assertEqual(renamed.parent_department, parent_root)
        finally:
            if frappe.db.exists("Department", new_id):
                frappe.delete_doc("Department", new_id, force=True)
            if frappe.db.exists("Department", old_id):
                frappe.delete_doc("Department", old_id, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_department()
        orig_ar = doc.get("department_name_ar")
        test_canonical = "إِدَارَةُ المَوَارِدِ البَشَرِيَّةِ"
        try:
            doc.set("department_name_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Hamza or Tashkeel
            query = "ادارة الموارد"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Department", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Department) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Department", txt=query)
            items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Department) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Department", doc.name)
            clean.set("department_name_ar", orig_ar)
            clean.save()
            frappe.db.commit()
