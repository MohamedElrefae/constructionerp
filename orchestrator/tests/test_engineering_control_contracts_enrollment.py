"""Tests for the test-only synthetic enrollment decision layer."""

from __future__ import annotations

import ast
import os
import socket
import sqlite3
from pathlib import Path

import pytest
from engineering_control_contracts.enrollment import (
    EnrollmentConflict,
    EnrollmentDenied,
    EnrollmentInvalid,
    SyntheticEnrollmentRegistry,
    SyntheticPrincipal,
)


def _admin(scope=("project-a", "project-b")):
    return SyntheticPrincipal("admin", frozenset({"admin", "read"}), frozenset(scope))


def _reader(project="project-a"):
    return SyntheticPrincipal("reader", frozenset({"read"}), frozenset({project}))


def _registry():
    registry = SyntheticEnrollmentRegistry()
    admin = _admin()
    registry.enroll_project(admin, "project-a", ["repo-shared"])
    registry.enroll_project(admin, "project-b", ["repo-shared"])
    registry.enroll_work_item(admin, "project-a", "work-a")
    registry.enroll_work_item(admin, "project-a", "work-a2", ["repo-a2"])
    registry.enroll_work_item(admin, "project-b", "work-b")
    return registry, admin


def test_canonical_ids_and_path_hints_fail_closed():
    registry = SyntheticEnrollmentRegistry()
    admin = _admin()
    for bad in ("", "../project", "/absolute", "has space", "x" * 97, "a/b", "a\\b"):
        with pytest.raises(EnrollmentInvalid):
            registry.enroll_project(admin, bad, ["repo-1"])
    for hint in ("../escape", "/absolute", "a/../b", "bad hint", "x" * 257):
        with pytest.raises(EnrollmentInvalid):
            registry.enroll_project(admin, "project-a", [hint])
    with pytest.raises(EnrollmentInvalid):
        registry.enroll_work_item(admin, "project-a", "work-a", "repo-as-string")


def test_multiple_projects_share_repository_without_implicit_authority():
    registry, _admin_p = _registry()
    assert registry.decide(_reader("project-a"), "project-a", "work-a", repository_hint="repo-shared")
    assert registry.decide(_reader("project-b"), "project-b", "work-b", repository_hint="repo-shared")
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader("project-a"), "project-b", "work-b", repository_hint="repo-shared")


def test_multiple_work_items_and_cross_project_scope_denied():
    registry, _admin_p = _registry()
    registry.decide(_reader("project-a"), "project-a", "work-a")
    registry.decide(_reader("project-a"), "project-a", "work-a2")
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader("project-a"), "project-a", "work-b")


def test_unknown_and_revoked_bindings_are_denied():
    registry, admin = _registry()
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader(), "project-a", "unknown")
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader("project-z"), "project-z", "work-a")

    registry.revoke_work_item(admin, "project-a", "work-a", "retired")
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader(), "project-a", "work-a")
    registry.revoke_project(admin, "project-b", "retired")
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader("project-b"), "project-b", "work-b")


def test_duplicate_conflict_rebind_and_audit():
    registry, admin = _registry()
    same = registry.enroll_project(admin, "project-a", ["repo-shared"])
    assert same.active and same.revision == 1
    with pytest.raises(EnrollmentConflict):
        registry.enroll_project(admin, "project-a", ["different-repo"])
    with pytest.raises(EnrollmentConflict):
        registry.enroll_work_item(admin, "project-a", "work-a", ["different-hint"])
    with pytest.raises(EnrollmentDenied):
        registry.rebind_project(_reader(), "project-a", ["repo-new"], "not admin")
    rebound = registry.rebind_project(admin, "project-a", ["repo-new"], "owner move")
    assert rebound.revision == 2
    assert registry.decide(_reader(), "project-a", "work-a", repository_hint="repo-new")
    assert any(event.action == "rebind_project" and event.actor == "admin" for event in registry.audit)
    sequences = [event.sequence for event in registry.audit]
    assert sequences == list(range(1, len(sequences) + 1))


def test_re_enrollment_replacement_and_collisions():
    registry, admin = _registry()
    registry.revoke_project(admin, "project-a", "pause")
    with pytest.raises(EnrollmentDenied):
        registry.re_enroll_project(admin, "project-a", ["different"])
    reenrolled = registry.re_enroll_project(admin, "project-a", ["repo-shared"])
    assert reenrolled.active and reenrolled.revision == 3

    with pytest.raises(EnrollmentConflict):
        registry.replace_work_item(admin, "project-a", "work-a", "work-a2", "collision")
    replacement = registry.replace_work_item(admin, "project-a", "work-a", "work-new", "owner replacement")
    assert replacement.active
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader(), "project-a", "work-a")
    registry.decide(_reader(), "project-a", "work-new")
    with pytest.raises(EnrollmentDenied):
        registry.revoke_work_item(_reader(), "project-a", "work-new", "not admin")


def test_unknown_or_unenrolled_legacy_project_is_not_inferred_from_repository():
    registry, _admin_p = _registry()
    # A repository hint alone is not a project identity.
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader("legacy"), "legacy", "work-a", repository_hint="repo-shared")
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader(), "project-a", "work-a", repository_hint="unknown-repo")


