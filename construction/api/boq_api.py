# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def require_boq_access(boq_header: str, ptype: str = "read") -> None:
    """Validate that the session user has the requested permission and scope on the BOQ Header."""
    if not boq_header:
        frappe.throw(_("BOQ Header is required."), frappe.ValidationError)
    if frappe.session.user == "Administrator":
        return
    if not frappe.db.exists("BOQ Header", boq_header):
        frappe.throw(_("BOQ Header {0} does not exist.").format(boq_header), frappe.DoesNotExistError)

    frappe.has_permission("BOQ Header", ptype=ptype, doc=boq_header, throw=True)


@frappe.whitelist()
def get_children(doctype, parent="", boq_header=None, is_root=False, **filters):
    """Get children for BOQ Structure tree view with IDOR access check."""
    if not boq_header:
        return []

    require_boq_access(boq_header, ptype="read")

    # Treat root label or is_root as top-level query
    if is_root or parent == "BOQ Structure" or not parent:
        parent_value = ""
        parent_fields = ""
    else:
        # Validate parent belongs to this boq_header
        parent_header = frappe.db.get_value("BOQ Structure", parent, "boq_header")
        if not parent_header or parent_header != boq_header:
            frappe.throw(
                _("Parent structure '{0}' does not belong to BOQ Header '{1}'.").format(parent, boq_header),
                frappe.PermissionError,
            )
        parent_value = parent
        parent_fields = ", `parent_structure` as parent"

    nodes = frappe.db.sql(
        f"""
		SELECT
			`name` as value,
			CONCAT(IFNULL(`wbs_code`,''), ' — ', `title`) as title,
			`is_group` as expandable,
            `item_count`,
            `total_contract_value`,
            `total_budgeted_cost`
			{parent_fields}
		FROM `tabBOQ Structure`
		WHERE IFNULL(`parent_structure`, '') = %(parent)s
		AND `docstatus` < 2
		AND `boq_header` = %(boq_header)s
		ORDER BY `lft`
	""",
        {"parent": parent_value, "boq_header": boq_header},
        as_dict=True,
    )

    return nodes


@frappe.whitelist()
def add_node():
    """Add a new BOQ Structure node from the tree view with permission enforcement."""
    from frappe.desk.treeview import make_tree_args

    args = frappe.local.form_dict
    args.doctype = "BOQ Structure"
    args = make_tree_args(**args)

    boq_header = args.get("boq_header")
    if boq_header:
        require_boq_access(boq_header, ptype="write")
    frappe.has_permission("BOQ Structure", ptype="create", throw=True)

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
    """Create a new BOQ Structure node from the tree view with permission check."""
    require_boq_access(boq_header, ptype="write")
    frappe.has_permission("BOQ Structure", ptype="create", throw=True)

    parent = parent_structure if parent_structure else ""

    doc = frappe.new_doc("BOQ Structure")
    doc.boq_header = boq_header
    doc.parent_structure = parent if parent else None
    doc.title = title or "New Node"
    doc.is_group = 1 if is_group else 0
    doc.insert()

    return {"success": True, "name": doc.name}


@frappe.whitelist()
def advance_boq_status(boq_header, target_status):
    """Advance BOQ status to next state with write permission check."""
    require_boq_access(boq_header, ptype="write")
    doc = frappe.get_doc("BOQ Header", boq_header)

    transitions = {"Draft": "Pricing", "Pricing": "Frozen", "Frozen": "Locked"}
    current_status = doc.status
    allowed_next = transitions.get(current_status)

    if target_status != allowed_next:
        frappe.throw(
            _("Invalid status transition from {0}. Next status should be {1}").format(
                current_status, allowed_next
            ),
            frappe.ValidationError,
        )

    doc.status = target_status
    doc.save()

    return {"success": True, "message": f"Status updated to {target_status}"}


@frappe.whitelist()
def export_boq_header_pdf(boq_header, column_config=None):
    """Export BOQ Header information only to PDF."""
    require_boq_access(boq_header, ptype="read")
    frappe.has_permission("BOQ Header", ptype="export", doc=boq_header, throw=True)

    from construction.services.boq_export_service import BOQExportService

    result = BOQExportService.export_header_to_pdf(boq_header, column_config)
    if result.get("success"):
        return {
            "success": True,
            "message": "BOQ Header PDF exported successfully",
            "file_url": result.get("file_url"),
            "file_name": result.get("file_name"),
        }
    return result


