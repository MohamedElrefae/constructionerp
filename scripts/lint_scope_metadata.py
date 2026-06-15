#!/usr/bin/env python3
"""
Metadata lint check for the Construction app Scope Context standard.

Fails if any scope-dimension field (project, company, cost_center, department,
branch) is exposed as a Frappe standard filter (in_standard_filter=1).

Intended for use in CI and pre-commit hooks.
"""

import json
import os
import sys

# Path is relative to repo root
BASE = os.path.join(os.path.dirname(__file__), "..", "construction", "construction", "doctype")
SCOPE_FIELDS = {"project", "company", "cost_center", "department", "branch"}


def lint_doctype_json(path: str) -> list[str]:
    """Return a list of violation messages for a single DocType JSON file."""
    violations = []
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"ERROR: could not parse {path}: {exc}"]

    doctype = doc.get("name") or os.path.basename(os.path.dirname(path))
    for field in doc.get("fields", []):
        fieldname = field.get("fieldname")
        if fieldname in SCOPE_FIELDS and field.get("in_standard_filter"):
            violations.append(f"FAIL: {doctype}.json field '{fieldname}' has in_standard_filter=1")
    return violations


def main() -> int:
    all_violations = []
    checked = 0

    for dt in sorted(os.listdir(BASE)):
        path = os.path.join(BASE, dt, f"{dt}.json")
        if not os.path.exists(path):
            continue
        checked += 1
        all_violations.extend(lint_doctype_json(path))

    if all_violations:
        print("\n".join(all_violations))
        print(f"\n{len(all_violations)} violation(s) found across {checked} DocType(s).")
        return 1

    print(f"PASS: no scope-dimension field has in_standard_filter=1 ({checked} DocTypes checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
