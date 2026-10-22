"""Regression tests for caller-owned transactions and safe after-commit work."""

import csv
import tempfile
from pathlib import Path
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTransactionBoundaryOwnership(FrappeTestCase):
    def test_role_seeder_does_not_commit_when_creating_roles(self):
        from construction.install import CONSTRUCTION_ROLES, seed_construction_roles

        with (
            mock.patch.object(frappe.db, "exists", return_value=False),
            mock.patch.object(frappe.db, "commit") as commit,
            mock.patch.object(frappe, "new_doc") as new_doc,
        ):
            created = seed_construction_roles()

        self.assertEqual(created, [name for name, _description in CONSTRUCTION_ROLES])
        self.assertEqual(new_doc.call_count, len(CONSTRUCTION_ROLES))
        commit.assert_not_called()

    def test_released_override_import_schedules_work_without_committing(self):
        from construction import translation_service

        fields = [
            "language",
            "source_text",
            "context",
            "ct_app",
            "translated_text",
            "domain",
            "release_status",
            "release_version",
            "a1_reviewer",
            "a1_approved_at",
            "a2_reviewer",
            "a2_approved_at",
            "a3_reviewer",
            "a3_approved_at",
            "references",
            "notes",
        ]
        payload = {
            "language": "ar",
            "source_text": "Transaction Boundary Test",
            "context": "",
            "ct_app": "construction",
            "translated_text": "اختبار",
            "domain": "test",
            "release_status": "Released",
            "release_version": "1.0",
            "a1_reviewer": "AI-A1 reviewer",
            "a1_approved_at": "2026-10-18 00:00:00",
            "a2_reviewer": "AI-A2 reviewer",
            "a2_approved_at": "2026-10-18 00:00:01",
            "a3_reviewer": "AI-A3 reviewer",
            "a3_approved_at": "2026-10-18 00:00:02",
            "references": "test",
            "notes": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one-release.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(payload)

            with (
                mock.patch.object(frappe, "only_for"),
                mock.patch.object(frappe, "get_all", return_value=[]),
                mock.patch.object(frappe.db, "commit") as commit,
                mock.patch.object(type(frappe.db.after_commit), "add", autospec=True) as add_after_commit,
                mock.patch.object(translation_service, "_get_runtime_rows", return_value=[]),
                mock.patch.object(
                    translation_service, "upsert_runtime_translation", return_value="row-name"
                ) as upsert,
                mock.patch.object(translation_service, "_finish_released_override_import") as finish,
            ):
                result = translation_service.import_released_overrides(path=path, dry_run=False)

                self.assertEqual(result["created"], 1)
                commit.assert_not_called()
                upsert.assert_called_once()
                self.assertTrue(upsert.call_args.kwargs["defer_cache_invalidation"])
                add_after_commit.assert_called_once()
                add_after_commit.call_args.args[1]()
                finish.assert_called_once_with(True)

    def test_import_after_commit_logging_failure_does_not_raise_or_skip_cleanup(self):
        from construction import translation_service

        with (
            mock.patch.object(
                frappe.cache, "set_value", side_effect=RuntimeError("cache unavailable")
            ) as set_value,
            mock.patch.object(frappe.cache, "hdel", side_effect=RuntimeError("cache unavailable")) as hdel,
            mock.patch.object(
                frappe.cache, "delete_value", side_effect=RuntimeError("cache unavailable")
            ) as delete_value,
            mock.patch.object(
                frappe, "clear_cache", side_effect=RuntimeError("cache unavailable")
            ) as clear_cache,
            mock.patch.object(frappe, "logger", side_effect=RuntimeError("logger unavailable")),
        ):
            translation_service._finish_released_override_import(True)

        set_value.assert_called_once()
        self.assertEqual(hdel.call_count, 2)
        delete_value.assert_called_once()
        clear_cache.assert_called_once()

    def test_import_after_commit_exception_logging_failure_does_not_raise(self):
        from construction import translation_service

        logger = mock.Mock()
        logger.exception.side_effect = RuntimeError("logger write failed")
        with (
            mock.patch.object(frappe.cache, "set_value", side_effect=RuntimeError("cache unavailable")),
            mock.patch.object(frappe.cache, "hdel", side_effect=RuntimeError("cache unavailable")),
            mock.patch.object(frappe.cache, "delete_value", side_effect=RuntimeError("cache unavailable")),
            mock.patch.object(frappe, "clear_cache", side_effect=RuntimeError("cache unavailable")),
            mock.patch.object(frappe, "logger", return_value=logger),
        ):
            translation_service._finish_released_override_import(True)

        self.assertEqual(logger.exception.call_count, 5)

    def test_identity_after_commit_callback_swallows_logger_creation_failure(self):
        from construction.setup.translation_catalog_fields import (
            _clear_translation_identity_cache_after_commit,
        )

        with (
            mock.patch("frappe.translate.clear_cache", side_effect=RuntimeError("cache unavailable")),
            mock.patch.object(frappe, "logger", side_effect=RuntimeError("logger unavailable")),
        ):
            _clear_translation_identity_cache_after_commit()

    def test_identity_after_commit_callback_swallows_logger_write_failure(self):
        from construction.setup.translation_catalog_fields import (
            _clear_translation_identity_cache_after_commit,
        )

        logger = mock.Mock()
        logger.exception.side_effect = RuntimeError("logger write failed")
        with (
            mock.patch("frappe.translate.clear_cache", side_effect=RuntimeError("cache unavailable")),
            mock.patch.object(frappe, "logger", return_value=logger),
        ):
            _clear_translation_identity_cache_after_commit()

        logger.exception.assert_called_once()
