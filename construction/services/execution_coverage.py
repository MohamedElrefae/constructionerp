"""Authorized read-only service and streaming export for WBS P3 Execution Coverage.

Security & product invariants:
- Entry gate via ``execution_tree_access.authorize(project, "read")`` (enforces
  ``BROWSE_ROLES``, active ``User Scope Context``, and native ``Project`` read).
- Authorizes explicit filter IDs and enforces the full native
  ``BOQ Header -> BOQ Item -> BOQ Item Stage`` read chain (``frappe.get_list``
  plus ``frappe.has_permission(..., "read", doc=...)``) before any aggregation,
  search, grouping, pagination, or export.
- Never mutates the database (zero ``File`` inserts; downloads stream directly).
- Never falls back to ``BOQ Item.planned_execution_node`` for unmapped Stages.
- Never sums quantities across BOQ Items or mixed UOMs.
- Fails closed with an explicit limit response when population caps are exceeded.
"""

from __future__ import annotations

import csv
import io
import re

import frappe
import xlsxwriter
from frappe import _
from frappe.utils.xlsxutils import ILLEGAL_CHARACTERS_RE, get_sanitized_sheet_name

from construction.construction.utils.export_sanitizer import sanitize_spreadsheet_value
from construction.services import execution_coverage_rules as coverage_rules
from construction.services import execution_mapping
from construction.services import execution_tree_access as access
from construction.services import execution_tree_rules as tree_rules

_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")

# Configurable caps so tests can verify fail-closed limit handling deterministically.
MAX_POPULATION_HEADERS = coverage_rules.MAX_POPULATION_HEADERS
MAX_POPULATION_STRUCTURES = coverage_rules.MAX_POPULATION_STRUCTURES
MAX_POPULATION_ITEMS = coverage_rules.MAX_POPULATION_ITEMS
MAX_POPULATION_STAGES = coverage_rules.MAX_POPULATION_STAGES
EXPORT_MAX = coverage_rules.EXPORT_MAX

_BOQ_VISIBILITY_DOCTYPES = frozenset({"BOQ Header", "BOQ Structure", "BOQ Item", "BOQ Item Stage"})


def _raise_rule_violation(error):
    code = getattr(error, "code", "")
    if code == "invalid_identifier":
        frappe.throw(_("Invalid filter value."), frappe.ValidationError)
    if code == "invalid_integer":
        frappe.throw(_("Page and page size must be valid positive integers."), frappe.ValidationError)
    if code == "invalid_mapping_state":
        frappe.throw(_("Unsupported mapping state filter."), frappe.ValidationError)
    if code == "invalid_stage_status":
        frappe.throw(_("Unsupported stage status filter."), frappe.ValidationError)
    if code == "invalid_view_mode":
        frappe.throw(_("Unsupported view mode."), frappe.ValidationError)
    if code == "invalid_export_format":
        frappe.throw(_("Unsupported export format."), frappe.ValidationError)
    if code == "request_too_large":
        frappe.throw(_("Request payload is too large."), frappe.ValidationError)
    if code == "invalid_request":
        frappe.throw(_("Request payload must be an object."), frappe.ValidationError)
    if code == "unknown_argument":
        frappe.throw(_("Unknown request argument."), frappe.ValidationError)
    frappe.throw(_("Invalid request parameters."), frappe.ValidationError)


def _translate_access_error(error):
    if isinstance(error, access.AccessDenied | access.UnsupportedProfile | access.IntegrityFailure):
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if isinstance(error, coverage_rules.CoverageRuleViolation | tree_rules.RuleViolation):
        _raise_rule_violation(error)
    raise error


