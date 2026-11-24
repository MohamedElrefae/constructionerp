"""Idempotent schema installer for the P1 Project Execution Tree."""

from __future__ import annotations

import json
from pathlib import Path

import frappe

from construction.services import execution_tree_rules as rules

NODE_TABLE = f"tab{rules.NODE_DOCTYPE}"
COUNTER_TABLE = f"tab{rules.COUNTER_DOCTYPE}"
NODE_UNIQUE_INDEX = "execution_node_project_code_unique"
NODE_PARENT_INDEX = "execution_node_project_parent"
COUNTER_PROJECT_INDEX = "execution_counter_project_unique"

PROTECTED_DEFINITION_PATHS = {
    # Relative to frappe.get_app_path("construction"), i.e. the app package
    # directory (``apps/construction/construction``), not the app source root.
    rules.NODE_DOCTYPE: "construction/doctype/execution_breakdown_node/execution_breakdown_node.json",
    rules.COUNTER_DOCTYPE: "construction/doctype/execution_code_counter/execution_code_counter.json",
}

DEFINITION_FIELD_COLUMNS = (
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


def candidate_protected_definition(doctype):
    """Read the candidate DocType JSON that framework sync would install."""

    relative = PROTECTED_DEFINITION_PATHS.get(doctype)
    if relative is None:
        raise SchemaConflict(f"No candidate definition is bound for {doctype}.")
    root = Path(frappe.get_app_path("construction")).resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SchemaConflict("The candidate definition escapes the app root.") from exc
    if not path.is_file():
        raise SchemaConflict(f"The candidate definition for {doctype} is unavailable.")
    return json.loads(path.read_text(encoding="utf-8"))


class SchemaConflict(Exception):
    pass


def _table_exists(table):
    return bool(frappe.db.sql("SHOW TABLES LIKE %s", (table,)))


def _columns(table):
    rows = frappe.db.sql(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, DATA_TYPE "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s",
        (table,),
        as_dict=True,
    )
    return {row["COLUMN_NAME"]: row for row in rows}


def _indexes(table):
    rows = frappe.db.sql(
        "SELECT INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME "
        "FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s "
        "ORDER BY INDEX_NAME, SEQ_IN_INDEX",
        (table,),
        as_dict=True,
    )
    indexes = {}
    for row in rows:
        entry = indexes.setdefault(row["INDEX_NAME"], {"unique": not int(row["NON_UNIQUE"]), "columns": []})
        entry["columns"].append(row["COLUMN_NAME"])
    return indexes


def _require_columns(table, required):
    columns = _columns(table)
    missing = sorted(set(required) - set(columns))
    if missing:
        raise SchemaConflict(f"{table} is missing required columns: {', '.join(missing)}")
    return columns


def _ensure_signed_bigint(columns):
    column = columns.get("last_issued")
    if column is None:
        raise SchemaConflict("Execution Code Counter.last_issued is missing.")
    column_type = str(column.get("COLUMN_TYPE") or "").lower()
    if "bigint" not in column_type or "unsigned" in column_type:
        raise SchemaConflict("Execution Code Counter.last_issued must be a signed BIGINT.")


def _ensure_unique(table, name, columns):
    indexes = _indexes(table)
    matching = [index for index, entry in indexes.items() if entry["columns"] == list(columns)]
    if matching:
        for index in matching:
            if not indexes[index]["unique"]:
                raise SchemaConflict(f"Index {index} exists without the required uniqueness.")
        return
    if name in indexes:
        raise SchemaConflict(f"Index name {name} already exists with a different definition.")
    duplicates = frappe.db.sql(
        f"SELECT {', '.join(columns)} FROM `{table}` GROUP BY {', '.join(columns)} "
        "HAVING COUNT(*) > 1 LIMIT 1"
    )
    if duplicates:
        raise SchemaConflict(f"Duplicate rows prevent the unique index on {table}.")
    frappe.db.sql_ddl(
        f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{name}` ({', '.join('`' + column + '`' for column in columns)})"
    )


def _ensure_index(table, name, columns):
    indexes = _indexes(table)
    for entry in indexes.values():
        if entry["columns"] == list(columns):
            return
    if name in indexes:
        raise SchemaConflict(f"Index name {name} already exists with a different definition.")
    frappe.db.sql_ddl(
        f"ALTER TABLE `{table}` ADD INDEX `{name}` ({', '.join('`' + column + '`' for column in columns)})"
    )


def _count(doctype, filters):
    if not frappe.db.table_exists(doctype):
        return 0
    return frappe.db.count(doctype, filters)


def _preflight_docTypes():
    if not frappe.db.table_exists("DocType"):
        return
    for doctype in rules.PROTECTED_DOCTYPES:
        rows = frappe.db.get_all(
            "DocType",
            filters={"name": doctype},
            fields=["name", "module", "custom", "istable", "issingle", "is_tree", "is_virtual"],
            limit_page_length=1,
        )
        if not rows:
            continue
        module = rows[0].get("module")
        if module != "construction":
            raise SchemaConflict(f"An unrelated {doctype} DocType already exists in module {module!r}.")
        # Same-module ownership alone is not compatibility: the existing
        # identity flags and complete ordered field definitions must equal the
        # candidate before framework metadata synchronization replaces them.
        existing_fields = frappe.db.get_all(
            "DocField",
            filters={"parent": doctype},
            fields=list(DEFINITION_FIELD_COLUMNS),
            order_by="idx",
            limit_page_length=0,
        )
        try:
            rules.validate_protected_definition(
                doctype, rows[0], existing_fields, candidate_protected_definition(doctype)
            )
        except rules.RuleViolation as error:
            raise SchemaConflict(str(error.message)) from error


def _preflight_permissions():
    for doctype in rules.PROTECTED_DOCTYPES:
        if _count("DocPerm", {"parent": doctype}):
            raise SchemaConflict(f"Stock DocPerm rows already exist for {doctype}.")
        if _count("Custom DocPerm", {"parent": doctype}):
            raise SchemaConflict(f"Custom DocPerm already exists for {doctype}.")
        if _count("DocShare", {"share_doctype": doctype}):
            raise SchemaConflict(f"Shares already exist for {doctype}.")
        if _count("Custom Field", {"dt": doctype}):
            raise SchemaConflict(f"Custom Fields already exist for {doctype}.")
        if _count("Property Setter", {"doc_type": doctype}):
            raise SchemaConflict(f"Property Setters already exist for {doctype}.")
        if _count("Workflow", {"document_type": doctype, "is_active": 1}):
            raise SchemaConflict(f"An active Workflow already exists for {doctype}.")


def _preflight_schema():
    for table, unique_columns in (
        (NODE_TABLE, ("project", "ebs_code")),
        (COUNTER_TABLE, ("project",)),
    ):
        if not _table_exists(table):
            continue
        columns = _columns(table)
        missing = sorted(set(unique_columns) - set(columns))
        if missing:
            raise SchemaConflict(f"{table} is missing required identity columns: {', '.join(missing)}")
        indexes = _indexes(table)
        for index, entry in indexes.items():
            if entry["columns"] == list(unique_columns) and not entry["unique"]:
                raise SchemaConflict(f"Index {index} on {table} exists without the required uniqueness.")
        duplicates = frappe.db.sql(
            f"SELECT {', '.join(unique_columns)} FROM `{table}` "
            f"GROUP BY {', '.join(unique_columns)} HAVING COUNT(*) > 1 LIMIT 1"
        )
        if duplicates:
            raise SchemaConflict(f"Duplicate rows exist in {table}.")


def preflight_install():
    """Detect conflicting installed objects before app metadata is replaced.

    Compatible earlier execution-tree objects (owned by the ``construction``
    module) are allowed through to ``ensure_execution_tree_schema`` for exact
    verification. Unrelated ownership, permissions, shares, metadata and
    incompatible schema fail closed without repairing business data.
    """

    _preflight_docTypes()
    _preflight_permissions()
    _preflight_schema()
    return True


def ensure_execution_tree_schema():
    """Create or verify every required definition; safe to repeat."""

    preflight_install()
    if not _table_exists(NODE_TABLE) or not _table_exists(COUNTER_TABLE):
        raise SchemaConflict("Execution tree DocTypes have not been synchronized yet.")
    node_columns = _require_columns(
        NODE_TABLE,
        ("name", "project", "company", "parent_node", "is_group", "disabled", "ebs_code", "title"),
    )
    counter_columns = _require_columns(COUNTER_TABLE, ("name", "project", "last_issued"))
    _ensure_signed_bigint(counter_columns)
    for column in ("project", "ebs_code", "parent_node", "title"):
        definition = str(node_columns.get(column, {}).get("DATA_TYPE") or "").lower()
        if definition not in ("varchar", "char", "text", "mediumtext", "longtext"):
            raise SchemaConflict(f"Execution Breakdown Node.{column} has an unsupported type.")
    if str(counter_columns.get("project", {}).get("DATA_TYPE") or "").lower() not in (
        "varchar",
        "char",
        "text",
    ):
        raise SchemaConflict("Execution Code Counter.project has an unsupported type.")
    _ensure_unique(COUNTER_TABLE, COUNTER_PROJECT_INDEX, ("project",))
    _ensure_unique(NODE_TABLE, NODE_UNIQUE_INDEX, ("project", "ebs_code"))
    _ensure_index(NODE_TABLE, NODE_PARENT_INDEX, ("project", "parent_node"))
    if _table_exists(f"tab{rules.AUDIT_DOCTYPE}"):
        from construction.services.execution_mapping import reconcile_audit_series_counter

        reconcile_audit_series_counter()
    return verify_execution_tree_schema(strict=False)


def verify_execution_tree_schema(strict=True):
    if not _table_exists(NODE_TABLE) or not _table_exists(COUNTER_TABLE):
        if strict:
            raise SchemaConflict("Execution tree tables are missing.")
        return {"ok": False, "reason": "missing_tables"}
    node_columns = _require_columns(
        NODE_TABLE,
        ("name", "project", "company", "parent_node", "is_group", "disabled", "ebs_code", "title"),
    )
    counter_columns = _require_columns(COUNTER_TABLE, ("name", "project", "last_issued"))
    _ensure_signed_bigint(counter_columns)
    node_indexes = _indexes(NODE_TABLE)
    counter_indexes = _indexes(COUNTER_TABLE)
    node_unique = any(
        entry["unique"] and entry["columns"] == ["project", "ebs_code"] for entry in node_indexes.values()
    )
    parent_index = any(entry["columns"] == ["project", "parent_node"] for entry in node_indexes.values())
    counter_unique = any(
        entry["unique"] and entry["columns"] == ["project"] for entry in counter_indexes.values()
    )
    if strict and not (node_unique and parent_index and counter_unique):
        raise SchemaConflict("Required execution tree indexes are missing.")
    return {
        "ok": bool(node_unique and parent_index and counter_unique),
        "node_unique": node_unique,
        "parent_index": parent_index,
        "counter_unique": counter_unique,
        "counter_bigint": str(counter_columns["last_issued"].get("COLUMN_TYPE") or ""),
    }
