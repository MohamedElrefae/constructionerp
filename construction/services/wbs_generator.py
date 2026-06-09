# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now

from construction.services.feature_flags import is_enabled


RESEQUENCE_FLAG = "enable_boq_wbs_resequence"
RESEQUENCE_ROLE = "System Manager"


class WBSGenerator:
    """Hierarchical WBS code generation for BOQ Structure tree."""

    @staticmethod
    def generate_code_for_node(
        boq_header: str, parent_structure: str = None, node_type: str = "Section"
    ) -> str:
        """Generate WBS code for a new node."""
        sibling_count = WBSGenerator._count_siblings(boq_header, parent_structure)
        seq = sibling_count + 1

        if not parent_structure:
            # Root level: 2-digit code
            return f"{seq:02d}"

        # Get parent WBS code
        parent_wbs = frappe.db.get_value("BOQ Structure", parent_structure, "wbs_code")

        if node_type == "Item":
            # Leaf items: 3-digit suffix
            return f"{parent_wbs}.{seq:03d}"
        else:
            # Sections: 2-digit suffix
            return f"{parent_wbs}.{seq:02d}"

    @staticmethod
    def regenerate_subtree(node_name: str, boq_header: str):
        """Regenerate WBS codes for a node and all its descendants."""
        frappe.throw(
            _("Use resequence_wbs for controlled BOQ-wide WBS regeneration. Node-level regeneration is disabled.")
        )

    @staticmethod
    def regenerate_all(boq_header: str):
        """Regenerate all WBS codes for a BOQ header."""
        return _resequence_wbs(
            boq_header,
            create_audit=False,
            require_draft=False,
            require_flag=False,
            require_role=False,
        )

    @staticmethod
    def _count_siblings(boq_header: str, parent_structure: str = None) -> int:
        """Count siblings for a given parent."""
        filters = {"boq_header": boq_header}
        if parent_structure:
            filters["parent_structure"] = parent_structure
        else:
            filters["parent_structure"] = ["is", "not set"]

        return frappe.db.count("BOQ Structure", filters)

    @staticmethod
    def parse_wbs_code(wbs_code: str) -> list:
        """Parse WBS code into segments."""
        return wbs_code.split(".")

    @staticmethod
    def build_wbs_code(segments: list) -> str:
        """Rebuild WBS code from segments."""
        return ".".join(segments)

    @staticmethod
    def validate_wbs_unique(wbs_code: str, boq_header: str, exclude: str = None) -> bool:
        """Check if WBS code is unique within BOQ header."""
        filters = {"boq_header": boq_header, "wbs_code": wbs_code}
        if exclude:
            filters["name"] = ["!=", exclude]

        return not frappe.db.exists("BOQ Structure", filters)

    @staticmethod
    def get_section_rollup(structure_name: str) -> float:
        """Calculate roll-up total for a section."""
        from frappe.utils.nestedset import get_descendants

        node = frappe.get_doc("BOQ Structure", structure_name)

        # Get all leaf nodes in this section
        descendants = get_descendants("BOQ Structure", node.name)

        # Get all BOQ Items for these structures
        items = frappe.get_all("BOQ Item", filters={"structure": ["in", descendants]}, fields=["line_total"])

        return sum(item.line_total for item in items if item.line_total)

    @staticmethod
    def get_leaf_items_in_section(section_name: str):
        """Get all leaf items within a section."""
        from frappe.utils.nestedset import get_descendants

        descendants = get_descendants("BOQ Structure", section_name)
        leaf_nodes = frappe.get_all(
            "BOQ Structure", filters={"name": ["in", descendants], "is_group": 0}, fields=["name"]
        )

        leaf_item_names = [node.name for node in leaf_nodes]
        items = frappe.get_all("BOQ Item", filters={"structure": ["in", leaf_item_names]}, fields=["*"])

        return items


@frappe.whitelist()
def resequence_wbs(boq_header: str) -> dict:
    """Draft-only privileged WBS resequence with an audit Comment."""
    return _resequence_wbs(
        boq_header,
        create_audit=True,
        require_draft=True,
        require_flag=True,
        require_role=True,
    )


