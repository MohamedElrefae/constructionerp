#!/usr/bin/env python3
"""G10 dependency reconciliation against the reviewed advisory inventory.

Reads the authoritative advisory manifest shipped with the customer release
gap-fixes work item, enumerates the *unique* advisory identities per package,
compares the currently installed version and the G10 target pin against the
highest recorded fix version, and classifies each package as:

  RESOLVED   target pin admits the highest recorded fix for every advisory
  PARTIAL    target pin admits some but not all recorded fixes
  BLOCKED    upstream framework constraint prevents the recorded fix

Output is deterministic plain text suitable for capture as
evidence/dependency-reconciliation.log.
"""

from __future__ import annotations

import json
import os
from importlib import metadata

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_ITEM = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(WORK_ITEM, "..", "..", "..", ".."))
INVENTORY = os.path.join(
    REPO, "docs", "ai", "work-items", "customer-release-gap-fixes", "ADVISORY_INVENTORY.json"
)

# G10 target pins aligned with Frappe v16.36.1 / ERPNext v16.37.0 metadata.
TARGET_PINS = {
    "cryptography": "50.0.0",
    "pyopenssl": "26.4.0",
    "pillow": "12.3.0",
    "sqlparse": "0.6.0",
    "sql_metadata": "3.0.1",
}

# Packages whose highest recorded fix cannot be taken within the version-16
# framework constraints remain application-level compensating controls.
COMPENSATING_CONTROLS = {
    "bleach": "bleach allowlist + narrative_sanitizer Unicode/HTML gate",
    "oauthlib": "framework boundary; no construction-level call path",
    "pdfkit": "construction.utils.security.enforce_local_asset_protocol + guard_ssrf",
    "pyjwt": "framework boundary; no construction-level call path",
    "pypdf": "construction.utils.security.validate_pdf_page_limit + validate_upload",
    "weasyprint": "construction.utils.security.enforce_local_asset_protocol + guard_ssrf",
}


def _norm(name: str) -> str:
    return name.lower().replace("-", "_")


def _installed(name: str) -> str:
    for candidate in (name, name.replace("_", "-")):
        try:
            return metadata.version(candidate)
        except metadata.PackageNotFoundError:
            continue
    return "<not installed>"


def _parse_version(value: str) -> tuple:
    parts = []
    for chunk in value.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _advisory_identity(adv: dict) -> str:
    """Return the canonical advisory identity used for deduplication.

    Matches the reconciliation method in SECURITY_UPGRADE_PATH.md: prefer the
    GHSA alias when present, otherwise fall back to the primary scanner id.
    This collapses BIT/CVE/PYSEC aliases of the same GitHub advisory to one
    identity (70 unique identities across the inventory).
    """
    ghsa = [a for a in adv.get("aliases", []) if a and a.startswith("GHSA-")]
    if ghsa:
        return ghsa[0]
    if adv.get("id", "").startswith("GHSA-"):
        return adv["id"]
    return adv.get("id", "")


def _unique_advisories(entry: dict) -> dict:
    """Deduplicate scanner entries into unique advisory identities."""
    unique = {}
    for adv in entry.get("advisories", []):
        key = _advisory_identity(adv)
        fixes = tuple(adv.get("fix_versions", []))
        existing = unique.get(key)
        if existing is None or _parse_version_list(fixes) > _parse_version_list(existing):
            unique[key] = fixes
    return unique


def _parse_version_list(fixes: tuple) -> tuple:
    parsed = [_parse_version(f) for f in fixes]
    return max(parsed) if parsed else (0,)


def main() -> int:
    with open(INVENTORY, encoding="utf-8") as handle:
        inventory = json.load(handle)

    print("G10 DEPENDENCY SECURITY RECONCILIATION")
    print("=" * 78)
    print(f"Inventory      : {os.path.relpath(INVENTORY, REPO)}")
    print(f"Inventory date : {inventory.get('date')}")
    print(f"Distributions  : {inventory.get('queried_distributions')}")
    print(f"Reported pkgs  : {inventory.get('reported_packages')}")
    print()
    print("Target pins (aligned with Frappe v16.36.1 / ERPNext v16.37.0):")
    for name, version in TARGET_PINS.items():
        print(f"  - {name}~={version}")
    print()

    header = f"{'package':<14}{'installed':<12}{'target':<12}{'uniq':>5}{'fixmax':>8}  {'outcome':<9} controls"
    print(header)
    print("-" * len(header))

    total_unique = 0
    resolved_ids = 0
    blocked_ids = 0
    partial_ids = 0

    summary = []
    for entry in inventory["dependencies"]:
        name = entry["name"]
        key = _norm(name)
        installed = entry.get("installed") or _installed(name)
        target = TARGET_PINS.get(key)
        unique = _unique_advisories(entry)
        total_unique += len(unique)

        highest_fix = (0,)
        for fixes in unique.values():
            highest_fix = max(highest_fix, _parse_version_list(fixes))

        if target:
            target_v = _parse_version(target)
            satisfiable = sum(
                1 for fixes in unique.values() if fixes and _parse_version_list(fixes) <= target_v
            )
            if satisfiable == len(unique):
                outcome = "RESOLVED"
                resolved_ids += len(unique)
            elif satisfiable:
                outcome = "PARTIAL"
                partial_ids += len(unique)
            else:
                outcome = "BLOCKED"
                blocked_ids += len(unique)
            target_display = target
        else:
            outcome = "BLOCKED"
            blocked_ids += len(unique)
            target_display = "-"

        fixmax = ".".join(str(p) for p in highest_fix) if highest_fix != (0,) else "-"
        controls = COMPENSATING_CONTROLS.get(key, "")
        summary.append((name, outcome, len(unique), controls))
        print(
            f"{name:<14}{installed:<12}{target_display:<12}{len(unique):>5}{fixmax:>8}  {outcome:<9} {controls}"
        )

    print()
    print("Unique advisory identities:", total_unique)
    print(f"  RESOLVED by target pins : {resolved_ids}")
    print(f"  PARTIAL (framework cap) : {partial_ids}")
    print(f"  BLOCKED (compensating)  : {blocked_ids}")
    print()
    print("Per-package disposition:")
    for name, outcome, count, controls in summary:
        print(f"  {name:<14} {outcome:<9} unique={count:<3} {controls}")
    print()
    print("NOTE: 'RESOLVED' is a metadata-level statement that the target pin admits")
    print("the recorded fix version; it is not an exploitability or release approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
