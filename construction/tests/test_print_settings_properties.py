"""
Property-based tests for Print Settings Dialog - Server Column Config Filtering
Tag: Feature: print-settings-dialog, Property 8: Server Column Config Filtering

Tests the BOQExportService.apply_column_config static method using hypothesis.
"""

import unittest
import json
import sys
from unittest.mock import MagicMock, patch

# Mock the frappe module before importing the service
frappe_mock = MagicMock()
frappe_mock.parse_json = lambda s: json.loads(s)
frappe_mock.log_error = MagicMock()
# Make @frappe.whitelist() a pass-through decorator so API functions stay callable
frappe_mock.whitelist = lambda *args, **kwargs: (lambda fn: fn)
frappe_mock._ = lambda s: s
sys.modules["frappe"] = frappe_mock
sys.modules["frappe.utils"] = MagicMock()
sys.modules["frappe.desk"] = MagicMock()
sys.modules["frappe.desk.treeview"] = MagicMock()

from hypothesis import given, strategies as st, settings, assume
from construction.construction.services.boq_export_service import BOQExportService


# --- Strategies ---

def column_key_strategy():
    """Generate unique column keys like 'col_0', 'col_1', etc."""
    return st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz_",
        min_size=2,
        max_size=15,
    ).filter(lambda s: s[0].isalpha())


def default_columns_strategy(min_size=1, max_size=8):
    """Generate a list of default column dicts with unique keys."""
    return st.lists(
        st.fixed_dictionaries({
            "key": column_key_strategy(),
            "label": st.text(min_size=1, max_size=30),
            "width": st.integers(min_value=1, max_value=100),
        }),
        min_size=min_size,
        max_size=max_size,
    ).filter(lambda cols: len({c["key"] for c in cols}) == len(cols))


def column_config_entry_strategy(field_keys):
    """Generate a ColumnConfig entry for one of the given field_keys."""
    return st.fixed_dictionaries({
        "field_key": st.sampled_from(field_keys),
        "label": st.text(min_size=1, max_size=30),
        "width": st.integers(min_value=1, max_value=100),
        "visible": st.booleans(),
        "sort_order": st.integers(min_value=0, max_value=100),
    })


