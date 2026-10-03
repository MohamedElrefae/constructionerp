"""Stage 5 Pilot tests: Asset bilingual enablement.

Run with:
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_asset_pilot

Covers:
- Patch v9_13 idempotency and reversibility for asset_name_ar and asset_name_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled=false, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Asset.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on asset_name_ar.
- naming_series identity invariant (decision A2, Employee pattern): name is the generated
  serial ACC-ASS-... and never the English value; rename preserves Arabic and norm keys.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit cc3a105).

Fixtures (decision A1): every test creates its own draft Asset (docstatus=0) against
existing site dependencies and deletes it on cleanup - never submitted, never cancelled.
"""

import re
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch
from uuid import uuid4

import frappe

from construction.patches.v9_13.add_asset_arabic_fields import execute as patch_execute
from construction.patches.v9_13.add_asset_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic

ASSET_FIELDS = [("Asset", "asset_name_ar"), ("Asset", "asset_name_ar_norm")]
NAMING_SERIES = "ACC-ASS-.YYYY.-"
NAME_PREFIX = "ACC-ASS-"


def _require_deps():
    """Resolve required Link references; skip rather than fail on a bare site (A1)."""
    deps = {}
    for dt in ("Company", "Location"):
        name = frappe.get_value(dt, {}, "name")
        if not name:
            raise unittest.SkipTest(f"No {dt} record available to build an Asset fixture")
        deps[dt] = name
    # Prefer an Item that carries an asset_category so the derived category resolves.
    item = frappe.get_value("Item", {"asset_category": ["is", "set"]}, "name")
    if not item:
        item = frappe.get_value("Item", {}, "name")
    if not item:
        raise unittest.SkipTest("No Item record available to build an Asset fixture")
    deps["Item"] = item
    return deps


