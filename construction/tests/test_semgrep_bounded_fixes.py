"""Focused regression tests for bounded Semgrep-driven compatibility fixes."""

import importlib
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import call, patch

import frappe

from construction import list_doctypes
from construction.api import scope_context_api
from construction.patches.v6_1 import rename_enable_scope_branch
from construction.patches.v8_2 import enable_global_export_menu_default
from construction.services import boq_rollup_audit


class TestListDoctypesCli(TestCase):
    def test_import_does_not_initialize_or_connect(self):
        with (
            patch.object(frappe, "init") as init,
            patch.object(frappe, "connect") as connect,
            patch.object(frappe, "destroy") as destroy,
        ):
            importlib.reload(list_doctypes)

        init.assert_not_called()
        connect.assert_not_called()
        destroy.assert_not_called()

    def test_main_connects_only_for_explicit_site_and_always_destroys(self):
        rows = [SimpleNamespace(name="BOQ Header", app_name="construction")]
        with (
            patch.object(frappe, "init") as init,
            patch.object(frappe, "connect") as connect,
            patch.object(frappe, "destroy") as destroy,
            patch.object(frappe, "get_list", return_value=rows) as get_list,
        ):
            result = list_doctypes.main(["--site", "fixture.local"])

        self.assertEqual(result, rows)
        init.assert_called_once_with("fixture.local")
        connect.assert_called_once_with()
        get_list.assert_called_once_with(
            "DocType", filters={"module": "construction"}, fields=["name", "app_name"]
        )
        destroy.assert_called_once_with()

    def test_main_destroys_site_when_query_fails(self):
        with (
            patch.object(frappe, "init"),
            patch.object(frappe, "connect"),
            patch.object(frappe, "destroy") as destroy,
            patch.object(frappe, "get_list", side_effect=RuntimeError("query failed")),
        ):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                list_doctypes.main(["--site", "fixture.local"])
        destroy.assert_called_once_with()


class TestBoundedFoundationFixes(TestCase):
    def test_aggregation_limit_translates_when_requested(self):
        with patch.object(boq_rollup_audit, "_", return_value="translated") as translate:
            self.assertEqual(boq_rollup_audit._aggregation_limit(), "translated")
        translate.assert_called_once()

    def test_scope_branch_patch_uses_singleton_database_api(self):
        with (
            patch.object(frappe.db, "table_exists", return_value=True, create=True),
            patch.object(frappe.db, "has_column", return_value=True, create=True),
            patch.object(frappe.db, "get_single_value", side_effect=[1, 0], create=True) as get_single,
            patch.object(frappe.db, "set_single_value", create=True) as set_single,
            patch.object(frappe.db, "commit", create=True) as commit,
        ):
            rename_enable_scope_branch.execute()

        self.assertEqual(
            get_single.call_args_list,
            [
                call("Construction Settings", "enable_scope_branch"),
                call("Construction Settings", "enable_scope_cost_center"),
            ],
        )
        set_single.assert_called_once_with("Construction Settings", "enable_scope_cost_center", 1)
        commit.assert_called_once_with()

    def test_export_menu_patch_uses_singleton_api_and_preserves_timestamp(self):
        with (
            patch.object(frappe.db, "get_single_value", return_value=0, create=True),
            patch.object(frappe.db, "set_single_value", create=True) as set_single,
        ):
            enable_global_export_menu_default.execute()

        set_single.assert_called_once_with(
            "Construction Settings",
            "enable_global_export_menu",
            1,
            update_modified=False,
        )

    def test_project_read_check_throws_and_keeps_exact_scope_fallback(self):
        denied = frappe.PermissionError("no doctype read permission")
        with (
            patch.object(frappe, "has_permission", side_effect=denied, create=True) as has_permission,
            patch.object(
                scope_context_api,
                "get_user_scope_context",
                return_value=SimpleNamespace(project="PRJ-1"),
            ),
            patch.object(frappe.db, "sql", return_value=[("Scoped Project",)], create=True),
        ):
            result = scope_context_api.get_project_display_name("PRJ-1")

        self.assertEqual(result, {"project_name": "Scoped Project"})
        has_permission.assert_called_once_with("Project", "read", throw=True)

    def test_project_read_check_rejects_nonmatching_scope_after_throw(self):
        def raise_error(message, error):
            raise error(message)

        with (
            patch.object(
                frappe,
                "has_permission",
                side_effect=frappe.PermissionError("no doctype read permission"),
                create=True,
            ),
            patch.object(
                scope_context_api,
                "get_user_scope_context",
                return_value=SimpleNamespace(project="PRJ-1"),
            ),
            patch.object(frappe, "throw", side_effect=raise_error, create=True),
        ):
            with self.assertRaises(frappe.PermissionError):
                scope_context_api.get_project_display_name("PRJ-2")
