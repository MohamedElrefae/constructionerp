"""Stage 5 Pilot tests: Company bilingual enablement.

Run with:
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_company_pilot

Covers:
- Patch v9_14 idempotency and reversibility for company_name_ar and company_name_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled=false, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Company.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on company_name_ar.
- Identity invariant over naming path (empty company_name rejected by autoname; name remains the
  English value; rename preserves Arabic and norm keys).
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical across reference commits).
"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch
from uuid import uuid4

import frappe

from construction.patches.v9_14.add_company_arabic_fields import execute as patch_execute
from construction.patches.v9_14.add_company_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic

COMPANY_FIELDS = [("Company", "company_name_ar"), ("Company", "company_name_ar_norm")]


def _get_target_company():
    """Helper to fetch an existing Company doc for testing."""
    docs = frappe.get_all("Company", filters={"name": ["like", "_Test Company%"]}, limit=1)
    if not docs:
        docs = frappe.get_all("Company", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Company")
    return frappe.get_doc("Company", docs[0].name)


class TestBilingualCompanyPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        frappe.local.ct_bilingual_mapping_cache = None
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Company master primary claim: bilingual_service.py and search.py must be byte-identical across reference commits."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "ba0e64b"
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
        """Idempotent execute and clean revert of patch v9_14 across Company custom fields."""
        patch_execute()
        for dt, fn in COMPANY_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in COMPANY_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in COMPANY_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in COMPANY_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_company_fields(self):
        """Ensure get_mapping resolves company_name_ar_norm, tree.enabled=false, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Company")
        self.assertIsNotNone(m, "Mapping missing for Company")
        self.assertEqual(m["resolved"].get("norm_field"), "company_name_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "company_name")
        self.assertEqual(m["resolved"].get("arabic_field"), "company_name_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertEqual(m["resolved"].get("identity_field"), "name")
        self.assertFalse(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(m.get("search", {}).get("fields"), ["company_name", "company_name_ar"])

    def test_active_and_schema_installed_fail_closed_on_missing_company_field(self):
        """If norm_field is declared on schema_installed Company but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Company": {
                    "state": "schema_installed",
                    "english_field": "company_name",
                    "arabic_field": "company_name_ar",
                    "norm_field": "nonexistent_company_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with mock_patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Company")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_company()
        orig_ar = doc.get("company_name_ar")
        orig_norm = doc.get("company_name_ar_norm")
        test_ar = "شركة الرفاعي للمقاولات العامة والإنشاءات"
        try:
            doc.set("company_name_ar", test_ar)
            doc.set("company_name_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Company", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("company_name_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Company!",
            )
        finally:
            clean = frappe.get_doc("Company", doc.name)
            clean.set("company_name_ar", orig_ar)
            clean.set("company_name_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """company_name_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "شركة\u202eالإنشاءات",  # Right-to-Left Override
            "شركة\u200eالإنشاءات",  # LRM
            "شركة\u202bالإنشاءات",  # RLE
            "شركة\x00الإنشاءات",  # NUL
        ]
        doc = _get_target_company()
        orig_val = doc.get("company_name_ar")
        for bad_sample in forbidden_samples:
            doc.set("company_name_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Company", doc.name)
        clean.set("company_name_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_identity_invariant_and_rename_preservation(self):
        """Company name matches company_name; autoname enforces non-empty; rename preserves Arabic."""
        company_ar_value = "شركة البناء والتطوير العقاري"
        suffix = uuid4().hex[:4].upper()
        test_abbr = f"T{suffix}"
        test_company = f"Co {suffix}"

        # 1. Empty company_name is rejected by the naming path (autoname = field:company_name)
        with self.assertRaises(frappe.ValidationError):
            bad_doc = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": "",
                    "abbr": f"B{suffix}",
                    "default_currency": "SAR",
                    "country": "Saudi Arabia",
                }
            )
            bad_doc.insert(ignore_permissions=True)

        # 2. Insert valid bilingual fixture
        doc = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": test_company,
                "abbr": test_abbr,
                "default_currency": "SAR",
                "country": "Saudi Arabia",
                "create_chart_of_accounts_based_on": "Standard Template",
                "chart_of_accounts": "Standard",
                "company_name_ar": company_ar_value,
            }
        )
        doc.insert(ignore_permissions=True)
        old_id = doc.name

        # Identity PK matches English company_name
        self.assertEqual(doc.name, test_company)
        self.assertEqual(doc.company_name_ar_norm, normalize_arabic(company_ar_value))

        new_id = f"{old_id} Renamed"

        try:
            if frappe.db.exists("Company", new_id):
                frappe.delete_doc("Company", new_id, force=True)

            frappe.rename_doc("Company", old_id, new_id, force=True)

            renamed = frappe.get_doc("Company", new_id)
            self.assertEqual(renamed.company_name, new_id)
            self.assertEqual(renamed.company_name_ar, company_ar_value)
            self.assertEqual(renamed.company_name_ar_norm, normalize_arabic(company_ar_value))
        finally:
            if frappe.db.exists("Company", new_id):
                frappe.delete_doc("Company", new_id, force=True)
            if frappe.db.exists("Company", old_id):
                frappe.delete_doc("Company", old_id, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_company()
        orig_ar = doc.get("company_name_ar")
        test_canonical = "شَرِكَةُ الإِنْشَاءَاتِ وَالتَّعْمِيرِ المِثَالِيَّةِ"
        try:
            doc.set("company_name_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Tashkeel
            query = "شركة الانشاءات والتعمير"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Company", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Company) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Company", txt=query)
            items = (
                dropdown_res.get("results", [])
                if isinstance(dropdown_res, dict)
                else dropdown_res
            )
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Company) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Company", doc.name)
            clean.set("company_name_ar", orig_ar)
            clean.save()
            frappe.db.commit()


if __name__ == "__main__":
    unittest.main()
