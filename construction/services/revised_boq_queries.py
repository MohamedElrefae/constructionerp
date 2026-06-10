import frappe
from frappe.utils import flt


def get_original_boq(boq_header):
    """Return the original BOQ view using original_qty.
    
    Shows only non-variation items with original contract values.
    """
    rows = frappe.db.sql("""
        SELECT
            item.name as boq_item,
            item.structure,
            structure.wbs_code,
            structure.title,
            item.unit,
            item.original_qty as contract_qty,
            item.contract_unit_price,
            item.original_qty * item.contract_unit_price * COALESCE(item.factor, 1.0) as contract_line_value
        FROM `tabBOQ Item` item
        INNER JOIN `tabBOQ Structure` structure ON structure.name = item.structure
        WHERE item.boq_header = %(boq_header)s
          AND item.is_variation_item = 0
        ORDER BY structure.lft
    """, {"boq_header": boq_header}, as_dict=True)
    
    return rows


def get_revised_boq(boq_header):
    """Return the current revised BOQ view.
    
    Uses current_revised_qty and current_revised_unit_price for value computation.
    Includes both contract and variation items.
    """
    rows = frappe.db.sql("""
        SELECT
            item.name as boq_item,
            item.structure,
            structure.wbs_code,
            structure.title,
            item.unit,
            item.is_variation_item,
            item.original_qty,
            item.current_revised_qty,
            item.current_revised_qty - item.original_qty as delta_qty,
            item.current_revised_qty - item.original_qty as delta_from_contract_qty,
            item.contract_unit_price,
            item.current_revised_unit_price,
            item.original_qty * item.contract_unit_price * COALESCE(item.factor, 1.0) as original_value,
            item.current_revised_qty * COALESCE(item.current_revised_unit_price, item.contract_unit_price) * COALESCE(item.factor, 1.0) as revised_value,
            (item.current_revised_qty * COALESCE(item.current_revised_unit_price, item.contract_unit_price) * COALESCE(item.factor, 1.0)) - 
            (item.original_qty * item.contract_unit_price * COALESCE(item.factor, 1.0)) as delta_value
        FROM `tabBOQ Item` item
        INNER JOIN `tabBOQ Structure` structure ON structure.name = item.structure
        WHERE item.boq_header = %(boq_header)s
        ORDER BY structure.lft
    """, {"boq_header": boq_header}, as_dict=True)
    
    return rows


def get_quantity_history(boq_item):
    """Return full quantity revision timeline for a BOQ Item.
    
    Ordered by revision_date descending.
    """
    rows = frappe.db.sql("""
        SELECT
            name,
            revision_date,
            revision_type,
            previous_qty,
            revised_qty,
            delta_qty,
            delta_from_contract_qty,
            change_pct,
            change_pct_from_contract,
            contract_unit_price,
            revised_unit_price,
            previous_value,
            revised_value,
            delta_value,
            rate_change_triggered,
            variation_order,
            status,
            approved_by,
            approved_on
        FROM `tabBOQ Quantity Revision`
        WHERE boq_item = %(boq_item)s
        ORDER BY revision_date DESC, modified DESC
    """, {"boq_item": boq_item}, as_dict=True)
    
    return rows


def get_vo_impact(boq_header):
    """Return commercial impact grouped by Variation Order.
    
    Sums delta_value per VO for the given BOQ Header.
    """
    rows = frappe.db.sql("""
        SELECT
            rev.variation_order,
            vo.vo_number,
            vo.vo_date,
            vo.status,
            COUNT(rev.name) as revision_count,
            SUM(rev.delta_value) as total_delta_value,
            SUM(CASE WHEN rev.delta_value > 0 THEN rev.delta_value ELSE 0 END) as positive_delta,
            SUM(CASE WHEN rev.delta_value < 0 THEN rev.delta_value ELSE 0 END) as negative_delta
        FROM `tabBOQ Quantity Revision` rev
        INNER JOIN `tabVariation Order` vo ON vo.name = rev.variation_order
        WHERE rev.boq_header = %(boq_header)s
          AND rev.status = 'Approved'
        GROUP BY rev.variation_order
        ORDER BY vo.vo_date DESC
    """, {"boq_header": boq_header}, as_dict=True)
    
    return rows


def get_omitted_items(boq_header):
    """Return items that have been fully omitted.
    
    current_revised_qty = 0 and is_variation_item = 0.
    """
    rows = frappe.db.sql("""
        SELECT
            item.name as boq_item,
            item.structure,
            structure.wbs_code,
            structure.title,
            item.unit,
            item.original_qty,
            item.current_revised_qty,
            item.contract_unit_price,
            item.original_qty * item.contract_unit_price * COALESCE(item.factor, 1.0) as original_value
        FROM `tabBOQ Item` item
        INNER JOIN `tabBOQ Structure` structure ON structure.name = item.structure
        WHERE item.boq_header = %(boq_header)s
          AND item.is_variation_item = 0
          AND COALESCE(item.current_revised_qty, item.quantity) = 0
        ORDER BY structure.lft
    """, {"boq_header": boq_header}, as_dict=True)
    
    return rows


def get_variation_items(boq_header):
    """Return all variation items for a BOQ Header.
    """
    rows = frappe.db.sql("""
        SELECT
            item.name as boq_item,
            item.structure,
            structure.wbs_code,
            structure.title,
            item.unit,
            item.original_qty,
            item.current_revised_qty,
            item.contract_unit_price,
            item.current_revised_unit_price,
            item.variation_order,
            item.current_revised_qty * COALESCE(item.current_revised_unit_price, item.contract_unit_price) * COALESCE(item.factor, 1.0) as revised_value
        FROM `tabBOQ Item` item
        INNER JOIN `tabBOQ Structure` structure ON structure.name = item.structure
        WHERE item.boq_header = %(boq_header)s
          AND item.is_variation_item = 1
        ORDER BY structure.lft
    """, {"boq_header": boq_header}, as_dict=True)
    
    return rows
