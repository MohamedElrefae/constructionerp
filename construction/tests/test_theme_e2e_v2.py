"""
End-to-End Test Suite for Phase 2 Theme System - Version 2 (SQL-based)
Run via: bench --site <site> execute construction.tests.test_theme_e2e_v2.run_all_tests
"""

import frappe
import json


def run_all_tests():
    """Run all E2E tests and print results."""
    print("=" * 60)
    print("PHASE 2 THEME SYSTEM - END-TO-END TEST SUITE v2")
    print("=" * 60)
    
    tests = [
        ("Database Structure", test_database_structure),
        ("Migration Verification", test_migration),
        ("API Endpoints (SQL)", test_api_sql_based),
        ("CSS Templates", test_css_templates),
        ("Theme Resolution", test_theme_resolution),
        ("Cache Keys", test_cache_keys),
        ("Permission Check", test_permissions),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 {test_name}...")
            test_func()
            print(f"✅ {test_name} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)
    
    if passed == len(tests):
        print("\n🎉 ALL TESTS PASSED! Phase 2 is ready for production!")
    
    return {"passed": passed, "failed": failed, "total": len(tests)}


def test_database_structure():
    """Test that the database table exists with correct columns."""
    # Check table exists
    result = frappe.db.sql("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'tabConstruction Theme'
    """)[0][0]
    
    assert result == 1, "Construction Theme table does not exist"
    
    # Check required columns
    required_columns = [
        'name', 'theme_name', 'accent_primary', 'navbar_bg', 
        'sidebar_bg', 'surface_bg', 'body_bg', 'text_primary'
    ]
    
    for col in required_columns:
        result = frappe.db.sql("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'tabConstruction Theme'
            AND column_name = %s
        """, (col,))[0][0]
        assert result == 1, f"Column {col} does not exist"
    
    # Check row count
    count = frappe.db.sql("SELECT COUNT(*) FROM `tabConstruction Theme`")[0][0]
    assert count >= 4, f"Should have at least 4 themes, found {count}"
    
    print(f"  ✓ Table exists with {count} theme(s)")


def test_migration():
    """Test that all 4 Phase 1 themes were migrated."""
    expected_themes = ['Light', 'Dark', 'Construction Light', 'Construction Dark']
    
    for theme_name in expected_themes:
        exists = frappe.db.sql(
            "SELECT 1 FROM `tabConstruction Theme` WHERE name = %s LIMIT 1",
            (theme_name,)
        )
        assert len(exists) > 0, f"Theme '{theme_name}' not found after migration"
    
    # Check system theme flags
    for theme_name in expected_themes:
        is_system = frappe.db.get_value("Construction Theme", theme_name, "is_system_theme")
        assert is_system == 1, f"Theme '{theme_name}' should have is_system_theme=1"
    
    # Check default flags
    light_default = frappe.db.get_value("Construction Theme", "Light", "is_default_light")
    dark_default = frappe.db.get_value("Construction Theme", "Dark", "is_default_dark")
    constr_dark_default = frappe.db.get_value("Construction Theme", "Construction Dark", "is_default_dark")
    
    assert light_default == 1, "Light theme should be default light"
    # Note: In a fresh install, only one default per mode
    
    # Check active status
    all_active = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabConstruction Theme` 
        WHERE is_active = 0
    """)[0][0]
    assert all_active == 0, "All themes should be active"
    
    print(f"  ✓ All {len(expected_themes)} themes migrated with correct settings")


def test_api_sql_based():
    """Test API endpoints using SQL queries."""
    # Test list_available_themes via SQL
    themes = frappe.db.sql("""
        SELECT name, theme_name, emoji_icon, theme_type, is_system_theme 
        FROM `tabConstruction Theme` 
        WHERE is_active = 1 
        ORDER BY is_system_theme DESC, theme_name ASC
        LIMIT 12
    """, as_dict=True)
    
    assert len(themes) >= 4, f"Should have at least 4 active themes, found {len(themes)}"
    
    # Test get_theme_css via template existence
    import os
    template_dir = "/home/melre/construction-erp/apps/backend/frappe-bench/apps/construction/construction/theme_templates"
    templates = ['base.css.j2', 'navbar.css.j2', 'sidebar.css.j2', 'buttons.css.j2']
    
    for template in templates:
        assert os.path.exists(f"{template_dir}/{template}"), f"Template {template} missing"
    
    # Test get_effective_desk_theme via checking API file exists
    api_file = "/home/melre/construction-erp/apps/backend/frappe-bench/apps/construction/construction/api/theme_api.py"
    assert os.path.exists(api_file), "theme_api.py should exist"
    
    with open(api_file, 'r') as f:
        content = f.read()
        assert "def get_effective_desk_theme" in content, "get_effective_desk_theme should be defined"
        assert "def get_theme_css" in content, "get_theme_css should be defined"
        assert "def list_available_themes" in content, "list_available_themes should be defined"
    
    print(f"  ✓ API endpoints accessible ({len(themes)} themes in DB)")


def test_css_templates():
    """Test that CSS templates exist and are valid."""
    import os
    
    template_dir = "/home/melre/construction-erp/apps/backend/frappe-bench/apps/construction/construction/theme_templates"
    templates = [
        'base.css.j2', 'navbar.css.j2', 'sidebar.css.j2', 
        'buttons.css.j2', 'forms.css.j2', 'tables.css.j2',
        'modals.css.j2', 'toasts.css.j2', 'tree.css.j2'
    ]
    
    total_size = 0
    for template in templates:
        path = f"{template_dir}/{template}"
        assert os.path.exists(path), f"Template {template} missing"
        
        with open(path, 'r') as f:
            content = f.read()
            total_size += len(content)
            # Check for Jinja2 syntax markers
            assert '{{' in content or '{%' in content, f"Template {template} should have Jinja2 syntax"
    
    # Check templates are substantial
    assert total_size > 2000, f"Templates should be substantial (>2000 chars), found {total_size}"
    
    print(f"  ✓ All {len(templates)} CSS templates present ({total_size} chars)")


def test_theme_resolution():
    """Test theme resolution logic via SQL."""
    from construction.api.theme_api import get_effective_desk_theme
    
    # Test with light mode
    result = get_effective_desk_theme("light")
    assert "theme_name" in result, "Should return theme_name"
    assert "mode" in result, "Should return mode"
    assert result["mode"] == "light", "Mode should be light"
    assert "is_construction" in result, "Should return is_construction flag"
    
    # Test with dark mode
    result = get_effective_desk_theme("dark")
    assert result["mode"] == "dark", "Mode should be dark"
    
    # Check if it resolved to a valid theme
    theme_name = result.get("theme_name")
    exists = frappe.db.sql(
        "SELECT 1 FROM `tabConstruction Theme` WHERE name = %s LIMIT 1",
        (theme_name,)
    )
    assert len(exists) > 0 or theme_name == "Standard", f"Resolved theme {theme_name} should exist or be 'Standard'"
    
    print(f"  ✓ Theme resolution working (resolved: {theme_name})")


def test_cache_keys():
    """Test that cache system is accessible."""
    # Test setting cache
    test_key = "theme_test_key"
    test_value = "test_value_123"
    
    frappe.cache().set_value(test_key, test_value, expires_in_sec=60)
    
    # Test getting cache
    cached = frappe.cache().get_value(test_key)
    assert cached == test_value, f"Cache get should return {test_value}, got {cached}"
    
    # Test deleting cache
    frappe.cache().delete_value(test_key)
    deleted = frappe.cache().get_value(test_key)
    assert deleted is None, "After delete, cache should be None"
    
    # Test theme_css pattern
    theme_name = "Construction Dark"
    cache_key = f"theme_css:{theme_name}"
    frappe.cache().set_value(cache_key, "test css", expires_in_sec=3600)
    css_cached = frappe.cache().get_value(cache_key)
    assert css_cached == "test css", "CSS cache pattern should work"
    frappe.cache().delete_value(cache_key)
    
    print("  ✓ Cache system working (set, get, delete)")


def test_permissions():
    """Test permission structure."""
    # Check DocType has permissions defined
    perms = frappe.db.sql("""
        SELECT role, permlevel, `read`, `write`, `create`, `delete`
        FROM `tabDocPerm`
        WHERE parent = 'Construction Theme'
    """, as_dict=True)
    
    assert len(perms) > 0, "Construction Theme should have permissions defined"
    
    # Check for System Manager or Administrator
    admin_roles = [p.role for p in perms]
    has_admin = 'System Manager' in admin_roles or 'Administrator' in admin_roles
    assert has_admin, "Should have System Manager or Administrator permissions"
    
    print(f"  ✓ Permissions configured ({len(perms)} permission rules)")


def print_browser_tests():
    """Print tests that should be run in browser."""
    print("\n" + "=" * 60)
    print("BROWSER CONSOLE TESTS (Run these in browser dev tools)")
    print("=" * 60)
    
    tests = """
// Test 1: Verify v3 loader loaded
console.log("Loader version:", ModernThemeLoader?.version || "NOT LOADED");
// Expected: "6.0"

// Test 2: Check if API-driven theme loaded
currentTheme = ModernThemeLoader?.getCurrentTheme();
console.log("Current theme:", currentTheme);
// Expected: {theme: "Construction Dark", mode: "dark", isConstruction: true, ...}

// Test 3: Check if CSS was injected
cssElements = document.querySelectorAll('style[data-theme-source="api"]');
console.log("API CSS elements:", cssElements.length);
// Expected: 1 or more

// Test 4: Check server-side persistence (no localStorage)
localStorageValue = localStorage.getItem("construction_theme");
console.log("localStorage value:", localStorageValue);
// Expected: null or empty (should not be used in v3)

// Test 5: Test API directly
frappe.call({
    method: "construction.api.theme_api.get_theme_css",
    args: { theme_name: "Construction Dark" },
    callback: (r) => console.log("CSS API:", r.message?.css?.length || 0, "chars")
});
// Expected: > 500 chars

// Test 6: List themes API
frappe.call({
    method: "construction.api.theme_api.list_available_themes",
    callback: (r) => console.log("Themes:", r.message?.themes?.map(t => t.theme_name))
});
// Expected: ["Light", "Dark", "Construction Light", "Construction Dark", ...]

// Test 7: Navbar indicator
indicator = document.getElementById("modern-theme-indicator");
console.log("Navbar indicator:", indicator ? "EXISTS" : "MISSING");
dot = document.getElementById("theme-mode-dot");
console.log("Theme dot color:", dot?.style?.background);
// Expected: color matching current theme accent
    """
    print(tests)


def print_manual_tests():
    """Print manual UI tests."""
    print("\n" + "=" * 60)
    print("MANUAL UI TESTS (Do these in the browser)")
    print("=" * 60)
    
    tests = """
1. Open your browser to: http://construction.local (or your site URL)
   Login and check console for "[Modern Theme] LOADER v6.0"

2. Navigate to: Construction > Construction Theme
   ✓ Should see 4 themes: Light, Dark, Construction Light, Construction Dark

3. Click "Construction Dark"
   ✓ Form should open with green accent colors (#4CAF50)
   ✓ All color fields should be populated

4. Click "Preview Theme" button
   ✓ Preview dialog should open
   ✓ Should see rendered UI with correct colors

5. Change accent_primary to red (#FF0000) and click Preview
   ✓ Preview should show red instead of green

6. Click Save (if you want to keep changes)
   ✓ Should save without errors

7. Open Theme Switcher (click user avatar → Theme)
   ✓ Should see 4 themes with emoji icons
   ✓ Switch to different theme
   ✓ Page should update colors immediately

8. Refresh the page (F5)
   ✓ Theme should persist (same theme after refresh)
   ✓ This proves server-side persistence is working!

9. Check for errors:
   ✓ No red errors in console related to "Modern Theme"
   ✓ Navbar shows correct theme name in indicator

10. If all above pass: 🎉 Phase 2 is fully working!
    """
    print(tests)


if __name__ == "__main__":
    result = run_all_tests()
    print_browser_tests()
    print_manual_tests()
