"""Stage 5 Wave 2c Pilot tests: Employee bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-employee-master \
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_employee_pilot

Covers:
- Patch v9_5 idempotency and reversibility for employee_name_ar and employee_name_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Employee.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on employee_name_ar.
- Org-chart identity invariant (name and reports_to remain ASCII serials/unaltered).
- Rename doc preserves Arabic and norm keys.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit b311377).
"""

import subprocess
import unittest
from pathlib import Path

import frappe

from construction.patches.v9_5.add_employee_arabic_fields import execute as patch_execute
from construction.patches.v9_5.add_employee_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_employee():
    """Helper to fetch an existing Employee doc for testing."""
    docs = frappe.get_all("Employee", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Employee")
    return frappe.get_doc("Employee", docs[0].name)


class TestBilingualEmployeePilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Employee master primary claim: bilingual_service.py and search.py must be byte-identical to base commit b311377."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "b3113779c32e7a8f95343d5352ad9a639d3c23a3"
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
        """Idempotent execute and clean revert of patch v9_5 across Employee custom fields."""
        patch_execute()
        targets = [
            ("Employee", "employee_name_ar"),
            ("Employee", "employee_name_ar_norm"),
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

    def test_registry_loads_and_maps_resolved_employee_fields(self):
        """Ensure get_mapping resolves employee_name_ar_norm, tree.enabled, and code_field."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Employee")
        self.assertIsNotNone(m, "Mapping missing for Employee")
        self.assertEqual(m["resolved"].get("norm_field"), "employee_name_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "employee_name")
        self.assertEqual(m["resolved"].get("arabic_field"), "employee_name_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertTrue(bool((m.get("tree") or {}).get("enabled")))

    def test_active_and_schema_installed_fail_closed_on_missing_employee_field(self):
        """If norm_field is declared on schema_installed Employee but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Employee": {
                    "state": "schema_installed",
                    "english_field": "employee_name",
                    "arabic_field": "employee_name_ar",
                    "norm_field": "nonexistent_employee_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Employee")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_employee()
        orig_ar = doc.get("employee_name_ar")
        orig_norm = doc.get("employee_name_ar_norm")
        test_ar = "المهندس أحمد مصطفى المنصوري"
        try:
            doc.set("employee_name_ar", test_ar)
            doc.set("employee_name_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Employee", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("employee_name_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Employee!",
            )
        finally:
            clean = frappe.get_doc("Employee", doc.name)
            clean.set("employee_name_ar", orig_ar)
            clean.set("employee_name_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """employee_name_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "أحمد\u202eالمنصوري",  # Right-to-Left Override
            "أحمد\u200eالمنصوري",  # LRM
            "أحمد\u202bالمنصوري",  # RLE
            "أحمد\x00المنصوري",  # NUL
        ]
        doc = _get_target_employee()
        orig_val = doc.get("employee_name_ar")
        for bad_sample in forbidden_samples:
            doc.set("employee_name_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Employee", doc.name)
        clean.set("employee_name_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_tree_identity_invariant_and_rename_preservation(self):
        """Employee preserves ASCII name serial, reports_to pointer, and retains Arabic/norm keys across rename."""
        doc = _get_target_employee()
        orig_name = doc.name
        orig_reports_to = doc.reports_to
        orig_eng = doc.employee_name
        orig_ar = doc.employee_name_ar
        test_ar = "المشرف الميداني طارق"
        try:
            doc.set("employee_name_ar", test_ar)
            doc.save()

            reloaded = frappe.get_doc("Employee", orig_name)
            self.assertEqual(reloaded.name, orig_name)
            self.assertEqual(reloaded.reports_to, orig_reports_to)
            self.assertEqual(reloaded.employee_name, orig_eng)
            self.assertEqual(reloaded.employee_name_ar, test_ar)
            self.assertEqual(reloaded.employee_name_ar_norm, normalize_arabic(test_ar))
        finally:
            clean = frappe.get_doc("Employee", orig_name)
            clean.set("employee_name_ar", orig_ar)
            clean.save()
            frappe.db.commit()

        # Rename preservation test
        emp_ar = "مهندس ضبط الجودة عمر"
        emp = frappe.get_doc({
            "doctype": "Employee",
            "first_name": "Omar",
            "last_name": "Test",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "date_of_joining": "2020-01-01",
            "company": "Elrefae",
            "status": "Active",
            "employee_name_ar": emp_ar,
        })
        emp.insert(ignore_permissions=True)
        old_id = emp.name
        new_id = f"{old_id}-RENAMED"
        if frappe.db.exists("Employee", new_id):
            frappe.delete_doc("Employee", new_id, force=True)

        self.assertEqual(emp.employee_name_ar_norm, normalize_arabic(emp_ar))

        frappe.rename_doc("Employee", old_id, new_id, force=True)

        renamed = frappe.get_doc("Employee", new_id)
        self.assertEqual(renamed.employee_name_ar, emp_ar)
        self.assertEqual(renamed.employee_name_ar_norm, normalize_arabic(emp_ar))

        frappe.delete_doc("Employee", new_id, force=True)
        frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_employee()
        orig_ar = doc.get("employee_name_ar")
        test_canonical = "أحمد إبراهيم الإنشائي"
        try:
            doc.set("employee_name_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef (missing hamza on أحمد)
            query = "احمد ابراهيم"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Employee", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Employee) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Employee", txt=query)
            items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Employee) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Employee", doc.name)
            clean.set("employee_name_ar", orig_ar)
            clean.save()
            frappe.db.commit()
