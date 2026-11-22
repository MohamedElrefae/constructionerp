"""Offline vectors for the framework-independent execution tree rules."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "construction" / "services" / "execution_tree_rules.py"
SPEC = importlib.util.spec_from_file_location("execution_tree_rules", MODULE_PATH)
rules = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rules)


def node(name, *, project="PROJ-1", parent=None, group=False, code=None, title=None, disabled=False):
    return {
        "name": name,
        "title": title or f"Title {name}",
        "project": project,
        "company": "Company A",
        "parent_node": parent,
        "is_group": 1 if group else 0,
        "disabled": 1 if disabled else 0,
        "ebs_code": code or f"EBS-{name.split('-')[-1].rjust(4, '0')}",
        "modified": "2026-11-18 00:00:00.000000",
    }


def test_code_formatting_pads_and_widens():
    assert rules.format_execution_code(1) == "EBS-0001"
    assert rules.format_execution_code(9999) == "EBS-9999"
    assert rules.format_execution_code(10000) == "EBS-10000"
    assert rules.format_execution_code(123456) == "EBS-123456"


def test_code_parsing_rejects_malformed_values():
    assert rules.parse_execution_code("EBS-0007") == 7
    for value in ("EBS-1", "EBS-", "XBS-0001", "EBS-00A1", "", "EBS-00000000000000000000"):
        with pytest.raises(rules.RuleViolation):
            rules.parse_execution_code(value)


def test_counter_widening_and_overflow_are_bounded():
    assert rules.next_counter_value(0) == 1
    assert rules.next_counter_value(9999) == 10000
    assert rules.validate_counter_value(rules.MAX_COUNTER_VALUE) == rules.MAX_COUNTER_VALUE
    with pytest.raises(rules.RuleViolation):
        rules.next_counter_value(rules.MAX_COUNTER_VALUE)
    for bad in (-1, "abc", True, None, rules.MAX_COUNTER_VALUE + 1):
        with pytest.raises(rules.RuleViolation):
            rules.validate_counter_value(bad)


def test_build_tree_orders_roots_and_children_deterministically():
    nodes = [
        node("EBN-3", code="EBS-0003"),
        node("EBN-1", group=True, code="EBS-0001"),
        node("EBN-2", parent="EBN-1", code="EBS-0002"),
        node("EBN-10", parent="EBN-1", code="EBS-0010"),
    ]
    ordered = rules.build_tree(nodes, project="PROJ-1")
    assert [item["name"] for item in ordered] == ["EBN-1", "EBN-2", "EBN-10", "EBN-3"]
    assert ordered[0]["depth"] == 1
    assert ordered[1]["depth"] == 2


def test_build_tree_rejects_cross_project_and_unknown_parent():
    with pytest.raises(rules.RuleViolation):
        rules.build_tree([node("EBN-1")], project="OTHER")
    with pytest.raises(rules.RuleViolation):
        rules.build_tree([node("EBN-1", parent="EBN-9")], project="PROJ-1")


def test_build_tree_rejects_non_group_parent_and_self_parent():
    with pytest.raises(rules.RuleViolation):
        rules.build_tree([node("EBN-1"), node("EBN-2", parent="EBN-1")], project="PROJ-1")
    with pytest.raises(rules.RuleViolation):
        rules.build_tree([node("EBN-1", parent="EBN-1", group=True)], project="PROJ-1")


def test_build_tree_detects_cycles():
    with pytest.raises(rules.RuleViolation):
        rules.build_tree(
            [
                node("EBN-1", parent="EBN-2", group=True),
                node("EBN-2", parent="EBN-1", group=True),
            ],
            project="PROJ-1",
        )


def test_build_tree_rejects_duplicate_names():
    with pytest.raises(rules.RuleViolation):
        rules.build_tree([node("EBN-1"), node("EBN-1")], project="PROJ-1")


def test_depth_limit_counts_root_as_level_one():
    nodes = []
    parent = None
    for level in range(1, rules.MAX_DEPTH + 1):
        name = f"EBN-{level}"
        nodes.append(node(name, parent=parent, group=level < rules.MAX_DEPTH))
        parent = name
    ordered = rules.build_tree(nodes, project="PROJ-1")
    assert max(item["depth"] for item in ordered) == rules.MAX_DEPTH
    nodes.append(node("EBN-99", parent=parent, group=True))
    with pytest.raises(rules.RuleViolation):
        rules.build_tree(nodes, project="PROJ-1")


def test_node_limit_is_enforced_before_materialization():
    fake = [{"name": f"EBN-{index}"} for index in range(rules.MAX_NODES + 1)]
    with pytest.raises(rules.RuleViolation) as error:
        rules.build_tree(fake, project="PROJ-1")
    assert error.value.code == "tree_too_large"


def test_create_parent_checks_group_existence_and_depth():
    nodes = [node("EBN-1", group=True), node("EBN-2", parent="EBN-1")]
    assert rules.validate_create_parent(nodes, project="PROJ-1", parent_node="EBN-1") == 2
    with pytest.raises(rules.RuleViolation):
        rules.validate_create_parent(nodes, project="PROJ-1", parent_node="EBN-2")
    with pytest.raises(rules.RuleViolation):
        rules.validate_create_parent(nodes, project="PROJ-1", parent_node="EBN-9")


def test_move_rejects_cycles_and_depth_overrun():
    nodes = [
        node("EBN-1", group=True),
        node("EBN-2", parent="EBN-1", group=True),
        node("EBN-3", parent="EBN-2"),
    ]
    assert rules.validate_move(nodes, project="PROJ-1", name="EBN-3", new_parent="EBN-1") == 2
    with pytest.raises(rules.RuleViolation):
        rules.validate_move(nodes, project="PROJ-1", name="EBN-1", new_parent="EBN-2")
    with pytest.raises(rules.RuleViolation):
        rules.validate_move(nodes, project="PROJ-1", name="EBN-1", new_parent="EBN-1")


def test_move_counts_subtree_height_against_depth_limit():
    nodes = []
    parent = None
    for level in range(1, rules.MAX_DEPTH):
        name = f"EBN-{level}"
        nodes.append(node(name, parent=parent, group=True))
        parent = name
    nodes.append(node("EBN-20", parent=parent))
    with pytest.raises(rules.RuleViolation):
        rules.validate_move(nodes, project="PROJ-1", name="EBN-1", new_parent="EBN-20")


def test_delete_and_group_change_rules():
    nodes = [node("EBN-1", group=True), node("EBN-2", parent="EBN-1")]
    assert rules.validate_delete(nodes, project="PROJ-1", name="EBN-2") == "EBN-2"
    with pytest.raises(rules.RuleViolation):
        rules.validate_delete(nodes, project="PROJ-1", name="EBN-1")
    with pytest.raises(rules.RuleViolation):
        rules.validate_group_change(nodes, project="PROJ-1", name="EBN-1", new_is_group=False)
    assert rules.validate_group_change(nodes, project="PROJ-1", name="EBN-2", new_is_group=True)


def test_input_validation_rejects_control_and_oversized_values():
    with pytest.raises(rules.RuleViolation):
        rules.validate_title("   ")
    with pytest.raises(rules.RuleViolation):
        rules.validate_title("x" * (rules.MAX_TITLE_LENGTH + 1))
    with pytest.raises(rules.RuleViolation):
        rules.validate_title("bad\x00title")
    with pytest.raises(rules.RuleViolation):
        rules.validate_boolean("true")
    assert rules.validate_boolean(0) is False
    assert rules.validate_boolean(True) is True
    with pytest.raises(rules.RuleViolation):
        rules.reject_unknown_arguments({"project": "P", "sql": "x"}, {"project"})
    with pytest.raises(rules.RuleViolation):
        rules.validate_request_size({"blob": "x" * (rules.MAX_REQUEST_BYTES + 1)})


def test_summaries_expose_only_allowlisted_fields():
    summary = rules.node_summary(node("EBN-1", group=True))
    assert set(summary) == set(rules.NODE_SUMMARY_FIELDS)
    assert "owner" not in summary


def test_expected_modified_staleness_is_exact():
    value = "2026-11-18 10:00:00.123456"
    assert rules.validate_expected_modified(value) == value
    assert rules.stale_version(value, value) is False
    assert rules.stale_version(value, "2026-11-18 10:00:00.000000") is True
    with pytest.raises(rules.RuleViolation):
        rules.validate_expected_modified("../bad", required=True)
    with pytest.raises(rules.RuleViolation):
        rules.validate_expected_modified(None, required=True)


def test_unknown_operation_is_refused():
    with pytest.raises(rules.RuleViolation):
        rules.validate_operation("drop_table")


HOOK_TEMPLATE = """
has_permission = {}
permission_query_conditions = {"*": "construction.overrides.scope_query.add_scope_conditions"}
override_doctype_class = {}
extend_doctype_class = {}
get_child_provider = {}
doc_events = {
    "*": {"validate": "construction.overrides.scope_enforcement.validate"},
    "Project": {
        "validate": ["construction.services.bilingual_service.enforce_bilingual_arabic_policy", "construction.services.execution_tree.project_validate"],
        "before_rename": "construction.services.execution_tree.project_before_rename",
        "on_trash": "construction.services.execution_tree.project_on_trash",
    },
    "DocShare": {"validate": "construction.services.execution_tree_access.reject_protected_share"},
}
has_permission["Execution Breakdown Node"] = "construction.services.execution_tree_access.has_protected_permission"
has_permission["Execution Code Counter"] = "construction.services.execution_tree_access.has_protected_permission"
permission_query_conditions["Execution Breakdown Node"] = "construction.services.execution_tree_access.protected_query_conditions"
permission_query_conditions["Execution Code Counter"] = "construction.services.execution_tree_access.protected_query_conditions"
"""


def test_hook_projection_accepts_the_reviewed_shape():
    projection = rules.extract_hook_projection(HOOK_TEMPLATE)
    rules.validate_hook_projection("construction", projection)
    wildcard = projection["permission_query_conditions"]["*"]
    assert wildcard == "construction.overrides.scope_query.add_scope_conditions" or wildcard == [
        "construction.overrides.scope_query.add_scope_conditions"
    ]


def test_hook_projection_denies_added_project_or_wildcard_permission_hooks():
    for source in (
        HOOK_TEMPLATE.replace("has_permission = {}", 'has_permission = {"Project": "x"}'),
        HOOK_TEMPLATE.replace("has_permission = {}", 'has_permission = {"*": "x"}'),
        HOOK_TEMPLATE.replace(
            'permission_query_conditions = {"*": "construction.overrides.scope_query.add_scope_conditions"}',
            'permission_query_conditions = {"Project": "x"}',
        ),
    ):
        projection = rules.extract_hook_projection(source)
        with pytest.raises(rules.UnsupportedProfile):
            rules.validate_hook_projection("construction", projection)


def test_hook_projection_denies_reordered_duplicate_or_missing_wildcard_handler():
    for source in (
        HOOK_TEMPLATE.replace(
            '{"*": "construction.overrides.scope_query.add_scope_conditions"}',
            '{"*": ["other.handler", "construction.overrides.scope_query.add_scope_conditions"]}',
        ),
        HOOK_TEMPLATE.replace(
            '{"*": "construction.overrides.scope_query.add_scope_conditions"}',
            '{"*": ["construction.overrides.scope_query.add_scope_conditions", "construction.overrides.scope_query.add_scope_conditions"]}',
        ),
        HOOK_TEMPLATE.replace('{"*": "construction.overrides.scope_query.add_scope_conditions"}', "{}"),
    ):
        projection = rules.extract_hook_projection(source)
        with pytest.raises(rules.UnsupportedProfile):
            rules.validate_hook_projection("construction", projection)


def test_hook_projection_denies_dynamic_relevant_expressions():
    source = "has_permission = {}\nhas_permission.update(build_hooks())\n"
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_hook_projection(source)


def test_custom_field_allowlist_is_finite_and_typed():
    link = {
        "fieldname": "branch",
        "fieldtype": "Link",
        "options": "Branch",
        "ignore_user_permissions": 0,
        "permlevel": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
    }
    rules.validate_custom_field_definition(link, doctype="Project")
    for bad in (
        {**link, "options": "BOQ Header"},
        {**link, "fieldtype": "Dynamic Link"},
        {**link, "fieldtype": "Table", "options": "Project User"},
        {**link, "fieldtype": "Table MultiSelect", "options": "Project User"},
        {**link, "fieldtype": "Data", "options": "Company"},
        {**link, "fieldtype": "Link", "ignore_user_permissions": 2},
        {**link, "fieldtype": "Link", "permlevel": -1},
    ):
        with pytest.raises(rules.RuleViolation):
            rules.validate_custom_field_definition(bad, doctype="Project")


def test_cosmetic_property_setter_allowlist_rejects_semantic_and_doctype_setters():
    assert rules.cast_property_setter("label", "New label", "Data") == "New label"
    assert rules.cast_property_setter("in_list_view", "1", "Check") == 1
    assert rules.cast_property_setter("columns", "2", "Int") == 2
    for prop, value, property_type in (
        ("options", "Company", "Data"),
        ("fieldtype", "Data", "Data"),
        ("permlevel", "0", "Int"),
        ("ignore_user_permissions", "1", "Check"),
        ("fieldname", "company", "Data"),
        ("hidden", "1", "Check"),
        ("in_list_view", "2", "Check"),
        ("label", 1, "Data"),
    ):
        with pytest.raises(rules.RuleViolation):
            rules.cast_property_setter(prop, value, property_type)


def test_parse_installed_app_registry_rejects_duplicates_and_order_changes():
    assert rules.parse_installed_apps('["frappe", "erpnext", "construction"]') == (
        "frappe",
        "erpnext",
        "construction",
    )
    for payload in (
        ["frappe", "construction", "erpnext"],
        ["frappe", "erpnext", "construction", "construction"],
        ["frappe", "erpnext"],
        ["frappe", "erpnext", "other"],
        "not json",
    ):
        with pytest.raises(rules.RuleViolation):
            rules.parse_installed_apps(payload)


def test_vendor_projection_tolerates_unrelated_dynamic_doc_events():
    source = """
