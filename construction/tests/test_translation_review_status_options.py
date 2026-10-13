"""Check upgrade repair for the app-owned Translation review Select field."""

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parents[1]


class TestTranslationReviewStatusOptions(TestCase):
    def load_setup(self, initial_options):
        self.field = SimpleNamespace(name="Translation-ct_review_status", options=initial_options)
        self.writes = []
        self.cache_clears = []

        def get_value(doctype, filters, fields, as_dict=False):
            self.assertEqual(doctype, "Custom Field")
            self.assertEqual(filters, {"dt": "Translation", "fieldname": "ct_review_status"})
            self.assertEqual(fields, ["name", "options"])
            self.assertTrue(as_dict)
            return self.field

        def set_value(doctype, name, fieldname, value, update_modified=True):
            self.writes.append((doctype, name, fieldname, value, update_modified))
            self.field.options = value

        frappe = ModuleType("frappe")
        frappe.db = SimpleNamespace(get_value=get_value, set_value=set_value)
        frappe.clear_cache = lambda **kwargs: self.cache_clears.append(kwargs)
        frappe.log_error = lambda *args, **kwargs: None
        custom = ModuleType("frappe.custom.doctype.custom_field.custom_field")
        custom.create_custom_field = lambda *args, **kwargs: None

        modules = {
            "frappe": frappe,
            "frappe.custom": ModuleType("frappe.custom"),
            "frappe.custom.doctype": ModuleType("frappe.custom.doctype"),
            "frappe.custom.doctype.custom_field": ModuleType("frappe.custom.doctype.custom_field"),
            custom.__name__: custom,
        }
        scope = patch.dict("sys.modules", modules)
        scope.start()
        self.addCleanup(scope.stop)

        spec = importlib.util.spec_from_file_location(
            "translation_catalog_fields_under_test", APP_ROOT / "setup/translation_catalog_fields.py"
        )
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        return setup

    def test_upgrade_replaces_stale_options_and_invalidates_meta(self):
        setup = self.load_setup("\nPending\nApproved\nRejected")

        setup.ensure_custom_fields()

        expected = next(
            field["options"] for field in setup.CUSTOM_FIELDS if field["fieldname"] == "ct_review_status"
        )
        self.assertIn("Released", expected.splitlines())
        self.assertEqual(self.field.options, expected)
        self.assertEqual(
            self.writes,
            [("Custom Field", "Translation-ct_review_status", "options", expected, False)],
        )
        self.assertEqual(self.cache_clears, [{"doctype": "Translation"}])

    def test_upgrade_is_noop_when_options_are_current(self):
        setup = self.load_setup(
            next(field["options"] for field in setup_fields() if field["fieldname"] == "ct_review_status")
        )

        setup.ensure_custom_fields()

        self.assertEqual(self.writes, [])
        self.assertEqual(self.cache_clears, [])


def setup_fields():
    spec = importlib.util.spec_from_file_location(
        "translation_catalog_fields_for_options", APP_ROOT / "setup/translation_catalog_fields.py"
    )
    module = importlib.util.module_from_spec(spec)
    # CUSTOM_FIELDS is declarative, but importing needs the Frappe module.
    frappe = ModuleType("frappe")
    custom = ModuleType("frappe.custom.doctype.custom_field.custom_field")
    custom.create_custom_field = lambda *args, **kwargs: None
    with patch.dict("sys.modules", {"frappe": frappe, custom.__name__: custom}):
        spec.loader.exec_module(module)
    return module.CUSTOM_FIELDS


if __name__ == "__main__":
    main(verbosity=2)
