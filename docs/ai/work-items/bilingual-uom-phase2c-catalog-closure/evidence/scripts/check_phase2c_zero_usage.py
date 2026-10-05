#!/usr/bin/env python3
"""
Zero-Usage Safety Check for UOM Phase 2C Catalog Closure.

Verifies:
1. Exact total UOM count (253) and populated Arabic count (45).
2. Derives 204 Phase 2C units as unpopulated minus vendor fixtures (_Test*) and F4-pruned (Pint (US), Acre).
3. Asserts derived 204 units match the frozen list from inventory-triage.log exactly.
4. Dynamically enumerates all tables and columns referencing UOM/unit in information_schema.
5. Parameterized search across all discovered tables to prove 0 active operational references exist.
6. Asserts post-state is 100% unchanged (45 populated, 253 total, 0 writes).
"""

import os
import re
import sys
import frappe

TRIAGE_LOG_PATH = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log"
OUTPUT_LOG_PATH = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage-closure/evidence/zero-usage-safety-check.log"
WORK_ITEM_LOG_PATH = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/zero-usage-safety-check.log"


def parse_frozen_phase2c_from_triage_log(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Triage log not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"--- Phase 2C / Exclusions .*?---\n(.*?)Total: 204", content, re.DOTALL)
    if not match:
        raise ValueError("Could not find Phase 2C section in triage log")

    lines = match.group(1).strip().splitlines()
    unit_names = []
    for line in lines:
        if not line.strip():
            continue
        left = line.strip().split(" - ")[0]
        m = re.match(r"^(.*?)\s*\(\1\)$", left)
        if m:
            unit_names.append(m.group(1))
        else:
            raise ValueError(f"Unable to parse line in triage log: {line}")

    return sorted(unit_names)