def _localized_labels():
    return {
        "state_healthy_linked": _("Healthy Linked"),
        "state_unlinked": _("Unmapped"),
        "state_link_issues": _("Needs Review"),
        "issue_disabled_node": _("Disabled Location"),
        "issue_disabled_ancestor": _("Disabled Ancestor"),
        "issue_missing_node": _("Missing Location"),
        "issue_project_mismatch": _("Project Mismatch"),
        "issue_group_node": _("Group Node Link"),
        "issue_broken_parent": _("Broken Ancestor Link"),
        "issue_cycle": _("Execution Tree Cycle"),
        "group_full": _("Full"),
        "group_partial": _("Partial"),
        "group_unmapped": _("Unmapped"),
        "group_needs_review": _("Needs Review"),
        "group_filtered_out": _("Zero Matching Stages"),
        "group_no_stages": _("No Stages"),
        "group_no_visible_stages": _("No visible Stages"),
        "view_stages": _("Stages"),
        "view_items": _("Items Summary"),
        "conflict_node_with_unlinked": _(
            "Filtering by both an Execution Location and Unmapped Stages cannot match any Stage because unmapped Stages have no Execution Location."
        ),
        "disclaimer": _(
            "Mapping completeness reflects Stage-to-location link counts only — it does not represent quantity balance, physical execution, certification, or financial completion."
        ),
        "meta_report": _("Report"),
        "meta_report_value": _("Execution Coverage"),
        "meta_project": _("Project"),
        "meta_view": _("View"),
        "meta_exported_rows": _("Exported Rows"),
        "meta_total_matching_rows": _("Total Matching Rows"),
        "meta_truncated": _("Truncated"),
        "meta_yes": _("Yes"),
        "meta_no": _("No"),
        "meta_truncation_notice": _("Truncation Notice"),
        "meta_summary_total_stages": _("Summary — Matching Stages"),
        "meta_summary_healthy_linked": _("Summary — Healthy Linked"),
        "meta_summary_unmapped": _("Summary — Unmapped"),
        "meta_summary_needs_review": _("Summary — Needs Review"),
        "meta_summary_disabled_links": _("Summary — Disabled Links"),
        "meta_summary_integrity_issues": _("Summary — Integrity Issues"),
        "meta_summary_completeness": _("Summary — Mapping Completeness"),
        "meta_summary_items_total": _("Summary — BOQ Items in Scope"),
        "meta_summary_items_no_stages": _("Summary — Items Without Stages"),
        "meta_summary_items_filtered_out": _("Summary — Items With Zero Matching Stages"),
        "meta_notice": _("Notice"),
        "col_stage": _("Stage"),
        "col_stage_code": _("Stage Code"),
        "col_stage_name": _("Stage Name"),
        "col_stage_status": _("Stage Status"),
        "col_mapping_status": _("Mapping Status"),
        "col_issue_detail": _("Issue Detail"),
        "col_ebs_code": _("Execution Code"),
        "col_node_title": _("Execution Location"),
        "col_node_path": _("Execution Path"),
        "col_planned_qty": _("Planned Qty"),
        "col_uom": _("UOM"),
        "col_boq_item": _("BOQ Item"),
        "col_wbs_code": _("Commercial WBS Code"),
        "col_item_title": _("Item Title"),
        "col_boq_header": _("BOQ Header"),
        "col_header_type": _("Header Type"),
        "col_header_status": _("Header Status"),
        "col_item_planning_default": _("Item Planning Default"),
        "col_item_group": _("Item Group"),
        "col_total_item_stages": _("Total Item Stages"),
        "col_matching_stages": _("Matching Stages"),
        "col_healthy_linked": _("Healthy Linked"),
        "col_unmapped": _("Unmapped"),
        "col_needs_review": _("Needs Review"),
        "col_disabled_links": _("Disabled Links"),
        "col_integrity_issues": _("Integrity Issues"),
        "col_item_qty": _("Item Qty"),
        "col_stage_planned_qty_sum": _("Stage Planned Qty Sum (Single Item)"),
        "col_status": _("Status"),
    }


