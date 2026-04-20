# Uninstall frappe_desk_theme - Step-by-Step Guide

## Overview

This guide provides step-by-step instructions for safely uninstalling the `frappe_desk_theme` app after all its features have been replicated in the Construction Theme system.

## Prerequisites

- All Construction Theme features are implemented and tested
- Default light and dark themes are configured
- Login page CSS generation is working
- Feature toggles are functional
- Staging environment has been verified

## Step 1: Dependency Audit

Run the dependency audit script to identify any remaining references to `frappe_desk_theme`:

```bash
cd construction
python construction/scripts/audit_frappe_desk_theme.py ..
```

**Expected Output:**
```
✓ No references to frappe_desk_theme found!
Safe to proceed with uninstall.
```

**If references are found:**
1. Review the list of files
2. Remove or update references in those files
3. Re-run the audit until no references remain

## Step 2: Verify Construction Theme System

Before uninstalling, verify that the Construction Theme system is fully functional:

```bash
# Test default light theme
bench --site [site] console
>>> from construction.construction.doctype.construction_theme.construction_theme import ConstructionTheme
>>> theme = ConstructionTheme.get_default_for_mode("light")
>>> print(theme)

# Test default dark theme
>>> theme = ConstructionTheme.get_default_for_mode("dark")
>>> print(theme)

# Test CSS generation
>>> theme_doc = frappe.get_doc("Construction Theme", theme.name)
>>> css = theme_doc.generate_css_variables()
>>> print(len(css))  # Should be > 0
```

## Step 3: Create Bench Backup

Create a backup before proceeding:

```bash
bench backup --site [site]
```

This creates a backup in `sites/[site]/private/backups/`.

## Step 4: Remove frappe_desk_theme References from hooks.py

Check if there are any references in the construction app's hooks.py:

```bash
grep -i "frappe_desk_theme" construction/construction/hooks.py
```

If found, remove them. (Current version should have none.)

## Step 5: Uninstall the App

```bash
bench --site [site] uninstall-app frappe_desk_theme
```

**Expected Output:**
```
Uninstalling frappe_desk_theme...
✓ frappe_desk_theme uninstalled successfully
```

## Step 6: Clear Assets and Rebuild

```bash
bench build
```

This clears stale assets and rebuilds the asset pipeline.

## Step 7: Verify Uninstall

Verify that `frappe_desk_theme` is no longer installed:

```bash
bench list-apps | grep frappe_desk_theme
```

**Expected Output:** (empty - no output)

## Step 8: Verify Construction Theme Rendering

Test that themes render correctly post-uninstall:

```bash
bench --site [site] console
>>> from construction.api.theme_api import get_effective_desk_theme
>>> result = get_effective_desk_theme("light")
>>> print(result)
>>> result = get_effective_desk_theme("dark")
>>> print(result)
```

## Step 9: Database Cleanup

Query the database for orphaned records:

```bash
bench --site [site] console
>>> import frappe
>>> # Check for orphaned desk_theme references in tabSingles
>>> orphaned = frappe.db.sql("""
...     SELECT * FROM tabSingles 
...     WHERE doctype LIKE '%desk_theme%' OR field LIKE '%desk_theme%'
... """, as_dict=True)
>>> print(orphaned)

>>> # Check for custom fields referencing desk_theme
>>> custom_fields = frappe.db.sql("""
...     SELECT * FROM tabCustom Field 
...     WHERE fieldname LIKE '%desk_theme%' OR label LIKE '%desk_theme%'
... """, as_dict=True)
>>> print(custom_fields)
```

**If orphaned records are found:**
1. Document them for manual cleanup
2. Optionally delete them if they're no longer needed:
   ```bash
   frappe.db.delete("Custom Field", {"fieldname": "desk_theme_field"})
   frappe.db.commit()
   ```

## Step 10: Verify Login Page

Test the login page to ensure it renders correctly:

1. Log out of the site
2. Navigate to `/login`
3. Verify that the login page is styled correctly
4. Check browser console for any errors

## Step 11: Test Theme Switching

Test theme switching in the desk:

1. Log in to the site
2. Click the theme indicator in the navbar
3. Switch between Construction Light, Construction Dark, and Frappe themes
4. Verify that themes apply correctly
5. Verify that feature toggles work (if enabled)

## Step 12: Verify Feature Toggles

If feature toggles are enabled on any theme:

1. Switch to a theme with toggles enabled
2. Verify that the corresponding body classes are applied:
   - `ct-theme-hide-help`
   - `ct-theme-hide-search`
   - `ct-theme-hide-sidebar`
   - `ct-theme-hide-like-comment`
   - `ct-theme-mobile-card`
3. Verify that the UI elements are hidden/transformed as expected

## Rollback Procedure

If issues occur, rollback to the backup:

```bash
# Restore from backup
bench restore --site [site] --backup-path sites/[site]/private/backups/[backup-file]

# Reinstall frappe_desk_theme if needed
bench --site [site] install-app frappe_desk_theme
```

## Troubleshooting

### Issue: Login page is unstyled after uninstall

**Solution:**
1. Verify that `login_theme.css` exists at `sites/[site]/public/files/construction/css/login_theme.css`
2. Verify that `web_include_css` in hooks.py includes `/assets/construction/css/login_theme.css`
3. Run `bench build` to rebuild assets
4. Clear browser cache and reload

### Issue: Theme switching doesn't work

**Solution:**
1. Check browser console for JavaScript errors
2. Verify that `modern_theme_loader_v3.js` is loaded
3. Verify that the API endpoint `get_effective_desk_theme` is accessible
4. Check server logs for errors

### Issue: Feature toggles not working

**Solution:**
1. Verify that the theme has feature toggles enabled
2. Check that `applyFeatureToggles()` is being called in `modern_theme_loader_v3.js`
3. Verify that the CSS rules for feature toggles are present in `construction_theme_components.css`
4. Check browser console for errors

## Post-Uninstall Cleanup

After successful uninstall:

1. Remove `frappe_desk_theme` from any documentation
2. Update any internal references to use Construction Theme instead
3. Archive any custom CSS or configurations from `frappe_desk_theme`
4. Document the new Construction Theme system for future maintainers

## Verification Checklist

- [ ] Dependency audit shows no references
- [ ] Backup created successfully
- [ ] `frappe_desk_theme` uninstalled without errors
- [ ] `bench build` completed successfully
- [ ] `bench list-apps` does not include `frappe_desk_theme`
- [ ] Login page renders correctly
- [ ] Theme switching works
- [ ] Default light theme loads correctly
- [ ] Default dark theme loads correctly
- [ ] Feature toggles work (if enabled)
- [ ] No orphaned database records
- [ ] Browser console shows no errors
- [ ] All tests pass

## Support

If issues occur during uninstall:

1. Check the troubleshooting section above
2. Review server logs: `bench logs`
3. Check browser console for JavaScript errors
4. Restore from backup if necessary
5. Contact the development team

---

**Last Updated:** 2026-04-18
**Version:** 1.0
