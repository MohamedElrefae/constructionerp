"""Stage 4 tests: governed Account-language export + proposal machinery.

Run with: bench --site [site] run-tests --module construction.tests.test_stage4_account_language

Covers the export provenance contract (no invented references, proposal
scaffold pending, no live mutation), the glossary lookup, the proposal
record validation, and the zero-mutation dry-run plan.
"""

import unittest

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
        self.assertEqual(manifest["with_current_arabic"], 0, "no account has an Arabic name yet")
        self.assertEqual(manifest["groups"] + manifest["leaves"], manifest["rows"])
        # Every row: pending proposal; no invented reference; no current Arabic.
        for row in rows:
            self.assertIn(slp.FLAG_PENDING, row["flags"])
            self.assertIn(slp.FLAG_NO_VERIFIED_REFERENCE, row["flags"])
            self.assertIsNone(row["source_reference"], "no MOF/EAS/ETA reference may be invented")
            self.assertIsNone(row["proposed_arabic"])
            self.assertIsNone(row["current_arabic"])

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
        plan = slp.dry_run_apply_proposals(rows, {first: {"proposed_arabic": "x"}})
        self.assertIn(first, plan["would_update"])
        self.assertEqual(len(plan["missing"]), len(rows) - 1)
        # No mutation can have occurred: nothing writes to the DB.
        self.assertEqual(plan["would_update"], [first])

    def test_write_path_uses_private_dir_and_returns_hash(self):
        rows, manifest = slp.export_account_catalog(write=True)
        self.assertTrue(manifest["export_file_sha256"])
        self.assertTrue(manifest["private_location"])
        self.assertTrue(manifest["private_location"].startswith("<site>/private/"))


if __name__ == "__main__":
    unittest.main()