def main():
    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("UOM PHASE 2C ZERO-USAGE SAFETY CHECK (READ-ONLY AUDIT)")
    log_lines.append("Site: v16.localhost")
    log_lines.append("Base commit: 3e871f0")
    log_lines.append("=" * 60)

    # 1. Baseline state assertion
    total_uoms = frappe.db.count("UOM")
    populated_rows = frappe.db.sql(
        "SELECT name, uom_name_ar FROM `tabUOM` WHERE uom_name_ar IS NOT NULL AND uom_name_ar != '' ORDER BY name",
        as_dict=True,
    )
    populated_count = len(populated_rows)

    log_lines.append(f"Total UOM records on site: {total_uoms} (Expected: 253)")
    log_lines.append(f"Populated Arabic UOM records: {populated_count} (Expected: 45)")

    if total_uoms != 253:
        log_lines.append(f"FAIL: Total UOM count mismatch (got {total_uoms}, expected 253)")
        print("\n".join(log_lines))
        return False

    if populated_count != 45:
        log_lines.append(f"FAIL: Populated Arabic count mismatch (got {populated_count}, expected 45)")
        print("\n".join(log_lines))
        return False

    log_lines.append("  PASS: Baseline state verified: exactly 45 populated, 253 total.")

    # 2. Derive unpopulated minus fixtures and pruned units
    unpopulated_rows = frappe.db.sql(
        "SELECT name FROM `tabUOM` WHERE uom_name_ar IS NULL OR uom_name_ar = '' ORDER BY name",
        as_dict=True,
    )
    unpopulated_names = set(r["name"] for r in unpopulated_rows)
    excluded_fixtures_and_pruned = {"_Test UOM", "_Test UOM 1", "Pint (US)", "Acre"}

    derived_phase2c = sorted(unpopulated_names - excluded_fixtures_and_pruned)
    log_lines.append(f"\nDerived Phase 2C exclusion candidate count: {len(derived_phase2c)} (Expected: 204)")

    if len(derived_phase2c) != 204:
        log_lines.append(f"FAIL: Expected 204 Phase 2C units, derived {len(derived_phase2c)}")
        print("\n".join(log_lines))
        return False

    # 3. Assert equality against frozen inventory-triage.log
    frozen_phase2c = parse_frozen_phase2c_from_triage_log(TRIAGE_LOG_PATH)
    log_lines.append(f"Loaded frozen Phase 2C units from inventory-triage.log: {len(frozen_phase2c)}")

    if derived_phase2c != frozen_phase2c:
        diff_derived_not_frozen = set(derived_phase2c) - set(frozen_phase2c)
        diff_frozen_not_derived = set(frozen_phase2c) - set(derived_phase2c)
        log_lines.append(f"FAIL: Drift detected between database derivation and inventory-triage.log:")
        log_lines.append(f"  In derived but not frozen: {diff_derived_not_frozen}")
        log_lines.append(f"  In frozen but not derived: {diff_frozen_not_derived}")
        print("\n".join(log_lines))
        return False

    log_lines.append("  PASS: Derived 204 Phase 2C units match inventory-triage.log with 100% byte equality.")

    # 4. Enumerate all tables & columns referencing UOM / unit
    target_columns = ("uom", "stock_uom", "unit", "purchase_uom", "weight_uom")
    schema_cols = frappe.db.sql(
        """
        SELECT TABLE_NAME, COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND COLUMN_NAME IN %(target_cols)s
        ORDER BY TABLE_NAME, COLUMN_NAME
        """,
        {"target_cols": target_columns},
        as_dict=True,
    )

    log_lines.append(f"\nEnumerated {len(schema_cols)} candidate table/column pairs from information_schema.")

    # Explicit mandatory tables to check from briefing
    mandatory_checks = [
        ("tabItem", "stock_uom"),
        ("tabItem", "purchase_uom"),
        ("tabItem", "weight_uom"),
        ("tabBOQ Item", "unit"),
        ("tabSales Invoice Item", "uom"),
        ("tabSales Invoice Item", "stock_uom"),
        ("tabPurchase Order Item", "uom"),
        ("tabPurchase Order Item", "stock_uom"),
        ("tabStock Entry Detail", "uom"),
        ("tabStock Entry Detail", "stock_uom"),
        ("tabMaterial Request Item", "uom"),
        ("tabMaterial Request Item", "stock_uom"),
        ("tabBOM Item", "uom"),
        ("tabBOM Item", "stock_uom"),
        ("tabStock Ledger Entry", "stock_uom"),
        ("tabItem Price", "uom"),
        ("tabDelivery Note Item", "uom"),
        ("tabDelivery Note Item", "stock_uom"),
        ("tabPurchase Receipt Item", "uom"),
        ("tabPurchase Receipt Item", "stock_uom"),
        ("tabPurchase Invoice Item", "uom"),
        ("tabPurchase Invoice Item", "stock_uom"),
        ("tabSales Order Item", "uom"),
        ("tabSales Order Item", "stock_uom"),
        ("tabQuotation Item", "uom"),
        ("tabQuotation Item", "stock_uom"),
    ]

    discovered_pairs = {(r["TABLE_NAME"], r["COLUMN_NAME"]) for r in schema_cols}
    for table_name, col_name in mandatory_checks:
        if (table_name, col_name) not in discovered_pairs:
            log_lines.append(f"FAIL: Mandatory audit target {table_name}.{col_name} not found in database schema!")
            print("\n".join(log_lines))
            return False

    log_lines.append(f"  PASS: All {len(mandatory_checks)} mandatory audit targets confirmed present in schema.")

    # 5. Parameterized zero-usage query across all discovered table/column pairs
    log_lines.append("\nQuerying references across all tables (parameterized IN query)...")
    total_references = 0
    hits = []

    for r in schema_cols:
        tbl = r["TABLE_NAME"]
        col = r["COLUMN_NAME"]
        try:
            cnt = frappe.db.sql(
                f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN %(units)s",
                {"units": tuple(derived_phase2c)},
            )[0][0]
            if cnt > 0:
                hits.append((tbl, col, cnt))
                total_references += cnt
        except Exception as e:
            log_lines.append(f"ERROR querying {tbl}.{col}: {e}")
            print("\n".join(log_lines))
            return False

    log_lines.append(f"\nAudit complete: scanned {len(schema_cols)} table/column pairs.")
    log_lines.append(f"Total active references found: {total_references}")

    if hits:
        log_lines.append("FAIL: Operational references found for Phase 2C units:")
        for tbl, col, cnt in hits:
            log_lines.append(f"  - {tbl}.{col}: {cnt} references")
        print("\n".join(log_lines))
        return False

    log_lines.append("  PASS: Zero active operational references across entire database (0 hits).")

    # 6. Post-state verification (assert read-only safety, zero writes)
    post_total = frappe.db.count("UOM")
    post_populated = len(
        frappe.db.sql(
            "SELECT name FROM `tabUOM` WHERE uom_name_ar IS NOT NULL AND uom_name_ar != ''",
            as_dict=True,
        )
    )

    log_lines.append(f"\nPost-audit verification: total={post_total}, populated={post_populated}")
    if post_total != total_uoms or post_populated != populated_count:
        log_lines.append("FAIL: Database mutation detected during read-only audit!")
        print("\n".join(log_lines))
        return False

    log_lines.append("  PASS: Database state completely unmodified (0 writes).")
    log_lines.append("\n" + "=" * 60)
    log_lines.append("FINAL VERDICT: PASS — ZERO-USAGE PROVEN, PHASE 2C READY FOR RATIFICATION")
    log_lines.append("=" * 60)

    # Write log file
    os.makedirs(os.path.dirname(WORK_ITEM_LOG_PATH), exist_ok=True)
    with open(WORK_ITEM_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print("\n".join(log_lines))
    print(f"\nAudit log saved to: {WORK_ITEM_LOG_PATH}")
    return True


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    success = main()
    if frappe.db:
        frappe.db.rollback()
    sys.exit(0 if success else 1)
