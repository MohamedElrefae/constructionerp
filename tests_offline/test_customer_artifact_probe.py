import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "ci"))

import customer_artifact_probe


class CustomerArtifactProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_sha = "a" * 40

    def tearDown(self):
        self.temp.cleanup()

    def _git(self, repo, *args):
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _repo(self, name="customer", extra_files=()):
        repo = self.root / name
        repo.mkdir()
        payload = {"construction/__init__.py": b"# customer app\n"}
        for rel, content in payload.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        rows = [
            {"path": rel, "sha256": hashlib.sha256(content).hexdigest()}
            for rel, content in sorted(payload.items())
        ]
        manifest = {
            "schema_version": 1,
            "source_head": self.source_sha,
            "files": len(rows),
            "rows": rows,
            "artifact_tree_sha256": customer_artifact_probe._tree_digest(rows),
        }
        (repo / customer_artifact_probe.MANIFEST_NAME).write_text(
            json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
        )
        for rel in extra_files:
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("unexpected\n", encoding="utf-8")
        self._git(repo, "init", "-b", "qa-candidate")
        self._git(repo, "add", "-A")
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=Customer artifact test",
                "-c",
                "user.email=customer-artifact-test@example.invalid",
                "commit",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return repo

    def test_root_repo_and_bench_clone_match_manifest_binding(self):
        repo = self._repo()
        binding = customer_artifact_probe.verify_checkout(repo, self.source_sha)
        clone = self.root / "bench-app"
        subprocess.run(["git", "clone", str(repo), str(clone)], check=True, capture_output=True, text=True)

        result = customer_artifact_probe.verify_checkout(
            clone,
            self.source_sha,
            expected_commit=binding["customer_commit"],
            expected_origin=repo,
            binding=binding,
        )
        self.assertEqual(result["manifest_sha256"], binding["manifest_sha256"])
        self.assertEqual(result["origin"], str(repo.resolve()))

    def test_bench_clone_upstream_remote_matches_staged_customer_artifact(self):
        repo = self._repo()
        binding = customer_artifact_probe.verify_checkout(repo, self.source_sha)
        clone = self.root / "bench-app-upstream"
        subprocess.run(
            ["git", "clone", "--origin", "upstream", str(repo), str(clone)],
            check=True,
            capture_output=True,
            text=True,
        )

        result = customer_artifact_probe.verify_checkout(
            clone,
            self.source_sha,
            expected_commit=binding["customer_commit"],
            expected_origin=repo,
            expected_remote="upstream",
            binding=binding,
        )
        self.assertEqual(result["origin"], str(repo.resolve()))

        with self.assertRaisesRegex(ValueError, "remote is missing: origin"):
            customer_artifact_probe.verify_checkout(
                clone,
                self.source_sha,
                expected_origin=repo,
                expected_remote="origin",
            )

        subprocess.run(
            ["git", "-C", str(clone), "remote", "set-url", "upstream", str(self.root)],
            check=True,
            capture_output=True,
            text=True,
        )
        with self.assertRaisesRegex(ValueError, "unexpected customer artifact origin"):
            customer_artifact_probe.verify_checkout(
                clone,
                self.source_sha,
                expected_origin=repo,
                expected_remote="upstream",
            )

    def test_rejects_invalid_customer_remote_name(self):
        repo = self._repo()
        with self.assertRaisesRegex(ValueError, "remote name is invalid"):
            customer_artifact_probe.verify_checkout(
                repo,
                self.source_sha,
                expected_origin=repo,
                expected_remote="../origin",
            )

    def test_rejects_payload_hash_drift(self):
        repo = self._repo()
        payload = repo / "construction" / "__init__.py"
        payload.write_text("# changed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, text=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=Customer artifact test",
                "-c",
                "user.email=customer-artifact-test@example.invalid",
                "commit",
                "--amend",
                "--no-edit",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            customer_artifact_probe.verify_checkout(repo, self.source_sha)

    def test_rejects_tracked_files_outside_manifest(self):
        repo = self._repo(extra_files=(".github/workflows/internal.yml",))
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            customer_artifact_probe.verify_checkout(repo, self.source_sha)

    def test_rejects_wrong_candidate_sha(self):
        repo = self._repo()
        with self.assertRaisesRegex(ValueError, "source_head"):
            customer_artifact_probe.verify_checkout(repo, "b" * 40)

    def test_recovery_context_is_exact_site_and_uuid_bound(self):
        with self.assertRaisesRegex(ValueError, "restricted"):
            customer_artifact_probe._recovery_record_path("production.local", "a" * 32, self.root)
        with self.assertRaisesRegex(ValueError, "token"):
            customer_artifact_probe._recovery_record_path(
                customer_artifact_probe.RECOVERY_SITE, "../outside", self.root
            )
        frappe = SimpleNamespace(local=SimpleNamespace(site="production.local"))
        with (
            patch.dict(
                os.environ,
                {
                    "C2_EXPECTED_SITE": customer_artifact_probe.RECOVERY_SITE,
                    "C2_RUNNER_TEMP": str(self.root),
                    "C2_RECOVERY_TOKEN": "a" * 32,
                },
            ),
            self.assertRaisesRegex(ValueError, "exact"),
        ):
            customer_artifact_probe._native_recovery_context(frappe)

    def test_c2_workflow_executes_external_probe_with_explicit_import_expressions(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        lines = workflow.splitlines()
        command_indexes = [
            index for index, line in enumerate(lines) if "bench --site c2_customer_site execute" in line
        ]
        commands = [lines[index].strip() for index in command_indexes]
        self.assertNotIn("execute customer_artifact_probe.", workflow)
        self.assertEqual(
            len(commands),
            9,
            "review the C2 native probe inventory when adding or removing a call",
        )
        method_counts = {}
        for index, command in zip(command_indexes, commands, strict=True):
            environment = "\n".join(lines[max(0, index - 4) : index])
            self.assertIn(
                'PYTHONPATH="$GITHUB_WORKSPACE/.github/ci',
                environment,
                "external CI helper path must be set for each native call",
            )
            match = re.fullmatch(
                r"bench --site c2_customer_site execute "
                r"\"__import__\('customer_artifact_probe'\)\.([a-z_]+)\(\)\"",
                command,
            )
            self.assertIsNotNone(
                match,
                f"C2 execute must use the explicit external-helper eval expression: {command}",
            )
            method = match.group(1)
            method_counts[method] = method_counts.get(method, 0) + 1

        self.assertEqual(
            method_counts,
            {
                "verify_import_path": 3,
                "verify_generated_theme_assets": 3,
                "prepare_recovery_marker": 1,
                "delete_recovery_marker": 1,
                "assert_recovery_marker": 1,
            },
        )

    def test_recovery_record_rejects_nonprivate_or_foreign_marker(self):
        token = "a" * 32
        record = {
            "site": customer_artifact_probe.RECOVERY_SITE,
            "token": token,
            "user": f"c2-recovery-{token}@example.invalid",
            "file_name": customer_artifact_probe._recovery_marker_file_name(token),
            "file_docname": "file-marker",
            "file_url": f"/private/files/{customer_artifact_probe._recovery_marker_file_name(token)}",
            "sha256": "b" * 64,
        }
        self.assertEqual(
            customer_artifact_probe._validate_recovery_record(
                record, customer_artifact_probe.RECOVERY_SITE, token
            ),
            record,
        )
        for field, value in (
            ("user", "Administrator"),
            ("file_url", f"/files/{record['file_name']}"),
            ("sha256", "not-a-hash"),
        ):
            invalid = {**record, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                customer_artifact_probe._validate_recovery_record(
                    invalid, customer_artifact_probe.RECOVERY_SITE, token
                )
        self.assertEqual(record["file_name"], customer_artifact_probe._recovery_marker_file_name(token))
        invalid = {**record, "file_docname": ""}
        with self.assertRaisesRegex(ValueError, "DocType name"):
            customer_artifact_probe._validate_recovery_record(
                invalid, customer_artifact_probe.RECOVERY_SITE, token
            )

    def test_backup_validation_requires_and_hashes_exact_private_marker(self):
        token = "c" * 32
        payload = b"synthetic C2 recovery marker\n"
        digest = hashlib.sha256(payload).hexdigest()
        file_name = customer_artifact_probe._recovery_marker_file_name(token)
        record = {
            "site": customer_artifact_probe.RECOVERY_SITE,
            "token": token,
            "user": f"c2-recovery-{token}@example.invalid",
            "file_name": file_name,
            "file_docname": "file-marker",
            "file_url": f"/private/files/{file_name}",
            "sha256": digest,
        }
        record_path = self.root / f"c2-recovery-{token}.json"
        record_path.write_text(json.dumps(record), encoding="utf-8")
        backup_dir = self.root / f"c2-recovery-{token}-backup"
        backup_dir.mkdir()
        with gzip.open(backup_dir / "20261018-c2_customer_site-database.sql.gz", "wb") as stream:
            stream.write(b"synthetic sql dump")
        for suffix, member_name, content in (
            ("files.tar", "sites/c2_customer_site/public/files/empty.txt", b"public"),
            ("private-files.tar", f"sites/c2_customer_site/private/files/{file_name}", payload),
        ):
            with tarfile.open(backup_dir / f"20261018-c2_customer_site-{suffix}", "w") as archive:
                info = tarfile.TarInfo(member_name)
                info.size = len(content)
                archive.addfile(info, BytesIO(content))

        output = backup_dir / "validation.json"
        customer_artifact_probe.validate_recovery_backup(backup_dir, record_path, output)
        validation = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(set(validation), {"database", "public", "private"})
        self.assertTrue(all(row["sha256"] for row in validation.values()))
        output.unlink()

        private_path = backup_dir / "20261018-c2_customer_site-private-files.tar"
        with tarfile.open(private_path, "w") as archive:
            info = tarfile.TarInfo("sites/c2_customer_site/private/files/wrong.txt")
            info.size = 1
            archive.addfile(info, BytesIO(b"x"))
        with self.assertRaisesRegex(ValueError, "exact C2 marker"):
            customer_artifact_probe.validate_recovery_backup(backup_dir, record_path, output)
        with tarfile.open(private_path, "w") as archive:
            info = tarfile.TarInfo(f"sites/c2_customer_site/private/files/{file_name}")
            info.size = 1
            archive.addfile(info, BytesIO(b"x"))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            customer_artifact_probe.validate_recovery_backup(backup_dir, record_path, output)

    def _asset_roots(self):
        customer = self.root / "customer"
        bench = customer / "bench"
        source = customer / "construction" / "public" / "css" / "modern_theme.css"
        served = bench / "sites" / "assets" / "construction" / "css" / "modern_theme.css"
        source.parent.mkdir(parents=True)
        served.parent.mkdir(parents=True)
        source.write_bytes(b"customer theme bytes\n")
        served.write_bytes(source.read_bytes())
        return customer, bench, source, served

    def test_registered_web_asset_matches_nonempty_customer_source(self):
        customer, bench, _, _ = self._asset_roots()
        customer_artifact_probe._verify_served_customer_asset(
            bench, customer, "/assets/construction/css/modern_theme.css?v=2.5.9"
        )

    def test_registered_web_asset_rejects_missing_source_and_served_files(self):
        customer, bench, source, served = self._asset_roots()
        source.unlink()
        with self.assertRaises(FileNotFoundError):
            customer_artifact_probe._verify_served_customer_asset(
                bench, customer, "/assets/construction/css/modern_theme.css"
            )
        source.write_bytes(b"customer theme bytes\n")
        served.unlink()
        with self.assertRaises(FileNotFoundError):
            customer_artifact_probe._verify_served_customer_asset(
                bench, customer, "/assets/construction/css/modern_theme.css"
            )

    def test_registered_web_asset_rejects_empty_and_hash_mismatch(self):
        customer, bench, _, served = self._asset_roots()
        served.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "empty"):
            customer_artifact_probe._verify_served_customer_asset(
                bench, customer, "/assets/construction/css/modern_theme.css"
            )
        served.write_bytes(b"different bytes")
        with self.assertRaisesRegex(ValueError, "differs"):
            customer_artifact_probe._verify_served_customer_asset(
                bench, customer, "/assets/construction/css/modern_theme.css"
            )

    def test_registered_web_asset_rejects_path_escape(self):
        customer, bench, _, _ = self._asset_roots()
        with self.assertRaisesRegex(ValueError, "invalid construction asset path"):
            customer_artifact_probe._verify_served_customer_asset(
                bench, customer, "/assets/construction/../outside.css"
            )

    def test_registered_web_asset_rejects_symlink_outside_customer_checkout(self):
        customer, bench, _, served = self._asset_roots()
        served.unlink()
        outside = self.root / "outside.css"
        outside.write_bytes(b"outside customer bytes")
        served.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "outside the customer checkout"):
            customer_artifact_probe._verify_served_customer_asset(
                bench, customer, "/assets/construction/css/modern_theme.css"
            )

    def test_login_css_requires_exact_nonempty_configured_output(self):
        asset = self.root / "login_theme.css"
        expected = "body[data-path='login'] { color: #123456; }"
        asset.write_text(expected, encoding="utf-8")
        customer_artifact_probe._verify_generated_login_css(asset, [expected])
        for actual in (None, "", "stale css", "unexpected css"):
            if actual is None:
                asset.unlink()
            else:
                asset.write_text(actual, encoding="utf-8")
            with self.assertRaises(ValueError):
                customer_artifact_probe._verify_generated_login_css(asset, [expected])

    def test_login_css_accepts_exact_native_empty_output_only(self):
        asset = self.root / "login_theme.css"
        asset.write_bytes(b"")
        customer_artifact_probe._verify_generated_login_css(asset, [""])
        asset.write_text("/* stale or unexpected */", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            customer_artifact_probe._verify_generated_login_css(asset, [""])

    def test_login_css_rejects_missing_file_even_when_output_is_empty(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            customer_artifact_probe._verify_generated_login_css(self.root / "missing.css", [""])

    def test_equal_last_writer_timestamps_keep_all_generators_as_candidates(self):
        themes = [
            {"name": "older", "modified": "2026-10-17 12:00:00"},
            {"name": "latest-a", "modified": "2026-10-18 12:00:00"},
            {"name": "latest-b", "modified": "2026-10-18 12:00:00"},
        ]
        candidates = customer_artifact_probe._latest_login_css_themes(themes)
        self.assertEqual([theme["name"] for theme in candidates], ["latest-a", "latest-b"])

        asset = self.root / "login_theme.css"
        for expected in ("native output A", "native output B"):
            asset.write_text(expected, encoding="utf-8")
            customer_artifact_probe._verify_generated_login_css(asset, ["native output A", "native output B"])
        asset.write_text("unrelated output", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            customer_artifact_probe._verify_generated_login_css(asset, ["native output A", "native output B"])

    def test_latest_theme_selector_rejects_no_eligible_themes(self):
        with self.assertRaisesRegex(ValueError, "no eligible"):
            customer_artifact_probe._latest_login_css_themes([])
        with self.assertRaisesRegex(ValueError, "no modification timestamp"):
            customer_artifact_probe._latest_login_css_themes([{"name": "incomplete"}])

    def test_construction_hook_inventory_keeps_only_local_construction_assets(self):
        urls = customer_artifact_probe._construction_web_asset_urls(
            {
                "web_include_css": [
                    "/assets/construction/css/modern_theme.css?v=2",
                    "/assets/erpnext/css/erpnext.css",
                ],
                "web_include_js": "/assets/construction/js/theme_loader.js",
            }
        )
        self.assertEqual(
            urls,
            [
                "/assets/construction/css/modern_theme.css?v=2",
                "/assets/construction/js/theme_loader.js",
            ],
        )
        with self.assertRaisesRegex(ValueError, "non-local"):
            customer_artifact_probe._construction_web_asset_urls(
                {"web_include_css": ["https://example.invalid/theme.css"], "web_include_js": []}
            )


if __name__ == "__main__":
    unittest.main()
