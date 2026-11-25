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
    header_src = (ROOT / "construction/construction/doctype/boq_header/boq_header.py").read_text(
        encoding="utf-8"
    )

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


def test_option3_least_privilege_display_context_hides_stage_info_from_non_planners():
    stage_queries = []

    def _sql(query, params=(), as_dict=False):
        if "`tabBOQ Item Stage`" in query:
            stage_queries.append((query, params))
            return [(1,)]
        if "`tabExecution Breakdown Node`" in query:
            return []
        if "`tabExecution Mapping Audit`" in query:
            return []
        return []

    class _Row(dict):
        def __getattr__(self, key):
            return self.get(key)

    def _get_value(dt, name, field, as_dict=False):
        if dt == "BOQ Item":
            return _Row(name=name, boq_header="BOQ-H-1", planned_execution_node=None)
        if dt == "BOQ Header":
            return "PROJ-1"
        return None

    db_stub = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: True,
        exists=lambda dt, name: True,
        get_value=_get_value,
        sql=_sql,
    )

    with _load_execution_mapping_with_stubs(db_stub, _sql) as (mod, frappe_stub, _all_dts):
        # 1. Accountant (non-planner): must NEVER query tabBOQ Item Stage and never expose stage_count
        frappe_stub.session = types.SimpleNamespace(user="acct@example.com")
        frappe_stub.get_roles = lambda user: ["Accountant"]
        frappe_stub.has_permission = lambda dt, ptype="read", doc=None: dt == "BOQ Item"

        ctx_acct = mod.get_mapping_display_context("BOQ Item", "BOQ-ITEM-1")
        assert stage_queries == [], "Non-planner must not trigger Stage existence query"
        assert "stage_count" not in ctx_acct
        assert ctx_acct["can_assign_location"] is False
        assert ctx_acct["stage_managed"] is False

        # 2. Planner without BOQ Item Stage read permission: must NOT query tabBOQ Item Stage
        frappe_stub.session = types.SimpleNamespace(user="pm_nostage@example.com")
        frappe_stub.get_roles = lambda user: ["Project Manager"]
        frappe_stub.has_permission = lambda dt, ptype="read", doc=None: dt == "BOQ Item"

        ctx_pm_no_read = mod.get_mapping_display_context("BOQ Item", "BOQ-ITEM-1")
        assert stage_queries == [], "Planner without Stage read perm must not query Stage table"
        assert ctx_pm_no_read["can_assign_location"] is False
        assert ctx_pm_no_read["stage_managed"] is False

        # 3. Authorized planner WITH BOQ Item Stage read permission: receives minimal booleans only
        frappe_stub.has_permission = lambda dt, ptype="read", doc=None: dt in ("BOQ Item", "BOQ Item Stage")
        ctx_pm = mod.get_mapping_display_context("BOQ Item", "BOQ-ITEM-1")
        assert len(stage_queries) == 1
        assert "stage_count" not in ctx_pm
        assert ctx_pm["stage_managed"] is True
        assert ctx_pm["can_assign_location"] is False


