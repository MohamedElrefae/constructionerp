from __future__ import annotations

from collections import Counter
from typing import Any

import frappe

WBS_UNIQUE_CONSTRAINT_NAME = "unique_boq_header_wbs_code"
WBS_UNIQUE_COLUMNS = ("boq_header", "wbs_code")


def _row(doc: Any) -> dict[str, Any]:
    return dict(doc)


def _table_ready(doctype: str) -> bool:
    """Whether the backing table for ``doctype`` exists.

    During a fresh ``install-app``, DocType sync order is not guaranteed: the
    ``BOQ Structure.on_doctype_update`` hook can fire before ``tabBOQ Item``
    is created. Health queries must tolerate that instead of aborting the
    install with a TableMissingError.
    """
    try:
        return bool(frappe.db.table_exists(doctype))
    except Exception:
        return False


def _issue(issue_type: str, severity: str, message: str, **context: Any) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "message": message,
        "context": context,
    }


@frappe.whitelist()
def run_wbs_health_check(boq_header: str | None = None) -> dict[str, Any]:
    """Return a read-only WBS health report for migration and policy decisions."""
    filters = {}
    if boq_header:
        filters["boq_header"] = boq_header

    # Fresh-install tolerance: skip queries for tables that do not exist yet
    # and report the skip instead of crashing mid-sync.
    structure_table_ready = _table_ready("BOQ Structure")
    item_table_ready = _table_ready("BOQ Item")
    skipped: list[str] = []
    if not structure_table_ready:
        skipped.append("BOQ Structure")
    if not item_table_ready:
        skipped.append("BOQ Item")

    structures: list[dict[str, Any]] = []
    if structure_table_ready:
        structures = [
            _row(row)
            for row in frappe.get_all(
                "BOQ Structure",
                filters=filters,
                fields=[
                    "name",
                    "title",
                    "boq_header",
                    "parent_structure",
                    "wbs_code",
                    "is_group",
                    "lft",
                    "rgt",
                    "docstatus",
                ],
                order_by="boq_header, lft, name",
            )
        ]
    items: list[dict[str, Any]] = []
    if item_table_ready:
        items = [
            _row(row)
            for row in frappe.get_all(
                "BOQ Item",
                filters=filters,
                fields=["name", "boq_header", "structure", "docstatus"],
                order_by="boq_header, name",
            )
        ]

    issues: list[dict[str, Any]] = []
    issues.extend(_find_duplicate_wbs(structures))
    issues.extend(_find_blank_wbs(structures))
    issues.extend(_find_parent_issues(structures))
    issues.extend(_find_nested_set_issues(structures))
    issues.extend(_find_boq_item_issues(structures, items))

    by_type = Counter(issue["issue_type"] for issue in issues)
    by_severity = Counter(issue["severity"] for issue in issues)

    return {
        "boq_header": boq_header,
        "healthy": not issues,
        "skipped_tables": skipped,
        "summary": {
            "structures_checked": len(structures),
            "items_checked": len(items),
            "issue_count": len(issues),
            "by_type": dict(sorted(by_type.items())),
            "by_severity": dict(sorted(by_severity.items())),
        },
        "issues": issues,
    }


def ensure_wbs_unique_constraint() -> dict[str, Any]:
    """Add the BOQ Header + WBS Code unique index after health preflight."""
    if not _table_ready("BOQ Structure"):
        # Fresh install mid-sync: the table does not exist yet. The index is
        # added the next time this hook runs (any BOQ Structure update) or by
        # patch v6_8 on migrate.
        return {
            "created": False,
            "skipped": True,
            "reason": "tabBOQ Structure does not exist yet (fresh install sync order)",
        }

    report = run_wbs_health_check()
    if not report.get("healthy"):
        frappe.throw("Cannot add BOQ Structure WBS unique constraint because WBS health check found issues.")

    existing_index = get_wbs_unique_index_name()
    if existing_index:
        return {"created": False, "index_name": existing_index, "health": report["summary"]}

    frappe.db.sql(
        f"""
        ALTER TABLE `tabBOQ Structure`
        ADD UNIQUE KEY `{WBS_UNIQUE_CONSTRAINT_NAME}` (`boq_header`, `wbs_code`)
        """
    )
    return {
        "created": True,
        "index_name": WBS_UNIQUE_CONSTRAINT_NAME,
        "health": report["summary"],
    }


def get_wbs_unique_index_name() -> str | None:
    rows = frappe.db.sql(
        """
        SHOW INDEX FROM `tabBOQ Structure`
        WHERE Non_unique = 0
        """,
        as_dict=True,
    )
    rows = sorted(rows, key=lambda row: (row.get("Key_name"), row.get("Seq_in_index")))
    columns_by_key: dict[str, list[str]] = {}
    for row in rows:
        key_name = row.get("Key_name")
        if key_name == "PRIMARY":
            continue
        columns_by_key.setdefault(key_name, []).append(row.get("Column_name"))

    for key_name, columns in columns_by_key.items():
        if tuple(columns) == WBS_UNIQUE_COLUMNS:
            return key_name

    return None


