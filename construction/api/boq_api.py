# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_children(doctype, parent="", boq_header=None, is_root=False, **filters):
    """Get children for BOQ Structure tree view."""
    # Treat root label or is_root as top-level query
    if is_root or parent == "BOQ Structure" or not parent:
        parent_value = ""
        conditions = "AND `boq_header` = %(boq_header)s" if boq_header else ""
        parent_fields = ""
    else:
        parent_value = parent
        conditions = ""
        parent_fields = ", `parent_structure` as parent"

    nodes = frappe.db.sql(
        f"""
		SELECT
			`name` as value,
			CONCAT(IFNULL(`wbs_code`,''), ' — ', `title`) as title,
			`is_group` as expandable
			{parent_fields}
		FROM `tabBOQ Structure`
		WHERE IFNULL(`parent_structure`, '') = %(parent)s
		AND `docstatus` < 2
		{conditions}
		ORDER BY `lft`
	""",
        {"parent": parent_value, "boq_header": boq_header},
        as_dict=True,
    )

    return nodes


@frappe.whitelist()
def add_node():
    """Add a new BOQ Structure node from the tree view."""
    from frappe.desk.treeview import make_tree_args

    args = frappe.local.form_dict
    args.doctype = "BOQ Structure"
    args = make_tree_args(**args)

    parent = args.get("parent_structure") or args.get("parent") or ""
    if parent == "BOQ Structure":
        parent = ""
    if parent and frappe.db.exists("BOQ Structure", parent):
        args.parent_structure = parent
    else:
        args.parent_structure = ""

    doc = frappe.new_doc("BOQ Structure")
    doc.update(args)
    doc.old_parent = ""
    doc.insert()
    return doc.name


