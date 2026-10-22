import csv
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import distribution_policy
import stage_distribution
import verify_staged_distribution


class DistributionPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, stage, rel, content="fixture\n"):
        path = stage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _valid_stage(self):
        stage = self.root / "customer"
        payload = {}
        for rel in verify_staged_distribution.REQUIRED:
            content = "fixture\n"
            if rel == "construction/data/translations/approved_ar_overrides.csv":
                content = (
                    "release_status,decision_ref\n"
                    "Released,content:construction/data/glossary/egyptian_construction_glossary.json\n"
                )
            elif rel in distribution_policy.LICENSE_CANDIDATES:
                content = "MIT License\n"
            path = self._write(stage, rel, content)
            payload[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        license_path = self._write(stage, "LICENSE", "MIT License\n")
        payload["LICENSE"] = hashlib.sha256(license_path.read_bytes()).hexdigest()
        rows = [{"path": path, "sha256": digest} for path, digest in sorted(payload.items())]
        manifest = {
            "schema_version": 1,
            "method": "test fixture",
            "source_head": "a" * 40,
            "artifact_tree_sha256": stage_distribution._tree_digest(rows),
            "files": len(rows),
            "rows": rows,
        }
        (stage / "DISTRIBUTION_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        return stage

    def _rewrite_manifest(self, stage):
        payload = {
            path.relative_to(stage).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in stage.rglob("*")
            if path.is_file() and path.name != "DISTRIBUTION_MANIFEST.json"
        }
        rows = [{"path": path, "sha256": digest} for path, digest in sorted(payload.items())]
        manifest = {
            "schema_version": 1,
            "method": "test fixture",
            "source_head": "a" * 40,
            "artifact_tree_sha256": stage_distribution._tree_digest(rows),
            "files": len(rows),
            "rows": rows,
        }
        (stage / "DISTRIBUTION_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_fresh_stage_verifies_without_rewriting_manifest(self):
        stage = self._valid_stage()
        manifest = stage / "DISTRIBUTION_MANIFEST.json"
        before = manifest.read_bytes()
        self.assertEqual(verify_staged_distribution.verify(stage), [])
        self.assertEqual(manifest.read_bytes(), before)

    def test_verifier_rejects_forbidden_or_nonallowlisted_paths(self):
        for rel in (
            "construction/tests/test_private_fixture.py",
            "construction/data/localization/vendor_delta_frappe.json",
            "construction/data/localization/stage4_export_manifest.json",
            "construction/data/localization/freshness_evidence.json",
            "construction/data/localization/site_classification.json",
            "construction/data/localization/vendor_msgids_frappe.txt",
            "docs/translation/internal.csv",
            "construction/public/dist/js/app.map",
            ".github/security/semgrep_review_ledger.json",
        ):
            with self.subTest(path=rel):
                stage = self._valid_stage()
                path = self._write(stage, rel)
                errors = verify_staged_distribution.verify(stage)
                self.assertTrue(errors, rel)
                path.unlink()

    def test_verifier_rejects_hash_drift(self):
        stage = self._valid_stage()
        source = stage / "README.md"
        source.write_text("changed after staging\n", encoding="utf-8")
        self.assertTrue(any("sha256 mismatch" in error for error in verify_staged_distribution.verify(stage)))

    def test_verifier_rejects_missing_active_content_reference(self):
        stage = self._valid_stage()
        csv_path = stage / "construction/data/translations/approved_ar_overrides.csv"
        csv_path.write_text(
            "release_status,decision_ref\n"
            "Released,content:construction/data/translations/release_evidence/missing.txt\n",
            encoding="utf-8",
        )
        self._rewrite_manifest(stage)
        errors = verify_staged_distribution.verify(stage)
        self.assertTrue(any("references missing content" in error for error in errors), errors)

    def test_verifier_rejects_traversing_absolute_and_excluded_active_content_references(self):
        invalid_references = (
            "content:../outside.txt",
            "content:/etc/passwd",
            "content:construction/tests/private_fixture.py",
            "content:docs/translation/internal.csv",
        )
        for reference in invalid_references:
            with self.subTest(reference=reference):
                stage = self._valid_stage()
                csv_path = stage / "construction/data/translations/approved_ar_overrides.csv"
                csv_path.write_text(f"release_status,decision_ref\nReleased,{reference}\n", encoding="utf-8")
                self._rewrite_manifest(stage)
                self.assertTrue(verify_staged_distribution.verify(stage), reference)

    def test_verifier_requires_at_least_one_nonempty_license(self):
        stage = self._valid_stage()
        (stage / "LICENSE").unlink()
        self._rewrite_manifest(stage)
        self.assertTrue(
            any("nonempty LICENSE" in error for error in verify_staged_distribution.verify(stage))
        )

    def test_stager_reads_committed_blobs_even_when_worktree_is_dirty_or_ignored(self):
        tracked = {
            path: f"committed {path}\n".encode() for path in distribution_policy.REQUIRED_CUSTOMER_FILES
        }
        tracked.update(
            {
                "construction/committed.py": b"committed module\n",
                "construction/tests/private.py": b"must be excluded\n",
                "LICENSE": b"MIT License\n",
            }
        )
        blob_ids = {f"blob-{index}": path for index, path in enumerate(tracked)}
        entries = {path: ("100644", "blob", object_id) for object_id, path in blob_ids.items()}

        def cat_file(args, **kwargs):
            return SimpleNamespace(stdout=tracked[blob_ids[args[-1]]])

        with (
            mock.patch.object(stage_distribution, "APP_ROOT", self.root),
            mock.patch.object(stage_distribution, "APP_ROOT_REAL", self.root.resolve()),
            mock.patch.object(stage_distribution, "_git_head", return_value="b" * 40),
            mock.patch.object(stage_distribution, "_git_tree_entries", return_value=entries),
            mock.patch.object(stage_distribution.subprocess, "run", side_effect=cat_file),
        ):
            head, sources = stage_distribution._committed_sources()
        self.assertEqual(head, "b" * 40)
        committed = dict(sources)
        self.assertEqual(committed["README.md"], b"committed README.md\n")
        self.assertEqual(committed["construction/committed.py"], b"committed module\n")
        self.assertNotIn("construction/tests/private.py", committed)

    def test_output_validation_never_removes_existing_path(self):
        app = self.root / "checkout"
        app.mkdir()
        existing = self.root / "keep-me"
        existing.mkdir()
        marker = existing / "data.txt"
        marker.write_text("preserve\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "already exists"):
            stage_distribution.stage(existing)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve\n")

    def test_output_validation_rejects_checkout_and_ancestor(self):
        app = self.root / "checkout"
        app.mkdir()
        with self.assertRaisesRegex(ValueError, "outside the app checkout"):
            stage_distribution.validate_output_path(app / "new-stage", app)

        future_app = self.root / "not-created-parent" / "checkout"
        with self.assertRaisesRegex(ValueError, "ancestor of the app checkout"):
            stage_distribution.validate_output_path(future_app.parent, future_app)

    def test_output_validation_resolves_symlinked_parent(self):
        app = self.root / "checkout"
        app.mkdir()
        link = self.root / "checkout-link"
        link.symlink_to(app, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "outside the app checkout"):
            stage_distribution.validate_output_path(link / "new-stage", app)

    def test_output_validation_refuses_existing_symlink_without_unlinking_target(self):
        app = self.root / "checkout"
        app.mkdir()
        target = self.root / "target"
        target.mkdir()
        marker = target / "keep.txt"
        marker.write_text("preserve\n", encoding="utf-8")
        link = self.root / "existing-link"
        link.symlink_to(target, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "already exists"):
            stage_distribution.validate_output_path(link, app)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve\n")

    def test_shared_policy_excludes_tests_and_localization_qualification_data(self):
        forbidden = (
            "docs/ai/report.md",
            "docs/feature_reviews/evidence/report.md",
            "docs/translation/history.csv",
            "docs/scope_context_option_a.log",
            "orchestrator/task.json",
            "tests_offline/test_gate.py",
            "erpnext-mcp-server/server.py",
            "construction/tests/test_anything.py",
            "construction/data/localization/stage4_export_manifest.json",
            "construction/data/localization/stage2_inventory_manifest.json",
            "construction/data/localization/freshness_evidence.json",
            "construction/data/localization/localization_manifest.json",
            "construction/data/localization/site_classification.json",
            "construction/data/localization/vendor_catalog_baseline.json",
            "construction/data/localization/vendor_msgids_erpnext.txt",
            "construction/data/localization/vendor_delta_frappe_abcdef12_reviewed.json",
            "construction/public/dist/js/app.map",
            "construction/public/dist/nested/app.map",
            "construction/public/css/theme_example.css",
            "construction/public/css/login_theme.css",
            "construction/__pycache__/module.pyc",
            "construction/module.pyc",
            "setup.py",
            "dist/app.whl",
        )
        for path in forbidden:
            with self.subTest(path=path):
                self.assertTrue(distribution_policy.never_ships(path), path)
        self.assertFalse(
            distribution_policy.never_ships("construction/data/translations/release_decisions.json")
        )
        self.assertFalse(
            distribution_policy.never_ships("construction/data/glossary/egyptian_construction_glossary.json")
        )
        self.assertFalse(distribution_policy.never_ships("construction/public/css/modern_theme_base.css"))
        for path in (".gitignore", ".gitattributes"):
            with self.subTest(customer_root_file=path):
                self.assertIn(path, distribution_policy.REQUIRED_CUSTOMER_FILES)
                self.assertTrue(distribution_policy.is_customer_path(path), path)

    def test_active_f31_and_stage1c_csv_references_are_customer_paths(self):
        csv_path = ROOT / "construction/data/translations/approved_ar_overrides.csv"
        selected = set()
        with csv_path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if row.get("source_text") not in {
                    "Variation Order",
                    "Desktop",
                    "Workspaces",
                    "Edit Sidebar",
                    "Toggle Theme",
                    "Toggle Full Width",
                    "Typography Settings",
                }:
                    continue
                for value in (row.get("decision_ref") or "").split(";"):
                    match = re.fullmatch(r"content:(.+)", value.strip())
                    if match:
                        selected.add(match.group(1))
        expected = {
            "construction/data/translations/f31_decision_evidence_2026-10-14.md",
            "construction/data/translations/f31_review_evidence_2026-10-18.json",
            "construction/data/glossary/f31_variation_order_amendment_v2_2.json",
            "construction/data/translations/stage1c_menu_label_review_evidence_v1.json",
        }
        self.assertEqual(selected, expected)
        for path in selected:
            self.assertTrue(distribution_policy.is_customer_path(path), path)
            self.assertFalse(distribution_policy.never_ships(path), path)
            self.assertTrue((ROOT / path).is_file(), path)

    def test_all_released_content_decision_refs_are_customer_paths(self):
        refs = set()
        csv_path = ROOT / "construction/data/translations/approved_ar_overrides.csv"
        with csv_path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if row.get("release_status") != "Released":
                    continue
                for value in (row.get("decision_ref") or "").split(";"):
                    match = re.fullmatch(r"content:(.+)", value.strip())
                    if match:
                        refs.add(match.group(1))
        self.assertTrue(refs)
        for path in refs:
            with self.subTest(path=path):
                self.assertTrue(distribution_policy.is_customer_path(path), path)
                self.assertFalse(distribution_policy.never_ships(path), path)
                self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
