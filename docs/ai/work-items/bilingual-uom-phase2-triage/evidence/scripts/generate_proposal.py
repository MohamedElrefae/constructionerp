#!/usr/bin/env python
"""Proposal draft script for bilingual UOM Phase 2+.

Creates a private proposal JSON under sites/v16.localhost/private/uom-phase2-triage/proposal.json.
This file MUST stay untracked / ignored by Git (R4 privacy rule).

Distinctness Invariant: Two different English units must not share the same Arabic translation
unless they are genuine synonyms.

Computes and records the SHA-256 hash of proposal.json.
"""

import json
import hashlib
import sys
import os
from datetime import datetime


TRANSLATIONS = {
    # Phase 2A - Dimensional
    "Millimeter": {"arabic": "مليمتر", "confidence": "high", "provenance": "standard linear unit"},
    "Centimeter": {"arabic": "سنتيمتر", "confidence": "high", "provenance": "standard linear unit"},
    "Meter": {"arabic": "متر", "confidence": "high", "provenance": "standard linear unit; synonym with M fixture"},
    "Kilometer": {"arabic": "كيلومتر", "confidence": "high", "provenance": "standard linear unit"},
    "Inch": {"arabic": "بوصة", "confidence": "high", "provenance": "standard imperial linear unit"},
    "Foot": {"arabic": "قدم", "confidence": "high", "provenance": "standard imperial linear unit"},
    "Yard": {"arabic": "ياردة", "confidence": "high", "provenance": "standard imperial linear unit"},
    # Phase 2A - Area & Volume
    "Square Meter": {"arabic": "متر مربع", "confidence": "high", "provenance": "standard area unit; synonym with M2 fixture"},
    "Square Foot": {"arabic": "قدم مربع", "confidence": "high", "provenance": "standard imperial area unit"},
    "Square Yard": {"arabic": "ياردة مربعة", "confidence": "high", "provenance": "standard imperial area unit"},
    "Cubic Centimeter": {"arabic": "سنتيمتر مكعب", "confidence": "high", "provenance": "standard volume unit"},
    "Cubic Foot": {"arabic": "قدم مكعب", "confidence": "high", "provenance": "standard imperial volume unit"},
    "Cubic Yard": {"arabic": "ياردة مكعبة", "confidence": "high", "provenance": "standard imperial volume unit"},
    "Cubic Meter": {"arabic": "متر مكعب", "confidence": "high", "provenance": "standard volume unit; synonym with M3 fixture"},
    # Phase 2A - Mass
    "Gram": {"arabic": "جرام", "confidence": "high", "provenance": "standard mass unit"},
    "Milligram": {"arabic": "مليجرام", "confidence": "high", "provenance": "standard mass unit"},
    "Pound": {"arabic": "رطل", "confidence": "high", "provenance": "standard mass unit"},
    "Ounce": {"arabic": "أونصة", "confidence": "high", "provenance": "standard mass unit"},
    # Phase 2A - MEP / Electrical / Energy
    "Kilowatt": {"arabic": "كيلوواط", "confidence": "high", "provenance": "standard power unit"},
    "Watt": {"arabic": "واط", "confidence": "high", "provenance": "standard power unit"},
    "Horsepower": {"arabic": "حصان", "confidence": "high", "provenance": "standard mechanical power unit"},
    "Ampere": {"arabic": "أمبير", "confidence": "high", "provenance": "standard electrical current unit"},
    "Joule": {"arabic": "جول", "confidence": "high", "provenance": "standard energy unit"},
    "Kilojoule": {"arabic": "كيلوجول", "confidence": "high", "provenance": "standard energy unit"},
    "Tesla": {"arabic": "تسلا", "confidence": "high", "provenance": "standard magnetic flux density unit"},
    # Phase 2A - Time
    "Minute": {"arabic": "دقيقة", "confidence": "high", "provenance": "standard time unit"},
    "Second": {"arabic": "ثانية", "confidence": "high", "provenance": "standard time unit"},
    "Hour": {"arabic": "ساعة", "confidence": "high", "provenance": "standard time unit; synonym with HR fixture"},
    "Week": {"arabic": "أسبوع", "confidence": "high", "provenance": "standard time unit"},
    # Phase 2B - Commercial / Packaging
    "Pair": {"arabic": "زوج", "confidence": "high", "provenance": "standard pair/count unit"},
}


def load_triage_units():
    """Load and parse candidate units from inventory-triage.log."""
    log_path = "/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log"
    units = []
    in_section = None
    with open(log_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if "Phase 2A" in line and "Priority" in line:
                in_section = "phase2a"
                continue
            elif "Phase 2B" in line and "Commercial" in line:
                in_section = "phase2b"
                continue
            elif "Phase 2C" in line and "Exclusions" in line:
                in_section = "phase2c"
                continue

            if in_section in ("phase2a", "phase2b") and raw_line.startswith("  "):
                parts = line.split(" - ")
                name_part = parts[0].strip()
                name = name_part.split(" (")[0].strip()
                if name and not name.startswith("Total:"):
                    entry = TRANSLATIONS.get(name, {
                        "arabic": "",
                        "confidence": "low",
                        "provenance": "unmapped",
                    })
                    units.append({
                        "name": name,
                        "section": in_section,
                        "arabic": entry["arabic"],
                        "confidence": entry["confidence"],
                        "provenance": entry["provenance"],
                    })
    return units


def main():
    units = load_triage_units()
    phase2a_units = [u for u in units if u["section"] == "phase2a"]
    phase2b_units = [u for u in units if u["section"] == "phase2b"]

    proposal = {
        "work_item": "bilingual-uom-phase2-triage",
        "generated": datetime.now().isoformat(),
        "phase2a_count": len(phase2a_units),
        "phase2b_count": len(phase2b_units),
        "total_count": len(units),
        "units": units,
    }

    output_path = "/home/mohamed/frappe-bench/sites/v16.localhost/private/uom-phase2-triage/proposal.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, ensure_ascii=False, indent=2)

    with open(output_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    print("Proposal generated: {}".format(output_path))
    print("SHA-256: {}".format(sha256))
    print("Total units in proposal: {}".format(len(units)))
    print("Phase 2A units: {}".format(len(phase2a_units)))
    print("Phase 2B units: {}".format(len(phase2b_units)))


if __name__ == "__main__":
    main()