def _resequence_wbs(
    boq_header: str,
    *,
    create_audit: bool,
    require_draft: bool,
    require_flag: bool,
    require_role: bool,
) -> dict:
    if not boq_header:
        frappe.throw(_("BOQ Header is required."))
    if not frappe.db.exists("BOQ Header", boq_header):
        frappe.throw(_("BOQ Header {0} was not found.").format(boq_header))
    if require_flag and not is_enabled(RESEQUENCE_FLAG):
        frappe.throw(_("WBS resequence is disabled in Construction Settings."))
    if require_role and RESEQUENCE_ROLE not in frappe.get_roles():
        frappe.throw(_("Only System Manager can resequence BOQ WBS codes."))

    status = frappe.db.get_value("BOQ Header", boq_header, "status")
    if require_draft and status != "Draft":
        frappe.throw(_("WBS resequence is allowed only while BOQ Header is Draft."))

    frappe.db.sql("select name from `tabBOQ Header` where name = %s for update", boq_header)
    rows = _get_structure_rows(boq_header)
    if not rows:
        return {
            "boq_header": boq_header,
            "status": status,
            "changed_count": 0,
            "audit_comment": None,
            "message": "No BOQ Structure rows to resequence.",
        }

    before = {row.name: row.wbs_code for row in rows}
    after = _build_resequence_map(rows)
    changed = [name for name, new_code in after.items() if before.get(name) != new_code]

    _set_temporary_wbs_codes(boq_header, rows)
    for name, new_code in after.items():
        frappe.db.set_value("BOQ Structure", name, "wbs_code", new_code, update_modified=False)

    audit_comment = _write_resequence_audit(boq_header, before, after, changed) if create_audit else None

    return {
        "boq_header": boq_header,
        "status": status,
        "changed_count": len(changed),
        "structure_count": len(rows),
        "audit_comment": audit_comment,
        "before": before,
        "after": after,
    }


def _get_structure_rows(boq_header: str) -> list:
    return frappe.get_all(
        "BOQ Structure",
        filters={"boq_header": boq_header},
        fields=["name", "parent_structure", "is_group", "wbs_code", "lft", "creation"],
        order_by="lft asc, creation asc, name asc",
    )


def _build_resequence_map(rows: list) -> dict[str, str]:
    rows_by_parent: dict[str, list] = {}
    row_by_name = {row.name: row for row in rows}

    for row in rows:
        parent = row.parent_structure if row.parent_structure in row_by_name else None
        rows_by_parent.setdefault(parent or "", []).append(row)

    result: dict[str, str] = {}

    def assign(parent_name: str, parent_code: str | None):
        siblings = rows_by_parent.get(parent_name or "", [])
        for seq, row in enumerate(siblings, start=1):
            if parent_code:
                width = 2 if row.is_group else 3
                code = f"{parent_code}.{seq:0{width}d}"
            else:
                code = f"{seq:02d}"
            result[row.name] = code
            assign(row.name, code)

    assign("", None)
    return result


def _set_temporary_wbs_codes(boq_header: str, rows: list):
    prefix = f"__RESEQ__{frappe.generate_hash(length=10)}"
    for idx, row in enumerate(rows, start=1):
        temp_code = f"{prefix}_{idx:04d}"
        frappe.db.set_value("BOQ Structure", row.name, "wbs_code", temp_code, update_modified=False)


def _write_resequence_audit(boq_header: str, before: dict, after: dict, changed: list[str]) -> str:
    payload = {
        "action": "resequence_wbs",
        "timestamp": now(),
        "user": frappe.session.user,
        "changed_count": len(changed),
        "before": {name: before.get(name) for name in changed},
        "after": {name: after.get(name) for name in changed},
    }
    comment = frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "BOQ Header",
            "reference_name": boq_header,
            "content": "WBS resequence audit\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        }
    )
    comment.insert(ignore_permissions=True)
    return comment.name