def _require_schema_ready():
    if not frappe.db.table_exists(tree_rules.NODE_DOCTYPE):
        frappe.throw(
            _("Execution tree schema is not installed. Run bench migrate."),
            frappe.ValidationError,
        )
    if not execution_mapping.require_mapping_column("BOQ Item", "planned_execution_node"):
        frappe.throw(
            _("Execution mapping schema is not installed. Run bench migrate."),
            frappe.ValidationError,
        )
    if not execution_mapping.require_mapping_column("BOQ Item Stage", "execution_node"):
        frappe.throw(
            _("Execution mapping schema is not installed. Run bench migrate."),
            frappe.ValidationError,
        )


def _has_partial_visibility(user, *, rejected_by_has_permission=False):
    if user == "Administrator":
        return False
    if rejected_by_has_permission:
        return True
    try:
        user_perms = frappe.permissions.get_user_permissions(user) or {}
    except Exception:
        return True
    if any(dt in user_perms for dt in _BOQ_VISIBILITY_DOCTYPES):
        return True
    for rows in user_perms.values():
        for perm in rows or ():
            if perm.get("applicable_for") in _BOQ_VISIBILITY_DOCTYPES:
                return True
    for dt in ("BOQ Header", "BOQ Item", "BOQ Item Stage"):
        try:
            role_perms = frappe.permissions.get_role_permissions(dt, user=user) or {}
            if role_perms.get("has_if_owner_enabled"):
                return True
        except Exception:
            return True
    return False


def _read_project_nodes(project):
    rows = frappe.db.sql(
        "SELECT name, title, project, company, parent_node, is_group, disabled, ebs_code, modified "
        "FROM `tabExecution Breakdown Node` WHERE project=%s "
        "ORDER BY name LIMIT %s",
        (project, tree_rules.MAX_NODES + 1),
        as_dict=True,
    )
    if len(rows) > tree_rules.MAX_NODES:
        frappe.throw(_("The execution tree exceeds its supported size."), frappe.ValidationError)
    return [
        {
            "name": row.get("name"),
            "title": row.get("title"),
            "project": row.get("project"),
            "company": row.get("company"),
            "parent_node": row.get("parent_node") or None,
            "is_group": int(row.get("is_group") or 0),
            "disabled": int(row.get("disabled") or 0),
            "ebs_code": row.get("ebs_code"),
            "modified": str(row.get("modified")) if row.get("modified") is not None else None,
        }
        for row in rows
    ]


def _read_cross_project_node_stubs(node_names, expected_project):
    """Look up non-project node existence without disclosing foreign titles or paths."""
    missing_names = sorted({name for name in node_names if name})
    if not missing_names:
        return []
    rows = frappe.db.get_all(
        tree_rules.NODE_DOCTYPE,
        filters={"name": ["in", missing_names]},
        fields=["name", "project", "is_group", "disabled"],
        limit_page_length=len(missing_names),
    )
    stubs = []
    for row in rows:
        if row.get("project") != expected_project:
            stubs.append(
                {
                    "name": row.get("name"),
                    "project": row.get("project"),
                    "is_group": int(row.get("is_group") or 0),
                    "disabled": int(row.get("disabled") or 0),
                    "ebs_code": "",
                    "title": "",
                    "parent_node": None,
                }
            )
    return stubs


