import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

CHECKER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_semgrep_review_ledger.py"
CHECKER_SPEC = importlib.util.spec_from_file_location("check_semgrep_review_ledger", CHECKER_PATH)
check_ledger = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(check_ledger)


class LedgerCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = "doctype.json"
        (self.root / self.source).write_text(json.dumps({"permissions": [{"read": 1, "role": "All"}]}))
        for path, content in (
            ("guard.py", "def guard(): return True\n"),
            ("test_guard.py", "def test_guard(): assert True\n"),
            (
                "construction/tests/test_native_security_rest_authorization.py",
                "def test_rest(): assert True\n",
            ),
        ):
            target_path = self.root / path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content)
        self.finding = {
            "check_id": "relaxed-permissions",
            "path": self.source,
            "start": {"line": 1, "col": 1, "offset": 0},
            "end": {"line": 1, "col": 9, "offset": 8},
        }
        self.inventory = [
            {
                "finding": copy.deepcopy(self.finding),
                "permission_index": 0,
                "canonical_fields": {"read": 1, "role": "All"},
            }
        ]
        self.raw = {"results": [copy.deepcopy(self.finding)], "errors": []}
        self.ledger = {
            "schema_version": 1,
            "required_targets": [copy.deepcopy(self.finding)],
            "entries": [self._entry()],
        }

    def tearDown(self):
        self.temp.cleanup()

    def _sha(self, path):
        return hashlib.sha256((self.root / path).read_bytes()).hexdigest()

    def _entry(self):
        entry = {
            "finding": copy.deepcopy(self.finding),
            "source_sha256": self._sha(self.source),
            "permission_record": {
                "document_path": self.source,
                "index": 0,
                "canonical_fields_sha256": check_ledger.canonical_permission_fields_sha256(
                    {"read": 1, "role": "All"}
                ),
            },
            "guards": [{"path": "guard.py", "sha256": self._sha("guard.py")}],
            "tests": [
                {
                    "path": "construction/tests/test_native_security_rest_authorization.py",
                    "sha256": self._sha("construction/tests/test_native_security_rest_authorization.py"),
                },
                {"path": "test_guard.py", "sha256": self._sha("test_guard.py")},
            ],
            "status": "REVIEWED",
            "decision": "ACCEPT",
            "review_gate": {
                "parent_review_id": "review-1",
                "combined_qualification_id": "local-qualification-1",
                "combined_qualification_sha256": "c" * 64,
                "reviewed_source_manifest_sha256": None,
                "native_rest_run_id": "native-rest-1",
                "native_rest_log_sha256": "a" * 64,
            },
        }
        entry["review_gate"]["reviewed_source_manifest_sha256"] = (
            check_ledger.reviewed_source_manifest_sha256(entry)
        )
        return entry

    def check(self, raw=None, ledger=None, scanner_exit=0, inventory=None):
        return check_ledger.validate(
            self.raw if raw is None else raw,
            scanner_exit,
            self.ledger if ledger is None else ledger,
            self.root,
            inventory=self.inventory if inventory is None else inventory,
        )

    def test_exact_reviewed_finding_is_accepted(self):
        report = self.check()
        self.assertEqual(
            (
                report["exit_code"],
                report["raw_findings_total"],
                report["reviewed_findings"],
                report["unresolved_findings"],
            ),
            (0, 1, 1, 0),
        )

    def test_new_unledgered_finding_is_unresolved(self):
        raw = copy.deepcopy(self.raw)
        new = copy.deepcopy(self.finding)
        new["start"]["line"] = 2
        new["start"]["offset"] = 10
        new["end"]["line"] = 2
        new["end"]["offset"] = 18
        raw["results"].append(new)
        report = self.check(raw=raw)
        self.assertEqual(
            (report["reviewed_findings"], report["unresolved_findings"], report["exit_code"]), (1, 1, 1)
        )

    def test_ledger_cannot_replace_pinned_target_even_if_targets_and_entries_change(self):
        ledger = copy.deepcopy(self.ledger)
        changed = copy.deepcopy(self.finding)
        changed["path"] = "other.json"
        (self.root / "other.json").write_text(json.dumps({"permissions": [{"read": 1, "role": "All"}]}))
        ledger["required_targets"] = [copy.deepcopy(changed)]
        replacement = self._entry()
        replacement.update({"finding": copy.deepcopy(changed), "source_sha256": self._sha("other.json")})
        replacement["permission_record"]["document_path"] = "other.json"
        ledger["entries"] = [replacement]
        report = self.check(ledger=ledger)
        self.assertEqual(report["exit_code"], 1)
        self.assertTrue(any("independently pinned" in error for error in report["ledger_errors"]))

    def test_source_and_permission_record_tampering_are_rejected(self):
        (self.root / self.source).write_text('{"permissions": []}')
        report = self.check()
        self.assertIn("source SHA-256 mismatch", report["unresolved"][0]["reason"])

        ledger = copy.deepcopy(self.ledger)
        ledger["entries"][0]["permission_record"]["index"] = 9
        report = self.check(ledger=ledger)
        self.assertIn(
            "permission record index/canonical fields differ from pinned inventory",
            report["unresolved"][0]["reason"],
        )

        ledger = copy.deepcopy(self.ledger)
        ledger["entries"][0]["permission_record"]["canonical_fields_sha256"] = "0" * 64
        report = self.check(ledger=ledger)
        self.assertIn(
            "permission record index/canonical fields differ from pinned inventory",
            report["unresolved"][0]["reason"],
        )

    def test_guard_and_test_hash_tampering_are_rejected(self):
        for ref_name in ("guards", "tests"):
            with self.subTest(ref=ref_name):
                ledger = copy.deepcopy(self.ledger)
                ledger["entries"][0][ref_name][0]["sha256"] = "0" * 64
                report = self.check(ledger=ledger)
                self.assertEqual(report["exit_code"], 1)
                self.assertIn("file SHA-256 mismatch", report["unresolved"][0]["reason"])

    def test_reviewed_source_manifest_mismatch_is_rejected(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["entries"][0]["review_gate"]["reviewed_source_manifest_sha256"] = "b" * 64
        report = self.check(ledger=ledger)
        self.assertEqual(report["exit_code"], 1)
        self.assertIn("source manifest SHA-256 mismatch", report["unresolved"][0]["reason"])

    def test_reviewed_requires_local_qualification_id_and_valid_digest(self):
        for field, value in (
            ("combined_qualification_id", None),
            ("combined_qualification_sha256", "not-a-sha256"),
        ):
            with self.subTest(field=field):
                ledger = copy.deepcopy(self.ledger)
                ledger["entries"][0]["review_gate"][field] = value
                report = self.check(ledger=ledger)
                self.assertEqual(report["exit_code"], 1)
                reason = report["unresolved"][0]["reason"]
                self.assertIn("local qualification", reason)
                if field == "combined_qualification_sha256":
                    self.assertIn("qualification SHA-256", reason)

    def test_scanner_errors_and_nonzero_exit_are_rejected(self):
        raw = copy.deepcopy(self.raw)
        raw["errors"] = [{"message": "scan failed"}]
        report = self.check(raw=raw)
        self.assertEqual(report["exit_code"], 1)
        report = self.check(scanner_exit=1)
        self.assertEqual(report["exit_code"], 1)
        self.assertTrue(any("without --error" in error for error in report["ledger_errors"]))

    def test_cli_rejects_malformed_raw_or_ledger_json(self):
        raw_path = self.root / "raw.json"
        ledger_path = self.root / "ledger.json"
        raw_path.write_text("not-json")
        ledger_path.write_text(json.dumps(self.ledger))
        for broken_path, contents in ((raw_path, "not-json"), (ledger_path, "{")):
            with self.subTest(path=broken_path.name):
                broken_path.write_text(contents)
                args = [
                    "check_semgrep_review_ledger.py",
                    "--raw-semgrep-json",
                    str(raw_path),
                    "--scanner-exit",
                    "0",
                    "--review-ledger",
                    str(ledger_path),
                    "--candidate-root",
                    str(self.root),
                ]
                output = io.StringIO()
                with patch.object(sys, "argv", args), redirect_stdout(output):
                    self.assertEqual(check_ledger.main(), 1)
                self.assertEqual(json.loads(output.getvalue())["exit_code"], 1)

    def test_stale_extra_and_missing_entries_are_rejected(self):
        ledger = copy.deepcopy(self.ledger)
        extra = copy.deepcopy(ledger["entries"][0])
        extra["finding"]["start"]["line"] = 99
        extra["finding"]["start"]["offset"] = 100
        extra["finding"]["end"]["line"] = 99
        extra["finding"]["end"]["offset"] = 108
        ledger["entries"].append(extra)
        report = self.check(ledger=ledger)
        self.assertTrue(any("stale/extra" in error for error in report["ledger_errors"]))

        ledger = copy.deepcopy(self.ledger)
        ledger["entries"].clear()
        report = self.check(ledger=ledger)
        self.assertTrue(any("missing" in error for error in report["ledger_errors"]))

    def test_noncanonical_alias_and_reversed_span_are_rejected(self):
        finding = copy.deepcopy(self.finding)
        finding["path"] = "./doctype.json"
        with self.assertRaises(ValueError):
            check_ledger.identity(finding)
        finding = copy.deepcopy(self.finding)
        finding["start"].update({"line": 1, "col": 2, "offset": 1})
        finding["end"].update({"line": 1, "col": 1, "offset": 2})
        with self.assertRaises(ValueError):
            check_ledger.identity(finding)

    def test_five_real_records_are_reviewed_and_strictly_bound(self):
        template_path = (
            Path(__file__).resolve().parents[1] / ".github" / "security" / "semgrep_review_ledger.json"
        )
        ledger = json.loads(template_path.read_text())
        self.assertEqual(len(ledger["entries"]), 5)
        self.assertTrue(all(entry["status"] == "REVIEWED" for entry in ledger["entries"]))
        self.assertTrue(all(entry["decision"] == "ACCEPT" for entry in ledger["entries"]))
        self.assertTrue(all(entry["guards"] and entry["tests"] for entry in ledger["entries"]))
        for entry in ledger["entries"]:
            with self.subTest(path=entry["finding"]["path"]):
                self.assertEqual(
                    entry["review_gate"]["reviewed_source_manifest_sha256"],
                    check_ledger.reviewed_source_manifest_sha256(entry),
                )

        raw = {"results": [copy.deepcopy(entry["finding"]) for entry in ledger["entries"]], "errors": []}
        report = check_ledger.validate(raw, 0, ledger, Path(__file__).resolve().parents[1])
        self.assertEqual(
            (
                report["raw_findings_total"],
                report["reviewed_findings"],
                report["unresolved_findings"],
                report["exit_code"],
            ),
            (5, 5, 0, 0),
        )
        self.assertEqual(report["ledger_errors"], [])

    def test_synthetic_pending_record_remains_fail_closed(self):
        template_path = (
            Path(__file__).resolve().parents[1] / ".github" / "security" / "semgrep_review_ledger.json"
        )
        ledger = json.loads(template_path.read_text())
        ledger["entries"][0]["status"] = "PENDING"
        ledger["entries"][0]["decision"] = None
        raw = {"results": [copy.deepcopy(entry["finding"]) for entry in ledger["entries"]], "errors": []}
        report = check_ledger.validate(raw, 0, ledger, Path(__file__).resolve().parents[1])
        self.assertEqual(
            (
                report["raw_findings_total"],
                report["reviewed_findings"],
                report["unresolved_findings"],
                report["exit_code"],
            ),
            (5, 4, 1, 1),
        )
        self.assertIn("manual-review entry is PENDING", report["unresolved"][0]["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
