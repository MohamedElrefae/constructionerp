#!/usr/bin/env python3
"""Guard: the frozen evidence contract must still agree with the live source.

The frozen contract in ``scripts/check_localization_gates.py`` is a REVIEWED
input. It was frozen from executed measurements, and it is only trustworthy
while the source it was measured from is unchanged. Nothing in the checker
alone can prove that: the contract's own constants and the code they describe
are edited together, so a silent drift (a test added here, a message added
there) would leave the contract stale while every self-referential test still
passes.

This module proves the agreement with a SECOND, INDEPENDENT extraction. It
counts, straight from the source, every ``test_*`` method the loader would
collect in the required module set, without reading the evidence and without
reading the contract constants, and requires the frozen counts to agree with
it. When they diverge the guard fails and names the module, both numbers and
the required remedy (re-measure and re-review the contract).

It also proves that the dated review record still describes the code and the
committed raw artifacts, and that the historical (2026-09-29) expectation is
preserved verbatim, kept separate, and is never compared against the live
source.

Pure source analysis: no site, no vendor checkout, no network.
"""

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER_RELPATH = "scripts/check_localization_gates.py"
EXTRACTOR_RELPATH = "construction/tests/tools/stage2_measure_extract_counts.py"
RECORD_RELPATH = "construction/tests/tools/stage2_current_measurements.json"
HISTORICAL_INDEX_RELPATH = "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt"