def test_prototype_has_no_runtime_io_or_engine_dependencies(monkeypatch):
    module_path = Path(__file__).parents[1] / "engineering_control_contracts/enrollment.py"
    source = module_path.read_text()
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    for forbidden in ("sqlite3", "subprocess", "engine", "store", "dashboard", "os", "pathlib"):
        assert forbidden not in imports

    def no_io(*args, **kwargs):
        raise AssertionError("prototype attempted filesystem/network/database access")

    monkeypatch.setattr("builtins.open", no_io)
    monkeypatch.setattr(os, "open", no_io)
    monkeypatch.setattr(socket, "socket", no_io)
    monkeypatch.setattr(sqlite3, "connect", no_io)

    registry = SyntheticEnrollmentRegistry()
    admin = SyntheticPrincipal("admin", frozenset({"admin"}), frozenset())
    reader = SyntheticPrincipal("reader", frozenset({"read"}), frozenset({"project-a"}))
    registry.enroll_project(admin, "project-a", ["repo-a"])
    registry.enroll_work_item(admin, "project-a", "work-a")
    registry.decide(reader, "project-a", "work-a")
    registry.rebind_project(admin, "project-a", ["repo-b"], "owner move")
    registry.replace_work_item(admin, "project-a", "work-a", "work-new", "replacement")
    registry.revoke_work_item(admin, "project-a", "work-new", "retired")
    registry.revoke_project(admin, "project-a", "retired")
    assert registry.audit


def test_principal_collections_are_strict_and_immutable():
    for capabilities in ("bread", "admin", ["read", "write"], [], ["read", ["admin"]]):
        with pytest.raises(EnrollmentInvalid):
            SyntheticPrincipal("owner", capabilities, frozenset({"project-a"}))
    with pytest.raises(EnrollmentInvalid):
        SyntheticPrincipal("owner", frozenset({"read"}), "project-a")
    with pytest.raises(EnrollmentInvalid):
        SyntheticPrincipal("owner", frozenset({"read"}), ["../project"])

    capabilities = {"read"}
    scope = {"project-a"}
    principal = SyntheticPrincipal("owner", capabilities, scope)
    capabilities.add("admin")
    scope.add("project-b")
    assert principal.capabilities == frozenset({"read"})
    assert principal.project_scope == frozenset({"project-a"})
    registry, _admin_p = _registry()
    with pytest.raises(EnrollmentDenied):
        registry.decide(principal, "project-b", "work-b")


def test_admin_is_global_but_reader_scope_is_exact():
    registry = SyntheticEnrollmentRegistry()
    global_admin = SyntheticPrincipal("admin", frozenset({"admin"}), frozenset())
    registry.enroll_project(global_admin, "project-a", ["repo-a"])
    registry.enroll_work_item(global_admin, "project-a", "work-a")
    reader = SyntheticPrincipal("reader", frozenset({"read"}), frozenset())
    with pytest.raises(EnrollmentDenied):
        registry.decide(reader, "project-a", "work-a")
    scoped = SyntheticPrincipal("reader", frozenset({"read"}), frozenset({"project-a"}))
    registry.decide(scoped, "project-a", "work-a")


def test_replacement_audit_records_old_and_new_and_reason_policy():
    registry, admin = _registry()
    replacement = registry.replace_work_item(admin, "project-a", "work-a", "work-new", "owner replacement")
    assert replacement.work_item_id == "work-new"
    event = registry.audit[-1]
    assert event.action == "replace_work_item"
    assert event.old_work_item_id == "work-a"
    assert event.new_work_item_id == "work-new"
    assert event.reason == "owner replacement"

    before = len(registry.audit)
    with pytest.raises(EnrollmentInvalid):
        registry.replace_work_item(admin, "project-a", "work-a2", "work-empty", "")
    assert len(registry.audit) == before
    assert registry.work_items[("project-a", "work-a2")].active


def test_mutations_under_revoked_project_are_denied_and_re_enrollment_restores_policy():
    registry, admin = _registry()
    registry.revoke_work_item(admin, "project-a", "work-a", "retired")
    registry.revoke_project(admin, "project-a", "project pause")
    before = len(registry.audit)

    with pytest.raises(EnrollmentDenied):
        registry.replace_work_item(admin, "project-a", "work-a2", "work-new", "staged")
    assert len(registry.audit) == before
    assert registry.work_items[("project-a", "work-a2")].active

    registry.re_enroll_project(admin, "project-a", ["repo-shared"])
    with pytest.raises(EnrollmentDenied):
        registry.decide(_reader(), "project-a", "work-a")  # individually revoked remains revoked
    registry.decide(_reader(), "project-a", "work-a2")  # active item restored
    assert not registry.work_items[("project-a", "work-a")].active


def test_work_item_mutations_are_denied_while_project_is_revoked():
    registry, admin = _registry()
    registry.revoke_project(admin, "project-b", "project pause")
    before_audit = len(registry.audit)
    before_revision = registry.work_items[("project-b", "work-b")].revision

    with pytest.raises(EnrollmentDenied):
        registry.revoke_work_item(admin, "project-b", "work-b", "retired")
    with pytest.raises(EnrollmentDenied):
        registry.enroll_work_item(admin, "project-b", "work-c")
    with pytest.raises(EnrollmentDenied):
        registry.replace_work_item(admin, "project-b", "work-b", "work-c", "staged")

    assert len(registry.audit) == before_audit
    item = registry.work_items[("project-b", "work-b")]
    assert item.active and item.revision == before_revision
    assert ("project-b", "work-c") not in registry.work_items

    registry.re_enroll_project(admin, "project-b", ["repo-shared"])
    registry.decide(_reader("project-b"), "project-b", "work-b")