has_permission = {}
permission_query_conditions = {"Event": "frappe.event.query"}
extend_doctype_class = {"Address": "erpnext.address"}
doc_events = {tuple(period_closing_doctypes): {"validate": "erpnext.period.validate"}}
"""
    projection = rules.extract_hook_projection(source, mode="vendor")
    rules.validate_hook_projection("erpnext", projection)


def test_vendor_project_or_wildcard_registrations_are_denied():
    for source in (
        'has_permission = {"Project": "x"}',
        'has_permission = {"*": "x"}',
        'permission_query_conditions = {"Project": "x"}',
        'permission_query_conditions = {"*": "x"}',
        'override_doctype_class = {"Project": "x"}',
        'extend_doctype_class = {"Project User": "x"}',
        'get_child_provider = {"Project": "x"}',
    ):
        projection = rules.extract_hook_projection(source, mode="vendor")
        with pytest.raises(rules.UnsupportedProfile):
            rules.validate_hook_projection("erpnext", projection)


def test_stock_field_projection_is_complete_and_exact():
    fields = [
        dict(zip(rules.STOCK_FIELD_PROJECTION_ATTRIBUTES, row, strict=True))
        for row in rules.PINNED_STOCK_PROJECT_FIELDS
    ]
    assert rules.validate_stock_field_projection("Project", fields) is True
    extra = {
        "fieldname": "wbs_note",
        "fieldtype": "Data",
        "options": None,
        "permlevel": 0,
        "ignore_user_permissions": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
        "is_virtual": 0,
    }
    with pytest.raises(rules.UnsupportedProfile):
        rules.validate_stock_field_projection("Project", [*fields, extra])
    with pytest.raises(rules.UnsupportedProfile):
        rules.validate_stock_field_projection("Project", fields[:-1])
    altered = [dict(field) for field in fields]
    altered[3]["options"] = "Something Else"
    with pytest.raises(rules.UnsupportedProfile):
        rules.validate_stock_field_projection("Project", altered)
    child = [
        dict(zip(rules.STOCK_FIELD_PROJECTION_ATTRIBUTES, row, strict=True))
        for row in rules.PINNED_STOCK_PROJECT_USER_FIELDS
    ]
    assert rules.validate_stock_field_projection("Project User", child) is True
    with pytest.raises(rules.UnsupportedProfile):
        rules.validate_stock_field_projection("Project User", [*child, extra])


def test_required_binary_settings_never_default_permissively():
    assert rules.parse_required_binary_setting("1", field="apply_strict_user_permissions") is True
    assert rules.parse_required_binary_setting("0", field="apply_strict_user_permissions") is False
    assert rules.parse_required_binary_setting(True, field="x") is True
    for raw in (None, "", "  ", "2", "yes", -1):
        with pytest.raises(rules.RuleViolation):
            rules.parse_required_binary_setting(raw, field="apply_strict_user_permissions")


EVENTS_SOURCE = """
period_closing = ["Sales Invoice", "Purchase Invoice"]
doc_events = {
    "*": {"validate": ["vendor.one", "vendor.two"]},
    tuple(period_closing): {"validate": "vendor.period"},
    "Project": {"before_rename": "vendor.rename"},
    "Unrelated": {"validate": "vendor.unrelated"},
}
"""


def test_relevant_doc_events_projection_expands_literal_tuple_keys():
    events = rules.extract_relevant_doc_events(EVENTS_SOURCE)
    assert events["*"]["validate"] == ["vendor.one", "vendor.two"]
    assert events["Project"]["before_rename"] == ["vendor.rename"]
    assert "Sales Invoice" not in events
    assert "Unrelated" not in events


def test_relevant_doc_events_denies_unresolved_or_dynamic_keys():
    unresolved = EVENTS_SOURCE.replace('period_closing = ["Sales Invoice", "Purchase Invoice"]\n', "")
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_relevant_doc_events(unresolved)
    dynamic = EVENTS_SOURCE.replace(
        '"Project": {"before_rename": "vendor.rename"},', '"Project": {"before_rename": build_handler()},'
    )
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_relevant_doc_events(dynamic)
    mutated = EVENTS_SOURCE + '\nperiod_closing.append("Project")\n'
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_relevant_doc_events(mutated)
    conditional = EVENTS_SOURCE + '\nif flag:\n    doc_events["Project"] = {"validate": "x"}\n'
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_relevant_doc_events(conditional)


def test_merge_doc_events_preserves_installed_handler_order():
    first = {"*": {"validate": ["a"]}, "Project": {"validate": ["p1"]}}
    second = {"*": {"validate": ["b", "c"]}, "Project": {"validate": "p2"}}
    merged = rules.merge_doc_events([first, second])
    assert merged["*"]["validate"] == ["a", "b", "c"]
    assert merged["Project"]["validate"] == ["p1", "p2"]


def test_protected_definition_comparison_refuses_incompatible_metadata():
    candidate = {
        "module": "construction",
        "field_order": ["project", "last_issued"],
        "fields": [
            {"fieldname": "project", "fieldtype": "Link", "options": "Project", "reqd": 1},
            {"fieldname": "last_issued", "fieldtype": "Long Int", "reqd": 1},
        ],
    }
    meta = {"module": "construction", "custom": 0, "istable": 0, "issingle": 0, "is_tree": 0, "is_virtual": 0}
    rows = [
        {"fieldname": "project", "fieldtype": "Link", "options": "Project", "reqd": 1},
        {"fieldname": "last_issued", "fieldtype": "Long Int", "reqd": 1},
    ]
    assert rules.validate_protected_definition("Execution Code Counter", meta, rows, candidate) is True
    bad_rows = [dict(row) for row in rows]
    bad_rows[1]["fieldtype"] = "Int"
    with pytest.raises(rules.RuleViolation):
        rules.validate_protected_definition("Execution Code Counter", meta, bad_rows, candidate)
    with pytest.raises(rules.RuleViolation):
        rules.validate_protected_definition("Execution Code Counter", dict(meta, istable=1), rows, candidate)
    with pytest.raises(rules.RuleViolation):
        rules.validate_protected_definition("Execution Code Counter", meta, rows[:1], candidate)
    with pytest.raises(rules.RuleViolation):
        rules.validate_protected_definition(
            "Execution Code Counter", dict(meta, module="other"), rows, candidate
        )


def test_container_call_grammar_is_finite():
    source = 'names = ["A", "B"]\nhas_permission = {tuple(names): "h"}\n'
    projection = rules.extract_hook_projection(source, mode="vendor")
    assert projection["has_permission"] == {("A", "B"): "h"}
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_hook_projection('has_permission = {tuple(build()): "h"}\n', mode="vendor")
    with pytest.raises(rules.UnsupportedProfile):
        rules.extract_hook_projection("has_permission = dict(a=1)\n", mode="vendor")
