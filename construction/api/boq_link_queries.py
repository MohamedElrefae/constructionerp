from typing import Any

import frappe

from construction.services.bilingual_service import normalize_arabic
from construction.services.boq_scope_filters import (
    ALLOWED_TRANSACTION_BOQ_STATUSES,
    append_allowed_status_filter,
    apply_header_filters,
    apply_header_scope,
    get_scope_payload,
    resolve_query_scope,
)
from construction.services.scope_resolution import get_scope_token


def _as_dict(filters: Any) -> dict[str, Any]:
    if not filters:
        return {}
    if isinstance(filters, str):
        return frappe.parse_json(filters) or {}
    return filters


def _extract_enforce_scope(filters: dict[str, Any], enforce_scope: Any = None) -> Any:
    # Always pop enforce_scope from filters to prevent parameter pollution
    filters.pop("enforce_scope", None)
    # Server-side authoritative: never accept client overrides
    return None


def _limit_values(txt: str, start: int, page_len: int) -> dict[str, Any]:
    return {
        "txt": f"%{txt or ''}%",
        "norm_txt": f"%{normalize_arabic(txt or '')}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }


def _join_project_sql(join_project: bool) -> str:
    return "INNER JOIN `tabProject` p ON p.name = h.project" if join_project else ""


def _attach_scope_response(scope: Any) -> None:
    if not scope:
        return
    frappe.local.response["boq_scope_token"] = get_scope_token(frappe.session.user)
    frappe.local.response["boq_scope_type"] = scope.scope_type
    if not scope.project:
        frappe.local.response["boq_scope_warning"] = (
            "No project selected — BOQ results are not project-scoped."
        )


def _truthy(value: Any) -> bool:
    return value in (True, 1, "1", "true", "True", "yes", "Yes")


def _gate_is_closed(filters: dict[str, Any]) -> bool:
    return _truthy(filters.get("require_gate")) and not _truthy(filters.get("gate_open"))


def _apply_allowed_statuses(
    conditions: list[str], values: dict[str, Any], filters: dict[str, Any], header_alias: str = "h"
) -> None:
    if not filters.get("allowed_statuses"):
        return
    conditions.append(f"{header_alias}.status IN %(allowed_statuses)s")
    values["allowed_statuses"] = tuple(filters.get("allowed_statuses"))


# ---------------------------------------------------------------------------
# Native ERPNext accounting dimension policy (F44 round 2).
#
# ERPNext provisions the "BOQ Item" accounting dimension
# (construction/install.py::setup_boq_accounting_dimension) and installs a
# native query for the "boq_item" field of every BOQ enabled child table
# (erpnext/public/js/utils/dimension_tree_filter.js::setup_child_filters).
# That native query is
# `erpnext.controllers.queries.get_filtered_dimensions`, which applies the
# Accounting Dimension Filter of the row's account:
#
#   erpnext/controllers/queries.py::get_filtered_dimensions
#     dimension_filters = get_dimension_filter_map().get((dimension, account))
#     "Allow"    -> name  IN  (allowed_dimensions)
#     otherwise  -> name NOT IN (allowed_dimensions)
#
# The BOQ cascade query replaces the native query for that field, so the app
# must apply the same policy itself; otherwise the correction would silently
# DROP the per-account dimension restriction (for example on Journal Entry
# expense rows). The policy is taken from the pinned native helper and is
# never re-implemented here, so it can neither widen nor narrow the native
# rule.
# ---------------------------------------------------------------------------
BOQ_ITEM_DIMENSION = "boq_item"
NATIVE_DIMENSION_ALLOWED_PARAM = "native_dimension_allowed"


def _native_dimension_filter_map() -> dict[Any, Any]:
    """Return the native ERPNext accounting dimension filter map.

    Produced by the pinned ERPNext helper
    `erpnext.accounts.doctype.accounting_dimension_filter.accounting_dimension_filter
    ::get_dimension_filter_map`, which is the exact map the native
    `get_filtered_dimensions` query uses. The import is local so this module
    stays importable without ERPNext present.
    """
    from erpnext.accounts.doctype.accounting_dimension_filter.accounting_dimension_filter import (
        get_dimension_filter_map,
    )

    return get_dimension_filter_map()


def resolve_native_dimension_policy(
    filters: dict[str, Any],
    dimension: str = BOQ_ITEM_DIMENSION,
    dimension_filter_map: dict[Any, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the native dimension restriction that applies to the request.

    Mirrors the pinned native semantics of
    `erpnext.controllers.queries.get_filtered_dimensions` exactly:

    * no account on the row           -> no restriction (the native map has no
                                         entry for an absent account),
    * account without a filter entry  -> no restriction,
    * entry with "Allow"               -> the BOQ Item name must be one of the
                                         allowed dimension values,
    * any other entry ("Restrict")     -> the BOQ Item name must NOT be one of
                                         the allowed dimension values.

    Validation contract:
      * The account is used ONLY as the policy key of the native map, exactly
        as ERPNext uses it. It is never returned to the client, never logged
        and never used to select or expose account data.
      * It is never able to relax a BOQ gate: the resolved restriction is
        applied IN ADDITION to the omission / header / structure / status /
        scope conditions, never instead of them.
      * A value that cannot be an Account name (control characters or beyond
        the Account name length) has no native map entry either, so it is
        ignored exactly like an unknown account.
    """
    account = filters.get("account")
    if not isinstance(account, str) or not account:
        return {"mode": None, "values": ()}
    if len(account) > 140 or any(ord(character) < 32 for character in account):
        return {"mode": None, "values": ()}

    if dimension_filter_map is None:
        dimension_filter_map = _native_dimension_filter_map()
    entry = (dimension_filter_map or {}).get((dimension, account))
    if not entry:
        return {"mode": None, "values": ()}

    allowed = tuple(entry.get("allowed_dimensions") or ())
    mode = "allow" if entry.get("allow_or_restrict") == "Allow" else "restrict"
    return {"mode": mode, "values": allowed}


def apply_native_dimension_policy(
    conditions: list[str],
    values: dict[str, Any],
    filters: dict[str, Any],
    item_alias: str = "i",
    dimension: str = BOQ_ITEM_DIMENSION,
    dimension_filter_map: dict[Any, Any] | None = None,
) -> dict[str, Any]:
    """Add the native dimension restriction to a BOQ Item query.

    The generated predicate is the effective predicate of the pinned native
    query for the same (dimension, account) pair:

    * "Allow"   -> `<alias>.name IN (<allowed dimension values>)`,
    * otherwise -> `<alias>.name NOT IN (<allowed dimension values>)`.

    An empty allowed list is the native edge case: ERPNext renders it as
    `name IN ('')` / `name NOT IN ('')`, i.e. no item for "Allow" and every
    item for "Restrict". The same values are bound here so the behaviour is
    identical. The values are bound as query parameters, never interpolated.
    """
    policy = resolve_native_dimension_policy(filters, dimension, dimension_filter_map)
    if policy["mode"] is None:
        return policy

    allowed = policy["values"] or ("",)
    values[NATIVE_DIMENSION_ALLOWED_PARAM] = allowed
    operator = "IN" if policy["mode"] == "allow" else "NOT IN"
    conditions.append(f"{item_alias}.name {operator} %({NATIVE_DIMENSION_ALLOWED_PARAM})s")
    return policy


@frappe.whitelist()
def get_boq_scope_token():
    """Return current BOQ scope details for client-side drift checks."""
    return get_scope_payload(frappe.session.user)


@frappe.whitelist()
def log_boq_scope_drift(form_doctype, form_name, previous_scope, current_scope):
    """Audit-log a scope drift event detected client-side during save."""
    frappe.log_error(
        title="BOQ Scope Drift",
        message=(
            f"User {frappe.session.user} attempted to save {form_doctype} {form_name} "
            f"after scope changed from {previous_scope} to {current_scope}. "
            f"Form was reloaded to prevent invalid attribution."
        ),
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_scope_projects(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
    """Return the active scope project for link validation without requiring Project select perms."""
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)

    scope = resolve_query_scope(enforce_scope)
    scope_project = filters.get("project") or (scope.project if scope else None)
    if not scope_project:
        return []

    projects = frappe.get_all(
        "Project",
        filters={"name": scope_project},
        fields=["name", "project_name"],
        limit=1,
        ignore_permissions=True,
    )
    if not projects:
        return []
    project = projects[0]

    txt = (txt or "").strip().lower()
    if txt and txt not in project.name.lower() and txt not in (project.project_name or "").lower():
        return []

    return [(project.name, project.project_name or project.name)]


@frappe.whitelist()
def get_allowed_transaction_boq_statuses():
    return ALLOWED_TRANSACTION_BOQ_STATUSES


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_headers(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
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
    _apply_allowed_statuses(conditions, values, filters, "h")

    where_clause = " AND ".join(conditions)
    query = (
        "\n\t\tSELECT h.name, h.title, h.project, h.title_ar\n"
        "\t\tFROM `tabBOQ Header` h\n"
        + _join_project_sql(join_project)
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (h.name LIKE %(txt)s OR h.title LIKE %(txt)s OR h.project LIKE %(txt)s"
        + " OR h.title_ar LIKE %(txt)s OR h.title_ar_norm LIKE %(norm_txt)s)\n"
        + "\t\tORDER BY h.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_structures(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_header") and not filters.get("boq_header"):
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
    if filters.get("exclude_zero_revised"):
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabBOQ Item` i
                WHERE i.structure = s.name
                  AND i.docstatus < 2
                  AND COALESCE(i.current_revised_qty, i.quantity) > 0
            )
            """
        )

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_header = True
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
    _apply_allowed_statuses(conditions, values, filters, "h")

    joins = []
    if join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Header` h ON h.name = s.boq_header")
    if join_project:
        joins.append("INNER JOIN `tabProject` p ON p.name = h.project")
    where_clause = " AND ".join(conditions)
    join_clause = " ".join(joins)
    query = (
        "\n\t\tSELECT s.name, s.title, s.wbs_code, s.title_ar\n"
        "\t\tFROM `tabBOQ Structure` s\n"
        + join_clause
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (s.name LIKE %(txt)s OR s.title LIKE %(txt)s OR s.wbs_code LIKE %(txt)s"
        + " OR s.title_ar LIKE %(txt)s OR s.title_ar_norm LIKE %(norm_txt)s)\n"
        + "\t\tORDER BY s.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_items(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_header") and not filters.get("boq_header"):
        return []
    if filters.get("require_structure") and not filters.get("structure"):
        return []

    conditions = [
        "i.docstatus < 2",
    ]

    # P1-2: Opt-in and null-safe filtering for omitted items
    if filters.get("exclude_zero_revised"):
        conditions.append("COALESCE(i.current_revised_qty, i.quantity) > 0")
    values = _limit_values(txt, start, page_len)
    join_project = apply_header_filters(conditions, values, filters, "h")

    if filters.get("boq_header"):
        conditions.append("i.boq_header = %(boq_header)s")
        values["boq_header"] = filters.get("boq_header")
    if filters.get("structure"):
        conditions.append("i.structure = %(structure)s")
        values["structure"] = filters.get("structure")
    if filters.get("is_variation_item") is not None:
        conditions.append("i.is_variation_item = %(is_variation_item)s")
        values["is_variation_item"] = int(filters.get("is_variation_item"))

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
    _apply_allowed_statuses(conditions, values, filters, "h")

    # The native ERPNext accounting dimension restriction of the row's account
    # is preserved on top of the BOQ gates (see resolve_native_dimension_policy).
    apply_native_dimension_policy(conditions, values, filters)

    where_clause = " AND ".join(conditions)
    query = (
        "\n\t\tSELECT i.name, h.title, i.quantity, h.project\n"
        "\t\tFROM `tabBOQ Item` i\n"
        "\t\tINNER JOIN `tabBOQ Header` h ON h.name = i.boq_header\n"
        + _join_project_sql(join_project)
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (i.name LIKE %(txt)s OR h.title LIKE %(txt)s)\n"
        + "\t\tORDER BY i.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_item_stages(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
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
    _apply_allowed_statuses(conditions, values, filters, "h")

    joins = []
    if join_item or join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Item` i ON i.name = st.boq_item")
    if join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Header` h ON h.name = i.boq_header")
    if join_project:
        joins.append("INNER JOIN `tabProject` p ON p.name = h.project")

    where_clause = " AND ".join(conditions)
    join_clause = " ".join(joins)
    query = (
        "\n\t\tSELECT st.name, st.stage_code, st.stage_name, st.planned_qty\n"
        "\t\tFROM `tabBOQ Item Stage` st\n"
        + join_clause
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (st.name LIKE %(txt)s OR st.stage_code LIKE %(txt)s OR st.stage_name LIKE %(txt)s)\n"
        + "\t\tORDER BY st.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_variation_orders(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
    """Link-search for Variation Order DocType.

    Filters:
        boq_header: only return VOs for that BOQ Header (skips user scope)
        project: scope to a project (joins BOQ Header)
        status: restrict to a single status value
    """
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_header") and not filters.get("boq_header"):
        return []

    conditions = ["vo.docstatus < 2"]
    values = _limit_values(txt, start, page_len)
    join_header = False
    join_project = False

    if filters.get("boq_header"):
        conditions.append("vo.boq_header = %(boq_header)s")
        values["boq_header"] = filters.get("boq_header")
    if filters.get("status"):
        conditions.append("vo.status = %(status)s")
        values["status"] = filters.get("status")
    if filters.get("project"):
        join_header = True
        conditions.append("h.project = %(project)s")
        values["project"] = filters.get("project")

    if filters.get("boq_header") and frappe.session.user != "Administrator":
        frappe.has_permission("BOQ Header", "read", doc=filters.get("boq_header"), throw=True)

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_header = True
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
        append_allowed_status_filter(conditions, values, "h")

    joins = []
    if join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Header` h ON h.name = vo.boq_header")
    if join_project:
        joins.append("INNER JOIN `tabProject` p ON p.name = h.project")

    where_clause = " AND ".join(conditions)
    join_clause = " ".join(joins)
    query = (
        "\n\t\tSELECT vo.name, vo.vo_number, vo.status, vo.boq_header\n"
        "\t\tFROM `tabVariation Order` vo\n"
        + join_clause
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (vo.name LIKE %(txt)s OR vo.vo_number LIKE %(txt)s OR vo.boq_header LIKE %(txt)s)\n"
        + "\t\tORDER BY vo.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_vo_line_boq_items(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
    """Link-search for the BOQ Item field on VO Line (Quantity Change / Omission).

    Restricts to leaves of the selected BOQ Header and excludes variation
    items (a Quantity Change VO line must target a contract item). User
    scope is skipped when a boq_header is pinned.
    """
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_header") and not filters.get("boq_header"):
        return []

    conditions = ["i.docstatus < 2", "i.is_variation_item = 0"]

    # Opt-in, null-safe omitted-item filtering: keeps this query at parity with
    # get_boq_items (and the VO Line form query) so omitted options are not offered.
    if filters.get("exclude_zero_revised"):
        conditions.append("COALESCE(i.current_revised_qty, i.quantity) > 0")
    values = _limit_values(txt, start, page_len)
    join_header = False
    join_project = False

    if filters.get("boq_header"):
        conditions.append("i.boq_header = %(boq_header)s")
        values["boq_header"] = filters.get("boq_header")
    if filters.get("structure"):
        conditions.append("i.structure = %(structure)s")
        values["structure"] = filters.get("structure")
    if filters.get("project"):
        join_header = True
        conditions.append("h.project = %(project)s")
        values["project"] = filters.get("project")

    if filters.get("boq_header") and frappe.session.user != "Administrator":
        frappe.has_permission("BOQ Header", "read", doc=filters.get("boq_header"), throw=True)

    scope = resolve_query_scope(enforce_scope)
    if scope:
        _attach_scope_response(scope)
        join_header = True
        join_project = apply_header_scope(conditions, values, scope, "h") or join_project
        append_allowed_status_filter(conditions, values, "h")

    joins = []
    if join_header or join_project:
        joins.append("INNER JOIN `tabBOQ Header` h ON h.name = i.boq_header")
    if join_project:
        joins.append("INNER JOIN `tabProject` p ON p.name = h.project")

    where_clause = " AND ".join(conditions)
    select_header_title = ", h.title" if (join_header or join_project) else ""
    join_clause = " ".join(joins)
    query = (
        "\n\t\tSELECT i.name, i.cost_item, i.quantity"
        + select_header_title
        + "\n\t\tFROM `tabBOQ Item` i\n"
        + join_clause
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (i.name LIKE %(txt)s OR i.cost_item LIKE %(txt)s)\n"
        + "\t\tORDER BY i.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_variation_structures(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict[str, Any] | str | None,
    enforce_scope: Any = None,
):
    """Link-search for VO Line.created_boq_structure (New Item VO line)."""
    filters = _as_dict(filters)
    enforce_scope = _extract_enforce_scope(filters, enforce_scope)
    if _gate_is_closed(filters):
        return []
    if filters.get("require_boq_header") and not filters.get("boq_header"):
        return []

    conditions = ["s.docstatus < 2", "s.is_variation_item = 1"]
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

    if filters.get("boq_header") and frappe.session.user != "Administrator":
        frappe.has_permission("BOQ Header", "read", doc=filters.get("boq_header"), throw=True)

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
    join_clause = " ".join(joins)
    query = (
        "\n\t\tSELECT s.name, s.title, s.wbs_code, s.variation_order\n"
        "\t\tFROM `tabBOQ Structure` s\n"
        + join_clause
        + "\n\t\tWHERE "
        + where_clause
        + "\n\t\t\tAND (s.name LIKE %(txt)s OR s.title LIKE %(txt)s OR s.wbs_code LIKE %(txt)s)\n"
        + "\t\tORDER BY s.modified DESC\n"
        + "\t\tLIMIT %(start)s, %(page_len)s\n"
    )
    return frappe.db.sql(query, values)
