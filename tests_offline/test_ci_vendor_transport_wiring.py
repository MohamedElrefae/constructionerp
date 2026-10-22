"""Guard the CI wiring that binds every gate-consuming job to the private vendor.

P13-CI-003 regression guard. Narrow and offline: reads the shipped workflow text
and the reviewed transport records only. No YAML library, no git, no network.

The invariants below are what makes the private Frappe v16 / Pillow 13 candidate
reviewable:

* the PUBLIC base commit is the only thing any job fetches; the unpublished
  private commit appears only as an assertion, never as a `ref:`/fetch target;
* every job that runs the localization source gate first reconstructs and
  verifies the exact private vendor commit (never the upstream base);
* the recorded vendor baseline pin is the private commit, with truthful
  coordinator-review provenance and no fabricated human approval;
* the sparse catalog checkout still materialises the transport patch target, so
  the tree reconstruction is not silently degraded;
* the pre-existing required checks (pre-commit, scope lint, Semgrep, real
  pip-audit) are still present and no `--update-baselines` shortcut exists.
"""

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
TRANSPORT = ROOT / ".github" / "ci"
PATCHES = TRANSPORT / "vendor_patches"
IDENTITY_PATH = PATCHES / "frappe-pillow13-vendor-divergence.json"
BASELINE_PATH = ROOT / "construction" / "data" / "localization" / "vendor_catalog_baseline.json"

BASE_COMMIT = "2871914b69b6e14a4b023d9b7cc52dc3e269cc1b"
EFFECTIVE_COMMIT = "af44091716ed4e9be32720483a27d3f1937ad7fd"
EFFECTIVE_TREE = "231f1d8b87171dfc6fcedb1ae320195953539c34"
ERPNEXT_COMMIT = "7474d9e786277383de1242ab882f16856d17a9c9"

APPLIER = "apply_private_vendor_divergence.py"
SOURCE_GATE = "scripts/check_localization_gates.py --ci-source-only"

STEP_START = re.compile(r"^      - ", re.MULTILINE)


def read(path):
    return path.read_text(encoding="utf-8")


def workflow_texts():
    return {p.name: read(p) for p in sorted(WORKFLOWS.glob("*.yml"))}


def steps(text):
    marks = [m.start() for m in STEP_START.finditer(text)]
    return [text[a:b] for a, b in zip(marks, marks[1:] + [len(text)], strict=True)]


def step(text, heading):
    hits = [s for s in steps(text) if heading in s.splitlines()[0]]
    assert len(hits) == 1, f"expected exactly one step containing {heading!r}, got {len(hits)}"
    return hits[0]


def step_index(text, heading):
    for index, block in enumerate(steps(text)):
        if heading in block.splitlines()[0]:
            return index
    raise AssertionError(f"step {heading!r} not found")


def job(text, name):
    """Return one top-level job block (2-space indented keys, 6-space steps)."""
    start = text.index(f"  {name}:")
    rest = text[start:]
    following = re.search(r"^  [A-Za-z0-9_-]+:$", rest[1:], re.MULTILINE)
    return rest if following is None else rest[: following.start() + 1]