@frappe.whitelist()
def create_boq_node(boq_header, parent_structure=None, title=None, is_group=0):
    """Create a new BOQ Structure node from the tree view."""
    try:
        # Get the parent structure if provided
        parent = parent_structure if parent_structure else ""

        # Create the BOQ Structure node
        doc = frappe.new_doc("BOQ Structure")
        doc.boq_header = boq_header
        doc.parent_structure = parent if parent else None
        doc.title = title or "New Node"
        doc.is_group = 1 if is_group else 0
        doc.insert()

        return {"success": True, "name": doc.name}
    except Exception as e:
        frappe.log_error(f"Error creating BOQ node: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def advance_boq_status(boq_header, target_status):
    """Advance BOQ status to next state."""
    try:
        doc = frappe.get_doc("BOQ Header", boq_header)

        # Define valid transitions
        transitions = {"Draft": "Pricing", "Pricing": "Frozen", "Frozen": "Locked"}

        current_status = doc.status
        allowed_next = transitions.get(current_status)

        if target_status != allowed_next:
            return {
                "success": False,
                "error": f"Invalid status transition from {current_status}. Next status should be {allowed_next}",
            }

        # Update status
        doc.status = target_status
        doc.save()

        return {"success": True, "message": f"Status updated to {target_status}"}
    except Exception as e:
        frappe.log_error(f"Error advancing BOQ status: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def export_boq_header_pdf(boq_header, column_config=None):
    """Export BOQ Header information only to PDF."""
    try:
        from construction.services.boq_export_service import BOQExportService

        # Generate PDF file with header info only
        result = BOQExportService.export_header_to_pdf(boq_header, column_config)

        if result.get("success"):
            return {
                "success": True,
                "message": "BOQ Header PDF exported successfully",
                "file_url": result.get("file_url"),
                "file_name": result.get("file_name"),
            }
        else:
            return result

    except Exception as e:
        frappe.log_error(f"PDF export error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def export_boq_header_excel(boq_header, column_config=None):
    """Export BOQ Header information only to Excel."""
    try:
        from construction.services.boq_export_service import BOQExportService

        # Generate Excel file with header info only
        result = BOQExportService.export_header_to_excel(boq_header, column_config)

        if result.get("success"):
            return {
                "success": True,
                "message": "BOQ Header exported successfully",
                "file_url": result.get("file_url"),
                "file_name": result.get("file_name"),
            }
        else:
            return result

    except Exception as e:
        frappe.log_error(f"Excel export error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def export_boq_excel(boq_header, column_config=None):
    """Export complete BOQ (Header + Structure + Items) to Excel."""
    try:
        from construction.services.boq_export_service import BOQExportService

        # Generate Excel file
        result = BOQExportService.export_to_excel(boq_header, column_config)

        if result.get("success"):
            return {
                "success": True,
                "message": "BOQ exported successfully",
                "file_url": result.get("file_url"),
                "file_name": result.get("file_name"),
            }
        else:
            return result

    except Exception as e:
        frappe.log_error(f"Excel export error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def export_boq_pdf(boq_header, column_config=None):
    """Export BOQ to PDF."""
    try:
        from construction.services.boq_export_service import BOQExportService

        # Generate PDF file
        result = BOQExportService.export_to_pdf(boq_header, column_config)

        if result.get("success"):
            return {
                "success": True,
                "message": "BOQ PDF exported successfully",
                "file_url": result.get("file_url"),
                "file_name": result.get("file_name"),
            }
        else:
            return result

    except Exception as e:
        frappe.log_error(f"PDF export error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def import_boq_excel(file_url, boq_header, dry_run=1, confirmed_import_mode=None, row_resolutions=None):
    """Import BOQ from Excel."""
    try:
        from construction.services.boq_import_service import BOQImportService

        result = BOQImportService.import_from_excel(
            file_url=file_url,
            boq_header=boq_header,
            dry_run=frappe.utils.cint(dry_run),
            confirmed_import_mode=confirmed_import_mode,
            row_resolutions=frappe.parse_json(row_resolutions) if row_resolutions else None,
        )

        return result
    except Exception as e:
        frappe.log_error(f"Excel import error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def generate_boq_import_error_report(file_url, boq_header=None, confirmed_import_mode=None, row_resolutions=None):
    """Generate an Excel review workbook with import errors and warnings."""
    try:
        from construction.services.boq_import_service import BOQImportService

        return BOQImportService.generate_import_error_report(
            file_url=file_url,
            boq_header=boq_header,
            confirmed_import_mode=confirmed_import_mode,
            row_resolutions=frappe.parse_json(row_resolutions) if row_resolutions else None,
        )
    except Exception as e:
        frappe.log_error(f"BOQ import error report API error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def bulk_update_boq_item_stages(updates):
    """Bulk update BOQ Item Stage measurement/certification fields through normal validation."""
    try:
        from construction.services.feature_flags import is_enabled

        if not is_enabled("enable_stage_measurement_ui"):
            return {"success": False, "error": "Stage measurement UI is disabled by Construction Settings."}

        allowed_fields = {
            "stage_status",
            "measured_executed_qty",
            "certified_qty",
            "percent_complete",
            "description",
        }
        payload = frappe.parse_json(updates) if isinstance(updates, str) else updates
        if not isinstance(payload, list):
            return {"success": False, "error": "Updates must be a list."}

        results = []
        for row in payload:
            stage_name = row.get("name")
            if not stage_name:
                results.append({"success": False, "error": "Missing stage name."})
                continue

            stage = frappe.get_doc("BOQ Item Stage", stage_name)
            for fieldname in allowed_fields:
                if fieldname in row:
                    stage.set(fieldname, row.get(fieldname))
            stage.save(ignore_permissions=True)
            results.append({"success": True, "name": stage.name})

        return {"success": all(row.get("success") for row in results), "results": results}
    except Exception as e:
        frappe.log_error(f"Bulk BOQ Item Stage update error: {str(e)}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Variation Order (VO) helpers
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_variation_order(boq_header, reason=None, description=None, engineer_name=None):
    """Create a Draft Variation Order for the given Locked BOQ Header.

    Gated by `enable_variation_orders` feature flag.
    """
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_variation_orders"):
        return {"success": False, "error": "Variation Orders are disabled by Construction Settings."}

    if not boq_header:
        return {"success": False, "error": "BOQ Header is required."}

    header_status = frappe.db.get_value("BOQ Header", boq_header, "status")
    if header_status != "Locked":
        return {
            "success": False,
            "error": f"BOQ Header {boq_header} must be Locked to raise a Variation Order (current: {header_status}).",
        }

    vo = frappe.new_doc("Variation Order")
    vo.boq_header = boq_header
    vo.status = "Draft"
    if reason:
        vo.reason = reason
    if description:
        vo.description = description
    if engineer_name:
        vo.engineer_name = engineer_name
    vo.flags.ignore_permissions = True
    vo.insert(ignore_permissions=True)

    return {"success": True, "name": vo.name, "vo_number": vo.vo_number}


@frappe.whitelist()
def transition_variation_order(vo_name, new_status, client_approval_document=None):
    """Transition a Variation Order to the next status with role + signed-PDF checks.

    Allowed transitions and required artefacts are enforced inside the
    Variation Order controller. The save is wrapped so that an invalid
    transition surfaces as ``{"success": False, "error": ...}`` rather than
    a 500.
    """
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_variation_orders"):
        return {"success": False, "error": "Variation Orders are disabled by Construction Settings."}

    if not vo_name or not new_status:
        return {"success": False, "error": "Variation Order name and new status are required."}

    try:
        vo = frappe.get_doc("Variation Order", vo_name)
    except frappe.DoesNotExistError:
        return {"success": False, "error": f"Variation Order {vo_name} does not exist."}

    if not frappe.has_permission("Variation Order", "write", doc=vo):
        return {"success": False, "error": "You do not have permission to modify this Variation Order."}

    vo.status = new_status
    if new_status == "Approved by Client" and client_approval_document:
        vo.client_approval_document = client_approval_document
    vo.flags.ignore_permissions = True
    try:
        vo.save(ignore_permissions=True)
    except frappe.ValidationError as e:
        return {"success": False, "error": str(e)}
    vo.reload()

    return {
        "success": True,
        "name": vo.name,
        "status": vo.status,
        "total_contract_delta": vo.total_contract_delta,
    }


@frappe.whitelist()
def get_variation_order_summary(boq_header):
    """Return VO summary metrics for a BOQ Header (counts by status + total delta)."""
    rows = frappe.db.sql(
        """
        select
            vo.status,
            count(*) as count,
            coalesce(sum(vo.total_contract_delta), 0) as total_delta
        from `tabVariation Order` vo
        where vo.boq_header = %(boq_header)s
          and vo.docstatus < 2
        group by vo.status
        """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    counts = {r.status: {"count": r.count, "total_delta": float(r.total_delta or 0)} for r in rows}
    return {"boq_header": boq_header, "by_status": counts}


@frappe.whitelist()
def is_variation_orders_enabled():
    """Client-side boolean helper for the rollout flag."""
    from construction.services.feature_flags import is_enabled

    return {"enabled": bool(is_enabled("enable_variation_orders"))}


@frappe.whitelist()
def get_revised_boq_view(boq_header):
    """Return the revised BOQ view for the given BOQ Header.

    Includes contract rows with approved VO deltas and variation items
    created by approved New Item VOs.
    """
    from construction.services.variation_orders import get_revised_boq_rows, get_revised_variation_rows

    return {
        "contract_rows": get_revised_boq_rows(boq_header),
        "variation_rows": get_revised_variation_rows(boq_header),
    }


@frappe.whitelist()
def create_material_request_for_vo(vo_name):
    """Create a Draft Material Request for variation items in an approved VO."""
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_variation_orders"):
        return {"success": False, "error": "Variation Orders are disabled by Construction Settings."}

    try:
        vo = frappe.get_doc("Variation Order", vo_name)
    except frappe.DoesNotExistError:
        return {"success": False, "error": f"Variation Order {vo_name} does not exist."}

    if vo.status != "Approved by Client":
        return {"success": False, "error": "Material Request can only be created from Approved by Client VOs."}

    variation_lines = [line for line in vo.lines if line.created_boq_item]
    if not variation_lines:
        return {"success": False, "error": "No variation items found in this VO."}

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.title = f"VO Procurement: {vo.vo_number}"
    mr.schedule_date = frappe.utils.add_days(None, 30)
    mr.flags.ignore_permissions = True

    for line in variation_lines:
        item_qty = frappe.db.get_value("BOQ Item", line.created_boq_item, "quantity")
        if not line.item_code:
            frappe.throw(_("Row {0}: Item Code (standard ERPNext Item) is required to generate Material Request.").format(line.idx))

        mr.append("items", {
            "item_code": line.item_code,
            "description": line.title,
            "qty": flt(item_qty),
            "schedule_date": mr.schedule_date,
            "warehouse": "",
            "boq_header": vo.boq_header,
            "boq_structure": line.created_boq_structure,
            "boq_item": line.created_boq_item,
        })

    mr.insert(ignore_permissions=True)

    return {"success": True, "name": mr.name, "material_request": mr.name}


@frappe.whitelist()
def get_boq_tree_summary(boq_header):
    """Return WBS tree summary with structure nodes and item counts."""
    structures = frappe.db.sql(
        """
        SELECT s.name, s.title, s.wbs_code, s.is_group, s.lft, s.rgt,
               s.parent_structure, COUNT(i.name) as item_count
        FROM `tabBOQ Structure` s
        LEFT JOIN `tabBOQ Item` i ON i.structure = s.name AND i.docstatus < 2
        WHERE s.boq_header = %(boq_header)s AND s.docstatus < 2
        GROUP BY s.name
        ORDER BY s.lft
        """,
        {"boq_header": boq_header},
        as_dict=True,
    )
    return structures
