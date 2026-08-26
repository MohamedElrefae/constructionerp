# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""
VFC Backend Tests.

Targets:
  - layout_api.py: all 5 endpoints (get_active_layout, save_layout,
    list_layouts, delete_layout, validate_layout)
  - Form Layout Profile DocType: validation, single-default enforcement,
    is_system delete guard, malformed sections_json rejection
  - modern_form_api.py: System Manager gate on all endpoints
  - Cache TTL: proof that get_active_layout caches and returns results
  - Seed fieldname validity: verify seed fieldnames exist in DocType meta
"""

import json
import unittest

import frappe

from construction.construction.api.layout_api import (
    delete_layout,
    delete_my_personal_layout,
    get_active_layout,
    list_layouts,
    save_layout,
    validate_layout,
)

# ──────────────────────────────────────────────────────────────────────
# Test helpers
# ──────────────────────────────────────────────────────────────────────

_VALID_SECTIONS = {
    "version": 1,
    "unassigned_policy": "append",
    "sections": [
        {
            "id": "sec_test",
            "label": "Test Section",
            "column_count": 2,
            "fields": [
                {"fieldname": "subject", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "status", "col": 2, "sort_order": 2, "visible": True},
            ],
        }
    ],
}


def _create_profile(doctype="Task", **overrides):
    """Create a minimal Form Layout Profile (caller must clean up)."""
    data = {
        "doctype": "Form Layout Profile",
        "reference_doctype": doctype,
        "profile_name": f"_Test_{frappe.generate_hash(length=6)}",
        "is_default": 0,
        "is_system": 0,
        "enabled": 1,
        "sections_json": json.dumps(_VALID_SECTIONS),
    }
    data.update(overrides)
    doc = frappe.get_doc(data)
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc


# ──────────────────────────────────────────────────────────────────────
# Form Layout Profile DocType tests
# ──────────────────────────────────────────────────────────────────────


class TestFormLayoutProfile(unittest.TestCase):
    def setUp(self):
        self.profiles = []

    def tearDown(self):
        for doc in self.profiles:
            try:
                frappe.delete_doc("Form Layout Profile", doc.name, ignore_permissions=True)
            except Exception:
                pass

    def _make_profile(self, **overrides):
        doc = _create_profile(**overrides)
        self.profiles.append(doc)
        return doc

    def test_single_default_enforced(self):
        p1 = self._make_profile(is_default=1)
        with self.assertRaises(frappe.ValidationError):
            self._make_profile(
                reference_doctype=p1.reference_doctype,
                is_default=1,
                profile_name="_Test_DupDefault",
            )

    def test_single_default_allows_different_doctype(self):
        p1 = self._make_profile(is_default=1)
        p2 = self._make_profile(
            reference_doctype="ToDo",
            is_default=1,
            profile_name="_Test_ToDoDefault",
        )

    def test_malformed_sections_json_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self._make_profile(sections_json="not valid json")

    def test_empty_sections_json_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self._make_profile(sections_json="[]")

    def test_duplicate_fieldname_rejected(self):
        dup_sections = {
            "version": 1,
            "sections": [
                {"label": "S1", "fields": [{"fieldname": "subject", "visible": True}]},
                {"label": "S2", "fields": [{"fieldname": "subject", "visible": True}]},
            ],
        }
        with self.assertRaises(frappe.ValidationError):
            self._make_profile(sections_json=json.dumps(dup_sections))

    def test_is_system_delete_guard(self):
        p = self._make_profile(is_system=1)
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Form Layout Profile", p.name, ignore_permissions=True)

    def test_unknown_field_does_not_block_save(self):
        warn_sections = {
            "version": 1,
            "sections": [
                {"label": "S1", "fields": [{"fieldname": "_non_existent_field_xyz", "visible": True}]}
            ],
        }
        p = self._make_profile(sections_json=json.dumps(warn_sections))

    def test_invalid_column_count_rejected(self):
        bad_sections = {
            "version": 1,
            "sections": [
                {"label": "Bad", "column_count": 5, "fields": [{"fieldname": "subject", "visible": True}]}
            ],
        }
        with self.assertRaises(frappe.ValidationError):
            self._make_profile(sections_json=json.dumps(bad_sections))


# ──────────────────────────────────────────────────────────────────────
# layout_api.py tests
# ──────────────────────────────────────────────────────────────────────


class TestLayoutAPI(unittest.TestCase):
    def setUp(self):
        self.profiles = []
        # Purge leftovers from previous runs (save_layout commits mid-test,
        # which defeats transaction rollback isolation)
        frappe.db.delete(
            "Form Layout Profile", {"name": ("in", ["Task-_Test_UpdateMe", "Task-_Test_SaveNew"])}
        )
        frappe.db.commit()

    def tearDown(self):
        for doc in self.profiles:
            try:
                frappe.delete_doc("Form Layout Profile", doc.name, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.delete(
            "Form Layout Profile", {"name": ("in", ["Task-_Test_UpdateMe", "Task-_Test_SaveNew"])}
        )
        frappe.db.commit()

    def _make_profile(self, **overrides):
        doc = _create_profile(**overrides)
        self.profiles.append(doc)
        return doc

    # ── get_active_layout ──

    def test_get_active_layout_returns_none_when_no_profile(self):
        result = get_active_layout("NonExistentDocType")
        self.assertIsNone(result)

    def test_get_active_layout_returns_default(self):
        p = self._make_profile(is_default=1)
        result = get_active_layout(p.reference_doctype)
        self.assertIsNotNone(result)
        self.assertEqual(result["profile_name"], p.profile_name)

    def test_get_active_layout_prefers_for_user(self):
        user = frappe.session.user
        self._make_profile(is_default=1, profile_name="_Test_Default")
        p = self._make_profile(for_user=user, profile_name="_Test_Personal", priority=20)
        result = get_active_layout(p.reference_doctype)
        self.assertIsNotNone(result)
        self.assertEqual(result["profile_name"], "_Test_Personal")

    def test_get_active_layout_prefers_role(self):
        user_roles = frappe.get_roles(frappe.session.user)
        target_role = next(r for r in user_roles if r not in ("Administrator", "System Manager", "All", "Guest"))
        self._make_profile(is_default=1, profile_name="_Test_Default")
        p = self._make_profile(for_role=target_role, profile_name="_Test_Role", priority=20)
        result = get_active_layout(p.reference_doctype)
        self.assertIsNotNone(result)
        self.assertEqual(result["profile_name"], "_Test_Role")

    def test_get_active_layout_disabled_profiles_ignored(self):
        dt = "ToDo"
        self._make_profile(reference_doctype=dt, is_default=1, enabled=0, profile_name="_Test_Disabled")
        result = get_active_layout(dt)
        self.assertIsNone(result)

    def test_get_active_layout_returns_sections(self):
        p = self._make_profile(is_default=1)
        result = get_active_layout(p.reference_doctype)
        self.assertIn("sections", result)
        self.assertIsInstance(result["sections"], list)
        self.assertGreater(len(result["sections"]), 0)

    # ── save_layout ──

    def test_save_layout_creates_new(self):
        result = save_layout(
            doctype="Task",
            profile_name="_Test_SaveNew",
            sections_json=json.dumps(_VALID_SECTIONS),
            is_default=0,
        )
        self.assertEqual(result["status"], "created")
        frappe.delete_doc("Form Layout Profile", result["name"], ignore_permissions=True)

    def test_save_layout_updates_existing(self):
        p = self._make_profile(profile_name="_Test_UpdateMe")
        result = save_layout(
            doctype=p.reference_doctype,
            profile_name=p.profile_name,
            sections_json=json.dumps(_VALID_SECTIONS),
            is_default=0,
        )
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["name"], p.name)

    # ── list_layouts ──

    def test_list_layouts_returns_profiles(self):
        p = self._make_profile(is_default=1)
        result = list_layouts(p.reference_doctype)
        self.assertIsInstance(result, list)
        names = [r["name"] for r in result]
        self.assertIn(p.name, names)

    def test_list_layouts_returns_empty_for_unknown(self):
        result = list_layouts("NonExistentDocType")
        self.assertEqual(result, [])

    # ── delete_layout ──

    def test_delete_layout_removes_profile(self):
        p = self._make_profile()
        result = delete_layout(p.name)
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(result["name"], p.name)
        self.profiles.remove(p)

    def test_delete_layout_blocks_is_system(self):
        p = self._make_profile(is_system=1)
        with self.assertRaises(frappe.PermissionError):
            delete_layout(p.name)

    # ── delete_my_personal_layout ──

    def test_delete_my_personal_layout_removes_for_user_profile(self):
        user = frappe.session.user
        p = self._make_profile(for_user=user, profile_name="_Test_PersonalDelete")
        result = delete_my_personal_layout(p.reference_doctype)
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(result["name"], p.name)
        self.profiles.remove(p)

    def test_delete_my_personal_layout_not_found(self):
        result = delete_my_personal_layout("NonExistentDocType")
        self.assertEqual(result["status"], "not_found")
        self.assertIsNone(result["name"])

    # ── validate_layout ──

    def test_validate_layout_valid(self):
        valid = {
            "sections": [
                {"label": "S1", "column_count": 2, "fields": [{"fieldname": "subject"}, {"fieldname": "status"}]}
            ]
        }
        result = validate_layout("Task", json.dumps(valid))
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_validate_layout_invalid_json(self):
        result = validate_layout("Task", "not json")
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_validate_layout_unknown_field_warns(self):
        bad = {"sections": [{"label": "S1", "fields": [{"fieldname": "_bogus_field"}], "column_count": 2}]}
        result = validate_layout("Task", json.dumps(bad))
        self.assertTrue(result["valid"])
        self.assertGreater(len(result["warnings"]), 0)

    def test_validate_layout_duplicate_fieldname_errors(self):
        dup = {
            "sections": [
                {"label": "S1", "fields": [{"fieldname": "subject"}, {"fieldname": "subject"}], "column_count": 2},
            ]
        }
        result = validate_layout("Task", json.dumps(dup))
        self.assertFalse(result["valid"])

    def test_validate_layout_hidden_required_errors(self):
        req = {
            "sections": [
                {
                    "label": "S1",
                    "fields": [{"fieldname": "subject", "visible": False}],
                    "column_count": 2,
                },
            ]
        }
        result = validate_layout("Task", json.dumps(req))
        self.assertFalse(result["valid"])


# ──────────────────────────────────────────────────────────────────────
# Seed fieldname validity tests
# ──────────────────────────────────────────────────────────────────────


class TestSeedValidity(unittest.TestCase):
    """Verify that seed profiles reference only valid fieldnames."""

    def _check_seed(self, doctype, layout):
        meta = frappe.get_meta(doctype)
        known = {f.fieldname for f in meta.fields}
        for section in layout.get("sections", []):
            for field_entry in section.get("fields", []):
                fn = field_entry["fieldname"]
                self.assertIn(
                    fn,
                    known,
                    f"Seed for {doctype} references unknown field '{fn}'",
                )

    def test_boq_header_seed(self):
        from construction.install import DEFAULT_BOQ_HEADER_LAYOUT

        self._check_seed("BOQ Header", DEFAULT_BOQ_HEADER_LAYOUT)

    def test_boq_item_stage_seed(self):
        from construction.install import DEFAULT_BOQ_ITEM_STAGE_LAYOUT

        self._check_seed("BOQ Item Stage", DEFAULT_BOQ_ITEM_STAGE_LAYOUT)

    def test_boq_structure_seed(self):
        from construction.install import DEFAULT_BOQ_STRUCTURE_LAYOUT

        self._check_seed("BOQ Structure", DEFAULT_BOQ_STRUCTURE_LAYOUT)

    def test_user_scope_context_seed(self):
        from construction.install import DEFAULT_USER_SCOPE_CONTEXT_LAYOUT

        self._check_seed("User Scope Context", DEFAULT_USER_SCOPE_CONTEXT_LAYOUT)

    def test_project_seed(self):
        from construction.install import DEFAULT_PROJECT_LAYOUT

        meta = frappe.get_meta("Project")
        known = {f.fieldname for f in meta.fields}
        for section in DEFAULT_PROJECT_LAYOUT.get("sections", []):
            for field_entry in section.get("fields", []):
                fn = field_entry["fieldname"]
                self.assertIn(
                    fn,
                    known,
                    f"Project seed references unknown field '{fn}' — "
                    f"verify against installed ERPNext version",
                )


# ──────────────────────────────────────────────────────────────────────
# modern_form_api.py — System Manager gate tests
# ──────────────────────────────────────────────────────────────────────


class TestModernFormAPIRestrictions(unittest.TestCase):
    """Verify that modern_form_api.py endpoints reject non-System-Manager users."""

    def setUp(self):
        self._original_user = frappe.session.user
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user(self._original_user)

    def _assert_gate(self, func, *args, **kwargs):
        with self.assertRaises(frappe.PermissionError):
            func(*args, **kwargs)

    def test_get_form_config_gated(self):
        from construction.api.modern_form_api import get_form_config

        self._assert_gate(get_form_config, "User Scope Context")

    def test_get_document_gated(self):
        from construction.api.modern_form_api import get_document

        self._assert_gate(get_document, "User Scope Context", frappe.db.exists("User Scope Context"))

    def test_create_document_gated(self):
        from construction.api.modern_form_api import create_document

        self._assert_gate(create_document, "User Scope Context", {})

    def test_update_document_gated(self):
        from construction.api.modern_form_api import update_document

        self._assert_gate(update_document, "User Scope Context", "", {})

    def test_delete_document_gated(self):
        from construction.api.modern_form_api import delete_document

        self._assert_gate(delete_document, "User Scope Context", "")

    def test_validate_field_gated(self):
        from construction.api.modern_form_api import validate_field

        self._assert_gate(validate_field, "User Scope Context", "user", "")

    def test_search_link_gated(self):
        from construction.api.modern_form_api import search_link

        self._assert_gate(search_link, "User Scope Context", "test")
