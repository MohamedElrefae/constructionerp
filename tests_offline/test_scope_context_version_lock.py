"""Offline contract checks for the scope save's version gate (not a DB lock test)."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


class Conflict(Exception):
    pass


class Validation(Exception):
    pass


class Denied(Exception):
    pass


class FakeDatabase:
    def __init__(self, version=None):
        self.version = version
        self.calls = []

    def get_value(self, doctype, filters, field, for_update=False):
        self.calls.append((doctype, filters, field, for_update))
        if doctype == "User":
            return filters
        return "scope-1" if self.version is not None else None


def build_guard(version=None):
    source = (ROOT / "construction/api/scope_context_api.py").read_text()
    module = ast.parse(source)
    guard = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "_locked_scope_for_save"
    )
    db = FakeDatabase(version)
    sentinel = object()
    fake = SimpleNamespace(
        db=db, PermissionError=Denied, ValidationError=Validation, TimestampMismatchError=Conflict
    )
    fake.throw = lambda message, exc: (_ for _ in ()).throw(exc(message))
    fake.get_doc = lambda doctype, name, for_update=False: SimpleNamespace(
        scope_version=db.version, for_update=for_update
    )
    fake.new_doc = lambda doctype: SimpleNamespace(scope_version=None)
    namespace = {"frappe": fake, "_": lambda value: value, "_UNSPECIFIED": sentinel}
    exec(
        compile(ast.fix_missing_locations(ast.Module(body=[guard], type_ignores=[])), "scope_guard", "exec"),
        namespace,
    )
    return namespace[guard.name], db, sentinel


def test_stale_save_is_rejected_after_newer_version_and_locks_are_requested():
    guard, db, _ = build_guard(7)
    winner = guard("user", 7)
    assert winner.for_update is True
    assert all(call[3] for call in db.calls)
    assert [call[0] for call in db.calls] == ["User", "User Scope Context"]
    db.version = 8  # Simulates a committed competing write; not a concurrency/DB test.
    with pytest.raises(Conflict):
        guard("user", 7)
    assert guard("user", "8").scope_version == 8


def test_new_scope_and_legacy_call_and_invalid_version():
    guard, _, omitted = build_guard()
    assert guard("user", 0).scope_version is None
    assert guard("user", omitted).scope_version is None
    for value in [True, -1, "-1", "NaN", None]:
        with pytest.raises(Validation):
            guard("user", value)


def test_scope_endpoint_passes_version_to_guard():
    module = ast.parse((ROOT / "construction/api/scope_context_api.py").read_text())
    endpoint = next(
        n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "set_scope_context"
    )
    assert "expected_scope_version" in [arg.arg for arg in endpoint.args.args]
    assert any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_locked_scope_for_save"
        and [a.id for a in n.args if isinstance(a, ast.Name)] == ["user", "expected_scope_version"]
        for n in ast.walk(endpoint)
    )


def build_get_scope_context(scope_doc):
    source = (ROOT / "construction/api/scope_context_api.py").read_text()
    module = ast.parse(source)
    fn = next(
        n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "get_scope_context"
    )
    fn.decorator_list = []  # offline: skip the whitelist wrapper
    calls = []

    def fake_helper(user=None):
        calls.append(user)
        return scope_doc

    namespace = {"frappe": SimpleNamespace(), "get_user_scope_context": fake_helper}
    exec(
        compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), "get_scope_context", "exec"),
        namespace,
    )
    return namespace[fn.name], calls


def test_get_scope_context_is_whitelisted():
    module = ast.parse((ROOT / "construction/api/scope_context_api.py").read_text())
    fn = next(
        n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "get_scope_context"
    )
    assert any(
        isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "whitelist"
        for d in fn.decorator_list
    )


def test_get_scope_context_returns_authoritative_scope_and_version():
    doc = SimpleNamespace(company="C1", cost_center="CC1", project="P1", department="D1", scope_version=5)
    fn, calls = build_get_scope_context(doc)
    assert fn() == {
        "scope": {"company": "C1", "cost_center": "CC1", "project": "P1", "department": "D1"},
        "scope_version": 5,
    }
    assert calls == [None]  # reads only the session user's own scope


def test_get_scope_context_without_scope_row_returns_nulls_and_zero():
    fn, _ = build_get_scope_context(None)
    assert fn() == {
        "scope": {"company": None, "cost_center": None, "project": None, "department": None},
        "scope_version": 0,
    }