class TestServerColumnConfigFiltering(unittest.TestCase):
    """
    Property 8: Server Column Config Filtering

    For any set of default columns and any valid Column_Configuration JSON,
    apply_column_config SHALL return only the columns where visible is True,
    sorted by sort_order, with each column's width matching the config.
    When Column_Configuration is None, it SHALL return all default columns
    in default order. When the config contains a field_key not present in
    the default columns, that key SHALL be skipped.

    **Validates: Requirements 9.1, 9.2, 9.4**
    """

    def setUp(self):
        """Reset frappe mock state before each test."""
        frappe_mock.log_error.reset_mock()

    # --- Property 8a: None config returns defaults unchanged ---
    @given(defaults=default_columns_strategy())
    @settings(max_examples=100)
    def test_none_config_returns_defaults(self, defaults):
        """
        **Validates: Requirements 9.1, 9.2**
        When column_config_json is None, apply_column_config returns
        default_columns unchanged.
        """
        result = BOQExportService.apply_column_config(defaults, None)
        self.assertEqual(result, defaults)

    # --- Property 8b: Valid config returns only visible columns sorted by sort_order ---
    @given(defaults=default_columns_strategy(), data=st.data())
    @settings(max_examples=100)
    def test_visible_columns_sorted_by_sort_order(self, defaults, data):
        """
        **Validates: Requirements 9.1, 9.2**
        Valid config returns only visible columns sorted by sort_order,
        with width matching the config.
        """
        field_keys = [c["key"] for c in defaults]

        # Generate a config entry for each default column with unique sort_orders
        config = []
        sort_orders = data.draw(
            st.lists(
                st.integers(min_value=0, max_value=200),
                min_size=len(field_keys),
                max_size=len(field_keys),
                unique=True,
            )
        )
        for i, key in enumerate(field_keys):
            visible = data.draw(st.booleans())
            width = data.draw(st.integers(min_value=1, max_value=100))
            config.append({
                "field_key": key,
                "label": defaults[i]["label"],
                "width": width,
                "visible": visible,
                "sort_order": sort_orders[i],
            })

        config_json = json.dumps(config)
        result = BOQExportService.apply_column_config(defaults, config_json)

        # Expected: visible entries sorted by sort_order
        expected_visible = sorted(
            [c for c in config if c["visible"]],
            key=lambda c: c["sort_order"],
        )

        # Result length must match visible count
        self.assertEqual(len(result), len(expected_visible))

        # Each result column must match expected key, label from defaults, and width from config
        defaults_map = {c["key"]: c for c in defaults}
        for res, exp in zip(result, expected_visible):
            self.assertEqual(res["key"], exp["field_key"])
            self.assertEqual(res["label"], defaults_map[exp["field_key"]]["label"])
            self.assertEqual(res["width"], exp["width"])

    # --- Property 8c: Unknown field_keys in config are skipped ---
    @given(defaults=default_columns_strategy(), data=st.data())
    @settings(max_examples=100)
    def test_unknown_keys_skipped(self, defaults, data):
        """
        **Validates: Requirements 9.4**
        Config entries with field_keys not in default_columns are skipped
        and a warning is logged.
        """
        frappe_mock.log_error.reset_mock()

        field_keys = [c["key"] for c in defaults]

        # Generate 1-3 unknown keys guaranteed not in defaults
        unknown_keys = data.draw(
            st.lists(
                column_key_strategy().filter(lambda k: k not in field_keys),
                min_size=1,
                max_size=3,
                unique=True,
            )
        )

        # Build config with only unknown keys, all visible
        config = []
        for i, key in enumerate(unknown_keys):
            config.append({
                "field_key": key,
                "label": f"Unknown {i}",
                "width": 10,
                "visible": True,
                "sort_order": i,
            })

        config_json = json.dumps(config)
        result = BOQExportService.apply_column_config(defaults, config_json)

        # All unknown keys should be skipped → empty result
        self.assertEqual(len(result), 0)

        # frappe.log_error should have been called for each unknown key
        self.assertEqual(frappe_mock.log_error.call_count, len(unknown_keys))

    # --- Property 8d: Invalid JSON falls back to defaults ---
    @given(defaults=default_columns_strategy())
    @settings(max_examples=100)
    def test_invalid_json_falls_back_to_defaults(self, defaults):
        """
        **Validates: Requirements 9.2**
        When column_config_json is invalid JSON, apply_column_config
        falls back to default_columns.
        """
        frappe_mock.log_error.reset_mock()

        # Make frappe.parse_json raise on bad input
        original_parse = frappe_mock.parse_json
        frappe_mock.parse_json = MagicMock(side_effect=ValueError("bad json"))

        try:
            result = BOQExportService.apply_column_config(defaults, "{not valid json!!")
            self.assertEqual(result, defaults)
            frappe_mock.log_error.assert_called()
        finally:
            frappe_mock.parse_json = original_parse


if __name__ == "__main__":
    unittest.main()


# --- Unit Tests for API Endpoint column_config Passthrough ---
# Task 7.4: Verify API endpoints accept column_config and pass it to export service
# **Validates: Requirements 9.2, 9.3**

# Pre-register the Frappe-style import path used inside boq_api.py functions:
#   from construction.services.boq_export_service import BOQExportService
# We create a mock module at that path so the local import resolves to our mock.
_mock_export_module = MagicMock()
sys.modules["construction.services"] = MagicMock()
sys.modules["construction.services.boq_export_service"] = _mock_export_module

from construction.construction.api.boq_api import (
    export_boq_pdf,
    export_boq_header_pdf,
    export_boq_excel,
    export_boq_header_excel,
)


