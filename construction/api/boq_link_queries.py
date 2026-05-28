import frappe

from construction.services.boq_scope_filters import (
    ALLOWED_TRANSACTION_BOQ_STATUSES,
    append_allowed_status_filter,
    apply_header_filters,
    apply_header_scope,
    get_scope_payload,
    resolve_query_scope,
)
from construction.services.scope_resolution import get_scope_token


def _as_dict(filters):
    if not filters:
        return {}
    if isinstance(filters, str):
        return frappe.parse_json(filters) or {}
    return filters


def _extract_enforce_scope(filters, enforce_scope):
    if enforce_scope is not None:
        return enforce_scope
    return filters.pop("enforce_scope", None)


def _limit_values(txt, start, page_len):
    return {
        "txt": f"%{txt or ''}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }


def _join_project_sql(join_project):
    return "INNER JOIN `tabProject` p ON p.name = h.project" if join_project else ""


def _attach_scope_response(scope):
    if not scope:
        return
    frappe.local.response["boq_scope_token"] = get_scope_token(frappe.session.user)
    frappe.local.response["boq_scope_type"] = scope.scope_type
    if not scope.project:
        frappe.local.response["boq_scope_warning"] = (
            "No project selected — BOQ results are not project-scoped."
        )


def _truthy(value):
    return value in (True, 1, "1", "true", "True", "yes", "Yes")


def _gate_is_closed(filters):
    return _truthy(filters.get("require_gate")) and not _truthy(filters.get("gate_open"))


@frappe.whitelist()
def get_boq_scope_token():
    """Return current BOQ scope details for client-side drift checks."""
    return get_scope_payload(frappe.session.user)


@frappe.whitelist()
def get_allowed_transaction_boq_statuses():
    return ALLOWED_TRANSACTION_BOQ_STATUSES


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_headers(doctype, txt, searchfield, start, page_len, filters, enforce_scope=None):
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []

    conditions = ["h.docstatus < 2"]
    values = _limit_values(txt, start, page_len)
    join_project = apply_header_filters(conditions, values, filters, "h")
    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
        append_allowed_status_filter(conditions, values, "h")
    elif filters.get("allowed_statuses"):
        conditions.append("h.status IN %(allowed_statuses)s")
        values["allowed_statuses"] = tuple(filters.get("allowed_statuses"))

    where_clause = " AND ".join(conditions)
    return frappe.db.sql(
        f"""
		SELECT h.name, h.title, h.project
		FROM `tabBOQ Header` h
		{_join_project_sql(join_project)}
		WHERE {where_clause}
			AND (h.name LIKE %(txt)s OR h.title LIKE %(txt)s OR h.project LIKE %(txt)s)
		ORDER BY h.modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
        values,
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_structures(doctype, txt, searchfield, start, page_len, filters, enforce_scope=None):
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []

    conditions = ["s.docstatus < 2", "s.is_group = 0"]
    values = _limit_values(txt, start, page_len)
    join_header = False
    join_project = False

    if filters.get("boq_header"):
        conditions.append("s.boq_header = %(boq_header)s")
        values["boq_header"] = filters.get("boq_header")
    if filters.get("project"):
        join_header = True
        conditions.append("h.project = %(project)s")
        values["project"] = filters.get("project")

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_header = True
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
        append_allowed_status_filter(conditions, values, "h")

    joins = []
    if join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Header` h ON h.name = s.boq_header")
    if join_project:
        joins.append("INNER JOIN `tabProject` p ON p.name = h.project")
    where_clause = " AND ".join(conditions)
    return frappe.db.sql(
        f"""
		SELECT s.name, s.title, s.wbs_code
		FROM `tabBOQ Structure` s
		{' '.join(joins)}
		WHERE {where_clause}
			AND (s.name LIKE %(txt)s OR s.title LIKE %(txt)s OR s.wbs_code LIKE %(txt)s)
		ORDER BY s.modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
        values,
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_items(doctype, txt, searchfield, start, page_len, filters, enforce_scope=None):
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_header") and not filters.get("boq_header"):
        return []
    if filters.get("require_structure") and not filters.get("structure"):
        return []

    conditions = ["i.docstatus < 2"]
    values = _limit_values(txt, start, page_len)
    join_project = apply_header_filters(conditions, values, filters, "h")

    if filters.get("boq_header"):
        conditions.append("i.boq_header = %(boq_header)s")
        values["boq_header"] = filters.get("boq_header")
    if filters.get("structure"):
        conditions.append("i.structure = %(structure)s")
        values["structure"] = filters.get("structure")

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
        append_allowed_status_filter(conditions, values, "h")
    elif filters.get("allowed_statuses"):
        conditions.append("h.status IN %(allowed_statuses)s")
        values["allowed_statuses"] = tuple(filters.get("allowed_statuses"))

    where_clause = " AND ".join(conditions)
    return frappe.db.sql(
        f"""
		SELECT i.name, h.title, i.quantity, h.project
		FROM `tabBOQ Item` i
		INNER JOIN `tabBOQ Header` h ON h.name = i.boq_header
		{_join_project_sql(join_project)}
		WHERE {where_clause}
			AND (i.name LIKE %(txt)s OR h.title LIKE %(txt)s)
		ORDER BY i.modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
        values,
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_item_stages(doctype, txt, searchfield, start, page_len, filters, enforce_scope=None):
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_item") and not filters.get("boq_item"):
        return []

    conditions = ["st.docstatus < 2"]
    values = _limit_values(txt, start, page_len)
    join_item = False
    join_header = False
    join_project = False

    if filters.get("boq_item"):
        conditions.append("st.boq_item = %(boq_item)s")
        values["boq_item"] = filters.get("boq_item")
    if filters.get("boq_header"):
        join_item = True
        conditions.append("i.boq_header = %(boq_header)s")
        values["boq_header"] = filters.get("boq_header")
    if filters.get("structure"):
        join_item = True
        conditions.append("i.structure = %(structure)s")
        values["structure"] = filters.get("structure")

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_item = True
        join_header = True
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
        append_allowed_status_filter(conditions, values, "h")

    joins = []
    if join_item or join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Item` i ON i.name = st.boq_item")
    if join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Header` h ON h.name = i.boq_header")
    if join_project:
        joins.append("INNER JOIN `tabProject` p ON p.name = h.project")

    where_clause = " AND ".join(conditions)
    return frappe.db.sql(
        f"""
		SELECT st.name, st.stage_code, st.stage_name, st.planned_qty
		FROM `tabBOQ Item Stage` st
		{' '.join(joins)}
		WHERE {where_clause}
			AND (st.name LIKE %(txt)s OR st.stage_code LIKE %(txt)s OR st.stage_name LIKE %(txt)s)
		ORDER BY st.modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
        values,
    )
