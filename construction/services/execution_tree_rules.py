"""Framework-independent rules for the P1 Project Execution Tree.

This module must not import ``frappe``, ``erpnext`` or ``construction`` so the
offline vectors can load it in isolation. It owns input validation, hierarchy
and code rules, and the pure authorization-decision rules that mirror the
pinned Frappe Project permission path.
"""

from __future__ import annotations

import ast
import json

MAX_NODES = 10000
MAX_DEPTH = 12
MAX_TITLE_LENGTH = 140
MAX_IDENTIFIER_LENGTH = 140
MAX_CODE_LENGTH = 40
MAX_REQUEST_BYTES = 16384

NODE_DOCTYPE = "Execution Breakdown Node"
COUNTER_DOCTYPE = "Execution Code Counter"
AUDIT_DOCTYPE = "Execution Mapping Audit"
PROTECTED_DOCTYPES = (NODE_DOCTYPE, COUNTER_DOCTYPE)

NODE_NAME_PREFIX = "EBN-"
CODE_PREFIX = "EBS-"
MIN_CODE_DIGITS = 4
MAX_COUNTER_VALUE = 9223372036854775807

EXPECTED_APP_ORDER = ("frappe", "erpnext", "construction")
SUPPORTED_APP_NAMES = frozenset(EXPECTED_APP_ORDER)
EXPECTED_WILDCARD_QUERY_HOOK = "construction.overrides.scope_query.add_scope_conditions"

AUTHORITY_DOCTYPES = frozenset(
    {
        "Project",
        "Project User",
        "User",
        "Role",
        "Has Role",
        "User Permission",
        "DocPerm",
        "Custom DocPerm",
        "DocShare",
        "Company",
        "Cost Center",
        "Department",
        "Branch",
        "Customer",
        "Sales Order",
        "Project Type",
        "Project Template",
        "Holiday List",
        "User Scope Context",
        "Construction Settings",
        "System Settings",
        NODE_DOCTYPE,
        COUNTER_DOCTYPE,
    }
)

PROJECT_LINK_TARGETS = {
    "project_type": "Project Type",
    "project_template": "Project Template",
    "department": "Department",
    "customer": "Customer",
    "sales_order": "Sales Order",
    "company": "Company",
    "cost_center": "Cost Center",
    "holiday_list": "Holiday List",
}
PROJECT_TABLE_TARGETS = {"users": "Project User"}
PROJECT_USER_LINK_TARGETS = {"user": "User"}

