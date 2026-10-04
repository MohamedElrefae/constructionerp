import frappe
from frappe.utils import flt

from construction.services.boq_pricing import positive_factor

APPROVED_STATUS = "Approved by Client"


def get_revised_qty(boq_item_name):
    item = frappe.db.get_value(
        "BOQ Item",
        boq_item_name,
        ["quantity", "current_revised_qty", "last_quantity_revision", "boq_header"],
        as_dict=True,
    )
    if not item:
        frappe.throw("BOQ Item does not exist", frappe.DoesNotExistError)
    if (
        not item.last_quantity_revision
        and frappe.db.get_value("BOQ Header", item.boq_header, "status") != "Locked"
    ):
        return flt(item.quantity)
    return flt(item.current_revised_qty if item.current_revised_qty is not None else item.quantity)


def get_revised_boq_rows(boq_header, include_variation=False):
    """Return the current projection, including approved standalone corrections.

    The legacy vo_* keys remain VO attribution, not the current total's basis.
    """
    items = frappe.db.sql(
        """
        select
            item.name as boq_item,
            item.structure,
            CASE WHEN item.is_variation_item = 1 THEN 0 ELSE item.quantity END as contract_qty,
            item.contract_unit_price,
            item.line_total as contract_line_value,
            item.factor,
            item.current_revised_qty,
            item.current_revised_unit_price,
            structure.wbs_code,
            structure.title,
            structure.is_group,
            structure.is_variation_item,
            item.unit
        from `tabBOQ Item` item
        inner join `tabBOQ Structure` structure on structure.name = item.structure
        where item.boq_header = %(boq_header)s
          and (%(include_variation)s = 1 or item.is_variation_item = 0)
        order by structure.lft
        """,
        {"boq_header": boq_header, "include_variation": int(bool(include_variation))},
        as_dict=True,
    )
    if not items:
        return []

    item_names = [row.boq_item for row in items]
    deltas = _get_approved_line_deltas(item_names)
    stages = _get_stage_totals(item_names)

    rows = []
    for row in items:
        delta = deltas.get(row.boq_item, {})
        stage = stages.get(row.boq_item, {})
        vo_qty_delta = flt(delta.get("qty_delta"))
        vo_value_delta = flt(delta.get("value_delta"))
        factor = positive_factor(row.factor)
        revised_qty = flt(
            row.current_revised_qty if row.current_revised_qty is not None else row.contract_qty
        )
        revised_rate = flt(
            row.current_revised_unit_price
            if row.current_revised_unit_price is not None
            else row.contract_unit_price
        )
        rows.append(
            {
                "boq_item": row.boq_item,
                "structure": row.structure,
                "wbs_code": row.wbs_code,
                "title": row.title,
                "unit": row.unit,
                "is_group": row.is_group,
                "is_variation_item": row.is_variation_item,
                "contract_qty": flt(row.contract_qty),
                "vo_qty_delta": vo_qty_delta,
                "revised_qty": revised_qty,
                "contract_unit_price": flt(row.contract_unit_price),
                "contract_line_value": flt(row.contract_qty) * flt(row.contract_unit_price) * factor,
                "vo_value_delta": vo_value_delta,
                "revised_value": revised_qty * revised_rate * factor,
                "measured_qty": flt(stage.get("measured_qty")),
                "certified_qty": flt(stage.get("certified_qty")),
            }
        )
    return rows


def _get_approved_line_deltas(item_names):
    rows = frappe.db.sql(
        """
        select
            line.boq_item,
            coalesce(sum(line.delta_qty), 0) as qty_delta,
            coalesce(sum(line.line_delta_value), 0) as value_delta
        from `tabVO Line` line
        inner join `tabVariation Order` vo on vo.name = line.parent
        where line.boq_item in %(item_names)s
          and line.line_type in ('Quantity Change', 'Omission')
          and vo.status = %(approved_status)s
          and vo.docstatus < 2
        group by line.boq_item
        """,
        {"item_names": tuple(item_names), "approved_status": APPROVED_STATUS},
        as_dict=True,
    )
    return {row.boq_item: row for row in rows}


def get_revised_variation_rows(boq_header):
    """Return variation items created by approved New Item VOs."""
    rows = frappe.db.sql(
        """
        select
            item.name as boq_item,
            item.structure,
            COALESCE(item.current_revised_qty, item.quantity) as delta_qty,
            COALESCE(item.current_revised_unit_price, item.contract_unit_price) as revised_unit_price,
            item.factor,
            structure.wbs_code,
            structure.title,
            structure.variation_order,
            item.unit
        from `tabBOQ Item` item
        inner join `tabBOQ Structure` structure on structure.name = item.structure
        where item.boq_header = %(boq_header)s
          and item.is_variation_item = 1
        order by structure.lft
        """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    for row in rows:
        row.revised_line_value = (
            flt(row.delta_qty) * flt(row.revised_unit_price) * positive_factor(row.factor)
        )
    return rows


def _get_stage_totals(item_names):
    rows = frappe.db.sql(
        """
        select
            boq_item,
            coalesce(sum(measured_executed_qty), 0) as measured_qty,
            coalesce(sum(certified_qty), 0) as certified_qty
        from `tabBOQ Item Stage`
        where boq_item in %(item_names)s
        group by boq_item
        """,
        {"item_names": tuple(item_names)},
        as_dict=True,
    )
    return {row.boq_item: row for row in rows}
