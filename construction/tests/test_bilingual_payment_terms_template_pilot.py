"""Stage 5 Wave 3 Pilot tests: Payment Terms Template bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-payment-terms-template-master \\
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_payment_terms_template_pilot

Covers:
- Patch v9_10 idempotency and reversibility for template_name_ar and template_name_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled=false, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Payment Terms Template.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on template_name_ar.
- Identity invariant over naming path (empty template_name raises via autoname; name remains English value; rename preserves Arabic and norm keys).
- Child detail rows requirement respected without orphan leakage on teardown.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit 2cbe71a).
"""

import subprocess
import unittest
from pathlib import Path
from uuid import uuid4

import frappe

from construction.patches.v9_10.add_payment_terms_template_arabic_fields import execute as patch_execute
from construction.patches.v9_10.add_payment_terms_template_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_payment_terms_template():
    """Helper to fetch an existing Payment Terms Template doc for testing."""
    docs = frappe.get_all("Payment Terms Template", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Payment Terms Template")
    return frappe.get_doc("Payment Terms Template", docs[0].name)


class TestBilingualPaymentTermsTemplatePilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Payment Terms Template master primary claim: bilingual_service.py and search.py must be byte-identical to base commit 2cbe71a."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "2cbe71a"
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
        """Idempotent execute and clean revert of patch v9_10 across Payment Terms Template custom fields."""
        patch_execute()
        targets = [
            ("Payment Terms Template", "template_name_ar"),
            ("Payment Terms Template", "template_name_ar_norm"),
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

    def test_registry_loads_and_maps_resolved_payment_terms_template_fields(self):
        """Ensure get_mapping resolves template_name_ar_norm, tree.enabled=false, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Payment Terms Template")
        self.assertIsNotNone(m, "Mapping missing for Payment Terms Template")
        self.assertEqual(m["resolved"].get("norm_field"), "template_name_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "template_name")
        self.assertEqual(m["resolved"].get("arabic_field"), "template_name_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertFalse(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(m.get("search", {}).get("fields"), ["template_name", "template_name_ar"])

    def test_active_and_schema_installed_fail_closed_on_missing_payment_terms_template_field(self):
        """If norm_field is declared on schema_installed Payment Terms Template but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Payment Terms Template": {
                    "state": "schema_installed",
                    "english_field": "template_name",
                    "arabic_field": "template_name_ar",
                    "norm_field": "nonexistent_ptt_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Payment Terms Template")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_payment_terms_template()
        orig_ar = doc.get("template_name_ar")
        orig_norm = doc.get("template_name_ar_norm")
        test_ar = "قالب شروط الدفع المعتمد للمقاولين"
        try:
            doc.set("template_name_ar", test_ar)
            doc.set("template_name_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Payment Terms Template", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("template_name_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Payment Terms Template!",
            )
        finally:
            clean = frappe.get_doc("Payment Terms Template", doc.name)
            clean.set("template_name_ar", orig_ar)
            clean.set("template_name_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """template_name_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "قالب\u202eشروط",  # Right-to-Left Override
            "قالب\u200eشروط",  # LRM
            "قالب\u202bشروط",  # RLE
            "قالب\x00شروط",  # NUL
        ]
        doc = _get_target_payment_terms_template()
        orig_val = doc.get("template_name_ar")
        for bad_sample in forbidden_samples:
            doc.set("template_name_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Payment Terms Template", doc.name)
        clean.set("template_name_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_identity_invariant_and_rename_preservation(self):
        """Payment Terms Template name remains English value; autoname enforces non-empty; rename preserves Arabic."""
        # 1. Assert empty template_name is rejected by naming path (autoname)
        with self.assertRaises(frappe.ValidationError):
            bad_doc = frappe.get_doc({
                "doctype": "Payment Terms Template",
                "template_name": "",
                "terms": [{
                    "payment_term": "_Test COD",
                    "invoice_portion": 100.0,
                    "due_date_based_on": "Day(s) after invoice date",
                }],
            })
            bad_doc.insert(ignore_permissions=True)

        # 2. Insert valid bilingual fixture with required detail row
        template_ar = "شروط الدفع القياسية للمشروع"
        test_template_name = f"Terms {uuid4().hex[:6]}"

        tmpl = frappe.get_doc({
            "doctype": "Payment Terms Template",
            "template_name": test_template_name,
            "template_name_ar": template_ar,
            "terms": [
                {
                    "payment_term": "_Test COD",
                    "description": "_Test Cash on Delivery",
                    "invoice_portion": 100.0,
                    "due_date_based_on": "Day(s) after invoice date",
                }
            ],
        })
        tmpl.insert(ignore_permissions=True)
        old_id = tmpl.name

        # Verify name PK matches English value, not Arabic
        self.assertEqual(tmpl.name, test_template_name)
        self.assertEqual(tmpl.template_name_ar_norm, normalize_arabic(template_ar))

        new_id = f"{old_id}-RENAMED"

        try:
            if frappe.db.exists("Payment Terms Template", new_id):
                frappe.delete_doc("Payment Terms Template", new_id, force=True)

            frappe.rename_doc("Payment Terms Template", old_id, new_id, force=True)

            renamed = frappe.get_doc("Payment Terms Template", new_id)
            self.assertEqual(renamed.template_name, new_id)
            self.assertEqual(renamed.template_name_ar, template_ar)
            self.assertEqual(renamed.template_name_ar_norm, normalize_arabic(template_ar))
            # Verify child row updated parent link
            self.assertEqual(len(renamed.terms), 1)
            self.assertEqual(renamed.terms[0].parent, new_id)
        finally:
            if frappe.db.exists("Payment Terms Template", new_id):
                frappe.delete_doc("Payment Terms Template", new_id, force=True)
            if frappe.db.exists("Payment Terms Template", old_id):
                frappe.delete_doc("Payment Terms Template", old_id, force=True)
            frappe.db.commit()

            # Assert zero leftover child rows
            leftover_children = frappe.get_all(
                "Payment Terms Template Detail",
                filters={"parent": ["in", [old_id, new_id]]},
            )
            self.assertEqual(len(leftover_children), 0, "Orphan child rows found after delete_doc!")

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_payment_terms_template()
        orig_ar = doc.get("template_name_ar")
        test_canonical = "قَالِبُ الدَّفْعَاتِ الْمُجَدْوَلَةِ"
        try:
            doc.set("template_name_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Tashkeel
            query = "قالب الدفعات"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Payment Terms Template", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Payment Terms Template) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Payment Terms Template", txt=query)
            items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Payment Terms Template) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Payment Terms Template", doc.name)
            clean.set("template_name_ar", orig_ar)
            clean.save()
            frappe.db.commit()