def test_option3_set_item_rejects_set_and_change_when_stages_exist_but_allows_clear():
    state = {"planned_execution_node": "EBN-0001", "has_stages": True, "updates": [], "audits": []}

    def _sql(query, params=(), as_dict=False):
        if "FROM `tabProject`" in query:
            return [{"name": "PROJ-1", "company": "Co", "cost_center": None}]
        if "FROM `tabExecution Breakdown Node`" in query:
            return [make_node("EBN-0001", title="Floor 1"), make_node("EBN-0002", title="Floor 2")]
        if "FROM `tabBOQ Item` WHERE name=%s" in query:
            return [
                {
                    "name": "BOQ-ITEM-1",
                    "boq_header": "BOQ-H-1",
                    "quantity": 100.0,
                    "planned_execution_node": state["planned_execution_node"],
                    "modified": "2026-11-25 10:00:00",
                    "modified_by": "Administrator",
                }
            ]
        if "FROM `tabBOQ Header`" in query:
            return [{"name": "BOQ-H-1", "project": "PROJ-1"}]
        if "FROM `tabBOQ Item Stage`" in query:
            return [(1,)] if state["has_stages"] else []
        if query.startswith("UPDATE `tabBOQ Item`"):
            state["planned_execution_node"] = params[0]
            state["updates"].append(params)
            return []
        return []

    class _Row(dict):
        def __getattr__(self, key):
            return self.get(key)

    db_stub = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: True,
        get_value=lambda dt, name, field, as_dict=False: (
            _Row(name="BOQ-ITEM-1", boq_header="BOQ-H-1") if dt == "BOQ Item" else "PROJ-1"
        ),
        sql=_sql,
    )

    with _load_execution_mapping_with_stubs(db_stub, _sql) as (mod, frappe_stub, _all_dts):
        frappe_stub.session = types.SimpleNamespace(user="Administrator")
        frappe_stub.has_permission = lambda dt, ptype="read", doc=None: True
        mod.access.authorize = lambda project, op: ({"project": project}, None)
        mod._insert_audit_row = lambda **kw: (state["audits"].append(kw), "EMA-0000001")[1]

        # Change rejected while Stages exist
        with pytest.raises(frappe_stub.ValidationError, match="while Stages exist"):
            mod.set_item_planned_execution_node(
                boq_item="BOQ-ITEM-1",
                execution_node="EBN-0002",
                reason="Trying to change",
                expected_modified="2026-11-25 10:00:00",
            )
        assert state["updates"] == []

        # Clear allowed while Stages exist (with mandatory reason)
        res = mod.set_item_planned_execution_node(
            boq_item="BOQ-ITEM-1",
            execution_node=None,
            reason="Clear legacy parent default",
            expected_modified="2026-11-25 10:00:00",
        )
        assert res["changed"] is True
        assert res["action"] == "clear"
        assert state["planned_execution_node"] is None

        # Set rejected while Stages exist
        with pytest.raises(frappe_stub.ValidationError, match="while Stages exist"):
            mod.set_item_planned_execution_node(
                boq_item="BOQ-ITEM-1",
                execution_node="EBN-0001",
                expected_modified="2026-11-25 10:00:00",
            )


def test_option3_stage_creation_inherits_and_atomically_clears_parent_item_default():
    state = {"planned_execution_node": "EBN-0001", "audits": []}

    def _sql(query, params=(), as_dict=False):
        if "FROM `tabProject`" in query:
            return [{"name": "PROJ-1", "company": "Co", "cost_center": None}]
        if "FROM `tabExecution Breakdown Node`" in query:
            return [make_node("EBN-0001", title="Floor 1")]
        if "FROM `tabBOQ Item` WHERE name=%s" in query:
            return [
                {
                    "name": "BOQ-ITEM-1",
                    "boq_header": "BOQ-H-1",
                    "structure": "STR-1",
                    "quantity": 100.0,
                    "planned_execution_node": state["planned_execution_node"],
                    "modified": "2026-11-25 10:00:00",
                    "modified_by": "Administrator",
                }
            ]
        if "FROM `tabBOQ Header`" in query:
            return [{"name": "BOQ-H-1", "project": "PROJ-1"}]
        if query.startswith("UPDATE `tabBOQ Item` SET planned_execution_node=NULL"):
            state["planned_execution_node"] = None
            return []
        return []

    db_stub = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: True,
        sql=_sql,
    )

    class _StageDoc:
        def __init__(self):
            self.name = "BOQ-STG-00001"
            self.boq_item = "BOQ-ITEM-1"
            self.boq_header = "BOQ-H-1"
            self.boq_structure = "STR-1"
            self.project = "PROJ-1"
            self.execution_node = None
            self.stage_status = "Not Started"
            self.measured_executed_qty = 0
            self.certified_qty = 0
            self.flags = types.SimpleNamespace()

        def is_new(self):
            return True

        def get(self, key):
            return getattr(self, key, None)

    with _load_execution_mapping_with_stubs(db_stub, _sql) as (mod, frappe_stub, _all_dts):
        frappe_stub.session = types.SimpleNamespace(user="site_eng@example.com")
        mod._insert_audit_row = lambda **kw: (state["audits"].append(kw), f"EMA-{len(state['audits']):07d}")[
            1
        ]

        doc = _StageDoc()
        mod.enforce_boq_stage_mapping_guard(doc)
        assert doc.execution_node == "EBN-0001", "First Stage should inherit eligible Item default"
        assert getattr(doc.flags, "_pending_parent_item_clear", None) is not None

        mod.record_pending_mapping_audit(doc)
        assert state["planned_execution_node"] is None, "Parent BOQ Item default must be cleared atomically"
        assert len(state["audits"]) == 2
        assert state["audits"][0]["target_doctype"] == "BOQ Item Stage"
        assert state["audits"][0]["action"] == "inherit_on_create"
        assert state["audits"][1]["target_doctype"] == "BOQ Item"
        assert state["audits"][1]["action"] == "clear"
        assert "BOQ-STG-00001" in state["audits"][1]["reason"]


