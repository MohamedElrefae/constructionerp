#!/usr/bin/env python
"""Inventory export & triage script for bilingual UOM Phase 2+.

Reads all 253 UOM rows, confirms 15 Phase-1 rows intact,
extracts 236 candidate rows and groups them by Phase 2A / 2B / 2C buckets,
generates evidence/inventory-triage.log.

DO NOT modify Company, hooks.py, bilingual_service.py, bilingual_registry.json,
or run_bilingual_regression_matrix.sh — those are reserved for the concurrent lane.
"""

import frappe
import json
import hashlib
import sys
from collections import OrderedDict


def fetch_uom_rows():
    """Fetch all UOM rows from the site."""
    rows = frappe.get_all(
        "UOM",
        fields=["name", "uom_name", "uom_name_ar", "enabled", "category", "common_code", "symbol"],
        order_by="name",
    )
    return rows


def classify_uom(row, phase1_frozen, phase1_pruned):
    """Classify a UOM row into Phase 1, 2A, 2B, 2C, or disabled.

    Returns (category, reason).
    """
    name = row.name

    # Rule 1: vendor fixture (name starts with _Test) -> never translated
    if name.startswith("_Test"):
        return "vendor_fixture", "name starts with _Test (absolute fixture rule)"

    # Rule 2: Phase 1 frozen allowlist (12 app fixtures + 3 in-use)
    if name in phase1_frozen:
        return "phase1_frozen", "name in Phase 1 frozen allowlist"

    # Rule 3: F4-pruned units (Pint US, Acre) -> in_use, untranslated, Phase 2+ candidates
    if name in phase1_pruned:
        return "phase2c_pruned", "name F4-pruned (in_use, untranslated, Phase 2+ candidate)"

    # Rule 4: disabled rows
    if not row.enabled:
        return "disabled", "enabled = 0"

    # Rule 5: in-use (referenced by live Item.stock_uom or BOQ Item.unit)
    in_use_names = _get_in_use_names()
    if name in in_use_names:
        return "in_use", "referenced by live Item.stock_uom or BOQ Item.unit"

    # Rule 6: Phase 2A -> Priority Construction & Engineering Physical Units
    phase2a_names = _phase2a_unit_names()
    if name in phase2a_names:
        return "phase2a", "Priority Construction & Engineering Physical Unit"

    # Rule 7: Phase 2B -> Commercial, Packaging & Material Handling Units
    phase2b_names = _phase2b_unit_names()
    if name in phase2b_names:
        return "phase2b", "Commercial, Packaging & Material Handling Unit"

    # Rule 8: all remaining enabled, unused, non-fixture units -> Phase 2C Exclusions
    return "phase2c_exclusion", "Enabled unused vendor seed unit - Phase 2C Exclusion"


def _get_in_use_names():
    """Derive in-use UOM names from live Items and BOQs."""
    item_uoms = set(
        frappe.db.sql(
            "SELECT DISTINCT stock_uom FROM tabItem "
            "WHERE stock_uom IS NOT NULL AND stock_uom != ''",
            pluck=True,
        )
    )
    boq_units = set(
        frappe.db.sql(
            "SELECT DISTINCT unit FROM `tabBOQ Item` "
            "WHERE unit IS NOT NULL AND unit != ''",
            pluck=True,
        )
    )
    return item_uoms | boq_units


def _phase2a_unit_names():
    """Return the frozen set of Phase 2A unit names (Priority Construction & Engineering)."""
    return frozenset([
        # Dimensional / Linear
        "Millimeter", "Centimeter", "Meter", "Kilometer",
        "Inch", "Foot", "Yard",
        # Area & Volume
        "Square Meter", "Square Foot", "Square Yard",
        "Cubic Centimeter", "Cubic Foot", "Cubic Yard", "Cubic Meter",
        "Gallon", "Quart", "Pint", "Liter", "Milliliter",
        # Mass & Density
        "Gram", "Milligram", "Kilogram", "Tonne", "Pound", "Ounce",
        # MEP / Electrical / Energy
        "Kilowatt", "Watt", "Horsepower", "Volt", "Ampere", "Joule", "Kilojoule", "Kilowatt-hour",
        "Ohm", "Siemens", "Farad", "Henry", "Tesla", "Weber",
        # Time
        "Minute", "Second", "Hour", "Day", "Week", "Month", "Year",
    ])


def _phase2b_unit_names():
    """Return the frozen set of Phase 2B unit names (Commercial, Packaging & Material Handling)."""
    return frozenset([
        "Roll", "Bundle", "Carton", "Packet", "Pallet",
        "Pair", "Dozen", "Ream", "Container", "Sheet", "Coil", "Pack", "Drum", "Box",
    ])