class TestAPIColumnConfigPassthrough(unittest.TestCase):
    """
    Unit tests for API endpoint column_config passthrough.

    Verifies that each of the four export API endpoints in boq_api.py:
    1. Accepts a column_config parameter and passes it to the BOQExportService method
    2. Is backward-compatible when column_config is omitted (None)

    **Validates: Requirements 9.2, 9.3**
    """

    def setUp(self):
        """Set up common mock return value and reset the mock service."""
        self.success_result = {
            "success": True,
            "file_url": "/files/test.pdf",
            "file_name": "test.pdf",
        }
        self.sample_column_config = json.dumps([
            {"field_key": "wbs_code", "label": "WBS Code", "width": 15, "visible": True, "sort_order": 0},
            {"field_key": "title", "label": "Title", "width": 40, "visible": True, "sort_order": 1},
        ])
        # Reset the mock service before each test
        self.mock_service = _mock_export_module.BOQExportService
        self.mock_service.reset_mock()

    # --- export_boq_pdf ---

    def test_export_boq_pdf_passes_column_config(self):
        """export_boq_pdf passes column_config to BOQExportService.export_to_pdf."""
        self.mock_service.export_to_pdf.return_value = self.success_result

        result = export_boq_pdf(boq_header="BOQ-001", column_config=self.sample_column_config)

        self.mock_service.export_to_pdf.assert_called_once_with("BOQ-001", self.sample_column_config)
        self.assertTrue(result["success"])

    def test_export_boq_pdf_none_column_config(self):
        """export_boq_pdf passes None when column_config is omitted (backward-compatible)."""
        self.mock_service.export_to_pdf.return_value = self.success_result

        result = export_boq_pdf(boq_header="BOQ-001")

        self.mock_service.export_to_pdf.assert_called_once_with("BOQ-001", None)
        self.assertTrue(result["success"])

    # --- export_boq_header_pdf ---

    def test_export_boq_header_pdf_passes_column_config(self):
        """export_boq_header_pdf passes column_config to BOQExportService.export_header_to_pdf."""
        self.mock_service.export_header_to_pdf.return_value = self.success_result

        result = export_boq_header_pdf(boq_header="BOQ-001", column_config=self.sample_column_config)

        self.mock_service.export_header_to_pdf.assert_called_once_with("BOQ-001", self.sample_column_config)
        self.assertTrue(result["success"])

    def test_export_boq_header_pdf_none_column_config(self):
        """export_boq_header_pdf passes None when column_config is omitted (backward-compatible)."""
        self.mock_service.export_header_to_pdf.return_value = self.success_result

        result = export_boq_header_pdf(boq_header="BOQ-001")

        self.mock_service.export_header_to_pdf.assert_called_once_with("BOQ-001", None)
        self.assertTrue(result["success"])

    # --- export_boq_excel ---

    def test_export_boq_excel_passes_column_config(self):
        """export_boq_excel passes column_config to BOQExportService.export_to_excel."""
        self.mock_service.export_to_excel.return_value = self.success_result

        result = export_boq_excel(boq_header="BOQ-001", column_config=self.sample_column_config)

        self.mock_service.export_to_excel.assert_called_once_with("BOQ-001", self.sample_column_config)
        self.assertTrue(result["success"])

    def test_export_boq_excel_none_column_config(self):
        """export_boq_excel passes None when column_config is omitted (backward-compatible)."""
        self.mock_service.export_to_excel.return_value = self.success_result

        result = export_boq_excel(boq_header="BOQ-001")

        self.mock_service.export_to_excel.assert_called_once_with("BOQ-001", None)
        self.assertTrue(result["success"])

    # --- export_boq_header_excel ---

    def test_export_boq_header_excel_passes_column_config(self):
        """export_boq_header_excel passes column_config to BOQExportService.export_header_to_excel."""
        self.mock_service.export_header_to_excel.return_value = self.success_result

        result = export_boq_header_excel(boq_header="BOQ-001", column_config=self.sample_column_config)

        self.mock_service.export_header_to_excel.assert_called_once_with("BOQ-001", self.sample_column_config)
        self.assertTrue(result["success"])

    def test_export_boq_header_excel_none_column_config(self):
        """export_boq_header_excel passes None when column_config is omitted (backward-compatible)."""
        self.mock_service.export_header_to_excel.return_value = self.success_result

        result = export_boq_header_excel(boq_header="BOQ-001")

        self.mock_service.export_header_to_excel.assert_called_once_with("BOQ-001", None)
        self.assertTrue(result["success"])
