"""Case-only sidebar migration regressions with a simulated Frappe boundary."""

import importlib.util
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

PATCH_PATH = Path(__file__).resolve().parents[1] / "patches/v9_17/align_legacy_sidebar_title_case.py"


class TestLegacySidebarTitlePatch(TestCase):
    def setUp(self):
        self.rows = [
            {
                "name": "Construction",
                "title": "Construction",
                "module": "construction",
                "app": "construction",
                "for_user": None,
                "modified": "unchanged",
                "items": [{"link_to": "Construction", "link_type": "Workspace"}],
            }
        ]
        self.modules = {"construction": "construction", "other": "other_app"}
        self.archive_exists = True
        self.writes = []
        self.cache_clears = []
        frappe = ModuleType("frappe")
        frappe.db = SimpleNamespace(
            table_exists=lambda dt: self.archive_exists,
            get_value=self.get_module,
            set_value=self.set_value,
        )
        frappe.get_all = self.get_all
        frappe.clear_cache = lambda **kwargs: self.cache_clears.append(kwargs)
        controller = ModuleType("frappe.desk.doctype.sidebar.sidebar")
        controller.Sidebar = object
        self.controller = controller
        context = patch.dict("sys.modules", {"frappe": frappe, controller.__name__: controller})
        context.start()
        self.addCleanup(context.stop)
        spec = importlib.util.spec_from_file_location("legacy_sidebar_patch", PATCH_PATH)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)

    def get_all(self, dt, filters, fields, **kwargs):
        self.assertEqual(dt, "Workspace Sidebar")
        self.assertEqual(filters, {"app": "construction", "for_user": ("is", "not set")})
        return [
            SimpleNamespace(**{field: row[field] for field in fields})
            for row in self.rows
            if row["app"] == filters["app"] and not row["for_user"]
        ]

    def get_module(self, dt, filters, field):
        self.assertEqual(dt, "Module Def")
        return next(
            (
                name
                for name, app in self.modules.items()
                if name.casefold() == filters["name"].casefold() and app == filters["app_name"]
            ),
            None,
        )

    def set_value(self, dt, name, field, value, update_modified=True):
        self.assertEqual(dt, "Workspace Sidebar")
        self.assertEqual(field, "title")
        self.assertFalse(update_modified)
        next(row for row in self.rows if row["name"] == name)[field] = value
        self.writes.append((name, field, value))

    def test_case_alias_is_aligned_without_renaming_or_changing_items(self):
        before = deepcopy(self.rows[0])
        self.migration.execute()
        self.assertEqual(self.rows[0]["title"], "construction")
        for field in before.keys() - {"title"}:
            self.assertEqual(self.rows[0][field], before[field])
        self.assertEqual(self.cache_clears, [{"doctype": "Workspace Sidebar"}])
        self.migration.execute()
        self.assertEqual(len(self.writes), 1)

    def test_converter_group_module_case_is_used(self):
        self.modules = {"Construction": "construction"}
        self.migration.execute()
        self.assertEqual(self.rows[0]["title"], self.rows[0]["module"])
        self.assertEqual(self.rows[0]["module"], "construction")

    def test_distinct_titles_other_apps_and_personal_arrangements_are_preserved(self):
        for title, app, user, module in [
            ("Construction Home", "construction", None, "construction"),
            ("Construction", "other_app", None, "construction"),
            ("Construction", "construction", "user@example.invalid", "construction"),
            ("Other", "construction", None, "other"),
        ]:
            with self.subTest(title=title, app=app, user=user):
                self.rows[0].update(title=title, app=app, for_user=user, module=module)
                before = deepcopy(self.rows)
                self.migration.execute()
                self.assertEqual(self.rows, before)
        self.assertEqual(self.writes, [])

    def test_missing_archive_is_safe(self):
        self.archive_exists = False
        self.migration.execute()
        self.assertEqual(self.writes, [])

    def test_older_frappe_without_sidebar_controller_is_unchanged(self):
        del self.controller.Sidebar
        self.migration.execute()
        self.assertEqual(self.writes, [])


if __name__ == "__main__":
    main()