# The historical expectation exactly as it was recorded on 2026-09-29. It is
# a historical artefact, not a live expectation: it is preserved verbatim and
# it is NEVER compared against the live source.
LEGACY_GATE = {"catalog": 817, "files": 265, "wrapped": 667, "json_labels": 29, "missing": 0}
LEGACY_MODULE_COUNTS = {
    "construction.searchable_dropdown.tests.test_search_api": 13,
    "construction.searchable_dropdown.tests.test_integration": 6,
    "construction.tests.test_bilingual_account_schema": 5,
    "construction.tests.test_translation_catalog": 3,
    "construction.tests.test_translation_stabilization_gates": 8,
    "construction.tests.test_localization_gates": 92,
    "construction.tests.test_bilingual_service": 38,
    "construction.tests.test_bilingual_account_pilot": 53,
    "construction.tests.test_stage4_account_language": 6,
    "construction.tests.test_stage4_report_extension": 11,
    "construction.tests.test_stage4_review_bundle": 36,
}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TestContractSourceAgreement(unittest.TestCase):
    """The frozen contract is verified against the live source and its record."""

    @classmethod
    def setUpClass(cls):
        cls.checker = _load(REPO_ROOT / CHECKER_RELPATH, "stage2_contract_checker")
        cls.extractor = _load(REPO_ROOT / EXTRACTOR_RELPATH, "stage2_contract_extractor")
        cls.record = json.loads((REPO_ROOT / RECORD_RELPATH).read_text(encoding="utf-8"))

    def live_module_counts(self):
        """Independent live extraction of the required module set."""
        counts = {}
        for module, _frozen in self.checker.CURRENT_EXPECTED_MODULES:
            path = REPO_ROOT / (module.replace(".", "/") + ".py")
            self.assertTrue(path.is_file(), f"required module source missing: {path}")
            total, _detail = self.extractor.module_test_count(path)
            counts[module] = total
        return counts

    # -- the drift guard ----------------------------------------------------
    def test_frozen_module_counts_match_an_independent_live_extraction(self):
        """The frozen counts must equal what the live source actually contains."""
        frozen = dict(self.checker.CURRENT_EXPECTED_MODULES)
        live = self.live_module_counts()
        drift = {
            module: (frozen[module], live[module])
            for module in sorted(frozen)
            if frozen[module] != live[module]
        }
        self.assertEqual(
            drift,
            {},
            "the frozen contract no longer matches the live source — re-measure and re-review "
            f"the contract ({self.checker.CURRENT_CONTRACT_ID}); "
            "frozen vs live: " + json.dumps(drift, sort_keys=True),
        )
        self.assertEqual(sum(frozen.values()), sum(live.values()))

    def test_the_frozen_module_set_is_the_required_set(self):
        """The contract must cover the whole required module set, not a subset."""
        self.assertEqual(len(self.checker.CURRENT_EXPECTED_MODULES), 11)
        self.assertEqual(
            sorted(dict(self.checker.CURRENT_EXPECTED_MODULES)),
            sorted(self.extractor.MODULES),
            "the frozen module set and the independently extracted module set differ",
        )

    # -- the reviewed record ------------------------------------------------
    def test_the_reviewed_record_matches_the_contract_constants(self):
        """The dated record must describe the contract that is actually frozen."""
        frozen = self.record["frozen_contract_from_these_measurements"]
        self.assertEqual(frozen["contract_id"], self.checker.CURRENT_CONTRACT_ID)
        self.assertEqual(frozen["gate"], self.checker.CURRENT_EXPECTED_GATE)
        self.assertEqual(
            frozen["modules"],
            dict(self.checker.CURRENT_EXPECTED_MODULES),
            "the record and the checker disagree",
        )
        self.assertEqual(
            frozen["module_aggregate"], sum(dict(self.checker.CURRENT_EXPECTED_MODULES).values())
        )
        self.assertEqual(frozen["source_pins"], self.checker.CURRENT_SOURCE_PINS)

    def test_the_recorded_raw_artifacts_are_still_intact(self):
        """Every artifact the record cites must still hash to the recorded digest."""
        checked = 0
        for measurement in self.record["measurements"]:
            artifacts = measurement.get("artifacts")
            if artifacts is None and measurement.get("artifact"):
                artifacts = [{"file": measurement["artifact"], "sha256": measurement["artifact_sha256"]}]
            for artifact in artifacts or []:
                path = REPO_ROOT / artifact["file"]
                self.assertTrue(path.is_file(), f"recorded artifact missing: {artifact['file']}")
                self.assertEqual(
                    _sha256(path),
                    artifact["sha256"],
                    f"recorded artifact changed: {artifact['file']}",
                )
                checked += 1
        self.assertGreater(checked, 0, "the record cites no artifact at all")

    def test_the_record_is_labelled_current_and_keeps_the_historical_set_separate(self):
        """The CURRENT record must not present itself as the historical evidence."""
        self.assertIn("CURRENT", self.record["record_kind"])
        self.assertIn("not_a_historical_record", self.record)
        historical_index = REPO_ROOT / HISTORICAL_INDEX_RELPATH
        self.assertTrue(historical_index.is_file(), "the historical evidence index is missing")
        historical_text = historical_index.read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_ROOT: /home/mohamed/frappe-bench/apps/construction", historical_text)
        self.assertIn("CANDIDATE_HEAD: 4123646bd8b7016abad8c276cea36a58d6cbfb3a", historical_text)
        # The CURRENT record must not claim the historical root or the
        # historical HEAD as its own.
        self.assertNotIn(
            "/home/mohamed/frappe-bench/apps/construction",
            json.dumps(self.record["environment"].get("root", "")),
        )

    # -- the historical expectation is preserved, not compared --------------
    def test_the_legacy_expectation_is_preserved_verbatim(self):
        """The historical expectation stays reachable and unchanged."""
        self.assertEqual(self.checker.LEGACY_EXPECTED_GATE, LEGACY_GATE)
        self.assertEqual(dict(self.checker.LEGACY_EXPECTED_MODULES), LEGACY_MODULE_COUNTS)
        self.assertEqual(sum(LEGACY_MODULE_COUNTS.values()), 271)
        self.assertEqual(self.checker.LEGACY_SOURCE_PINS, {})
        legacy = self.record["historical_expectation_kept_separate"]
        self.assertEqual(legacy["contract_id"], self.checker.LEGACY_CONTRACT_ID)
        self.assertEqual(legacy["gate"], LEGACY_GATE)
        self.assertEqual(legacy["modules"], LEGACY_MODULE_COUNTS)

    def test_the_legacy_expectation_is_not_the_live_source(self):
        """The legacy numbers are historical: they must differ from the live source.

        This is the explicit statement that the two contracts are not
        interchangeable and that only the CURRENT contract describes the live
        source.
        """
        live = self.live_module_counts()
        legacy = dict(self.checker.LEGACY_EXPECTED_MODULES)
        self.assertNotEqual(legacy, live, "the legacy expectation silently became the live source")
        self.assertNotEqual(self.checker.LEGACY_EXPECTED_GATE, self.checker.CURRENT_EXPECTED_GATE)

    # -- the source pins ----------------------------------------------------
    def test_the_contract_source_pins_match_the_live_files(self):
        """A drifted pinned source invalidates the frozen counts."""
        self.assertTrue(self.checker.CURRENT_SOURCE_PINS)
        for rel, want in sorted(self.checker.CURRENT_SOURCE_PINS.items()):
            path = REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"contract-pinned source missing: {rel}")
            self.assertEqual(
                _sha256(path),
                want,
                f"contract-pinned source drifted: {rel} — re-measure and re-review the contract",
            )


if __name__ == "__main__":
    unittest.main()
