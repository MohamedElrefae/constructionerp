import frappe
from frappe import _
from frappe.utils import flt


def get_boq_cost_analysis_summary(boq_header):
    """Report 1: BOQ Cost Analysis Summary.

    Shows approved cost analysis details for all BOQ Items in a header.
    """
    rows = frappe.db.sql(
        """
        SELECT
            bca.name as analysis_name,
            bca.boq_item,
            bca.analysis_status,
            bca.total_direct_cost,
            bca.overhead_pct,
            bca.profit_pct,
            bca.total_unit_cost,
            bca.suggested_sell_rate,
            bi.structure,
            bi.item_type,
            bi.quantity,
            bi.unit,
            bi.contract_unit_price
        FROM `tabBOQ Cost Analysis` bca
        INNER JOIN `tabBOQ Item` bi ON bi.name = bca.boq_item
        WHERE bi.boq_header = %(boq_header)s
          AND bca.docstatus = 1
        ORDER BY bi.idx
    """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    return rows


def get_boq_item_cost_vs_contract(boq_header):
    """Report 2: BOQ Item Estimated Cost vs Contract Rate.

    Shows approved unit cost, contract rate, and margin for each item.
    """
    rows = frappe.db.sql(
        """
        SELECT
            bi.name as boq_item,
            bi.structure,
            bi.item_type,
            bi.quantity,
            bi.unit,
            bi.contract_unit_price,
            bi.est_unit_cost,
            bi.est_unit_price,
            bi.calculated_sell_price,
            bi.overhead_pct,
            bi.profit_pct,
            (bi.contract_unit_price - bi.est_unit_cost) as margin_amount,
            CASE
                WHEN bi.est_unit_cost > 0
                THEN (bi.contract_unit_price - bi.est_unit_cost) / bi.est_unit_cost * 100
                ELSE 0
            END as margin_pct,
            bca.name as analysis_name,
            bca.analysis_status
        FROM `tabBOQ Item` bi
        LEFT JOIN `tabBOQ Cost Analysis` bca
            ON bca.boq_item = bi.name
            AND bca.analysis_status = 'Approved'
            AND bca.docstatus = 1
        WHERE bi.boq_header = %(boq_header)s
        ORDER BY bi.idx
    """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    return rows


def get_resource_requirement_summary(boq_header):
    """Report 3: Resource Requirement Summary by resource stream.

    Aggregates resource quantities across all approved cost analyses.
    """
    rows = frappe.db.sql(
        """
        SELECT
            bcd.cost_stream,
            bcd.item_code,
            bcd.item_name,
            bcd.resource_uom,
            SUM(bcd.qty_per_boq_unit * bi.quantity) as total_resource_qty,
            AVG(bcd.cost_rate) as avg_cost_rate,
            SUM(bcd.amount * bi.quantity / NULLIF(bca.analysis_qty, 0)) as total_resource_cost
        FROM `tabBOQ Cost Analysis Detail` bcd
        INNER JOIN `tabBOQ Cost Analysis` bca
            ON bca.name = bcd.parent
            AND bca.docstatus = 1
            AND bca.analysis_status = 'Approved'
        INNER JOIN `tabBOQ Item` bi
            ON bi.name = bca.boq_item
        WHERE bi.boq_header = %(boq_header)s
        GROUP BY bcd.cost_stream, bcd.item_code, bcd.item_name, bcd.resource_uom
        ORDER BY bcd.cost_stream, SUM(bcd.amount * bi.quantity / NULLIF(bca.analysis_qty, 0)) DESC
    """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    return rows


def get_resource_price_history(item_code=None, supplier=None, region=None, from_date=None, to_date=None):
    """Report 4: Resource Price History / Rate Movement.

    Shows price changes over time for selected items.
    All filtering is done in-database via parameterized SQL.
    """
    RPH = frappe.qb.DocType("Resource Price History")
    query = (
        frappe.qb.from_(RPH)
        .select(
            RPH.item_code,
            RPH.item_name,
            RPH.resource_type,
            RPH.price_date,
            RPH.rate,
            RPH.currency,
            RPH.exchange_rate,
            RPH.uom,
            RPH.supplier,
            RPH.source_doctype,
            RPH.source_name,
            RPH.project,
            RPH.region,
            RPH.company,
        )
        .where(RPH.status == "Active")
        .orderby(RPH.item_code, RPH.price_date, order=frappe.qb.desc)
    )

    if item_code:
        query = query.where(RPH.item_code == item_code)
    if supplier:
        query = query.where(RPH.supplier == supplier)
    if region:
        query = query.where(RPH.region == region)
    if from_date:
        query = query.where(RPH.price_date >= from_date)
    if to_date:
        query = query.where(RPH.price_date <= to_date)

    return query.run(as_dict=True)


def get_boq_items_missing_analysis(boq_header):
    """Report 5: BOQ Items Missing Approved Cost Analysis.

    Lists BOQ Items without an approved cost analysis.
    """
    rows = frappe.db.sql(
        """
        SELECT
            bi.name as boq_item,
            bi.structure,
            bi.item_type,
            bi.quantity,
            bi.unit,
            bi.contract_unit_price,
            bi.est_unit_cost,
            bi.cost_item
        FROM `tabBOQ Item` bi
        WHERE bi.boq_header = %(boq_header)s
          AND bi.docstatus < 2
          AND NOT EXISTS (
              SELECT 1
              FROM `tabBOQ Cost Analysis` bca
              WHERE bca.boq_item = bi.name
                AND bca.analysis_status = 'Approved'
                AND bca.docstatus = 1
          )
        ORDER BY bi.idx
    """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    return rows
