"""Add for_user column to Form Layout Profile DocType."""

import frappe


def execute():
    if not frappe.db.has_column("Form Layout Profile", "for_user"):
        frappe.db.add_column(
            "Form Layout Profile",
            "for_user",
            "varchar(140)",
            after="for_role",
        )
    frappe.clear_cache()
