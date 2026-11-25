"""Offline vectors for the pure WBS authorization-decision rules.

These vectors distinguish native Project authorization from the additional WBS
role and organizational boundary. They do not exercise a database, a live
Frappe permission cache, or an HTTP route.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import subprocess
import sys
import threading
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "construction" / "services" / "execution_tree_rules.py"
SPEC = importlib.util.spec_from_file_location("execution_tree_access_rules", MODULE_PATH)
rules = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rules)


_FRAPPE_STUB = None
_STUB_NAMES = (
    "frappe",
    "frappe.model",
    "frappe.model.document",
    "construction",
    "construction.services",
    "construction.services.execution_tree_rules",
    "construction.services.execution_tree_access",
    "construction.setup",
    "construction.setup.execution_tree_schema",
)


def _ensure_frappe_stub():
    global _FRAPPE_STUB
    if _FRAPPE_STUB is None:
        frappe_stub = types.ModuleType("frappe")
        frappe_stub.session = types.SimpleNamespace(user="offline@example.test")
        frappe_stub.PermissionError = type("PermissionError", (Exception,), {})
        frappe_stub.ValidationError = type("ValidationError", (Exception,), {})
        frappe_stub._ = lambda message: message

        def _throw(message, exc=None):
            raise (exc or frappe_stub.ValidationError)(message)

        frappe_stub.throw = _throw
        _FRAPPE_STUB = frappe_stub
    return _FRAPPE_STUB


@contextlib.contextmanager
def _framework_stubs():
    """Register stub packages only while an isolated module executes.

    The stub entries are removed afterwards so the offline import guard in
    conftest remains effective for the rest of the suite.
    """

    frappe_stub = _ensure_frappe_stub()
    construction = types.ModuleType("construction")
    construction.__path__ = []
    services = types.ModuleType("construction.services")
    services.__path__ = []
    services.execution_tree_rules = rules
    services.execution_tree_access = sys.modules.get("execution_tree_access_under_test")
    setup_package = types.ModuleType("construction.setup")
    setup_package.__path__ = []
    sys.modules.update(
        {
            "frappe": frappe_stub,
            "construction": construction,
            "construction.services": services,
            "construction.services.execution_tree_rules": rules,
            "construction.setup": setup_package,
        }
    )
    access_module = sys.modules.get("execution_tree_access_under_test")
    if access_module is not None:
        sys.modules["construction.services.execution_tree_access"] = access_module
    try:
        yield frappe_stub
    finally:
        for name in _STUB_NAMES:
            sys.modules.pop(name, None)


def _load_access_module():
    """Load the access module in isolation with a stubbed framework.

    This keeps the offline suite free of real ``construction``/``frappe``
    imports while exercising profile parsing, share evaluation, scope
    normalization and reader cleanup with fake readers.
    """

    if "execution_tree_access_under_test" in sys.modules:
        return sys.modules["execution_tree_access_under_test"]
    path = ROOT / "construction" / "services" / "execution_tree_access.py"
    spec = importlib.util.spec_from_file_location("execution_tree_access_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with _framework_stubs():
        spec.loader.exec_module(module)
    sys.modules["execution_tree_access_under_test"] = module
    return module


access = _load_access_module()


class FakeReader:
    def __init__(self, *, one=None, query=None):
        self._one = one or (lambda sql, params=None: None)
        self._query = query or (lambda sql, params=None: [])
        self.calls = []

    def one(self, sql, params=None):
        self.calls.append(("one", sql, params))
        return self._one(sql, params)

    def query(self, sql, params=None):
        self.calls.append(("query", sql, params))
        return self._query(sql, params)


class FakeConnection:
    def __init__(self, *, cursor_error=None):
        self.cursor_error = cursor_error
        self.rollback_called = False
        self.close_called = False

    def cursor(self):
        if self.cursor_error:
            raise self.cursor_error
        return types.SimpleNamespace(
            execute=lambda *a, **k: None,
            fetchone=lambda: {"isolation": "REPEATABLE-READ", "read_only": 1},
        )

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.close_called = True


STOCK_PERMISSIONS = [
    {"role": "Projects Manager", "permlevel": 0, "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "Projects User", "permlevel": 0, "read": 1, "write": 1},
    {"role": "Employee", "permlevel": 0, "select": 1},
]

CUSTOM_PERMISSIONS = [
    {"role": "Projects User", "permlevel": 0, "read": 1, "write": 0},
    {"role": "Project Manager", "permlevel": 0, "write": 1},
]


def test_role_permission_projection_matches_stock_project_semantics():
    result = rules.compute_role_permissions(STOCK_PERMISSIONS, {"Projects User"})
    assert result["read"] == 1
    assert result["write"] == 1
    assert result["create"] == 0
    assert result["delete"] == 0


def test_custom_docperm_replaces_stock_permissions():
    result = rules.compute_role_permissions(CUSTOM_PERMISSIONS, {"Projects Manager"})
    assert result["read"] == 0
    assert result["write"] == 0
    custom = rules.compute_role_permissions(CUSTOM_PERMISSIONS, {"Project Manager"})
    assert custom["write"] == 1


def test_if_owner_permissions_only_grant_expected_rights():
    permissions = [{"role": "All", "permlevel": 0, "read": 1, "write": 1, "if_owner": 1}]
    owner = rules.compute_role_permissions(permissions, {"All"}, is_owner=True)
    outsider = rules.compute_role_permissions(permissions, {"All"}, is_owner=False)
    assert owner["if_owner"]["write"] == 1
    assert outsider["if_owner"]["write"] == 0
    assert outsider["read"] == 1
    merged_owner = rules.evaluate_native_document_permission(
        permissions=permissions,
        roles={"All"},
        is_owner=True,
        ptype="write",
        user_permission_allowed=True,
    )
    merged_outsider = rules.evaluate_native_document_permission(
        permissions=permissions,
        roles={"All"},
        is_owner=False,
        ptype="read",
        user_permission_allowed=True,
    )
    assert merged_owner["allowed"] is True
    assert merged_outsider["allowed"] is False


def test_owner_user_permission_fallback_replaces_permissions():
    permissions = [{"role": "Projects User", "permlevel": 0, "read": 1, "if_owner": 1}]
    owner_result = rules.evaluate_native_document_permission(
        permissions=permissions,
        roles={"Projects User"},
        is_owner=True,
        ptype="read",
        user_permission_allowed=False,
    )
    outsider_result = rules.evaluate_native_document_permission(
        permissions=permissions,
        roles={"Projects User"},
        is_owner=False,
        ptype="read",
        user_permission_allowed=False,
    )
    assert owner_result["allowed"] is True
    assert owner_result["stage"] == "document_permission"
    assert outsider_result["allowed"] is False


def test_document_denial_can_fall_back_to_a_matching_share():
    denied = rules.evaluate_native_document_permission(
        permissions=CUSTOM_PERMISSIONS,
        roles={"Projects User"},
        is_owner=False,
        ptype="write",
        user_permission_allowed=True,
        share_allowed=False,
    )
    shared = rules.evaluate_native_document_permission(
        permissions=CUSTOM_PERMISSIONS,
        roles={"Projects User"},
        is_owner=False,
        ptype="write",
        user_permission_allowed=True,
        share_allowed=True,
    )
    assert denied["allowed"] is False
    assert shared["allowed"] is True
    assert shared["stage"] == "share_fallback"


def test_controller_denial_still_allows_native_share_fallback():
    result = rules.evaluate_native_document_permission(
        permissions=STOCK_PERMISSIONS,
        roles={"Projects User"},
        is_owner=False,
        ptype="read",
        user_permission_allowed=True,
        share_allowed=True,
        controller_denied=True,
    )
    assert result["allowed"] is True
    assert result["stage"] == "share_fallback"


def test_unsupported_profile_blocks_before_share_fallback():
    with pytest.raises(rules.UnsupportedProfile):
        rules.evaluate_native_document_permission(
            permissions=STOCK_PERMISSIONS,
            roles={"Projects User"},
            is_owner=False,
            ptype="read",
            user_permission_allowed=True,
            share_allowed=True,
            unsupported="unexpected Project has_permission hook",
        )


def test_user_permissions_check_self_and_link_fields():
    user_permissions = {
        "Project": [{"doc": "P1", "applicable_for": None}],
        "Company": [{"doc": "A", "applicable_for": "Project"}],
    }
    link_fields = [
        {"fieldname": "company", "options": "Company", "ignore_user_permissions": 0},
        {"fieldname": "customer", "options": "Customer", "ignore_user_permissions": 0},
    ]
    assert rules.user_permission_allows(
        doctype="Project",
        docname="P1",
        doc_values={"company": "A"},
        link_fields=link_fields,
        user_permissions=user_permissions,
    )
    assert not rules.user_permission_allows(
        doctype="Project",
        docname="P2",
        doc_values={"company": "A"},
        link_fields=link_fields,
        user_permissions=user_permissions,
    )
    assert not rules.user_permission_allows(
        doctype="Project",
        docname="P1",
        doc_values={"company": "B"},
        link_fields=link_fields,
        user_permissions=user_permissions,
    )


def test_strict_user_permissions_reject_blank_links_but_exempts_are_supported():
    user_permissions = {"Company": [{"doc": "A", "applicable_for": None}]}
    link_fields = [{"fieldname": "company", "options": "Company", "ignore_user_permissions": 0}]
    assert rules.user_permission_allows(
        doctype="Project",
        docname="P1",
        doc_values={"company": ""},
        link_fields=link_fields,
        user_permissions=user_permissions,
        strict=False,
    )
    assert not rules.user_permission_allows(
        doctype="Project",
        docname="P1",
        doc_values={"company": ""},
        link_fields=link_fields,
        user_permissions=user_permissions,
        strict=True,
    )
    assert rules.user_permission_allows(
        doctype="Project",
        docname="P1",
        doc_values={"company": "B"},
        link_fields=[{"fieldname": "company", "options": "Company", "ignore_user_permissions": 1}],
        user_permissions=user_permissions,
        strict=True,
    )


def test_applicable_for_is_filtered_per_doctype():
    user_permissions = {"Company": [{"doc": "A", "applicable_for": "Sales Order"}]}
    assert rules.user_permission_allows(
        doctype="Project",
        docname="P1",
        doc_values={"company": "B"},
        link_fields=[{"fieldname": "company", "options": "Company"}],
        user_permissions=user_permissions,
    )


def test_browse_requires_wbs_role_and_native_read():
    allowed = rules.decide_operation_access(
        operation="read",
        roles={"Site Engineer"},
        native_read=True,
        native_write=False,
        organizational_allowed=True,
    )
    missing_native = rules.decide_operation_access(
        operation="read",
        roles={"Site Engineer"},
        native_read=False,
        native_write=False,
        organizational_allowed=True,
    )
    no_role = rules.decide_operation_access(
        operation="read",
        roles={"Accounts User"},
        native_read=True,
        native_write=False,
        organizational_allowed=True,
    )
    assert allowed["allowed"] is True
    assert missing_native["reason"] == "native_project_permission"
    assert no_role["reason"] == "wbs_role"


def test_mutation_matrix_requires_write_and_delete_requires_system_manager():
    create = rules.decide_operation_access(
        operation="create",
        roles={"Project Manager"},
        native_read=True,
        native_write=True,
        organizational_allowed=True,
    )
    no_write = rules.decide_operation_access(
        operation="update",
        roles={"Project Manager"},
        native_read=True,
        native_write=False,
        organizational_allowed=True,
    )
    site_delete = rules.decide_operation_access(
        operation="delete",
        roles={"Site Engineer", "Project Manager"},
        native_read=True,
        native_write=True,
        organizational_allowed=True,
    )
    manager_delete = rules.decide_operation_access(
        operation="delete",
        roles={"System Manager"},
        native_read=True,
        native_write=True,
        organizational_allowed=True,
    )
    assert create["allowed"] is True
    assert no_write["reason"] == "native_project_permission"
    assert site_delete["reason"] == "wbs_role"
    assert manager_delete["allowed"] is True


def test_organizational_boundary_applies_to_system_manager():
    denied = rules.decide_operation_access(
        operation="read",
        roles={"System Manager"},
        native_read=True,
        native_write=True,
        organizational_allowed=False,
    )
    assert denied["allowed"] is False
    assert denied["reason"] == "organizational_boundary"


def test_literal_administrator_retains_native_bypass():
    result = rules.decide_operation_access(
        operation="delete",
        roles=set(),
        native_read=False,
        native_write=False,
        organizational_allowed=False,
        is_administrator=True,
    )
    assert result["allowed"] is True
    assert result["reason"] == "administrator"


def test_scope_boundary_disabled_keeps_native_and_role_checks():
    assert rules.organizational_allows(
        scope_enabled=False,
        scope=None,
        project="P1",
        project_company="A",
        project_cost_center="CC-A",
    )


def test_scope_boundary_enabled_requires_company_project_and_cost_center_subtree():
    scope = {"company": "A", "project": "P1", "cost_center": "CC-ROOT"}
    assert rules.organizational_allows(
        scope_enabled=True,
        scope=scope,
        project="P1",
        project_company="A",
        project_cost_center="CC-CHILD",
        cost_center_in_scope_subtree=True,
    )
    assert not rules.organizational_allows(
        scope_enabled=True,
        scope=scope,
        project="P1",
        project_company="B",
        project_cost_center="CC-CHILD",
    )
    assert not rules.organizational_allows(
        scope_enabled=True,
        scope=scope,
        project="P2",
        project_company="A",
        project_cost_center="CC-CHILD",
    )
    assert not rules.organizational_allows(
        scope_enabled=True,
        scope=scope,
        project="P1",
        project_company="A",
        project_cost_center="CC-OUTSIDE",
        cost_center_in_scope_subtree=False,
    )


def test_scope_boundary_missing_scope_or_blank_project_cost_center():
    assert not rules.organizational_allows(
        scope_enabled=True,
        scope=None,
        project="P1",
        project_company="A",
        project_cost_center="CC-A",
    )
    assert not rules.organizational_allows(
        scope_enabled=True,
        scope={"company": "", "project": "P1"},
        project="P1",
        project_company="A",
        project_cost_center="CC-A",
    )
    assert rules.organizational_allows(
        scope_enabled=True,
        scope={"company": "A", "cost_center": "CC-ROOT"},
        project="P1",
        project_company="A",
        project_cost_center=None,
    )


def test_installed_app_registry_requires_exact_order_and_no_duplicates():
    rows = [{"defvalue": '["frappe", "erpnext", "construction"]'}]
    reader = FakeReader(query=lambda sql, params=None: rows if "installed_apps" in sql else [])
    assert access._read_installed_apps(reader) == ("frappe", "erpnext", "construction")
    for payload in (
        [],
        ["frappe", "construction", "erpnext"],
        ["frappe", "erpnext", "construction", "construction"],
        ["frappe", "erpnext"],
        "not json",
    ):
        bad = FakeReader(
            query=lambda sql, params=None, payload=payload: [{"defvalue": json.dumps(payload)}]
            if isinstance(payload, list)
            else [{"defvalue": payload}],
        )
        with pytest.raises(access.UnsupportedProfile):
            access._read_installed_apps(bad)


def test_empty_or_ambiguous_registry_denies():
    empty = FakeReader(query=lambda sql, params=None: [])
    with pytest.raises(access.UnsupportedProfile):
        access._read_installed_apps(empty)
    ambiguous = FakeReader(query=lambda sql, params=None: [{"defvalue": "[]"}, {"defvalue": "[]"}])
    with pytest.raises(access.UnsupportedProfile):
        access._read_installed_apps(ambiguous)


def test_null_user_share_is_not_a_grant_but_everyone_and_exact_actor_are():
    assert rules.share_grants(row_user=None, everyone=0, actor="u@example.test") is False
    assert rules.share_grants(row_user="", everyone=0, actor="u@example.test") is False
    assert rules.share_grants(row_user="other@example.test", everyone=0, actor="u@example.test") is False
    assert rules.share_grants(row_user="u@example.test", everyone=0, actor="u@example.test") is True
    assert rules.share_grants(row_user=None, everyone=1, actor="u@example.test") is True
    assert rules.share_grants(row_user=None, everyone=1, actor="Guest") is False


def test_share_allowed_rejects_null_user_without_everyone():
    rows = [{"user": None, "everyone": 0, "read": 1, "write": 0, "share": 0}]
    reader = FakeReader(query=lambda sql, params=None: rows)
    assert access._share_allowed(reader, "P1", "actor@example.test", "read") is False
    rows[0]["everyone"] = 1
    assert access._share_allowed(reader, "P1", "actor@example.test", "read") is True


def test_child_rows_require_parenttype_and_parentfield_and_reject_inconsistent_rows():
    stock = _stock_field_dicts("Project User")

    def one(sql, params=None):
        if "tabDocType" in sql:
            return {"name": "Project User", "module": "Projects", "istable": 1, "issingle": 0, "is_tree": 0}
        if "COUNT(*)" in sql and "parenttype" in sql:
            return {"total": 0}
        if "information_schema.COLUMNS" in sql:
            return {"data_type": "varchar"}
        return None

    def query(sql, params=None):
        if "tabDocField" in sql:
            return stock
        if "tabCustom Field" in sql:
            return []
        if "tabProperty Setter" in sql:
            return []
        if "tabProject User" in sql:
            return [{"parent": "P1", "parenttype": "Project", "parentfield": "users", "user": "u"}]
        return []

    reader = FakeReader(one=one, query=query)
    rows, _links = access._read_child_rows(reader, "P1", "Project User")
    assert rows and rows[0]["user"] == "u"
    child_sql = [call[1] for call in reader.calls if "tabProject User" in call[1]]
    assert any("parenttype='Project'" in sql and "parentfield='users'" in sql for sql in child_sql)
    assert any("parenttype<>'Project'" in sql for sql in child_sql)


def test_child_rows_reject_inconsistent_attached_rows():
    stock = _stock_field_dicts("Project User")

    def one(sql, params=None):
        if "tabDocType" in sql:
            return {"name": "Project User", "module": "Projects", "istable": 1, "issingle": 0, "is_tree": 0}
        if "COUNT(*)" in sql and "parenttype" in sql:
            return {"total": 1}
        if "information_schema.COLUMNS" in sql:
            return {"data_type": "varchar"}
        return None

    def query(sql, params=None):
        if "tabDocField" in sql:
            return stock
        return []

    reader = FakeReader(one=one, query=query)
    with pytest.raises(access.IntegrityFailure):
        access._read_child_rows(reader, "P1", "Project User")


def test_scope_setting_missing_empty_or_nonbinary_denies():
    for raw in (None, "", "2", "yes"):
        with pytest.raises(rules.RuleViolation):
            rules.parse_scope_enabled(raw)
    assert rules.parse_scope_enabled("0") is False
    assert rules.parse_scope_enabled("1") is True
    assert rules.parse_scope_enabled(True) is True


def test_organizational_scope_missing_configuration_denies():
    reader = FakeReader(query=lambda sql, params=None: [])
    with pytest.raises(access.AccessDenied):
        access._organizational_allowed(reader, "u", {"name": "P1", "company": "A"}, {})


def test_fresh_reader_closes_when_cursor_creation_fails(monkeypatch):
    connection = FakeConnection(cursor_error=RuntimeError("cursor failed"))
    module = types.ModuleType("MySQLdb")
    module.cursors = types.SimpleNamespace(DictCursor=object)
    module.release = types.SimpleNamespace(version_info=(2, 2, 7, "final", 0))
    module.connect = lambda **kwargs: connection
    monkeypatch.setitem(sys.modules, "MySQLdb", module)
    monkeypatch.setitem(sys.modules, "MySQLdb.cursors", module.cursors)
    monkeypatch.setitem(sys.modules, "MySQLdb.release", module.release)
    monkeypatch.setattr(access, "_connection_settings", lambda: {})
    with pytest.raises(RuntimeError):
        with access.FreshAuthorityReader():
            pass
    assert connection.rollback_called is True
    assert connection.close_called is True


def test_fresh_reader_refuses_reconnect_attempt(monkeypatch):
    connection = FakeConnection()
    module = types.ModuleType("MySQLdb")
    module.cursors = types.SimpleNamespace(DictCursor=object)
    module.release = types.SimpleNamespace(version_info=(2, 2, 7, "final", 0))
    module.connect = lambda **kwargs: connection
    monkeypatch.setitem(sys.modules, "MySQLdb", module)
    monkeypatch.setitem(sys.modules, "MySQLdb.cursors", module.cursors)
    monkeypatch.setitem(sys.modules, "MySQLdb.release", module.release)
    monkeypatch.setattr(access, "_connection_settings", lambda: {})
    reader = access.FreshAuthorityReader()
    with reader:
        assert connection.ping is access._refuse_ping
        with pytest.raises(access.UnsupportedProfile, match="econnect attempt refused"):
            connection.ping()
    assert connection.close_called is True


def test_fresh_reader_rejects_unreviewed_driver_generation(monkeypatch):
    connection = FakeConnection()
    module = types.ModuleType("MySQLdb")
    module.cursors = types.SimpleNamespace(DictCursor=object)
    module.release = types.SimpleNamespace(version_info=(2, 1, 9, "final", 0))
    module.connect = lambda **kwargs: connection
    monkeypatch.setitem(sys.modules, "MySQLdb", module)
    monkeypatch.setitem(sys.modules, "MySQLdb.cursors", module.cursors)
    monkeypatch.setitem(sys.modules, "MySQLdb.release", module.release)
    monkeypatch.setattr(access, "_connection_settings", lambda: {})
    with pytest.raises(access.UnsupportedProfile, match="outside the reviewed generation"):
        with access.FreshAuthorityReader():
            pass
    assert connection.close_called is False


def test_seal_accepts_matching_source_and_rejects_changed_source():
    path = ROOT / "construction" / "services" / "execution_tree_access.py"
    source = path.read_text()
    access._seal_module(
        "execution_tree_access_under_test", source, path, ROOT / "construction", required=True
    )
    changed = source.replace(
        "Nested execution tree guards are not permitted.",
        "A different guard message.",
    )
    assert changed != source
    with pytest.raises(access.UnsupportedProfile):
        access._seal_module(
            "execution_tree_access_under_test", changed, path, ROOT / "construction", required=True
        )


def test_seal_denies_a_missing_required_module():
    path = ROOT / "construction" / "services" / "execution_tree_access.py"
    with pytest.raises(access.UnsupportedProfile):
        access._seal_module(
            "not.a.serving.module", path.read_text(), path, ROOT / "construction", required=True
        )


class _ProjectMetaReader:
    def one(self, sql, params=None):
        if "tabDocType" in sql:
            return {
                "name": "Project",
                "module": "Projects",
                "istable": 0,
                "issingle": 0,
                "is_tree": 0,
            }
        if "information_schema.COLUMNS" in sql:
            return {"data_type": "varchar"}
        return None

    def query(self, sql, params=None):
        return []


def _stock_field_dicts(doctype="Project"):
    pinned = (
        rules.PINNED_STOCK_PROJECT_FIELDS if doctype == "Project" else rules.PINNED_STOCK_PROJECT_USER_FIELDS
    )
    return [dict(zip(rules.STOCK_FIELD_PROJECTION_ATTRIBUTES, row, strict=True)) for row in pinned]


def _project_stock_fields(extra=None):
    fields = _stock_field_dicts("Project")
    if extra is not None:
        fields.append(extra)
    return fields


def test_project_stock_metadata_accepts_the_validated_users_table():
    access._validate_stock_metadata(_ProjectMetaReader(), "Project", _project_stock_fields())


def test_project_stock_metadata_rejects_an_additional_child_table():
    extra = {
        "fieldname": "other_users",
        "fieldtype": "Table",
        "options": "Project User",
        "ignore_user_permissions": 0,
        "permlevel": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
    }
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_ProjectMetaReader(), "Project", _project_stock_fields(extra))


def test_project_stock_metadata_rejects_a_forbidden_field_type():
    extra = {
        "fieldname": "computed",
        "fieldtype": "Dynamic Link",
        "options": "",
        "ignore_user_permissions": 0,
        "permlevel": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
    }
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_ProjectMetaReader(), "Project", _project_stock_fields(extra))


def test_custom_link_storage_requires_a_physical_column():
    present = FakeReader(one=lambda sql, params=None: {"data_type": "varchar"})
    access._assert_custom_link_storage(present, "Project", "branch")
    assert any("information_schema.COLUMNS" in call[1] for call in present.calls)

    missing = FakeReader(one=lambda sql, params=None: None)
    with pytest.raises(access.UnsupportedProfile):
        access._assert_custom_link_storage(missing, "Project", "branch")

    wrong_type = FakeReader(one=lambda sql, params=None: {"data_type": "int"})
    with pytest.raises(access.UnsupportedProfile):
        access._assert_custom_link_storage(wrong_type, "Project", "branch")


def test_loaded_hook_comparison_normalizes_listified_handlers(monkeypatch):
    projections = {
        "construction": {
            "has_permission": {"Execution Breakdown Node": "h"},
            "permission_query_conditions": {
                "*": "q",
                "Execution Code Counter": "q2",
            },
            "override_doctype_class": {},
            "extend_doctype_class": {},
            "get_child_provider": {},
        }
    }
    loaded = {
        "has_permission": {"Execution Breakdown Node": ["h"]},
        "permission_query_conditions": {
            "*": ["q"],
            "Execution Code Counter": ["q2"],
        },
        "override_doctype_class": {},
        "extend_doctype_class": {},
        "get_child_provider": {},
    }
    monkeypatch.setattr(
        access.frappe, "get_hooks", lambda hook, app_name=None: loaded.get(hook, []), raising=False
    )
    access._assert_loaded_hooks_match(["construction"], projections, {"construction": {}})

    changed = dict(loaded)
    changed["has_permission"] = {"Execution Breakdown Node": ["other"]}
    monkeypatch.setattr(
        access.frappe, "get_hooks", lambda hook, app_name=None: changed.get(hook, []), raising=False
    )
    with pytest.raises(access.UnsupportedProfile):
        access._assert_loaded_hooks_match(["construction"], projections, {"construction": {}})


def _metadata_reader(custom_rows=(), *, virtual_doctype=0, setters=()):
    def one(sql, params=None):
        if "tabDocType" in sql:
            return {
                "name": "Project",
                "module": "Projects",
                "istable": 0,
                "issingle": 0,
                "is_tree": 0,
                "is_virtual": virtual_doctype,
            }
        if "information_schema.COLUMNS" in sql:
            return {"data_type": "varchar"}
        return None

    def query(sql, params=None):
        if "tabDocField" in sql:
            doctype = params[0] if params else "Project"
            return _stock_field_dicts(doctype)
        if "tabCustom Field" in sql:
            return list(custom_rows)
        if "tabProperty Setter" in sql:
            return list(setters)
        return []

    return FakeReader(one=one, query=query)


def test_virtual_custom_field_is_rejected_before_permission_evaluation():
    custom = {
        "fieldname": "computed_note",
        "fieldtype": "Data",
        "options": "",
        "ignore_user_permissions": 0,
        "permlevel": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
        "is_virtual": 1,
    }
    with pytest.raises(access.UnsupportedProfile):
        access._read_fields(_metadata_reader([custom]), "Project")


def test_virtual_doctype_identity_is_rejected():
    with pytest.raises(access.UnsupportedProfile):
        access._assert_doctype_stock_identity(_metadata_reader(virtual_doctype=1), "Project", istable=0)


class _GuardDoc:
    doctype = rules.NODE_DOCTYPE

    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_capability_binds_permission_type_to_its_operation():
    doc = _GuardDoc(project="P1")
    other = _GuardDoc(project="P1")
    with access.establish_guard(
        actor="offline@example.test",
        operation="create",
        project="P1",
        doctype=rules.NODE_DOCTYPE,
        document=doc,
    ):
        assert access.has_protected_permission(doc, "create", user="offline@example.test") is True
        assert access.has_protected_permission(doc, "write", user="offline@example.test") is False
        assert access.has_protected_permission(doc, "delete", user="offline@example.test") is False
        # A different unsaved object cannot borrow the create capability.
        assert access.has_protected_permission(other, "create", user="offline@example.test") is False


# ---------------------------------------------------------------------------
# SCP-004: complete stock field projection vs the pinned schema
# ---------------------------------------------------------------------------


def test_stock_metadata_rejects_an_extra_typed_scalar_field():
    extra = {
        "fieldname": "wbs_note",
        "fieldtype": "Data",
        "options": None,
        "ignore_user_permissions": 0,
        "permlevel": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
        "is_virtual": 0,
    }
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_ProjectMetaReader(), "Project", _project_stock_fields(extra))


def test_stock_metadata_rejects_missing_or_altered_stock_fields():
    fields = _project_stock_fields()
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_ProjectMetaReader(), "Project", fields[:-1])
    altered = _project_stock_fields()
    for field in altered:
        if field["fieldname"] == "company":
            field["reqd"] = 0
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_ProjectMetaReader(), "Project", altered)
    reordered = _project_stock_fields()
    reordered[0], reordered[1] = reordered[1], reordered[0]
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_ProjectMetaReader(), "Project", reordered)


def test_stock_metadata_requires_physical_storage_for_stock_links():
    class _NoStorageReader(_ProjectMetaReader):
        def one(self, sql, params=None):
            if "information_schema.COLUMNS" in sql:
                return None
            return super().one(sql, params)

    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(_NoStorageReader(), "Project", _project_stock_fields())


def test_project_user_stock_projection_is_pinned():
    class _ChildMetaReader(_ProjectMetaReader):
        def one(self, sql, params=None):
            if "tabDocType" in sql:
                return {
                    "name": "Project User",
                    "module": "Projects",
                    "istable": 1,
                    "issingle": 0,
                    "is_tree": 0,
                }
            return super().one(sql, params)

    access._validate_stock_metadata(_ChildMetaReader(), "Project User", _stock_field_dicts("Project User"))
    extra = {
        "fieldname": "extra",
        "fieldtype": "Data",
        "options": None,
        "ignore_user_permissions": 0,
        "permlevel": 0,
        "hidden": 0,
        "reqd": 0,
        "read_only": 0,
        "is_virtual": 0,
    }
    with pytest.raises(access.UnsupportedProfile):
        access._validate_stock_metadata(
            _ChildMetaReader(), "Project User", [*_stock_field_dicts("Project User"), extra]
        )


# ---------------------------------------------------------------------------
# SCP-003: semantic / DocType-level / missing-target Property Setters
# ---------------------------------------------------------------------------


def _setter_row(field_name, prop, value, property_type, scope="DocField"):
    return {
        "field_name": field_name,
        "property": prop,
        "value": value,
        "property_type": property_type,
        "doctype_or_field": scope,
    }


def test_semantic_property_setter_is_denied_at_field_load():
    setter = _setter_row("company", "ignore_user_permissions", "1", "Check")
    with pytest.raises(access.UnsupportedProfile):
        access._read_fields(_metadata_reader(setters=[setter]), "Project")


def test_doctype_level_property_setter_is_denied():
    setter = _setter_row(None, "label", "Renamed", "Data", scope="DocType")
    with pytest.raises(access.UnsupportedProfile):
        access._read_fields(_metadata_reader(setters=[setter]), "Project")


def test_property_setter_with_missing_target_is_denied():
    setter = _setter_row("not_a_field", "label", "X", "Data")
    with pytest.raises(access.UnsupportedProfile):
        access._read_fields(_metadata_reader(setters=[setter]), "Project")


def test_stock_naming_series_options_setter_is_applied_on_project():
    # Regression: every ordinary (non-Administrator) `get_tree` read hit the
    # stock `Project-naming_series-options` Property Setter and denied with
    # 403. The read profile accepts it because it pins the stock Project
    # projection.
    setter = _setter_row("naming_series", "options", "PROJ-.####", "Text")
    fields = access._read_fields(_metadata_reader(setters=[setter]), "Project")
    naming_series = next(field for field in fields if field["fieldname"] == "naming_series")
    assert naming_series["options"] == "PROJ-.####"


def test_permlevel_and_options_setters_are_denied():
    for prop, value, property_type in (
        ("permlevel", "0", "Int"),
        ("options", "Company", "Data"),
        ("fieldtype", "Data", "Data"),
        ("fieldname", "company", "Data"),
    ):
        with pytest.raises(access.UnsupportedProfile):
            access._read_fields(
                _metadata_reader(setters=[_setter_row("company", prop, value, property_type)]),
                "Project",
            )


def test_typed_cosmetic_setter_is_applied():
    setter = _setter_row("company", "label", "Operating Company", "Data")
    fields = access._read_fields(_metadata_reader(setters=[setter]), "Project")
    company = next(field for field in fields if field["fieldname"] == "company")
    assert company["label"] == "Operating Company"


# ---------------------------------------------------------------------------
# SCP-011 / SCP-017 / SCP-016: evaluation integrity
# ---------------------------------------------------------------------------


class _EvalReader:
    """Fake authority reader routing the exact queries _evaluate issues."""

    def __init__(self, *, roles=("Project Manager", "Projects Manager"), strict="0", sharing="0", scope="0"):
        self.roles = roles
        self.strict = strict
        self.sharing = sharing
        self.scope = scope
        self.engine_checked = False
        self.calls = []

    def one(self, sql, params=None):
        self.calls.append(("one", sql, params))
        if "FROM tabUser " in sql or "FROM tabUser WHERE" in sql:
            return {"name": params[0], "enabled": 1, "user_type": "System User"}
        if "FROM tabProject " in sql or "FROM tabProject WHERE" in sql:
            return {"name": "P1", "company": "A", "cost_center": None, "owner": "other@example.test"}
        if "tabDocType" in sql:
            child = params and params[0] == "Project User"
            return {
                "name": params[0] if params else "Project",
                "module": "Projects",
                "istable": 1 if child else 0,
                "issingle": 0,
                "is_tree": 0,
                "is_virtual": 0,
            }
        if "information_schema.COLUMNS" in sql:
            return {"data_type": "varchar"}
        if "COUNT(*)" in sql and "parenttype" in sql:
            return {"total": 0}
        if "tabUser Scope Context" in sql:
            return None
        return None

    def query(self, sql, params=None):
        self.calls.append(("query", sql, params))
        if "tabHas Role" in sql:
            return [{"role": role} for role in self.roles]
        if "tabDocField" in sql:
            return _stock_field_dicts(params[0] if params else "Project")
        if "tabCustom Field" in sql or "tabProperty Setter" in sql:
            return []
        if "tabCustom DocPerm" in sql:
            return []
        if "tabDocPerm" in sql:
            return [dict(row) for row in STOCK_PERMISSIONS]
        if "tabUser Permission" in sql:
            return []
        if "tabDocShare" in sql:
            return []
        if "tabProject User" in sql:
            return []
        if "tabSingles" in sql:
            doctype = params[0]
            if doctype == "Construction Settings":
                return [] if self.scope is None else [{"field": "enable_scope_context", "value": self.scope}]
            rows = []
            if self.strict is not None:
                rows.append({"field": "apply_strict_user_permissions", "value": self.strict})
            if self.sharing is not None:
                rows.append({"field": "disable_document_sharing", "value": self.sharing})
            return rows
        return []

    def verify_storage_engines(self):
        self.engine_checked = True
        return True


def _patch_profile(monkeypatch, profile=None):
    monkeypatch.setattr(
        access,
        "_assert_supported_profile",
        lambda reader: profile
        if profile is not None
        else {"installed": ("frappe", "erpnext", "construction")},
    )
    monkeypatch.setattr(access, "_assert_no_protected_shares", lambda reader: None)
    monkeypatch.setattr(access, "_recheck_profile", lambda profile: True)


def test_administrator_does_not_bypass_deployment_profile(monkeypatch):
    def _broken(reader):
        raise access.UnsupportedProfile("profile integrity broken")

    monkeypatch.setattr(access, "_assert_supported_profile", _broken)
    monkeypatch.setattr(access.frappe.session, "user", "Administrator")
    reader = FakeReader()
    with pytest.raises(access.UnsupportedProfile):
        access._evaluate(reader, "P1", "read")
    assert reader.calls == []


def test_administrator_positive_path_verifies_storage(monkeypatch):
    _patch_profile(monkeypatch)
    monkeypatch.setattr(access.frappe.session, "user", "Administrator")
    reader = _EvalReader()
    decision = access._evaluate(reader, "P1", "delete")
    assert decision["allowed"] is True
    assert decision["reason"] == "administrator"
    assert reader.engine_checked is True


def test_missing_strict_user_permission_setting_denies(monkeypatch):
    _patch_profile(monkeypatch)
    monkeypatch.setattr(access.frappe.session, "user", "manager@example.test")
    reader = _EvalReader(strict=None)
    with pytest.raises(access.UnsupportedProfile):
        access._evaluate(reader, "P1", "update")


def test_missing_sharing_setting_or_nonbinary_strict_denies(monkeypatch):
    _patch_profile(monkeypatch)
    monkeypatch.setattr(access.frappe.session, "user", "manager@example.test")
    with pytest.raises(access.UnsupportedProfile):
        access._evaluate(_EvalReader(sharing=None), "P1", "update")
    with pytest.raises(access.UnsupportedProfile):
        access._evaluate(_EvalReader(strict="2"), "P1", "update")


def test_ordinary_positive_path_requires_settings_and_verifies_storage(monkeypatch):
    _patch_profile(monkeypatch)
    monkeypatch.setattr(access.frappe.session, "user", "manager@example.test")
    reader = _EvalReader()
    decision = access._evaluate(reader, "P1", "update")
    assert decision["allowed"] is True
    assert reader.engine_checked is True


# ---------------------------------------------------------------------------
# SCP-016: transactional storage for every queried authority table
# ---------------------------------------------------------------------------


class _EngineCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows


def test_queried_tables_are_recorded_from_sql():
    reader = access.FreshAuthorityReader()
    reader._cursor = _EngineCursor([])
    reader.query("SELECT name FROM tabProject WHERE name=%s", ("P1",))
    reader.query("SELECT * FROM `tabExecution Breakdown Node` WHERE project=%s", ("P1",))
    reader.query("SELECT field, value FROM tabSingles WHERE doctype=%s", ("System Settings",))
    reader.query("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME=%s", ("tabProject",))
    assert reader._queried_tables == {"Project", "Execution Breakdown Node", "Singles"}


def test_nontransactional_or_missing_queried_table_denies():
    reader = access.FreshAuthorityReader()
    reader._queried_tables = {"Project", "DocShare"}
    reader._cursor = _EngineCursor(
        [{"TABLE_NAME": "tabProject", "ENGINE": "InnoDB"}, {"TABLE_NAME": "tabDocShare", "ENGINE": "MyISAM"}]
    )
    with pytest.raises(access.UnsupportedProfile):
        reader.verify_storage_engines()
    reader._cursor = _EngineCursor([{"TABLE_NAME": "tabProject", "ENGINE": "InnoDB"}])
    with pytest.raises(access.UnsupportedProfile):
        reader.verify_storage_engines()
    reader._cursor = _EngineCursor(
        [{"TABLE_NAME": "tabProject", "ENGINE": "InnoDB"}, {"TABLE_NAME": "tabDocShare", "ENGINE": "InnoDB"}]
    )
    assert reader.verify_storage_engines() is True


# ---------------------------------------------------------------------------
# SCP-008: closed field-transition capabilities
# ---------------------------------------------------------------------------


def test_guard_transition_rejects_omitted_changed_fields():
    doc = _GuardDoc(
        project="P1",
        name="EBN-1",
        title="old",
        parent_node="EBN-0",
        is_group=0,
        disabled=0,
        company="A",
        ebs_code="EBS-0001",
    )
    with access.establish_guard(
        actor="offline@example.test",
        operation="update",
        project="P1",
        doctype=rules.NODE_DOCTYPE,
        document=doc,
        name="EBN-1",
        targets={"title": "new"},
    ) as guard:
        access.require_guard_transition(guard, document=doc, field="title", value="new")
        with pytest.raises(access.frappe.PermissionError):
            access.require_guard_transition(guard, document=doc, field="title", value="other")
        # The finding's reproduction: parent_node omitted from targets but
        # changed to another valid same-Project group must deny.
        with pytest.raises(access.frappe.PermissionError):
            access.require_guard_transition(guard, document=doc, field="parent_node", value="EBN-9")
        access.require_guard_transition(guard, document=doc, field="parent_node", value="EBN-0")
        access.require_guard_transition(guard, document=doc, field="disabled", value=0)
        with pytest.raises(access.frappe.PermissionError):
            access.require_guard_transition(guard, document=doc, field="disabled", value=1)
        with pytest.raises(access.frappe.PermissionError):
            access.require_guard_transition(guard, document=doc, field="unknown_field", value=1)


def test_create_guard_binds_every_transition_field():
    doc = _GuardDoc(
        project="P1",
        title="t",
        parent_node=None,
        is_group=0,
        disabled=0,
        company="A",
        ebs_code="EBS-0001",
    )
    with access.establish_guard(
        actor="offline@example.test",
        operation="create",
        project="P1",
        doctype=rules.NODE_DOCTYPE,
        document=doc,
        company="A",
        code="EBS-0001",
        targets={
            "company": "A",
            "ebs_code": "EBS-0001",
            "title": "t",
            "parent_node": None,
            "is_group": 0,
            "disabled": 0,
        },
    ) as guard:
        access.require_guard_transition(guard, document=doc, field="disabled", value=0)
        with pytest.raises(access.frappe.PermissionError):
            access.require_guard_transition(guard, document=doc, field="disabled", value=1)


# ---------------------------------------------------------------------------
# SCP-002: doc_events and materialized dispatch-map comparison
# ---------------------------------------------------------------------------


def _dispatch_events():
    return {
        "frappe": {},
        "erpnext": {"*": {"validate": ["erpnext.handler"]}},
        "construction": {
            "*": {"validate": ["construction.overrides.scope_enforcement.validate"]},
            "Project": {
                "before_rename": ["construction.services.execution_tree.project_before_rename"],
                "on_trash": ["construction.services.execution_tree.project_on_trash"],
            },
            "DocShare": {"validate": ["construction.services.execution_tree_access.reject_protected_share"]},
        },
    }


def test_dispatch_map_matches_bound_source(monkeypatch):
    events = _dispatch_events()
    expected = rules.merge_doc_events([events[app] for app in ("frappe", "erpnext", "construction")])
    monkeypatch.setattr(access.frappe, "get_doc_hooks", lambda: dict(expected), raising=False)
    access._assert_dispatch_map_match(["frappe", "erpnext", "construction"], events)


def test_stale_dispatch_map_denies(monkeypatch):
    events = _dispatch_events()
    expected = rules.merge_doc_events([events[app] for app in ("frappe", "erpnext", "construction")])
    stale = {key: dict(value) for key, value in expected.items()}
    stale["Project"] = {"on_trash": stale["Project"]["on_trash"]}
    monkeypatch.setattr(access.frappe, "get_doc_hooks", lambda: stale, raising=False)
    with pytest.raises(access.UnsupportedProfile):
        access._assert_dispatch_map_match(["frappe", "erpnext", "construction"], events)
    extra = {key: dict(value) for key, value in expected.items()}
    extra["DocShare"] = {"validate": expected["DocShare"]["validate"] + ["unknown.handler"]}
    monkeypatch.setattr(access.frappe, "get_doc_hooks", lambda: extra, raising=False)
    with pytest.raises(access.UnsupportedProfile):
        access._assert_dispatch_map_match(["frappe", "erpnext", "construction"], events)


def test_uninspectable_dispatch_map_denies(monkeypatch):
    def _broken():
        raise RuntimeError("no dispatch map")

    monkeypatch.setattr(access.frappe, "get_doc_hooks", _broken, raising=False)
    with pytest.raises(access.UnsupportedProfile):
        access._assert_dispatch_map_match(["construction"], {"construction": {}})


def test_loaded_construction_doc_events_must_match_projection(monkeypatch):
    projections = {
        "construction": {
            "has_permission": {},
            "permission_query_conditions": {},
            "override_doctype_class": {},
            "extend_doctype_class": {},
            "get_child_provider": {},
            "doc_events": {"Project": {"validate": ["a"]}},
        }
    }
    loaded = {
        "has_permission": {},
        "permission_query_conditions": {},
        "override_doctype_class": {},
        "extend_doctype_class": {},
        "get_child_provider": {},
        "doc_events": {"Project": {"validate": ["a"]}},
    }
    monkeypatch.setattr(
        access.frappe, "get_hooks", lambda hook, app_name=None: loaded.get(hook, []), raising=False
    )
    access._assert_loaded_hooks_match(["construction"], projections, {"construction": {}})
    loaded["doc_events"] = {"Project": {"validate": ["b"]}}
    with pytest.raises(access.UnsupportedProfile):
        access._assert_loaded_hooks_match(["construction"], projections, {"construction": {}})


def test_pinned_anchors_match_the_reviewed_source_packet():
    import re

    packet = (ROOT / "docs" / "ai" / "work-items" / "WBS" / "12_P1_PINNED_FRAMEWORK_SOURCE.md").read_text(
        encoding="utf-8"
    )
    controller_anchor = re.search(
        r"## erpnext/projects/doctype/project/project\.py\n\nFull blob SHA-256 `([0-9a-f]{64})`", packet
    )
    assert controller_anchor
    assert access.PINNED_CONTROLLER_SOURCES["erpnext.projects.doctype.project.project"][
        1
    ] == controller_anchor.group(1)

    def json_block(header):
        index = packet.index(header)
        match = re.search(r"```json\n(.*?)\n```", packet[index:], re.S)
        return json.loads(match.group(1))

    for header, pinned in (
        ("## erpnext/projects/doctype/project/project.json", rules.PINNED_STOCK_PROJECT_FIELDS),
        (
            "## erpnext/projects/doctype/project_user/project_user.json",
            rules.PINNED_STOCK_PROJECT_USER_FIELDS,
        ),
    ):
        definition = json_block(header)
        fields = {field["fieldname"]: field for field in definition["fields"]}
        expected = tuple(
            (
                name,
                fields[name]["fieldtype"],
                fields[name].get("options") or None,
                int(fields[name].get("permlevel", 0)),
                int(fields[name].get("ignore_user_permissions", 0)),
                int(fields[name].get("hidden", 0)),
                int(fields[name].get("reqd", 0)),
                int(fields[name].get("read_only", 0)),
                int(fields[name].get("is_virtual", 0)),
            )
            for name in definition["field_order"]
        )
        assert pinned == expected


# ---------------------------------------------------------------------------
# SCP-009 / SCP-012: locking reads and MariaDB clause order (isolated service)
# ---------------------------------------------------------------------------


def _load_service_module():
    if "execution_tree_under_test" in sys.modules:
        return sys.modules["execution_tree_under_test"]
    path = ROOT / "construction" / "services" / "execution_tree.py"
    spec = importlib.util.spec_from_file_location("execution_tree_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with _framework_stubs() as frappe_stub:
        if not hasattr(frappe_stub, "db"):
            frappe_stub.db = types.SimpleNamespace(sql=lambda *a, **k: [], table_exists=lambda dt: True)
        if not hasattr(frappe_stub, "get_doc"):
            frappe_stub.get_doc = lambda *a, **k: None
        spec.loader.exec_module(module)
    sys.modules["execution_tree_under_test"] = module
    return module


service = _load_service_module()

NODE_ROW = {
    "name": "EBN-1",
    "title": "old",
    "project": "P1",
    "company": "A",
    "parent_node": None,
    "is_group": 0,
    "disabled": 0,
    "ebs_code": "EBS-0001",
    "modified": "2026-11-18 00:00:00.000000",
}
PROJECT_ROW = {"name": "P1", "company": "A", "cost_center": None, "owner": "o", "modified": "m"}


class _FakeDB:
    def __init__(self, node_rows=None, counter_rows=None):
        self.calls = []
        self.node_rows = [dict(NODE_ROW)] if node_rows is None else node_rows
        self.counter_rows = [] if counter_rows is None else counter_rows

    def table_exists(self, doctype):
        return True

    def sql(self, sql, params=None, as_dict=False):
        self.calls.append((sql, params))
        if "FROM tabProject" in sql:
            return [dict(PROJECT_ROW)]
        if "tabExecution Code Counter" in sql:
            return [dict(row) for row in self.counter_rows]
        if "tabExecution Breakdown Node" in sql:
            if "AND name=%s" in sql:
                return [dict(row) for row in self.node_rows if row["name"] == params[1]]
            return [dict(row) for row in self.node_rows]
        return []


class _FakeDoc:
    def __init__(self, values):
        self._values = dict(values)
        self.saved = False
        for key, value in values.items():
            setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def save(self, ignore_permissions=False):
        self.saved = True

    def as_dict(self):
        return {key: getattr(self, key) for key in self._values}


def test_locked_tree_query_uses_mariadb_clause_order(monkeypatch):
    db = _FakeDB(node_rows=[])
    monkeypatch.setattr(access.frappe, "db", db, raising=False)
    service._locked_nodes("P1")
    sql = db.calls[0][0]
    assert "LIMIT %s FOR UPDATE" in sql
    assert "FOR UPDATE LIMIT" not in sql
    assert sql.index("LIMIT") < sql.index("FOR UPDATE")


def test_counter_and_node_reads_are_locking(monkeypatch):
    db = _FakeDB(counter_rows=[{"name": "P1", "project": "P1", "last_issued": 3}])
    monkeypatch.setattr(access.frappe, "db", db, raising=False)
    counter = service._load_counter("P1", create_if_missing=False)
    assert counter["last_issued"] == 3
    service._load_node("P1", "EBN-1")
    service._locked_counter("P1")
    service._has_nodes("P1")
    for sql, _params in db.calls:
        if sql.startswith("SELECT"):
            assert "FOR UPDATE" in sql
            assert "FOR UPDATE LIMIT" not in sql


def test_update_loads_document_with_current_locking_read(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(access.frappe, "db", db, raising=False)
    decision = {"project": "P1", "company": "A", "cost_center": None, "allowed": True, "actions": {}}
    monkeypatch.setattr(access, "authorize", lambda project, operation, payload_reader=None: (decision, None))
    loaded = []

    def _get_doc(doctype, name=None, for_update=None, **kwargs):
        loaded.append((doctype, name, for_update))
        return _FakeDoc(NODE_ROW)

    monkeypatch.setattr(access.frappe, "get_doc", _get_doc, raising=False)
    summary = service.update_node("P1", "EBN-1", NODE_ROW["modified"], title="New")
    assert summary["title"] == "New"
    assert loaded == [(rules.NODE_DOCTYPE, "EBN-1", True)]
    for sql, _params in db.calls:
        if "tabExecution Breakdown Node" in sql:
            assert "FOR UPDATE" in sql


def test_allocation_loads_counter_with_current_locking_read(monkeypatch):
    db = _FakeDB(counter_rows=[{"name": "P1", "project": "P1", "last_issued": 0}])
    monkeypatch.setattr(access.frappe, "db", db, raising=False)
    loaded = []
    counter_doc = _FakeDoc({"name": "P1", "project": "P1", "last_issued": 0})

    def _get_doc(doctype, name=None, for_update=None, **kwargs):
        loaded.append((doctype, name, for_update))
        return counter_doc

    monkeypatch.setattr(access.frappe, "get_doc", _get_doc, raising=False)
    code = service._allocate_code("P1")
    assert code == "EBS-0001"
    assert loaded == [(rules.COUNTER_DOCTYPE, "P1", True)]
    assert counter_doc.last_issued == 1
    assert counter_doc.saved is True


def test_node_controller_child_check_is_locking(monkeypatch):
    frappe_model = types.ModuleType("frappe.model")
    frappe_model.__path__ = []
    document_module = types.ModuleType("frappe.model.document")
    document_module.Document = object
    monkeypatch.setitem(sys.modules, "frappe.model", frappe_model)
    monkeypatch.setitem(sys.modules, "frappe.model.document", document_module)
    path = (
        ROOT
        / "construction"
        / "construction"
        / "doctype"
        / "execution_breakdown_node"
        / "execution_breakdown_node.py"
    )
    spec = importlib.util.spec_from_file_location("execution_breakdown_node_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with _framework_stubs():
        spec.loader.exec_module(module)
    node = object.__new__(module.ExecutionBreakdownNode)
    node.name = "EBN-1"
    node.project = "P1"
    db = _FakeDB(node_rows=[dict(NODE_ROW, name="EBN-2", parent_node="EBN-1")])
    monkeypatch.setattr(access.frappe, "db", db, raising=False)
    with access.establish_guard(
        actor=access.frappe.session.user,
        operation="delete",
        project="P1",
        doctype=rules.NODE_DOCTYPE,
        document=node,
        name="EBN-1",
    ):
        with pytest.raises(access.frappe.ValidationError):
            node.on_trash()
    child_sql = [sql for sql, _params in db.calls if "parent_node=%s" in sql]
    assert child_sql and all("FOR UPDATE" in sql for sql in child_sql)
    db.calls.clear()
    db.node_rows = []
    with access.establish_guard(
        actor=access.frappe.session.user,
        operation="delete",
        project="P1",
        doctype=rules.NODE_DOCTYPE,
        document=node,
        name="EBN-1",
    ):
        node.on_trash()


# ---------------------------------------------------------------------------
# SCP-010: preflight refuses incompatible same-module definitions
# ---------------------------------------------------------------------------


def _candidate_json(doctype):
    folder = {
        rules.NODE_DOCTYPE: "execution_breakdown_node",
        rules.COUNTER_DOCTYPE: "execution_code_counter",
    }[doctype]
    path = ROOT / "construction" / "construction" / "doctype" / folder / f"{folder}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _existing_definition_rows(doctype, *, mutate=None):
    candidate = _candidate_json(doctype)
    meta = {
        "name": doctype,
        "module": "construction",
        "custom": 0,
        "istable": 0,
        "issingle": 0,
        "is_tree": 0,
        "is_virtual": 0,
    }
    fields = {field["fieldname"]: field for field in candidate["fields"]}
    rows = []
    for name in candidate["field_order"]:
        field = fields[name]
        rows.append(
            {
                "fieldname": name,
                "fieldtype": field.get("fieldtype"),
                "options": field.get("options"),
                "permlevel": field.get("permlevel", 0),
                "ignore_user_permissions": field.get("ignore_user_permissions", 0),
                "hidden": field.get("hidden", 0),
                "reqd": field.get("reqd", 0),
                "read_only": field.get("read_only", 0),
                "is_virtual": field.get("is_virtual", 0),
            }
        )
    if mutate:
        mutate(meta, rows)
    return meta, rows


def _preflight_reader(definitions):
    def one(sql, params=None):
        if "information_schema.TABLES" in sql:
            return {"total": 1}
        if "COUNT(*)" in sql:
            return {"total": 0}
        return None

    def query(sql, params=None):
        meta, rows = definitions[params[0]]
        if "FROM tabDocType" in sql:
            return [dict(meta)]
        if "tabDocField" in sql:
            return [dict(row) for row in rows]
        return []

    reader = FakeReader(one=one, query=query)
    reader.verify_storage_engines = lambda: True
    return reader


def _compatible_definitions():
    return {doctype: _existing_definition_rows(doctype) for doctype in rules.PROTECTED_DOCTYPES}


@contextlib.contextmanager
def _schema_stub():
    setup_package = types.ModuleType("construction.setup")
    setup_package.__path__ = []
    schema_module = types.ModuleType("construction.setup.execution_tree_schema")
    schema_module.candidate_protected_definition = _candidate_json
    with _framework_stubs():
        sys.modules["construction.setup"] = setup_package
        sys.modules["construction.setup.execution_tree_schema"] = schema_module
        yield


def test_preflight_accepts_compatible_earlier_wbs_objects():
    with _schema_stub():
        assert access.preflight_conflicts(_preflight_reader(_compatible_definitions())) is True


def test_preflight_refuses_incompatible_same_module_fields():
    def _mutate(meta, rows):
        for row in rows:
            if row["fieldname"] == "ebs_code":
                row["fieldtype"] = "Int"

    definitions = _compatible_definitions()
    definitions[rules.NODE_DOCTYPE] = _existing_definition_rows(rules.NODE_DOCTYPE, mutate=_mutate)
    with _schema_stub():
        with pytest.raises(access.IntegrityFailure):
            access.preflight_conflicts(_preflight_reader(definitions))


def test_preflight_refuses_unrelated_owner_and_identity():
    definitions = _compatible_definitions()
    definitions[rules.NODE_DOCTYPE][0]["module"] = "other_app"
    with _schema_stub():
        with pytest.raises(access.IntegrityFailure):
            access.preflight_conflicts(_preflight_reader(definitions))
    definitions = _compatible_definitions()
    definitions[rules.NODE_DOCTYPE][0]["istable"] = 1
    with _schema_stub():
        with pytest.raises(access.IntegrityFailure):
            access.preflight_conflicts(_preflight_reader(definitions))


def test_schema_preflight_compares_definitions(monkeypatch):
    frappe_stub = _ensure_frappe_stub()
    meta, rows = _existing_definition_rows(rules.NODE_DOCTYPE)

    def _mutate(meta, rows):
        for row in rows:
            if row["fieldname"] == "last_issued" or row["fieldname"] == "ebs_code":
                row["fieldtype"] = "Int"

    bad_meta, bad_rows = _existing_definition_rows(rules.NODE_DOCTYPE, mutate=_mutate)

    class _SchemaDB:
        def __init__(self, meta, rows):
            self.meta = meta
            self.rows = rows

        def table_exists(self, doctype):
            return True

        def get_all(self, doctype, filters=None, fields=None, order_by=None, limit_page_length=None):
            if doctype == "DocType":
                return [dict(self.meta)] if filters.get("name") == self.meta["name"] else []
            if doctype == "DocField":
                return [dict(row) for row in self.rows]
            return []

    monkeypatch.setattr(frappe_stub, "db", _SchemaDB(bad_meta, bad_rows), raising=False)
    monkeypatch.setattr(frappe_stub, "get_app_path", lambda app: str(ROOT / "construction"), raising=False)
    path = ROOT / "construction" / "setup" / "execution_tree_schema.py"
    spec = importlib.util.spec_from_file_location("execution_tree_schema_under_test", path)
    schema = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with _framework_stubs():
        spec.loader.exec_module(schema)
    with pytest.raises(schema.SchemaConflict):
        schema._preflight_docTypes()
    monkeypatch.setattr(frappe_stub, "db", _SchemaDB(meta, rows), raising=False)
    schema._preflight_docTypes()


# ---------------------------------------------------------------------------
# SCP-015: transport binding expectations and counter-aware state assertions
# ---------------------------------------------------------------------------


def _load_transport_module():
    if "execution_tree_transport_under_test" in sys.modules:
        return sys.modules["execution_tree_transport_under_test"]
    path = ROOT / "construction" / "tests" / "execution_tree_transport.py"
    spec = importlib.util.spec_from_file_location("execution_tree_transport_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules["execution_tree_transport_under_test"] = module
    return module


transport = _load_transport_module()


def test_authorization_reader_requests_read_only_session(monkeypatch):
    """MariaDB ignores the START TRANSACTION READ ONLY flag in @@tx_read_only."""

    MySQLdb = pytest.importorskip("MySQLdb")
    statements = []

    class FakeCursor:
        _row = None

        def execute(self, sql, params=None):
            statements.append(sql)
            if sql.startswith("START TRANSACTION"):
                self._row = {
                    "isolation": "REPEATABLE-READ",
                    "read_only": 1 if "SET SESSION tx_read_only = 1" in statements else 0,
                }

        def fetchone(self):
            return self._row

        def close(self):
            pass

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def rollback(self):
            pass

        def close(self):
            pass

    with _framework_stubs():
        frappe_stub = sys.modules["frappe"]
        monkeypatch.setattr(
            frappe_stub,
            "local",
            types.SimpleNamespace(
                db=types.SimpleNamespace(
                    get_connection_settings=lambda: {"user": "u", "passwd": "p", "db": "d"}
                )
            ),
            raising=False,
        )
        monkeypatch.setattr(MySQLdb, "connect", lambda **kwargs: FakeConnection())
        reader = access.FreshAuthorityReader()
        reader.__enter__()
        try:
            assert statements[0] == "SET SESSION tx_read_only = 1"
            assert statements[-2] == "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY"
            assert statements[-1] == "SELECT @@tx_isolation AS isolation, @@tx_read_only AS read_only"
        finally:
            reader.close()


def test_authorization_reader_rejects_a_writable_transaction():
    class Cursor:
        def __init__(self, read_only):
            self.read_only = read_only

        def execute(self, sql):
            self.sql = sql

        def fetchone(self):
            return {"isolation": "REPEATABLE-READ", "read_only": self.read_only}

    reader = access.FreshAuthorityReader()
    reader._cursor = Cursor(0)
    with pytest.raises(access.UnsupportedProfile, match="not read-only"):
        reader._verify_transaction()
    reader._cursor = Cursor(1)
    assert reader._verify_transaction() is None


def test_installed_mysqlclient_source_matches_reviewed_reconnect_facts():
    # Pin the installed driver source the reader's reconnect claims rest on.
    # A different version or changed source must be re-inspected before use.
    MySQLdb = pytest.importorskip("MySQLdb")
    import MySQLdb.release

    assert MySQLdb.release.version_info[:3] == access.PINNED_MYSQLDB_VERSION
    driver_dir = Path(MySQLdb.__file__).parent
    c_path = driver_dir / "_mysql.c"
    if not c_path.is_file():
        pytest.fail("installed mysqlclient C source is unavailable for re-inspection")
    c_source = c_path.read_text(encoding="utf-8", errors="replace")
    # No auto_reconnect setting exists anywhere in the driver.
    assert "auto_reconnect" not in c_source
    for module_file in ("connections.py", "cursors.py"):
        assert "auto_reconnect" not in (driver_dir / module_file).read_text(encoding="utf-8", errors="replace")
    # Reconnect is a client-library option controlled only through ping().
    assert "mysql_options(&self->connection, MYSQL_OPT_RECONNECT" in c_source
    assert "self->reconnect = false;" in c_source
    # The C connection type exposes no reconnect state to Python.
    memberlist = c_source[c_source.index("_mysql_ConnectionObject_memberlist") :]
    memberlist = memberlist[: memberlist.index("_mysql_ResultObject_memberlist")]
    assert "reconnect" not in memberlist


def test_ping_guard_binds_to_real_mysqlclient_connection_type():
    # Never connected; the guard must bind to the same class MySQLdb.connect
    # returns, and refuse the reconnect path with either argument form.
    MySQLdb = pytest.importorskip("MySQLdb")
    from MySQLdb.connections import Connection as RealConnection

    conn = RealConnection.__new__(RealConnection)
    access._disable_reconnect(conn)
    assert conn.ping is access._refuse_ping
    with pytest.raises(access.UnsupportedProfile, match="econnect attempt refused"):
        conn.ping()
    with pytest.raises(access.UnsupportedProfile, match="econnect attempt refused"):
        conn.ping(reconnect=True)


def test_api_accepts_framework_arguments_and_rejects_caller_extras():
    """Frappe passes ``cmd`` into every call; it must not be treated as payload."""

    with _framework_stubs() as frappe_stub:
        service_stub = types.ModuleType("construction.services.execution_tree")
        service_stub.get_tree = lambda project: {"project": project}
        frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn)
        sys.modules["construction.services.execution_tree"] = service_stub
        sys.modules["construction.services"].execution_tree = service_stub
        try:
            path = ROOT / "construction" / "api" / "execution_tree_api.py"
            spec = importlib.util.spec_from_file_location("execution_tree_api_under_test", path)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            assert module.get_tree(project="P1", cmd="route", _="123") == {"project": "P1"}
            with pytest.raises(frappe_stub.ValidationError, match="Unknown request argument"):
                module.get_tree(project="P1", bogus="x")
        finally:
            sys.modules.pop("construction.services.execution_tree", None)


def test_worker_database_connection_must_be_open(tmp_path):
    proc = tmp_path / "proc"
    (proc / "101" / "net").mkdir(parents=True)
    (proc / "101" / "net" / "unix").write_text(
        "Num RefCount Protocol Flags Type St Inode Path\n"
        "0: 00000002 00000000 00010000 0001 01 500 /run/mysqld/mysqld.sock\n"
    )
    (proc / "101" / "fd").mkdir()
    (proc / "101" / "fd" / "9").symlink_to("socket:[500]")
    workers = [{"pid": 101}]
    assert transport._verify_worker_database_connections(proc, workers, "/run/mysqld/mysqld.sock") == {
        "database_connections_checked": 1
    }

    (proc / "101" / "fd" / "9").unlink()
    with pytest.raises(transport.BindingError, match="not open"):
        transport._verify_worker_database_connections(proc, workers, "/run/mysqld/mysqld.sock")

    (proc / "101" / "fd" / "9").symlink_to("socket:[500]")
    with pytest.raises(transport.BindingError, match="no socket"):
        transport._verify_worker_database_connections(proc, workers, "/run/other.sock")
    with pytest.raises(transport.BindingError, match="database socket path"):
        transport._verify_worker_database_connections(proc, workers, "relative.sock")


def test_endpoints_pass_coerced_booleans_to_services():
    """Form-encoded booleans must reach the service as booleans."""

    with _framework_stubs() as frappe_stub:
        calls = {}
        parameters = {
            "get_tree": ("project",),
            "create_node": ("project", "title", "is_group", "parent_node", "expected_parent_modified"),
            "update_node": ("project", "name", "expected_modified", "title", "is_group"),
            "move_node": ("project", "name", "expected_modified", "parent_node", "expected_parent_modified"),
            "set_disabled": ("project", "name", "expected_modified", "disabled"),
            "delete_node": ("project", "name", "expected_modified"),
        }

        def record(name):
            def callable_(*args, **kwargs):
                calls[name] = dict(zip(parameters[name], args, strict=False)) | kwargs
                return {"ok": True}

            return callable_

        service_stub = types.ModuleType("construction.services.execution_tree")
        for name in ("get_tree", "create_node", "update_node", "move_node", "set_disabled", "delete_node"):
            setattr(service_stub, name, record(name))
        frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn)
        sys.modules["construction.services.execution_tree"] = service_stub
        sys.modules["construction.services"].execution_tree = service_stub
        try:
            path = ROOT / "construction" / "api" / "execution_tree_api.py"
            spec = importlib.util.spec_from_file_location("execution_tree_api_endpoints_under_test", path)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)

            module.create_node(project="P", title="t", is_group="true")
            assert calls["create_node"]["is_group"] is True
            module.create_node(project="P", title="t", is_group="0")
            assert calls["create_node"]["is_group"] is False

            module.update_node(project="P", name="N", expected_modified="x", title="t", is_group="false")
            assert calls["update_node"]["is_group"] is False

            module.move_node(project="P", name="N", expected_modified="x")
            assert calls["move_node"]["name"] == "N"

            module.set_disabled(project="P", name="N", expected_modified="x", disabled="on")
            assert calls["set_disabled"]["disabled"] is True

            module.delete_node(project="P", name="N", expected_modified="x")
            assert calls["delete_node"]["project"] == "P"

            assert module._prepare({"is_group": "maybe"})["is_group"] == "maybe"
        finally:
            sys.modules.pop("construction.services.execution_tree", None)


def test_named_guard_accepts_the_reloaded_saved_document():
    """frappe.delete_doc reloads the document before on_trash."""

    class Doc:
        doctype = "Execution Breakdown Node"

        def __init__(self, name, project):
            self._values = {"name": name, "project": project}

        def get(self, key):
            return self._values.get(key)

    with _framework_stubs() as frappe_stub:
        original = Doc("EBN-1", "P1")
        with access.establish_guard(
            actor=frappe_stub.session.user,
            operation="delete",
            project="P1",
            doctype=Doc.doctype,
            document=original,
            name="EBN-1",
        ):
            reloaded = Doc("EBN-1", "P1")
            assert (
                access.require_guard(Doc.doctype, "delete", "P1", "EBN-1", document=reloaded)["name"]
                == "EBN-1"
            )
            for wrong in (Doc("EBN-2", "P1"), Doc("EBN-1", "P2")):
                with pytest.raises(frappe_stub.PermissionError):
                    access.require_guard(Doc.doctype, "delete", "P1", "EBN-1", document=wrong)


def test_guard_reload_exception_is_limited_to_delete():
    """Only on_trash reloads the document; other operations need the exact object."""

    class Doc:
        doctype = "Execution Breakdown Node"

        def __init__(self, name, project):
            self._values = {"name": name, "project": project}

        def get(self, key):
            return self._values.get(key)

    with _framework_stubs() as frappe_stub:
        actor = frappe_stub.session.user
        original = Doc("EBN-1", "P1")
        for operation in ("update", "move", "set_disabled"):
            with access.establish_guard(
                actor=actor,
                operation=operation,
                project="P1",
                doctype=Doc.doctype,
                document=original,
                name="EBN-1",
            ):
                with pytest.raises(frappe_stub.PermissionError):
                    access.require_guard(Doc.doctype, operation, "P1", "EBN-1", document=Doc("EBN-1", "P1"))
                assert (
                    access.require_guard(Doc.doctype, operation, "P1", "EBN-1", document=original)["name"]
                    == "EBN-1"
                )


def test_nested_guard_is_refused():
    class Doc:
        doctype = "Execution Breakdown Node"

        def __init__(self):
            self._values = {"name": "EBN-1", "project": "P1"}

        def get(self, key):
            return self._values.get(key)

    with _framework_stubs() as frappe_stub:
        doc = Doc()
        with access.establish_guard(
            actor=frappe_stub.session.user,
            operation="update",
            project="P1",
            doctype=Doc.doctype,
            document=doc,
            name="EBN-1",
        ):
            with pytest.raises(access.IntegrityFailure):
                with access.establish_guard(
                    actor=frappe_stub.session.user,
                    operation="update",
                    project="P1",
                    doctype=Doc.doctype,
                    document=doc,
                    name="EBN-1",
                ):
                    pass


def test_serving_seal_compares_container_constants_by_value():
    """Set and dict iteration order must not make the seal flaky."""

    assert access._same_constant(frozenset({"a", "b"}), frozenset({"b", "a"}), "") is True
    assert access._same_constant({"a": 1, "b": 2}, {"b": 2, "a": 1}, "") is True
    assert access._same_constant((1, "x"), (1, "y"), "") is False
    assert access._same_constant(frozenset({"a"}), {"a"}, "") is False
    # Python-equal but differently typed values must not be conflated.
    assert access._same_constant({1}, {True}, "") is False
    assert access._same_constant({1: "x"}, {True: "x"}, "") is False
    assert access._same_constant([1], [True], "") is False
    assert access._same_constant({"a": 1}, {"a": True}, "") is False
    set_a = compile("def f():\n    return {'alpha', 'beta'}\n", "<a>", "exec")
    set_b = compile("def f():\n    return {'alpha', 'beta'}\n", "<a>", "exec")
    fa = next(c for c in set_a.co_consts if isinstance(c, types.CodeType))
    fb = next(c for c in set_b.co_consts if isinstance(c, types.CodeType))
    assert access._compare_code(fa, fb) is None


def test_native_suite_fails_before_fixture_setup_without_lab_binding(monkeypatch):
    frappe_tests = types.ModuleType("frappe.tests")
    frappe_tests.__path__ = []
    frappe_test_utils = types.ModuleType("frappe.tests.utils")

    class FakeTestCase:
        @classmethod
        def setUpClass(cls):
            pytest.fail("base fixture setup must not run")

    frappe_test_utils.FrappeTestCase = FakeTestCase
    with _framework_stubs() as frappe_stub:
        monkeypatch.setitem(sys.modules, "frappe.tests", frappe_tests)
        monkeypatch.setitem(sys.modules, "frappe.tests.utils", frappe_test_utils)
        monkeypatch.setitem(
            sys.modules, "construction.services.execution_tree", types.ModuleType("execution_tree")
        )
        path = ROOT / "construction" / "tests" / "test_execution_tree.py"
        spec = importlib.util.spec_from_file_location("native_execution_tree_under_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with pytest.raises(RuntimeError, match="native suite disabled"):
            module.ExecutionTreeTestCase.setUpClass()
        committed = threading.Event()
        order = []
        monkeypatch.setattr(frappe_stub, "init", lambda **kw: order.append(("init", kw)), raising=False)
        monkeypatch.setattr(frappe_stub, "connect", lambda: order.append(("connect", None)), raising=False)
        monkeypatch.setattr(frappe_stub, "set_user", lambda user: order.append(("user", user)), raising=False)
        monkeypatch.setattr(frappe_stub, "destroy", lambda: order.append(("destroy", None)), raising=False)

        def commit():
            assert not committed.is_set()
            order.append(("commit", None))

        monkeypatch.setattr(
            frappe_stub, "db", types.SimpleNamespace(commit=commit, rollback=lambda: None), raising=False
        )
        subject = module.ExecutionTreeTestCase()
        subject.manager = "fixture-manager"
        results = {}
        subject._race_worker(lambda: "done", results, "job", "fixture.site", "/fixture/sites", committed)
        assert committed.is_set() and results["job"] == "done"
        assert order[0] == ("init", {"site": "fixture.site", "sites_path": "/fixture/sites"})
        assert [item[0] for item in order] == ["init", "connect", "user", "commit", "destroy"]


def _binding_dict():
    return {
        "bench_root": "/lab/bench",
        "sites_path": "/lab/bench/sites",
        "app_root": "/lab/bench/apps/construction",
        "site": "wbs-p1-fixture.localhost",
        "http_endpoint": "http://127.0.0.1:8000",
        "db_name": "lab_db",
        "db_socket": "/run/mysqld/mysqld.sock",
        "redis_origin": "redis://127.0.0.1:13000",
        "phase": "fixture",
        "evidence_root": "/lab/evidence",
        "project": "P1",
        "other_project": "P2",
        "other_company": "B",
        "candidate_id": "candidate-1",
        "candidate_manifest_path": "/lab/candidate.json",
        "dependency_identities": {"frappe": "f", "erpnext": "e", "construction": "c"},
        "serving_process_identities": ["worker-1", "worker-2"],
        "serving_process_records": [
            {
                "pid": 101,
                "start_ticks": 55,
                "socket_inode": 300,
                "exe": "/lab/bench/env/bin/python",
                "cwd": "/lab/bench",
                "endpoint": "http://127.0.0.1:8001",
            },
            {
                "pid": 102,
                "start_ticks": 56,
                "socket_inode": 301,
                "exe": "/lab/bench/env/bin/python",
                "cwd": "/lab/bench",
                "endpoint": "http://127.0.0.1:8002",
            },
        ],
        "fixtures": {alias: f"{alias}@example.test" for alias in transport.ALLOWED_FIXTURES},
        "credentials_env": "WBS_LAB_PASSWORD",
        "expected_manifest_path": "/lab/expected.json",
    }


def test_expected_manifest_binds_site_origin_roots_and_phase(tmp_path):
    binding = _binding_dict()
    manifest = tmp_path / "expected.json"
    manifest.write_text(json.dumps({key: binding[key] for key in transport.EXPECTED_IDENTITY_KEYS}))
    binding["expected_manifest_path"] = str(manifest)
    transport._verify_expected_manifest(binding)
    for key in (
        "site",
        "http_endpoint",
        "bench_root",
        "sites_path",
        "app_root",
        "db_name",
        "db_socket",
        "redis_origin",
        "phase",
    ):
        altered = dict(binding)
        altered[key] = altered[key] + "-wrong"
        with pytest.raises(transport.BindingError):
            transport._verify_expected_manifest(altered)
    incomplete = {key: binding[key] for key in transport.EXPECTED_IDENTITY_KEYS if key != "phase"}
    manifest.write_text(json.dumps(incomplete))
    with pytest.raises(transport.BindingError):
        transport._verify_expected_manifest(binding)


def test_expected_manifest_is_type_strict_for_nested_values(tmp_path):
    binding = _binding_dict()
    binding["serving_process_records"][0]["pid"] = 1
    manifest = {key: binding[key] for key in transport.EXPECTED_IDENTITY_KEYS}
    path = tmp_path / "expected.json"
    path.write_text(json.dumps(manifest))
    binding["expected_manifest_path"] = str(path)
    transport._verify_expected_manifest(binding)

    altered = json.loads(json.dumps(manifest))
    altered["serving_process_records"][0]["pid"] = True
    path.write_text(json.dumps(altered))
    with pytest.raises(transport.BindingError, match="serving_process_records"):
        transport._verify_expected_manifest(binding)

    altered = json.loads(json.dumps(manifest))
    altered["serving_process_records"][0]["endpoint"] = "http://127.0.0.1:9999"
    path.write_text(json.dumps(altered))
    with pytest.raises(transport.BindingError, match="serving_process_records"):
        transport._verify_expected_manifest(binding)


def test_binding_requires_complete_identity_keys():
    binding = _binding_dict()
    del binding["phase"]
    missing = sorted(transport.REQUIRED_BINDING_KEYS - set(binding))
    assert missing == ["phase"]
    assert transport.ALLOWED_PHASES == frozenset({"fresh", "upgrade", "fixture"})


def _candidate_file_fixture(tmp_path):
    root = tmp_path.resolve()
    (root / "app").mkdir()
    path = root / "app" / "file.py"
    path.write_bytes(b"original")
    manifest = {
        "kind": "code",
        "entries": [
            {
                "path": "app/file.py",
                "kind": "file",
                "mode": "100644",
                "content_sha256": hashlib.sha256(b"original").hexdigest(),
            }
        ],
    }
    candidate_id = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return root, path, manifest, candidate_id


def test_candidate_files_match_manifest_and_reject_drift(tmp_path):
    root, path, manifest, candidate_id = _candidate_file_fixture(tmp_path)
    assert transport._verify_candidate_files(root, manifest, candidate_id)["verified_files"] == 1
    path.write_bytes(b"changed")
    with pytest.raises(transport.BindingError, match="content or mode"):
        transport._verify_candidate_files(root, manifest, candidate_id)
    path.write_bytes(b"original")
    path.chmod(0o755)
    with pytest.raises(transport.BindingError, match="content or mode"):
        transport._verify_candidate_files(root, manifest, candidate_id)
    with pytest.raises(transport.BindingError, match="identity"):
        transport._verify_candidate_files(root, manifest, "0" * 64)


def test_candidate_files_reject_escaping_paths_and_symlinks(tmp_path):
    root, path, manifest, candidate_id = _candidate_file_fixture(tmp_path)
    path.unlink()
    path.symlink_to(root / "outside")
    with pytest.raises(transport.BindingError, match="symlink"):
        transport._verify_candidate_files(root, manifest, candidate_id)
    manifest["entries"][0]["path"] = "../outside"
    candidate_id = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    with pytest.raises(transport.BindingError, match="path"):
        transport._verify_candidate_files(root, manifest, candidate_id)


def test_candidate_checkout_checks_base_and_unrelated_changes(tmp_path):
    root = tmp_path.resolve()

    def git(*args):
        return (
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
            .stdout.decode()
            .strip()
        )

    git("init", "-q")
    git("config", "user.email", "fixture@example.test")
    git("config", "user.name", "Fixture")
    (root / "tracked.txt").write_text("base")
    (root / "other.txt").write_text("untouched")
    (root / ".gitignore").write_text("ignored/\n*.pyc\n")
    git("add", "tracked.txt", "other.txt", ".gitignore")
    git("commit", "-q", "-m", "base")
    base = git("rev-parse", "HEAD")
    (root / "tracked.txt").write_text("candidate")
    manifest = {
        "kind": "code",
        "base_commit": base,
        "entries": [
            {
                "path": "tracked.txt",
                "kind": "file",
                "mode": "100644",
                "content_sha256": hashlib.sha256(b"candidate").hexdigest(),
            }
        ],
    }

    def manifest_id():
        return hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()

    assert transport._verify_candidate_checkout(root, manifest, manifest_id())[
        "nonignored_change_set_verified"
    ]
    (root / "ignored").mkdir()
    (root / "ignored" / "plugin.py").write_text("ignored executable")
    with pytest.raises(transport.BindingError, match="Ignored checkout artifacts"):
        transport._verify_candidate_checkout(root, manifest, manifest_id())
    (root / "ignored" / "plugin.py").unlink()
    (root / "ignored").rmdir()
    (root / "stale.pyc").write_bytes(b"ignored cache")
    with pytest.raises(transport.BindingError, match="Ignored checkout artifacts"):
        transport._verify_candidate_checkout(root, manifest, manifest_id())
    (root / "stale.pyc").unlink()
    for flag in ("--assume-unchanged", "--skip-worktree"):
        git("update-index", flag, "other.txt")
        (root / "other.txt").write_text("hidden")
        with pytest.raises(transport.BindingError, match="index entries"):
            transport._verify_candidate_checkout(root, manifest, manifest_id())
        git(
            "update-index",
            "--no-assume-unchanged" if flag == "--assume-unchanged" else "--no-skip-worktree",
            "other.txt",
        )
        (root / "other.txt").write_text("untouched")
    (root / "other.txt").write_text("staged but hidden")
    git("add", "other.txt")
    (root / "other.txt").write_text("untouched")
    with pytest.raises(transport.BindingError, match="Staged changes"):
        transport._verify_candidate_checkout(root, manifest, manifest_id())
    git("reset", "-q", "HEAD", "--", "other.txt")
    (root / "other.txt").write_text("unexpected")
    with pytest.raises(transport.BindingError, match="base file differs"):
        transport._verify_candidate_checkout(root, manifest, manifest_id())
    (root / "other.txt").write_text("untouched")
    (root / "unexpected.py").write_text("extra")
    with pytest.raises(transport.BindingError, match="changes differ"):
        transport._verify_candidate_checkout(root, manifest, manifest_id())
    (root / "unexpected.py").unlink()
    manifest["base_commit"] = "0" * 40
    with pytest.raises(transport.BindingError, match="base HEAD"):
        transport._verify_candidate_checkout(root, manifest, manifest_id())


def _fake_worker(proc_root, pid, start, inode):
    process = proc_root / str(pid)
    (process / "fd").mkdir(parents=True)
    # Linux stat field 22 is index 19 after the comm and state prefix.
    (process / "stat").write_text(
        f"{pid} (fixture worker) " + " ".join(["S"] + ["0"] * 18 + [str(start)]) + "\n"
    )
    (process / "exe").symlink_to("/lab/bench/env/bin/python")
    (process / "cwd").symlink_to("/lab/bench")
    (process / "fd" / "7").symlink_to(f"socket:[{inode}]")
    (process / "net").mkdir()
    db_inode = inode + 1000
    (process / "net" / "unix").write_text(
        "Num RefCount Protocol Flags Type St Inode Path\n"
        f"0: 00000002 00000000 00010000 0001 01 {db_inode} /run/mysqld/mysqld.sock\n"
    )
    (process / "fd" / "10").symlink_to(f"socket:[{db_inode}]")
    return {
        "pid": pid,
        "start_ticks": start,
        "socket_inode": inode,
        "exe": "/lab/bench/env/bin/python",
        "cwd": "/lab/bench",
    }


def test_worker_records_verify_identity_and_socket_without_http(tmp_path):
    workers = [_fake_worker(tmp_path, 101, 55, 300), _fake_worker(tmp_path, 102, 56, 301)]
    assert transport._verify_worker_process_records(tmp_path, workers) == {"process_records_checked": 2}
    stale = [dict(workers[0], start_ticks=54), workers[1]]
    with pytest.raises(transport.BindingError, match="start identity"):
        transport._verify_worker_process_records(tmp_path, stale)
    wrong_socket = [dict(workers[0], socket_inode=999), workers[1]]
    with pytest.raises(transport.BindingError, match="socket descriptor"):
        transport._verify_worker_process_records(tmp_path, wrong_socket)
    with pytest.raises(transport.BindingError, match="Invalid worker identity"):
        transport._verify_worker_process_records(tmp_path, [workers[0], workers[0]])
    wrong_exe = [workers[0], dict(workers[1], exe="/wrong/python")]
    with pytest.raises(transport.BindingError, match="executable or cwd"):
        transport._verify_worker_process_records(tmp_path, wrong_exe)


def _fake_tcp_listener(proc_root, worker, port, *, address="0100007F", state="0A"):
    directory = proc_root / str(worker["pid"]) / "net"
    directory.mkdir(exist_ok=True)
    (directory / "tcp").write_text(
        "  sl local_address remote_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"
        f"  0: {address}:{port:04X} 00000000:0000 {state} 00000000:00000000 00:00000000 00000000 1000 0 {worker['socket_inode']}\n"
    )
    worker["endpoint"] = f"http://127.0.0.1:{port}"


def test_worker_listeners_require_separate_expected_loopback_sockets(tmp_path):
    workers = [_fake_worker(tmp_path, 101, 55, 300), _fake_worker(tmp_path, 102, 56, 301)]
    for process in ("self", "thread-self", "101", "102"):
        directory = tmp_path / process / "ns"
        directory.mkdir(parents=True)
        (directory / "net").symlink_to("net:[200]")
    _fake_tcp_listener(tmp_path, workers[0], 8001)
    _fake_tcp_listener(tmp_path, workers[1], 8002)
    assert transport._verify_worker_loopback_listeners(tmp_path, workers) == {"loopback_listeners_checked": 2}
    thread_namespace = tmp_path / "thread-self" / "ns" / "net"
    thread_namespace.unlink()
    thread_namespace.symlink_to("net:[201]")
    with pytest.raises(transport.BindingError, match="namespaces differ"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)
    thread_namespace.unlink()
    thread_namespace.symlink_to("net:[200]")
    namespace = tmp_path / "102" / "ns" / "net"
    namespace.unlink()
    namespace.symlink_to("net:[201]")
    with pytest.raises(transport.BindingError, match="namespaces differ"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)
    namespace.unlink()
    namespace.symlink_to("net:[200]")
    namespace.unlink()
    with pytest.raises(transport.BindingError, match="Unable to inspect network namespace"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)
    namespace.symlink_to("net:[200]")
    _fake_tcp_listener(tmp_path, workers[0], 8001, address="00000000")
    with pytest.raises(transport.BindingError, match="not the expected loopback listener"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)
    _fake_tcp_listener(tmp_path, workers[0], 8001, state="01")
    with pytest.raises(transport.BindingError, match="not the expected loopback listener"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)
    _fake_tcp_listener(tmp_path, workers[0], 8001)
    workers[1]["endpoint"] = workers[0]["endpoint"]
    with pytest.raises(transport.BindingError, match="distinct"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)
    workers[1]["endpoint"] = "http://example.test:8002"
    with pytest.raises(transport.BindingError, match="loopback URL"):
        transport._verify_worker_loopback_listeners(tmp_path, workers)


def _runtime_binding_fixture(tmp_path):
    root = tmp_path.resolve()
    bench = root / "bench"
    sites = bench / "sites"
    sites.mkdir(parents=True)
    (sites / "wbs-p1-fixture.localhost").write_text("")
    app = bench / "apps" / "construction"
    app.mkdir(parents=True)

    def git(*args):
        return (
            subprocess.run(["git", "-C", str(app), *args], check=True, capture_output=True)
            .stdout.decode()
            .strip()
        )

    git("init", "-q")
    git("config", "user.email", "fixture@example.test")
    git("config", "user.name", "Fixture")
    (app / "tracked.txt").write_text("base")
    (app / "other.txt").write_text("untouched")
    git("add", "tracked.txt", "other.txt")
    git("commit", "-q", "-m", "base")
    (app / "tracked.txt").write_text("candidate")
    manifest = {
        "kind": "code",
        "base_commit": git("rev-parse", "HEAD"),
        "entries": [
            {
                "path": "tracked.txt",
                "kind": "file",
                "mode": "100644",
                "content_sha256": hashlib.sha256(b"candidate").hexdigest(),
            }
        ],
    }
    candidate_id = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    candidate_path = root / "candidate.json"
    candidate_path.write_text(json.dumps(manifest))

    binding = _binding_dict()
    binding.update(
        {
            "bench_root": str(bench),
            "sites_path": str(sites),
            "app_root": str(app),
            "candidate_id": candidate_id,
            "candidate_manifest_path": str(candidate_path),
        }
    )
    proc = root / "proc"
    workers = [_fake_worker(proc, 101, 55, 300), _fake_worker(proc, 102, 56, 301)]
    for process in ("self", "thread-self", "101", "102"):
        directory = proc / process / "ns"
        directory.mkdir(parents=True)
        (directory / "net").symlink_to("net:[200]")
    _fake_tcp_listener(proc, workers[0], 8001)
    _fake_tcp_listener(proc, workers[1], 8002)
    binding["serving_process_records"] = workers
    expected = root / "expected.json"
    expected.write_text(json.dumps({key: binding[key] for key in transport.EXPECTED_IDENTITY_KEYS}))
    binding["expected_manifest_path"] = str(expected)
    binding_path = root / "binding.json"
    binding_path.write_text(json.dumps(binding))
    return binding, binding_path, app, proc, workers


def test_runtime_binding_proof_composes_all_checks(tmp_path):
    binding, binding_path, app, proc, workers = _runtime_binding_fixture(tmp_path)
    proof = transport.verify_runtime_binding(binding_path, proc_root=proc)
    assert proof["candidate_id"] == binding["candidate_id"]
    assert proof["verified_files"] == 1
    assert proof["process_records_checked"] == 2
    assert proof["loopback_listeners_checked"] == 2
    assert proof["transport_enabled"] is False
    assert proof["unverified"] == [
        "request routing to the intended worker",
        "loaded application code",
        "database connection provenance",
        "persisted-state observation",
    ]
    with pytest.raises(transport.BindingError, match="disabled"):
        transport._require_verified_runtime()


def test_runtime_binding_rejects_worker_record_drift(tmp_path):
    binding, binding_path, app, proc, workers = _runtime_binding_fixture(tmp_path)
    descriptor = proc / "102" / "fd" / "7"
    descriptor.unlink()
    descriptor.symlink_to("socket:[999]")
    with pytest.raises(transport.BindingError, match="socket descriptor"):
        transport.verify_runtime_binding(binding_path, proc_root=proc)


def test_runtime_binding_rejects_unapproved_worker_records(tmp_path):
    binding, binding_path, app, proc, workers = _runtime_binding_fixture(tmp_path)
    binding["serving_process_records"][1]["endpoint"] = "http://127.0.0.1:9999"
    binding_path.write_text(json.dumps(binding))
    with pytest.raises(transport.BindingError, match="serving_process_records"):
        transport.verify_runtime_binding(binding_path, proc_root=proc)


def test_runtime_binding_rejects_candidate_manifest_identity_mismatch(tmp_path):
    binding, binding_path, app, proc, workers = _runtime_binding_fixture(tmp_path)
    manifest_path = Path(binding["candidate_manifest_path"])
    manifest = json.loads(manifest_path.read_text())
    manifest["entries"][0]["mode"] = "100755"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(transport.BindingError, match="identity mismatch"):
        transport.verify_runtime_binding(binding_path, proc_root=proc)


def test_runtime_binding_rechecks_candidate_after_worker_inspection(tmp_path, monkeypatch):
    binding, binding_path, app, proc, workers = _runtime_binding_fixture(tmp_path)
    real = transport._verify_worker_loopback_listeners

    def drift(proc_root, records):
        result = real(proc_root, records)
        (app / "tracked.txt").write_text("drifted during inspection")
        return result

    monkeypatch.setattr(transport, "_verify_worker_loopback_listeners", drift)
    with pytest.raises(transport.BindingError, match="content or mode"):
        transport.verify_runtime_binding(binding_path, proc_root=proc)


def test_binding_requires_candidate_manifest_and_worker_records(tmp_path):
    binding, binding_path, app, proc, workers = _runtime_binding_fixture(tmp_path)
    assert {"candidate_manifest_path", "serving_process_records"} <= transport.REQUIRED_BINDING_KEYS
    path = tmp_path / "altered.json"

    altered = json.loads(binding_path.read_text())
    del altered["candidate_manifest_path"]
    path.write_text(json.dumps(altered))
    with pytest.raises(transport.BindingError, match="missing required keys"):
        transport._load_binding(path)

    altered = json.loads(binding_path.read_text())
    altered["candidate_manifest_path"] = str(tmp_path / "absent.json")
    path.write_text(json.dumps(altered))
    with pytest.raises(transport.BindingError, match="candidate manifest is unavailable"):
        transport._load_binding(path)

    altered = json.loads(binding_path.read_text())
    altered["serving_process_records"] = []
    path.write_text(json.dumps(altered))
    with pytest.raises(transport.BindingError, match="Two serving-process records"):
        transport._load_binding(path)


def test_catalog_covers_required_families():
    names = {case["name"] for case in transport.ACCEPTANCE_CASES + transport.GENERIC_CASES}
    assert len(transport.ACCEPTANCE_CASES) >= 20
    assert len(transport.GENERIC_CASES) >= 12
    for required in (
        "read_denied_outsider",
        "create_denied_engineer",
        "delete_denied_manager",
        "delete_allowed_system_manager",
        "move_to_root_allowed_manager",
        "update_stale_version_denied",
        "cross_project_parent_denied",
        "read_denied_after_revocation",
        "revocation_remove_user_permission",
        "read_restored_after_cleanup",
        "protected_share_denied_manager",
        "company_change_denied_after_issue",
        "stock_docperm_inventory_empty",
        "generic_list_denied_engineer",
        "logout_cleanup",
        "create_after_denial_allocates_next_code",
    ):
        assert required in names
    assert all(
        case["expect"] in ("allow", "deny", "error")
        for case in transport.ACCEPTANCE_CASES + transport.GENERIC_CASES
    )


def _observer_snapshot(counter=None):
    return {
        "project": "P1",
        "company": "Company A",
        "nodes": {},
        "counter": counter,
        "shares": {},
        "project_row": {"name": "P1", "company": "Company A"},
        "counter_row": {"name": "counter-1", "project": "P1", "last_issued": counter}
        if counter is not None
        else None,
    }


_OBSERVED_NODE = {
    "company": "Company A",
    "ebs_code": "EBS-0001",
    "title": "Root",
    "parent_node": None,
    "is_group": 1,
    "disabled": False,
    "modified": "2026-11-19 12:00:00",
}
_OBSERVED_SHARE = {
    "share_doctype": "Execution Breakdown Node",
    "share_name": "EBN-1",
    "user": None,
    "everyone": True,
    "read": 1,
    "write": 0,
    "share": 0,
    "submit": 0,
}


def test_denied_create_advancing_counter_is_detected(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    monkeypatch.setattr(transport, "_session", lambda binding, fixture, opener: ({"Cookie": "x"}, "pw"))
    monkeypatch.setattr(transport, "_tree_digest", lambda *a, **k: "identical-tree")
    context["_persisted_state_observer"] = lambda *args: _observer_snapshot(1)
    responses = []

    def _request(endpoint, method, payload, headers, opener):
        return responses.pop(0)

    monkeypatch.setattr(transport, "_request", _request)
    create = {
        "name": "probe",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {"title": "t", "is_group": False},
        "expect": "allow",
        "capture": "node",
    }
    denied = {
        "name": "denied",
        "fixture": "allowed_engineer",
        "method": "create_node",
        "payload": {"title": "t", "is_group": False},
        "expect": "deny",
    }
    responses.append((200, {"message": {"name": "EBN-1", "ebs_code": "EBS-0001", "modified": "m1"}}))
    first = transport.run_case(binding, create, context)
    assert first["matched"] is True
    responses.append((403, {"exc_type": "PermissionError"}))
    denied_result = transport.run_case(binding, denied, context)
    assert denied_result["matched"] is True
    assert denied_result["state_unchanged"] is True
    # The denied create secretly advanced the counter: the next allowed create
    # skips EBS-0002. The tree digest is identical, so only the code-continuity
    # assertion can detect this persisted-state change.
    responses.append((200, {"message": {"name": "EBN-3", "ebs_code": "EBS-0003", "modified": "m3"}}))
    gap = transport.run_case(binding, dict(create, name="probe2", capture="node2"), context)
    assert gap["code_continuity"] is False
    assert gap["matched"] is False
    # Control: an exactly-next allocation passes.
    context.pop("expected_code_number:P1", None)
    responses.append((200, {"message": {"name": "EBN-1", "ebs_code": "EBS-0001", "modified": "m1"}}))
    transport.run_case(binding, dict(create, name="reset"), context)
    responses.append((200, {"message": {"name": "EBN-2", "ebs_code": "EBS-0002", "modified": "m2"}}))
    ok = transport.run_case(binding, dict(create, name="probe3", capture="node3"), context)
    assert ok["code_continuity"] is True
    assert ok["matched"] is True


def test_denied_mutation_requires_independent_state_and_fails_on_change(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    monkeypatch.setattr(transport, "_session", lambda *args: ({}, "pw"))
    calls = []
    monkeypatch.setattr(transport, "_request", lambda *args: calls.append(args) or (403, {}))
    case = {
        "name": "denied",
        "fixture": "allowed_engineer",
        "method": "create_node",
        "payload": {"title": "t", "is_group": False},
        "expect": "deny",
    }
    result = transport.run_case(binding, case, context)
    assert result["matched"] is False and result["actual"] == "not_run"
    assert calls == []
    snapshots = iter([_observer_snapshot(1), _observer_snapshot(2)])
    context["_persisted_state_observer"] = lambda *args: next(snapshots)
    result = transport.run_case(binding, case, context)
    assert result["matched"] is False and result["state_unchanged"] is False
    snapshots = iter([_observer_snapshot(1), None])
    context["_persisted_state_observer"] = lambda *args: next(snapshots)
    assert transport.run_case(binding, case, context)["matched"] is False


def test_denied_mutation_detects_reused_mutable_snapshot(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    monkeypatch.setattr(transport, "_session", lambda *args: ({}, "pw"))
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    state = _observer_snapshot(1)

    def observe(binding, case, payload):
        assert payload["project"] == binding["project"]
        return state

    def deny(*args):
        state["counter"] += 1
        return 403, {}

    context["_persisted_state_observer"] = observe
    monkeypatch.setattr(transport, "_request", deny)
    case = {"name": "denied", "fixture": "allowed_engineer", "method": "create_node", "expect": "deny"}
    result = transport.run_case(binding, case, context)
    assert result["actual"] == "deny"
    assert result["state_unchanged"] is False
    assert result["matched"] is False


@pytest.mark.parametrize(
    "incomplete",
    [
        {},
        {"project": "P1", "company": "Company A", "nodes": {}, "shares": {}},
        dict(_observer_snapshot(), project="Wrong Project"),
        dict(_observer_snapshot(), counter=True),
        dict(_observer_snapshot(1), nodes={"EBN-1": {}}),
        dict(_observer_snapshot(1), shares={"SHARE-1": {}}),
        dict(_observer_snapshot(1), nodes={"": _OBSERVED_NODE}),
        dict(_observer_snapshot(1), shares={" ": _OBSERVED_SHARE}),
        dict(_observer_snapshot(1), nodes={"EBN-1": dict.fromkeys(_OBSERVED_NODE)}),
        dict(_observer_snapshot(1), shares={"SHARE-1": dict.fromkeys(_OBSERVED_SHARE)}),
        dict(_observer_snapshot(1), nodes={"EBN-1": dict(_OBSERVED_NODE, disabled="0")}),
        dict(_observer_snapshot(1), shares={"SHARE-1": dict(_OBSERVED_SHARE, everyone=False)}),
        dict(_observer_snapshot(1), nodes={"EBN-1": dict(_OBSERVED_NODE, company="Other Company")}),
        dict(_observer_snapshot(0), nodes={"EBN-1": _OBSERVED_NODE}),
        dict(_observer_snapshot(1), nodes={"EBN-1": dict(_OBSERVED_NODE, ebs_code="EBS-0002")}),
        dict(_observer_snapshot(1), nodes={"EBN-1": dict(_OBSERVED_NODE, ebs_code="EBS-000¹")}),
        dict(_observer_snapshot(1), nodes={"EBN-1": _OBSERVED_NODE, "EBN-2": _OBSERVED_NODE}),
        dict(_observer_snapshot(1), project_row=None),
        dict(_observer_snapshot(1), counter_row=None),
        dict(_observer_snapshot(1), counter_row={"name": "counter-1", "project": "P1", "last_issued": 2}),
        dict(_observer_snapshot(), counter_row={"name": "counter-1", "project": "P1", "last_issued": 0}),
    ],
)
def test_denied_mutation_rejects_incomplete_snapshot(monkeypatch, incomplete):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    monkeypatch.setattr(transport, "_session", lambda *args: ({}, "pw"))
    calls = []
    monkeypatch.setattr(transport, "_request", lambda *args: calls.append(args) or (403, {}))
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    case = {"name": "denied", "fixture": "allowed_engineer", "method": "create_node", "expect": "deny"}

    context["_persisted_state_observer"] = lambda *args: incomplete
    result = transport.run_case(binding, case, context)
    assert result["actual"] == "not_run" and result["matched"] is False
    assert not calls

    snapshots = iter([_observer_snapshot(), incomplete])
    context["_persisted_state_observer"] = lambda *args: next(snapshots)
    result = transport.run_case(binding, case, context)
    assert result["state_unchanged"] is False and result["matched"] is False
    assert "after snapshot" in result["error"]
    assert len(calls) == 1

    context["_persisted_state_observer"] = lambda *args: _observer_snapshot()
    result = transport.run_case(binding, case, context)
    assert result["state_unchanged"] is True and result["matched"] is True


def test_observer_snapshot_accepts_nullable_root_and_everyone_share():
    snapshot = dict(
        _observer_snapshot(1), nodes={"EBN-1": _OBSERVED_NODE}, shares={"SHARE-1": _OBSERVED_SHARE}
    )
    assert transport._valid_observer_snapshot(snapshot, "P1")


def test_observer_snapshot_allows_retained_counter_ahead_of_widened_code():
    node = dict(_OBSERVED_NODE, ebs_code="EBS-10000")
    snapshot = dict(_observer_snapshot(10002), nodes={"EBN-1": node})
    assert transport._valid_observer_snapshot(snapshot, "P1")


class _SnapshotConnection:
    def __init__(self, *, database="lab_db", missing_engine=False, counter=2):
        self.database = database
        self.missing_engine = missing_engine
        self.counter = counter
        self.sql = []
        self.result = []
        self.rolled_back = False
        self.closed = False
        self.cursor_closed = False

    def cursor(self):
        return self

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        if "DATABASE() AS" in sql:
            self.result = [{"database_name": self.database}]
        elif "information_schema.TABLES" in sql:
            self.result = [
                {"TABLE_NAME": name, "ENGINE": "InnoDB"}
                for name in params
                if not (self.missing_engine and name == "tabDocShare")
            ]
        elif "FROM `tabProject`" in sql:
            self.result = [{"name": "P1", "company": "Company A"}]
        elif "FROM `tabExecution Breakdown Node`" in sql:
            self.result = [dict(_OBSERVED_NODE, name="EBN-1")]
        elif "FROM `tabExecution Code Counter`" in sql:
            self.result = [{"name": "counter-1", "project": "P1", "last_issued": self.counter}]
        elif "FROM `tabDocShare`" in sql:
            self.result = [dict(_OBSERVED_SHARE, name="SHARE-1")]
        else:
            self.result = []

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result

    def rollback(self):
        self.rolled_back = True

    def close(self):
        if not self.cursor_closed:
            self.cursor_closed = True
        else:
            self.closed = True


def test_persisted_reader_captures_node_counter_and_shares(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    connection = _SnapshotConnection()
    snapshot = transport._read_persisted_snapshot(connection, project="P1", expected_database="lab_db")
    assert snapshot["nodes"]["EBN-1"]["ebs_code"] == "EBS-0001"
    assert snapshot["counter"] == 2 and "SHARE-1" in snapshot["shares"]
    assert snapshot["counter_row"]["name"] == "counter-1"
    assert snapshot["project_row"]["name"] == "P1"
    assert connection.rolled_back and connection.closed
    assert any("CONSISTENT SNAPSHOT, READ ONLY" in sql for sql, _ in connection.sql)
    assert all("P1" not in sql for sql, _ in connection.sql)


def test_persisted_reader_detects_counter_identity_change(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    before = transport._read_persisted_snapshot(
        _SnapshotConnection(), project="P1", expected_database="lab_db"
    )

    class ChangedCounter(_SnapshotConnection):
        def execute(self, sql, params=None):
            super().execute(sql, params)
            if "FROM `tabExecution Code Counter`" in sql:
                self.result[0]["name"] = "counter-replaced"

    after = transport._read_persisted_snapshot(ChangedCounter(), project="P1", expected_database="lab_db")
    assert before["counter"] == after["counter"]
    assert before != after


@pytest.mark.parametrize("options", [{"database": "other_db"}, {"missing_engine": True}, {"counter": 0}])
def test_persisted_reader_fails_closed_and_closes_connection(monkeypatch, options):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    connection = _SnapshotConnection(**options)
    with pytest.raises(transport.BindingError):
        transport._read_persisted_snapshot(connection, project="P1", expected_database="lab_db")
    assert connection.rolled_back and connection.closed


class _RevocationAdapter:
    def __init__(self):
        self.session = object()
        self.calls = []
        self.revoked = False
        self.state = _observer_snapshot(1)

    def worker_identities(self):
        return "worker-a", "worker-b"

    def login_on_worker(self, worker):
        self.calls.append(("login", worker))
        return self.session

    def read(self, worker, session, project):
        assert worker == "worker-a" and session is self.session and project == "P1"
        self.calls.append(("read", self.revoked))
        return "deny" if self.revoked else "allow"

    def snapshot(self, project):
        self.calls.append(("snapshot", project))
        return self.state

    def revoke_and_commit(self, worker, access_input):
        assert worker == "worker-b"
        self.calls.append(("revoke", access_input))
        self.revoked = True
        return True

    def mutate(self, worker, session, project):
        assert worker == "worker-a" and session is self.session and self.revoked
        self.calls.append(("mutate", project))
        return "deny"

    def control_read(self, worker, project):
        self.calls.append(("control", project))
        return "allow"

    def restore_and_commit(self, worker, access_input):
        assert worker == "worker-b"
        self.calls.append(("restore", access_input))
        self.revoked = False
        return True

    def logout(self, worker, session):
        assert worker == "worker-a" and session is self.session
        self.calls.append(("logout", worker))
        return True


@pytest.mark.parametrize(
    "access_input", ["role", "custom_docperm", "user_permission", "project_share", "active_scope"]
)
def test_revocation_sequence_reuses_session_and_restores(monkeypatch, access_input):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    adapter = _RevocationAdapter()
    assert transport._exercise_revocation_sequence(adapter, project="P1", access_input=access_input)[
        "matched"
    ]
    assert [call[0] for call in adapter.calls] == [
        "login",
        "read",
        "snapshot",
        "revoke",
        "read",
        "mutate",
        "snapshot",
        "control",
        "restore",
        "read",
        "logout",
    ]


def test_revocation_sequence_restores_after_failure_and_detects_side_effect(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    adapter = _RevocationAdapter()

    def unsafe_mutate(*args):
        adapter.state["counter"] = 2
        adapter.state["counter_row"]["last_issued"] = 2
        return "deny"

    adapter.mutate = unsafe_mutate
    with pytest.raises(transport.BindingError, match="preserve persisted state"):
        transport._exercise_revocation_sequence(adapter, project="P1", access_input="role")
    assert (
        adapter.calls[-3:] == [("restore", "role"), ("read", False), ("logout", "worker-a")]
        and not adapter.revoked
    )


def test_revocation_sequence_refuses_same_worker_and_unconfirmed_commit(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    adapter = _RevocationAdapter()
    adapter.worker_identities = lambda: ("worker-a", "worker-a")
    with pytest.raises(transport.BindingError, match="distinct workers"):
        transport._exercise_revocation_sequence(adapter, project="P1", access_input="role")
    assert adapter.calls == []
    adapter = _RevocationAdapter()
    adapter.revoke_and_commit = lambda *args: False
    with pytest.raises(transport.BindingError, match="commit was not confirmed"):
        transport._exercise_revocation_sequence(adapter, project="P1", access_input="role")
    assert adapter.calls[-3:] == [("restore", "role"), ("read", False), ("logout", "worker-a")]


def test_revocation_sequence_requires_restored_access_and_session_cleanup(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    adapter = _RevocationAdapter()
    adapter.restore_and_commit = lambda *args: True
    with pytest.raises(transport.BindingError, match="did not regain access"):
        transport._exercise_revocation_sequence(adapter, project="P1", access_input="role")
    assert adapter.calls[-1] == ("logout", "worker-a")
    adapter = _RevocationAdapter()
    adapter.read = lambda *args: "deny"
    with pytest.raises(transport.BindingError, match="Warm request"):
        transport._exercise_revocation_sequence(adapter, project="P1", access_input="role")
    assert adapter.calls[-1] == ("logout", "worker-a")


def test_transport_cli_refuses_declared_binding_without_runtime_proof(monkeypatch, capsys):
    monkeypatch.setattr(transport, "_load_binding", lambda path: pytest.fail("must not read binding"))
    assert transport.main(["--binding", "/tmp/claimed-binding"]) == 2
    assert "disabled" in capsys.readouterr().out


def test_transport_callables_refuse_execution_before_any_http(monkeypatch):
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    context["_persisted_state_observer"] = lambda *args: pytest.fail("must not read persisted state")
    monkeypatch.setattr(
        transport.urllib.request, "build_opener", lambda *args: pytest.fail("must not open HTTP")
    )
    with pytest.raises(transport.BindingError, match="disabled"):
        transport.run(binding, "allowed_engineer", "get_tree", {})
    with pytest.raises(transport.BindingError, match="disabled"):
        transport.run_catalog(binding)
    with pytest.raises(transport.BindingError, match="disabled"):
        transport.run_case(binding, transport.GENERIC_CASES[3], context)
    with pytest.raises(transport.BindingError, match="disabled"):
        transport._login(binding["http_endpoint"], "user", "password", None)
    with pytest.raises(transport.BindingError, match="disabled"):
        transport._open(None, None)
    with pytest.raises(transport.BindingError, match="disabled"):
        transport._exercise_revocation_sequence(None, project="P1", access_input="role")


def test_generic_resource_path_substitutes_and_encodes_node(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    monkeypatch.setattr(transport, "_session", lambda *args: ({}, "pw"))
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    case = next(item for item in transport.GENERIC_CASES if item["name"] == "generic_read_denied_outsider")

    def deny(opener, request):
        assert request.full_url == (
            binding["http_endpoint"] + "/api/resource/Execution%20Breakdown%20Node/EBN%20A%2FB%3F%23%25"
        )
        return 403, {}

    monkeypatch.setattr(transport, "_open", deny)
    context["node"] = "EBN A/B?#%"
    assert transport.run_case(binding, case, context)["matched"] is True
    assert transport.run_catalog(binding, only=case["name"])[0]["actual"] == "not_run"
    with pytest.raises(transport.BindingError, match="missing or invalid"):
        transport.run_case(binding, case, transport._context_from_binding(binding))


@pytest.mark.parametrize(
    "payload",
    [
        b'{"exc_type":"PermissionError","message":{"project":"secret"}}',
        b'{"exc_type":"PermissionError","_server_messages":"secret"}',
        b"not-json-secret",
        b'["secret"]',
        b"\xffsecret",
    ],
)
def test_denial_with_disclosed_or_unparsed_body_never_passes(payload):
    assert not transport._is_denied(403, transport._decode(payload))
    assert not transport._is_validation_error(417, transport._decode(payload))


def test_denial_accepts_only_empty_or_redacted_error_body():
    assert transport._is_denied(403, {})
    assert transport._is_denied(403, {"exc_type": "PermissionError"})
    assert transport._is_validation_error(417, {"exc_type": "ValidationError"})


@pytest.mark.parametrize("response", [{}, {"exc_type": "PermissionError"}, {"exc_type": "ValidationError"}])
def test_generic_resource_404_does_not_prove_denial(monkeypatch, response):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    monkeypatch.setattr(transport, "_session", lambda *args: ({}, "pw"))
    monkeypatch.setattr(transport, "_generic_request", lambda *args: (404, response))
    binding = _binding_dict()
    context = dict(transport._context_from_binding(binding), node="EBN-1")
    case = next(item for item in transport.GENERIC_CASES if item["name"] == "generic_read_denied_outsider")
    result = transport.run_case(binding, case, context)
    assert result["status"] == 404
    assert result["actual"] == "error" and result["matched"] is False


def test_generic_inventory_expectation(monkeypatch):
    monkeypatch.setattr(transport, "_require_verified_runtime", lambda: None)
    binding = _binding_dict()
    context = transport._context_from_binding(binding)
    monkeypatch.setattr(transport, "_session", lambda binding, fixture, opener: ({"Cookie": "x"}, "pw"))
    case = {
        "name": "inventory",
        "fixture": "administrator",
        "http_method": "GET",
        "path": "/api/method/frappe.client.get_list",
        "payload": {},
        "expect": "allow",
        "expect_empty": True,
    }
    monkeypatch.setattr(transport, "_generic_request", lambda *a, **k: (200, {"message": []}))
    assert transport.run_case(binding, case, context)["matched"] is True
    monkeypatch.setattr(transport, "_generic_request", lambda *a, **k: (200, {"message": [{"name": "x"}]}))
    result = transport.run_case(binding, case, context)
    assert result["inventory_empty"] is False
    assert result["matched"] is False


# ---------------------------------------------------------------------------
# SCP-013: page generation/selection binding (isolated Node behavior probe)
# ---------------------------------------------------------------------------


def test_page_generation_and_denial_behavior():
    import subprocess

    js_path = (
        ROOT / "construction" / "construction" / "page" / "execution_breakdown" / "execution_breakdown.js"
    )
    completed = subprocess.run(
        ["node", "--test", str(ROOT / "tests_offline" / "test_scope_context_wbs.js")],
        capture_output=True, text=True, timeout=60, cwd=str(ROOT),
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr



def test_construction_hook_seal_matches_reviewed_generation_and_rejects_drift(tmp_path, monkeypatch):
    """The reviewed asset-version change must not disable full-blob hook sealing."""
    hook_source = (ROOT / "construction" / "hooks.py").read_bytes()
    assert hashlib.sha256(hook_source).hexdigest() == access.PINNED_HOOK_HASHES["construction"]
    hook_file = tmp_path / "hooks.py"
    hook_file.write_bytes(hook_source)
    monkeypatch.setattr(access, "_app_root", lambda app: tmp_path)
    _, sources, _, _ = access._project_profile_source(["construction"])
    assert sources["construction"]["sha256"] == access.PINNED_HOOK_HASHES["construction"]
    hook_file.write_bytes(hook_source + b"\n# unreviewed drift\n")
    with pytest.raises(access.UnsupportedProfile, match="hook source does not match"):
        access._project_profile_source(["construction"])