def _find_duplicate_wbs(structures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for structure in structures:
        wbs_code = (structure.get("wbs_code") or "").strip()
        if not wbs_code:
            continue
        key = (structure.get("boq_header"), wbs_code)
        buckets.setdefault(key, []).append(structure)

    issues = []
    for (boq_header, wbs_code), rows in buckets.items():
        if len(rows) <= 1:
            continue
        issues.append(
            _issue(
                "duplicate_wbs_code",
                "error",
                f"Duplicate WBS code {wbs_code} found in BOQ Header {boq_header}.",
                boq_header=boq_header,
                wbs_code=wbs_code,
                structures=[row["name"] for row in rows],
            )
        )
    return issues


def _find_blank_wbs(structures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _issue(
            "blank_wbs_code",
            "error",
            f"BOQ Structure {structure['name']} has a blank WBS code.",
            structure=structure["name"],
            boq_header=structure.get("boq_header"),
        )
        for structure in structures
        if not (structure.get("wbs_code") or "").strip()
    ]


def _find_parent_issues(structures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {structure["name"]: structure for structure in structures}
    issues = []

    for structure in structures:
        parent_name = structure.get("parent_structure")
        if not parent_name:
            continue

        parent = by_name.get(parent_name)
        if not parent:
            issues.append(
                _issue(
                    "missing_parent_structure",
                    "error",
                    f"BOQ Structure {structure['name']} references missing parent {parent_name}.",
                    structure=structure["name"],
                    parent_structure=parent_name,
                    boq_header=structure.get("boq_header"),
                )
            )
            continue

        if parent.get("boq_header") != structure.get("boq_header"):
            issues.append(
                _issue(
                    "parent_header_mismatch",
                    "error",
                    f"BOQ Structure {structure['name']} parent belongs to another BOQ Header.",
                    structure=structure["name"],
                    parent_structure=parent_name,
                    child_boq_header=structure.get("boq_header"),
                    parent_boq_header=parent.get("boq_header"),
                )
            )

        if not parent.get("is_group"):
            issues.append(
                _issue(
                    "leaf_used_as_parent",
                    "error",
                    f"BOQ Structure {structure['name']} uses leaf {parent_name} as parent.",
                    structure=structure["name"],
                    parent_structure=parent_name,
                    boq_header=structure.get("boq_header"),
                )
            )

    return issues


def _find_nested_set_issues(structures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {structure["name"]: structure for structure in structures}
    issues = []

    for structure in structures:
        lft = structure.get("lft") or 0
        rgt = structure.get("rgt") or 0
        if lft <= 0 or rgt <= 0 or lft >= rgt:
            issues.append(
                _issue(
                    "invalid_nested_set_bounds",
                    "error",
                    f"BOQ Structure {structure['name']} has invalid nested-set bounds.",
                    structure=structure["name"],
                    boq_header=structure.get("boq_header"),
                    lft=lft,
                    rgt=rgt,
                )
            )
            continue

        parent_name = structure.get("parent_structure")
        if not parent_name or parent_name not in by_name:
            continue

        parent = by_name[parent_name]
        parent_lft = parent.get("lft") or 0
        parent_rgt = parent.get("rgt") or 0
        if not (parent_lft < lft and rgt < parent_rgt):
            issues.append(
                _issue(
                    "nested_set_parent_bounds_mismatch",
                    "error",
                    f"BOQ Structure {structure['name']} is not inside its parent's nested-set bounds.",
                    structure=structure["name"],
                    parent_structure=parent_name,
                    boq_header=structure.get("boq_header"),
                    lft=lft,
                    rgt=rgt,
                    parent_lft=parent_lft,
                    parent_rgt=parent_rgt,
                )
            )

    return issues


def _find_boq_item_issues(
    structures: list[dict[str, Any]], items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_structure = {structure["name"]: structure for structure in structures}
    linked_items_by_structure: dict[str, list[dict[str, Any]]] = {}
    issues = []

    for item in items:
        structure_name = item.get("structure")
        if structure_name:
            linked_items_by_structure.setdefault(structure_name, []).append(item)

        structure = by_structure.get(structure_name)
        if not structure:
            issues.append(
                _issue(
                    "boq_item_missing_structure",
                    "error",
                    f"BOQ Item {item['name']} references missing BOQ Structure {structure_name}.",
                    boq_item=item["name"],
                    structure=structure_name,
                    boq_header=item.get("boq_header"),
                )
            )
            continue

        if item.get("boq_header") != structure.get("boq_header"):
            issues.append(
                _issue(
                    "boq_item_header_mismatch",
                    "error",
                    f"BOQ Item {item['name']} header does not match its BOQ Structure.",
                    boq_item=item["name"],
                    structure=structure_name,
                    item_boq_header=item.get("boq_header"),
                    structure_boq_header=structure.get("boq_header"),
                )
            )

        if structure.get("is_group"):
            issues.append(
                _issue(
                    "boq_item_linked_to_group_structure",
                    "error",
                    f"BOQ Item {item['name']} is linked to group BOQ Structure {structure_name}.",
                    boq_item=item["name"],
                    structure=structure_name,
                    boq_header=item.get("boq_header"),
                )
            )

    for structure in structures:
        if structure.get("is_group"):
            continue
        linked_items = linked_items_by_structure.get(structure["name"], [])
        if not linked_items:
            issues.append(
                _issue(
                    "leaf_structure_missing_boq_item",
                    "warning",
                    f"Leaf BOQ Structure {structure['name']} has no linked BOQ Item.",
                    structure=structure["name"],
                    boq_header=structure.get("boq_header"),
                )
            )
        elif len(linked_items) > 1:
            issues.append(
                _issue(
                    "leaf_structure_multiple_boq_items",
                    "error",
                    f"Leaf BOQ Structure {structure['name']} has multiple linked BOQ Items.",
                    structure=structure["name"],
                    boq_header=structure.get("boq_header"),
                    boq_items=[item["name"] for item in linked_items],
                )
            )

    return issues
