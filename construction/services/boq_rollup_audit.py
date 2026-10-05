"""Read-only discrepancy audit for stored BOQ header and structure rollups."""

import frappe
from frappe import _
from frappe.utils import cint, flt

HEADER_TOTAL_FIELDS = (
    "total_contract_value",
    "total_estimated_value",
    "total_budgeted_cost",
    "total_revised_value",
)
STRUCTURE_TOTAL_FIELDS = ("item_count", "total_contract_value", "total_budgeted_cost")

AGGREGATION_LIMIT = _(
    "This audit mirrors current controller semantics: BOQ Header totals do not filter item docstatus; "
    "contract, estimated, and budget totals exclude variation items, while revised totals include all items. "
    "BOQ Structure totals include only structures and items with docstatus below 2, and include variation "
    "items in contract and budget totals."
)


def audit_boq_rollups(boq_header):
    """Return stored and recomputed totals without changing any BOQ records.

    This is an internal service function, not a whitelisted RPC endpoint. Only the
    Administrator session may inspect the selected BOQ's rollup values.
    """
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator may audit BOQ rollups."), frappe.PermissionError)

    if not isinstance(boq_header, str) or not boq_header.strip():
        frappe.throw(_("A BOQ Header name is required."), frappe.ValidationError)

    header_rows = frappe.db.sql(
        """
        SELECT name, total_contract_value, total_estimated_value,
               total_budgeted_cost, total_revised_value
        FROM `tabBOQ Header`
        WHERE name = %s
        """,
        (boq_header,),
        as_dict=True,
    )
    if not header_rows:
        frappe.throw(_("BOQ Header {0} does not exist.").format(boq_header), frappe.DoesNotExistError)

    header_row = header_rows[0]
    header_totals = frappe.db.sql(
        """
        SELECT
            COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN line_total ELSE 0 END), 0)
                AS total_contract_value,
            COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN est_line_total ELSE 0 END), 0)
                AS total_estimated_value,
            COALESCE(
                SUM(
                    CASE WHEN is_variation_item = 0
                         THEN quantity * est_unit_cost * COALESCE(factor, 1.0)
                         ELSE 0
                    END
                ),
                0
            ) AS total_budgeted_cost,
            COALESCE(
                SUM(
                    COALESCE(current_revised_qty, quantity)
                    * COALESCE(current_revised_unit_price, contract_unit_price)
                    * COALESCE(factor, 1.0)
                ),
                0
            ) AS total_revised_value
        FROM `tabBOQ Item`
        WHERE boq_header = %s
        """,
        (boq_header,),
        as_dict=True,
    )[0]

    structure_rows = frappe.db.sql(
        """
        SELECT
            s.name,
            s.item_count AS stored_item_count,
            s.total_contract_value AS stored_total_contract_value,
            s.total_budgeted_cost AS stored_total_budgeted_cost,
            COALESCE(agg.item_count, 0) AS computed_item_count,
            COALESCE(agg.total_contract_value, 0) AS computed_total_contract_value,
            COALESCE(agg.total_budgeted_cost, 0) AS computed_total_budgeted_cost
        FROM `tabBOQ Structure` s
        LEFT JOIN (
            SELECT
                source.name AS structure_name,
                COUNT(DISTINCT i.name) AS item_count,
                COALESCE(
                    SUM(CASE WHEN i.docstatus < 2 THEN i.line_total ELSE 0 END),
                    0
                ) AS total_contract_value,
                COALESCE(
                    SUM(
                        CASE WHEN i.docstatus < 2
                             THEN i.quantity * i.est_unit_cost * COALESCE(i.factor, 1.0)
                             ELSE 0
                        END
                    ),
                    0
                ) AS total_budgeted_cost
            FROM `tabBOQ Structure` source
            LEFT JOIN `tabBOQ Structure` descendant
                ON descendant.boq_header = source.boq_header
               AND descendant.lft >= source.lft
               AND descendant.rgt <= source.rgt
               AND descendant.docstatus < 2
            LEFT JOIN `tabBOQ Item` i
                ON i.structure = descendant.name
               AND i.docstatus < 2
            WHERE source.boq_header = %(header)s
              AND source.docstatus < 2
            GROUP BY source.name
        ) agg ON agg.structure_name = s.name
        WHERE s.boq_header = %(header)s
          AND s.docstatus < 2
        ORDER BY s.lft, s.name
        """,
        {"header": boq_header},
        as_dict=True,
    )

    header_doc = frappe.get_doc("BOQ Header", boq_header)
    header_stored = {field: header_row.get(field) or 0 for field in HEADER_TOTAL_FIELDS}
    header_computed = {field: header_totals.get(field) or 0 for field in HEADER_TOTAL_FIELDS}

    structure_doc = frappe.get_doc("BOQ Structure", structure_rows[0].name) if structure_rows else None
    audited_structures = []
    for row in structure_rows:
        stored = {
            "item_count": row.stored_item_count or 0,
            "total_contract_value": row.stored_total_contract_value or 0,
            "total_budgeted_cost": row.stored_total_budgeted_cost or 0,
        }
        computed = {
            "item_count": row.computed_item_count or 0,
            "total_contract_value": row.computed_total_contract_value or 0,
            "total_budgeted_cost": row.computed_total_budgeted_cost or 0,
        }
        audited_structures.append(
            {
                "name": row.name,
                "stored": stored,
                "computed": computed,
                "mismatched_fields": _mismatched_fields(
                    STRUCTURE_TOTAL_FIELDS, stored, computed, structure_doc
                ),
            }
        )

    return {
        "boq_header": boq_header,
        "header": {
            "stored": header_stored,
            "computed": header_computed,
            "mismatched_fields": _mismatched_fields(
                HEADER_TOTAL_FIELDS, header_stored, header_computed, header_doc
            ),
        },
        "structures": audited_structures,
        "aggregation_limit": AGGREGATION_LIMIT,
    }


def _mismatched_fields(fields, stored, computed, precision_doc):
    mismatches = []
    for field in fields:
        if field == "item_count":
            differs = cint(stored[field]) != cint(computed[field])
        else:
            precision = precision_doc.precision(field)
            differs = flt(stored[field], precision) != flt(computed[field], precision)
        if differs:
            mismatches.append(field)
    return mismatches
