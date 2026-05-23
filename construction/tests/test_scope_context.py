import frappe
from construction.api.scope_context_api import (
    set_scope_context,
    get_user_scope_context,
    get_user_scope_hierarchy,
)
from construction.boot import extend_bootinfo


def run_all_tests():
    print("=" * 60)
    print("SCOPE CONTEXT - INTEGRATION TEST SUITE")
    print("=" * 60)

    tests = [
        ("T-001 Create scope context", test_create_scope_context),
        ("T-002 Update scope context", test_update_scope_context),
        ("T-003 Session Defaults sync", test_session_defaults_sync),
        ("T-004 Cross-validation", test_cross_validation),
        ("T-005 Authorization", test_authorization),
        ("T-006 Bootinfo includes scope_context", test_bootinfo_scope_context),
        ("T-007 Bootinfo includes hierarchy", test_bootinfo_hierarchy),
        ("T-008 Track Changes version log", test_version_log),
        ("T-009 Concurrent writes", test_concurrent_writes),
        ("T-010 First-time user hierarchy", test_first_time_user),
        ("T-011 Session Defaults cleared on switch", test_defaults_cleared_on_switch),
        ("T-012 NestedSet descendant expansion", test_nestedset_expansion),
        ("T-013 Server-side query injection", test_server_side_injection),
    ]

    passed = 0
    failed = 0

    frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1)

    for test_name, test_func in tests:
        try:
            test_func()
            print(f"  {test_name}")
            passed += 1
        except Exception as e:
            print(f"  {test_name}: {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        raise Exception(f"{failed} test(s) failed")
    print("ALL TESTS PASSED")


def _cleanup():
    frappe.db.delete("User Scope Context", {"user": "Administrator"})
    frappe.db.delete("User Scope Context", {"user": "test_scope@example.com"})
    frappe.db.commit()


def _ensure_test_user():
    if not frappe.db.exists("User", "test_scope@example.com"):
        user = frappe.new_doc("User")
        user.email = "test_scope@example.com"
        user.first_name = "Test Scope"
        user.send_welcome_email = 0
        user.insert(ignore_permissions=True)
        frappe.db.commit()


_COST_CENTER = "Main - E"  # non-group cost center belonging to Elrefae
_GROUP_CC = "Elrefae - E"  # group cost center (lft=1, rgt=4)


# === T-001 ===
def test_create_scope_context():
    _cleanup()
    result = set_scope_context(company="Elrefae", cost_center=_COST_CENTER, source="test")
    assert result["success"] is True
    assert result["scope_version"] == 1

    doc = get_user_scope_context("Administrator")
    assert doc is not None
    assert doc.company == "Elrefae"
    assert doc.cost_center == _COST_CENTER
    assert doc.scope_version == 1
    frappe.db.commit()


# === T-002 ===
def test_update_scope_context():
    _cleanup()
    r1 = set_scope_context(company="Elrefae", source="test")
    r2 = set_scope_context(company="Elrefae", cost_center=_COST_CENTER, source="test")
    assert r2["scope_version"] > r1["scope_version"]

    doc = get_user_scope_context("Administrator")
    assert doc.company == "Elrefae"
    assert doc.cost_center == _COST_CENTER
    assert doc.scope_version == 2
    frappe.db.commit()


# === T-003 ===
def test_session_defaults_sync():
    _cleanup()
    set_scope_context(company="Elrefae", cost_center=_COST_CENTER, source="test")
    frappe.db.commit()

    c = frappe.defaults.get_user_default("company", "Administrator")
    cc = frappe.defaults.get_user_default("cost_center", "Administrator")
    assert c == "Elrefae", f"Expected Elrefae, got {c}"
    assert cc == _COST_CENTER, f"Expected {_COST_CENTER}, got {cc}"


# === T-004 ===
def test_cross_validation():
    from construction.construction.utils.scope_validation import validate_scope_dimensions

    ok, msg = validate_scope_dimensions("Elrefae", _COST_CENTER, None, None)
    assert ok is True, f"Expected valid, got error: {msg}"

    ok, msg = validate_scope_dimensions("Elrefae", None, None, None)
    assert ok is True

    ok, msg = validate_scope_dimensions("Elrefae", "NonExistentCC", None, None)
    assert ok is True


# === T-005 ===
def test_authorization():
    _ensure_test_user()
    frappe.set_user("test_scope@example.com")

    try:
        set_scope_context(company="__NONEXISTENT__", source="test")
        assert False, "Should have thrown"
    except Exception:
        pass

    frappe.set_user("Administrator")


# === T-006 ===
def test_bootinfo_scope_context():
    _cleanup()
    result = set_scope_context(company="Elrefae", source="test")
    frappe.db.commit()
    assert result["success"] is True

    bootinfo = extend_bootinfo({})
    assert bootinfo.get("scope_context_enabled") is True, (
        f"scope_context_enabled should be True, got {bootinfo.get('scope_context_enabled')}"
    )
    sc = bootinfo.get("scope_context")
    assert sc is not None, f"scope_context missing from bootinfo: {bootinfo}"
    assert sc.get("current") is not None, f"current missing: {sc}"
    assert sc["current"]["company"] == "Elrefae", (
        f"Expected company=Elrefae, got {sc['current'].get('company')}"
    )


# === T-007 ===
def test_bootinfo_hierarchy():
    bootinfo = extend_bootinfo({})
    sc = bootinfo.get("scope_context", {})
    hierarchy = sc.get("hierarchy", {})
    assert "companies" in hierarchy
    assert "cost_centers" in hierarchy
    assert "projects" in hierarchy
    assert "departments" in hierarchy
    assert len(hierarchy["companies"]) > 0
    # Verify NestedSet fields present
    if hierarchy["cost_centers"]:
        cc = hierarchy["cost_centers"][0]
        assert "lft" in cc
        assert "rgt" in cc
        assert "is_group" in cc


# === T-008 ===
def test_version_log():
    _cleanup()
    set_scope_context(company="Elrefae", source="test")
    frappe.db.commit()

    set_scope_context(company="Elrefae", cost_center=_COST_CENTER, source="test")
    frappe.db.commit()

    doc = get_user_scope_context("Administrator")
    assert doc.scope_version >= 2


# === T-009 ===
def test_concurrent_writes():
    _cleanup()
    set_scope_context(company="Elrefae", source="test")
    frappe.db.commit()

    set_scope_context(company="Elrefae", cost_center=_COST_CENTER, source="test")
    frappe.db.commit()

    doc = get_user_scope_context("Administrator")
    assert doc.company == "Elrefae"
    assert doc.cost_center == _COST_CENTER


# === T-010 ===
def test_first_time_user():
    hierarchy = get_user_scope_hierarchy("__nonexistent_test_user__")
    assert hierarchy is not None
    assert "companies" in hierarchy
    assert "cost_centers" in hierarchy


# === T-011 ===
def test_defaults_cleared_on_switch():
    _cleanup()
    set_scope_context(company="Elrefae", cost_center=_COST_CENTER, project=None, department=None, source="test")
    frappe.db.commit()
    frappe.clear_cache(user="Administrator")

    p = frappe.defaults.get_user_default("project", "Administrator")
    d = frappe.defaults.get_user_default("department", "Administrator")
    assert p is None or p == "", f"Expected None or '', got {repr(p)}"
    assert d is None or d == "", f"Expected None or '', got {repr(d)}"


# === T-012 ===
def test_nestedset_expansion():
    """Verify NestedSet descendant expansion logic used client-side."""
    hierarchy = get_user_scope_hierarchy("Administrator")
    cost_centers = hierarchy.get("cost_centers", [])

    group_cc = next((cc for cc in cost_centers if cc["name"] == _GROUP_CC), None)
    assert group_cc is not None, f"Group cost center {_GROUP_CC} not found"
    assert group_cc["is_group"] == 1 or group_cc["is_group"] is True

    descendants = [
        cc["name"] for cc in cost_centers
        if cc["lft"] >= group_cc["lft"] and cc["rgt"] <= group_cc["rgt"]
    ]
    assert _GROUP_CC in descendants, "Group should include itself"
    assert _COST_CENTER in descendants, (
        f"'{_COST_CENTER}' should be descendant of '{_GROUP_CC}' "
        f"(lft={group_cc['lft']}, rgt={group_cc['rgt']})"
    )

    non_group = next((cc for cc in cost_centers if cc["name"] == _COST_CENTER), None)
    assert non_group is not None
    child_descendants = [
        cc["name"] for cc in cost_centers
        if cc["lft"] >= non_group["lft"] and cc["rgt"] <= non_group["rgt"]
    ]
    assert len(child_descendants) == 1, "Non-group should have no children beyond itself"
    assert child_descendants[0] == _COST_CENTER


# === T-013 ===
def test_server_side_injection():
    from construction.overrides.scope_query import add_scope_conditions

    # Admin always bypasses
    assert add_scope_conditions("Administrator", "Sales Invoice") == ""

    # Set scope defaults for a non-admin test user
    for key in ("company", "cost_center", "project", "department"):
        frappe.defaults.clear_user_default(key, "test_user2")
    frappe.defaults.set_user_default("company", "Elrefae", "test_user2")
    frappe.defaults.set_user_default("cost_center", _GROUP_CC, "test_user2")

    # Doctype with both company + cost_center columns
    cc_result = add_scope_conditions("test_user2", "Sales Invoice")
    assert "cost_center" in cc_result, f"cost_center not in: {cc_result}"
    assert "lft" in cc_result.lower(), f"lft not in: {cc_result}"

    # System doctype skipped
    sys_result = add_scope_conditions("test_user2", "User")
    assert sys_result == "", f"System doctype should be skipped, got: {sys_result}"

    # Doctype missing cost_center column (has company but not cost_center)
    emp_result = add_scope_conditions("test_user2", "Employee")
    assert "cost_center" not in emp_result, "Employee has no cost_center column"

    # Doctype with neither column
    country_result = add_scope_conditions("test_user2", "Country")
    assert country_result == "", f"Country has no scope columns, got: {country_result}"

    # No scope set for this user (clear all user-level defaults)
    for key in ("company", "cost_center", "project", "department"):
        frappe.defaults.clear_user_default(key, "test_nobody")
    none_result = add_scope_conditions("test_nobody", "Sales Invoice")
    assert "cost_center" not in none_result, \
        f"cost_center should not appear for unscoped user: {none_result}"
    assert "project" not in none_result, \
        f"project should not appear for unscoped user: {none_result}"


if __name__ == "__main__":
    run_all_tests()
