"""Enforce the canonical unique identity index for Translation rows."""

import frappe
from frappe import _


def execute():
    from construction.setup.translation_catalog_fields import ensure_translation_digest_unique_index

    result = ensure_translation_digest_unique_index()
    if result.get("skipped"):
        frappe.throw(_("Translation identity schema is unavailable; repair Custom Fields before retrying"))
    if not result.get("verified"):
        frappe.throw(_("Translation digest uniqueness could not be verified"))
    action = "Created" if result.get("created") else "Verified"
    print(f"[v9_18] {action} unique Translation digest index ct_translation_key_digest")