class TransportIdentityTest(unittest.TestCase):
    def setUp(self):
        self.identity = json.loads(read(IDENTITY_PATH))

    def test_identity_record_matches_the_shipped_bytes(self):
        identity = self.identity
        self.assertEqual(identity["base_commit"], BASE_COMMIT)
        self.assertEqual(identity["effective_commit"], EFFECTIVE_COMMIT)
        self.assertEqual(identity["effective_commit_tree"], EFFECTIVE_TREE)
        self.assertEqual(identity["effective_commit_parent"], BASE_COMMIT)
        patch = PATCHES / identity["patch_file"]
        commit_object = PATCHES / identity["commit_object_file"]
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), identity["patch_sha256"])
        self.assertEqual(
            hashlib.sha256(commit_object.read_bytes()).hexdigest(),
            identity["commit_object_sha256"],
        )
        self.assertEqual(commit_object.stat().st_size, identity["commit_object_bytes"])
        header = commit_object.read_text(encoding="utf-8").splitlines()[:2]
        self.assertEqual(header[0], f"tree {EFFECTIVE_TREE}")
        self.assertEqual(header[1], f"parent {BASE_COMMIT}")

    def test_patch_changes_only_the_declared_file(self):
        identity = self.identity
        patch = read(PATCHES / identity["patch_file"])
        targets = {line[len("+++ b/") :].strip() for line in patch.splitlines() if line.startswith("+++ b/")}
        self.assertEqual(targets, {identity["patched_file"]})
        self.assertIn('+    "Pillow~=13.0.0",', patch)
        self.assertIn('-    "Pillow~=12.3.0",', patch)

    def test_recorded_baseline_pin_is_the_private_commit(self):
        baseline = json.loads(read(BASELINE_PATH))
        frappe = baseline["apps"]["frappe"]
        self.assertEqual(frappe["commit"], EFFECTIVE_COMMIT)
        self.assertEqual(frappe["commit"], self.identity["effective_commit"])
        self.assertEqual(baseline["apps"]["erpnext"]["commit"], ERPNEXT_COMMIT)
        # The catalog inventory is untouched by the divergence: the baseline PO
        # digest must still equal the digest the stage-2 fixture pins record.
        fixtures = json.loads(
            read(ROOT / "construction" / "data" / "localization" / "vendor_ci_inputs.json")
        )["apps"]["frappe"]["inputs"]["frappe/locale/ar.po"]["sha256"]
        self.assertEqual(frappe["po_sha"], fixtures)

    def test_baseline_provenance_is_truthful(self):
        frappe = json.loads(read(BASELINE_PATH))["apps"]["frappe"]
        review = frappe["commit_pin_review"]
        self.assertTrue(review["recorded_utc"].endswith("Z"))
        self.assertIn("NOT human approval", review["authority"])
        self.assertIn("coordinator", review["authority"].lower())
        self.assertIn("catalog_delta", review)
        self.assertIn("none", review["catalog_delta"].lower())