def _create_asset(asset_name, asset_ar=None):
    """Insert a draft Asset fixture (docstatus=0) with existing site dependencies.

    `asset_type: Existing Asset` is ERPNext's own fixture recipe (test_asset.create_asset):
    it short-circuits the CWIP purchase-document requirement and the net-vs-purchase
    amount comparison, so no purchase receipt/invoice is needed. Fixtures are never
    submitted (decision A1).
    """
    deps = _require_deps()
    doc = frappe.get_doc(
        {
            "doctype": "Asset",
            "naming_series": NAMING_SERIES,
            "asset_name": asset_name,
            "asset_type": "Existing Asset",
            "item_code": deps["Item"],
            "location": deps["Location"],
            "company": deps["Company"],
            "purchase_date": "2026-01-01",
            "net_purchase_amount": 100000,
            "asset_name_ar": asset_ar,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def _delete_asset(name):
    """Delete a draft Asset fixture plus its Asset Activity audit rows."""
    if frappe.db.exists("Asset", name):
        frappe.delete_doc("Asset", name, force=True, ignore_permissions=True)
    for row in frappe.get_all(
        "Asset Activity", filters={"asset": name}, pluck="name", limit=0
    ):
        frappe.delete_doc("Asset Activity", row, force=True, ignore_permissions=True)
    frappe.db.commit()


class TestBilingualAssetPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        frappe.local.ct_bilingual_mapping_cache = None
        patch_execute()
        _require_deps()

    def test_zero_service_edits_guard(self):
        """Asset master primary claim: bilingual_service.py and search.py must be byte-identical to base commit cc3a105."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "cc3a105"
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
        """Idempotent execute and clean revert of patch v9_13 across Asset custom fields."""
        patch_execute()
        for dt, fn in ASSET_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in ASSET_FIELDS:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in ASSET_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in ASSET_FIELDS:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_asset_fields(self):
        """Ensure get_mapping resolves asset_name_ar_norm, tree.enabled=false, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Asset")
        self.assertIsNotNone(m, "Mapping missing for Asset")
        self.assertEqual(m["resolved"].get("norm_field"), "asset_name_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "asset_name")
        self.assertEqual(m["resolved"].get("arabic_field"), "asset_name_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertEqual(m["resolved"].get("identity_field"), "name")
        self.assertFalse(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(
            m.get("search", {}).get("fields"), ["asset_name", "asset_name_ar"]
        )

    def test_active_and_schema_installed_fail_closed_on_missing_asset_field(self):
        """If norm_field is declared on schema_installed Asset but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Asset": {
                    "state": "schema_installed",
                    "english_field": "asset_name",
                    "arabic_field": "asset_name_ar",
                    "norm_field": "nonexistent_asset_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with mock_patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Asset")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _create_asset(f"CT-ASSET-{uuid4().hex[:6]}")
        try:
            test_ar = "رافعة برجية معتمدة للمشروع"
            doc.set("asset_name_ar", test_ar)
            doc.set("asset_name_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Asset", doc.name)
            self.assertEqual(
                reloaded.get("asset_name_ar_norm"),
                normalize_arabic(test_ar),
                "Poisoned key survived or norm key not derived on Asset!",
            )
        finally:
            _delete_asset(doc.name)

    def test_arabic_edit_rejects_bidi_controls(self):
        """asset_name_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "رافعة\u202eبرجية",  # Right-to-Left Override
            "رافعة\u200eبرجية",  # LRM
            "رافعة\u202bبرجية",  # RLE
            "رافعة\x00برجية",  # NUL
        ]
        doc = _create_asset(f"CT-ASSET-{uuid4().hex[:6]}")
        try:
            for bad_sample in forbidden_samples:
                doc.set("asset_name_ar", bad_sample)
                with self.assertRaises(frappe.ValidationError):
                    doc.save()
        finally:
            _delete_asset(doc.name)

    def test_naming_series_identity_invariant_and_rename_preservation(self):
        """Decision A2 (Employee pattern): name is the naming-series serial, never asset_name;
        rename preserves asset_name, asset_name_ar and the norm key."""
        # 1. Even when asset_name is left blank (ERPNext derives it from the Item),
        #    the identity PK is still the naming-series serial - never the English value.
        deps = _require_deps()
        derived = frappe.get_doc(
            {
                "doctype": "Asset",
                "naming_series": NAMING_SERIES,
                "asset_type": "Existing Asset",
                "item_code": deps["Item"],
                "location": deps["Location"],
                "company": deps["Company"],
                "purchase_date": "2026-01-01",
                "net_purchase_amount": 100000,
            }
        )
        derived.insert(ignore_permissions=True)
        derived_id = derived.name
        try:
            self.assertTrue(derived_id.startswith(NAME_PREFIX), derived_id)
            self.assertTrue(derived.asset_name, "asset_name must be derived when blank")
            self.assertNotEqual(derived_id, derived.asset_name)
        finally:
            _delete_asset(derived_id)

        # 2. Insert a valid bilingual draft fixture
        asset_ar = "مشتل البناء المتكامل"
        test_asset_name = f"CT-ASSET-{uuid4().hex[:6]}"
        doc = _create_asset(test_asset_name, asset_ar=asset_ar)
        old_id = doc.name

        try:
            # Identity PK is the generated series, distinct from the English value
            self.assertNotEqual(doc.name, test_asset_name)
            self.assertTrue(
                doc.name.startswith(NAME_PREFIX),
                f"expected naming-series name, got {doc.name!r}",
            )
            self.assertRegex(doc.name, re.compile(rf"^{NAME_PREFIX}\d{{4}}-\d+$"))
            self.assertEqual(doc.asset_name, test_asset_name)
            self.assertEqual(doc.docstatus, 0, "fixtures must stay draft (A1)")
            self.assertEqual(doc.asset_name_ar_norm, normalize_arabic(asset_ar))

            # 3. Rename preserves Arabic identity keys
            new_id = f"{old_id}-RENAMED"
            if frappe.db.exists("Asset", new_id):
                _delete_asset(new_id)
            frappe.rename_doc("Asset", old_id, new_id, force=True)

            renamed = frappe.get_doc("Asset", new_id)
            self.assertEqual(renamed.name, new_id)
            self.assertEqual(renamed.asset_name, test_asset_name)
            self.assertEqual(renamed.asset_name_ar, asset_ar)
            self.assertEqual(
                renamed.asset_name_ar_norm, normalize_arabic(asset_ar)
            )
        finally:
            for candidate in (old_id, f"{old_id}-RENAMED"):
                _delete_asset(candidate)

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        test_canonical = "قَاطِعُ الأَسْمِنْتِ المُشْرَفِيِّ"
        doc = _create_asset(f"CT-ASSET-{uuid4().hex[:6]}", asset_ar=test_canonical)
        try:
            frappe.db.commit()
            query = "قاطع الاسمنت"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Asset", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Asset) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Asset", txt=query)
            items = (
                dropdown_res.get("results", [])
                if isinstance(dropdown_res, dict)
                else dropdown_res
            )
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Asset) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            _delete_asset(doc.name)
