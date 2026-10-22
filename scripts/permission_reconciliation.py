"""Permission reconciliation: effective vs installed-standard DocType permissions.

When Custom DocPerm rows exist for a DocType, Frappe uses those rows INSTEAD
OF the standard DocPerm rows. An additive-looking grant can therefore silently
replace the baseline (observed 2026-10-14: cost-database grants wiped standard
Item/Company/RPH/Analysis/UOM/BOQ permissions site-wide until replicated).

Usage (from the app root):
    python3 scripts/permission_reconciliation.py [--json] [--baseline PATH]

Without --baseline it prints the current drift report: every DocType with
Custom DocPerm rows, the standard rows they displace, and the net effective
rights per role. With --baseline it diffs against a checked-in JSON snapshot
and exits non-zero on undocumented change. Regenerate the baseline only after
reviewing each delta (F31/F41).
"""

import json
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


def collect(site):
    import frappe

    frappe.init(site=site, sites_path="sites")
    frappe.connect()
    frappe.set_user("Administrator")
    doctypes = sorted({r["parent"] for r in frappe.db.get_list("Custom DocPerm", fields=["parent"])})
    report = {"site": site, "customized_doctypes": {}}
    for dt in doctypes:
        std = {
            r["role"]: {k: r.get(k, 0) for k in RIGHTS}
            for r in frappe.db.get_list(
                "DocPerm", filters={"parent": dt, "permlevel": 0}, fields=["role", *RIGHTS]
            )
        }
        custom = {
            r["role"]: {k: r.get(k, 0) for k in RIGHTS}
            for r in frappe.db.get_list("Custom DocPerm", filters={"parent": dt}, fields=["role", *RIGHTS])
        }
        # Effective rights = custom rows only (standard displaced).
        report["customized_doctypes"][dt] = {
            "standard_roles": sorted(std),
            "custom_roles": sorted(custom),
            "roles_only_in_custom": sorted(set(custom) - set(std)),
            "roles_missing_vs_standard": sorted(set(std) - set(custom)),
            "changed_rights": {
                role: {
                    k: {"standard": std[role][k], "custom": custom[role][k]}
                    for k in RIGHTS
                    if std[role][k] != custom[role][k]
                }
                for role in sorted(set(std) & set(custom))
                if any(std[role][k] != custom[role][k] for k in RIGHTS)
            },
            "effective": custom,
        }
    return report


def main():
    site = "v16rehearsal.localhost"
    args = sys.argv[1:]
    baseline = None
    if "--baseline" in args:
        baseline = args[args.index("--baseline") + 1]
    if "--site" in args:
        site = args[args.index("--site") + 1]
    import os

    sys.path.insert(0, "apps/frappe")
    sys.path.insert(0, "apps/erpnext")
    sys.path.insert(0, "apps/construction")
    os.chdir("/home/mohamed/frappe-bench")

    report = collect(site)
    if "--json" in args or baseline:
        print(json.dumps(report, indent=1, default=str))
    else:
        for dt, info in report["customized_doctypes"].items():
            print(f"== {dt} ==")
            print(
                f"  standard roles ({len(info['standard_roles'])}) custom roles ({len(info['custom_roles'])})"
            )
            if info["roles_only_in_custom"]:
                print(f"  added roles: {info['roles_only_in_custom']}")
            if info["roles_missing_vs_standard"]:
                print(f"  DROPPED roles (no effective rights!): {info['roles_missing_vs_standard']}")
            for role, diff in info["changed_rights"].items():
                print(f"  changed {role}: {diff}")
    if baseline:
        with open(baseline) as f:
            expected = json.load(f)
        # Compare only the customized_doctypes section.
        if expected.get("customized_doctypes") != report["customized_doctypes"]:
            print("DRIFT vs baseline", file=sys.stderr)
            return 1
        print("matches baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