class WorkflowWiringTest(unittest.TestCase):
    def setUp(self):
        self.workflows = workflow_texts()
        self.linter = job(self.workflows["linter.yml"], "linter")
        self.ci = self.workflows["ci.yml"]
        self.stage2 = job(self.ci, "stage2-evidence-protocol")

    def test_linter_applies_and_verifies_the_private_vendor_before_the_gate(self):
        apply_index = step_index(self.linter, "Apply approved private Frappe vendor divergence")
        verify_index = step_index(self.linter, "Verify private Frappe vendor identity")
        gate_index = step_index(self.linter, "Localization source gates")
        self.assertLess(apply_index, verify_index)
        self.assertLess(verify_index, gate_index)
        apply_step = step(self.linter, "Apply approved private Frappe vendor divergence")
        verify_step = step(self.linter, "Verify private Frappe vendor identity")
        for block in (apply_step, verify_step):
            self.assertIn(APPLIER, block)
            self.assertIn(EFFECTIVE_COMMIT, block)
            self.assertIn(EFFECTIVE_TREE, block)
        self.assertIn("--verify", verify_step)
        self.assertNotIn("--verify", apply_step)
        self.assertIn(ERPNEXT_COMMIT, apply_step)

    def test_linter_sets_python_up_before_running_the_transport(self):
        python_index = step_index(self.linter, "actions/setup-python@v5")
        apply_index = step_index(self.linter, "Apply approved private Frappe vendor divergence")
        gate_index = step_index(self.linter, "Localization source gates")
        self.assertLess(python_index, apply_index)
        self.assertLess(apply_index, gate_index)
        self.assertIn("python-version: '3.14'", step(self.linter, "actions/setup-python@v5"))

    def test_every_private_vendor_gate_consumer_applies_the_same_transport(self):
        consumers = [name for name, text in self.workflows.items() if SOURCE_GATE in text]
        self.assertTrue(consumers, "no workflow runs the localization source gate")
        for name in consumers:
            text = self.workflows[name]
            self.assertIn(APPLIER, text, f"{name} runs the gate without building the vendor identity")
            self.assertIn(EFFECTIVE_COMMIT, text, f"{name} lacks the effective commit assertion")

    def test_stage2_protocol_job_runs_the_same_vendor_for_its_gate_suite(self):
        # The stage-2 job runs the standalone localization gate suite, so it is a
        # gate consumer: it must transport the same effective vendor. Its fixture
        # job still digest-verifies the vendor FILES, whose bytes do not change.
        self.assertIn(APPLIER, self.stage2)
        self.assertIn(EFFECTIVE_COMMIT, self.stage2)
        self.assertIn(EFFECTIVE_TREE, self.stage2)
        self.assertIn("--verify", self.stage2)
        checkout = step(self.stage2, "Checkout pinned Frappe catalog and script manager")
        self.assertIn(f"ref: {BASE_COMMIT}", checkout)
        sparse = checkout.split("sparse-checkout:", 1)[1]
        self.assertIn("frappe/public/js/frappe/form/script_manager.js", sparse)
        self.assertIn("pyproject.toml", sparse)
        self.assertIn(ERPNEXT_COMMIT, self.stage2)
        self.assertIn("script_manager.js", self.stage2)
        apply_index = step_index(self.stage2, "Apply approved private Frappe vendor divergence")
        verify_index = step_index(self.stage2, "Verify the pinned vendor inputs")
        suite_index = step_index(self.stage2, "Standalone localization gate suite")
        self.assertLess(apply_index, verify_index)
        self.assertLess(verify_index, suite_index)

    def test_stage2_fixture_pins_name_the_effective_commit_and_unchanged_bytes(self):
        fixtures = json.loads(read(ROOT / "construction" / "data" / "localization" / "vendor_ci_inputs.json"))
        frappe = fixtures["apps"]["frappe"]
        self.assertEqual(frappe["commit"], EFFECTIVE_COMMIT)
        self.assertEqual(
            frappe["inputs"]["frappe/locale/ar.po"]["sha256"],
            "ad0c7b27c0406257911210b5c5a354a2fa9506f8fac1b9552806c592c7038205",
        )
        self.assertEqual(
            frappe["inputs"]["frappe/public/js/frappe/form/script_manager.js"]["sha256"],
            "e7204be9dc75381e7a979f7a46f4cc4b14cf0f7f27f18415b121ccc9e07ed025",
        )
        self.assertEqual(fixtures["apps"]["erpnext"]["commit"], ERPNEXT_COMMIT)

    def test_no_workflow_fetches_the_unpublished_commit(self):
        published_line = re.compile(r"^\s*(ref|repository|path):\s*" + EFFECTIVE_COMMIT + r"\s*$")
        for name, text in self.workflows.items():
            for line in text.splitlines():
                self.assertIsNone(
                    published_line.match(line), f"{name} pins the unpublished commit as a checkout ref"
                )
                lowered = line.lower()
                if EFFECTIVE_COMMIT in line and (
                    "fetch" in lowered or "clone" in lowered or "git+" in lowered
                ):
                    self.fail(f"{name} tries to fetch the unpublished commit: {line.strip()}")

    def test_sparse_catalog_checkout_materialises_the_patch_target(self):
        identity = json.loads(read(IDENTITY_PATH))
        checkout = step(self.linter, "Checkout pinned Frappe catalog")
        self.assertIn(f"ref: {BASE_COMMIT}", checkout)
        self.assertIn("sparse-checkout-cone-mode: false", checkout)
        self.assertIn("frappe/locale", checkout)
        self.assertIn(identity["patched_file"], checkout.split("sparse-checkout:", 1)[1])
        self.assertNotIn(EFFECTIVE_COMMIT, checkout)

    def test_required_checks_survive_and_no_baseline_shortcut_is_introduced(self):
        for name, text in self.workflows.items():
            self.assertNotIn("--update-baselines", text, name)
        self.assertIn("pre-commit run --show-diff-on-failure", self.linter)
        self.assertIn("python3 scripts/lint_scope_metadata.py", self.linter)
        self.assertIn("semgrep scan", self.linter)
        audit = job(self.workflows["linter.yml"], "deps-vulnerable-check")
        self.assertIn("pip-audit==2.10.1", audit)
        self.assertIn("pip-audit --desc on .", audit)
        self.assertNotIn("--ignore-vuln", self.workflows["linter.yml"])


if __name__ == "__main__":
    unittest.main()
