# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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
