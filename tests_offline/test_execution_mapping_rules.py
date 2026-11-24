"""Offline vectors for WBS P2 execution-location mapping rules and schema invariants (Slice 1)."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sys
import types
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
    assert "def set_stage_execution_node" in api_text


def test_stage_execution_lock_conditions_and_transitions_a1():
    # Unlocked states (A1 current persisted values)
    assert (
        rules.evaluate_stage_lock_conditions(
            {"stage_status": "Not Started", "measured_executed_qty": 0, "certified_qty": 0}
        )
        == ()
    )
    assert (
        rules.evaluate_stage_lock_conditions(
            {"stage_status": "In Progress", "measured_executed_qty": 0, "certified_qty": 0}
        )
        == ()
    )
    # Positive measurement locks; correcting back to zero unlocks (A1).
    assert rules.evaluate_stage_lock_conditions(
        {"stage_status": "In Progress", "measured_executed_qty": 10.0, "certified_qty": 0}
    ) == ("measured_qty",)
    assert (
        rules.evaluate_stage_lock_conditions(
            {"stage_status": "In Progress", "measured_executed_qty": 0.0, "certified_qty": 0}
        )
        == ()
    )
    # Partial certification (certified_qty > 0 while status In Progress).
    assert rules.evaluate_stage_lock_conditions(
        {"stage_status": "In Progress", "measured_executed_qty": 50.0, "certified_qty": 20.0}
    ) == ("measured_qty", "certified_qty")
    # Completed & Certified statuses.
    assert rules.evaluate_stage_lock_conditions(
        {"stage_status": "Completed", "measured_executed_qty": 0, "certified_qty": 0}
    ) == ("status_completed",)
    assert rules.evaluate_stage_lock_conditions(
        {"stage_status": "Certified", "measured_executed_qty": 0, "certified_qty": 0}
    ) == ("status_certified",)
    # Zero-qty In Progress Stage linked to a Purchase Order Item (Draft or Cancelled counts).
    assert rules.evaluate_stage_lock_conditions(
        {"stage_status": "In Progress", "measured_executed_qty": 0, "certified_qty": 0},
        transaction_ref_doctypes=("Purchase Order Item",),
    ) == ("transaction_ref:Purchase Order Item",)

    # Unlocked transitions
    assert rules.classify_stage_mapping_transition(None, "EBN-0001", ()) == ("set", False)
    assert rules.classify_stage_mapping_transition("EBN-0001", "EBN-0002", ()) == ("change", False)
    assert rules.classify_stage_mapping_transition("EBN-0001", None, ()) == ("clear", False)
    assert rules.classify_stage_mapping_transition("EBN-0001", "EBN-0001", ()) == (None, False)

    # Execution-locked transitions (Alternative B + A1)
    lock = ("transaction_ref:Purchase Order Item",)
    assert rules.classify_stage_mapping_transition(None, "EBN-0001", lock) == ("initial_historical_map", True)
    assert rules.classify_stage_mapping_transition("EBN-0001", "EBN-0001", lock) == (None, False)
    for target in ("EBN-0002", None):
        with pytest.raises(rules.RuleViolation) as exc_info:
            rules.classify_stage_mapping_transition("EBN-0001", target, lock)
        assert exc_info.value.code == "execution_locked"


def test_slice2_transaction_lock_source_invariants():
    acct_src = (ROOT / "construction/services/boq_accounting.py").read_text(encoding="utf-8")
    assert "FROM `tabBOQ Item Stage` WHERE name = %s FOR UPDATE" in acct_src
    mapping_src = (ROOT / "construction/services/execution_mapping.py").read_text(encoding="utf-8")
    assert "TRANSACTION_CHILD_DOCTYPES" in mapping_src
    assert "def set_stage_execution_node(" in mapping_src
    # _find_stage_transaction_refs must fail closed on missing table/column (never continue).
    fn_start = mapping_src.index("def _find_stage_transaction_refs(")
    fn_end = mapping_src.index("def evaluate_stage_execution_lock(")
    fn_block = mapping_src[fn_start:fn_end]
    assert "continue" not in fn_block
    assert "required transaction table {0} is missing." in fn_block
    assert "{0}.{1} is missing. Run bench migrate." in fn_block


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


@contextlib.contextmanager
def _load_execution_mapping_with_stubs(db_stub, sql_fn):
    """Load execution_mapping.py in isolation without importing real Frappe."""
    frappe_stub = types.ModuleType("frappe")
    frappe_stub.ValidationError = type("ValidationError", (Exception,), {})
    frappe_stub.PermissionError = type("PermissionError", (Exception,), {})
    frappe_stub.DoesNotExistError = type("DoesNotExistError", (Exception,), {})
    frappe_stub._ = lambda message: message
    frappe_stub.db = db_stub

    def _throw(message, exc=None):
        raise (exc or frappe_stub.ValidationError)(message)

    frappe_stub.throw = _throw

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.flt = lambda v: float(v or 0)
    frappe_utils.now_datetime = lambda: "2026-11-24 00:00:00"

    construction = types.ModuleType("construction")
    construction.__path__ = []
    services = types.ModuleType("construction.services")
    services.__path__ = []
    services.execution_tree_rules = rules
    services.execution_tree_access = types.ModuleType("construction.services.execution_tree_access")

    boq_transactions = types.ModuleType("construction.services.boq_transactions")
    boq_transactions.current_boq_sql = sql_fn

    boq_lifecycle = types.ModuleType("construction.services.boq_lifecycle")
    boq_lifecycle.TRANSACTION_CHILD_DOCTYPES = (
        "Purchase Order Item",
        "Purchase Receipt Item",
        "Purchase Invoice Item",
        "Stock Entry Detail",
        "Timesheet Detail",
        "Journal Entry Account",
        "Sales Invoice Item",
        "Material Request Item",
    )

    stubs = {
        "frappe": frappe_stub,
        "frappe.utils": frappe_utils,
        "construction": construction,
        "construction.services": services,
        "construction.services.execution_tree_rules": rules,
        "construction.services.execution_tree_access": services.execution_tree_access,
        "construction.services.boq_transactions": boq_transactions,
        "construction.services.boq_lifecycle": boq_lifecycle,
    }
    previous = {k: sys.modules.get(k) for k in stubs}
    try:
        sys.modules.update(stubs)
        spec = importlib.util.spec_from_file_location(
            "execution_mapping_under_test", ROOT / "construction/services/execution_mapping.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        yield mod, frappe_stub, boq_lifecycle.TRANSACTION_CHILD_DOCTYPES
    finally:
        for k, old in previous.items():
            if old is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = old


def test_find_stage_transaction_refs_fails_closed_on_missing_schema():
    queries = []

    def _sql(query, params=()):
        queries.append((query, params))
        if "`tabPurchase Order Item`" in query:
            return [(1,)]
        return []

    # 1. All 8 required tables & boq_item_stage columns present -> queries all 8 with LOCK IN SHARE MODE.
    db_ok = types.SimpleNamespace(table_exists=lambda dt: True, has_column=lambda dt, col: True)
    with _load_execution_mapping_with_stubs(db_ok, _sql) as (mod, _frappe, all_dts):
        assert mod._find_stage_transaction_refs("BOQ-STG-00001") == ("Purchase Order Item",)
        assert len(queries) == len(all_dts) == 8
        assert all("LOCK IN SHARE MODE" in q for q, _p in queries)

    # 2. Missing table among the 8 required child types -> fails closed with ValidationError.
    db_missing_table = types.SimpleNamespace(
        table_exists=lambda dt: dt != "Stock Entry Detail",
        has_column=lambda dt, col: True,
    )
    with _load_execution_mapping_with_stubs(db_missing_table, _sql) as (mod, frappe_stub, _all_dts):
        with pytest.raises(frappe_stub.ValidationError, match="Stock Entry Detail"):
            mod._find_stage_transaction_refs("BOQ-STG-00001")

    # 3. Missing boq_item_stage column on any of the 8 required child types -> fails closed with ValidationError.
    db_missing_col = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: not (dt == "Material Request Item" and col == "boq_item_stage"),
    )
    with _load_execution_mapping_with_stubs(db_missing_col, _sql) as (mod, frappe_stub, _all_dts):
        with pytest.raises(frappe_stub.ValidationError, match="Material Request Item.boq_item_stage"):
            mod._find_stage_transaction_refs("BOQ-STG-00001")