@frappe.whitelist()
def export_boq_header_excel(boq_header, column_config=None):
    """Export BOQ Header information only to Excel."""
    require_boq_access(boq_header, ptype="read")
    frappe.has_permission("BOQ Header", ptype="export", doc=boq_header, throw=True)

    from construction.services.boq_export_service import BOQExportService

    result = BOQExportService.export_header_to_excel(boq_header, column_config)
    if result.get("success"):
        return {
            "success": True,
            "message": "BOQ Header Excel exported successfully",
            "file_url": result.get("file_url"),
            "file_name": result.get("file_name"),
        }
    return result


@frappe.whitelist()
def export_boq_excel(boq_header, column_config=None):
    """Export full BOQ structure and items to Excel."""
    require_boq_access(boq_header, ptype="read")
    frappe.has_permission("BOQ Header", ptype="export", doc=boq_header, throw=True)

    from construction.services.boq_export_service import BOQExportService

    result = BOQExportService.export_to_excel(boq_header, column_config)
    if result.get("success"):
        return {
            "success": True,
            "message": "BOQ Excel exported successfully",
            "file_url": result.get("file_url"),
            "file_name": result.get("file_name"),
        }
    return result


@frappe.whitelist()
def export_boq_pdf(boq_header, column_config=None):
    """Export full BOQ structure and items to PDF."""
    require_boq_access(boq_header, ptype="read")
    frappe.has_permission("BOQ Header", ptype="export", doc=boq_header, throw=True)

    from construction.services.boq_export_service import BOQExportService

    result = BOQExportService.export_to_pdf(boq_header, column_config)
    if result.get("success"):
        return {
            "success": True,
            "message": "BOQ PDF exported successfully",
            "file_url": result.get("file_url"),
            "file_name": result.get("file_name"),
        }
    return result


@frappe.whitelist()
def import_boq_excel(file_url, boq_header, dry_run=1, confirmed_import_mode=None, row_resolutions=None):
    """Import BOQ from Excel with write permission checks."""
    require_boq_access(boq_header, ptype="write")

    from construction.services.boq_import_service import BOQImportService

    return BOQImportService.import_from_excel(
        file_url=file_url,
        boq_header=boq_header,
        dry_run=frappe.utils.cint(dry_run),
        confirmed_import_mode=confirmed_import_mode,
        row_resolutions=frappe.parse_json(row_resolutions) if row_resolutions else None,
    )


@frappe.whitelist()
def generate_boq_import_error_report(
    file_url, boq_header=None, confirmed_import_mode=None, row_resolutions=None
):
    """Generate an Excel review workbook with import errors and warnings."""
    if boq_header:
        require_boq_access(boq_header, ptype="read")

    from construction.services.boq_import_service import BOQImportService

    return BOQImportService.generate_import_error_report(
        file_url=file_url,
        boq_header=boq_header,
        confirmed_import_mode=confirmed_import_mode,
        row_resolutions=frappe.parse_json(row_resolutions) if row_resolutions else None,
    )


@frappe.whitelist()
def bulk_update_boq_item_stages(updates):
    """Bulk update BOQ Item Stage measurement/certification fields through normal validation."""
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_stage_measurement_ui"):
        frappe.throw(_("Stage measurement UI is disabled by Construction Settings."), frappe.ValidationError)

    frappe.has_permission("BOQ Item Stage", ptype="write", throw=True)

    allowed_fields = {
        "stage_status",
        "measured_executed_qty",
        "certified_qty",
        "percent_complete",
        "description",
    }
    payload = frappe.parse_json(updates) if isinstance(updates, str) else updates
    if not isinstance(payload, list):
        frappe.throw(_("Updates must be a list."), frappe.ValidationError)

    results = []
    for row in payload:
        stage_name = row.get("name")
        if not stage_name:
            continue

        stage = frappe.get_doc("BOQ Item Stage", stage_name)
        frappe.has_permission("BOQ Item Stage", ptype="write", doc=stage, throw=True)
        for fieldname in allowed_fields:
            if fieldname in row:
                stage.set(fieldname, row.get(fieldname))
        stage.save()
        results.append({"success": True, "name": stage.name})

    return {"success": True, "results": results}


# ---------------------------------------------------------------------------
# Variation Order (VO) helpers
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_variation_order(boq_header, reason=None, description=None, engineer_name=None):
    """Create a Draft Variation Order for the given Locked BOQ Header."""
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_variation_orders"):
        return {"success": False, "error": "Variation Orders are disabled by Construction Settings."}

    if not boq_header:
        return {"success": False, "error": "BOQ Header is required."}

    require_boq_access(boq_header, ptype="write")
    frappe.has_permission("Variation Order", ptype="create", throw=True)

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
    vo.insert()

    return {"success": True, "name": vo.name, "vo_number": vo.vo_number}


