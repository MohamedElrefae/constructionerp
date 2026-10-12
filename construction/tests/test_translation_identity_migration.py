"""Execute migration code against SQLite to regress SQL NULL and paging behavior.

Frappe schema/cache boundaries and MariaDB-specific index/DDL are simulated;
this suite does not qualify a native MariaDB or cloud migration.
"""

import hashlib
import importlib.util
import json
import os
import re
import sqlite3
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parents[1]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Row(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class TestTranslationIdentityMigration(TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE `tabTranslation` (
                name TEXT PRIMARY KEY, language TEXT, source_text TEXT, context TEXT,
                translated_text TEXT, ct_app TEXT, ct_is_catalog_entry INTEGER,
                ct_origin TEXT, ct_key_digest TEXT, ct_search_normalized TEXT,
                modified TEXT, creation TEXT
            )"""
        )
        self.columns = {row[1] for row in self.connection.execute("PRAGMA table_info(tabTranslation)")}
        self.write_count = 0
        self.cache_clears = 0
        frappe = ModuleType("frappe")
        frappe.throw = self.throw
        frappe.db = SimpleNamespace(
            sql=self.sql,
            get_value=self.get_value,
            set_value=self.set_value,
            has_column=lambda dt, field: field in self.columns,
            commit=self.connection.commit,
            delete=lambda *args: self.fail("Repair must preserve every Translation row"),
        )
        frappe.get_all = self.get_all
        translate = ModuleType("frappe.translate")
        translate.strip_html_tags = lambda value: re.sub(r"<[^>]*>", "", value)
        translate.clear_cache = self.clear_cache
        custom = ModuleType("frappe.custom.doctype.custom_field.custom_field")
        custom.create_custom_field = lambda *args, **kwargs: None
        modules = patch.dict(
            "sys.modules", {"frappe": frappe, translate.__name__: translate, custom.__name__: custom}
        )
        modules.start()
        self.addCleanup(modules.stop)
        self.setup = load_file(
            "identity_setup",
            os.environ.get("TRANSLATION_SETUP_UNDER_TEST", APP_ROOT / "setup/translation_catalog_fields.py"),
        )
        self.setup.ensure_custom_fields = lambda: None
        modules2 = patch.dict("sys.modules", {"construction.setup.translation_catalog_fields": self.setup})
        modules2.start()
        self.addCleanup(modules2.stop)
        self.legacy = load_file(
            "identity_v8_6",
            os.environ.get(
                "TRANSLATION_PATCH_UNDER_TEST",
                APP_ROOT / "patches/v8_6/add_translation_identity_and_dedup.py",
            ),
        )
        self.forward = load_file(
            "identity_v9_16", APP_ROOT / "patches/v9_16/repair_legacy_translation_identity.py"
        )

    @staticmethod
    def throw(message):
        raise RuntimeError(message)

    def clear_cache(self):
        self.cache_clears += 1

    def sql(self, query, values=None, as_dict=False):
        normalized = query.strip().lower()
        if normalized.startswith("show index"):
            return [("ct_translation_key_digest",)]
        if normalized.startswith("alter table"):
            return []  # MariaDB-specific DDL is outside this SQLite regression.
        query = re.sub(r"%\((\w+)\)s", r":\1", query)
        rows = self.connection.execute(query, values or {}).fetchall()
        return [Row(row) for row in rows] if as_dict else [tuple(row) for row in rows]

    def get_all(self, dt, fields, filters=None, order_by=None, limit_page_length=0, limit_start=0):
        conditions, parameters = [], []
        for field, value in (filters or {}).items():
            if isinstance(value, (list, tuple)):
                operator, value = value
                if operator == "in":
                    conditions.append(f"{field} IN ({','.join('?' for _ in value)})")
                    parameters.extend(value)
                else:
                    conditions.append(f"{field} {operator} ?")
                    parameters.append(value)
            else:
                conditions.append(f"{field} = ?")
                parameters.append(value)
        query = "SELECT " + ",".join(fields) + " FROM tabTranslation"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        if order_by:
            query += " ORDER BY " + order_by
        if limit_page_length:
            query += " LIMIT ? OFFSET ?"
            parameters.extend((limit_page_length, limit_start))
        return [Row(row) for row in self.connection.execute(query, parameters)]

    def get_value(self, dt, filters, field):
        rows = self.get_all(dt, fields=[field], filters=filters)
        return rows[0][field] if rows else None

    def set_value(self, dt, name, updates, update_modified=True):
        self.assertFalse(update_modified)
        self.assertTrue(set(updates) <= self.columns)
        assignments = ",".join(f"{field}=?" for field in updates)
        self.connection.execute(
            f"UPDATE tabTranslation SET {assignments} WHERE name=?", [*updates.values(), name]
        )
        self.write_count += 1

    def insert(self, name, catalog=None, digest=None, app="construction", context="", source=None):
        self.connection.execute(
            """INSERT INTO tabTranslation
            (name, language, source_text, translated_text, context, ct_app,
             ct_is_catalog_entry, ct_key_digest, modified, creation)
            VALUES (?, 'ar', ?, 'preserved translation', ?, ?, ?, ?, 'unchanged', 'unchanged')""",
            (name, source or f"Source {name}", context, app, catalog, digest),
        )

    def snapshot(self):
        return self.sql("SELECT * FROM tabTranslation ORDER BY name", as_dict=True)

    def test_legacy_patch_includes_null_catalog_flags_and_verifies(self):
        self.insert("legacy-null")
        self.insert("runtime-zero", catalog=0)
        self.insert("catalog-one", catalog=1)
        self.legacy.execute()
        rows = self.snapshot()
        self.assertTrue(all(row.ct_key_digest for row in rows))
        legacy = next(row for row in rows if row.name == "legacy-null")
        self.assertEqual(legacy.ct_is_catalog_entry, 0)
        self.assertEqual(legacy.ct_origin, "Site Override")

    def test_forward_patch_repairs_1000_null_digests_without_skipping_pages(self):
        for index in range(1000):
            self.insert(f"row-{index:04}", catalog=None if index % 2 else 0)
        before = self.snapshot()
        self.forward.execute()
        after = self.snapshot()
        self.assertEqual(len(after), 1000)
        self.assertTrue(all(row.ct_key_digest and row.ct_is_catalog_entry == 0 for row in after))
        for old, new in zip(before, after, strict=True):
            for field in (
                "name",
                "language",
                "source_text",
                "context",
                "translated_text",
                "ct_app",
                "modified",
            ):
                self.assertEqual(old[field], new[field])
        self.assertEqual(self.write_count, 1000)
        self.forward.execute()
        self.assertEqual(self.write_count, 1000)
        self.assertEqual(self.snapshot(), after)
        self.assertEqual(self.cache_clears, 1)

    def test_hook_repairs_null_and_empty_digests_and_preserves_valid_rows(self):
        self.insert("missing-null", catalog=0)
        self.insert("missing-empty", catalog=0, digest="")
        self.insert("valid", catalog=0, digest="existing-digest")
        self.assertEqual(self.setup.ensure_translation_identity(), {"backfilled": 2})
        self.assertEqual(self.get_value("Translation", {"name": "valid"}, "ct_key_digest"), "existing-digest")

    def test_catalog_runtime_and_context_use_distinct_canonical_identities(self):
        self.insert("catalog", catalog=1, source="Shared")
        self.insert("runtime", catalog=None, app="other-app", source="Shared")
        self.insert("context", catalog=0, context="Button", source="Shared")
        self.forward.execute()
        rows = {row.name: row for row in self.snapshot()}
        self.assertEqual(len({row.ct_key_digest for row in rows.values()}), 3)
        payload = ["ar", "Shared", "", "runtime"]
        expected = hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(rows["runtime"].ct_key_digest, expected)
        self.assertIsNone(rows["catalog"].ct_origin)

    def test_collision_with_existing_identity_refuses_without_deleting_rows(self):
        digest = self.legacy._digest("ar", "Shared", "", "", False)
        self.insert("existing", catalog=0, digest=digest, source="Shared")
        self.insert("legacy", source="Shared")
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "identity collision"):
            self.forward.execute()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.write_count, 0)

    def test_collision_between_pending_rows_is_detected_before_page_writes(self):
        self.insert("duplicate-1", source="Shared")
        self.insert("duplicate-2", source="Shared")
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "identity collision"):
            self.forward.execute()
        self.assertEqual(self.snapshot(), before)

    def test_existing_digest_with_null_flag_becomes_visible_to_runtime_loader(self):
        digest = self.legacy._digest("ar", "Shared", "", "", False)
        self.insert("legacy", digest=digest, source="Shared")
        self.forward.execute()
        runtime = self.sql("SELECT name FROM tabTranslation WHERE ct_is_catalog_entry = 0")
        self.assertEqual(runtime, [("legacy",)])


if __name__ == "__main__":
    main()
