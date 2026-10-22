"""Apply the F21-D001 narrow Company read grant for the F19 report audience.

Frappe uses Custom DocPerm rows *instead of* the standard DocPerm rows for a DocType once
any exist, so an additive-looking grant can silently replace the site's whole permission
table for that DocType (observed in this program: one added row discarded 8 doctypes'
standard rows). This script therefore refuses to write to a DocType that has no custom
rows yet — replicate the standard rows first, review, then re-run.

The grant is deliberately minimal: Company read ONLY. It does not confer write/create/
delete/submit/cancel/report/export/import/share/print/email, and it confers nothing on any
business DocType. Access to cost analysis or price history records still requires those
DocTypes' own permissions; Company read is the scope gate for the Company filter that
`construction.api.construction_reports.report_view` applies. Per-company restriction
remains native User Permissions, and Construction scope still requires an active User
Scope Context.

Usage (from the app root):
    python3 scripts/apply_report_audience_company_read.py --site v16rehearsal.localhost
    python3 scripts/apply_report_audience_company_read.py --site ... --dry-run
"""

import argparse
import os
import sys

RIGHTS = [
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "report",
    "export",
    "import",
    "share",
    "print",
    "email",
]

# The documented per-view audience: these roles hold read on the estimation views'
# parents (BOQ Header, BOQ Cost Analysis) but had no native Company read, so
# report_view refused them at its first gate (F21-D001).
#   Project Manager, Construction Owner — owner instruction.
#   Site Engineer, Read-Only — their documented audience includes the estimation
#   views (both hold BOQ Header read); without this grant the views were unusable
#   for exactly the roles the views exist to serve.
# Accountant is not included: the finance/report disposition keeps finance roles on
# their own audience, and the accountant persona already reaches Company through
# Accounts User.
AUDIENCE = {
    "Company": [
        "Project Manager",
        "Construction Owner",
        "Site Engineer",
        "Read-Only",
    ],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="v16rehearsal.localhost")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, "apps/frappe")
    sys.path.insert(0, "apps/erpnext")
    sys.path.insert(0, "apps/construction")
    os.chdir("/home/mohamed/frappe-bench")

    import frappe

    frappe.init(site=args.site, sites_path="sites")
    frappe.connect()
    frappe.set_user("Administrator")

    changed = False
    for doctype, roles in AUDIENCE.items():
        existing = frappe.get_all(
            "Custom DocPerm", filters={"parent": doctype}, fields=["name", "role", *RIGHTS]
        )
        by_role = {}
        for row in existing:
            by_role.setdefault(row["role"], []).append(row)

        if not existing:
            sys.exit(
                f"REFUSING to write to {doctype}: it has no Custom DocPerm rows. Creating the "
                "first custom row for a DocType discards its standard rows site-wide. "
                "Replicate the standard rows, review them, then re-run."
            )

        for role in roles:
            rows = by_role.get(role) or []
            read_row = next(
                (
                    r
                    for r in rows
                    if cint(r["read"]) == 1 and all(not cint(r[k]) for k in RIGHTS if k != "read")
                ),
                None,
            )
            if read_row and not rows:
                continue
            exact = [r for r in rows if all((cint(r[k]) == (1 if k == "read" else 0)) for k in RIGHTS)]
            if exact:
                print(f"== {doctype} / {role}: already read-only (no change)")
                continue
            if rows and not read_row:
                # A row exists for this role but with wider rights: report it rather than
                # silently editing someone's grant.
                print(f"== {doctype} / {role}: EXISTING rows found, not modified by this script:")
                for r in rows:
                    print("     ", {k: r[k] for k in ["name", "role", *RIGHTS] if k != "name"})
                continue

            print(f"== {doctype} / {role}: granting read only")
            if not args.dry_run:
                doc = frappe.get_doc(
                    {
                        "doctype": "Custom DocPerm",
                        "parent": doctype,
                        "parenttype": "DocType",
                        "parentfield": "permissions",
                        "role": role,
                        "permlevel": 0,
                        **{k: (1 if k == "read" else 0) for k in RIGHTS},
                    }
                )
                doc.insert(ignore_permissions=True)
                changed = True

    if changed and not args.dry_run:
        frappe.db.commit()
        print("committed")
    print("dry run: nothing written" if args.dry_run else "done")


def cint(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    main()
