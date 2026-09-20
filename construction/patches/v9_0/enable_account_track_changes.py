import frappe


def execute():
    """Enable native Version tracking on ERPNext Account (Stage 3 pilot).

    WP6 evaluation outcome: Frappe's native Version audit is the right
    mechanism, but ERPNext ships Account with `track_changes = 0`, so no
    Version rows are recorded for Account field changes (including
    bilingual Arabic-only edits). Enabling tracking through the standard
    DocType property (no vendor source edit, no new audit DocType) closes
    that proven gap for the pilot.

    Idempotent; safe to re-run.
    """
    if not frappe.db.exists("DocType", "Account"):
        return
    current = frappe.db.get_value("DocType", "Account", "track_changes")
    if not current:
        frappe.db.set_value("DocType", "Account", "track_changes", 1)
        frappe.clear_cache(doctype="Account")
        frappe.db.commit()


def revert():
    """Reversal: restore the ERPNext default (tracking disabled)."""
    if not frappe.db.exists("DocType", "Account"):
        return
    frappe.db.set_value("DocType", "Account", "track_changes", 0)
    frappe.clear_cache(doctype="Account")
    frappe.db.commit()