def test_option3_migration_cleanup_is_idempotent():
    state = {
        "items": [
            {
                "name": "BOQ-ITEM-DUAL",
                "boq_header": "BOQ-H-1",
                "project": "PROJ-1",
                "planned_execution_node": "EBN-0001",
            }
        ],
        "audits": [],
    }

    def _sql(query, params=(), as_dict=False):
        if "EXISTS (" in query and "`tabBOQ Item Stage`" in query:
            return [r for r in state["items"] if r["planned_execution_node"]]
        if "FROM `tabExecution Breakdown Node`" in query:
            return [make_node("EBN-0001", title="Floor 1")]
        if query.startswith("UPDATE `tabBOQ Item` SET planned_execution_node=NULL"):
            target = params[2]
            for r in state["items"]:
                if r["name"] == target:
                    r["planned_execution_node"] = None
            return []
        return []

    db_stub = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: True,
        sql=_sql,
    )

    with _load_execution_mapping_with_stubs(db_stub, _sql) as (mod, frappe_stub, _all_dts):
        frappe_stub.session = types.SimpleNamespace(user="Administrator")
        mod._insert_audit_row = lambda **kw: (state["audits"].append(kw), "EMA-0000099")[1]

        r1 = mod.clear_dual_mapped_boq_item_locations()
        assert r1 == {"cleared": 1}
        assert state["items"][0]["planned_execution_node"] is None
        assert len(state["audits"]) == 1
        assert state["audits"][0]["action"] == "clear"

        # Second run must be a 0-row no-op
        r2 = mod.clear_dual_mapped_boq_item_locations()
        assert r2 == {"cleared": 0}
        assert len(state["audits"]) == 1


