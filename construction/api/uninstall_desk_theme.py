"""
frappe_desk_theme Uninstall Process

Safely removes frappe_desk_theme after all features are replicated
in the Construction Theme system.

Usage:
  bench --site [site] execute construction.api.uninstall_desk_theme.execute
"""
import frappe
import os
import subprocess


def execute(dry_run=True):
    """Run the full uninstall process.
    
    Args:
        dry_run: If True, only audit and report. If False, actually uninstall.
    """
    print("=" * 60)
    print("frappe_desk_theme Uninstall Process")
    print("=" * 60)
    
    # Step 1: Dependency audit
    print("\n--- Step 1: Dependency Audit ---")
    refs = _audit_dependencies()
    if refs:
        print(f"\nFound {len(refs)} references to frappe_desk_theme:")
        for ref in refs[:20]:
            print(f"  {ref}")
        if len(refs) > 20:
            print(f"  ... and {len(refs) - 20} more")
        if not dry_run:
            print("\nABORTING: Resolve references before uninstalling.")
            return {"success": False, "reason": "active_references", "refs": refs}
    else:
        print("  No external references found. Safe to proceed.")
    
    # Step 2: Verify Construction Theme feature parity
    print("\n--- Step 2: Feature Parity Check ---")
    parity = _check_feature_parity()
    if not parity["ready"]:
        print(f"  Missing features: {parity['missing']}")
        if not dry_run:
            return {"success": False, "reason": "missing_features", "missing": parity["missing"]}
    else:
        print("  All features replicated. Ready to uninstall.")

    if dry_run:
        print("\n--- DRY RUN COMPLETE ---")
        print("Run with dry_run=False to actually uninstall.")
        return {"success": True, "dry_run": True, "refs": refs, "parity": parity}
    
    # Step 3: Backup
    print("\n--- Step 3: Creating Backup ---")
    try:
        bench_path = frappe.utils.get_bench_path()
        result = subprocess.run(
            ["bench", "--site", frappe.local.site, "backup"],
            cwd=bench_path, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("  Backup created successfully.")
        else:
            print(f"  Backup warning: {result.stderr[:200]}")
    except Exception as e:
        print(f"  Backup error: {e}. Proceeding anyway.")
    
    # Step 4: Uninstall
    print("\n--- Step 4: Uninstalling frappe_desk_theme ---")
    try:
        bench_path = frappe.utils.get_bench_path()
        result = subprocess.run(
            ["bench", "--site", frappe.local.site, "uninstall-app", "frappe_desk_theme", "--yes"],
            cwd=bench_path, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("  frappe_desk_theme uninstalled successfully.")
        else:
            print(f"  Uninstall error: {result.stderr[:500]}")
            return {"success": False, "reason": "uninstall_failed", "error": result.stderr}
    except Exception as e:
        print(f"  Uninstall error: {e}")
        return {"success": False, "reason": "uninstall_exception", "error": str(e)}
    
    # Step 5: Verify
    print("\n--- Step 5: Post-Uninstall Verification ---")
    _verify_post_uninstall()
    
    # Step 6: Cleanup orphaned records
    print("\n--- Step 6: Orphan Cleanup ---")
    _cleanup_orphans()
    
    print("\n" + "=" * 60)
    print("Uninstall complete!")
    print("=" * 60)
    return {"success": True}


def _audit_dependencies():
    """Scan all app directories for references to frappe_desk_theme."""
    refs = []
    bench_path = frappe.utils.get_bench_path()
    apps_dir = os.path.join(bench_path, "apps")
    
    for app_name in os.listdir(apps_dir):
        if app_name in ("frappe_desk_theme", ".git", "node_modules", "__pycache__"):
            continue
        app_path = os.path.join(apps_dir, app_name)
        if not os.path.isdir(app_path):
            continue
        for root, dirs, files in os.walk(app_path):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".pytest_cache")]
            for fname in files:
                if fname.endswith((".py", ".js", ".json", ".html")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", errors="ignore") as f:
                            content = f.read()
                        if "frappe_desk_theme" in content or "desk_theme" in content.lower():
                            rel = os.path.relpath(fpath, bench_path)
                            refs.append(rel)
                    except Exception:
                        pass
    return refs


def _check_feature_parity():
    """Check if Construction Theme has all features from frappe_desk_theme."""
    missing = []
    # Check Construction Theme exists with themes
    ct_count = frappe.db.count("Construction Theme", {"is_active": 1})
    if ct_count < 4:
        missing.append(f"Only {ct_count} active themes (need at least 4)")
    # Check Modern Theme Settings exists
    try:
        frappe.get_doc("Modern Theme Settings")
    except Exception:
        missing.append("Modern Theme Settings not configured")
    # Check theme API is working
    try:
        from construction.api.theme_api import get_effective_desk_theme
        result = get_effective_desk_theme("light")
        if not result.get("theme_name"):
            missing.append("Theme API not returning themes")
    except Exception as e:
        missing.append(f"Theme API error: {e}")
    return {"ready": len(missing) == 0, "missing": missing}


def _verify_post_uninstall():
    """Verify Construction Theme still works after uninstall."""
    try:
        from construction.api.theme_api import get_effective_desk_theme
        for mode in ("light", "dark"):
            result = get_effective_desk_theme(mode)
            print(f"  {mode} mode: theme={result.get('theme_name')}, source={result.get('source')}")
    except Exception as e:
        print(f"  Verification error: {e}")


def _cleanup_orphans():
    """Find and report orphaned records referencing desk_theme."""
    orphans = frappe.db.sql("""
        SELECT doctype, field, value FROM tabSingles 
        WHERE value LIKE '%%desk_theme%%' OR field LIKE '%%desk_theme%%'
    """, as_dict=True)
    if orphans:
        print(f"  Found {len(orphans)} orphaned Singles records:")
        for o in orphans:
            print(f"    {o.doctype}.{o.field} = {o.value}")
    else:
        print("  No orphaned records found.")
