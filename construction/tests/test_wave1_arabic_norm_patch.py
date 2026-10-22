"""Stateful patch regressions runnable without a site or customer data.

Load the complete patch with a simulated Frappe schema/database boundary.
These tests do not establish native MariaDB or cloud migration success.
"""

import importlib.util
import os
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parents[1]
PATCH_PATH = APP_ROOT / "patches/v9_2/add_wave1_arabic_norm_fields.py"


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


class TestWave1ArabicNormPatch(TestCase):
    def setUp(self):
        self.schemas = {
            "Item": {"name", "item_name"},
            "Customer": {"name", "customer_name"},
            "Supplier": {"name", "supplier_name"},
        }
        self.columns = deepcopy(self.schemas)
        self.definitions = {}
        self.records = {dt: [] for dt in self.schemas}
        self.writes = []
        self.queries = []
        self.synced = []
        self.creation_error = None
        self.frappe = ModuleType("frappe")
        self.frappe.db = SimpleNamespace(
            exists=lambda kind, dt: dt == "Custom Field" or dt in self.schemas,
            get_value=self.get_value,
            set_value=self.set_value,
            has_column=lambda dt, field: field in self.columns[dt],
            updatedb=self.updatedb,
        )
        self.frappe.get_meta = lambda dt, **kwargs: SimpleNamespace(
            has_field=lambda field: field in self.schemas[dt]
        )
        self.frappe.clear_cache = lambda **kwargs: None
        self.frappe.log_error = lambda *args: None
        self.frappe.get_all = self.get_all
        custom_field = ModuleType("frappe.custom.doctype.custom_field.custom_field")
        custom_field.create_custom_field = self.create_custom_field
        registry = load_file("wave1_normalization", APP_ROOT / "services/bilingual_registry.py")
        self.modules = patch.dict(
            "sys.modules",
            {
                "frappe": self.frappe,
                custom_field.__name__: custom_field,
                "construction.services.bilingual_registry": registry,
            },
        )
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.migration = load_file("wave1_patch", os.environ.get("WAVE1_PATCH_UNDER_TEST", PATCH_PATH))

    def create_custom_field(self, dt, definition, **kwargs):
        if self.creation_error:
            raise self.creation_error
        field = definition["fieldname"]
        if field in self.schemas[dt]:
            raise AssertionError("Existing schema must be preserved")
        self.definitions[(dt, field)] = deepcopy(definition)
        self.schemas[dt].add(field)
        self.columns[dt].add(field)

    def updatedb(self, dt):
        self.synced.append(dt)
        self.columns[dt].update(self.schemas[dt])

    def get_value(self, dt, name, field=None):
        if dt == "Custom Field":
            key = (name["dt"], name["fieldname"])
            return "-".join(key) if key in self.definitions else None
        return next(row for row in self.records[dt] if row.name == name).get(field)

    def set_value(self, dt, name, field, value, **kwargs):
        if field not in self.columns[dt]:
            raise RuntimeError(f"Unknown column '{field}'")
        self.assertFalse(kwargs["update_modified"])
        self.writes.append((dt, name, field, value))
        next(row for row in self.records[dt] if row.name == name)[field] = value

    def get_all(self, dt, filters, fields, **kwargs):
        self.queries.append(dt)
        for field in set(fields) | set(filters):
            if field not in self.columns[dt]:
                raise RuntimeError(f"Unknown column '{field}' in 'SELECT'")
        source = next(iter(filters))
        return [
            Row({field: row.get(field) for field in fields}) for row in self.records[dt] if row.get(source)
        ]

    def seed_existing_fields(self):
        for target in self.migration.TARGETS:
            dt = target["dt"]
            for field in (target["source_field"], target["fieldname"]):
                self.create_custom_field(dt, {"fieldname": field, "label": "Customer-owned label"})

    def test_legacy_site_without_customer_and_supplier_arabic_columns(self):
        self.create_custom_field("Item", {"fieldname": "item_name_ar"})
        self.records["Item"] = [Row(name="ITEM-1", item_name_ar="أَحْمَـد")]
        self.migration.execute()
        for target in self.migration.TARGETS:
            self.assertIn(target["source_field"], self.columns[target["dt"]])
            self.assertIn(target["fieldname"], self.columns[target["dt"]])
        self.assertEqual(self.records["Item"][0]["item_name_ar_norm"], "احمد")

    def test_empty_legacy_site_provisions_all_three_masters(self):
        self.migration.execute()
        self.assertEqual(len(self.definitions), 6)
        self.assertEqual(self.writes, [])

    def test_existing_values_customizations_and_second_run_are_preserved(self):
        self.seed_existing_fields()
        self.records["Customer"] = [
            Row(
                name="CUST-1",
                customer_name="Existing Name",
                customer_name_in_arabic="أَحْمَـد",
                customer_name_in_arabic_norm="stale",
                modified="unchanged",
            ),
            Row(
                name="CUST-2",
                customer_name="No Arabic",
                customer_name_in_arabic="",
                customer_name_in_arabic_norm=None,
                modified="unchanged",
            ),
        ]
        definitions = deepcopy(self.definitions)
        self.migration.execute()
        row = self.records["Customer"][0]
        self.assertEqual(row["customer_name_in_arabic_norm"], "احمد")
        self.assertEqual(row["customer_name_in_arabic"], "أَحْمَـد")
        self.assertEqual(row["customer_name"], "Existing Name")
        self.assertEqual(row["modified"], "unchanged")
        records = deepcopy(self.records)
        writes = deepcopy(self.writes)
        self.migration.execute()
        self.assertEqual(self.records, records)
        self.assertEqual(self.writes, writes)
        self.assertEqual(self.definitions, definitions)
        self.assertIsNone(self.records["Customer"][1]["customer_name_in_arabic_norm"])

    def test_retry_repairs_metadata_with_missing_physical_columns(self):
        self.seed_existing_fields()
        self.columns["Customer"].remove("customer_name_in_arabic")
        self.columns["Supplier"].remove("supplier_name_in_arabic_norm")
        self.migration.execute()
        self.assertEqual(self.synced, ["Customer", "Supplier"])
        self.assertIn("customer_name_in_arabic", self.columns["Customer"])
        self.assertIn("supplier_name_in_arabic_norm", self.columns["Supplier"])

    def test_creation_failure_stops_before_backfill_and_can_be_retried(self):
        self.creation_error = RuntimeError("Simulated DDL failure")
        with self.assertRaisesRegex(RuntimeError, "Simulated DDL failure"):
            self.migration.execute()
        self.assertEqual(self.queries, [])
        self.creation_error = None
        self.migration.execute()
        self.assertEqual(len(self.definitions), 6)

    def test_absent_optional_doctype_is_not_created(self):
        del self.schemas["Supplier"]
        self.migration.execute()
        self.assertNotIn("Supplier", self.schemas)
        self.assertNotIn("Supplier", self.queries)


if __name__ == "__main__":
    main()
