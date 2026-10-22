"""Negative CLI matrix for the Stage-2 evidence protocol.

Every case drives the real CLIs as subprocesses and asserts that the invalid
invocation is REFUSED: a non-zero exit code and a failure message that names
the rejected input. Each case runs in its own subprocess invocation; no case
may inherit state from a previous one.

Covered:

  * unknown option, duplicated option, invalid option value,
  * both spellings: separated (``--flag value``) and inline (``--flag=value``),
  * a raw-command invocation and a wrong-site invocation are refused,
  * missing required metadata, duplicated metadata,
  * a stale metadata value, a mismatched hash, a mismatched command,
  * cross-invocation state: a failing invocation must not leave state behind
    for the next one (both CLIs reset their invocation state).

The evidence under test is the SYNTHETIC set produced by
``stage2_evidence_fixtures.py``; no real capture or real site is involved.

Run standalone:
    python3 construction/tests/tools/test_stage2_evidence_cli_matrix.py
"""

import json
import re
import shutil
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage2_evidence_fixtures as fx

WRONG_SITE = "v16-wrong-site.localhost"


class TestStage2EvidenceCliMatrix(unittest.TestCase):
    """Every invalid invocation must be refused, in its own subprocess."""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = fx.make_tmp_root("stage2-climatrix-")
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
        cls.captures = cls.tmp / fx.CAPTURES_DIRNAME
        cls.out_dir = cls.tmp / fx.OUTPUT_DIRNAME
        fx.build_captures(cls.captures, cls.checker, cls.candidate, cls.site)
        proc = fx.run_assembler(cls.candidate, cls.captures, cls.out_dir, cls.site)
        if proc.returncode != 0:
            raise AssertionError("assembler failed: " + proc.stdout + proc.stderr)
        cls.checker_path = cls.candidate / "scripts" / "check_localization_gates.py"
        cls.assembler_path = cls.candidate / "construction/tests/tools/stage2_evidence_assemble.py"

    @classmethod
    def tearDownClass(cls):
        fx.remove_tmp_root(getattr(cls, "tmp", None))

    # -- helpers ---------------------------------------------------------
    def checker_args(self, extra=(), evidence_dir=None, site=None):
        args = [f"--root={self.candidate}"]
        if evidence_dir is not None:
            args.append(f"--evidence-dir={evidence_dir}")
        if site is not None:
            args.append(f"--expected-evidence-site={site}")
        args.extend(extra)
        return args

    def assembler_args(self, extra=(), out_dir=None, site=None):
        args = [f"--captures={self.captures}", f"--out={out_dir or self.out_dir}"]
        if site is not None:
            args.append(f"--site={site}")
        args.extend(extra)
        return args

    def run_checker(self, extra=(), evidence_dir=None, site=None):
        cmd = [sys.executable, str(self.checker_path), *self.checker_args(extra, evidence_dir, site)]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.candidate))
        return proc, cmd

    def run_assembler(self, extra=(), out_dir=None, site=None):
        cmd = [sys.executable, str(self.assembler_path), *self.assembler_args(extra, out_dir, site)]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.candidate))
        return proc, cmd

    def assert_refused(self, proc, cmd, expected):
        """The invocation must fail and the message must name the rejected input."""
        output = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, f"expected refusal from {cmd}:\n{output}")
        self.assertTrue(
            expected in output,
            f"failure message must name {expected!r}:\n{output}",
        )

    def evidence_copy(self, name):
        """An isolated copy of the assembled evidence for one mutation case."""
        target = self.tmp / f"evidence-{name}"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(self.out_dir, target)
        return target

    def tampered_evidence(self, name, overrides):
        """Assemble a capture set whose captured numbers are deliberately wrong."""
        captures = self.tmp / f"captures-{name}"
        out_dir = self.tmp / f"evidence-{name}"
        shutil.rmtree(out_dir, ignore_errors=True)
        fx.build_captures(
            captures,
            self.checker,
            self.candidate,
            self.site,
            overrides=overrides,
        )
        proc = fx.run_assembler(self.candidate, captures, out_dir, self.site)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return out_dir

    # -- accepted spellings -------------------------------------------------
    def test_both_option_spellings_are_accepted(self):
        """The separated and the inline spelling must both work, for both CLIs."""
        checker_separated = [
            sys.executable,
            str(self.checker_path),
            "--root",
            str(self.candidate),
            "--evidence-dir",
            str(self.out_dir),
            "--expected-evidence-site",
            self.site,
            "--evidence-contract",
            "current",
        ]
        checker_inline = [
            sys.executable,
            str(self.checker_path),
            f"--root={self.candidate}",
            f"--evidence-dir={self.out_dir}",
            f"--expected-evidence-site={self.site}",
            "--evidence-contract=current",
        ]
        assembler_separated = [
            sys.executable,
            str(self.assembler_path),
            "--captures",
            str(self.captures),
            "--out",
            str(self.tmp / "evidence-spelling-separated"),
            "--site",
            self.site,
        ]
        assembler_inline = [
            sys.executable,
            str(self.assembler_path),
            f"--captures={self.captures}",
            f"--out={self.tmp / 'evidence-spelling-inline'}",
            f"--site={self.site}",
        ]
        for name, cmd in (
            ("checker-separated", checker_separated),
            ("checker-inline", checker_inline),
            ("assembler-separated", assembler_separated),
            ("assembler-inline", assembler_inline),
        ):
            with self.subTest(case=name):
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.candidate))
                output = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 0, f"{name} must be accepted:\n{output}")
                if name.startswith("checker"):
                    _, errors, error_count = fx.parse_checker_output(proc.stdout)
                    self.assertEqual(errors, [], output)
                    self.assertEqual(error_count, 0, output)

    def test_unknown_evidence_contract_is_refused(self):
        """An unknown contract name is refused by name; the default is never guessed."""
        for name, extra in (
            ("inline", ["--evidence-contract=bogus"]),
            ("separated", ["--evidence-contract", "bogus"]),
        ):
            with self.subTest(case=name):
                cmd = [
                    sys.executable,
                    str(self.checker_path),
                    f"--root={self.candidate}",
                    f"--evidence-dir={self.out_dir}",
                    f"--expected-evidence-site={self.site}",
                    *extra,
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.candidate))
                self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("--evidence-contract", proc.stdout + proc.stderr)

    # -- tampered counts ----------------------------------------------------
    def test_tampered_counts_are_refused(self):
        """A capture with a wrong number must be refused, not accepted."""
        gate = dict(self.checker.CURRENT_EXPECTED_GATE)
        cases = [
            ("tampered-catalog-count", {"gate": {"catalog": gate["catalog"] + 1}}),
            ("tampered-file-count", {"gate": {"files": gate["files"] + 1}}),
            ("tampered-wrapped-count", {"gate": {"wrapped": gate["wrapped"] + 1}}),
            ("tampered-json-labels-count", {"gate": {"json_labels": gate["json_labels"] + 1}}),
            ("tampered-missing-count", {"gate": {"missing": 1}}),
            (
                "tampered-module-count",
                {"module_counts": {"construction.tests.test_bilingual_service": 39}},
            ),
            (
                "tampered-module-count-self-consistent-aggregate",
                {"module_counts": {"construction.tests.test_stage4_report_extension": 15}},
            ),
            ("tampered-standalone-count", {"standalone_count": 95}),
            ("tampered-dryrun-total", {"dryrun": {"total": 4338, "skipped": 4338}}),
        ]
        for name, overrides in cases:
            with self.subTest(case=name):
                out_dir = self.tampered_evidence(name, overrides)
                proc, _cmd = self.run_checker(evidence_dir=out_dir, site=self.site)
                output = proc.stdout + proc.stderr
                self.assertNotEqual(proc.returncode, 0, f"{name} must be refused:\n{output}")
                _, errors, error_count = fx.parse_checker_output(proc.stdout)
                self.assertTrue(errors, f"{name} must produce an explicit error:\n{output}")
                self.assertNotEqual(error_count, 0, output)
                self.assertTrue(
                    any(
                        "contract" in e
                        or "arithmetic" in e
                        or "schema" in e
                        or "index" in e
                        or "artifact" in e
                        for e in errors
                    ),
                    f"{name} must name the rejected expectation: {errors}",
                )

    def test_tampered_artifact_hash_is_refused(self):
        """A capture whose artifact hash is not the live one must be refused."""
        out_dir = self.evidence_copy("tampered-artifact-hash")
        target = out_dir / "full-gate.txt"
        body = target.read_text(encoding="utf-8")
        target.write_text(
            re.sub(r"^PO_SHA256: [0-9a-f]{64}$", "PO_SHA256: " + "0" * 64, body, count=1, flags=re.M),
            encoding="utf-8",
        )
        proc, _cmd = self.run_checker(evidence_dir=out_dir, site=self.site)
        output = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, output)
        _, errors, _ = fx.parse_checker_output(proc.stdout)
        self.assertTrue(
            any("artifact" in e for e in errors),
            f"the wrong artifact hash must be named: {errors}",
        )

    def test_current_contract_rejects_the_legacy_expectation(self):
        """The current contract must not accept the historical numbers."""
        captures = self.tmp / "captures-legacy-contract"
        out_dir = self.tmp / "evidence-legacy-contract"
        fx.build_captures(
            captures,
            self.checker,
            self.candidate,
            self.site,
            contract="legacy",
        )
        proc = fx.run_assembler(self.candidate, captures, out_dir, self.site)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc, _cmd = self.run_checker(evidence_dir=out_dir, site=self.site)
        output = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, output)
        _, errors, _ = fx.parse_checker_output(proc.stdout)
        self.assertTrue(
            any("contract" in e for e in errors),
            f"the legacy expectation must be named: {errors}",
        )

    # -- CLI level cases -------------------------------------------------
    def test_cli_option_matrix_is_refused(self):
        """Unknown / duplicated / invalid options are refused, both spellings."""
        checker = lambda *extra, **kw: [  # noqa: E731
            sys.executable,
            str(self.checker_path),
            *self.checker_args(extra=list(extra), **kw),
        ]
        assembler = lambda *extra, **kw: [  # noqa: E731
            sys.executable,
            str(self.assembler_path),
            *self.assembler_args(extra=list(extra), **kw),
        ]
        cases = [
            (
                "checker-unknown-option-inline",
                checker("--not-a-real-option=1"),
                "--not-a-real-option",
            ),
            (
                "checker-unknown-option-separated",
                checker("--not-a-real-option"),
                "--not-a-real-option",
            ),
            (
                "checker-unknown-option-with-value",
                checker("--not-a-real-option", "value"),
                "--not-a-real-option",
            ),
            (
                "checker-raw-command-argument",
                checker("bench --site v16.localhost run-tests"),
                "bench --site v16.localhost run-tests",
            ),
            (
                "checker-duplicate-site-option-inline",
                checker(f"--expected-evidence-site={self.site}", site=self.site),
                "--expected-evidence-site",
            ),
            (
                "checker-duplicate-site-option-separated",
                checker("--expected-evidence-site", self.site, site=self.site),
                "--expected-evidence-site",
            ),
            (
                "checker-duplicate-evidence-dir",
                checker(f"--evidence-dir={self.out_dir}", evidence_dir=self.out_dir),
                "--evidence-dir",
            ),
            (
                "checker-empty-value-inline",
                checker("--evidence-dir="),
                "--evidence-dir",
            ),
            (
                "checker-empty-value-separated",
                checker("--evidence-dir", ""),
                "--evidence-dir",
            ),
            (
                "checker-missing-value",
                checker("--evidence-dir"),
                "--evidence-dir",
            ),
            (
                "assembler-unknown-option-inline",
                assembler("--not-a-real-option=1"),
                "--not-a-real-option",
            ),
            (
                "assembler-unknown-option-separated",
                assembler("--not-a-real-option"),
                "--not-a-real-option",
            ),
            (
                "assembler-raw-command-argument",
                assembler("bench --site v16.localhost console"),
                "bench --site v16.localhost console",
            ),
            (
                "assembler-duplicate-site-option-inline",
                assembler(f"--site={self.site}", f"--site={self.site}"),
                "--site",
            ),
            (
                "assembler-duplicate-site-option-separated",
                assembler("--site", self.site, "--site", self.site),
                "--site",
            ),
            (
                "assembler-duplicate-captures-option",
                assembler(f"--captures={self.captures}"),
                "--captures",
            ),
            (
                "assembler-empty-value-inline",
                assembler("--site="),
                "--site",
            ),
            (
                "assembler-empty-value-separated",
                assembler("--site", ""),
                "--site",
            ),
            (
                "assembler-missing-value",
                assembler("--site"),
                "--site",
            ),
        ]
        for name, cmd, expected in cases:
            with self.subTest(case=name):
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.candidate))
                self.assert_refused(proc, cmd, expected)

    def test_wrong_site_invocation_is_refused(self):
        """A foreign site is refused by both CLIs and names the site."""
        out_dir = self.tmp / "evidence-wrong-site"
        proc, cmd = self.run_assembler(extra=[f"--site={WRONG_SITE}"], out_dir=out_dir)
        self.assert_refused(proc, cmd, WRONG_SITE)
        self.assertIn("not the requested", proc.stdout + proc.stderr)
        # No envelope may be stamped with the foreign site.
        written = sorted(p.name for p in out_dir.glob("*.txt")) if out_dir.exists() else []
        self.assertEqual(written, [], "a refused assembly must not write envelopes")

        proc, cmd = self.run_checker(evidence_dir=self.out_dir, site=WRONG_SITE)
        self.assert_refused(proc, cmd, WRONG_SITE)

    # -- evidence metadata cases ----------------------------------------
    def test_evidence_metadata_matrix_is_refused(self):
        """Missing / duplicated / stale / mismatched evidence metadata is refused."""
        cases = []

        # missing required metadata: the SITE row of one envelope.
        missing_site = self.evidence_copy("missing-site")
        target = missing_site / "sync.txt"
        target.write_text(
            "\n".join(l for l in target.read_text(encoding="utf-8").splitlines() if not l.startswith("SITE:"))
            + "\n",
            encoding="utf-8",
        )
        cases.append(("missing-envelope-site-row", missing_site, "evidence-envelope-site"))

        # missing required metadata: the EVIDENCE_SITE row of the index.
        missing_index_site = self.evidence_copy("missing-index-site")
        target = missing_index_site / "index.txt"
        target.write_text(
            "\n".join(
                l
                for l in target.read_text(encoding="utf-8").splitlines()
                if not l.startswith("EVIDENCE_SITE:")
            )
            + "\n",
            encoding="utf-8",
        )
        cases.append(("missing-index-site-row", missing_index_site, "evidence-index-site"))

        # duplicated metadata: a second SITE row in one envelope.
        duplicate_site = self.evidence_copy("duplicate-site")
        target = duplicate_site / "sync.txt"
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                "SITE: " + self.site, "SITE: " + self.site + "\nSITE: " + self.site, 1
            ),
            encoding="utf-8",
        )
        cases.append(("duplicate-envelope-site-row", duplicate_site, "evidence-envelope-site"))

        # duplicated metadata: a second EVIDENCE_SITE row in the index.
        duplicate_index_site = self.evidence_copy("duplicate-index-site")
        target = duplicate_index_site / "index.txt"
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                "EVIDENCE_SITE: " + self.site,
                "EVIDENCE_SITE: " + self.site + "\nEVIDENCE_SITE: " + self.site,
                1,
            ),
            encoding="utf-8",
        )
        cases.append(("duplicate-index-site-row", duplicate_index_site, "evidence-index-site"))

        # stale metadata: an envelope timestamp older than the governed window.
        stale = self.evidence_copy("stale")
        target = stale / "sync.txt"
        target.write_text(
            re.sub(
                r"^STARTED_UTC: .*$",
                "STARTED_UTC: 2020-01-01T00:00:00Z",
                target.read_text(encoding="utf-8"),
                count=1,
                flags=re.M,
            ),
            encoding="utf-8",
        )
        cases.append(("stale-envelope-timestamp", stale, "evidence-stale"))

        # mismatched hash: the envelope no longer matches its index digest.
        tampered = self.evidence_copy("mismatched-hash")
        target = tampered / "full-gate.txt"
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                "NOTE: bootstrap run for envelope generation;",
                "NOTE: tampered envelope content;",
                1,
            ),
            encoding="utf-8",
        )
        cases.append(("mismatched-envelope-hash", tampered, "evidence-index-mismatch"))

        # mismatched command: the envelope records another command.
        wrong_command = self.evidence_copy("mismatched-command")
        target = wrong_command / "sync.txt"
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                "COMMAND: bench --site " + self.site + " console sync_translation_catalog(dry_run=False)",
                "COMMAND: echo forged",
                1,
            ),
            encoding="utf-8",
        )
        cases.append(("mismatched-envelope-command", wrong_command, "evidence-command"))

        for name, evidence_dir, expected in cases:
            with self.subTest(case=name):
                proc, cmd = self.run_checker(evidence_dir=evidence_dir, site=self.site)
                self.assert_refused(proc, cmd, expected)

    # -- cross invocation state -----------------------------------------
    def test_checker_state_is_reset_between_invocations(self):
        """A refused invocation must not leak its state into the next one."""
        driver = self.tmp / "checker_state_driver.py"
        scripts_dir = str(self.candidate / "scripts")
        driver.write_text(
            textwrap.dedent(
                f"""
                import json, sys
                sys.path.insert(0, {scripts_dir!r})
                import check_localization_gates as g

                code1, _, errors1 = g.main(
                    ["check", "--root={self.candidate}",
                     "--expected-evidence-site=first.example",
                     "--expected-evidence-site=second.example"]
                )
                state1 = {{
                    "site": g.EVIDENCE_SITE,
                    "required": g.EVIDENCE_SITE_REQUIRED,
                    "dir": g.EVIDENCE_DIR,
                }}
                code2, _, errors2 = g.main(
                    ["check", "--root={self.candidate}",
                     "--evidence-dir={self.out_dir}",
                     "--expected-evidence-site={self.site}"]
                )
                state2 = {{
                    "site": g.EVIDENCE_SITE,
                    "required": g.EVIDENCE_SITE_REQUIRED,
                    "dir": str(g.EVIDENCE_DIR),
                }}
                print("STATE " + json.dumps({{
                    "code1": code1, "errors1": errors1, "state1": state1,
                    "code2": code2, "errors2": errors2, "state2": state2,
                }}))
                """
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, str(driver)], capture_output=True, text=True, cwd=str(self.candidate)
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = None
        for line in proc.stdout.splitlines():
            if line.startswith("STATE "):
                payload = json.loads(line[len("STATE ") :])
        self.assertIsNotNone(payload, proc.stdout + proc.stderr)

        # The first invocation was refused for a duplicated option.
        self.assertEqual(payload["code1"], 1, payload)
        self.assertTrue(
            any("--expected-evidence-site" in e for e in payload["errors1"]),
            payload["errors1"],
        )
        # The refused invocation applied no site at all.
        self.assertFalse(payload["state1"]["required"], payload["state1"])
        self.assertIsNone(payload["state1"]["dir"], payload["state1"])

        # The second invocation inherited nothing and validated the evidence.
        self.assertEqual(payload["code2"], 0, payload["errors2"])
        self.assertEqual(payload["errors2"], [], payload["errors2"])
        self.assertEqual(payload["state2"]["site"], self.site, payload["state2"])
        self.assertTrue(payload["state2"]["required"], payload["state2"])
        self.assertEqual(payload["state2"]["dir"], str(self.out_dir), payload["state2"])

    def test_assembler_state_is_reset_between_invocations(self):
        """A refused assembly must not leak its site into the next invocation."""
        out_dir = self.tmp / "evidence-assembler-state"
        driver = self.tmp / "assembler_state_driver.py"
        driver.write_text(
            textwrap.dedent(
                f"""
                import importlib.util, json, sys

                spec = importlib.util.spec_from_file_location(
                    "assembler_under_test", {str(self.assembler_path)!r}
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                first = None
                mod._cli(["--site={WRONG_SITE}", "--captures={self.captures}", "--out={out_dir}"])
                try:
                    mod.main()
                except SystemExit as exc:
                    first = exc.code
                mod._cli(["--site={self.site}", "--captures={self.captures}", "--out={out_dir}"])
                mod.main()
                print("STATE " + json.dumps({{
                    "first": first,
                    "site": mod.EVIDENCE_SITE,
                    "written": sorted(p.name for p in __import__("pathlib").Path({str(out_dir)!r}).glob("*.txt")),
                }}))
                """
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, str(driver)], capture_output=True, text=True, cwd=str(self.candidate)
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = None
        for line in proc.stdout.splitlines():
            if line.startswith("STATE "):
                payload = json.loads(line[len("STATE ") :])
        self.assertIsNotNone(payload, proc.stdout + proc.stderr)

        # The foreign-site assembly was refused and stamped nothing.
        self.assertTrue(payload["first"], payload)
        self.assertIn(WRONG_SITE, str(payload["first"]), payload)
        # The next invocation started from its own site, not the refused one.
        self.assertEqual(payload["site"], self.site, payload)
        self.assertIn("sync.txt", payload["written"], payload)
        body = (out_dir / "sync.txt").read_text(encoding="utf-8")
        self.assertEqual([l for l in body.splitlines() if l.startswith("SITE:")], [f"SITE: {self.site}"])


if __name__ == "__main__":
    unittest.main()
