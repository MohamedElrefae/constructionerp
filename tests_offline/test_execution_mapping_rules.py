"""Offline vectors for WBS P2 execution-location mapping rules and schema invariants (Slice 1)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "construction" / "services" / "execution_tree_rules.py"
SPEC = importlib.util.spec_from_file_location("execution_tree_rules_p2", MODULE_PATH)
rules = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rules)


def make_node(name, *, project="PROJ-1", parent=None, group=False, code=None, title=None, disabled=False):
    return {
        "name": name,
        "title": title or f"Title {name}",
        "project": project,
        "company": "Company A",
        "parent_node": parent,
        "is_group": 1 if group else 0,
        "disabled": 1 if disabled else 0,
        "ebs_code": code or f"EBS-{name.split('-')[-1].rjust(4, '0')}",
        "modified": "2026-11-24 00:00:00.000000",
    }


def test_role_boundaries_for_construction_owner_and_delete_roles():
    assert "Construction Owner" in rules.BROWSE_ROLES
    assert "Construction Owner" in rules.MAPPING_PLANNER_ROLES
    assert "Construction Owner" not in rules.WRITE_ROLES
    assert "Construction Owner" not in rules.DELETE_ROLES
    assert rules.WRITE_ROLES == frozenset({"Project Manager", "System Manager"})
    assert rules.DELETE_ROLES == frozenset({"System Manager"})
    assert "Site Engineer" in rules.BROWSE_ROLES
    assert "Site Engineer" not in rules.MAPPING_PLANNER_ROLES
    assert "Accountant" not in rules.BROWSE_ROLES
    assert "Accountant" not in rules.MAPPING_PLANNER_ROLES


def test_disabled_ancestor_makes_leaf_ineligible():
    nodes = [
        make_node("EBN-0001", group=True, title="Site", disabled=False),
        make_node("EBN-0002", parent="EBN-0001", group=True, title="Building A", disabled=True),
        make_node("EBN-0003", parent="EBN-0002", group=False, title="Floor 2", disabled=False),
        make_node("EBN-0004", parent="EBN-0001", group=False, title="Building B", disabled=False),
    ]
    by_name = rules.index_nodes_by_name(nodes)

    assert rules.disabled_state(by_name, "EBN-0004") == (False, None)
    assert rules.is_effectively_enabled(by_name, "EBN-0004") is True

    assert rules.disabled_state(by_name, "EBN-0002") == (True, "self")
    assert rules.disabled_state(by_name, "EBN-0003") == (True, "ancestor")
    assert rules.is_effectively_enabled(by_name, "EBN-0003") is False

    ok, code, _msg = rules.is_eligible_execution_leaf(by_name, "EBN-0003", project="PROJ-1")
    assert ok is False
    assert code == "disabled_ancestor"

    ok2, code2, _msg2 = rules.is_eligible_execution_leaf(by_name, "EBN-0004", project="PROJ-1")
    assert ok2 is True
    assert code2 is None


def test_eligible_leaf_rejects_group_foreign_project_self_disabled_and_missing():
    nodes = [
        make_node("EBN-0001", group=True, title="Building A"),
        make_node("EBN-0002", parent="EBN-0001", group=False, title="Floor 1", disabled=True),
        make_node("EBN-0003", project="PROJ-2", group=False, title="Other Project Leaf"),
    ]
    by_name = rules.index_nodes_by_name(nodes)

    assert rules.is_eligible_execution_leaf(by_name, "EBN-0001", project="PROJ-1")[:2] == (
        False,
        "group_not_eligible",
    )
    assert rules.is_eligible_execution_leaf(by_name, "EBN-0002", project="PROJ-1")[:2] == (
        False,
        "disabled_node",
    )
    assert rules.is_eligible_execution_leaf(by_name, "EBN-0003", project="PROJ-1")[:2] == (
        False,
        "project_mismatch",
    )
    assert rules.is_eligible_execution_leaf(by_name, "EBN-9999", project="PROJ-1")[:2] == (
        False,
        "invalid_node",
    )


def test_build_node_path_and_collect_subtree():
    nodes = [
        make_node("EBN-0001", group=True, title="Tower A"),
        make_node("EBN-0002", parent="EBN-0001", group=True, title="Podium"),
        make_node("EBN-0003", parent="EBN-0002", group=False, title="Level 1"),
        make_node("EBN-0004", parent="EBN-0002", group=False, title="Level 2"),
        make_node("EBN-0005", group=False, title="Gatehouse"),
    ]
    by_name = rules.index_nodes_by_name(nodes)

    assert rules.build_node_path(by_name, "EBN-0003") == "Tower A / Podium / Level 1"
    assert rules.collect_subtree(nodes, "EBN-0001") == frozenset(
        {"EBN-0001", "EBN-0002", "EBN-0003", "EBN-0004"}
    )
    assert rules.collect_subtree(nodes, "EBN-0002") == frozenset({"EBN-0002", "EBN-0003", "EBN-0004"})
    assert rules.collect_subtree(nodes, "EBN-0003") == frozenset({"EBN-0003"})


def test_mapping_reason_policy():
    assert rules.validate_mapping_reason("set", None) == ""
    assert rules.validate_mapping_reason("set", "  Initial assignment  ") == "Initial assignment"
    assert rules.validate_mapping_reason("inherit_on_create", "") == ""
    assert rules.validate_mapping_reason("set_on_create", None) == ""

    for action in ("change", "clear", "initial_historical_map"):
        with pytest.raises(rules.RuleViolation) as exc_info:
            rules.validate_mapping_reason(action, "   ")
        assert exc_info.value.code == "reason_required"
        assert rules.validate_mapping_reason(action, "Reassigned to Tower B") == "Reassigned to Tower B"


def test_schema_invariants_for_slice_1():
    item_json = json.loads(
        (ROOT / "construction/construction/doctype/boq_item/boq_item.json").read_text(encoding="utf-8")
    )
    stage_json = json.loads(
        (ROOT / "construction/construction/doctype/boq_item_stage/boq_item_stage.json").read_text(
            encoding="utf-8"
        )
    )
    audit_json = json.loads(
        (
            ROOT / "construction/construction/doctype/execution_mapping_audit/execution_mapping_audit.json"
        ).read_text(encoding="utf-8")
    )

    item_field = next(f for f in item_json["fields"] if f["fieldname"] == "planned_execution_node")
    assert item_field["fieldtype"] == "Link"
    assert item_field["options"] == "Execution Breakdown Node"
    assert item_field.get("read_only") == 1
    assert item_field.get("no_copy") == 1
    assert item_field.get("search_index") == 1
    assert not item_field.get("reqd")

    stage_field = next(f for f in stage_json["fields"] if f["fieldname"] == "execution_node")
    assert stage_field["fieldtype"] == "Link"
    assert stage_field["options"] == "Execution Breakdown Node"
    assert stage_field.get("read_only") == 1
    assert stage_field.get("no_copy") == 1
    assert stage_field.get("search_index") == 1
    assert not stage_field.get("reqd")

    assert audit_json["permissions"] == []
    assert audit_json["engine"] == "InnoDB"
    assert audit_json["autoname"] == "EMA-.#######"
    assert audit_json["allow_rename"] == 0
    assert audit_json["allow_import"] == 0
    for f in audit_json["fields"]:
        if f["fieldname"] in ("old_node", "new_node", "target_name", "boq_item", "boq_header"):
            assert f["fieldtype"] == "Data"

    api_text = (ROOT / "construction/api/execution_mapping_api.py").read_text(encoding="utf-8")
    assert "def set_stage_execution_node" not in api_text


def test_display_confidentiality_and_fail_closed_schema_source_invariants():
    mapping_src = (ROOT / "construction/services/execution_mapping.py").read_text(encoding="utf-8")
    tree_src = (ROOT / "construction/services/execution_tree.py").read_text(encoding="utf-8")
    header_src = (
        ROOT / "construction/construction/doctype/boq_header/boq_header.py"
    ).read_text(encoding="utf-8")

    # Display endpoint must never expose audit reason/trigger/name or latest_audit key.
    assert '"latest_audit"' not in mapping_src
    assert "def _display_attribution_summary" in mapping_src
    # Confirm _display_attribution_summary SQL selects only non-sensitive attribution columns.
    summary_start = mapping_src.index("def _display_attribution_summary")
    summary_end = mapping_src.index("def get_mapping_display_context")
    summary_block = mapping_src[summary_start:summary_end]
    assert "SELECT action, is_historical_assignment, changed_by, changed_on" in summary_block
    assert '"reason"' not in summary_block
    assert '"historical_trigger"' not in summary_block
    assert '"audit_name"' not in summary_block

    # Fail-closed schema helpers must not exist as exception-swallowing _has_column wrappers.
    assert "def _has_column(" not in mapping_src
    assert "def _has_column(" not in tree_src
    assert "require_mapping_column" in mapping_src
    assert "require_mapping_column" in tree_src

    # BOQ Header controller must guard project changes when child mappings exist.
    assert "enforce_boq_header_project_change_guard" in header_src

    # Audit series reconciliation must be wired into on_doctype_update.
    audit_ctrl = (
        ROOT / "construction/construction/doctype/execution_mapping_audit/execution_mapping_audit.py"
    ).read_text(encoding="utf-8")
    assert "def on_doctype_update()" in audit_ctrl
    assert "reconcile_audit_series_counter" in audit_ctrl
    assert "def reconcile_audit_series_counter()" in mapping_src
    # Item reparent guard must inspect mapped child Stages when boq_header changes.
    assert "FROM `tabBOQ Item Stage` s" in mapping_src

