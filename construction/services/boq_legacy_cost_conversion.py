"""Reviewed legacy cost conversion; never guess or overwrite historical amounts.

These functions are deliberately not RPC endpoints. An authorized operator
previews a saved replacement Draft and an explicitly supplied manual basis,
then applies that exact digest in the caller-owned transaction.
"""

import hashlib
import json

import frappe
from frappe import _

from construction.services.boq_pricing import PERCENT_FIELDS, number, positive_factor
from construction.services.boq_transactions import current_boq_sql, lock_boq_item_header


def _require_owner():
    if frappe.session.user != "Administrator" and "Construction Owner" not in frappe.get_roles():
        frappe.throw(
            _("Only the Construction Owner can authorize legacy cost conversion."), frappe.PermissionError
        )


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _review(boq_item, replacement_analysis, manual_basis, reason):
    _require_owner()
    if not isinstance(manual_basis, dict) or not isinstance(reason, str) or not reason.strip():
        frappe.throw(_("An explicit reviewed manual basis and review reason are required."))
    if len(reason) > 2000:
        frappe.throw(_("Conversion review reason must not exceed 2000 characters."))
    values = {}
    for field in ("est_unit_cost", *PERCENT_FIELDS):
        if field not in manual_basis:
            frappe.throw(_("Reviewed manual basis is missing {0}.").format(field))
        values[field] = number(manual_basis[field], field, maximum=100 if field in PERCENT_FIELDS else None)
    header_name = lock_boq_item_header(boq_item)
    item = frappe.get_doc("BOQ Item", boq_item, for_update=True)
    replacement = frappe.get_doc("BOQ Cost Analysis", replacement_analysis, for_update=True)
    for doctype, name, ptype in (
        ("BOQ Header", header_name, "write"),
        ("BOQ Item", boq_item, "write"),
        ("BOQ Cost Analysis", replacement_analysis, "write"),
        ("BOQ Cost Analysis", replacement_analysis, "submit"),
    ):
        frappe.has_permission(doctype, ptype, doc=name, throw=True)
    if item.cost_basis != "Legacy Review" or item.manual_cost_snapshot:
        frappe.throw(_("This item is not an unresolved legacy cost basis."))
    positive_factor(item.factor)
    if (
        replacement.docstatus != 0
        or replacement.analysis_status != "Draft"
        or replacement.boq_item != item.name
        or replacement.is_template
    ):
        frappe.throw(_("Replacement must be a saved Draft cost analysis for this BOQ Item."))
    # Reject ambiguous history rather than pick an arbitrary approved record.
    history = current_boq_sql(
        "SELECT name FROM `tabBOQ Cost Analysis` WHERE boq_item = %s AND docstatus > 0 ORDER BY name FOR UPDATE NOWAIT",
        boq_item,
    )
    historical = [frappe.get_doc("BOQ Cost Analysis", row[0], for_update=True) for row in history]
    active = [doc for doc in historical if doc.docstatus == 1 and doc.analysis_status == "Approved"]
    if (
        not historical
        or len(active) > 1
        or any(doc.pricing_rule_version != "legacy-unversioned/v0" for doc in active)
    ):
        frappe.throw(_("Legacy cost history requires reconciliation before conversion."))
    for doc in historical:
        frappe.has_permission("BOQ Cost Analysis", "read", doc=doc, throw=True)
    stored_replacement = replacement.as_dict()
    replacement.validate()
    replacement.validate_approvable()
    binding = {
        "schema": "boq-legacy-cost-conversion/v1",
        "item": item.as_dict(),
        "history": [doc.as_dict() for doc in historical],
        "replacement": stored_replacement,
        "manual_basis": values,
        "reason": reason.strip(),
    }
    preview = {
        "schema": binding["schema"],
        "boq_item": item.name,
        "replacement_analysis": replacement.name,
        "legacy_analyses": [doc.name for doc in historical],
        "before_unit_cost": item.est_unit_cost,
        "after_unit_cost": replacement.total_unit_cost,
        "after_suggested_rate": replacement.suggested_sell_rate,
        "manual_basis": values,
        "reason": reason.strip(),
        "inputs_digest": _digest(binding),
    }
    return item, replacement, active, preview


def preview_legacy_cost_conversion(boq_item, replacement_analysis, manual_basis, reason):
    """No writes; return the bound proposed conversion for domain review."""
    return _review(boq_item, replacement_analysis, manual_basis, reason)[3]


def apply_legacy_cost_conversion(boq_item, replacement_analysis, manual_basis, reason, expected_digest):
    """Apply only the reviewed state, with native approval and atomic rollback.

    Caller must arrange a recoverable backup and commit/rollback. On lock
    contention, the shared BOQ guard still requires a full transaction rollback.
    """
    _require_owner()
    savepoint = "legacy_cost_" + frappe.generate_hash(length=8)
    frappe.db.savepoint(savepoint)
    try:
        item, replacement, active, preview = _review(boq_item, replacement_analysis, manual_basis, reason)
        if not isinstance(expected_digest, str) or expected_digest != preview["inputs_digest"]:
            frappe.throw(_("Legacy conversion preview has changed. Review a fresh preview."))
        snapshot = dict(preview["manual_basis"])
        snapshot.update(
            schema="boq-manual-cost/v1",
            captured_by=frappe.session.user,
            captured_on=frappe.utils.now(),
            conversion=preview,
        )
        # This is the sole deliberate legacy provenance bypass. All historic
        # quantities, costs, approval identities and dates remain unchanged.
        for legacy in active:
            legacy.db_set("analysis_status", "Superseded", update_modified=False)
        item.db_set(
            dict(
                preview["manual_basis"],
                cost_basis="Manual",
                active_cost_analysis=None,
                manual_cost_snapshot=frappe.as_json(snapshot),
            ),
            update_modified=False,
        )
        replacement.submit()
        item.reload()
        # Native approval refreshes the current manual snapshot. Retain the
        # reviewed conversion binding as well as its valid restoration basis.
        item.db_set("manual_cost_snapshot", frappe.as_json(snapshot), update_modified=False)
        replacement.add_comment("Info", frappe.as_json(dict(preview, reviewed_by=frappe.session.user)))
        return dict(preview, applied=True, approved_analysis=replacement.name)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
