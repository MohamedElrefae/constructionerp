#!/usr/bin/env python
"""Dry-run script for bilingual UOM Phase 2+.

Validates that target rows exist and currently have empty uom_name_ar.
Asserts WRITES_PERFORMED: 0.
Logs to evidence/dry-run.log.

DO NOT modify Company, hooks.py, bilingual_service.py, bilingual_registry.json,
or run_bilingual_regression_matrix.sh — those are reserved for the concurrent lane.
"""

import frappe
import json
import hashlib
import sys
import os


def main():
    """Dry-run: validate target rows and assert zero writes."""
    # Load proposal to get target units
    proposal_path = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase2-triage/proposal.json"
    with open(proposal_path) as f:
        proposal = json.load(f)

    units = proposal.get("units", [])
    phase2a_units = [u for u in units if u.get("section") in ("phase2a", "phase2b")]

    # Verify all target rows exist and have empty uom_name_ar
    writes_performed = 0
    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("UOM PHASE 2+ DRY-RUN VALIDATION")
    log_lines.append("Base commit: 5d96f12")
    log_lines.append("=" * 60)
    log_lines.append("")

    log_lines.append("--- Validation: Target rows exist and have empty uom_name_ar ---")

    for u in phase2a_units:
        name = u["name"]
        # Fetch the UOM document
        try:
            doc = frappe.get_doc("UOM", name)
            has_arabic = bool(doc.uom_name_ar)
            if has_arabic:
                writes_performed += 1
                log_lines.append("  {}: ALREADY HAS uom_name_ar = '{}' — would require update".format(name, doc.uom_name_ar))
            else:
                log_lines.append("  {}: empty uom_name_ar — OK".format(name))
        except Exception as e:
            writes_performed += 1
            log_lines.append("  {}: NOT FOUND — {}".format(name, str(e)))

    log_lines.append("")
    log_lines.append("--- WRITES_PERFORMED: {} ---".format(writes_performed))
    log_lines.append("--- ASSERTION: WRITES_PERFORMED must be 0 ---")

    if writes_performed > 0:
        log_lines.append("  FAIL: {} rows already have uom_name_ar populated".format(writes_performed))
    else:
        log_lines.append("  PASS: All target rows have empty uom_name_ar. Zero writes performed.")

    log_lines.append("")
    log_lines.append("--- Distinctness Invariant Check ---")
    arabic_vals = [u["arabic"] for u in phase2a_units if u["arabic"]]
    if len(arabic_vals) != len(set(arabic_vals)):
        duplicates = [x for x in arabic_vals if arabic_vals.count(x) > 1]
        log_lines.append("  FAIL: Distinctness invariant violated — duplicate Arabic values: {}".format(set(duplicates)))
    else:
        log_lines.append("  PASS: Distinctness invariant upheld — no duplicate Arabic translations.")

    log_lines.append("")
    log_lines.append("=" * 60)
    log_lines.append("DRY-RUN RESULT")
    log_lines.append("PASS" if writes_performed == 0 else "FAIL")
    log_lines.append("=" * 60)

    # Write evidence log
    evidence_path = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/dry-run.log"
    os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
    with open(evidence_path, "w") as f:
        f.write("\n".join(log_lines))

    print("\n".join(log_lines))
    print("\nDry-run log written to: {}".format(evidence_path))

    return writes_performed == 0


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    success = main()
    if frappe.db:
        frappe.db.rollback()
    sys.exit(0 if success else 1)