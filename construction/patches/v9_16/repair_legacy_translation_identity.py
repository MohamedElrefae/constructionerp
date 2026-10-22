"""Repair identities missed by v8_6 on legacy rows with NULL catalog flags."""

import frappe
from frappe import _


def execute():
    from construction.setup.translation_catalog_fields import (
        count_incomplete_translation_identities,
        ensure_translation_identity,
    )

    result = ensure_translation_identity()
    if result.get("skipped"):
        frappe.throw(_("Translation identity schema is unavailable; retry after repairing Custom Fields"))
    missing = count_incomplete_translation_identities()
    if missing:
        frappe.throw(_("Legacy Translation identity repair left incomplete rows"))
    print(f"[v9_16] Repaired {result['backfilled']} translation identities; zero incomplete rows")