def _authorize_explicit_filters(norm_filters, project_nodes_by_name):
    """Authorize explicit filter IDs against ``project`` and native read permissions."""
    project = norm_filters["project"]
    boq_header = norm_filters["boq_header"]
    boq_structure = norm_filters["boq_structure"]
    boq_item = norm_filters["boq_item"]
    execution_node = norm_filters["execution_node"]

    if boq_header:
        header_row = frappe.db.get_value(
            "BOQ Header", boq_header, ["name", "project"], as_dict=True
        )
        if not header_row or header_row.project != project:
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        if not frappe.has_permission("BOQ Header", "read", doc=boq_header):
            frappe.throw(_("Not permitted."), frappe.PermissionError)

    structure_row = None
    if boq_structure:
        structure_row = frappe.db.get_value(
            "BOQ Structure",
            boq_structure,
            ["name", "project", "boq_header", "lft", "rgt"],
            as_dict=True,
        )
        if not structure_row or structure_row.project != project:
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        if not structure_row.boq_header or not frappe.has_permission(
            "BOQ Header", "read", doc=structure_row.boq_header
        ):
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        if not frappe.has_permission("BOQ Structure", "read", doc=boq_structure):
            frappe.throw(_("Not permitted."), frappe.PermissionError)

    if boq_item:
        item_row = frappe.db.get_value(
            "BOQ Item", boq_item, ["name", "boq_header", "structure"], as_dict=True
        )
        if not item_row or not item_row.boq_header:
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        item_project = frappe.db.get_value("BOQ Header", item_row.boq_header, "project")
        if item_project != project:
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        if not frappe.has_permission("BOQ Header", "read", doc=item_row.boq_header):
            frappe.throw(_("Not permitted."), frappe.PermissionError)
        if not frappe.has_permission("BOQ Item", "read", doc=boq_item):
            frappe.throw(_("Not permitted."), frappe.PermissionError)

    if execution_node and execution_node not in project_nodes_by_name:
        frappe.throw(_("Execution location was not found in this Project."), frappe.ValidationError)

    return structure_row


def _limit_exceeded_payload(limit_type, limit_value, norm_filters, labels):
    message = _(
        "Too many records match the current scope (more than {0}). Narrow the BOQ Header, BOQ Structure, or BOQ Item filter to view complete coverage."
    ).format(limit_value)
    return {
        "ok": False,
        "limit_exceeded": True,
        "limit_type": limit_type,
        "limit": limit_value,
        "message": message,
        "project": norm_filters["project"],
        "filters": norm_filters,
        "has_stage_filters": bool(
            norm_filters["execution_node"]
            or norm_filters["mapping_state"] != "all"
            or norm_filters["stage_status"]
            or norm_filters["search"]
        ),
        "filter_conflict": None,
        "disclaimer": labels["disclaimer"],
        "summary": None,
        "population_summary": None,
        "item_group_counts": None,
        "view_mode": norm_filters["view_mode"],
        "headers": [],
        "rows": [],
        "pagination": {
            "page": norm_filters["page"],
            "page_size": norm_filters["page_size"],
            "total_rows": 0,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        },
    }


