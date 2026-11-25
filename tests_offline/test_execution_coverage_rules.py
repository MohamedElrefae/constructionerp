"""Offline test vectors for WBS P3 Execution Coverage rules & static invariants (Slice 1)."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "construction" / "services" / "execution_coverage_rules.py"
SERVICE_PATH = ROOT / "construction" / "services" / "execution_coverage.py"
API_PATH = ROOT / "construction" / "api" / "execution_coverage_api.py"

SPEC = importlib.util.spec_from_file_location("execution_coverage_rules_p3", RULES_PATH)
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
        "modified": "2026-11-25 00:00:00.000000",
    }


def make_item(
    name,
    *,
    header="BOQ-2026-0001",
    header_type="Contract",
    header_status="Locked",
    wbs_code="1.1",
    title=None,
    quantity=100.0,
    unit="m3",
    planned_execution_node=None,
):
    return {
        "name": name,
        "boq_header": header,
        "header_title": f"Header {header}",
        "header_type": header_type,
        "header_status": header_status,
        "structure": f"STR-{name}",
        "wbs_code": wbs_code,
        "item_title": title or f"Item {name}",
        "item_description": f"Description for {name}",
        "quantity": quantity,
        "unit": unit,
        "planned_execution_node": planned_execution_node,
    }


def make_stage(
    name,
    *,
    boq_item,
    header="BOQ-2026-0001",
    stage_code="STG-1",
    stage_name=None,
    stage_status="Not Started",
    execution_node=None,
    planned_qty=25.0,
):
    return {
        "name": name,
        "project": "PROJ-1",
        "boq_header": header,
        "boq_structure": f"STR-{boq_item}",
        "boq_item": boq_item,
        "stage_code": stage_code,
        "stage_name": stage_name or f"Stage {name}",
        "stage_status": stage_status,
        "execution_node": execution_node,
        "planned_qty": planned_qty,
    }


def test_rules_module_has_zero_framework_imports():
    tree = ast.parse(RULES_PATH.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"frappe", "erpnext", "construction"})


def test_classify_stage_link_all_states_and_zero_fallback():
    nodes = [
        make_node("EBN-ROOT", group=True, code="EBS-0001", title="Tower A"),
        make_node("EBN-LEAF", parent="EBN-ROOT", code="EBS-0002", title="Floor 1"),
        make_node("EBN-DIS-SELF", parent="EBN-ROOT", disabled=True, code="EBS-0003", title="Retired Slab"),
        make_node("EBN-DIS-GRP", parent="EBN-ROOT", group=True, disabled=True, code="EBS-0004", title="Retired Wing"),
        make_node("EBN-DIS-CHILD", parent="EBN-DIS-GRP", disabled=False, code="EBS-0005", title="Zone B"),
        make_node("EBN-FOREIGN", project="PROJ-2", code="EBS-0001", title="Other Project"),
        make_node("EBN-BROKEN", parent="EBN-GHOST", code="EBS-0006", title="Broken"),
        make_node("EBN-CYC-1", parent="EBN-CYC-2", code="EBS-0007", title="Cyc1"),
        make_node("EBN-CYC-2", parent="EBN-CYC-1", code="EBS-0008", title="Cyc2"),
    ]
    index = rules.index_nodes_by_name(nodes)

    assert rules.classify_stage_link(None, index, "PROJ-1") == ("unlinked", None, None)
    assert rules.classify_stage_link("   ", index, "PROJ-1") == ("unlinked", None, None)
    assert rules.classify_stage_link("EBN-LEAF", index, "PROJ-1") == ("healthy_linked", None, None)
    assert rules.classify_stage_link("EBN-DIS-SELF", index, "PROJ-1") == (
        "link_issues",
        "disabled_node",
        "disabled_links",
    )
    assert rules.classify_stage_link("EBN-DIS-CHILD", index, "PROJ-1") == (
        "link_issues",
        "disabled_ancestor",
        "disabled_links",
    )
    assert rules.classify_stage_link("EBN-MISSING", index, "PROJ-1") == (
        "link_issues",
        "missing_node",
        "integrity_issues",
    )
    assert rules.classify_stage_link("EBN-FOREIGN", index, "PROJ-1") == (
        "link_issues",
        "project_mismatch",
        "integrity_issues",
    )
    assert rules.classify_stage_link("EBN-ROOT", index, "PROJ-1") == (
        "link_issues",
        "group_node",
        "integrity_issues",
    )
    assert rules.classify_stage_link("EBN-BROKEN", index, "PROJ-1") == (
        "link_issues",
        "broken_parent",
        "integrity_issues",
    )
    assert rules.classify_stage_link("EBN-CYC-1", index, "PROJ-1") == (
        "link_issues",
        "cycle",
        "integrity_issues",
    )


def test_unmapped_stage_never_falls_back_to_item_planned_node_and_uses_unmapped_label():
    nodes = [
        make_node("EBN-ROOT", group=True, code="EBS-0001", title="Tower A"),
        make_node("EBN-L1", parent="EBN-ROOT", code="EBS-0002", title="Floor 1"),
    ]
    items = [make_item("BOQI-1", planned_execution_node="EBN-L1")]
    stages = [make_stage("STG-1", boq_item="BOQI-1", execution_node=None)]

    res = rules.evaluate_coverage(project="PROJ-1", items=items, stages=stages, project_nodes=nodes)
    assert res["summary"]["total_stages"] == 1
    assert res["summary"]["healthy_linked"] == 0
    assert res["summary"]["unlinked"] == 1
    assert res["summary"]["coverage_pct"] == 0.0
    assert res["summary"]["coverage_pct_display"] == "0.0%"

    stage_row = res["rows"][0]
    assert stage_row["mapping_state"] == "unlinked"
    assert stage_row["mapping_state_label"] == "Unmapped"
    assert stage_row["item_planned_execution_node"] == "EBN-L1"
    assert "EBS-0002" in stage_row["item_planned_node_display"]


def test_zero_stage_denominator_returns_na_without_division_error():
    nodes = [make_node("EBN-L1", code="EBS-0001", title="Site")]
    items = [make_item("BOQI-EMPTY")]
    res = rules.evaluate_coverage(project="PROJ-1", items=items, stages=[], project_nodes=nodes)

    assert res["summary"]["total_stages"] == 0
    assert res["summary"]["coverage_pct"] is None
    assert res["summary"]["coverage_pct_display"] == "N/A"
    assert res["population_summary"]["items_without_stages"] == 1
    assert res["item_group_counts"]["no_stages"] == 1
    assert len(res["_all_no_stages_rows"]) == 1


def test_reconciliation_disabled_vs_integrity_and_item_groups():
    nodes = [
        make_node("EBN-GRP", group=True, code="EBS-0001", title="Building A"),
        make_node("EBN-OK", parent="EBN-GRP", code="EBS-0002", title="Level 1"),
        make_node("EBN-DIS", parent="EBN-GRP", disabled=True, code="EBS-0003", title="Old Zone"),
        make_node("EBN-DIS-GRP", parent="EBN-GRP", group=True, disabled=True, code="EBS-0004", title="Closed Wing"),
        make_node("EBN-DIS-ANC", parent="EBN-DIS-GRP", disabled=False, code="EBS-0005", title="Room 1"),
    ]
    extra_nodes = [make_node("EBN-OTHER", project="PROJ-2", code="", title="")]
    items = [
        make_item("BOQI-FULL", wbs_code="1.1", quantity=50.0, unit="m3"),
        make_item("BOQI-PARTIAL", wbs_code="1.2", quantity=200.0, unit="kg"),
        make_item("BOQI-UNMAPPED", wbs_code="1.3", quantity=80.0, unit="m2"),
        make_item("BOQI-REVIEW", wbs_code="1.10", quantity=120.0, unit="m3"),
        make_item("BOQI-NOSTG", wbs_code="2.1", quantity=15.0, unit="Nos"),
    ]
    stages = [
        make_stage("STG-01", boq_item="BOQI-FULL", execution_node="EBN-OK", planned_qty=50.0),
        make_stage("STG-02", boq_item="BOQI-PARTIAL", execution_node="EBN-OK", planned_qty=100.0),
        make_stage("STG-03", boq_item="BOQI-PARTIAL", execution_node=None, planned_qty=100.0),
        make_stage("STG-04", boq_item="BOQI-UNMAPPED", execution_node=None, planned_qty=80.0),
        # BOQI-REVIEW has 1 healthy + 2 disabled + 3 integrity issues -> must be needs_review
        make_stage("STG-05", boq_item="BOQI-REVIEW", execution_node="EBN-OK", planned_qty=20.0),
        make_stage("STG-06", boq_item="BOQI-REVIEW", execution_node="EBN-DIS", planned_qty=20.0),
        make_stage("STG-07", boq_item="BOQI-REVIEW", execution_node="EBN-DIS-ANC", planned_qty=20.0),
        make_stage("STG-08", boq_item="BOQI-REVIEW", execution_node="EBN-GHOST", planned_qty=20.0),
        make_stage("STG-09", boq_item="BOQI-REVIEW", execution_node="EBN-OTHER", planned_qty=20.0),
        make_stage("STG-10", boq_item="BOQI-REVIEW", execution_node="EBN-GRP", planned_qty=20.0),
    ]

    res = rules.evaluate_coverage(
        project="PROJ-1",
        items=items,
        stages=stages,
        project_nodes=nodes,
        extra_nodes=extra_nodes,
    )
    summary = res["summary"]
    assert summary["total_stages"] == 10
    assert summary["healthy_linked"] == 3
    assert summary["unlinked"] == 2
    assert summary["link_issues"] == 5
    assert summary["disabled_links"] == 2
    assert summary["integrity_issues"] == 3
    assert summary["total_stages"] == summary["healthy_linked"] + summary["unlinked"] + summary["link_issues"]
    assert summary["link_issues"] == summary["disabled_links"] + summary["integrity_issues"]
    assert summary["coverage_pct"] == 30.0
    assert summary["coverage_pct_display"] == "30.0%"

    # Zero cross-item quantity totals anywhere in summary or population_summary
    for forbidden in ("total_qty", "planned_qty_total", "total_planned_qty", "quantity_total"):
        assert forbidden not in summary
        assert forbidden not in res["population_summary"]

    # Item groups reconcile cleanly and preserve natural WBS ordering (1.2 before 1.10)
    assert res["item_group_counts"] == {
        "full": 1,
        "partial": 1,
        "unmapped": 1,
        "needs_review": 1,
        "filtered_out": 0,
        "no_stages": 1,
    }
    assert sum(res["item_group_counts"].values()) == res["population_summary"]["total_items"] == 5
    assert [r["wbs_code"] for r in res["_all_item_rows"]] == ["1.1", "1.2", "1.3", "1.10", "2.1"]


def test_stage_filter_hiding_all_stages_produces_filtered_out_never_no_stages():
    nodes = [
        make_node("EBN-A", code="EBS-0001", title="Zone A"),
        make_node("EBN-B", code="EBS-0002", title="Zone B"),
    ]
    items = [
        make_item("BOQI-A", wbs_code="1.1"),
        make_item("BOQI-B", wbs_code="1.2"),
        make_item("BOQI-EMPTY", wbs_code="1.3"),
    ]
    stages = [
        make_stage("STG-A1", boq_item="BOQI-A", execution_node="EBN-A", stage_status="In Progress"),
        make_stage("STG-B1", boq_item="BOQI-B", execution_node="EBN-B", stage_status="Completed"),
    ]

    # Filter to Zone A: BOQI-B has 1 Stage in population, 0 matching -> filtered_out, NOT no_stages!
    filters = rules.normalize_filters(project="PROJ-1", execution_node="EBN-A", view_mode="items")
    res = rules.evaluate_coverage(
        project="PROJ-1", items=items, stages=stages, project_nodes=nodes, filters=filters
    )
    by_item = {row["name"]: row for row in res["_all_item_rows"]}
    assert by_item["BOQI-A"]["filtered_group"] == "full"
    assert by_item["BOQI-B"]["total_item_stages"] == 1
    assert by_item["BOQI-B"]["matching_stages"] == 0
    assert by_item["BOQI-B"]["filtered_group"] == "filtered_out"
    assert by_item["BOQI-B"]["filtered_group_label"] == "Zero Matching Stages"
    assert by_item["BOQI-EMPTY"]["filtered_group"] == "no_stages"

    assert res["item_group_counts"]["no_stages"] == 1
    assert res["item_group_counts"]["filtered_out"] == 1
    assert res["population_summary"]["items_without_stages"] == 1
    assert res["population_summary"]["items_hidden_by_stage_filters"] == 1
    assert [r["name"] for r in res["_all_no_stages_rows"]] == ["BOQI-EMPTY"]

    # Same rule for search filter hiding all Stages of BOQI-A and BOQI-B
    search_filters = rules.normalize_filters(project="PROJ-1", search="NO-MATCH-XYZ", view_mode="items")
    res2 = rules.evaluate_coverage(
        project="PROJ-1", items=items, stages=stages, project_nodes=nodes, filters=search_filters
    )
    assert res2["summary"]["total_stages"] == 0
    assert res2["summary"]["coverage_pct"] is None
    assert res2["item_group_counts"]["filtered_out"] == 2
    assert res2["item_group_counts"]["no_stages"] == 1
    assert [r["name"] for r in res2["_all_no_stages_rows"]] == ["BOQI-EMPTY"]


def test_partial_visibility_labels_zero_stage_bucket_as_no_visible_stages():
    nodes = [make_node("EBN-A", code="EBS-0001", title="Zone A")]
    items = [make_item("BOQI-1")]
    res = rules.evaluate_coverage(
        project="PROJ-1",
        items=items,
        stages=[],
        project_nodes=nodes,
        partial_visibility=True,
    )
    assert res["population_summary"]["partial_visibility"] is True
    assert res["population_summary"]["no_stages_label"] == "No visible Stages"
    assert res["_all_item_rows"][0]["filtered_group_label"] == "No visible Stages"
    assert res["_all_no_stages_rows"][0]["status_label"] == "No visible Stages"


def test_subtree_filter_includes_descendants_and_detects_node_with_unlinked_conflict():
    nodes = [
        make_node("EBN-ROOT", group=True, code="EBS-0001", title="Building"),
        make_node("EBN-FL1", parent="EBN-ROOT", group=True, code="EBS-0002", title="Floor 1"),
        make_node("EBN-RM1", parent="EBN-FL1", code="EBS-0003", title="Room 1"),
        make_node("EBN-FL2", parent="EBN-ROOT", code="EBS-0004", title="Floor 2"),
    ]
    items = [make_item("BOQI-1")]
    stages = [
        make_stage("STG-1", boq_item="BOQI-1", execution_node="EBN-RM1"),
        make_stage("STG-2", boq_item="BOQI-1", execution_node="EBN-FL2"),
        make_stage("STG-3", boq_item="BOQI-1", execution_node=None),
    ]

    # Subtree filter on EBN-FL1 matches descendant EBN-RM1 only
    f1 = rules.normalize_filters(project="PROJ-1", execution_node="EBN-FL1")
    r1 = rules.evaluate_coverage(project="PROJ-1", items=items, stages=stages, project_nodes=nodes, filters=f1)
    assert [row["name"] for row in r1["_all_stage_rows"]] == ["STG-1"]
    assert r1["filter_conflict"] is None

    # Contradictory filter: execution_node + mapping_state="unlinked"
    f2 = rules.normalize_filters(project="PROJ-1", execution_node="EBN-ROOT", mapping_state="unlinked")
    r2 = rules.evaluate_coverage(project="PROJ-1", items=items, stages=stages, project_nodes=nodes, filters=f2)
    assert r2["filter_conflict"] is not None
    assert r2["filter_conflict"]["code"] == "node_with_unlinked"
    assert r2["rows"] == []
    assert r2["summary"]["total_stages"] == 0
    assert r2["summary"]["coverage_pct"] is None
    # Item with 3 existing Stages stays filtered_out, never no_stages
    assert r2["item_group_counts"]["filtered_out"] == 1
    assert r2["item_group_counts"]["no_stages"] == 0


def test_pagination_stability_and_export_table_metadata_numeric_and_truncation():
    nodes = [make_node("EBN-L1", code="EBS-0001", title="Zone 1")]
    items = [make_item("BOQI-1", quantity=75.5, unit="m3")]
    stages = [
        make_stage(f"STG-{i:03d}", boq_item="BOQI-1", stage_code=f"S-{i:03d}", execution_node="EBN-L1", planned_qty=12.5)
        for i in range(1, 8)
    ]

    # Paginate with page_size=3 -> exact deterministic reconstruction
    collected = []
    for page in (1, 2, 3):
        f = rules.normalize_filters(project="PROJ-1", page=page, page_size=3)
        res = rules.evaluate_coverage(project="PROJ-1", items=items, stages=stages, project_nodes=nodes, filters=f)
        collected.extend(row["name"] for row in res["rows"])
    assert collected == [f"STG-{i:03d}" for i in range(1, 8)]

    # Build export table capped at max_rows=5 -> truncation metadata embedded + numeric qty
    base = rules.evaluate_coverage(project="PROJ-1", items=items, stages=stages, project_nodes=nodes)
    table = rules.build_export_table(base, view_mode="stages", max_rows=5)
    assert table["exported_rows"] == 5
    assert table["total_matching_rows"] == 7
    assert table["truncated"] is True
    assert table["omitted_rows"] == 2

    meta = {row[0]: row[1] for row in table["metadata_rows"]}
    assert meta["Exported Rows"] == 5
    assert meta["Total Matching Rows"] == 7
    assert meta["Truncated"] == "Yes"
    assert "Truncation Notice" in meta
    assert "5" in meta["Truncation Notice"] and "2" in meta["Truncation Notice"]
    assert meta["Summary — Mapping Completeness"] == "100.0%"
    assert meta["Notice"] == rules.DISCLAIMER_TEXT

    qty_col = table["headers"].index("Planned Qty")
    assert all(isinstance(row[qty_col], float) and row[qty_col] == 12.5 for row in table["data_rows"])
    assert [row[0] for row in table["data_rows"]] == [f"STG-{i:03d}" for i in range(1, 6)]

    # Items export keeps counts as int and quantities as float
    item_table = rules.build_export_table(base, view_mode="items", max_rows=5)
    iq_col = item_table["headers"].index("Item Qty")
    sq_col = item_table["headers"].index("Stage Planned Qty Sum (Single Item)")
    tot_col = item_table["headers"].index("Total Item Stages")
    assert isinstance(item_table["data_rows"][0][iq_col], float)
    assert isinstance(item_table["data_rows"][0][sq_col], float)
    assert isinstance(item_table["data_rows"][0][tot_col], int)


def test_filter_validation_rejects_bad_inputs():
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="")
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", mapping_state="bogus")
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", stage_status="Unknown")
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", view_mode="evil")
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", export_format="pdf")
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", page=0)
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", page=True)
    with pytest.raises(rules.CoverageRuleViolation):
        rules.normalize_filters(project="PROJ-1", page_size=rules.PAGE_MAX + 1)


def test_service_and_api_static_security_and_read_only_invariants():
    service_src = SERVICE_PATH.read_text(encoding="utf-8")
    api_src = API_PATH.read_text(encoding="utf-8")

    # Service enforces P1 tree authorization + native BOQ Header/Item/Stage read checks + formula sanitizer
    assert 'access.authorize(project, "read")' in service_src
    assert 'frappe.has_permission("BOQ Header", "read", doc=' in service_src
    assert 'frappe.has_permission("BOQ Item", "read", doc=' in service_src
    assert 'frappe.has_permission("BOQ Item Stage", "read", doc=' in service_src
    assert "sanitize_spreadsheet_value" in service_src
    assert "if len(subtree_structures) > MAX_POPULATION_STRUCTURES:" in service_src
    assert '"structures", MAX_POPULATION_STRUCTURES' in service_src

    # Strictly read-only: zero DB write calls or File creation anywhere in service or API
    for src in (service_src, api_src):
        for forbidden in (".insert(", ".save(", "db.set_value(", "db.delete(", "save_file", '"File"'):
            assert forbidden not in src

    # API exposes strictly GET whitelisted endpoints and streams download directly
    api_tree = ast.parse(api_src)
    whitelisted = []
    for node in ast.walk(api_tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "whitelist":
                    whitelisted.append((node.name, ast.unparse(dec)))
    assert len(whitelisted) == 2
    for _fn_name, dec_text in whitelisted:
        assert "methods=['GET']" in dec_text or 'methods=["GET"]' in dec_text
    assert 'frappe.response["type"] = "download"' in api_src


def test_structure_subtree_limit_fails_closed_when_item_structure_is_beyond_cutoff(monkeypatch):
    """Lowered-cap test: a BOQ Structure subtree exceeding MAX_POPULATION_STRUCTURES
    must return an explicit limit response (and refuse export) rather than silently
    omitting Items whose Structure falls beyond the cutoff.
    """
    import sys
    import types

    class _ValidationError(Exception):
        pass

    class _PermissionError(Exception):
        pass

    class _AttrDict(dict):
        def __getattr__(self, key):
            return self[key]

    # Root group + 3 child structures; the matching Item lives on STR-BEYOND (index 3 > cap=2)
    subtree_rows = [
        {"name": "STR-ROOT"},
        {"name": "STR-CHILD-1"},
        {"name": "STR-BEYOND"},
    ]

    fake_frappe = types.ModuleType("frappe")
    fake_frappe._ = lambda text: text
    fake_frappe.ValidationError = _ValidationError
    fake_frappe.PermissionError = _PermissionError
    fake_frappe.session = types.SimpleNamespace(user="Administrator")

    def _throw(msg, exc=_ValidationError):
        raise exc(msg)

    fake_frappe.throw = _throw
    fake_frappe.has_permission = lambda *args, **kwargs: True

    def _get_value(doctype, name, fields, as_dict=False):
        if doctype == "BOQ Structure" and name == "STR-ROOT":
            return _AttrDict(name="STR-ROOT", project="PROJ-1", boq_header="BOQ-H1", lft=1, rgt=8)
        return None

    fake_frappe.db = types.SimpleNamespace(
        table_exists=lambda _dt: True,
        sql=lambda *_a, **_kw: [],
        get_value=_get_value,
    )

    def _get_list(doctype, filters=None, fields=None, order_by=None, limit_page_length=None):
        if doctype == "BOQ Header":
            return [{"name": "BOQ-H1", "title": "Main BOQ", "boq_type": "Contract", "status": "Draft", "project": "PROJ-1"}]
        if doctype == "BOQ Structure":
            return subtree_rows[: limit_page_length or len(subtree_rows)]
        raise AssertionError(f"Unexpected get_list({doctype}) after structure limit exceeded")

    fake_frappe.get_list = _get_list

    fake_xlsx_utils = types.ModuleType("frappe.utils.xlsxutils")
    fake_xlsx_utils.ILLEGAL_CHARACTERS_RE = types.SimpleNamespace(sub=lambda _r, s: s)
    fake_xlsx_utils.get_sanitized_sheet_name = lambda name: name

    fake_utils = types.ModuleType("frappe.utils")
    fake_utils.xlsxutils = fake_xlsx_utils

    fake_xlsxwriter = types.ModuleType("xlsxwriter")

    fake_access = types.ModuleType("construction.services.execution_tree_access")
    fake_access.AccessDenied = type("AccessDenied", (Exception,), {})
    fake_access.UnsupportedProfile = type("UnsupportedProfile", (Exception,), {})
    fake_access.IntegrityFailure = type("IntegrityFailure", (Exception,), {})
    fake_access.authorize = lambda project, op: ({"allowed": True}, {})

    fake_mapping = types.ModuleType("construction.services.execution_mapping")
    fake_mapping.require_mapping_column = lambda _dt, _col: True

    fake_tree_rules = types.ModuleType("construction.services.execution_tree_rules")
    fake_tree_rules.NODE_DOCTYPE = "Execution Breakdown Node"
    fake_tree_rules.MAX_NODES = 10000
    fake_tree_rules.RuleViolation = type("RuleViolation", (ValueError,), {})

    fake_sanitizer = types.ModuleType("construction.construction.utils.export_sanitizer")
    fake_sanitizer.sanitize_spreadsheet_value = lambda val: val

    # Install isolated stub modules for loading execution_coverage.py offline
    stub_modules = {
        "frappe": fake_frappe,
        "frappe.utils": fake_utils,
        "frappe.utils.xlsxutils": fake_xlsx_utils,
        "xlsxwriter": fake_xlsxwriter,
        "construction": types.ModuleType("construction"),
        "construction.construction": types.ModuleType("construction.construction"),
        "construction.construction.utils": types.ModuleType("construction.construction.utils"),
        "construction.construction.utils.export_sanitizer": fake_sanitizer,
        "construction.services": types.ModuleType("construction.services"),
        "construction.services.execution_coverage_rules": rules,
        "construction.services.execution_mapping": fake_mapping,
        "construction.services.execution_tree_access": fake_access,
        "construction.services.execution_tree_rules": fake_tree_rules,
    }
    for mod_name, mod_obj in stub_modules.items():
        monkeypatch.setitem(sys.modules, mod_name, mod_obj)

    svc_spec = importlib.util.spec_from_file_location("execution_coverage_under_test", SERVICE_PATH)
    svc = importlib.util.module_from_spec(svc_spec)
    assert svc_spec.loader is not None
    svc_spec.loader.exec_module(svc)

    # Cap = 2 structures, while subtree has 3 structures (STR-BEYOND is beyond the cutoff!)
    monkeypatch.setattr(svc, "MAX_POPULATION_STRUCTURES", 2)

    resp = svc.get_execution_coverage(project="PROJ-1", boq_structure="STR-ROOT")
    assert resp["ok"] is False
    assert resp["limit_exceeded"] is True
    assert resp["limit_type"] == "structures"
    assert resp["limit"] == 2
    assert resp["summary"] is None
    assert resp["population_summary"] is None
    assert resp["rows"] == []

    with pytest.raises(_ValidationError):
        svc.build_execution_coverage_export(
            project="PROJ-1", boq_structure="STR-ROOT", export_format="csv"
        )