@frappe.whitelist()
def transition_variation_order(vo_name, new_status, client_approval_document=None):
    """Transition a Variation Order to the next status with role + signed-PDF checks."""
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_variation_orders"):
        frappe.throw(_("Variation Orders are disabled by Construction Settings."), frappe.ValidationError)

    # Uniform non-disclosing denial: missing and unauthorized names must be
    # indistinguishable (closes the existence oracle), and authorization
    # always precedes any row lock or data response.
    def _uniform_denial():
        frappe.throw(
            _("Variation Order {0} not found.").format(vo_name),
            frappe.DoesNotExistError,
        )

    # ── Phase 1: permission-safe, non-locking pre-check ──
    try:
        vo = frappe.get_doc("Variation Order", vo_name)
    except frappe.DoesNotExistError:
        vo = None
    if vo is None or not frappe.has_permission("Variation Order", "write", doc=vo):
        _uniform_denial()

    # ── Phase 2: acquire the row lock for atomic transition serialization ──
    locked_rows = frappe.db.sql(
        "SELECT name, status FROM `tabVariation Order` WHERE name = %s FOR UPDATE",
        (vo_name,),
        as_dict=True,
    )
    if not locked_rows:
        _uniform_denial()

    # ── Phase 3: revalidate authorization against post-lock state ──
    vo = frappe.get_doc("Variation Order", vo_name)
    if not frappe.has_permission("Variation Order", "write", doc=vo):
        _uniform_denial()

    if locked_rows[0].status == new_status:
        return {
            "success": True,
            "name": vo.name,
            "status": vo.status,
            "total_contract_delta": vo.total_contract_delta,
            "already_at_status": True,
        }

    # Establish atomic unique savepoint around the entire status transition
    savepoint = f"sp_vo_trans_{frappe.generate_hash(length=8)}"
    frappe.db.savepoint(savepoint)
    try:
        vo.status = new_status
        if new_status == "Approved by Client" and client_approval_document:
            vo.client_approval_document = client_approval_document

        vo.save()
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

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
    require_boq_access(boq_header, ptype="read")

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
    """Return the revised BOQ view for the given BOQ Header."""
    require_boq_access(boq_header, ptype="read")

    from construction.services.variation_orders import get_revised_boq_rows, get_revised_variation_rows

    return {
        "contract_rows": get_revised_boq_rows(boq_header),
        "variation_rows": get_revised_variation_rows(boq_header),
    }


