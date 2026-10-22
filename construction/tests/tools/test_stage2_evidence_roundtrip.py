"""Subprocess round trip: synthetic captures -> assembler -> checker.

The test drives the real CLIs as subprocesses over a throw-away directory
tree that contains three DISTINCT trees:

  * ``synthetic-captures``     — synthetic raw capture inputs,
  * ``synthetic-evidence-out`` — the assembler's output (external),
  * ``synthetic-bench/apps/construction`` — the candidate root the checker reads.

Every capture is a labelled SYNTHETIC TEST FIXTURE (see
``stage2_evidence_fixtures.py``); nothing here is a real capture of a real
site run and nothing is written outside the temporary tree.

Run standalone:
    python3 construction/tests/tools/test_stage2_evidence_roundtrip.py
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage2_evidence_fixtures as fx


class TestStage2EvidenceRoundTrip(unittest.TestCase):
    """assembler (subprocess) -> checker (subprocess) over synthetic captures."""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = fx.make_tmp_root("stage2-roundtrip-")
        cls.repo_root = fx.REPO_ROOT
        cls.pins = fx.vendor_pins(cls.repo_root)
        try:
            cls.required_inputs = {
                app: {rel: spec["sha256"] for rel, spec in sorted(inputs["inputs"].items())}
                for app, inputs in fx.load_required_vendor_inputs(cls.repo_root).items()
            }
        except fx.VendorInputsUnavailable as exc:
            fx.remove_tmp_root(cls.tmp)
            if fx.ci_mode():
                # A required CI run must FAIL when a mandatory pinned input is
                # absent; it must never skip and report green.
                raise AssertionError(f"CI mode: {exc}") from exc
            raise unittest.SkipTest(f"LOCAL UNIT LAYER (skipped): {exc}") from exc
        cls.vendor_apps = fx.find_vendor_apps(cls.repo_root, cls.pins, cls.required_inputs)
        if cls.vendor_apps is None:
            problems = fx.vendor_input_problems(cls.repo_root, cls.pins, cls.required_inputs)
            fx.remove_tmp_root(cls.tmp)
            if fx.ci_mode():
                # A required CI run must FAIL when the pinned vendor inputs are
                # missing; it must never skip and report green.
                raise AssertionError(
                    "CI mode: the pinned vendor inputs are required and are not available:\n  - "
                    + "\n  - ".join(problems)
                )
            raise unittest.SkipTest(
                "LOCAL UNIT LAYER (skipped): no bench-shaped vendor checkout with the pinned "
                "frappe/erpnext commits and pinned input bytes is available; set "
                "STAGE2_VENDOR_APPS_DIR to a mirror to run this layer:\n  - " + "\n  - ".join(problems)
            )
        cls.candidate, cls.head = fx.build_candidate_root(cls.tmp, cls.repo_root, cls.vendor_apps)
        cls.checker = fx.load_checker(cls.candidate)
        cls.site = json.loads(
            (cls.candidate / "construction/data/localization/site_classification.json").read_text(
                encoding="utf-8"
            )
        )["site"]
        assert cls.site not in fx.PROTECTED_SITES, "the round trip must not use a protected site"
        cls.captures = cls.tmp / fx.CAPTURES_DIRNAME
        cls.out_dir = cls.tmp / fx.OUTPUT_DIRNAME
        cls.content_captures, cls.stamp_captures = fx.build_captures(
            cls.captures, cls.checker, cls.candidate, cls.site
        )

    @classmethod
    def tearDownClass(cls):
        fx.remove_tmp_root(getattr(cls, "tmp", None))

    def test_required_vendor_inputs_are_present_and_pinned(self):
        """The vendor tree the protocol runs against is the pinned one."""
        self.assertIsNotNone(self.vendor_apps, "a pinned vendor checkout is required")
        for app, inputs in sorted(self.required_inputs.items()):
            for rel, want in sorted(inputs.items()):
                path = Path(self.vendor_apps) / app / rel
                self.assertTrue(path.is_file(), f"missing required vendor input {app}/{rel}")
                self.assertEqual(fx.sha256_file(path), want, f"vendor input {app}/{rel} drifted")

    def test_three_distinct_trees_are_used(self):
        self.assertTrue(self.captures.is_dir())
        self.assertTrue(self.candidate.is_dir())
        self.assertNotEqual(self.captures, self.out_dir)
        self.assertNotEqual(self.captures, self.candidate)
        self.assertNotEqual(self.out_dir, self.candidate)
        self.assertNotIn(str(self.repo_root), str(self.captures))
        self.assertNotIn(str(self.repo_root), str(self.out_dir))

    def test_every_capture_is_labelled_synthetic(self):
        manifest = self.captures / fx.FIXTURE_MANIFEST
        self.assertTrue(manifest.is_file(), "the capture directory must declare itself synthetic")
        self.assertIn(fx.SYNTHETIC_MARKER, manifest.read_text(encoding="utf-8"))
        for name in self.content_captures:
            text = (self.captures / name).read_text(encoding="utf-8")
            self.assertIn(
                fx.SYNTHETIC_MARKER,
                text,
                f"capture {name} must carry the synthetic-fixture marker",
            )
        self.assertTrue(self.stamp_captures, "timestamp sidecars must exist")
        for name in self.stamp_captures:
            self.assertIn(name, manifest.read_text(encoding="utf-8"))

    def test_assembler_writes_the_ten_envelopes_and_index(self):
        proc = fx.run_assembler(self.candidate, self.captures, self.out_dir, self.site)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for name in self.checker.EVIDENCE_FILES:
            self.assertTrue((self.out_dir / name).is_file(), f"missing envelope {name}")
        self.assertTrue((self.out_dir / "index.txt").is_file())

    def test_round_trip_is_bound_to_the_tested_head_and_validates(self):
        proc = fx.run_assembler(self.candidate, self.captures, self.out_dir, self.site)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        index_text = (self.out_dir / "index.txt").read_text(encoding="utf-8")
        # The evidence is bound to the immutable tested HEAD of the checkout.
        self.assertIn(f"CANDIDATE_HEAD: {self.head}", index_text)
        self.assertIn(f"CANDIDATE_ROOT: {self.candidate.resolve()}", index_text)
        self.assertIn(f"EVIDENCE_SITE: {self.site}", index_text)

        # Every envelope carries exactly one SITE row for the expected site.
        for name in self.checker.EVIDENCE_FILES:
            body = (self.out_dir / name).read_text(encoding="utf-8")
            site_rows = [line for line in body.splitlines() if line.startswith("SITE:")]
            self.assertEqual(site_rows, [f"SITE: {self.site}"], f"{name} site rows")

        check = fx.run_checker(self.candidate, self.out_dir, self.site)
        stdout = check.stdout + check.stderr
        counts, errors, error_count = fx.parse_checker_output(check.stdout)
        self.assertEqual(check.returncode, 0, stdout)
        self.assertEqual(errors, [], stdout)
        self.assertEqual(error_count, 0, stdout)
        self.assertIn("construction/locale/ar.po", counts)

    def test_checker_rejects_the_same_captures_for_another_site(self):
        """The bound site is not interchangeable: a foreign expectation fails."""
        proc = fx.run_assembler(self.candidate, self.captures, self.out_dir, self.site)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        check = fx.run_checker(self.candidate, self.out_dir, "v16-wrong-site.localhost")
        stdout = check.stdout + check.stderr
        _, errors, _ = fx.parse_checker_output(check.stdout)
        self.assertEqual(check.returncode, 1, stdout)
        self.assertTrue(errors, stdout)
        self.assertTrue(
            any("site" in e.lower() for e in errors),
            f"the rejected site must be named: {errors}",
        )

    def test_current_contract_is_pinned_to_the_live_source_artifacts(self):
        """The frozen contract is tied to real source artifacts, not to a number."""
        self.assertTrue(self.checker.CURRENT_SOURCE_PINS, "the current contract must pin its sources")
        for rel, want in sorted(self.checker.CURRENT_SOURCE_PINS.items()):
            path = Path(self.repo_root) / rel
            self.assertTrue(path.is_file(), f"contract-pinned source missing: {rel}")
            self.assertEqual(
                fx.sha256_file(path),
                want,
                f"contract-pinned source drifted: {rel} — re-measure and re-review the contract",
            )

    def test_legacy_contract_still_validates_the_historical_expectation(self):
        """The historical (2026-09-29) expectation is preserved and reachable."""
        legacy_captures = self.tmp / "legacy-captures"
        legacy_out = self.tmp / "legacy-evidence-out"
        fx.build_captures(
            legacy_captures,
            self.checker,
            self.candidate,
            self.site,
            contract="legacy",
        )
        proc = fx.run_assembler(self.candidate, legacy_captures, legacy_out, self.site)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        legacy = fx.run_checker(
            self.candidate, legacy_out, self.site, extra_args=["--evidence-contract=legacy"]
        )
        stdout = legacy.stdout + legacy.stderr
        _, errors, error_count = fx.parse_checker_output(legacy.stdout)
        self.assertEqual(legacy.returncode, 0, stdout)
        self.assertEqual(errors, [], stdout)
        self.assertEqual(error_count, 0, stdout)

        # The very same evidence must NOT pass under the current contract:
        # the two expectations are distinct and neither is inferred.
        current = fx.run_checker(self.candidate, legacy_out, self.site)
        current_stdout = current.stdout + current.stderr
        _, current_errors, _ = fx.parse_checker_output(current.stdout)
        self.assertEqual(current.returncode, 1, current_stdout)
        self.assertTrue(
            any("contract" in e for e in current_errors),
            f"the legacy expectation must be rejected by the current contract: {current_errors}",
        )


if __name__ == "__main__":
    unittest.main()