def _compute_authorized_coverage(norm_filters):
    """Run the full authorized coverage pipeline shared by view and export."""
    _require_schema_ready()

    project = norm_filters["project"]
    try:
        access.authorize(project, "read")
    except Exception as error:
        _translate_access_error(error)

    for dt in ("BOQ Header", "BOQ Item", "BOQ Item Stage"):
        if not frappe.has_permission(dt, "read"):
            frappe.throw(_("Not permitted."), frappe.PermissionError)

    labels = _localized_labels()
    project_nodes = _read_project_nodes(project)
    project_nodes_by_name = coverage_rules.index_nodes_by_name(project_nodes)
    structure_filter_row = _authorize_explicit_filters(norm_filters, project_nodes_by_name)

    user = frappe.session.user
    rejected_by_has_permission = False

    # 1. Authorized BOQ Headers in project (Decision #3: all readable headers across statuses & types)
    header_filters = {"project": project}
    if norm_filters["boq_header"]:
        header_filters["name"] = norm_filters["boq_header"]

    raw_headers = frappe.get_list(
        "BOQ Header",
        filters=header_filters,
        fields=["name", "title", "boq_type", "status", "project"],
        order_by="name asc",
        limit_page_length=MAX_POPULATION_HEADERS + 1,
    )
    if len(raw_headers) > MAX_POPULATION_HEADERS:
        return _limit_exceeded_payload("headers", MAX_POPULATION_HEADERS, norm_filters, labels)

    headers_by_name = {}
    for row in raw_headers:
        name = row.get("name")
        if name and frappe.has_permission("BOQ Header", "read", doc=name):
            headers_by_name[name] = row
        else:
            rejected_by_has_permission = True

    header_options = [
        {
            "name": row["name"],
            "title": row.get("title") or row["name"],
            "boq_type": row.get("boq_type") or "",
            "status": row.get("status") or "",
        }
        for row in headers_by_name.values()
    ]

    # 2. Optional BOQ Structure subtree resolution (NestedSet lft/rgt)
    allowed_structure_names = None
    empty_population = not headers_by_name
    if not empty_population and structure_filter_row is not None:
        if structure_filter_row.boq_header not in headers_by_name:
            empty_population = True
        else:
            subtree_structures = frappe.get_list(
                "BOQ Structure",
                filters={
                    "boq_header": structure_filter_row.boq_header,
                    "lft": [">=", structure_filter_row.lft],
                    "rgt": ["<=", structure_filter_row.rgt],
                },
                fields=["name"],
                order_by="lft asc, name asc",
                limit_page_length=MAX_POPULATION_STRUCTURES + 1,
            )
            if len(subtree_structures) > MAX_POPULATION_STRUCTURES:
                return _limit_exceeded_payload(
                    "structures", MAX_POPULATION_STRUCTURES, norm_filters, labels
                )
            allowed_structure_names = [
                row["name"]
                for row in subtree_structures
                if row.get("name") and frappe.has_permission("BOQ Structure", "read", doc=row["name"])
            ]
            if not allowed_structure_names:
                empty_population = True

    # 3. Authorized BOQ Items within authorized Headers (and optional Structure/Item filters)
    authorized_items_by_name = {}
    if not empty_population:
        item_filters = {"boq_header": ["in", sorted(headers_by_name)]}
        if norm_filters["boq_item"]:
            item_filters["name"] = norm_filters["boq_item"]
        if allowed_structure_names is not None:
            item_filters["structure"] = ["in", allowed_structure_names]

        raw_items = frappe.get_list(
            "BOQ Item",
            filters=item_filters,
            fields=["name", "boq_header", "structure", "quantity", "unit", "planned_execution_node"],
            order_by="name asc",
            limit_page_length=MAX_POPULATION_ITEMS + 1,
        )
        if len(raw_items) > MAX_POPULATION_ITEMS:
            return _limit_exceeded_payload("items", MAX_POPULATION_ITEMS, norm_filters, labels)

        for row in raw_items:
            name = row.get("name")
            if (
                name
                and row.get("boq_header") in headers_by_name
                and frappe.has_permission("BOQ Item", "read", doc=name)
            ):
                authorized_items_by_name[name] = row
            else:
                rejected_by_has_permission = True

    # Batch-fetch BOQ Structure display metadata for authorized Items
    structures_by_name = {}
    structure_ids = sorted(
        {row.get("structure") for row in authorized_items_by_name.values() if row.get("structure")}
    )
    if structure_ids:
        struct_rows = frappe.get_list(
            "BOQ Structure",
            filters={"name": ["in", structure_ids]},
            fields=["name", "title", "wbs_code", "description", "boq_header"],
            limit_page_length=len(structure_ids),
        )
        for srow in struct_rows:
            if srow.get("name") and srow.get("boq_header") in headers_by_name:
                structures_by_name[srow["name"]] = srow

    # 4. Authorized BOQ Item Stages within authorized Header -> Item chain
    authorized_stages = []
    if authorized_items_by_name:
        stage_filters = {
            "boq_header": ["in", sorted(headers_by_name)],
            "boq_item": ["in", sorted(authorized_items_by_name)],
        }
        raw_stages = frappe.get_list(
            "BOQ Item Stage",
            filters=stage_filters,
            fields=[
                "name",
                "project",
                "boq_header",
                "boq_structure",
                "boq_item",
                "stage_code",
                "stage_name",
                "stage_status",
                "execution_node",
                "planned_qty",
            ],
            order_by="name asc",
            limit_page_length=MAX_POPULATION_STAGES + 1,
        )
        if len(raw_stages) > MAX_POPULATION_STAGES:
            return _limit_exceeded_payload("stages", MAX_POPULATION_STAGES, norm_filters, labels)

        for row in raw_stages:
            name = row.get("name")
            item_name = row.get("boq_item")
            parent_item = authorized_items_by_name.get(item_name)
            if (
                name
                and parent_item is not None
                and row.get("boq_header") in headers_by_name
                and row.get("boq_header") == parent_item.get("boq_header")
                and frappe.has_permission("BOQ Item Stage", "read", doc=name)
            ):
                authorized_stages.append(row)
            else:
                rejected_by_has_permission = True

    # Build enriched Item dicts for pure evaluation
    enriched_items = []
    referenced_external_nodes = set()
    for item_name, row in authorized_items_by_name.items():
        header = headers_by_name[row["boq_header"]]
        struct = structures_by_name.get(row.get("structure")) or {}
        planned_node = (str(row.get("planned_execution_node") or "").strip()) or None
        if planned_node and planned_node not in project_nodes_by_name:
            referenced_external_nodes.add(planned_node)
        enriched_items.append(
            {
                "name": item_name,
                "boq_header": row["boq_header"],
                "header_title": header.get("title") or row["boq_header"],
                "header_type": header.get("boq_type") or "",
                "header_status": header.get("status") or "",
                "structure": row.get("structure") or "",
                "wbs_code": struct.get("wbs_code") or "",
                "item_title": struct.get("title") or item_name,
                "item_description": struct.get("description") or "",
                "quantity": row.get("quantity"),
                "unit": row.get("unit") or "",
                "planned_execution_node": planned_node,
            }
        )

    for srow in authorized_stages:
        exec_node = (str(srow.get("execution_node") or "").strip()) or None
        if exec_node and exec_node not in project_nodes_by_name:
            referenced_external_nodes.add(exec_node)

    extra_nodes = _read_cross_project_node_stubs(referenced_external_nodes, project)
    partial_visibility = _has_partial_visibility(
        user, rejected_by_has_permission=rejected_by_has_permission
    )

    result = coverage_rules.evaluate_coverage(
        project=project,
        items=enriched_items,
        stages=authorized_stages,
        project_nodes=project_nodes,
        extra_nodes=extra_nodes,
        filters=norm_filters,
        partial_visibility=partial_visibility,
        labels=labels,
    )
    result["headers"] = header_options
    return result


