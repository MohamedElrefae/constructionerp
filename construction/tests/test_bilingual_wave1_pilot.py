"""
Stage 5 Wave 1 Pilot tests: Item, Customer, Supplier bilingual enablement.

Run with: bench --site [site] run-tests --module construction.tests.test_bilingual_wave1_pilot

Covers:
- Patch v9_2 idempotency and reversibility for Item, Customer, and Supplier norm fields.
- Registry mapping resolution including norm_field.
- Fail-closed validation when declared norm_field is missing on active/schema_installed doctypes.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on Arabic fields.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics
  across both search_bilingual and searchable_link_search.
- Search projection and ASCII query baseline behavior.
"""

import unittest
from pathlib import Path

import frappe

from construction.patches.v9_2.add_wave1_arabic_norm_fields import execute as patch_execute
from construction.patches.v9_2.add_wave1_arabic_norm_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


class TestBilingualWave1Pilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_norm_field_patch_idempotent_and_reversible(self):
        """Idempotent execute and clean revert across Item, Customer, Supplier."""
        patch_execute()
        for dt, fn in [
            ("Item", "item_name_ar_norm"),
            ("Customer", "customer_name_in_arabic_norm"),
            ("Supplier", "supplier_name_in_arabic_norm"),
        ]:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in [
            ("Item", "item_name_ar_norm"),
            ("Customer", "customer_name_in_arabic_norm"),
            ("Supplier", "supplier_name_in_arabic_norm"),
        ]:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in [
            ("Item", "item_name_ar_norm"),
            ("Customer", "customer_name_in_arabic_norm"),
            ("Supplier", "supplier_name_in_arabic_norm"),
        ]:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in [
            ("Item", "item_name_ar_norm"),
            ("Customer", "customer_name_in_arabic_norm"),
            ("Supplier", "supplier_name_in_arabic_norm"),
        ]:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_norm_fields(self):
        """Ensure get_mapping resolves norm_field for all Wave 1 masters."""
        frappe.local.ct_bilingual_mapping_cache = None
        for dt, expected_norm in [
            ("Account", "account_name_ar_norm"),
            ("Item", "item_name_ar_norm"),
            ("Customer", "customer_name_in_arabic_norm"),
            ("Supplier", "supplier_name_in_arabic_norm"),
        ]:
            m = svc.get_mapping(dt)
            self.assertIsNotNone(m, f"Mapping missing for {dt}")
            self.assertEqual(m["resolved"].get("norm_field"), expected_norm)

    def test_active_and_schema_installed_fail_closed_on_missing_norm_field(self):
        """If norm_field is declared on active/schema_installed doctype but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Item": {
                    "state": "schema_installed",
                    "english_field": "item_name",
                    "arabic_field": "item_name_ar",
                    "norm_field": "nonexistent_norm_field",
                    "code_field": "item_code",
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Item")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """A client-provided POISONED-KEY must never survive on save for Wave 1 targets."""
        targets = [
            ("Item", "item_name_ar", "item_name_ar_norm", "أسمنت بورتلاندي مقاوم"),
            ("Customer", "customer_name_in_arabic", "customer_name_in_arabic_norm", "شركة الأمل للتطوير"),
            ("Supplier", "supplier_name_in_arabic", "supplier_name_in_arabic_norm", "مؤسسة الوفاء للتوريدات"),
        ]
        for dt, ar_fn, norm_fn, test_ar in targets:
            docs = frappe.get_all(dt, limit=1)
            self.assertTrue(docs, f"No existing {dt} records to test")
            doc = frappe.get_doc(dt, docs[0].name)
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
        """Arabic identity fields reject bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        targets = [
            ("Item", "item_name_ar"),
            ("Customer", "customer_name_in_arabic"),
            ("Supplier", "supplier_name_in_arabic"),
        ]
        forbidden_samples = [
            "اسم\u202eعربي",  # Right-to-Left Override
            "اسم\u200eعربي",  # LRM
            "اسم\u2066عربي",  # LRI
            "اسم\u0000عربي",  # NUL
        ]
        for dt, ar_fn in targets:
            docs = frappe.get_all(dt, limit=1)
            self.assertTrue(docs, f"No existing {dt} records to test")
            doc = frappe.get_doc(dt, docs[0].name)
            orig_ar = doc.get(ar_fn)
            try:
                for bad in forbidden_samples:
                    doc.set(ar_fn, bad)
                    with self.assertRaises(frappe.ValidationError):
                        doc.save()
            finally:
                clean = frappe.get_doc(dt, doc.name)
                clean.set(ar_fn, orig_ar)
                clean.save()
                frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Bilingual search and searchable_link_search match despite spelling variations."""
        targets = [
            ("Item", "item_name_ar", "أَحْمَـد للأسمنت", "احمد"),
            ("Customer", "customer_name_in_arabic", "مَجْمُوعَة الإِخْوَة", "مجموعة الاخوة"),
            ("Supplier", "supplier_name_in_arabic", "شَرِكَةُ الأَهْرَامِ", "شركة الاهرام"),
        ]
        for dt, ar_fn, full_ar, bare_query in targets:
            docs = frappe.get_all(dt, limit=1)
            self.assertTrue(docs, f"No existing {dt} records to test")
            doc = frappe.get_doc(dt, docs[0].name)
            orig_ar = doc.get(ar_fn)
            try:
                doc.set(ar_fn, full_ar)
                doc.save()

                # 1. svc.search_bilingual
                res1 = svc.search_bilingual(dt, txt=bare_query)
                self.assertIsNotNone(res1)
                matched_ids1 = [r["value"] for r in res1]
                self.assertIn(
                    doc.name,
                    matched_ids1,
                    f"{dt}: search_bilingual failed to match '{bare_query}' against '{full_ar}'",
                )

                # 2. searchable_link_search
                res2 = searchable_link_search(dt, txt=bare_query)
                self.assertIsNotNone(res2)
                matched_ids2 = [r["value"] for r in res2]
                self.assertIn(
                    doc.name,
                    matched_ids2,
                    f"{dt}: searchable_link_search failed to match '{bare_query}' against '{full_ar}'",
                )
            finally:
                clean = frappe.get_doc(dt, doc.name)
                clean.set(ar_fn, orig_ar)
                clean.save()
                frappe.db.commit()

    def test_search_projection_includes_arabic_fields(self):
        """Bilingual search and read_identity return Arabic field values alongside English and code."""
        docs = frappe.get_all("Item", limit=1)
        self.assertTrue(docs)
        doc = frappe.get_doc("Item", docs[0].name)
        orig_ar = doc.item_name_ar
        try:
            doc.item_name_ar = "صنف تجريبي"
            doc.save()

            # 1. search_bilingual with lang='ar' returns Arabic label and mode
            results_ar = svc.search_bilingual("Item", txt="صنف", lang="ar")
            self.assertTrue(results_ar)
            hit_ar = next((r for r in results_ar if r["value"] == doc.name), None)
            self.assertIsNotNone(hit_ar)
            self.assertEqual(hit_ar.get("label"), "صنف تجريبي")
            self.assertEqual(hit_ar.get("label_mode"), "arabic")

            # 2. read_identity returns explicit arabic and english fields
            ident = svc.read_identity("Item", doc.name)
            self.assertIsNotNone(ident)
            self.assertEqual(ident.get("arabic"), "صنف تجريبي")
            self.assertEqual(ident.get("english"), doc.item_name)
        finally:
            clean = frappe.get_doc("Item", doc.name)
            clean.item_name_ar = orig_ar
            clean.save()
            frappe.db.commit()

    def test_rename_doc_preserves_arabic_and_norm_keys(self):
        """Standard Frappe rename_doc on Wave 1 targets preserves Arabic name and derived norm key."""
        # Fetch valid reference groups from live site fixtures
        cust_fixture = frappe.get_all("Customer", fields=["customer_group", "territory"], limit=1)[0]
        supp_fixture = frappe.get_all("Supplier", fields=["supplier_group"], limit=1)[0]

        targets = [
            ("Item", {
                "doctype": "Item",
                "item_code": "CT-TEST-REN-ITM-01",
                "item_name": "Test Rename Item",
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "item_name_ar": "صنف تجريبي قابل للتسمية",
            }, "CT-TEST-REN-ITM-02", "item_name_ar", "item_name_ar_norm"),
            ("Customer", {
                "doctype": "Customer",
                "customer_name": "CT-TEST-REN-CUST-01",
                "customer_type": "Company",
                "customer_group": cust_fixture["customer_group"],
                "territory": cust_fixture["territory"],
                "customer_name_in_arabic": "عميل تجريبي قابل للتسمية",
            }, "CT-TEST-REN-CUST-02", "customer_name_in_arabic", "customer_name_in_arabic_norm"),
            ("Supplier", {
                "doctype": "Supplier",
                "supplier_name": "CT-TEST-REN-SUPP-01",
                "supplier_type": "Company",
                "supplier_group": supp_fixture["supplier_group"],
                "supplier_name_in_arabic": "مورد تجريبي قابل للتسمية",
            }, "CT-TEST-REN-SUPP-02", "supplier_name_in_arabic", "supplier_name_in_arabic_norm"),
        ]
        for dt, doc_data, new_name, ar_fn, norm_fn in targets:
            doc = frappe.get_doc(doc_data)
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            old_name = doc.name
            expected_norm = normalize_arabic(doc.get(ar_fn))
            try:
                self.assertEqual(doc.get(norm_fn), expected_norm)
                frappe.rename_doc(dt, old_name, new_name, force=True)
                frappe.db.commit()

                renamed = frappe.get_doc(dt, new_name)
                self.assertEqual(renamed.name, new_name)
                self.assertEqual(renamed.get(ar_fn), doc_data[ar_fn])
                self.assertEqual(renamed.get(norm_fn), expected_norm)
            finally:
                for n in [old_name, new_name]:
                    if frappe.db.exists(dt, n):
                        frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
                frappe.db.commit()