def test_option3_draft_stage_reparent_atomically_clears_destination_item_default():
    state = {"dest_default": "EBN-0002", "audits": []}

    def _sql(query, params=(), as_dict=False):
        if "FROM `tabProject`" in query:
            return [{"name": "PROJ-1", "company": "Co", "cost_center": None}]
        if "FROM `tabExecution Breakdown Node`" in query:
            return [make_node("EBN-0001", title="Floor 1"), make_node("EBN-0002", title="Floor 2")]
        if "FROM `tabBOQ Item` WHERE name=%s" in query:
            return [
                {
                    "name": "BOQ-ITEM-DEST",
                    "boq_header": "BOQ-H-1",
                    "structure": "STR-2",
                    "quantity": 50.0,
                    "planned_execution_node": state["dest_default"],
                    "modified": "2026-11-25 10:00:00",
                    "modified_by": "Administrator",
                }
            ]
        if "FROM `tabBOQ Header`" in query:
            return [{"name": "BOQ-H-1", "project": "PROJ-1"}]
        if query.startswith("UPDATE `tabBOQ Item` SET planned_execution_node=NULL"):
            state["dest_default"] = None
            return []
        return []

    db_stub = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: True,
        get_value=lambda dt, name, field, as_dict=False: "PROJ-1",
        sql=_sql,
    )

    class _MovedStageDoc:
        def __init__(self):
            self.name = "BOQ-STG-00010"
            self.boq_item = "BOQ-ITEM-DEST"
            self.boq_header = "BOQ-H-1"
            self.boq_structure = "STR-2"
            self.project = "PROJ-1"
            self.execution_node = "EBN-0001"
            self.flags = types.SimpleNamespace()

        def is_new(self):
            return False

        def get(self, key):
            return getattr(self, key, None)

        def get_doc_before_save(self):
            return {"boq_item": "BOQ-ITEM-OLD", "execution_node": "EBN-0001"}

    with _load_execution_mapping_with_stubs(db_stub, _sql) as (mod, frappe_stub, _all_dts):
        frappe_stub.session = types.SimpleNamespace(user="Administrator")
        mod._insert_audit_row = lambda **kw: (state["audits"].append(kw), "EMA-0000101")[1]

        doc = _MovedStageDoc()
        mod.enforce_boq_stage_mapping_guard(doc)
        assert doc.execution_node == "EBN-0001", "Existing Stage's own location must stay unchanged"
        assert getattr(doc.flags, "_pending_parent_item_clear", None) is not None

        mod.record_pending_mapping_audit(doc)
        assert state["dest_default"] is None, "Destination BOQ Item default must be cleared on reparent"
        assert len(state["audits"]) == 1
        assert state["audits"][0]["target_doctype"] == "BOQ Item"
        assert state["audits"][0]["target_name"] == "BOQ-ITEM-DEST"
        assert state["audits"][0]["action"] == "clear"
        assert "moved to this BOQ Item" in state["audits"][0]["reason"]


def test_option3_migration_cleanup_fails_closed_before_updating_without_audit_or_context():
    updates = []

    def _make_sql(rows):
        def _sql(query, params=(), as_dict=False):
            if "EXISTS (" in query and "`tabBOQ Item Stage`" in query:
                return rows
            if query.startswith("UPDATE `tabBOQ Item`"):
                updates.append(params)
                return []
            return []

        return _sql

    # 1. Missing Execution Mapping Audit table -> fails BEFORE any UPDATE
    rows_valid = [
        {
            "name": "BOQ-ITEM-DUAL",
            "boq_header": "BOQ-H-1",
            "project": "PROJ-1",
            "planned_execution_node": "EBN-0001",
        }
    ]
    db_no_audit = types.SimpleNamespace(
        table_exists=lambda dt: dt != "Execution Mapping Audit",
        has_column=lambda dt, col: True,
        sql=_make_sql(rows_valid),
    )
    with _load_execution_mapping_with_stubs(db_no_audit, _make_sql(rows_valid)) as (
        mod,
        frappe_stub,
        _all_dts,
    ):
        with pytest.raises(frappe_stub.ValidationError, match="Execution Mapping Audit"):
            mod.clear_dual_mapped_boq_item_locations()
        assert updates == [], "Must not update any BOQ Item if audit table is missing"

    # 2. Missing BOQ Header / Project on ANY dual-mapped row -> fails BEFORE any UPDATE
    rows_missing_ctx = [
        {
            "name": "BOQ-ITEM-OK",
            "boq_header": "BOQ-H-1",
            "project": "PROJ-1",
            "planned_execution_node": "EBN-0001",
        },
        {
            "name": "BOQ-ITEM-ORPHAN",
            "boq_header": "BOQ-H-MISSING",
            "project": None,
            "planned_execution_node": "EBN-0001",
        },
    ]
    db_ok = types.SimpleNamespace(
        table_exists=lambda dt: True,
        has_column=lambda dt, col: True,
        sql=_make_sql(rows_missing_ctx),
    )
    with _load_execution_mapping_with_stubs(db_ok, _make_sql(rows_missing_ctx)) as (
        mod,
        frappe_stub,
        _all_dts,
    ):
        with pytest.raises(frappe_stub.ValidationError, match="BOQ Header and Project"):
            mod.clear_dual_mapped_boq_item_locations()
        assert updates == [], "Must not partially update BOQ-ITEM-OK when BOQ-ITEM-ORPHAN lacks context"