def main():
    """Main entry point: export inventory, classify, and generate triage log."""
    # Phase 1 frozen allowlist (from Tier 5F completion)
    phase1_frozen = frozenset([
        "M3", "M2", "M", "TON", "KG", "PCS", "LS", "DAY", "HR", "BAG", "LTR", "SET",
        "Nos", "Tonne", "Box",
    ])

    # F4-pruned units (owner decision from Tier 5F)
    phase1_pruned = frozenset(["Pint (US)", "Acre"])

    # Fetch all UOM rows
    rows = fetch_uom_rows()
    total = len(rows)
    print("Total UOM rows fetched: {}".format(total))

    # Classification buckets
    buckets = {
        "phase1_frozen": [],
        "vendor_fixture": [],
        "phase2c_pruned": [],
        "disabled": [],
        "in_use": [],
        "phase2a": [],
        "phase2b": [],
        "phase2c_exclusion": [],
    }

    for row in rows:
        category, reason = classify_uom(row, phase1_frozen, phase1_pruned)
        buckets[category].append({
            "name": row.name,
            "english_name": row.uom_name or row.name,
            "category": row.category or "",
            "enabled": row.enabled,
            "reason": reason,
        })

    # Log results
    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("UOM PHASE 2+ TRIAGE INVENTORY EXPORT")
    log_lines.append("Base commit: 5d96f12")
    log_lines.append("Total UOM rows: {}".format(total))
    log_lines.append("=" * 60)
    log_lines.append("")

    # Phase 1 summary
    pf = buckets["phase1_frozen"]
    vf = buckets["vendor_fixture"]
    pp = buckets["phase2c_pruned"]
    dis = buckets["disabled"]
    iu = buckets["in_use"]
    p2a = buckets["phase2a"]
    p2b = buckets["phase2b"]
    p2c = buckets["phase2c_exclusion"]

    log_lines.append("--- Phase 1 Frozen (15 rows) ---")
    for r in pf:
        log_lines.append("  {} ({}) - {}".format(r["name"], r["english_name"], r["reason"]))
    log_lines.append("Total: {}".format(len(pf)))

    log_lines.append("")
    log_lines.append("--- Vendor Fixtures (2 rows, never translated) ---")
    for r in vf:
        log_lines.append("  {} ({}) - {}".format(r["name"], r["english_name"], r["reason"]))
    log_lines.append("Total: {}".format(len(vf)))

    log_lines.append("")
    log_lines.append("--- F4-Pruned (2 rows: Pint (US), Acre) ---")
    for r in pp:
        log_lines.append("  {} ({}) - {}".format(r["name"], r["english_name"], r["reason"]))
    log_lines.append("Total: {}".format(len(pp)))

    log_lines.append("")
    log_lines.append("--- Disabled Rows ---")
    for r in dis:
        log_lines.append("  {} ({}) - enabled={}".format(r["name"], r["english_name"], r["enabled"]))
    log_lines.append("Total: {}".format(len(dis)))

    log_lines.append("")
    log_lines.append("--- In-Use Units (non-fixture, live references) ---")
    for r in iu:
        log_lines.append("  {} ({}) - referenced by Item or BOQ".format(r["name"], r["english_name"]))
    log_lines.append("Total: {}".format(len(iu)))

    log_lines.append("")
    log_lines.append("--- Phase 2A - Priority Construction & Engineering Physical Units ---")
    for r in p2a:
        log_lines.append("  {} ({}) - {}".format(r["name"], r["english_name"], r["reason"]))
    log_lines.append("Total: {} (target: 30-45)".format(len(p2a)))

    log_lines.append("")
    log_lines.append("--- Phase 2B - Commercial, Packaging & Material Handling Units ---")
    for r in p2b:
        log_lines.append("  {} ({}) - {}".format(r["name"], r["english_name"], r["reason"]))
    log_lines.append("Total: {} (target: 20-30)".format(len(p2b)))

    log_lines.append("")
    log_lines.append("--- Phase 2C / Exclusions (~160+ rows) ---")
    for r in p2c:
        log_lines.append("  {} ({}) - {}".format(r["name"], r["english_name"], r["reason"]))
    log_lines.append("Total: {} (Phase 2C Exclusion - no Arabic values drafted)".format(len(p2c)))

    log_lines.append("")
    log_lines.append("=" * 60)
    log_lines.append("TRIAGE SUMMARY")
    log_lines.append("Phase 1 Frozen:        {} / 15".format(len(pf)))
    log_lines.append("Vendor Fixtures:       {} / 2 (never translated)".format(len(vf)))
    log_lines.append("F4-Pruned:             {} rows (Phase 2+ candidates)".format(len(pp)))
    log_lines.append("Disabled:              {} ".format(len(dis)))
    log_lines.append("In-Use:                {}".format(len(iu)))
    log_lines.append("Phase 2A:              {} / (30-45)".format(len(p2a)))
    log_lines.append("Phase 2B:              {} / (20-30)".format(len(p2b)))
    log_lines.append("Phase 2C Exclusions:   {} / (160+)".format(len(p2c)))
    log_lines.append("=" * 60)

    # Write evidence log
    evidence_path = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log"
    with open(evidence_path, "w") as f:
        f.write("\n".join(log_lines))

    print("\n".join(log_lines))
    print("\nTriage log written to: {}".format(evidence_path))

    # Verify Phase 1 frozen match
    expected_phase1 = {"M3", "M2", "M", "TON", "KG", "PCS", "LS", "DAY", "HR", "BAG", "LTR", "SET", "Nos", "Tonne", "Box"}
    actual_phase1 = {r["name"] for r in pf}
    if actual_phase1 == expected_phase1:
        result_str = "PHASE1_FROZEN_MATCH YES - derived allowlist matches frozen literal exactly."
    else:
        missing = expected_phase1 - actual_phase1
        extra = actual_phase1 - expected_phase1
        result_str = "PHASE1_FROZEN_MATCH FAIL - missing: {}, extra: {}".format(missing, extra)

    with open(evidence_path, "a") as f:
        f.write("\n" + result_str)

    # Print final result lines
    print("\nPHASE1_FROZEN_MATCH: {}".format("YES" if actual_phase1 == expected_phase1 else "FAIL"))
    print("PRUNED_BY_OWNER: {} rows (Pint (US), Acre)".format(len(pp)))


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    main()
    if frappe.db:
        frappe.db.rollback()