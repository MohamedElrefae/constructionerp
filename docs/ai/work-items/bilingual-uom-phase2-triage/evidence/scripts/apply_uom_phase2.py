#!/usr/bin/env python
"""Governed apply script for bilingual UOM Phase 2+.

Loads each document: doc = frappe.get_doc("UOM", row["name"]).
Sets doc.uom_name_ar = row["arabic"].
Calls doc.save().
The registered enforce_bilingual_arabic_policy hook automatically derives
uom_name_ar_norm and validates text direction.

Wrapped in an atomic transaction with fail-closed rollback.
Logs to evidence/apply.log.
"""

import json
import sys
import os
import frappe


def main():
    proposal_path = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase2-triage/proposal.json"
    with open(proposal_path, encoding="utf-8") as f:
        proposal = json.load(f)

    units = proposal.get("units", [])
    target_units = [u for u in units if u.get("section") in ("phase2a", "phase2b")]

    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("UOM PHASE 2+ GOVERNED APPLY")
    log_lines.append("Base commit: 5d96f12")
    log_lines.append("=" * 60)
    log_lines.append("")

    saved = 0
    failed = 0

    try:
        for u in target_units:
            name = u["name"]
            arabic = u["arabic"]
            if not arabic:
                raise ValueError(f"Missing Arabic translation for {name}")

            doc = frappe.get_doc("UOM", name)
            doc.uom_name_ar = arabic
            doc.save()
            saved += 1
            log_lines.append(f"  {name}: Saved uom_name_ar='{arabic}', norm derived server-side")

        frappe.db.commit()
        log_lines.append("\nTRANSACTION COMMITTED SUCCESSFULLY")
    except Exception as exc:
        frappe.db.rollback()
        failed = len(target_units)
        saved = 0
        log_lines.append(f"\nFAIL-CLOSED TRANSACTION ROLLBACK: {exc}")
        print(f"Apply failed and rolled back: {exc}")

    log_lines.append("")
    log_lines.append("=" * 60)
    log_lines.append("APPLY RESULT")
    log_lines.append(f"SUMMARY written={saved} skipped=0 failed={failed}")
    log_lines.append("=" * 60)

    evidence_path = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/apply.log"
    os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print("\n".join(log_lines))
    print(f"\nApply log written to: {evidence_path}")

    return saved, failed


if __name__ == "__main__":
    if not getattr(frappe, "db", None):
        frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
        frappe.connect()
    frappe.set_user("Administrator")
    saved, failed = main()
    sys.exit(0 if failed == 0 and saved > 0 else 1)