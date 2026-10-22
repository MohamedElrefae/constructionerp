"""Focused unit coverage for translation catalog transaction boundaries."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

_MODULE_PATH = Path(__file__).parents[1] / "construction" / "api" / "translation_tools.py"
_MODULE_SPEC = importlib.util.spec_from_file_location("translation_tools_atomicity_target", _MODULE_PATH)
translation_tools = importlib.util.module_from_spec(_MODULE_SPEC)


def _identity_whitelist(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    return lambda function: function


_import_frappe = SimpleNamespace(_=lambda text: text, whitelist=_identity_whitelist)
_import_translate = SimpleNamespace(
    MERGED_TRANSLATION_KEY="merged", USER_TRANSLATION_KEY="user", strip_html_tags=lambda value: value
)
_import_utils = SimpleNamespace(cint=lambda value: int(value or 0))
with patch.dict(
    sys.modules,
    {
        "frappe": _import_frappe,
        "frappe.translate": _import_translate,
        "frappe.utils": _import_utils,
    },
):
    _MODULE_SPEC.loader.exec_module(translation_tools)


class TestTranslationCatalogAtomicity(TestCase):
    def setUp(self):
        self.frappe = SimpleNamespace(
            only_for=MagicMock(),
            db=SimpleNamespace(
                has_column=MagicMock(return_value=True),
                get_all=MagicMock(return_value=[]),
                bulk_insert=MagicMock(),
                set_value=MagicMock(),
                get_value=MagicMock(),
                delete=MagicMock(),
                commit=MagicMock(),
                after_commit=SimpleNamespace(add=MagicMock()),
            ),
            cache=SimpleNamespace(delete_value=MagicMock()),
            clear_cache=MagicMock(),
            logger=MagicMock(return_value=MagicMock()),
            get_all=MagicMock(return_value=[]),
            parse_json=MagicMock(),
            utils=SimpleNamespace(now=MagicMock(return_value="2026-10-18 12:00:00")),
            generate_hash=MagicMock(return_value="catalog-row"),
            session=SimpleNamespace(user="Administrator"),
            throw=MagicMock(side_effect=RuntimeError("catalog fields not present")),
        )
        self.frappe.db.has_column.side_effect = lambda doctype, field: (
            field
            in {
                *translation_tools._REQUIRED_CATALOG_FIELDS,
            }
        )
        self.po_path = MagicMock()
        self.po_path.exists.return_value = True
        self.message = SimpleNamespace(id="Source", context=None, string="ترجمة")
        self.patches = [
            patch.object(translation_tools, "frappe", self.frappe),
            patch.object(translation_tools, "_po_path_for_app", return_value=self.po_path),
            patch.object(translation_tools, "read_po", return_value=[self.message]),
        ]
        for mocked in self.patches:
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_sync_dry_run_preflights_without_writes_or_callbacks(self):
        result = translation_tools.sync_translation_catalog(apps=["construction"], dry_run=True)

        self.assertEqual(result, {"apps": ["construction"], "created": 1, "updated": 0, "dry_run": True})
        self.frappe.db.bulk_insert.assert_not_called()
        self.frappe.db.set_value.assert_not_called()
        self.frappe.db.commit.assert_not_called()
        self.frappe.db.after_commit.add.assert_not_called()

    def test_sync_mutation_leaves_commit_to_request_and_defers_cache_clear(self):
        result = translation_tools.sync_translation_catalog(apps=["construction"], dry_run=False)

        self.assertEqual(result["created"], 1)
        self.frappe.db.bulk_insert.assert_called_once()
        self.frappe.db.commit.assert_not_called()
        callback = self.frappe.db.after_commit.add.call_args.args[0]
        self.frappe.cache.delete_value.assert_not_called()
        self.frappe.clear_cache.assert_not_called()
        callback()
        self.frappe.cache.delete_value.assert_called_once()
        self.frappe.clear_cache.assert_called_once()

    def test_sync_noop_does_not_schedule_cache_clear(self):
        self.frappe.get_all.return_value = [
            SimpleNamespace(name="existing", source_text="Source", context="", ct_app="construction")
        ]
        self.frappe.db.get_value.return_value = "ترجمة"

        result = translation_tools.sync_translation_catalog(apps=["construction"], dry_run=False)

        self.assertEqual((result["created"], result["updated"]), (0, 0))
        self.frappe.db.after_commit.add.assert_not_called()
        self.frappe.db.commit.assert_not_called()

    def test_reset_dry_run_has_no_delete_or_callback(self):
        self.frappe.get_all.return_value = [
            SimpleNamespace(name="stale", source_text="Old", context="", ct_app="construction")
        ]

        result = translation_tools.reset_catalog_overrides(apps=["construction"], dry_run=True)

        self.assertEqual(result, {"deleted": 1, "dry_run": True})
        self.assertEqual(
            self.frappe.get_all.call_args.kwargs["filters"]["ct_app"],
            ["in", ["construction"]],
        )
        self.frappe.db.delete.assert_not_called()
        self.frappe.db.commit.assert_not_called()
        self.frappe.db.after_commit.add.assert_not_called()

    def test_reset_mutation_leaves_commit_to_request_and_defers_cache_clear(self):
        self.frappe.get_all.return_value = [
            SimpleNamespace(name="stale", source_text="Old", context="", ct_app="construction")
        ]

        result = translation_tools.reset_catalog_overrides(apps=["construction"], dry_run=False)

        self.assertEqual(result, {"deleted": 1, "dry_run": False})
        self.assertEqual(
            self.frappe.get_all.call_args.kwargs["filters"]["ct_app"],
            ["in", ["construction"]],
        )
        self.frappe.db.delete.assert_called_once_with("Translation", "stale")
        self.frappe.db.commit.assert_not_called()
        callback = self.frappe.db.after_commit.add.call_args.args[0]
        self.frappe.cache.delete_value.assert_not_called()
        self.frappe.clear_cache.assert_not_called()
        callback()
        self.frappe.cache.delete_value.assert_called_once()
        self.frappe.clear_cache.assert_called_once()

    def test_cache_failures_are_logged_independently_after_commit(self):
        logger = self.frappe.logger.return_value
        self.frappe.cache.delete_value.side_effect = RuntimeError("key cache failed")
        self.frappe.clear_cache.side_effect = RuntimeError("frappe cache failed")

        translation_tools._clear_catalog_caches_after_commit()

        self.assertEqual(logger.exception.call_count, 2)
        self.frappe.cache.delete_value.assert_called_once()
        self.frappe.clear_cache.assert_called_once()

    def test_logger_creation_failure_does_not_escape_or_skip_cache_attempts(self):
        self.frappe.cache.delete_value.side_effect = RuntimeError("key cache failed")
        self.frappe.logger.side_effect = RuntimeError("logger unavailable")

        translation_tools._clear_catalog_caches_after_commit()

        self.frappe.cache.delete_value.assert_called_once()
        self.frappe.clear_cache.assert_called_once()

    def test_logger_exception_failure_does_not_escape_or_skip_cache_attempts(self):
        self.frappe.cache.delete_value.side_effect = RuntimeError("key cache failed")
        self.frappe.logger.return_value.exception.side_effect = RuntimeError("log write failed")

        translation_tools._clear_catalog_caches_after_commit()

        self.frappe.cache.delete_value.assert_called_once()
        self.frappe.clear_cache.assert_called_once()

    def test_missing_schema_uses_existing_diagnostic_without_ensuring_fields(self):
        self.frappe.db.has_column.side_effect = lambda doctype, field: field != "ct_app"

        with self.assertRaisesRegex(RuntimeError, "catalog fields not present"):
            translation_tools.sync_translation_catalog(apps=["construction"], dry_run=True)

        self.frappe.db.commit.assert_not_called()
        self.frappe.db.after_commit.add.assert_not_called()
