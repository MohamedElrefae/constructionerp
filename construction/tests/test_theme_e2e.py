"""
End-to-End Test Suite for Phase 2 Theme System
Run via: bench --site <site> execute construction.tests.test_theme_e2e.run_all_tests
"""

import frappe
import json


def run_all_tests():
    """Run all E2E tests and print results."""
    print("=" * 60)
    print("PHASE 2 THEME SYSTEM - END-TO-END TEST SUITE")
    print("=" * 60)

    tests = [
        ("Database Structure", test_database_structure),
        ("Migration Verification", test_migration),
        ("API Endpoints", test_api_endpoints),
        ("CSS Generation", test_css_generation),
        ("Theme Resolution", test_theme_resolution),
        ("Cache System", test_cache_system),
        ("Validation Rules", test_validation),
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

    print("  ✓ Table structure verified")


def test_migration():
    """Test that all 4 Phase 1 themes were migrated."""
    expected_themes = ['Light', 'Dark', 'Construction Light', 'Construction Dark']

    for theme_name in expected_themes:
        exists = frappe.db.exists("Construction Theme", theme_name)
        assert exists, f"Theme '{theme_name}' not found after migration"

    # Check system theme flags
    for theme_name in expected_themes:
        is_system = frappe.db.get_value("Construction Theme", theme_name, "is_system_theme")
        assert is_system == 1, f"Theme '{theme_name}' should have is_system_theme=1"

    # Check default flags
    light_default = frappe.db.get_value("Construction Theme", "Light", "is_default_light")
    dark_default = frappe.db.get_value("Construction Theme", "Dark", "is_default_dark")

    assert light_default == 1, "Light theme should be default light"
    assert dark_default == 1, "Dark theme should be default dark"

    print(f"  ✓ All {len(expected_themes)} themes migrated with correct flags")


def test_api_endpoints():
    """Test that all API endpoints are accessible."""
    from construction.api import theme_api

    # Test list_available_themes
    result = theme_api.list_available_themes()
    assert result.get("success") == True, "list_available_themes failed"
    assert len(result.get("themes", [])) >= 4, "Should have at least 4 themes"

    # Test get_theme_css
    result = theme_api.get_theme_css("Construction Dark")
    assert "css" in result, "get_theme_css should return css"
    assert len(result["css"]) > 0, "CSS should not be empty"

    # Test get_effective_desk_theme
    result = theme_api.get_effective_desk_theme("dark")
    assert "theme_name" in result, "get_effective_desk_theme should return theme_name"
    assert "mode" in result, "get_effective_desk_theme should return mode"
    assert "is_construction" in result, "get_effective_desk_theme should return is_construction"

    # Test preview_theme
    result = theme_api.preview_theme(
        temporary=True,
        theme_name="Test",
        theme_type="Custom Light",
        accent_primary="#FF0000",
        navbar_bg="#FFFFFF",
        sidebar_bg="#F0F0F0",
        surface_bg="#FFFFFF",
        body_bg="#F5F5F5",
        text_primary="#000000"
    )
    assert "css" in result, "preview_theme should return css"

    print("  ✓ All 4 API endpoints working")


def test_css_generation():
    """Test that CSS is generated correctly."""
    # Get Construction Dark theme
    theme_doc = frappe.get_doc("Construction Theme", "Construction Dark")
    css = theme_doc.generate_css()

    # Check CSS contains expected patterns
    assert "html[data-modern-theme=\"Construction Dark\"]" in css, "Should have theme selector"
    assert ".navbar" in css, "Should have navbar styles"
    assert ".btn-primary" in css, "Should have button styles"
    assert "#4CAF50" in css, "Should contain accent color"
    assert "#1a3a1e" in css, "Should contain navbar background"

    # Check it's not just empty
    assert len(css) > 500, "CSS should be substantial (>500 chars)"

    print(f"  ✓ CSS generation working ({len(css)} chars generated)")


def test_theme_resolution():
    """Test theme resolution logic."""
    from construction.api.theme_api import get_effective_desk_theme

    # Test with light mode
    result = get_effective_desk_theme("light")
    assert result["mode"] == "light", "Should return light mode"
    assert result["needs_css_injection"] in [True, False], "Should indicate CSS injection need"

    # Test with dark mode
    result = get_effective_desk_theme("dark")
    assert result["mode"] == "dark", "Should return dark mode"

    # Test without parameter (should use user preference)
    result = get_effective_desk_theme()
    assert "mode" in result, "Should return mode even without parameter"

    print("  ✓ Theme resolution working for light/dark/no-param")


def test_cache_system():
    """Test that caching is working."""
    # Clear any existing cache
    frappe.cache().delete_value("theme_css:Construction Dark")

    # Generate CSS (should not be cached)
    theme_doc = frappe.get_doc("Construction Theme", "Construction Dark")
    css1 = theme_doc.generate_css()

    # Check cache was set
    cached = frappe.cache().get_value("theme_css:Construction Dark")
    assert cached is not None, "CSS should be cached after generation"
    assert cached == css1, "Cached CSS should match generated CSS"

    # Generate again (should use cache)
    css2 = theme_doc.generate_css()
    assert css1 == css2, "Second generation should return same CSS"

    # Clear cache
    frappe.cache().delete_value("theme_css:Construction Dark")
    cached = frappe.cache().get_value("theme_css:Construction Dark")
    assert cached is None, "Cache should be cleared"

    print("  ✓ Cache system working (set, get, clear)")


def test_validation():
    """Test validation rules."""
    # Test contrast ratio calculation
    theme = frappe.new_doc("Construction Theme")
    theme.theme_name = "_Test Contrast"
    theme.theme_type = "Custom Light"
    theme.accent_primary = "#FFFFFF"  # White on white (bad contrast)
    theme.surface_bg = "#FFFFFF"
    theme.navbar_bg = "#FFFFFF"
    theme.sidebar_bg = "#F0F0F0"
    theme.body_bg = "#F5F5F5"
    theme.text_primary = "#000000"

    # Calculate contrast
    theme._calculate_contrast_ratio()
    assert theme.contrast_ratio is not None, "Contrast ratio should be calculated"
    assert theme.contrast_ratio < 2.0, "White on white should have low contrast"

    # Test hex validation
    assert theme._is_valid_hex_color("#FF0000") == True, "Valid hex should pass"
    assert theme._is_valid_hex_color("#FFF") == True, "3-char hex should pass"
    assert theme._is_valid_hex_color("not-a-color") == False, "Invalid hex should fail"
    assert theme._is_valid_hex_color("") == True, "Empty should pass (optional)"

    print("  ✓ Validation rules working (contrast, hex colors)")


def print_browser_tests():
    """Print tests that should be run in browser."""
    print("\n" + "=" * 60)
    print("BROWSER CONSOLE TESTS (Run these in browser dev tools)")
    print("=" * 60)

    tests = """
// Test 1: Verify v3 loader loaded
console.log("Loader version:", ModernThemeLoader.version);
// Expected: "6.0"

// Test 2: Check if API-driven theme loaded
currentTheme = ModernThemeLoader.getCurrentTheme();
console.log("Current theme:", currentTheme);
// Expected: {theme: "Construction Dark", mode: "dark", isConstruction: true}

// Test 3: Check if CSS was injected
cssElement = document.getElementById("theme-css-construction-dark");
console.log("CSS element exists:", !!cssElement);
console.log("CSS length:", cssElement ? cssElement.textContent.length : 0);
// Expected: true, > 500

// Test 4: Check server-side persistence (no localStorage)
localStorage.getItem("construction_theme");
// Expected: null (should be empty - we don't use localStorage anymore)

// Test 5: API test
frappe.call({method: "construction.api.theme_api.list_available_themes",
  callback: (r) => console.log("Themes:", r.message.themes.length)
});
// Expected: 4 or more themes

// Test 6: Navbar indicator
indicator = document.getElementById("modern-theme-indicator");
console.log("Navbar indicator exists:", !!indicator);
// Expected: true
    """
    print(tests)


def print_manual_tests():
    """Print manual UI tests."""
    print("\n" + "=" * 60)
    print("MANUAL UI TESTS")
    print("=" * 60)

    tests = """
1. Navigate to: Construction > Construction Theme
   ✓ Should see 4 themes listed (Light, Dark, Construction Light, Construction Dark)

2. Click on "Construction Dark"
   ✓ Should open form with all color fields populated
   ✓ Should see green colors (#4CAF50, #1a3a1e)

3. Click "Preview Theme" button
   ✓ Should open preview dialog
   ✓ Should see rendered preview with correct colors

4. Edit accent_primary color to red (#FF0000)
   ✓ Should see color swatches update
   ✓ Save should work without errors

5. Open Theme Switcher (top-right user menu)
   ✓ Should see 4 themes with emoji icons
   ✓ Switching themes should work
   ✓ Navbar should update color immediately

6. Refresh page after theme switch
   ✓ Theme should persist (server-side)
   ✓ No flash of wrong theme during load

7. Check browser console
   ✓ Should see "[Modern Theme] LOADER v6.0"
   ✓ No red error messages from theme system
    """
    print(tests)


if __name__ == "__main__":
    result = run_all_tests()
    print_browser_tests()
    print_manual_tests()
