"""Align BOQ Header project link metadata with the scoped link query."""

import frappe


def _update_docfield(parent, fieldname, updates):
    names = frappe.get_all(
        "DocField",
        filters={"parent": parent, "fieldname": fieldname},
        pluck="name",
    )
    for name in names:
        for key, value in updates.items():
            frappe.db.set_value("DocField", name, key, value, update_modified=False)


def execute():
    _update_docfield(
        "BOQ Header",
        "project_name",
        {
            "fetch_from": "",
            "ignore_user_permissions": 1,
        },
    )
    _update_docfield(
        "BOQ Header",
        "project",
        {
            "ignore_user_permissions": 1,
        },
    )

    frappe.clear_cache(doctype="BOQ Header")
    frappe.db.commit()
