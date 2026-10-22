"""List DocTypes owned by the Construction module on an explicitly named site.

Run from the bench root with ``./env/bin/python <path-to-this-file> --site <site>``.
Importing this utility never initializes a site or connects to a database.
"""

import argparse

import frappe


def list_doctypes():
    """Print Construction-module DocTypes using the already-connected site."""
    doctypes = frappe.get_list("DocType", filters={"module": "construction"}, fields=["name", "app_name"])
    for doctype in doctypes:
        print(f"{doctype.name} -> {doctype.app_name}")
    return doctypes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, help="Frappe site to inspect")
    args = parser.parse_args(argv)

    frappe.init(args.site)
    try:
        frappe.connect()
        return list_doctypes()
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
