import frappe
from frappe import _
from frappe.utils import flt

from construction.services.boq_lookups import get_stages_for_item

TOLERANCE = 0.001


def validate_stage_quantities(doc):
    for fieldname in ("planned_qty", "measured_executed_qty", "certified_qty"):
        value = flt(doc.get(fieldname))
        if value < 0:
            frappe.throw(_("Field '{0}' must be non-negative").format(doc.meta.get_label(fieldname)))

    if flt(doc.certified_qty) > flt(doc.measured_executed_qty):
        frappe.throw(_("Certified quantity cannot exceed measured executed quantity"))

    percent_complete = flt(doc.percent_complete)
    if percent_complete < 0 or percent_complete > 100:
        frappe.throw(_("Percent complete must be between 0 and 100"))

    _validate_planned_distribution(doc)


def validate_boq_item_stage_distribution(boq_item):
    if not boq_item.get("has_stages") or not boq_item.name:
        return

    parent_qty = _get_parent_quantity_for_stage_distribution(boq_item.name)
    total_planned = sum(flt(stage.planned_qty) for stage in get_stages_for_item(boq_item.name))
    header_status = frappe.db.get_value("BOQ Header", boq_item.boq_header, "status")
    _enforce_distribution_rule(total_planned, parent_qty, header_status)


def _validate_planned_distribution(doc):
    _acquire_stage_distribution_lock(doc.boq_item)
    parent_qty = _get_parent_quantity_for_stage_distribution(doc.boq_item)
    header_status = frappe.db.get_value("BOQ Header", doc.boq_header, "status")

    frappe.db.sql(
        "SELECT name, quantity FROM `tabBOQ Item` WHERE name = %s FOR UPDATE",
        (doc.boq_item,),
    )

    params = {"boq_item": doc.boq_item, "name": doc.name or ""}
    total_planned = sum(
        flt(row.planned_qty)
        for row in frappe.db.sql(
            """
            SELECT name, planned_qty
            FROM `tabBOQ Item Stage`
            WHERE boq_item = %(boq_item)s
              AND name != %(name)s
            FOR UPDATE
            """,
            params,
            as_dict=True,
        )
    )
    total_planned += flt(doc.planned_qty)

    _enforce_distribution_rule(total_planned, parent_qty, header_status)


def _get_parent_quantity_for_stage_distribution(boq_item):
    try:
        from construction.services.variation_orders import get_revised_qty

        return flt(get_revised_qty(boq_item))
    except Exception:
        return flt(frappe.db.get_value("BOQ Item", boq_item, "quantity"))


def _acquire_stage_distribution_lock(boq_item: str):
    if not boq_item:
        return

    lock_name = f"construction:boq_stage_distribution:{boq_item}"
    held_locks = getattr(frappe.flags, "boq_stage_distribution_locks", None) or set()
    if lock_name in held_locks:
        return

    result = frappe.db.sql("SELECT GET_LOCK(%s, 10)", lock_name)
    if not result or result[0][0] != 1:
        frappe.throw(_("Could not acquire BOQ Item Stage distribution lock. Please retry."))

    held_locks.add(lock_name)
    frappe.flags.boq_stage_distribution_locks = held_locks

    def release_lock():
        try:
            frappe.db.sql("SELECT RELEASE_LOCK(%s)", lock_name)
        finally:
            locks = getattr(frappe.flags, "boq_stage_distribution_locks", None) or set()
            locks.discard(lock_name)
            frappe.flags.boq_stage_distribution_locks = locks

    frappe.db.after_commit.add(release_lock)
    frappe.db.after_rollback.add(release_lock)


def _enforce_distribution_rule(total_planned, parent_qty, header_status):
    if header_status in ("Draft", "Pricing"):
        if total_planned > parent_qty:
            frappe.throw(
                _("Total planned quantity ({0}) exceeds BOQ Item quantity ({1})").format(
                    total_planned, parent_qty
                )
            )
    elif header_status in ("Frozen", "Locked"):
        if abs(total_planned - parent_qty) > TOLERANCE:
            frappe.throw(
                _("Frozen/Locked BOQ requires exact stage distribution. Total: {0}, Expected: {1}").format(
                    total_planned, parent_qty
                )
            )