# Complete stock field projections transcribed from the pinned source packet
# (Project JSON blob 29aa376d3bc270c7885de02250d1fa73cfdcdcd7614c28eb9722a59fcded0f7b,
# Project User JSON blob 01e03f20c52a5c79c85db241061d496b8aed5242787e9c17390665a21aac395e,
# ERPNext commit 7474d9e786277383de1242ab882f16856d17a9c9). Rows follow the pinned
# field_order and carry (fieldname, fieldtype, options, permlevel,
# ignore_user_permissions, hidden, reqd, read_only, is_virtual) with documented
# absent scalar defaults normalized explicitly.
PINNED_STOCK_PROJECT_FIELDS = (
    ("naming_series", "Select", "PROJ-.####", 0, 0, 0, 1, 0, 0),
    ("project_name", "Data", None, 0, 0, 0, 1, 0, 0),
    ("status", "Select", "Open\nOn hold\nCompleted\nCancelled", 0, 0, 0, 0, 0, 0),
    ("project_type", "Link", "Project Type", 0, 0, 0, 0, 0, 0),
    (
        "percent_complete_method",
        "Select",
        "Manual\nTask Completion\nTask Progress\nTask Weight",
        0,
        0,
        0,
        0,
        0,
        0,
    ),
    ("column_break_5", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("project_template", "Link", "Project Template", 0, 0, 0, 0, 0, 0),
    ("priority", "Select", "Medium\nLow\nHigh", 0, 0, 0, 0, 0, 0),
    ("department", "Link", "Department", 0, 0, 0, 0, 0, 0),
    ("is_active", "Select", "Yes\nNo", 0, 0, 0, 0, 0, 0),
    ("percent_complete", "Percent", None, 0, 0, 0, 0, 0, 0),
    ("section_break_18", "Section Break", None, 0, 0, 0, 0, 0, 0),
    ("expected_start_date", "Date", None, 0, 0, 0, 0, 0, 0),
    ("actual_start_date", "Date", None, 0, 0, 0, 0, 1, 0),
    ("actual_time", "Float", None, 0, 0, 0, 0, 1, 0),
    ("column_break_20", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("expected_end_date", "Date", None, 0, 0, 0, 0, 0, 0),
    ("actual_end_date", "Date", None, 0, 0, 0, 0, 1, 0),
    ("costing_tab", "Tab Break", None, 0, 0, 0, 0, 0, 0),
    ("project_details", "Section Break", "fa fa-money", 0, 0, 0, 0, 0, 0),
    ("estimated_costing", "Currency", "Company:company:default_currency", 0, 0, 0, 0, 0, 0),
    ("total_costing_amount", "Currency", None, 0, 0, 0, 0, 1, 0),
    ("total_purchase_cost", "Currency", None, 0, 0, 0, 0, 1, 0),
    ("company", "Link", "Company", 0, 0, 0, 1, 0, 0),
    ("column_break_28", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("total_sales_amount", "Currency", None, 0, 0, 0, 0, 1, 0),
    ("total_billable_amount", "Currency", None, 0, 0, 0, 0, 1, 0),
    ("total_billed_amount", "Currency", None, 0, 0, 0, 0, 1, 0),
    ("total_consumed_material_cost", "Currency", None, 0, 0, 0, 0, 1, 0),
    ("cost_center", "Link", "Cost Center", 0, 0, 0, 0, 0, 0),
    ("margin", "Section Break", None, 0, 0, 0, 0, 0, 0),
    ("gross_margin", "Currency", "Company:company:default_currency", 0, 0, 0, 0, 1, 0),
    ("column_break_37", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("per_gross_margin", "Percent", None, 0, 0, 0, 0, 1, 0),
    ("monitor_progress_tab", "Tab Break", None, 0, 0, 0, 0, 0, 0),
    ("collect_progress", "Check", None, 0, 0, 0, 0, 0, 0),
    ("holiday_list", "Link", "Holiday List", 0, 0, 0, 0, 0, 0),
    ("frequency", "Select", "Hourly\nTwice Daily\nDaily\nWeekly", 0, 0, 0, 0, 0, 0),
    ("from_time", "Time", None, 0, 0, 0, 0, 0, 0),
    ("to_time", "Time", None, 0, 0, 0, 0, 0, 0),
    ("first_email", "Time", None, 0, 0, 0, 0, 0, 0),
    ("second_email", "Time", None, 0, 0, 0, 0, 0, 0),
    ("daily_time_to_send", "Time", None, 0, 0, 0, 0, 0, 0),
    (
        "day_to_send",
        "Select",
        "Monday\nTuesday\nWednesday\nThursday\nFriday\nSaturday\nSunday",
        0,
        0,
        0,
        0,
        0,
        0,
    ),
    ("weekly_time_to_send", "Time", None, 0, 0, 0, 0, 0, 0),
    ("column_break_45", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("subject", "Data", None, 0, 0, 0, 0, 0, 0),
    ("message", "Text", None, 0, 0, 0, 0, 0, 0),
    ("more_info_tab", "Tab Break", None, 0, 0, 0, 0, 0, 0),
    ("customer_details", "Section Break", "fa fa-user", 0, 0, 0, 0, 0, 0),
    ("customer", "Link", "Customer", 0, 0, 0, 0, 0, 0),
    ("column_break_14", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("sales_order", "Link", "Sales Order", 0, 0, 0, 0, 0, 0),
    ("users_section", "Section Break", None, 0, 0, 0, 0, 0, 0),
    ("users", "Table", "Project User", 1, 0, 0, 0, 0, 0),
    ("copied_from", "Data", None, 1, 0, 1, 0, 1, 0),
    ("section_break0", "Section Break", "fa fa-list", 0, 0, 0, 0, 0, 0),
    ("notes", "Text Editor", None, 0, 0, 0, 0, 0, 0),
    ("connections_tab", "Tab Break", None, 0, 0, 0, 0, 0, 0),
)

PINNED_STOCK_PROJECT_USER_FIELDS = (
    ("user", "Link", "User", 0, 0, 0, 1, 0, 0),
    ("email", "Read Only", None, 0, 0, 0, 0, 0, 0),
    ("image", "Read Only", None, 0, 0, 1, 0, 0, 0),
    ("column_break_2", "Column Break", None, 0, 0, 0, 0, 0, 0),
    ("full_name", "Read Only", None, 0, 0, 0, 0, 0, 0),
    ("welcome_email_sent", "Check", None, 0, 0, 0, 0, 0, 0),
    ("view_attachments", "Check", None, 0, 0, 0, 0, 0, 0),
    ("hide_timesheets", "Check", None, 0, 0, 0, 0, 0, 0),
    ("section_break_5", "Section Break", None, 0, 0, 0, 0, 0, 0),
    ("project_status", "Text", None, 0, 0, 0, 0, 0, 0),
)

STOCK_FIELD_PROJECTION_ATTRIBUTES = (
    "fieldname",
    "fieldtype",
    "options",
    "permlevel",
    "ignore_user_permissions",
    "hidden",
    "reqd",
    "read_only",
    "is_virtual",
)

SUPPORTED_CUSTOM_LINK_TARGETS = frozenset(
    {
        "Project",
        "Company",
        "Cost Center",
        "Department",
        "Branch",
        "User",
        "Project Type",
        "Project Template",
        "Customer",
        "Sales Order",
        "Holiday List",
    }
)

SUPPORTED_USER_PERMISSION_TARGETS = frozenset(
    set(PROJECT_LINK_TARGETS.values()) | SUPPORTED_CUSTOM_LINK_TARGETS | {"Project", "Project User"}
)

SUPPORTED_SCALAR_FIELDTYPES = frozenset(
    {
        "Data",
        "Read Only",
        "Small Text",
        "Text",
        "Long Text",
        "Text Editor",
        "Check",
        "Int",
        "Float",
        "Currency",
        "Percent",
        "Date",
        "Datetime",
        "Time",
        "Duration",
        "Select",
        "Section Break",
        "Column Break",
        "Tab Break",
    }
)

FORBIDDEN_CUSTOM_FIELDTYPES = frozenset(
    {"Dynamic Link", "Table", "Table MultiSelect", "Link Table", "Virtual"}
)

# Finite typed cosmetic allowlist. The value selects the accepted type family.
SUPPORTED_FIELD_PROPERTY_SETTERS = {
    "label": "text",
    "description": "text",
    "placeholder": "text",
    "in_list_view": "check",
    "in_standard_filter": "check",
    "print_hide": "check",
    "columns": "int",
    "width": "width",
    "bold": "check",
}

RELEVANT_HOOKS = (
    "has_permission",
    "permission_query_conditions",
    "override_doctype_class",
    "extend_doctype_class",
    "get_child_provider",
    "doc_events",
)

# DocTypes whose materialized doc_events dispatch entries can affect WBS
# authority or the protected lifecycle. The serving dispatch map is compared
# for exactly this inventory; unrelated vendor event dictionaries remain bound
# by their pinned full-blob hook hashes.
RELEVANT_DISPATCH_DOCTYPES = frozenset({"*", "DocShare"} | AUTHORITY_DOCTYPES)

BROWSE_ROLES = frozenset({"Site Engineer", "Project Manager", "Construction Owner", "System Manager"})
WRITE_ROLES = frozenset({"Project Manager", "System Manager"})
DELETE_ROLES = frozenset({"System Manager"})
MAPPING_PLANNER_ROLES = frozenset({"System Manager", "Construction Owner", "Project Manager"})
MAPPING_ACTIONS = (
    "set",
    "change",
    "clear",
    "set_on_create",
    "inherit_on_create",
    "initial_historical_map",
)
REASON_REQUIRED_ACTIONS = frozenset({"change", "clear", "initial_historical_map"})
MAX_REASON_LENGTH = 500

OPERATIONS = ("read", "create", "update", "move", "set_disabled", "delete")
MUTATION_OPERATIONS = frozenset({"create", "update", "move", "set_disabled", "delete"})

IMMUTABLE_NODE_FIELDS = ("name", "project", "company", "ebs_code")
EDITABLE_NODE_FIELDS = ("title", "is_group")

PERMISSION_RIGHTS = (
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "report",
    "export",
    "print",
    "email",
    "share",
    "select",
    "import",
)

NODE_SUMMARY_FIELDS = (
    "name",
    "title",
    "project",
    "company",
    "parent_node",
    "is_group",
    "disabled",
    "ebs_code",
    "modified",
)


class RuleViolation(ValueError):
    """A caller input or persisted state violates an execution-tree rule."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class UnsupportedProfile(RuleViolation):
    """The permission profile is outside the reviewed supported inventory."""


def validate_operation(operation):
    if operation not in OPERATIONS:
        raise RuleViolation("invalid_operation", "Unsupported execution tree operation.")
    return operation


def validate_identifier(value, *, field="identifier", max_length=MAX_IDENTIFIER_LENGTH):
    if not isinstance(value, str):
        raise RuleViolation("invalid_identifier", f"{field} must be text.")
    text = value.strip()
    if not text:
        raise RuleViolation("invalid_identifier", f"{field} is required.")
    if len(text) > max_length:
        raise RuleViolation("invalid_identifier", f"{field} is too long.")
    if any(ord(char) < 32 for char in text):
        raise RuleViolation("invalid_identifier", f"{field} contains control characters.")
    return text


def validate_title(value):
    title = validate_identifier(value, field="Title", max_length=MAX_TITLE_LENGTH)
    return title


def validate_boolean(value, *, field="value"):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise RuleViolation("invalid_boolean", f"{field} must be a boolean.")


def validate_request_size(payload):
    if not isinstance(payload, dict):
        raise RuleViolation("invalid_request", "Request payload must be an object.")
    size = 0
    for key, value in payload.items():
        if not isinstance(key, str):
            raise RuleViolation("invalid_request", "Request keys must be text.")
        size += len(key.encode("utf-8"))
        size += len(str(value).encode("utf-8")) if value is not None else 0
        if size > MAX_REQUEST_BYTES:
            raise RuleViolation("request_too_large", "Request payload is too large.")
    return payload


def reject_unknown_arguments(payload, allowed):
    unknown = sorted(set(payload) - set(allowed))
    if unknown:
        raise RuleViolation("unknown_argument", "Unknown request argument.")
    return payload


def _counter_int(value):
    if isinstance(value, bool):
        raise RuleViolation("invalid_counter", "Counter value must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip(), 10)
        except ValueError as exc:
            raise RuleViolation("invalid_counter", "Counter value must be an integer.") from exc
    raise RuleViolation("invalid_counter", "Counter value must be an integer.")


def validate_counter_value(value):
    number = _counter_int(value)
    if number < 0:
        raise RuleViolation("invalid_counter", "Counter value cannot be negative.")
    if number > MAX_COUNTER_VALUE:
        raise RuleViolation("counter_overflow", "Execution code counter has overflowed.")
    return number


def next_counter_value(current):
    number = validate_counter_value(current)
    if number >= MAX_COUNTER_VALUE:
        raise RuleViolation("counter_overflow", "Execution code counter has overflowed.")
    return number + 1


def format_execution_code(number):
    number = validate_counter_value(number)
    if number < 1:
        raise RuleViolation("invalid_code", "Execution code number must be positive.")
    width = max(MIN_CODE_DIGITS, len(str(number)))
    return f"{CODE_PREFIX}{str(number).rjust(width, '0')}"


def parse_execution_code(code):
    if not isinstance(code, str):
        raise RuleViolation("invalid_code", "Execution code must be text.")
    text = code.strip()
    if not text.startswith(CODE_PREFIX):
        raise RuleViolation("invalid_code", "Execution code has an invalid prefix.")
    digits = text[len(CODE_PREFIX) :]
    if len(digits) < MIN_CODE_DIGITS or not digits.isdigit():
        raise RuleViolation("invalid_code", "Execution code has an invalid format.")
    if len(digits) > len(str(MAX_COUNTER_VALUE)) or len(text) > MAX_CODE_LENGTH:
        raise RuleViolation("invalid_code", "Execution code is too long.")
    number = int(digits, 10)
    if number < 1:
        raise RuleViolation("invalid_code", "Execution code number must be positive.")
    return number


def counter_document_name(project):
    return validate_identifier(project, field="Project", max_length=MAX_IDENTIFIER_LENGTH)


def _as_int_flag(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int) and value in (0, 1):
        return value
    raise RuleViolation("invalid_node", "Node flags must be boolean.")


def _normalize_node(node, expected_project):
    if not isinstance(node, dict):
        raise RuleViolation("invalid_node", "Each node must be an object.")
    name = validate_identifier(node.get("name"), field="Node name")
    title = validate_title(node.get("title"))
    project = validate_identifier(node.get("project"), field="Project")
    if project != expected_project:
        raise RuleViolation("cross_project_node", "Node belongs to a different Project.")
    company = node.get("company")
    if company is not None:
        company = validate_identifier(company, field="Company")
    parent = node.get("parent_node")
    if parent in ("", None):
        parent = None
    else:
        parent = validate_identifier(parent, field="Parent node")
        if parent == name:
            raise RuleViolation("self_parent", "A node cannot be its own parent.")
    code = node.get("ebs_code")
    if code is not None:
        code = validate_identifier(code, field="Execution code", max_length=MAX_CODE_LENGTH)
        parse_execution_code(code)
    disabled = _as_int_flag(node.get("disabled", 0))
    is_group = _as_int_flag(node.get("is_group", 0))
    modified = node.get("modified")
    if modified is not None and not isinstance(modified, str):
        modified = str(modified)
    return {
        "name": name,
        "title": title,
        "project": project,
        "company": company,
        "parent_node": parent,
        "is_group": bool(is_group),
        "disabled": bool(disabled),
        "ebs_code": code,
        "modified": modified,
    }


def _code_sort_key(node):
    code = node.get("ebs_code") or ""
    try:
        number = parse_execution_code(code)
    except RuleViolation:
        number = 0
    return (number, code, node["name"])


def build_tree(nodes, *, project, enforce_limits=True):
    project = validate_identifier(project, field="Project")
    if not isinstance(nodes, list):
        raise RuleViolation("invalid_tree", "Nodes must be a list.")
    if enforce_limits and len(nodes) > MAX_NODES:
        raise RuleViolation("tree_too_large", "The execution tree exceeds its node limit.")

    normalized = []
    by_name = {}
    for raw in nodes:
        node = _normalize_node(raw, project)
        if node["name"] in by_name:
            raise RuleViolation("duplicate_node", "The execution tree contains duplicate node names.")
        by_name[node["name"]] = node
        normalized.append(node)

    children = {name: [] for name in by_name}
    roots = []
    for node in normalized:
        parent = node["parent_node"]
        if parent is None:
            roots.append(node["name"])
            continue
        parent_node = by_name.get(parent)
        if parent_node is None:
            raise RuleViolation("missing_parent", "A node references a missing parent.")
        if not parent_node["is_group"]:
            raise RuleViolation("non_group_parent", "A parent must be a group node.")
        children[parent].append(node["name"])

    depth = {}
    for start in by_name:
        path = []
        seen = set()
        current = start
        while current is not None and current not in depth:
            if current in seen:
                raise RuleViolation("cycle", "The execution tree contains a cycle.")
            seen.add(current)
            path.append(current)
            current = by_name[current]["parent_node"]
        base = depth[current] if current is not None else 0
        for offset, name in enumerate(reversed(path), start=1):
            depth[name] = base + offset

    if enforce_limits and depth and max(depth.values()) > MAX_DEPTH:
        raise RuleViolation("depth_exceeded", "The execution tree exceeds its depth limit.")

    ordered = []

    def visit(name, level):
        node = by_name[name]
        ordered.append({**node, "depth": level})
        for child in sorted(children[name], key=lambda item: _code_sort_key(by_name[item])):
            visit(child, level + 1)

    for name in sorted(roots, key=lambda item: _code_sort_key(by_name[item])):
        visit(name, 1)
    return ordered


def node_summary(node):
    return {field: node.get(field) for field in NODE_SUMMARY_FIELDS}


def summarize_tree(ordered_nodes):
    return [node_summary(node) | {"depth": node.get("depth")} for node in ordered_nodes]


def tree_index(nodes, *, project):
    ordered = build_tree(nodes, project=project)
    return {node["name"]: node for node in ordered}


def child_names(nodes, name):
    return [node["name"] for node in nodes if node.get("parent_node") == name]


def subtree_height(nodes, name):
    index = {node["name"]: node for node in nodes}
    if name not in index:
        raise RuleViolation("missing_node", "The node does not exist.")

    def walk(current, seen):
        if current in seen:
            raise RuleViolation("cycle", "The execution tree contains a cycle.")
        seen = seen | {current}
        children = child_names(nodes, current)
        if not children:
            return 1
        return 1 + max(walk(child, seen) for child in children)

    return walk(name, set())


def validate_create_parent(nodes, *, project, parent_node):
    ordered = build_tree(nodes, project=project)
    if len(ordered) >= MAX_NODES:
        raise RuleViolation("node_limit", "The execution tree has reached its node limit.")
    if parent_node is None:
        return 1
    index = {node["name"]: node for node in ordered}
    parent = index.get(parent_node)
    if parent is None:
        raise RuleViolation("missing_parent", "The selected parent does not exist.")
    if not parent["is_group"]:
        raise RuleViolation("non_group_parent", "The selected parent is not a group.")
    depth = parent["depth"] + 1
    if depth > MAX_DEPTH:
        raise RuleViolation("depth_exceeded", "The new node would exceed the depth limit.")
    return depth


def validate_move(nodes, *, project, name, new_parent):
    ordered = build_tree(nodes, project=project)
    index = {node["name"]: node for node in ordered}
    node = index.get(name)
    if node is None:
        raise RuleViolation("missing_node", "The node does not exist.")
    if new_parent in ("", None):
        new_parent = None
    if new_parent == name:
        raise RuleViolation("self_parent", "A node cannot be its own parent.")

    if node["parent_node"] == new_parent:
        return node["depth"]

    if new_parent is None:
        new_depth = 1
    else:
        parent = index.get(new_parent)
        if parent is None:
            raise RuleViolation("missing_parent", "The destination parent does not exist.")
        if not parent["is_group"]:
            raise RuleViolation("non_group_parent", "The destination parent is not a group.")
        new_depth = parent["depth"] + 1

    cursor = new_parent
    while cursor is not None:
        if cursor == name:
            raise RuleViolation("cycle", "A node cannot be moved below its own subtree.")
        cursor = index[cursor]["parent_node"] if cursor in index else None

    height = subtree_height(ordered, name)
    if new_depth + height - 1 > MAX_DEPTH:
        raise RuleViolation("depth_exceeded", "The move would exceed the depth limit.")
    return new_depth


def validate_delete(nodes, *, project, name):
    ordered = build_tree(nodes, project=project)
    index = {node["name"]: node for node in ordered}
    if name not in index:
        raise RuleViolation("missing_node", "The node does not exist.")
    if child_names(ordered, name):
        raise RuleViolation("node_has_children", "A node with children cannot be deleted.")
    return name


def validate_group_change(nodes, *, project, name, new_is_group):
    ordered = build_tree(nodes, project=project)
    index = {node["name"]: node for node in ordered}
    if name not in index:
        raise RuleViolation("missing_node", "The node does not exist.")
    new_is_group = bool(validate_boolean(new_is_group, field="is_group"))
    if not new_is_group and child_names(ordered, name):
        raise RuleViolation("group_has_children", "A group with children cannot become a leaf.")
    return new_is_group


def user_permission_allows(
    *,
    doctype,
    docname,
    doc_values,
    link_fields,
    user_permissions,
    strict=False,
    child_rows=(),
):
    """Mirror Frappe's self-document and Link user-permission checks."""

    def allowed_docs(rows):
        return [
            row.get("doc")
            for row in rows
            if not row.get("applicable_for") or row.get("applicable_for") == doctype
        ]

    rows = list((user_permissions or {}).get(doctype, []))
    if rows:
        permitted = allowed_docs(rows)
        if permitted and (not docname or str(docname) not in permitted):
            return False

    def check(values, fields):
        for field in fields:
            if field.get("ignore_user_permissions"):
                continue
            options = field.get("options")
            value = values.get(field.get("fieldname"))
            if not value and not strict:
                continue
            if options not in (user_permissions or {}):
                continue
            permitted = allowed_docs(user_permissions.get(options, []))
            if permitted and str(value) not in permitted:
                return False
        return True

    if not check(doc_values or {}, link_fields or ()):
        return False
    return all(check(row, row.get("_link_fields") or ()) for row in child_rows or ())


def compute_role_permissions(permissions, roles, *, is_owner=False):
    if not isinstance(permissions, list | tuple):
        raise UnsupportedProfile("unsupported_permissions", "Project permissions are not a list.")
    roles = set(roles or ())
    applicable = []
    for perm in permissions:
        if not isinstance(perm, dict):
            raise UnsupportedProfile("unsupported_permissions", "Unsupported permission row.")
        if perm.get("role") in roles and int(perm.get("permlevel") or 0) == 0:
            applicable.append(perm)
    result = {right: 0 for right in PERMISSION_RIGHTS}
    result["if_owner"] = {}
    has_if_owner_enabled = any(bool(perm.get("if_owner")) for perm in applicable)
    result["has_if_owner_enabled"] = has_if_owner_enabled
    for right in PERMISSION_RIGHTS:
        value = any(bool(perm.get(right)) for perm in applicable)
        result[right] = 1 if value else 0
        if (
            value
            and has_if_owner_enabled
            and right != "create"
            and not any(bool(perm.get(right)) and not bool(perm.get("if_owner")) for perm in applicable)
        ):
            result["if_owner"][right] = 1 if (value and is_owner) else 0
            result[right] = 1 if right in ("select", "read") else 0
    return result


def apply_user_permission_result(role_result, *, is_owner, user_permission_allowed, ptype):
    permissions = dict(role_result)
    permissions["if_owner"] = dict(role_result.get("if_owner") or {})
    if user_permission_allowed:
        return permissions
    if is_owner:
        requested = dict(permissions.get("if_owner") or {})
        requested["create"] = 0
        return requested
    return {}


def evaluate_native_document_permission(
    *,
    permissions,
    roles,
    is_owner,
    ptype,
    user_permission_allowed,
    share_allowed=False,
    controller_denied=False,
    unsupported=None,
):
    if unsupported:
        raise UnsupportedProfile("unsupported_profile", str(unsupported))
    if ptype not in PERMISSION_RIGHTS:
        raise RuleViolation("invalid_permission_type", "Unsupported permission type.")
    role_result = compute_role_permissions(permissions, roles, is_owner=is_owner)
    if role_result.get("has_if_owner_enabled"):
        role_result = dict(role_result)
        role_result["if_owner"] = dict(role_result.get("if_owner") or {})
        role_result.update(role_result["if_owner"])
    if controller_denied:
        base = {ptype: 0}
        stage = "controller_denied"
    else:
        base = apply_user_permission_result(
            role_result,
            is_owner=is_owner,
            user_permission_allowed=user_permission_allowed,
            ptype=ptype,
        )
        stage = "document_permission"
    allowed = bool(base.get(ptype))
    if not allowed and share_allowed:
        allowed = True
        stage = "share_fallback"
    return {"allowed": allowed, "stage": stage, "native": role_result}


def decide_operation_access(
    *,
    operation,
    roles,
    native_read,
    native_write,
    organizational_allowed,
    is_administrator=False,
):
    validate_operation(operation)
    roles = set(roles or ())
    if is_administrator:
        return {
            "allowed": True,
            "reason": "administrator",
            "required_role": None,
        }
    if operation == "read":
        required = BROWSE_ROLES
        native_allowed = bool(native_read)
    elif operation == "delete":
        required = DELETE_ROLES
        native_allowed = bool(native_write)
    else:
        required = WRITE_ROLES
        native_allowed = bool(native_write)
    reason = "allowed"
    allowed = True
    if not roles & required:
        allowed = False
        reason = "wbs_role"
    elif not native_allowed:
        allowed = False
        reason = "native_project_permission"
    elif not organizational_allowed:
        allowed = False
        reason = "organizational_boundary"
    return {
        "allowed": allowed,
        "reason": reason,
        "required_role": sorted(required),
        "required_native": "read" if operation == "read" else "write",
    }


def organizational_allows(
    *,
    scope_enabled,
    scope,
    project,
    project_company,
    project_cost_center,
    cost_center_in_scope_subtree=True,
):
    if not scope_enabled:
        return True
    if not isinstance(scope, dict) or not scope.get("company"):
        return False
    if project_company and project_company != scope["company"]:
        return False
    if scope.get("project") and project and scope["project"] != project:
        return False
    if scope.get("cost_center") and project_cost_center:
        if not cost_center_in_scope_subtree:
            return False
    return True


def validate_node_summary(node):
    summary = node_summary(node)
    if set(summary) != set(NODE_SUMMARY_FIELDS):
        raise RuleViolation("invalid_summary", "Node summary exposes unexpected fields.")
    return summary


def validate_expected_modified(value, *, field="expected_modified", required=False):
    if value in (None, ""):
        if required:
            raise RuleViolation("missing_version", f"{field} is required.")
        return None
    if not isinstance(value, str):
        raise RuleViolation("invalid_version", f"{field} must be text.")
    if len(value) > 32 or any(char not in "0123456789-:. " for char in value):
        raise RuleViolation("invalid_version", f"{field} is not a valid version value.")
    return value


def stale_version(current_modified, expected_modified):
    if expected_modified is None:
        return False
    if current_modified is None:
        return True
    return str(current_modified) != str(expected_modified)


def share_grants(*, row_user, everyone, actor):
    """Return True only for an exact-actor or explicit everyone share.

    A NULL/empty ``user`` without ``everyone`` is never a grant.
    """

    if int(everyone or 0) == 1:
        return actor != "Guest"
    if not row_user:
        return False
    return str(row_user) == str(actor)


def parse_scope_enabled(raw):
    """Normalize ``enable_scope_context``.

    Absent, empty or non-binary configuration is an error, never an implicit
    "scope off" default.
    """

    if raw is None:
        raise RuleViolation("missing_scope_setting", "Scope configuration is missing.")
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip()
    if text == "":
        raise RuleViolation("missing_scope_setting", "Scope configuration is empty.")
    if text not in ("0", "1"):
        raise RuleViolation("invalid_scope_setting", "Scope configuration is not binary.")
    return text == "1"


def parse_installed_apps(payload):
    """Validate the raw ``installed_apps`` registry value.

    The registry must be one JSON list containing exactly the supported app
    order with no duplicates.
    """

    value = payload
    if isinstance(payload, str):
        try:
            value = json.loads(payload)
        except ValueError as exc:
            raise RuleViolation("invalid_apps", "Installed-app registry is malformed.") from exc
    if not isinstance(value, list | tuple):
        raise RuleViolation("invalid_apps", "Installed-app registry is not a list.")
    items = list(value)
    if any(not isinstance(item, str) or not item for item in items):
        raise RuleViolation("invalid_apps", "Installed-app registry has invalid entries.")
    if len(items) != len(set(items)):
        raise RuleViolation("invalid_apps", "Installed-app registry contains duplicates.")
    if tuple(items) != EXPECTED_APP_ORDER:
        raise RuleViolation("invalid_apps", "Installed-app order is outside the supported profile.")
    return tuple(items)


class HookProjectionError(UnsupportedProfile):
    """A relevant hook registration is dynamic or outside the projection grammar."""


def _literal(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise HookProjectionError("unresolved_hook_name", f"Unresolved name {node.id!r}.")
    if isinstance(node, ast.List):
        return [_literal(item, env) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_literal(item, env) for item in node.elts)
    if isinstance(node, ast.Set):
        return {_literal(item, env) for item in node.elts}
    if isinstance(node, ast.Dict):
        result = {}
        for key_node, value_node in zip(node.keys, node.values, strict=True):
            if key_node is None:
                unpacked = _literal(value_node, env)
                if not isinstance(unpacked, dict):
                    raise HookProjectionError("invalid_hook", "Only mapping unpacking is supported.")
                for key, value in unpacked.items():
                    result[key] = value
            else:
                key = _literal(key_node, env)
                if isinstance(key, str | int | bool):
                    result[key] = _literal(value_node, env)
                elif isinstance(key, tuple | frozenset) and all(
                    isinstance(member, str | int | bool) for member in key
                ):
                    # Hashable literal container keys, e.g. tuple(doctype_list)
                    # in vendor doc_events; expanded by the dispatch projection.
                    result[key] = _literal(value_node, env)
                else:
                    raise HookProjectionError("invalid_hook", "Hook keys must be literal scalars.")
        return result
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _literal(node.operand, env)
        if isinstance(operand, int) and not isinstance(operand, bool):
            return -operand
        raise HookProjectionError("invalid_hook", "Unsupported unary expression.")
    if isinstance(node, ast.ListComp):
        return _literal_comprehension(node, env)
    if isinstance(node, ast.DictComp):
        result = {}
        for item in _literal_comprehension(node, env, paired=True):
            key, value = item
            result[key] = value
        return result
    if isinstance(node, ast.Call):
        # Finite pure container conversions of an already resolved literal
        # sequence (for example ``tuple(period_closing_doctypes)`` used as a
        # doc_events key). No other call form is projected.
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in ("tuple", "list", "set", "frozenset")
            and len(node.args) == 1
            and not node.keywords
        ):
            operand = _literal(node.args[0], env)
            if isinstance(operand, list | tuple | set | frozenset):
                try:
                    converter = {
                        "tuple": tuple,
                        "list": list,
                        "set": set,
                        "frozenset": frozenset,
                    }[node.func.id]
                    return converter(operand)
                except TypeError as exc:
                    raise HookProjectionError(
                        "dynamic_hook", "Container conversion has unhashable members."
                    ) from exc
        raise HookProjectionError("dynamic_hook", "Dynamic hook expression is unsupported.")
    raise HookProjectionError("dynamic_hook", "Dynamic hook expression is unsupported.")


def _literal_comprehension(node, env, *, paired=False):
    if len(node.generators) != 1:
        raise HookProjectionError("dynamic_hook", "Nested comprehensions are unsupported.")
    generator = node.generators[0]
    if generator.ifs:
        raise HookProjectionError("dynamic_hook", "Conditional comprehensions are unsupported.")
    if not isinstance(generator.target, ast.Name):
        raise HookProjectionError("dynamic_hook", "Comprehension targets must be names.")
    sequence = _literal(generator.iter, env)
    if not isinstance(sequence, list | tuple):
        raise HookProjectionError("dynamic_hook", "Comprehensions need literal sequences.")
    output = []
    for item in sequence:
        local = dict(env)
        local[generator.target.id] = item
        if paired:
            key_node, value_node = node.key, node.value
            output.append((_literal(key_node, local), _literal(value_node, local)))
        else:
            output.append(_literal(node.elt, local))
    return output


def _mentions_hook(statement, names):
    for child in ast.walk(statement):
        if isinstance(child, ast.Name) and child.id in names:
            return True
    return False


def extract_hook_projection(source, filename="<hooks>", mode="construction"):
    """Extract the deterministic relevant hook projection from hook source.

    This never imports or executes the module. Supported forms are literal
    containers/scalars, previously resolved literal names, ordered dictionary
    updates/subscript assignments, dictionary unpacking and finite
    comprehensions over literal sequences.

    ``mode="vendor"`` applies the same grammar to the permission-relevant
    surfaces but ignores ``doc_events``: vendor files are additionally bound by
    their pinned full-blob hash, and their unrelated event dictionaries may
    contain reviewed dynamic keys. ``mode="events"`` projects only
    ``doc_events`` and is strict: every key and handler must resolve, because
    the result feeds the serving dispatch-map comparison.
    """

    try:
        module = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise HookProjectionError("invalid_hook_source", "Hook source cannot be parsed.") from exc

    env = {}
    projection = {}
    relevant = set(RELEVANT_HOOKS)
    if mode == "vendor":
        relevant.discard("doc_events")
    elif mode == "events":
        relevant = {"doc_events"}
    guarded_names = set()
    if mode == "events":
        for statement in module.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "doc_events" for target in statement.targets
            ):
                for child in ast.walk(statement.value):
                    if isinstance(child, ast.Name):
                        guarded_names.add(child.id)
        guarded_names -= {"doc_events", "tuple", "list", "set", "frozenset"}
    seen_definitions = set()
    for statement in module.body:
        if mode == "events" and guarded_names:
            is_events_assign = isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "doc_events" for target in statement.targets
            )
            single_literal_definition = (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id in guarded_names
                and statement.targets[0].id not in seen_definitions
            )
            if not is_events_assign and not single_literal_definition:
                if _mentions_hook(statement, guarded_names):
                    raise HookProjectionError(
                        "dynamic_hook",
                        "A statement can change a name referenced by doc_events.",
                    )
            if single_literal_definition:
                seen_definitions.add(statement.targets[0].id)
        if isinstance(statement, ast.Import | ast.ImportFrom):
            continue
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                _assign_target(target, statement.value, env, projection, relevant)
            continue
        if isinstance(statement, ast.AnnAssign) and statement.value is not None:
            _assign_target(statement.target, statement.value, env, projection, relevant)
            continue
        if isinstance(statement, ast.AugAssign):
            _aug_assign_target(statement.target, statement.op, statement.value, env, projection, relevant)
            continue
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            continue
        if _mentions_hook(statement, relevant):
            raise HookProjectionError(
                "dynamic_hook",
                "A conditional or dynamic statement can change a relevant hook registration.",
            )
    for name in relevant:
        if name not in projection:
            projection[name] = {} if name != "get_child_provider" else {}
    return projection


def _assign_target(target, value, env, projection, relevant):
    if isinstance(target, ast.Name):
        try:
            resolved = _literal(value, env)
        except HookProjectionError:
            if target.id in relevant:
                raise
            env.pop(target.id, None)
            return
        env[target.id] = resolved
        if target.id in relevant:
            projection[target.id] = resolved
        return
    if isinstance(target, ast.Subscript):
        base = _base_name(target.value)
        if base is None:
            if _mentions_hook(target, relevant):
                raise HookProjectionError("dynamic_hook", "Dynamic hook subscript target.")
            return
        if base in relevant:
            container = projection.setdefault(base, {})
            key = _literal(target.slice, env)
            container[key] = _literal(value, env)
        else:
            try:
                container = env[base]
                container[_literal(target.slice, env)] = _literal(value, env)
            except (HookProjectionError, KeyError, TypeError):
                env.pop(base, None)
        return
    if isinstance(target, ast.Tuple | ast.List):
        for item in target.elts:
            _assign_target(item, value, env, projection, relevant)
        return
    raise HookProjectionError("dynamic_hook", "Unsupported assignment target.")


def _aug_assign_target(target, op, value, env, projection, relevant):
    base = _base_name(target)
    if base is None or (base not in relevant and base not in env):
        if base is not None and base in relevant:
            raise HookProjectionError("dynamic_hook", "Unresolved relevant hook update.")
        return
    if not isinstance(target, ast.Name):
        raise HookProjectionError("dynamic_hook", "Only whole-dictionary hook updates are supported.")
    current = projection.get(base) if base in relevant else env.get(base)
    if current is None:
        raise HookProjectionError("dynamic_hook", "Hook update target is unresolved.")
    if isinstance(op, ast.BitOr):
        extra = _literal(value, env)
        if not isinstance(current, dict) or not isinstance(extra, dict):
            raise HookProjectionError("dynamic_hook", "Only dictionary union is supported.")
        merged = dict(current)
        merged.update(extra)
    else:
        raise HookProjectionError("dynamic_hook", "Unsupported augmented assignment.")
    env[base] = merged
    if base in relevant:
        projection[base] = merged


def _base_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return None


def validate_hook_projection(app, projection, expected_wildcard=EXPECTED_WILDCARD_QUERY_HOOK):
    """Validate a projection against the finite supported boundary."""

    has_permission = projection.get("has_permission") or {}
    query_conditions = projection.get("permission_query_conditions") or {}
    overrides = projection.get("override_doctype_class") or {}
    extensions = projection.get("extend_doctype_class") or {}
    child_providers = projection.get("get_child_provider") or {}
    doc_events = projection.get("doc_events") or {}

    if not isinstance(has_permission, dict) or not isinstance(query_conditions, dict):
        raise HookProjectionError("invalid_hook", "Permission hooks must be mappings.")
    if "Project" in has_permission or "*" in has_permission:
        raise HookProjectionError("unsupported_profile", "Project or wildcard has_permission hook installed.")
    if "Project" in query_conditions:
        raise HookProjectionError("unsupported_profile", "Project permission query hook installed.")
    wildcard = query_conditions.get("*")
    if isinstance(wildcard, str):
        wildcard = [wildcard]
    if wildcard is None:
        wildcard = []
    if app == "construction":
        if not isinstance(wildcard, list | tuple) or list(wildcard) != [expected_wildcard]:
            raise HookProjectionError(
                "unsupported_profile",
                "Wildcard permission query hook registration is not the exact expected handler.",
            )
    elif wildcard:
        # Any vendor wildcard entry would be merged with the Construction
        # registration and violate the exact effective inventory.
        raise HookProjectionError(
            "unsupported_profile", "A vendor wildcard permission query hook adds an unsupported handler."
        )
    for table, label in ((overrides, "override"), (extensions, "extension")):
        if not isinstance(table, dict):
            raise HookProjectionError("invalid_hook", f"Unsupported {label} hook shape.")
        affected = sorted(AUTHORITY_DOCTYPES & set(table))
        if affected:
            raise HookProjectionError(
                "unsupported_profile",
                f"Unsupported {label} for authority DocType(s): {', '.join(affected)}.",
            )
    if child_providers:
        raise HookProjectionError("unsupported_profile", "Computed child providers are unsupported.")

    if app == "construction":
        _validate_construction_events(doc_events, has_permission, query_conditions)


def _validate_construction_events(doc_events, has_permission, query_conditions):
    if not isinstance(doc_events, dict):
        raise HookProjectionError("invalid_hook", "doc_events must be a mapping.")
    wildcard_events = doc_events.get("*") or {}
    wildcard_validate = wildcard_events.get("validate") if isinstance(wildcard_events, dict) else None
    if isinstance(wildcard_validate, str):
        wildcard_validate = [wildcard_validate]
    if "construction.overrides.scope_enforcement.validate" not in list(wildcard_validate or []):
        raise HookProjectionError("unsupported_profile", "Wildcard scope enforcement is missing.")
    project_events = doc_events.get("Project") or {}
    allowed_project_events = {"validate", "before_rename", "on_trash"}
    if not isinstance(project_events, dict) or set(project_events) - allowed_project_events:
        raise HookProjectionError("unsupported_profile", "Unexpected Project lifecycle handlers.")
    validate_handlers = project_events.get("validate") or []
    if isinstance(validate_handlers, str):
        validate_handlers = [validate_handlers]
    if "construction.services.execution_tree.project_validate" not in list(validate_handlers):
        raise HookProjectionError("unsupported_profile", "Project execution-tree validation is missing.")
    if project_events.get("before_rename") != "construction.services.execution_tree.project_before_rename":
        raise HookProjectionError("unsupported_profile", "Project rename guard is missing.")
    if project_events.get("on_trash") != "construction.services.execution_tree.project_on_trash":
        raise HookProjectionError("unsupported_profile", "Project delete guard is missing.")
    share_events = doc_events.get("DocShare") or {}
    if isinstance(share_events, dict):
        if (
            share_events.get("validate")
            != "construction.services.execution_tree_access.reject_protected_share"
        ):
            raise HookProjectionError("unsupported_profile", "Protected share validation is missing.")
    for doctype in PROTECTED_DOCTYPES:
        expected = "construction.services.execution_tree_access.has_protected_permission"
        if has_permission.get(doctype) != expected:
            raise HookProjectionError(
                "unsupported_profile", f"{doctype} protected permission handler is not exact."
            )
        expected_query = "construction.services.execution_tree_access.protected_query_conditions"
        if query_conditions.get(doctype) != expected_query:
            raise HookProjectionError(
                "unsupported_profile", f"{doctype} protected query handler is not exact."
            )


def cast_property_setter(property_name, value, property_type):
    """Validate and cast one supported cosmetic Property Setter value."""

    kind = SUPPORTED_FIELD_PROPERTY_SETTERS.get(property_name)
    if kind is None:
        raise RuleViolation("unsupported_setter", "Unsupported Property Setter.")
    if kind == "text":
        if not isinstance(value, str):
            raise RuleViolation("invalid_setter", "Property Setter value must be text.")
        return value
    if kind == "check":
        if property_type not in ("Check", "Int"):
            raise RuleViolation("invalid_setter", "Boolean Property Setter has an unexpected type.")
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise RuleViolation("invalid_setter", "Boolean Property Setter value is not an integer.") from exc
        if number not in (0, 1):
            raise RuleViolation("invalid_setter", "Boolean Property Setter value is not binary.")
        return number
    if kind == "int":
        if property_type not in ("Int", None):
            raise RuleViolation("invalid_setter", "Integer Property Setter has an unexpected type.")
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise RuleViolation("invalid_setter", "Integer Property Setter value is not an integer.") from exc
        if number < 0:
            raise RuleViolation("invalid_setter", "Integer Property Setter value is negative.")
        return number
    if kind == "width":
        if property_type == "Int":
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise RuleViolation("invalid_setter", "Width Property Setter value is invalid.") from exc
            if number < 0:
                raise RuleViolation("invalid_setter", "Width Property Setter value is negative.")
            return number
        if isinstance(value, str):
            return value
        raise RuleViolation("invalid_setter", "Width Property Setter value is invalid.")
    raise RuleViolation("unsupported_setter", "Unsupported Property Setter.")


def validate_custom_field_definition(field, *, doctype):
    """Validate one custom field against the finite supported allowlist."""

    fieldtype = field.get("fieldtype")
    if fieldtype in FORBIDDEN_CUSTOM_FIELDTYPES:
        raise UnsupportedProfile("unsupported_custom_field", f"Unsupported {fieldtype} custom field.")
    if fieldtype == "Link":
        if field.get("options") not in SUPPORTED_CUSTOM_LINK_TARGETS:
            raise UnsupportedProfile("unsupported_custom_link", "Custom Link target is outside the profile.")
    elif fieldtype in SUPPORTED_SCALAR_FIELDTYPES:
        if field.get("options") and fieldtype != "Select":
            raise UnsupportedProfile("invalid_custom_field", "Custom scalar field carries options.")
    else:
        raise UnsupportedProfile("unsupported_custom_field", f"Unsupported custom field type {fieldtype!r}.")
    if not validate_field_flags(field):
        raise UnsupportedProfile("invalid_custom_field", "Custom field flags are not typed.")
    return field


def validate_field_flags(field):
    for name in ("ignore_user_permissions", "hidden", "reqd", "read_only"):
        value = field.get(name, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value not in (0, 1):
            return False
    permlevel = field.get("permlevel", 0)
    if not isinstance(permlevel, int) or isinstance(permlevel, bool) or permlevel < 0:
        return False
    return True


def stock_field_projection(field):
    return (
        field.get("fieldname"),
        field.get("fieldtype"),
        field.get("options") or None,
        field.get("permlevel", 0),
        field.get("ignore_user_permissions", 0),
        field.get("hidden", 0),
        field.get("reqd", 0),
        field.get("read_only", 0),
        field.get("is_virtual", 0),
    )


def validate_stock_field_projection(doctype, fields):
    """Require the complete stock field inventory to match the pinned schema.

    Any missing, extra, reordered or altered stock field denies the profile.
    Supported extensions live in Custom Field rows and are validated
    separately; they never widen this stock projection.
    """

    pinned = {
        "Project": PINNED_STOCK_PROJECT_FIELDS,
        "Project User": PINNED_STOCK_PROJECT_USER_FIELDS,
    }.get(doctype)
    if pinned is None:
        raise UnsupportedProfile("unsupported_stock_schema", f"No pinned stock schema for {doctype}.")
    actual = tuple(stock_field_projection(field) for field in fields)
    if actual != pinned:
        raise UnsupportedProfile(
            "unsupported_stock_schema",
            f"The stock {doctype} field inventory does not match the pinned schema.",
        )
    return True


def parse_required_binary_setting(raw, *, field):
    """A required scalar setting must be present and binary.

    Missing, empty or nonbinary configuration is an error, never a permissive
    default such as non-strict User Permissions or scope-off.
    """

    if raw is None:
        raise RuleViolation("missing_setting", f"The required setting {field} is missing.")
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip()
    if text == "":
        raise RuleViolation("missing_setting", f"The required setting {field} is empty.")
    if text not in ("0", "1"):
        raise RuleViolation("invalid_setting", f"The required setting {field} is not binary.")
    return text == "1"


def _listify_handlers(value):
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def relevant_dispatch_subset(events):
    """Reduce one app's literal doc_events mapping to the relevant inventory.

    Tuple/list keys are expanded exactly as the framework dispatch map does.
    Every key and handler must be a resolved literal; anything else denies.
    """

    if not isinstance(events, dict):
        raise HookProjectionError("invalid_hook", "doc_events must be a mapping.")
    subset = {}
    for key, value in events.items():
        if isinstance(key, str):
            names = [key]
        elif isinstance(key, tuple | list | frozenset | set):
            names = list(key)
        else:
            raise HookProjectionError("dynamic_hook", "Unsupported doc_events key.")
        if not isinstance(value, dict):
            raise HookProjectionError("invalid_hook", "doc_events entries must be mappings.")
        for name in names:
            if not isinstance(name, str):
                raise HookProjectionError("dynamic_hook", "doc_events keys must be text.")
            if name not in RELEVANT_DISPATCH_DOCTYPES:
                continue
            bucket = subset.setdefault(name, {})
            for method, handlers in value.items():
                if not isinstance(method, str):
                    raise HookProjectionError("dynamic_hook", "doc_events methods must be text.")
                bucket.setdefault(method, []).extend(_listify_handlers(handlers))
    return subset


def extract_relevant_doc_events(source, filename="<hooks>"):
    """Strictly project the relevant doc_events registrations from hook source.

    Unlike the vendor permission-surface projection, this never tolerates an
    unresolved or dynamic expression: the result is an expected value for the
    serving dispatch-map comparison, so uncertainty denies.
    """

    projection = extract_hook_projection(source, filename=filename, mode="events")
    return relevant_dispatch_subset(projection.get("doc_events") or {})


def merge_doc_events(app_events):
    """Merge per-app relevant events in installed order (append_hook semantics)."""

    merged = {}
    for events in app_events:
        for doctype, methods in events.items():
            bucket = merged.setdefault(doctype, {})
            for method, handlers in methods.items():
                bucket.setdefault(method, []).extend(_listify_handlers(handlers))
    return merged


def protected_definition_projection(definition):
    """Normalize a candidate protected DocType JSON into its identity projection."""

    fields = {field["fieldname"]: field for field in definition.get("fields", [])}
    order = definition.get("field_order") or list(fields)
    rows = []
    for name in order:
        field = fields.get(name)
        if field is None:
            raise RuleViolation("schema_collision", "Candidate definition has an unresolved field.")
        rows.append(
            (
                name,
                field.get("fieldtype"),
                field.get("options") or None,
                int(field.get("permlevel", 0)),
                int(field.get("ignore_user_permissions", 0)),
                int(field.get("hidden", 0)),
                int(field.get("reqd", 0)),
                int(field.get("read_only", 0)),
                int(field.get("is_virtual", 0)),
            )
        )
    flags = (
        definition.get("module"),
        int(definition.get("custom", 0)),
        int(definition.get("istable", 0)),
        int(definition.get("issingle", 0)),
        int(definition.get("is_tree", 0)),
        int(definition.get("is_virtual", 0)),
    )
    return flags, tuple(rows)


def validate_protected_definition(doctype, existing_meta, existing_fields, candidate):
    """Refuse incompatible customer metadata before framework synchronization.

    An existing protected DocType is compatible only when its ownership,
    identity flags and complete ordered field projection equal the candidate
    definition. Anything else is a collision, not a repair opportunity.
    """

    expected_flags, expected_fields = protected_definition_projection(candidate)
    if not isinstance(existing_meta, dict):
        raise RuleViolation("schema_collision", f"The existing {doctype} definition is unreadable.")
    actual_flags = (
        existing_meta.get("module"),
        int(existing_meta.get("custom") or 0),
        int(existing_meta.get("istable") or 0),
        int(existing_meta.get("issingle") or 0),
        int(existing_meta.get("is_tree") or 0),
        int(existing_meta.get("is_virtual") or 0),
    )
    if actual_flags != expected_flags:
        raise RuleViolation("schema_collision", f"The existing {doctype} DocType identity is incompatible.")
    actual_fields = tuple(
        (
            field.get("fieldname"),
            field.get("fieldtype"),
            field.get("options") or None,
            int(field.get("permlevel") or 0),
            int(field.get("ignore_user_permissions") or 0),
            int(field.get("hidden") or 0),
            int(field.get("reqd") or 0),
            int(field.get("read_only") or 0),
            int(field.get("is_virtual") or 0),
        )
        for field in existing_fields
    )
    if actual_fields != expected_fields:
        raise RuleViolation("schema_collision", f"The existing {doctype} field definitions are incompatible.")
    return True


def index_nodes_by_name(nodes):
    """Build a name -> node mapping from an iterable of execution-tree node dicts."""
    indexed = {}
    for node in nodes:
        name = node.get("name")
        if name:
            indexed[name] = node
    return indexed


def node_ancestor_chain(nodes_by_name, node_name):
    """Return the root-to-node chain of node dicts for ``node_name``."""
    if not node_name or node_name not in nodes_by_name:
        raise RuleViolation("missing_node", "Execution location was not found.")
    chain = []
    seen = set()
    cursor = node_name
    while cursor:
        if cursor in seen:
            raise RuleViolation("cycle", "Execution tree contains a cycle.")
        if cursor not in nodes_by_name:
            raise RuleViolation("broken_parent", "Execution location has a missing ancestor.")
        seen.add(cursor)
        node = nodes_by_name[cursor]
        chain.append(node)
        cursor = node.get("parent_node") or None
    chain.reverse()
    return chain


def disabled_state(nodes_by_name, node_name):
    """Return ``(is_disabled, reason)`` checking both the node and every ancestor."""
    if not node_name or node_name not in nodes_by_name:
        return True, "missing"
    chain = node_ancestor_chain(nodes_by_name, node_name)
    node = chain[-1]
    if int(node.get("disabled") or 0):
        return True, "self"
    for ancestor in chain[:-1]:
        if int(ancestor.get("disabled") or 0):
            return True, "ancestor"
    return False, None


def is_effectively_enabled(nodes_by_name, node_name):
    """True only when ``node_name`` and all of its ancestors are enabled."""
    is_disabled, _reason = disabled_state(nodes_by_name, node_name)
    return not is_disabled


def build_node_path(nodes_by_name, node_name, separator=" / "):
    """Build the human-readable ancestor title path for ``node_name``."""
    chain = node_ancestor_chain(nodes_by_name, node_name)
    parts = [str(item.get("title") or item.get("ebs_code") or item.get("name") or "").strip() for item in chain]
    return separator.join(part for part in parts if part)


def validate_eligible_execution_leaf(nodes_by_name, node_name, *, project):
    """Validate that ``node_name`` is a same-project, effectively-enabled leaf node."""
    node_name = validate_identifier(node_name, field="Execution location")
    project = validate_identifier(project, field="Project")
    node = nodes_by_name.get(node_name)
    if node is None:
        raise RuleViolation("invalid_node", "Execution location does not exist in this Project.")
    if node.get("project") != project:
        raise RuleViolation("project_mismatch", "Execution location belongs to a different Project.")
    if int(node.get("is_group") or 0):
        raise RuleViolation("group_not_eligible", "Execution location must be a leaf node, not a group.")
    is_disabled, reason = disabled_state(nodes_by_name, node_name)
    if is_disabled:
        if reason == "ancestor":
            raise RuleViolation(
                "disabled_ancestor",
                "Execution location is under a disabled ancestor branch and cannot be assigned.",
            )
        raise RuleViolation("disabled_node", "Execution location is disabled and cannot be assigned.")
    return node


def is_eligible_execution_leaf(nodes_by_name, node_name, *, project):
    """Non-throwing eligibility predicate returning ``(ok, code, message)``."""
    try:
        validate_eligible_execution_leaf(nodes_by_name, node_name, project=project)
    except RuleViolation as error:
        return False, error.code, error.message
    return True, None, None


def collect_subtree(nodes, root_name):
    """Return ``frozenset`` of ``root_name`` and all of its transitive descendants."""
    children_by_parent = {}
    for node in nodes:
        name = node.get("name")
        parent = node.get("parent_node") or None
        if name and parent:
            children_by_parent.setdefault(parent, []).append(name)
    subtree = set()
    stack = [root_name]
    while stack:
        current = stack.pop()
        if current in subtree:
            continue
        subtree.add(current)
        stack.extend(children_by_parent.get(current, ()))
    return frozenset(subtree)


def validate_mapping_reason(action, reason):
    """Normalize and enforce reason presence for mapping actions."""
    if action not in MAPPING_ACTIONS:
        raise RuleViolation("invalid_action", "Unsupported mapping action.")
    cleaned = "" if reason is None else str(reason).strip()
    if len(cleaned) > MAX_REASON_LENGTH:
        raise RuleViolation("reason_too_long", f"Mapping reason cannot exceed {MAX_REASON_LENGTH} characters.")
    if action in REASON_REQUIRED_ACTIONS and not cleaned:
        raise RuleViolation("reason_required", f"A non-blank reason is required to {action} an execution location.")
    return cleaned


def evaluate_stage_lock_conditions(stage_row, transaction_ref_doctypes=()):
    """Return sorted active A1 execution-lock triggers from current persisted Stage state.

    Evaluates current values ("while any execution-lock condition holds"):
    - ``measured_executed_qty > 0`` -> ``"measured_qty"``
    - ``certified_qty > 0`` -> ``"certified_qty"``
    - ``stage_status == "Completed"`` -> ``"status_completed"``
    - ``stage_status == "Certified"`` -> ``"status_certified"``
    - Any existing transaction child row (Draft, Submitted, or Cancelled) ->
      ``"transaction_ref:<ChildDocType>"``
    """
    triggers = []
    if float(stage_row.get("measured_executed_qty") or 0) > 0:
        triggers.append("measured_qty")
    if float(stage_row.get("certified_qty") or 0) > 0:
        triggers.append("certified_qty")
    status = str(stage_row.get("stage_status") or "").strip()
    if status == "Completed":
        triggers.append("status_completed")
    elif status == "Certified":
        triggers.append("status_certified")
    for child_dt in sorted({str(dt).strip() for dt in (transaction_ref_doctypes or ()) if str(dt).strip()}):
        triggers.append(f"transaction_ref:{child_dt}")
    return tuple(triggers)


def classify_stage_mapping_transition(old_node, new_node, lock_triggers):
    """Classify an existing-Stage location transition under Alternative B + A1.

    Returns ``(action, is_historical_assignment)`` or ``(None, False)`` for a no-op.
    Raises ``RuleViolation("execution_locked", ...)`` when relinking or clearing
    while any execution-lock condition holds.
    """
    old_val = (str(old_node).strip() if old_node is not None else "") or None
    new_val = (str(new_node).strip() if new_node is not None else "") or None
    if old_val == new_val:
        return None, False
    triggers = tuple(lock_triggers or ())
    if triggers:
        if old_val is None and new_val is not None:
            return "initial_historical_map", True
        raise RuleViolation(
            "execution_locked",
            "Cannot change or clear Execution Location while an execution-lock condition holds.",
        )
    if old_val is None and new_val is not None:
        return "set", False
    if old_val is not None and new_val is None:
        return "clear", False
    return "change", False
