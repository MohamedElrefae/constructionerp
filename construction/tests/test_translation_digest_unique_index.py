"""Regression tests for the Translation digest unique-index repair."""

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

SETUP_PATH = Path(__file__).resolve().parents[1] / "setup" / "translation_catalog_fields.py"


def load_setup():
    spec = importlib.util.spec_from_file_location("translation_digest_index_setup", SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeDB:
    def __init__(self, indexes=(), incomplete=0, duplicates=()):
        self.indexes = list(indexes)
        self.incomplete = incomplete
        self.duplicates = list(duplicates)
        self.alter_count = 0
        self.commit_count = 0
        self.alter_error = None

    @staticmethod
    def _index(name="ct_translation_key_digest", non_unique=0, seq=1, column="ct_key_digest", sub_part=None):
        return {
            "Key_name": name,
            "Non_unique": non_unique,
            "Seq_in_index": seq,
            "Column_name": column,
            "Sub_part": sub_part,
        }

    def has_column(self, doctype, fieldname):
        return (doctype, fieldname) == ("Translation", "ct_key_digest")

    def sql(self, query, values=None, as_dict=False):
        normalized = " ".join(query.split()).upper()
        if normalized.startswith("SHOW INDEX"):
            index_name = (values or {}).get("name")
            return [row.copy() for row in self.indexes if row["Key_name"] == index_name]
        if normalized.startswith("SELECT COUNT(*)"):
            return [(self.incomplete,)]
        if normalized.startswith("SELECT CT_KEY_DIGEST"):
            return [row.copy() for row in self.duplicates]
        if normalized.startswith("ALTER TABLE"):
            self.alter_count += 1
            if self.alter_error:
                raise self.alter_error
            self.indexes.append(self._index())
            return []
        raise AssertionError(f"Unexpected SQL: {query}")

    def commit(self):
        self.commit_count += 1


class TestTranslationDigestUniqueIndex(TestCase):
    def setUp(self):
        self.db = FakeDB()
        frappe = ModuleType("frappe")
        frappe._ = lambda message: message
        frappe.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
        frappe.db = self.db
        custom = ModuleType("frappe.custom.doctype.custom_field.custom_field")
        custom.create_custom_field = lambda *_args, **_kwargs: None
        packages = {
            name: ModuleType(name)
            for name in (
                "frappe.custom",
                "frappe.custom.doctype",
                "frappe.custom.doctype.custom_field",
            )
        }
        for package in packages.values():
            package.__path__ = []
        modules = patch.dict(
            "sys.modules",
            {"frappe": frappe, **packages, custom.__name__: custom},
        )
        modules.start()
        self.addCleanup(modules.stop)
        self.setup = load_setup()

    def test_creates_and_verifies_named_full_unique_single_column_index(self):
        result = self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(result, {"created": True, "verified": True})
        self.assertEqual(self.db.alter_count, 1)
        self.assertEqual(self.db.commit_count, 1)
        self.assertEqual(self.db.indexes, [self.db._index()])

    def test_exact_existing_index_is_idempotent(self):
        self.db.indexes = [self.db._index()]
        result = self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(result, {"created": False, "verified": True})
        self.assertEqual(self.db.alter_count, 0)

    def test_existing_unique_index_does_not_hide_incomplete_rows(self):
        self.db.indexes = [self.db._index()]
        self.db.incomplete = 1
        with self.assertRaisesRegex(RuntimeError, "digest rows are incomplete"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.alter_count, 0)

    def test_different_name_nonunique_index_is_preserved_and_exact_unique_added(self):
        old_index = self.db._index(name="ct_key_digest_index", non_unique=1)
        self.db.indexes = [old_index]
        result = self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(result, {"created": True, "verified": True})
        self.assertEqual(self.db.indexes, [old_index, self.db._index()])

    def test_incomplete_rows_fail_before_ddl(self):
        self.db.incomplete = 1
        with self.assertRaisesRegex(RuntimeError, "digest rows are incomplete"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.alter_count, 0)

    def test_duplicate_digests_fail_before_ddl(self):
        self.db.duplicates = [{"ct_key_digest": "duplicate"}]
        with self.assertRaisesRegex(RuntimeError, "duplicate digests remain"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.alter_count, 0)

    def test_nonunique_index_with_target_name_fails_closed(self):
        self.db.indexes = [self.db._index(non_unique=1)]
        with self.assertRaisesRegex(RuntimeError, "unexpected definition"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.alter_count, 0)

    def test_composite_or_prefix_target_index_fails_closed(self):
        self.db.indexes = [
            self.db._index(seq=1),
            self.db._index(seq=2, column="language"),
        ]
        with self.assertRaisesRegex(RuntimeError, "unexpected definition"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.alter_count, 0)

        self.db.indexes = [self.db._index(sub_part=32)]
        with self.assertRaisesRegex(RuntimeError, "unexpected definition"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.alter_count, 0)

    def test_missing_digest_column_is_explicitly_skipped(self):
        self.db.has_column = lambda *_args: False
        result = self.setup.ensure_translation_digest_unique_index()
        self.assertTrue(result["skipped"])
        self.assertEqual(self.db.alter_count, 0)

    def test_ddl_errors_propagate_after_pre_ddl_commit(self):
        self.db.alter_error = RuntimeError("DDL rejected")
        with self.assertRaisesRegex(RuntimeError, "DDL rejected"):
            self.setup.ensure_translation_digest_unique_index()
        self.assertEqual(self.db.commit_count, 1)
        self.assertEqual(self.db.alter_count, 1)

    def test_setup_apply_leaves_transaction_commit_to_caller(self):
        with patch.object(self.setup, "ensure_custom_fields") as ensure_fields:
            self.setup.apply()
        ensure_fields.assert_called_once_with()
        self.assertEqual(self.db.commit_count, 0)


if __name__ == "__main__":
    main()
