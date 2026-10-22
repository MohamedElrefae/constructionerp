"""One-time patch: migrate User Scope Context records from branch to cost_center.

For each User Scope Context where cost_center is empty and branch has a value:
1. Look up a Cost Center whose `name` matches the branch value
2. If found, set cost_center to that Cost Center name
3. If not found, leave empty — user will be prompted to select on next login

Branch and Cost Center are separate doctypes, so a direct name match is
the best-effort heuristic. Most pre-existing records will need manual
re-selection, which is the correct behavior for a data model change.
"""

import frappe


def execute():
    if not frappe.db.table_exists("tabUser Scope Context"):
        return

    records = frappe.get_all(
        "User Scope Context",
        fields=["name", "branch", "company"],
        filters={
            "cost_center": ["is", "not set"],
            "branch": ["is", "set"],
        },
    )

    for r in records:
        if not r.branch:
            continue

        # Best-effort: try direct name match
        if frappe.db.exists("Cost Center", r.branch):
            frappe.db.set_value(
                "User Scope Context",
                r.name,
                "cost_center",
                r.branch,
            )

    frappe.db.commit()