def get_execution_coverage(
    *,
    project=None,
    boq_header=None,
    boq_structure=None,
    boq_item=None,
    execution_node=None,
    mapping_state=None,
    stage_status=None,
    search=None,
    view_mode=None,
    page=None,
    page_size=None,
):
    """Return paginated authorized Execution Coverage data for the given filters."""
    try:
        norm_filters = coverage_rules.normalize_filters(
            project=project,
            boq_header=boq_header,
            boq_structure=boq_structure,
            boq_item=boq_item,
            execution_node=execution_node,
            mapping_state=mapping_state,
            stage_status=stage_status,
            search=search,
            view_mode=view_mode,
            page=page,
            page_size=page_size,
        )
    except coverage_rules.CoverageRuleViolation as error:
        _raise_rule_violation(error)

    result = _compute_authorized_coverage(norm_filters)
    # Strip internal unpaginated lists before returning JSON response
    result.pop("_all_stage_rows", None)
    result.pop("_all_item_rows", None)
    result.pop("_all_no_stages_rows", None)
    return result


def _sanitize_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int | float):
        return value
    return sanitize_spreadsheet_value(str(value))


def serialize_csv_bytes(export_table):
    """Serialize canonical export table as UTF-8 BOM CSV bytes with formula neutralization."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    for row in export_table["all_rows"]:
        writer.writerow([_sanitize_cell(cell) for cell in row])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def serialize_xlsx_bytes(export_table):
    """Serialize canonical export table as XLSX bytes preserving numeric cells & formula safety."""
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"constant_memory": True})
    ws = wb.add_worksheet(get_sanitized_sheet_name("Execution Coverage"))
    bold_fmt = wb.add_format({"bold": True})

    meta_len = len(export_table["metadata_rows"])
    header_row_idx = meta_len + 1  # blank separator row sits at index meta_len

    for row_idx, row in enumerate(export_table["all_rows"]):
        row_fmt = bold_fmt if row_idx == header_row_idx else None
        for col_idx, raw_cell in enumerate(row):
            cell = _sanitize_cell(raw_cell)
            cell_fmt = bold_fmt if (row_idx < meta_len and col_idx == 0) else row_fmt
            if isinstance(cell, int | float) and not isinstance(cell, bool):
                ws.write_number(row_idx, col_idx, cell, cell_fmt)
            else:
                text = ILLEGAL_CHARACTERS_RE.sub("", str(cell))
                ws.write_string(row_idx, col_idx, text, cell_fmt)

    wb.close()
    buf.seek(0)
    return buf.getvalue()


def _safe_filename_segment(text):
    cleaned = _FILENAME_SAFE_RE.sub("_", str(text or "")).strip("._")
    return cleaned or "project"


def build_execution_coverage_export(
    *,
    project=None,
    boq_header=None,
    boq_structure=None,
    boq_item=None,
    execution_node=None,
    mapping_state=None,
    stage_status=None,
    search=None,
    view_mode=None,
    export_format=None,
):
    """Authorize, build, and serialize an in-memory CSV or XLSX download (zero DB writes)."""
    try:
        norm_filters = coverage_rules.normalize_filters(
            project=project,
            boq_header=boq_header,
            boq_structure=boq_structure,
            boq_item=boq_item,
            execution_node=execution_node,
            mapping_state=mapping_state,
            stage_status=stage_status,
            search=search,
            view_mode=view_mode,
            export_format=export_format,
        )
    except coverage_rules.CoverageRuleViolation as error:
        _raise_rule_violation(error)

    result = _compute_authorized_coverage(norm_filters)
    if result.get("limit_exceeded"):
        frappe.throw(
            _(
                "Too many records match the current scope (more than {0}). Narrow the BOQ Header, BOQ Structure, or BOQ Item filter before exporting."
            ).format(result["limit"]),
            frappe.ValidationError,
        )

    labels = _localized_labels()
    export_table = coverage_rules.build_export_table(
        result,
        view_mode=norm_filters["view_mode"],
        max_rows=EXPORT_MAX,
        labels=labels,
    )
    if export_table["truncated"]:
        labels["truncation_notice_value"] = _(
            "Export capped at {0} rows; {1} additional matching rows were omitted. Narrow filters to export all rows."
        ).format(export_table["max_rows"], export_table["omitted_rows"])
        export_table = coverage_rules.build_export_table(
            result,
            view_mode=norm_filters["view_mode"],
            max_rows=EXPORT_MAX,
            labels=labels,
        )

    fmt = norm_filters["export_format"]
    safe_proj = _safe_filename_segment(norm_filters["project"])
    mode = norm_filters["view_mode"]
    if fmt == "xlsx":
        content = serialize_xlsx_bytes(export_table)
        filename = f"execution_coverage_{safe_proj}_{mode}.xlsx"
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = serialize_csv_bytes(export_table)
        filename = f"execution_coverage_{safe_proj}_{mode}.csv"
        content_type = "text/csv; charset=utf-8"

    return {
        "filename": filename,
        "filecontent": content,
        "content_type": content_type,
        "exported_rows": export_table["exported_rows"],
        "total_matching_rows": export_table["total_matching_rows"],
        "truncated": export_table["truncated"],
    }