@frappe.whitelist()
def create_material_request_for_vo(vo_name):
    """Create a Draft Material Request for variation items in an approved VO (idempotent & collision-safe)."""
    from construction.services.feature_flags import is_enabled

    if not is_enabled("enable_variation_orders"):
        frappe.throw(_("Variation Orders are disabled by Construction Settings."), frappe.ValidationError)

    if not vo_name:
        frappe.throw(_("Variation Order name is required."), frappe.ValidationError)

    frappe.has_permission("Variation Order", ptype="read", doc=vo_name, throw=True)
    frappe.has_permission("Material Request", ptype="create", throw=True)

    # Pessimistic row locking on VO
    locked_vo = frappe.db.sql(
        "SELECT name, status, boq_header, vo_number, project FROM `tabVariation Order` WHERE name = %(name)s FOR UPDATE",
        {"name": vo_name},
        as_dict=True,
    )
    if not locked_vo:
        frappe.throw(_("Variation Order {0} does not exist.").format(vo_name), frappe.DoesNotExistError)

    vo = frappe.get_doc("Variation Order", vo_name)
    require_boq_access(vo.boq_header, ptype="write")

    if vo.status != "Approved by Client":
        frappe.throw(
            _("Material Request can only be created from Approved by Client VOs."),
            frappe.ValidationError,
        )

    # Idempotency check with locking Current Read under MariaDB/InnoDB REPEATABLE READ
    existing_mr = frappe.db.sql(
        """
        SELECT name FROM `tabMaterial Request`
        WHERE (custom_variation_order = %(vo_name)s OR title = %(title)s)
          AND docstatus < 2
        LIMIT 1
        FOR UPDATE
        """,
        {"vo_name": vo.name, "title": f"VO Procurement: {vo.name}"},
        as_dict=True,
    )

    if existing_mr:
        mr_name = existing_mr[0].name
        return {
            "success": True,
            "name": mr_name,
            "material_request": mr_name,
            "already_existed": True,
        }

    variation_lines = [line for line in vo.lines if line.created_boq_item]
    if not variation_lines:
        frappe.throw(_("No variation items found in this VO."), frappe.ValidationError)

    resolved_company = getattr(vo, "company", None) or (
        frappe.db.get_value("Project", vo.project, "company") if getattr(vo, "project", None) else None
    )
    if not resolved_company:
        frappe.throw(
            _("Cannot create Material Request: Linked Project {0} has no Company assigned.").format(vo.project),
            frappe.ValidationError,
        )

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.company = resolved_company
    mr.title = f"VO Procurement: {vo.name}"
    if mr.meta.has_field("custom_variation_order"):
        mr.custom_variation_order = vo.name
    mr.schedule_date = frappe.utils.add_days(None, 30)

    for line in variation_lines:
        item_qty = (
            frappe.db.get_value("BOQ Item", line.created_boq_item, "quantity") if line.created_boq_item else None
        )
        raw_item = getattr(line, "item_code", None)
        if not raw_item and line.created_boq_item:
            cost_item = frappe.db.get_value("BOQ Item", line.created_boq_item, "cost_item")
            if cost_item and frappe.db.exists("Item", cost_item):
                raw_item = cost_item

        if not raw_item or not frappe.db.exists("Item", raw_item):
            frappe.throw(
                _(
                    "Row {0}: Valid ERPNext Item Code is required for variation item '{1}' to generate Material Request."
                ).format(line.idx, line.title),
                frappe.ValidationError,
            )

        mr.append(
            "items",
            {
                "item_code": raw_item,
                "description": line.title,
                "qty": flt(item_qty or line.revised_qty or line.quantity),
                "schedule_date": mr.schedule_date,
                "warehouse": "",
                "boq_header": vo.boq_header,
                "boq_structure": line.created_boq_structure,
                "boq_item": line.created_boq_item,
                "project": vo.project,
            },
        )

    mr.insert()
    return {"success": True, "name": mr.name, "material_request": mr.name}


@frappe.whitelist()
def get_boq_tree_summary(boq_header):
    """Return WBS tree summary with structure nodes and item counts."""
    require_boq_access(boq_header, ptype="read")

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


@frappe.whitelist()
def get_boq_structure_summary(boq_header):
    """Return BOQ header totals plus the WBS tree summary for the BOQ Structure form."""
    if not boq_header:
        return {"header": None, "nodes": [], "summary": {}}

    require_boq_access(boq_header, ptype="read")

    header = frappe.db.get_value(
        "BOQ Header",
        boq_header,
        ["name", "title", "project", "project_name", "total_contract_value", "total_budgeted_cost"],
        as_dict=True,
    )
    if not header:
        return {"header": None, "nodes": [], "summary": {}}

    nodes = get_boq_tree_summary(boq_header) or []
    leaf_count = sum(1 for node in nodes if not node.get("is_group"))
    group_count = sum(1 for node in nodes if node.get("is_group"))
    item_count = sum(frappe.utils.cint(node.get("item_count")) for node in nodes)

    return {
        "header": header,
        "nodes": nodes,
        "summary": {
            "structure_count": len(nodes),
            "group_count": group_count,
            "leaf_count": leaf_count,
            "item_count": item_count,
            "total_contract_value": header.get("total_contract_value") or 0,
            "total_budgeted_cost": header.get("total_budgeted_cost") or 0,
        },
    }


# ---------------------------------------------------------------------------
# Scope-aware BOQ helpers
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_boq_header_scope_context(boq_header: str) -> dict:
    """Return safe project/company context for a BOQ Header if authorized."""
    if not boq_header:
        frappe.throw(_("BOQ Header is required"))

    require_boq_access(boq_header, ptype="read")

    from construction.api.scope_context_api import get_user_scope_hierarchy

    header = frappe.get_doc("BOQ Header", boq_header)

    # Validate project is in user's authorized scope
    scope = get_user_scope_hierarchy()
    allowed_projects = {p.get("name") for p in scope.get("projects", [])}

    if header.project and allowed_projects and header.project not in allowed_projects:
        frappe.throw(
            _("You are not authorized to access this BOQ Header project."),
            frappe.PermissionError,
        )

    return {
        "project": header.project,
        "project_name": header.project_name,
        "company": header.company,
        "cost_center": header.cost_center,
    }
