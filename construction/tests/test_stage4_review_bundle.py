"""Stage 4 tests: governed review-bundle schema + fail-closed validator.

Pure stdlib — runs standalone and via bench:
  python3 construction/tests/test_stage4_review_bundle.py
  bench --site [site] run-tests --module construction.tests.test_stage4_review_bundle

Proves: no import payload without distinct proposal/AI-A2 provenance, a
decision, confidence, and a verified reference or explicit documented
absence; exceptions preserved as reviewable rows; no Arabic values invented.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "construction"))

from services import account_review_bundle as rb  # noqa: E402


def good_row(identity="1100 - Cash - E", decision="approved", ref_status="verified"):
    reference = (
        {"status": "verified", "value": "EAS 48 §…", "source": "EAS"}
        if ref_status == "verified"
        else {"status": "absent", "value": None, "source": None}
    )
    flags = ["no_verified_reference"] if ref_status == "absent" else []
    return {
        "identity": identity,
        "english": "Cash",
        "is_group": False,
        "proposal": {
            "arabic": "نقدية",
            "confidence": "high",
            "flags": [],
            "provenance": {"reviewer": "AI-A1", "model": "proposal-model", "session": "sess-1", "submitted_utc": "2026-09-10T00:00:00Z"},
        },
        "a2_review": {
            "decision": decision,
            "confidence": "high",
            "rationale": "matches glossary",
            "reference": reference,
            "provenance": {"reviewer": "AI-A2", "model": "a2-model", "session": "sess-2", "reviewed_utc": "2026-09-10T01:00:00Z"},
        },
        "flags": flags,
    }


def bundle_with(*rows):
    return {"schema": rb.BUNDLE_SCHEMA, "company": "Elrefae", "rows": list(rows)}


def export_payload(rows):
    return {"schema": rb.EXPORT_SCHEMA, "company": "Elrefae", "rows": rows}


def export_row(identity, english):
    return {"identity": identity, "english": english}


def make_export_and_manifest(rows):
    """Write a private export + a governed manifest in temp files; return
    (manifest_path, export_path, export_sha). Use `inject_manifest` to point
    the production entry point at it (private DI seam only)."""
    d = tempfile.mkdtemp()
    export_path = Path(d) / "export.json"
    export_path.write_text(json.dumps(export_payload(rows)), encoding="utf-8")
    sha = hashlib.sha256(export_path.read_bytes()).hexdigest()
    manifest = {
        "schema": rb.GOVERNED_MANIFEST_SCHEMA,
        "company": "Elrefae",
        "export_path": str(export_path),
        "export_sha256": sha,
        "rows": len(rows),
    }
    manifest_path = Path(d) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return str(manifest_path), str(export_path), sha


def inject_manifest(manifest_path):
    """Test-only DI: monkeypatch the PRIVATE governed-manifest resolver so the
    public entry point (which takes no path) reads the temp manifest."""
    import unittest.mock as _mock
    return _mock.patch.object(rb, "_governed_manifest_path", lambda: manifest_path)


class TestReviewBundleValidation(unittest.TestCase):
    def test_valid_bundle_passes(self):
        summary = rb.validate_bundle(bundle_with(good_row()))
        self.assertEqual(summary["violations"], [])
        self.assertEqual(summary["approved_count"], 1)
        self.assertEqual(summary["row_count"], 1)

    def test_template_is_empty_and_not_prefilled(self):
        t = rb.bundle_template()
        row = t["rows"][0]
        self.assertIsNone(row["proposal"]["arabic"])
        self.assertIsNone(row["a2_review"]["decision"])
        self.assertIsNone(row["identity"])

    def test_missing_schema_rejected(self):
        summary = rb.validate_bundle({"rows": [good_row()]})
        self.assertTrue(any("schema" in v for v in summary["violations"]))

    def test_invented_or_missing_arabic_rejected(self):
        row = good_row()
        row["proposal"]["arabic"] = None
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("proposal.arabic" in v for v in summary["violations"]))

    def test_missing_decision_rejected(self):
        row = good_row()
        row["a2_review"]["decision"] = None
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("decision" in v for v in summary["violations"]))

    def test_missing_confidence_rejected(self):
        row = good_row()
        row["a2_review"]["confidence"] = None
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("confidence" in v for v in summary["violations"]))

    def test_reference_must_be_verified_or_explicit_absence(self):
        row = good_row()
        row["a2_review"]["reference"] = {"status": "something_else"}
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("reference.status" in v for v in summary["violations"]))

    def test_verified_reference_requires_value_and_source(self):
        row = good_row()
        row["a2_review"]["reference"] = {"status": "verified", "value": None, "source": None}
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("never be invented" in v or "requires value" in v for v in summary["violations"]))

    def test_absent_reference_requires_explicit_flag(self):
        row = good_row(ref_status="absent")
        row["flags"] = []
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("no_verified_reference" in v for v in summary["violations"]))

    def test_explicit_absence_is_acceptable(self):
        summary = rb.validate_bundle(bundle_with(good_row(ref_status="absent")))
        self.assertEqual(summary["violations"], [])

    def test_proposal_and_a2_must_be_independent(self):
        row = good_row()
        row["a2_review"]["provenance"]["session"] = row["proposal"]["provenance"]["session"]
        row["a2_review"]["provenance"]["reviewer"] = row["proposal"]["provenance"]["reviewer"]
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("DISTINCT" in v for v in summary["violations"]))

    def test_timestamp_order_enforced(self):
        row = good_row()
        row["proposal"]["provenance"]["submitted_utc"] = "2026-09-10T02:00:00Z"
        row["a2_review"]["provenance"]["reviewed_utc"] = "2026-09-10T01:00:00Z"
        summary = rb.validate_bundle(bundle_with(row))
        self.assertTrue(any("after the AI-A2" in v for v in summary["violations"]))

    def test_duplicate_identity_rejected(self):
        summary = rb.validate_bundle(bundle_with(good_row(), good_row()))
        self.assertTrue(any("duplicate identity" in v for v in summary["violations"]))

    def test_exceptions_preserved_as_reviewable(self):
        summary = rb.validate_bundle(bundle_with(good_row()))
        self.assertEqual(summary["reviewable_exceptions"], [])
        exc = good_row(identity="1200 - X - E", decision="exception", ref_status="absent")
        summary2 = rb.validate_bundle(bundle_with(exc))
        self.assertEqual(summary2["violations"], [])
        self.assertEqual(summary2["reviewable_exceptions"], ["1200 - X - E"])


class TestIdentityBindingAndTimeBounds(unittest.TestCase):
    def test_unknown_identity_rejected(self):
        summary = rb.validate_bundle(bundle_with(good_row()), expected_identities={"9999 - Other - E"})
        self.assertTrue(any("not in the exported/candidate" in v for v in summary["violations"]))

    def test_silently_omitted_exported_identity_rejected(self):
        summary = rb.validate_bundle(
            bundle_with(good_row(identity="1100 - Cash - E")),
            expected_identities={"1100 - Cash - E", "1200 - Missing - E"},
        )
        self.assertTrue(any("silently omitted" in v for v in summary["violations"]))
        self.assertIn("1200 - Missing - E", summary["missing_identities"])

    def test_english_value_must_match_candidate(self):
        summary = rb.validate_bundle(
            bundle_with(good_row(identity="1100 - Cash - E")),
            expected_english={"1100 - Cash - E": "Cash"},
        )
        self.assertEqual(summary["violations"], [])
        summary2 = rb.validate_bundle(
            bundle_with(good_row(identity="1100 - Cash - E")),
            expected_english={"1100 - Cash - E": "Petty Cash"},
        )
        self.assertTrue(any("does not match the candidate" in v for v in summary2["violations"]))

    def test_future_timestamps_rejected(self):
        row = good_row()
        row["a2_review"]["provenance"]["reviewed_utc"] = "2999-01-01T00:00:00Z"
        summary = rb.validate_bundle(bundle_with(row), now_utc="2026-09-10T12:00:00Z")
        self.assertTrue(any("in the future" in v for v in summary["violations"]))


class TestGovernedManifestBoundary(unittest.TestCase):
    def test_public_entry_takes_no_manifest_path(self):
        import inspect

        params = set(inspect.signature(rb.build_import_payload).parameters)
        self.assertEqual(params, {"bundle", "now_utc"})
        # No caller-supplied path, object, mapping, or SHA is accepted.
        for banned in ("manifest_path", "candidate", "expected_identities", "expected_english", "expected_sha256"):
            self.assertNotIn(banned, params)
        with self.assertRaises(TypeError):
            rb.build_import_payload(bundle_with(good_row()), manifest_path="/tmp/forged.json")

    def test_governed_manifest_path_is_internal_and_fixed(self):
        path = rb._governed_manifest_path()
        self.assertTrue(path.endswith("construction/data/localization/stage4_export_manifest.json"))

    def test_production_entry_uses_governed_manifest(self):
        # No injection: the real governed manifest + real private export are
        # used, so a forged bundle identity cannot reach a payload.
        with self.assertRaises(rb.BundleError):
            rb.build_import_payload(bundle_with(good_row(identity="9999 - Forged - E")))

    def test_valid_flow_emits_payload_bound_to_manifest(self):
        manifest_path, export_path, sha = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        with inject_manifest(manifest_path):
            result = rb.build_import_payload(bundle_with(good_row()), now_utc="2026-09-10T12:00:00Z")
        self.assertEqual(result["payload"], [{"identity": "1100 - Cash - E", "arabic": "نقدية"}])
        self.assertEqual(result["manifest"]["candidate_export_sha256"], sha)
        self.assertEqual(result["manifest"]["candidate_export"], export_path)
        self.assertEqual(result["manifest"]["candidate_identity_count"], 1)

    def test_forged_identity_cannot_reach_payload(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row(identity="9999 - Forged - E")))

    def test_missing_manifest_rejected(self):
        with inject_manifest("/nonexistent/manifest.json"):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))

    def test_non_path_manifest_rejected(self):
        with inject_manifest({"export_sha256": "00" * 32}):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))

    def test_tampered_export_rejected(self):
        manifest_path, export_path, sha = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        Path(export_path).write_text(json.dumps(export_payload([export_row("1100 - Cash - E", "Forged")])), encoding="utf-8")
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))

    def test_manifest_sha_mismatch_rejected(self):
        manifest_path, export_path, sha = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        m["export_sha256"] = "00" * 32
        Path(manifest_path).write_text(json.dumps(m), encoding="utf-8")
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))

    def test_wrong_manifest_schema_rejected(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        m["schema"] = "other/v1"
        Path(manifest_path).write_text(json.dumps(m), encoding="utf-8")
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))

    def test_extra_and_missing_mapping_keys_rejected(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row(identity="1200 - Extra - E")))
        manifest_path2, _, _ = make_export_and_manifest(
            [export_row("1100 - Cash - E", "Cash"), export_row("1200 - X - E", "X")]
        )
        with inject_manifest(manifest_path2):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))

    def test_manifest_missing_export_path_rejected(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        del m["export_path"]
        Path(manifest_path).write_text(json.dumps(m), encoding="utf-8")
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()))


class TestMalformedNowUtcFailsClosed(unittest.TestCase):
    def test_malformed_now_utc_rejected(self):
        summary = rb.validate_bundle(bundle_with(good_row()), now_utc="not-a-date")
        self.assertTrue(any("now_utc is not a valid" in v for v in summary["violations"]))

    def test_payload_refused_on_malformed_now_utc(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(good_row()), now_utc="garbage")

    def test_valid_now_utc_still_rejects_future(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        row = good_row()
        row["a2_review"]["provenance"]["reviewed_utc"] = "2999-01-01T00:00:00Z"
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(row), now_utc="2026-09-10T12:00:00Z")


class TestImportPayloadFailClosed(unittest.TestCase):
    def test_payload_refused_on_any_violation(self):
        manifest_path, _, _ = make_export_and_manifest([export_row("1100 - Cash - E", "Cash")])
        row = good_row()
        row["a2_review"]["decision"] = None
        with inject_manifest(manifest_path):
            with self.assertRaises(rb.BundleError):
                rb.build_import_payload(bundle_with(row))

    def test_manifest_records_bundle_hash_and_exceptions(self):
        manifest_path, _, _ = make_export_and_manifest(
            [export_row("1100 - Cash - E", "Cash"), export_row("1300 - Y - E", "Cash")]
        )
        with inject_manifest(manifest_path):
            result = rb.build_import_payload(
                bundle_with(good_row(), good_row(identity="1300 - Y - E", decision="exception", ref_status="absent"))
            )
        self.assertTrue(result["manifest"]["bundle_sha256"])
        self.assertEqual(result["manifest"]["exception_count"], 1)
        self.assertIn("1300 - Y - E", result["manifest"]["reviewable_exceptions"])

    def test_rollback_note_documented(self):
        self.assertIn("Rollback", rb.rollback_note())


if __name__ == "__main__":
    unittest.main()
