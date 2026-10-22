"""Native HTTP regression coverage for translation catalog transactions."""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import frappe
from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import get_test_client

from construction.api import translation_tools


class TestTranslationCatalogHTTPAtomicity(FrappeAPITestCase):
    """Exercise endpoint transaction behavior through Frappe's WSGI client."""

    TEST_CLIENT = get_test_client(use_cookies=False)

    def setUp(self):
        super().setUp()
        self.original_user = frappe.session.user
        frappe.set_user("Administrator")
        self.test_app = f"ct_http_test_{uuid4().hex}"
        self.sentinel_app = f"{self.test_app}_sentinel"
        self.test_apps = {self.test_app, self.sentinel_app}
        self.po_tempdir = tempfile.TemporaryDirectory(prefix="translation-catalog-http-")
        self.addCleanup(self.po_tempdir.cleanup)
        self.addCleanup(self._cleanup_rows)
        required = (
            "ct_is_catalog_entry",
            "ct_app",
            "ct_po_translation",
            "ct_review_status",
            "ct_catalog_synced_at",
        )
        missing = [fieldname for fieldname in required if not frappe.db.has_column("Translation", fieldname)]
        self.assertFalse(missing, f"native catalog tests require preinstalled fields: {missing}")
        index_rows = frappe.db.sql(
            "SHOW INDEX FROM `tabTranslation` WHERE Key_name = %s", ("ct_translation_key_digest",)
        )
        self.assertTrue(index_rows, "native catalog tests require the preinstalled digest unique index")

    def _write_po(self, entries):
        catalog = Catalog(locale="ar")
        for source, translated in entries:
            catalog.add(source, translated)
        path = Path(self.po_tempdir.name) / f"{uuid4().hex}.po"
        with path.open("wb") as handle:
            write_po(handle, catalog)
        return path

    def _post(self, endpoint, path, apps=None, **kwargs):
        apps = apps or [self.test_app]
        data = {"sid": self.sid, "apps": json.dumps(apps), **kwargs}
        # Commit only test-owned fixture/session state before the WSGI request;
        # reset the caller connection afterward so reads observe the request's
        # committed result instead of a repeatable-read snapshot.
        frappe.db.commit()
        try:
            with patch.object(translation_tools, "_po_path_for_app", return_value=path):
                return self.post(self.method(f"construction.api.translation_tools.{endpoint}"), data)
        finally:
            frappe.db.rollback()

    def _other_catalog_snapshot(self):
        rows = frappe.get_all(
            "Translation",
            filters={"language": "ar", "ct_is_catalog_entry": 1},
            fields=["name", "ct_app", "source_text", "context", "ct_key_digest"],
            limit_page_length=0,
        )
        payload = sorted(
            (row.name, row.ct_app or "", row.source_text or "", row.context or "", row.ct_key_digest or "")
            for row in rows
            if row.ct_app != self.test_app
        )
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return len(payload), hashlib.sha256(encoded).hexdigest()

    def _insert_stale_catalog_row(self, source, app=None):
        app = app or self.test_app
        return frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "ar",
                "source_text": source,
                "translated_text": "ترجمة اختبارية",
                "context": "",
                "ct_is_catalog_entry": 1,
                "ct_app": app,
                "ct_po_translation": "ترجمة اختبارية",
                "ct_review_status": "Approved",
                "ct_catalog_synced_at": frappe.utils.now(),
            }
        ).insert(ignore_permissions=True)

    def _cleanup_rows(self):
        try:
            frappe.set_user("Administrator")
            for row in frappe.get_all(
                "Translation",
                filters={
                    "language": "ar",
                    "ct_app": ["in", list(self.test_apps)],
                    "ct_is_catalog_entry": 1,
                },
                pluck="name",
                limit_page_length=0,
            ):
                frappe.db.delete("Translation", row)
            frappe.db.commit()
        finally:
            frappe.set_user(self.original_user)

    def test_sync_http_failure_rolls_back_prior_batch(self):
        source = f"Catalog rollback transaction {uuid4().hex}"
        path = self._write_po([(source, "ترجمة اختبارية")])
        # Repeating the app leaves the endpoint's initial key snapshot unchanged.
        # Batch size one inserts the first batch into the request transaction;
        # the repeated key then hits the unique digest index and fails the request.
        response = self._post(
            "sync_translation_catalog",
            path,
            [self.test_app, self.test_app],
            dry_run=0,
            batch_size=1,
        )

        self.assertNotEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(
            frappe.db.count(
                "Translation",
                {
                    "language": "ar",
                    "source_text": source,
                    "ct_app": self.test_app,
                    "ct_is_catalog_entry": 1,
                },
            ),
            0,
            "the earlier batch must be rolled back when a later batch fails",
        )

    def test_sync_http_success_commits_catalog_rows(self):
        source = f"Catalog successful transaction {uuid4().hex}"
        path = self._write_po([(source, "ترجمة اختبارية")])

        response = self._post("sync_translation_catalog", path, dry_run=0, batch_size=1)

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["message"]["created"], 1)
        self.assertEqual(
            frappe.db.count(
                "Translation",
                {
                    "language": "ar",
                    "source_text": source,
                    "ct_app": self.test_app,
                    "ct_is_catalog_entry": 1,
                },
            ),
            1,
        )

    def test_reset_http_success_removes_requested_namespace_only(self):
        source = f"Catalog reset transaction {uuid4().hex}"
        doc = self._insert_stale_catalog_row(source)
        sentinel = self._insert_stale_catalog_row(f"Catalog sentinel {uuid4().hex}", self.sentinel_app)
        frappe.db.commit()
        path = self._write_po([])
        other_rows_before = self._other_catalog_snapshot()

        response = self._post("reset_catalog_overrides", path, dry_run=0)

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["message"]["deleted"], 1)
        self.assertFalse(frappe.db.exists("Translation", doc.name))
        self.assertTrue(frappe.db.exists("Translation", sentinel.name))
        self.assertEqual(self._other_catalog_snapshot(), other_rows_before)

    def test_reset_http_failure_rolls_back_earlier_deletion(self):
        rows = [self._insert_stale_catalog_row(f"Catalog reset rollback {uuid4().hex}") for _ in range(2)]
        sentinel = self._insert_stale_catalog_row(
            f"Catalog rollback sentinel {uuid4().hex}", self.sentinel_app
        )
        frappe.db.commit()
        path = self._write_po([])
        other_rows_before = self._other_catalog_snapshot()
        db_class = type(frappe.local.db)
        original_delete = db_class.delete
        delete_names = {doc.name for doc in rows}
        deletions = []

        def fail_second_delete(db, doctype, filters=None, debug=False, **kwargs):
            if doctype == "Translation" and isinstance(filters, str) and filters in delete_names:
                deletions.append(filters)
                if len(deletions) == 2:
                    raise RuntimeError("injected second catalog deletion failure")
            return original_delete(db, doctype, filters, debug=debug, **kwargs)

        with patch.object(db_class, "delete", new=fail_second_delete):
            response = self._post("reset_catalog_overrides", path, dry_run=0)

        self.assertNotEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(len(deletions), 2)
        self.assertTrue(all(frappe.db.exists("Translation", doc.name) for doc in rows))
        self.assertTrue(frappe.db.exists("Translation", sentinel.name))
        self.assertEqual(self._other_catalog_snapshot(), other_rows_before)

    def test_http_success_survives_postcommit_cache_failure(self):
        source = f"Catalog postcommit cache failure {uuid4().hex}"
        path = self._write_po([(source, "ترجمة اختبارية")])
        callback_ran = []
        logger_calls = []
        original_callback = translation_tools._clear_catalog_caches_after_commit

        def cache_failure_in_after_commit():
            callback_ran.append(True)
            with (
                patch.object(
                    frappe.cache,
                    "delete_value",
                    side_effect=RuntimeError("injected cache failure"),
                ),
                patch.object(
                    frappe,
                    "logger",
                    return_value=type(
                        "TestLogger",
                        (),
                        {"exception": lambda _self, *args: logger_calls.append(args)},
                    )(),
                ),
            ):
                original_callback()

        with patch.object(
            translation_tools,
            "_clear_catalog_caches_after_commit",
            new=cache_failure_in_after_commit,
        ):
            response = self._post("sync_translation_catalog", path, dry_run=0, batch_size=1)

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(callback_ran, [True])
        self.assertEqual(len(logger_calls), 2)
        self.assertEqual(response.get_json()["message"]["created"], 1)
        self.assertEqual(
            frappe.db.count(
                "Translation",
                {
                    "language": "ar",
                    "source_text": source,
                    "ct_app": self.test_app,
                    "ct_is_catalog_entry": 1,
                },
            ),
            1,
        )
