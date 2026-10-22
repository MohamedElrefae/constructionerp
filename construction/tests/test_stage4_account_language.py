"""Stage 4 tests: governed Account-language export + proposal machinery.

Run with: bench --site [site] run-tests --module construction.tests.test_stage4_account_language

Covers the export provenance contract (no invented references, proposal
scaffold pending, no live mutation), the glossary lookup, the proposal
record validation, and the zero-mutation dry-run plan. The suite is valid
both before and after an authorized Arabic-name import.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe

from construction.services import account_language_proposal as slp


class TestStage4AccountLanguage(unittest.TestCase):
    def test_export_returns_governed_manifest_contract(self):
        rows, manifest = slp.export_account_catalog(write=False)
        self.assertGreater(len(rows), 0)
        self.assertEqual(manifest["schema"], slp.EXPORT_SCHEMA)
        self.assertEqual(manifest["domain"], slp.DOMAIN)
        self.assertEqual(manifest["source_classification"], "non-production test")
        self.assertEqual(manifest["no_verified_reference"], slp.FLAG_NO_VERIFIED_REFERENCE)
        self.assertEqual(manifest["proposal_pending"], slp.FLAG_PENDING)
        self.assertIn("export_file_sha256", manifest)
        self.assertIn("recorded_utc", manifest)
        self.assertEqual(
            manifest["with_current_arabic"],
            sum(1 for row in rows if row["current_arabic"]),
        )
        self.assertEqual(manifest["groups"] + manifest["leaves"], manifest["rows"])
        # Every row remains a proposal scaffold with no invented reference.
        # current_arabic reflects live state and may be populated post-import.
        for row in rows:
            self.assertIn(slp.FLAG_PENDING, row["flags"])
            self.assertIn(slp.FLAG_NO_VERIFIED_REFERENCE, row["flags"])
            self.assertIsNone(row["source_reference"], "no MOF/EAS/ETA reference may be invented")
            self.assertIsNone(row["proposed_arabic"])

    def test_export_rows_have_identity_and_english(self):
        rows, _ = slp.export_account_catalog(write=False)
        for row in rows:
            self.assertTrue(row["identity"])
            self.assertTrue(row["english"])
            self.assertIsInstance(row["is_group"], bool)
            self.assertIn("account_number", row)

    def test_glossary_lookup_returns_mapping(self):
        mapping = slp.glossary_lookup()
        self.assertIsInstance(mapping, dict)
        self.assertGreater(len(mapping), 0)
        for k, v in mapping.items():
            self.assertTrue(k)
            self.assertTrue(v)

    def test_validate_proposal_contract(self):
        self.assertTrue(slp.validate_proposal(None))
        self.assertTrue(slp.validate_proposal({}))
        good = {
            "identity": "x - Cash - E",
            "english": "Cash",
            "is_group": False,
            "proposed_arabic": "نقدية",
            "confidence": "high",
        }
        self.assertEqual(slp.validate_proposal(good), [])  # structurally valid

    def test_dry_run_apply_is_zero_mutation_plan(self):
        rows, _ = slp.export_account_catalog(write=False)
        first = rows[0]["identity"]
        preview_rows = [dict(row) for row in rows]
        preview_rows[0]["current_arabic"] = None
        plan = slp.dry_run_apply_proposals(preview_rows, {first: {"proposed_arabic": "x"}})
        self.assertIn(first, plan["would_update"])
        self.assertEqual(len(plan["missing"]), len(rows) - 1)
        # No mutation can have occurred: nothing writes to the DB.
        self.assertEqual(plan["would_update"], [first])

    def test_write_path_uses_private_dir_and_returns_hash(self):
        real_get_app_path = frappe.get_app_path
        with tempfile.TemporaryDirectory() as temp_dir:
            private_dir = Path(temp_dir) / "private" / "stage4"
            manifest_path = Path(temp_dir) / "stage4_export_manifest.json"

            def isolated_app_path(app, *parts):
                if parts == (slp.GOVERNED_MANIFEST_RELPATH,):
                    return str(manifest_path)
                return real_get_app_path(app, *parts)

            with (
                patch.object(frappe, "get_app_path", side_effect=isolated_app_path),
                patch.object(frappe.utils, "get_site_path", return_value=str(private_dir)),
            ):
                rows, manifest = slp.export_account_catalog(write=True)

            self.assertTrue(rows)
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(manifest["export_file_sha256"])
            self.assertTrue(manifest["private_location"])
            self.assertTrue(manifest["private_location"].startswith("<site>/private/"))


if __name__ == "__main__":
    unittest.main()
