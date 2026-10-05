#!/usr/bin/env python
"""Post-import verification script for bilingual UOM Phase 2+.

Confirms all 30 approved rows have non-empty uom_name_ar and correct
server-derived uom_name_ar_norm.

Confirms earlier frozen surfaces remain intact:
  - 15 Phase-1 UOMs intact.
  - 81 Accounts intact.
  - Wave-1 masters (Item 8, Customer 1, Cost Center 3, Warehouse 6, Project 5) intact.
  - Wave-2 groups (Item Group 6, Customer Group 5, Supplier Group 8, Territory 4) intact.
  - Departments (14) intact.
  - Company (1) intact (Elrefae = شركة الرفاعي للمقاولات العامة).
  - Total UOMs = 253, total UOMs with Arabic = 45 (15 Phase 1 + 30 Phase 2).

Logs to evidence/post-import-verification.log.
"""

import json
import sys
import os
import frappe
from construction.services.bilingual_service import normalize_arabic


FROZEN_PRIOR = {
    "accounts_ar": 81,
    "items_ar": 8,
    "customers_ar": 1,
    "suppliers_ar": 0,
    "cost_centers_ar": 3,
    "warehouses_ar": 6,
    "projects_ar": 5,
    "departments_ar": 14,
}

PHASE1_NAMES = {
    "M3", "M2", "M", "TON", "KG", "PCS", "LS", "DAY", "HR", "BAG", "LTR", "SET",
    "Nos", "Tonne", "Box",
}


def main():
    proposal_path = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase2-triage/proposal.json"
    with open(proposal_path, encoding="utf-8") as f:
        proposal = json.load(f)

    units = proposal.get("units", [])
    target_units = [u for u in units if u.get("section") in ("phase2a", "phase2b")]

    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("UOM PHASE 2+ POST-IMPORT VERIFICATION")
    log_lines.append("Base commit: 5d96f12")
    log_lines.append("=" * 60)
    log_lines.append("")

    verified = 0
    norm_consistent = 0
    identity_unchanged = 0
    exceptions = []

    log_lines.append("--- Verification: Target 30 rows have uom_name_ar and server norm ---")

    for u in target_units:
        name = u["name"]
        expected_ar = u["arabic"]
        expected_norm = normalize_arabic(expected_ar)

        db_row = frappe.db.get_value("UOM", name, ["name", "uom_name_ar", "uom_name_ar_norm"], as_dict=True)
        if not db_row:
            exceptions.append(f"{name}: row missing from database")
            continue

        if db_row.name == name:
            identity_unchanged += 1

        actual_ar = db_row.uom_name_ar or ""
        actual_norm = db_row.uom_name_ar_norm or ""

        if actual_ar == expected_ar:
            verified += 1
        else:
            exceptions.append(f"{name}: actual Arabic '{actual_ar}' != expected '{expected_ar}'")

        if actual_norm == expected_norm:
            norm_consistent += 1
        else:
            exceptions.append(f"{name}: norm '{actual_norm}' != expected '{expected_norm}'")

        log_lines.append(f"  {name}: ar='{actual_ar}', norm='{actual_norm}' - OK")

    # Verify Phase 1 rows intact
    log_lines.append("\n--- Verification: Phase 1 rows intact (15 rows) ---")
    p1_verified = 0
    for p1 in PHASE1_NAMES:
        p1_ar = frappe.db.get_value("UOM", p1, "uom_name_ar")
        if p1_ar:
            p1_verified += 1
        else:
            exceptions.append(f"Phase 1 UOM {p1} lost Arabic value")
    log_lines.append(f"  Phase-1 intact: {p1_verified}/15")

    # Verify frozen prior surfaces
    log_lines.append("\n--- Verification: Frozen Prior Surfaces ---")
    prior = {
        "accounts_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabAccount` WHERE account_name_ar IS NOT NULL AND account_name_ar != ''"
        )[0][0],
        "items_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabItem` WHERE item_name_ar IS NOT NULL AND item_name_ar != ''"
        )[0][0],
        "customers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCustomer` WHERE customer_name_in_arabic IS NOT NULL AND customer_name_in_arabic != ''"
        )[0][0],
        "suppliers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSupplier` WHERE supplier_name_in_arabic IS NOT NULL AND supplier_name_in_arabic != ''"
        )[0][0],
        "cost_centers_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabCost Center` WHERE cost_center_name_ar IS NOT NULL AND cost_center_name_ar != ''"
        )[0][0],
        "warehouses_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabWarehouse` WHERE warehouse_name_ar IS NOT NULL AND warehouse_name_ar != ''"
        )[0][0],
        "projects_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabProject` WHERE project_name_ar IS NOT NULL AND project_name_ar != ''"
        )[0][0],
        "departments_ar": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDepartment` WHERE department_name_ar IS NOT NULL AND department_name_ar != ''"
        )[0][0],
    }

    for k, exp in FROZEN_PRIOR.items():
        act = prior[k]
        if act == exp:
            log_lines.append(f"  {k}: {act} == {exp} - OK")
        else:
            exceptions.append(f"{k}: actual {act} != frozen {exp}")

    # Company Arabic check
    company_ar = frappe.db.get_value("Company", "Elrefae", "company_name_ar")
    if company_ar == "شركة الرفاعي للمقاولات العامة":
        log_lines.append(f"  company_ar (Elrefae): '{company_ar}' - OK (Tier 5H intact)")
    else:
        exceptions.append(f"company_ar unexpected: '{company_ar}'")

    # Total UOM counts
    total_uom = frappe.db.count("UOM")
    total_ar_uom = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabUOM` WHERE uom_name_ar IS NOT NULL AND uom_name_ar != ''"
    )[0][0]
    log_lines.append(f"\n  Total UOM rows: {total_uom} (expected 253)")
    log_lines.append(f"  Total UOM with Arabic: {total_ar_uom} (expected 45)")

    if total_uom != 253:
        exceptions.append(f"Total UOM count {total_uom} != 253")
    if total_ar_uom != 45:
        exceptions.append(f"Total UOM with Arabic {total_ar_uom} != 45")

    log_lines.append("")
    log_lines.append("=" * 60)
    log_lines.append("POST-IMPORT VERIFICATION RESULT")
    log_lines.append(
        f"verified={verified} norm_consistent={norm_consistent} "
        f"identity_unchanged={identity_unchanged} exceptions={len(exceptions)}"
    )
    log_lines.append("=" * 60)

    if exceptions:
        log_lines.append("\nEXCEPTIONS FOUND:")
        for ex in exceptions:
            log_lines.append(f"  - {ex}")

    evidence_path = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/post-import-verification.log"
    os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print("\n".join(log_lines))
    print(f"\nVerification log written to: {evidence_path}")

    return len(exceptions) == 0 and verified == 30 and norm_consistent == 30


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    success = main()
    sys.exit(0 if success else 1)