# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import json
import os

import frappe

# ---------------------------------------------------------------------------
# BOQ Integration Setup
# ---------------------------------------------------------------------------

BOQ_DIMENSION_NAME = "BOQ Item"
BOQ_DIMENSION_DOCTYPE = "BOQ Item"

BOQ_TRANSACTION_CHILD_DOCTYPES = (
    "Purchase Order Item",
    "Purchase Receipt Item",
    "Purchase Invoice Item",
    "Stock Entry Detail",
    "Timesheet Detail",
    "Journal Entry Account",
    "Sales Invoice Item",
    "Material Request Item",
)

BOQ_CASCADE_INSERT_AFTER = {
    "Purchase Order Item": "expense_category",
    "Purchase Receipt Item": "expense_category",
    "Purchase Invoice Item": "expense_category",
    "Stock Entry Detail": "expense_category",
    "Timesheet Detail": "activity_type",
    "Journal Entry Account": "account",
    "Sales Invoice Item": "is_progress_billing",
    "Material Request Item": "expense_category",
}

BOQ_EXPENSE_CATEGORY_INSERT_AFTER = {
    "Purchase Order Item": "item_code",
    "Purchase Receipt Item": "item_code",
    "Purchase Invoice Item": "cost_center",
    "Stock Entry Detail": "item_code",
    "Journal Entry Account": "account",
    "Material Request Item": "item_code",
}

BOQ_CASCADE_DEPENDS_ON = {
    "Purchase Order Item": "eval:doc.expense_category == 'Direct'",
    "Purchase Receipt Item": "eval:doc.expense_category == 'Direct'",
    "Purchase Invoice Item": "eval:doc.expense_category == 'Direct'",
    "Stock Entry Detail": "eval:doc.expense_category == 'Direct'",
    "Journal Entry Account": "eval:doc.expense_category == 'Direct'",
    "Material Request Item": "eval:doc.expense_category == 'Direct'",
    "Sales Invoice Item": "eval:doc.is_progress_billing",
    "Timesheet Detail": (
        "eval:frappe.boot.direct_labor_designations "
        "&& frappe.boot.direct_labor_designations.includes(doc.designation)"
    ),
}

BOQ_EXPENSE_CATEGORY_DOCTYPES = {
    "Purchase Order Item",
    "Purchase Receipt Item",
    "Purchase Invoice Item",
    "Stock Entry Detail",
    "Journal Entry Account",
    "Material Request Item",
}

BOQ_LEGACY_EXPENSE_CATEGORY_HIDE_DOCTYPES = {
    "Sales Invoice Item",
    "Timesheet Detail",
}

BOQ_CASCADE_FIELDNAMES = (
    "boq_header",
    "boq_structure",
    "boq_item",
    "boq_item_stage",
    "boq_selection_scope_type",
)

DIRECT_LABOR_DESIGNATION_DEFAULTS = (
    ("Site Worker", "Mandatory"),
    ("Mason", "Mandatory"),
    ("Carpenter", "Mandatory"),
    ("Steel Fixer", "Mandatory"),
    ("Operator", "Mandatory"),
    ("Electrician", "Mandatory"),
    ("Plumber", "Mandatory"),
    ("Site Engineer", "Optional"),
    ("Site Supervisor", "Optional"),
    ("Foreman", "Optional"),
    ("Project Manager", "Not Applicable"),
)


def setup_website_branding():
    """Apply website defaults when the Website module is available."""
    if not frappe.db.exists("DocType", "Website Settings"):
        return

    settings = frappe.get_single("Website Settings")
    meta = frappe.get_meta("Website Settings")
    updates = {
        "home_page": "index",
        "app_name": "Construction Sense",
        "banner_image": "/assets/construction/images/construction_logo.svg",
        "splash_image": "/assets/construction/images/construction_logo.svg",
        "disable_signup": 1,
    }

    changed = False
    for fieldname, value in updates.items():
        if meta.has_field(fieldname) and getattr(settings, fieldname, None) != value:
            setattr(settings, fieldname, value)
            changed = True

    if changed:
        settings.save(ignore_permissions=True)


def fix_select_permissions():
    """Set select=1 on all DocPerm records that have read=1 but select=0.

    In Frappe v16, DatabaseQuery.check_select_permission() requires
    'select' permission for frappe.get_list() calls (used by Number
    Cards, Dashboard Charts, etc.). ERPNext ships most roles with
    read=1 but select=0, which causes permission errors on workspace
    widgets for non-admin users.

    This is idempotent and safe: 'read' already grants data visibility,
    'select' just allows the query to run.
    """
    try:
        updated = frappe.db.sql(
            "UPDATE `tabDocPerm` SET `select`=1 WHERE `read`=1 AND `select`=0",
            update=True,
        )
        if updated:
            frappe.db.commit()
            frappe.clear_cache()
    except Exception:
        pass


def fix_system_manager_permissions():
    """Ensure System Manager role has DocPerm entries on ALL doctypes.

    In some local databases, System Manager DocPerm entries are missing
    from ERPNext doctypes (Sales Order, Purchase Order, Project, etc.).
    Without these, even System Manager users get 'Insufficient Permission'
    errors on workspace Number Cards and Dashboard Charts.

    This is idempotent: it only inserts entries where none exist.
    """
    try:
        doctypes = frappe.db.sql("""
            SELECT DISTINCT dt.name
            FROM `tabDocType` dt
            WHERE NOT EXISTS (
                SELECT 1 FROM `tabDocPerm` dp
                WHERE dp.parent = dt.name AND dp.role = 'System Manager'
            )
            AND dt.name NOT IN ('DocType', 'DocField', 'DocPerm', 'Custom Field',
                'Property Setter', 'Installed Application', 'Installed Apps',
                'Module Def', 'Module Onboarding', 'Section Order')
        """)

        inserted = 0
        for (dt_name,) in doctypes:
            try:
                meta = frappe.get_meta(dt_name)
                frappe.get_doc({
                    "doctype": "DocPerm",
                    "parent": dt_name,
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": "System Manager",
                    "permlevel": 0,
                    "read": 1,
                    "write": 1,
                    "create": 1,
                    "delete": 1,
                    "submit": 1 if meta.is_submittable else 0,
                    "cancel": 1 if meta.is_submittable else 0,
                    "amend": 1 if meta.is_submittable else 0,
                    "print": 1,
                    "email": 1,
                    "report": 1,
                    "import": 1,
                    "export": 1,
                    "share": 1,
                    "select": 1,
                }).db_insert()
                inserted += 1
            except Exception:
                pass

        if inserted:
            frappe.db.commit()
            frappe.clear_cache()
    except Exception:
        pass


def setup_boq_integration():
    """Idempotently provision BOQ accounting and operational fields."""
    setup_boq_accounting_dimension()
    setup_boq_custom_fields()
    setup_boq_indexes()
    setup_boq_rollout_mode()
    setup_direct_labor_designations()
    setup_boq_structure_constraints()
    setup_boq_print_formats()


def setup_boq_print_formats():
    if not frappe.db.exists("DocType", "Print Format"):
        return

    print_format_path = os.path.join(
        frappe.get_app_path("construction"),
        "print_format",
        "boq_print_format",
        "boq_print_format.json",
    )
    if not os.path.exists(print_format_path):
        return

    with open(print_format_path) as f:
        data = json.load(f)

    data = {key: value for key, value in data.items() if not isinstance(value, list)}

    name = data.get("name")
    if not name:
        return

    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        changed = False
        for fieldname, value in data.items():
            if fieldname in {"doctype", "name", "creation", "modified", "modified_by", "owner", "idx"}:
                continue
            if hasattr(doc, fieldname) and getattr(doc, fieldname) != value:
                setattr(doc, fieldname, value)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
        return

    doc = frappe.get_doc(data)
    doc.insert(ignore_permissions=True)


def setup_boq_structure_constraints():
    if not frappe.db.table_exists("tabBOQ Structure"):
        return

    from construction.services.boq_wbs_health import ensure_wbs_unique_constraint

    ensure_wbs_unique_constraint()


def setup_boq_accounting_dimension():
    if not frappe.db.exists("DocType", BOQ_DIMENSION_DOCTYPE):
        return
    if not frappe.db.exists("DocType", "Accounting Dimension"):
        return

    dimension_name = frappe.db.get_value(
        "Accounting Dimension", {"document_type": BOQ_DIMENSION_DOCTYPE}, "name"
    )

    if dimension_name:
        dimension = frappe.get_doc("Accounting Dimension", dimension_name)
        if dimension.disabled:
            dimension.disabled = 0
            dimension.save(ignore_permissions=True)
    else:
        dimension = frappe.new_doc("Accounting Dimension")
        dimension.document_type = BOQ_DIMENSION_DOCTYPE
        dimension.label = BOQ_DIMENSION_NAME
        dimension.insert(ignore_permissions=True)

    _sync_boq_dimension_fields(dimension)


def _sync_boq_dimension_fields(dimension):
    try:
        from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
            make_dimension_in_accounting_doctypes,
        )
    except Exception:
        frappe.log_error(
            "ERPNext Accounting Dimension sync function could not be imported",
            "BOQ Integration Setup",
        )
        return

    make_dimension_in_accounting_doctypes(doc=dimension)


def setup_boq_custom_fields():
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except Exception:
        frappe.log_error("Custom Field API could not be imported", "BOQ Integration Setup")
        return

    for doctype in BOQ_TRANSACTION_CHILD_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue

        meta = frappe.get_meta(doctype, cached=False)
        for field in _get_boq_custom_fields_for_doctype(doctype):
            field_def = field.copy()
            field_def["insert_after"] = _resolve_insert_after(meta, field_def.get("insert_after"))
            _sync_custom_field(doctype, field_def, create_custom_field)
            frappe.clear_cache(doctype=doctype)
            meta = frappe.get_meta(doctype, cached=False)
        _hide_legacy_expense_category_field(doctype)


def _get_boq_custom_fields_for_doctype(doctype):
    fields = []
    if doctype in BOQ_EXPENSE_CATEGORY_DOCTYPES:
        fields.append(
            {
                "fieldname": "expense_category",
                "fieldtype": "Select",
                "options": "\nDirect\nIndirect\nOverhead\nCapital",
                "label": "Expense Category",
                "default": "" if doctype == "Journal Entry Account" else "Direct",
                "insert_after": BOQ_EXPENSE_CATEGORY_INSERT_AFTER.get(doctype),
                "hidden": 0,
                "read_only": 0,
                "description": "Set to Direct to unlock BOQ attribution fields.",
            }
        )
    elif doctype == "Sales Invoice Item":
        fields.append(
            {
                "fieldname": "is_progress_billing",
                "fieldtype": "Check",
                "label": "Progress Billing",
                "default": "0",
                "insert_after": "item_code",
                "hidden": 0,
                "read_only": 0,
                "in_list_view": 1,
                "columns": 1,
            }
        )
    elif doctype == "Timesheet Detail":
        fields.append(
            {
                "fieldname": "designation",
                "fieldtype": "Data",
                "label": "Employee Designation",
                "insert_after": "activity_type",
                "hidden": 1,
                "read_only": 1,
                "no_copy": 1,
            }
        )

    base_gate = BOQ_CASCADE_DEPENDS_ON.get(doctype, "eval:doc.expense_category == 'Direct'")
    base_expr = _strip_eval(base_gate)

    fields.extend(
        [
            {
                "fieldname": "boq_header",
                "fieldtype": "Link",
                "options": "BOQ Header",
                "label": "BOQ Header",
                "insert_after": BOQ_CASCADE_INSERT_AFTER.get(doctype),
                "depends_on": f"eval:{base_expr}",
                "read_only_depends_on": f"eval:!({base_expr})",
                "hidden": 0,
                "read_only": 0,
                "description": "Locked until the row is applicable for direct BOQ attribution.",
            },
            {
                "fieldname": "boq_structure",
                "fieldtype": "Link",
                "options": "BOQ Structure",
                "label": "BOQ Structure",
                "insert_after": "boq_header",
                "depends_on": f"eval:doc.boq_header && ({base_expr})",
                "read_only_depends_on": f"eval:!doc.boq_header || !({base_expr})",
                "hidden": 0,
                "read_only": 0,
                "description": "Locked until a BOQ Header is selected.",
            },
            {
                "fieldname": "boq_item",
                "fieldtype": "Link",
                "options": "BOQ Item",
                "label": "BOQ Item",
                "insert_after": "boq_structure",
                "depends_on": f"eval:doc.boq_header && doc.boq_structure && ({base_expr})",
                "read_only_depends_on": f"eval:!doc.boq_header || !doc.boq_structure || !({base_expr})",
                "hidden": 0,
                "read_only": 0,
                "description": "Locked until BOQ Header and BOQ Structure are selected.",
            },
            {
                "fieldname": "boq_item_stage",
                "fieldtype": "Link",
                "options": "BOQ Item Stage",
                "label": "BOQ Item Stage",
                "insert_after": "boq_item",
                "depends_on": f"eval:doc.boq_item && ({base_expr})",
                "read_only_depends_on": f"eval:!doc.boq_item || !({base_expr})",
                "hidden": 0,
                "read_only": 0,
                "description": "Locked until a BOQ Item is selected.",
            },
            {
                "fieldname": "boq_selection_scope_type",
                "fieldtype": "Select",
                "options": "\nProject-Scoped\nCompany-CostCenter-Scoped",
                "label": "BOQ Selection Scope Type",
                "insert_after": "boq_item_stage",
                "hidden": 1,
                "read_only": 1,
                "no_copy": 1,
            },
        ]
    )
    return fields


def _sync_custom_field(doctype, field_def, create_custom_field):
    meta = frappe.get_meta(doctype, cached=False)
    fieldname = field_def["fieldname"]
    custom_field_name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")

    if not custom_field_name and meta.has_field(fieldname):
        return

    if not custom_field_name:
        create_custom_field(doctype, field_def, ignore_validate=True)
        return

    doc = frappe.get_doc("Custom Field", custom_field_name)
    changed = False
    for key, value in field_def.items():
        if getattr(doc, key, None) != value:
            setattr(doc, key, value)
            changed = True
    if changed:
        doc.save(ignore_permissions=True)


def _hide_legacy_expense_category_field(doctype):
    if doctype not in BOQ_LEGACY_EXPENSE_CATEGORY_HIDE_DOCTYPES:
        return

    custom_field_name = frappe.db.get_value(
        "Custom Field", {"dt": doctype, "fieldname": "expense_category"}, "name"
    )
    if not custom_field_name:
        return

    doc = frappe.get_doc("Custom Field", custom_field_name)
    changed = False
    for key, value in {
        "hidden": 1,
        "read_only": 1,
        "no_copy": 1,
        "description": "Legacy BOQ expense gate hidden; this DocType uses its own BOQ cascade gate.",
    }.items():
        if getattr(doc, key, None) != value:
            setattr(doc, key, value)
            changed = True
    if changed:
        doc.save(ignore_permissions=True)


def _default_insert_anchor(doctype):
    return BOQ_CASCADE_INSERT_AFTER.get(doctype) or "project"


def _strip_eval(expression):
    return (expression or "").replace("eval:", "", 1)


def _resolve_insert_after(meta, preferred_field):
    if preferred_field and meta.has_field(preferred_field):
        return preferred_field

    for fallback in ("project", "item_code", "account", "activity_type"):
        if meta.has_field(fallback):
            return fallback

    fields = meta.get("fields") or []
    return fields[-1].fieldname if fields else None


def setup_boq_indexes():
    indexes = (
        ("BOQ Header", ["project"], "idx_boq_header_project"),
        ("BOQ Structure", ["boq_header", "is_group"], "idx_boq_structure_header_group"),
        ("BOQ Item", ["boq_header", "structure"], "idx_boq_item_header_structure"),
        ("BOQ Item Stage", ["boq_item"], "idx_boq_item_stage_item"),
    )
    for doctype, fields, index_name in indexes:
        if not frappe.db.table_exists(doctype):
            continue
        if not all(frappe.db.has_column(doctype, field) for field in fields):
            continue
        if _index_exists(doctype, index_name):
            continue
        try:
            frappe.db.add_index(doctype, fields, index_name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed to add BOQ cascade index {index_name}",
            )


def _index_exists(doctype, index_name):
    return bool(
        frappe.db.sql(
            """
			SELECT 1
			FROM information_schema.statistics
			WHERE table_schema = DATABASE()
			  AND table_name = %(table_name)s
			  AND index_name = %(index_name)s
			LIMIT 1
			""",
            {"table_name": f"tab{doctype}", "index_name": index_name},
        )
    )


def setup_direct_labor_designations():
    if not frappe.db.exists("DocType", "Construction Settings"):
        return
    if not frappe.db.table_exists("Direct Labor Designation"):
        return
    if not frappe.get_meta("Construction Settings", cached=False).has_field("direct_labor_designations"):
        return
    if not frappe.db.exists("DocType", "Designation"):
        return

    settings = frappe.get_single("Construction Settings")
    existing = {
        row.designation for row in (settings.get("direct_labor_designations") or []) if row.designation
    }
    available_designations = {
        row.name
        for row in frappe.get_all(
            "Designation",
            filters={"name": ["in", [item[0] for item in DIRECT_LABOR_DESIGNATION_DEFAULTS]]},
            fields=["name"],
        )
    }
    changed = False
    for designation, requirement in DIRECT_LABOR_DESIGNATION_DEFAULTS:
        if designation in existing or designation not in available_designations:
            continue
        settings.append(
            "direct_labor_designations",
            {"designation": designation, "boq_requirement": requirement},
        )
        changed = True
    if changed:
        settings.save(ignore_permissions=True)


def setup_boq_rollout_mode():
    if not frappe.db.exists("DocType", "Construction Settings"):
        return
    if not frappe.get_meta("Construction Settings", cached=False).has_field("enable_boq_cascade_filtering"):
        return

    current = frappe.db.sql(
        """
		SELECT value
		FROM `tabSingles`
		WHERE doctype = %(doctype)s
		  AND field = %(field)s
		""",
        {
            "doctype": "Construction Settings",
            "field": "enable_boq_cascade_filtering",
        },
        as_dict=True,
    )
    current_value = current[0].value if current else None
    if current_value in {"Off", "On", "Strict"}:
        return
    if current:
        frappe.db.sql(
            """
			UPDATE `tabSingles`
			SET value = %(value)s
			WHERE doctype = %(doctype)s
			  AND field = %(field)s
			""",
            {
                "value": "Off",
                "doctype": "Construction Settings",
                "field": "enable_boq_cascade_filtering",
            },
        )
    else:
        frappe.db.set_single_value("Construction Settings", "enable_boq_cascade_filtering", "Off")


# ---------------------------------------------------------------------------
# Form Layout Profile Seeds
# ---------------------------------------------------------------------------

DEFAULT_BOQ_HEADER_LAYOUT = {
    "version": 1,
    "unassigned_policy": "append",
    "sections": [
        {
            "id": "sec_identity",
            "label": "Identity",
            "column_count": 3,
            "sort_order": 1,
            "visible": True,
            "collapsible": False,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "project", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "project_name", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "boq_type", "col": 3, "sort_order": 3, "visible": True},
                {"fieldname": "status", "col": 1, "sort_order": 4, "visible": True},
                {"fieldname": "title", "col": 2, "sort_order": 5, "visible": True},
                {"fieldname": "version", "col": 3, "sort_order": 6, "visible": True},
            ],
        },
        {
            "id": "sec_financial",
            "label": "Financial Summary",
            "column_count": 3,
            "sort_order": 2,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "total_contract_value", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "total_estimated_value", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "total_budgeted_cost", "col": 3, "sort_order": 3, "visible": True},
            ],
        },
        {
            "id": "sec_audit",
            "label": "Lock Information",
            "column_count": 2,
            "sort_order": 3,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": True,
            "fields": [
                {"fieldname": "locked_by", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "locked_date", "col": 2, "sort_order": 2, "visible": True},
            ],
        },
    ],
}

DEFAULT_BOQ_ITEM_STAGE_LAYOUT = {
    "version": 1,
    "unassigned_policy": "append",
    "sections": [
        {
            "id": "sec_identity",
            "label": "Identity",
            "column_count": 2,
            "sort_order": 1,
            "visible": True,
            "collapsible": False,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "project", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "boq_header", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "boq_structure", "col": 1, "sort_order": 3, "visible": True},
                {"fieldname": "boq_item", "col": 2, "sort_order": 4, "visible": True},
                {"fieldname": "stage_code", "col": 1, "sort_order": 5, "visible": True},
                {"fieldname": "stage_name", "col": 2, "sort_order": 6, "visible": True},
                {"fieldname": "stage_status", "col": 1, "sort_order": 7, "visible": True},
            ],
        },
        {
            "id": "sec_quantities",
            "label": "Quantities",
            "column_count": 2,
            "sort_order": 2,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "planned_qty", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "percent_complete", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "measured_executed_qty", "col": 1, "sort_order": 3, "visible": True},
                {"fieldname": "certified_qty", "col": 2, "sort_order": 4, "visible": True},
            ],
        },
        {
            "id": "sec_notes",
            "label": "Notes",
            "column_count": 1,
            "sort_order": 3,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "description", "col": 1, "sort_order": 1, "visible": True},
            ],
        },
    ],
}

DEFAULT_BOQ_STRUCTURE_LAYOUT = {
    "version": 1,
    "unassigned_policy": "append",
    "sections": [
        {
            "id": "sec_identity",
            "label": "Identity",
            "column_count": 2,
            "sort_order": 1,
            "visible": True,
            "collapsible": False,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "title", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "wbs_code", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "boq_header", "col": 1, "sort_order": 3, "visible": True},
                {"fieldname": "project", "col": 2, "sort_order": 4, "visible": True},
                {"fieldname": "parent_structure", "col": 1, "sort_order": 5, "visible": True},
                {"fieldname": "is_group", "col": 2, "sort_order": 6, "visible": True},
                {"fieldname": "description", "col": 1, "sort_order": 7, "visible": True},
            ],
        },
        {
            "id": "sec_owner_refs",
            "label": "Owner References",
            "column_count": 3,
            "sort_order": 2,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "owner_page", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "owner_ref_no", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "owner_file_ref", "col": 3, "sort_order": 3, "visible": True},
            ],
        },
    ],
}


DEFAULT_USER_SCOPE_CONTEXT_LAYOUT = {
    "version": 1,
    "unassigned_policy": "append",
    "sections": [
        {
            "id": "sec_scope",
            "label": "Scope Context",
            "column_count": 2,
            "sort_order": 1,
            "visible": True,
            "collapsible": False,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "user", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "company", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "project", "col": 1, "sort_order": 3, "visible": True},
                {"fieldname": "cost_center", "col": 2, "sort_order": 4, "visible": True},
                {"fieldname": "department", "col": 1, "sort_order": 5, "visible": True},
                {"fieldname": "branch", "col": 2, "sort_order": 6, "visible": True},
            ],
        },
        {
            "id": "sec_meta",
            "label": "Session Metadata",
            "column_count": 2,
            "sort_order": 2,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": True,
            "fields": [
                {"fieldname": "scope_version", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "last_active_at", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "client_id", "col": 1, "sort_order": 3, "visible": True},
            ],
        },
    ],
}

DEFAULT_PROJECT_LAYOUT = {
    "version": 1,
    "unassigned_policy": "append",
    "sections": [
        {
            "id": "sec_identity",
            "label": "Project Identity",
            "column_count": 2,
            "sort_order": 1,
            "visible": True,
            "collapsible": False,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "project_name", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "status", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "project_type", "col": 1, "sort_order": 3, "visible": True},
                {"fieldname": "percent_complete", "col": 2, "sort_order": 4, "visible": True},
            ],
        },
        {
            "id": "sec_schedule",
            "label": "Schedule",
            "column_count": 2,
            "sort_order": 2,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": False,
            "fields": [
                {"fieldname": "expected_start_date", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "expected_end_date", "col": 2, "sort_order": 2, "visible": True},
            ],
        },
        {
            "id": "sec_costing",
            "label": "Costing",
            "column_count": 2,
            "sort_order": 3,
            "visible": True,
            "collapsible": True,
            "collapsed_by_default": True,
            "fields": [
                {"fieldname": "estimated_costing", "col": 1, "sort_order": 1, "visible": True},
                {"fieldname": "total_sales_amount", "col": 2, "sort_order": 2, "visible": True},
                {"fieldname": "total_purchase_cost", "col": 1, "sort_order": 3, "visible": True},
                {"fieldname": "gross_margin", "col": 2, "sort_order": 4, "visible": True},
            ],
        },
    ],
}


def seed_form_layout_profiles():
    """Seed default Form Layout Profiles for construction DocTypes.

    Called by after_migrate hook. Idempotent — skips existing profiles.
    Covers: BOQ Header, BOQ Item Stage, BOQ Structure, User Scope Context, Project.

    Stage 1: construction module doctypes only.
    Future stages will expand to the full ERPNext app.
    """
    profiles = [
        {
            "reference_doctype": "BOQ Header",
            "profile_name": "Default",
            "is_default": 1,
            "is_system": 1,
            "priority": 10,
            "sections_json": json.dumps(DEFAULT_BOQ_HEADER_LAYOUT),
        },
        {
            "reference_doctype": "BOQ Item Stage",
            "profile_name": "Default",
            "is_default": 1,
            "is_system": 1,
            "priority": 10,
            "sections_json": json.dumps(DEFAULT_BOQ_ITEM_STAGE_LAYOUT),
        },
        {
            "reference_doctype": "BOQ Structure",
            "profile_name": "Default",
            "is_default": 1,
            "is_system": 1,
            "priority": 10,
            "sections_json": json.dumps(DEFAULT_BOQ_STRUCTURE_LAYOUT),
        },
        {
            "reference_doctype": "User Scope Context",
            "profile_name": "Default",
            "is_default": 1,
            "is_system": 1,
            "priority": 10,
            "sections_json": json.dumps(DEFAULT_USER_SCOPE_CONTEXT_LAYOUT),
        },
        {
            "reference_doctype": "Project",
            "profile_name": "Default",
            "is_default": 1,
            "is_system": 1,
            "priority": 10,
            "sections_json": json.dumps(DEFAULT_PROJECT_LAYOUT),
        },
    ]

    for data in profiles:
        # Skip if the target DocType isn't registered yet (e.g. not yet migrated)
        if not frappe.db.exists("DocType", data["reference_doctype"]):
            continue

        name = frappe.db.get_value(
            "Form Layout Profile",
            {"reference_doctype": data["reference_doctype"], "profile_name": data["profile_name"]},
            "name",
        )
        if name:
            continue

        doc = frappe.get_doc({"doctype": "Form Layout Profile", **data})
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# System Themes
# ---------------------------------------------------------------------------

SYSTEM_THEMES = [
    {
        "theme_name": "Light",
        "theme_type": "Custom Light",
        "is_system_theme": 1,
        "is_active": 1,
        "accent_primary": "#2076FF",
        "emoji_icon": "☀️",
        "navbar_bg": "#FFFFFF",
        "sidebar_bg": "#F8FAFC",
        "surface_bg": "#FFFFFF",
        "body_bg": "#F5F6FA",
        "text_primary": "#2C3E50",
        "text_secondary": "#7F8C8D",
        "border_color": "#D5DADF",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
    },
    {
        "theme_name": "Dark",
        "theme_type": "Custom Dark",
        "is_system_theme": 1,
        "is_active": 1,
        "accent_primary": "#2076FF",
        "emoji_icon": "🌙",
        "navbar_bg": "#1E1E1E",
        "sidebar_bg": "#2D2D2D",
        "surface_bg": "#3A3A3A",
        "body_bg": "#1A1A1A",
        "text_primary": "#E8E8E8",
        "text_secondary": "#A8A8A8",
        "border_color": "#4A4A4A",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "error_color": "#dc3545",
    },
    {
        "theme_name": "Construction Light",
        "theme_type": "Construction Light",
        "is_system_theme": 1,
        "is_active": 1,
        "accent_primary": "#2563EB",
        "emoji_icon": "🏗️",
        "navbar_bg": "#FFFFFF",
        "sidebar_bg": "#F8FAFC",
        "surface_bg": "#FFFFFF",
        "body_bg": "#F8FAFC",
        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "border_color": "#E2E8F0",
        "success_color": "#16A34A",
        "warning_color": "#D97706",
        "error_color": "#DC2626",
    },
    {
        "theme_name": "Construction Dark",
        "theme_type": "Construction Dark",
        "is_system_theme": 1,
        "is_active": 1,
        "accent_primary": "#2563EB",
        "emoji_icon": "🏗️",
        "navbar_bg": "#1E293B",
        "sidebar_bg": "#0F172A",
        "surface_bg": "#1E293B",
        "body_bg": "#0F172A",
        "text_primary": "#F8FAFC",
        "text_secondary": "#94A3B8",
        "border_color": "#334155",
        "success_color": "#22C55E",
        "warning_color": "#F59E0B",
        "error_color": "#EF4444",
    },
]


def create_system_themes():
    """Idempotent creation of the 4 system themes.

    Called by after_install and after_migrate hooks.
    Does NOT call frappe.db.commit() — Frappe manages the transaction.
    """
    for theme_data in SYSTEM_THEMES:
        if not frappe.db.exists("Construction Theme", theme_data["theme_name"]):
            doc = frappe.get_doc({"doctype": "Construction Theme", **theme_data})
            doc.flags.ignore_permissions = True
            doc.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Branch.company Custom Field (required for HR integrity)
# ---------------------------------------------------------------------------


def setup_erpnext_standard_filters():
    """Apply Property Setters that hide Company standard filters on ERPNext transactional DocTypes.

    Called by after_install and after_migrate hooks, and by patch.
    Idempotent — safe to run multiple times.
    """
    from construction.patches.v7_2.set_erpnext_standard_filters import (
        setup_erpnext_standard_filters as _setup,
    )

    _setup()


def setup_branch_company_field():
    """Create Branch.company Custom Field if missing.

    Called by after_install hook and by patch.
    Does NOT call frappe.db.commit() — caller manages the transaction.
    """
    if not frappe.db.exists("DocType", "Branch"):
        return
    if not frappe.db.exists("Custom Field", {"dt": "Branch", "fieldname": "company"}):
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Branch",
                "fieldname": "company",
                "label": "Company",
                "fieldtype": "Link",
                "options": "Company",
                "insert_after": "branch",
                "in_list_view": 1,
                "in_standard_filter": 1,
            }
        ).insert(ignore_permissions=True)


def setup_variation_order_custom_field():
    """Create or idempotently reconcile Material Request.custom_variation_order.

    Reconciliation covers pre-existing fields created before search indexing
    was introduced, so upgrades converge on the same schema as fresh installs.
    Index-creation errors are logged loudly instead of being swallowed.
    """
    if not frappe.db.exists("DocType", "Material Request"):
        return

    field_name = frappe.db.get_value(
        "Custom Field", {"dt": "Material Request", "fieldname": "custom_variation_order"}
    )
    if not field_name:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Material Request",
                "fieldname": "custom_variation_order",
                "label": "Variation Order",
                "fieldtype": "Link",
                "options": "Variation Order",
                "insert_after": "title",
                "read_only": 1,
                "search_index": 1,
            }
        ).insert(ignore_permissions=True)
    elif not frappe.db.get_value("Custom Field", field_name, "search_index"):
        # Reconcile legacy field metadata so DocType matches the physical index.
        frappe.db.set_value("Custom Field", field_name, "search_index", 1)
        frappe.clear_doctype_cache("Material Request")

    try:
        frappe.db.add_index("Material Request", ["custom_variation_order"], "idx_mr_custom_vo")
    except Exception as e:
        frappe.logger("construction_install").error(
            f"Failed to ensure idx_mr_custom_vo index on 'tabMaterial Request': {e}"
        )

    _enforce_one_active_mr_per_vo()


def _enforce_one_active_mr_per_vo():
    """Enforce a database-backed one-non-cancelled-MR-per-VO invariant.

    MariaDB cannot express a partial UNIQUE index (``UNIQUE ... WHERE
    docstatus < 2``), so we add a STORED generated column that is the VO
    name only while the MR is not cancelled, and NULL otherwise. NULLs do
    not participate in a UNIQUE index, so at most one non-cancelled MR can
    reference any given Variation Order. Cancelled MRs (``docstatus = 2``)
    do NOT block a replacement — matching the ``docstatus < 2`` logic used
    by ``create_material_request_for_vo``.

    The reconcile is idempotent and logged loudly (never silently swallowed).
    """
    if not frappe.db.exists("DocType", "Material Request"):
        return
    if not frappe.db.exists("DocType", "Variation Order"):
        return

    stored_col = "custom_variation_order_active"

    # Existence check that never relies on the (possible stale) has_column cache.
    exists = frappe.db.sql(
        "SHOW COLUMNS FROM `tabMaterial Request` LIKE %(col)s", {"col": stored_col}
    )
    if not exists:
        try:
            frappe.db.sql(
                f"ALTER TABLE `tabMaterial Request` "
                f"ADD COLUMN `{stored_col}` VARCHAR(140) "
                f"AS (CASE WHEN docstatus < 2 THEN `custom_variation_order` ELSE NULL END) "
                f"STORED"
            )
        except Exception as e:
            # "Duplicate column" is benign (a concurrent run added it); anything
            # else must be surfaced loudly.
            if "Duplicate column" not in str(e):
                frappe.logger("construction_install").error(
                    f"Failed to add generated column '{stored_col}' on 'tabMaterial Request': {e}"
                )
                return

    # Deduplicate any pre-existing conflicts before enforcing the unique index,
    # otherwise index creation fails on an already-populated site.
    try:
        dups = frappe.db.sql(
            f"""
            SELECT `{stored_col}`, COUNT(*) AS c
            FROM `tabMaterial Request`
            WHERE `{stored_col}` IS NOT NULL
            GROUP BY `{stored_col}`
            HAVING COUNT(*) > 1
            """,
            as_dict=True,
        )
        for dup in dups:
            vo_name = dup[stored_col]
            keep = frappe.db.sql(
                f"SELECT name FROM `tabMaterial Request` "
                f"WHERE `{stored_col}` = %(vo)s ORDER BY creation ASC LIMIT 1",
                {"vo": vo_name},
                as_dict=True,
            )
            keep_name = keep[0]["name"] if keep else None
            extras = frappe.db.sql(
                f"SELECT name FROM `tabMaterial Request` "
                f"WHERE `{stored_col}` = %(vo)s AND name != %(keep)s",
                {"vo": vo_name, "keep": keep_name},
                as_dict=True,
            )
            for ex in extras:
                frappe.db.sql(
                    f"UPDATE `tabMaterial Request` SET `{stored_col}` = NULL WHERE name = %(name)s",
                    {"name": ex["name"]},
                )
            frappe.logger("construction_install").warning(
                f"Deduplicated {len(extras)} extra active Material Request(s) for Variation Order "
                f"'{vo_name}' (kept '{keep_name}') to satisfy the one-active-MR-per-VO invariant."
            )
    except Exception as e:
        frappe.logger("construction_install").error(
            f"Failed to deduplicate active Material Requests for '{stored_col}': {e}"
        )

    try:
        frappe.db.sql("ALTER TABLE `tabMaterial Request` DROP INDEX `uniq_mr_one_active_vo`")
    except Exception:
        pass  # index may not exist yet
    try:
        frappe.db.sql(
            "CREATE UNIQUE INDEX `uniq_mr_one_active_vo` "
            "ON `tabMaterial Request` (`custom_variation_order_active`)"
        )
    except Exception as e:
        frappe.logger("construction_install").error(
            f"Failed to enforce unique index 'uniq_mr_one_active_vo' on 'tabMaterial Request': {e}"
        )


# ---------------------------------------------------------------------------
# Workspace Sidebar Reconciler (v16+)
# ---------------------------------------------------------------------------


def setup_workspace_sidebar():
    """Reconcile the Construction workspace sidebar to the desired state.

    Uses a reconciler pattern: always rebuilds the items child table to
    guarantee correct state, regardless of what currently exists in the DB.

    Loads configuration from fixtures/workspace_sidebar_items.json so that
    navigation structure changes don't require code deployments.

    Called by after_migrate hook. Does NOT call frappe.db.commit() —
    Frappe's migration runner manages the transaction boundary.

    Skips gracefully on Frappe versions that don't have Workspace Sidebar
    (v15 and earlier).
    """
    # Feature detection: skip if Workspace Sidebar doesn't exist (v15)
    if not frappe.db.table_exists("Workspace Sidebar"):
        return

    # Load configuration from JSON fixture
    config_path = os.path.join(frappe.get_app_path("construction"), "config", "workspace_sidebar_items.json")
    if not os.path.exists(config_path):
        frappe.log_error(
            f"Workspace sidebar config not found: {config_path}",
            "Construction Setup",
        )
        return

    with open(config_path) as f:
        config = json.load(f)

    # Get or create the sidebar record
    # ignore_permissions is required because after_migrate runs as Administrator
    # but Workspace Sidebar may have restrictive permissions on custom apps
    if frappe.db.exists("Workspace Sidebar", config["title"]):
        sidebar = frappe.get_doc("Workspace Sidebar", config["title"])
    else:
        sidebar = frappe.new_doc("Workspace Sidebar")

    # Reconcile top-level fields
    sidebar.title = config["title"]
    sidebar.module = config["module"]
    sidebar.app = config["app"]
    sidebar.header_icon = config["header_icon"]
    sidebar.standard = 0  # standard=0 for custom apps to allow uninstallation

    # Reconcile items: clear and rebuild to guarantee correct state
    sidebar.items = []
    for item_data in config.get("items", []):
        sidebar.append("items", item_data)

    sidebar.save(ignore_permissions=True)

    # Invalidate workspace-related caches
    _invalidate_workspace_caches()


def _invalidate_workspace_caches():
    """Clear workspace and sidebar caches after reconciliation.

    Frappe aggressively caches workspace sidebars and desktop metadata.
    Without explicit invalidation, changes may not be visible until
    server restart.
    """
    try:
        frappe.cache().delete_key("workspace_sidebar")
        frappe.cache().delete_key("desktop_icons")
        # Clear user-specific bootinfo cache for all enabled users
        for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
            frappe.cache().hdel("bootinfo", user)
    except Exception:
        # Cache clearing is best-effort; don't fail the migration
        pass


# ---------------------------------------------------------------------------
# Item Construction Custom Fields (Idempotent)
# ---------------------------------------------------------------------------


def setup_item_construction_fields():
    """Idempotently add construction custom fields to standard ERPNext Item.

    Called by after_install and after_migrate hooks.
    Does NOT modify core erpnext/item.json.
    """
    if not frappe.db.exists("DocType", "Item"):
        return
    if not frappe.db.exists("DocType", "Custom Field"):
        return

    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        return

    fields = [
        {
            "fieldname": "item_name_ar",
            "fieldtype": "Data",
            "label": "Item Name (Arabic)",
            "insert_after": "item_name",
            "translatable": 0,
        },
        {
            "fieldname": "is_construction_resource",
            "fieldtype": "Check",
            "label": "Is Construction Resource",
            "insert_after": "item_name_ar",
            "default": "0",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "fieldname": "construction_resource_type",
            "fieldtype": "Select",
            "label": "Construction Resource Type",
            "options": "\nMaterial\nLabor\nPlant\nSubcontract\nOverhead",
            "insert_after": "is_construction_resource",
            "depends_on": "eval:doc.is_construction_resource",
            "in_standard_filter": 1,
        },
        {
            "fieldname": "default_cost_stream",
            "fieldtype": "Select",
            "label": "Default Cost Stream",
            "options": "\nM\nL\nP\nS\nO",
            "insert_after": "construction_resource_type",
            "depends_on": "eval:doc.is_construction_resource",
            "in_standard_filter": 1,
        },
        {
            "fieldname": "default_wastage_pct",
            "fieldtype": "Percent",
            "label": "Default Wastage %",
            "insert_after": "default_cost_stream",
            "depends_on": "eval:doc.is_construction_resource",
        },
        {
            "fieldname": "default_productivity_qty_per_day",
            "fieldtype": "Float",
            "label": "Default Productivity Qty/Day",
            "insert_after": "default_wastage_pct",
            "depends_on": "eval:doc.is_construction_resource",
        },
        {
            "fieldname": "labor_trade_designation",
            "fieldtype": "Link",
            "label": "Labor Trade Designation",
            "options": "Designation",
            "insert_after": "default_productivity_qty_per_day",
            "depends_on": "eval:doc.is_construction_resource",
        },
        {
            "fieldname": "linked_asset",
            "fieldtype": "Link",
            "label": "Linked Asset",
            "options": "Asset",
            "insert_after": "labor_trade_designation",
            "depends_on": "eval:doc.is_construction_resource",
        },
    ]

    for field_def in fields:
        fieldname = field_def["fieldname"]
        custom_field_name = frappe.db.get_value(
            "Custom Field", {"dt": "Item", "fieldname": fieldname}, "name"
        )

        if custom_field_name:
            _update_item_construction_custom_field(custom_field_name, field_def)
        else:
            try:
                create_custom_field("Item", field_def, ignore_validate=True)
            except Exception:
                frappe.log_error(
                    f"Failed to create custom field {fieldname} on Item",
                    "Setup Item Construction Fields",
                )

    frappe.clear_cache(doctype="Item")


def _update_item_construction_custom_field(custom_field_name, field_def):
    try:
        doc = frappe.get_doc("Custom Field", custom_field_name)
        changed = False
        for key in (
            "label",
            "fieldtype",
            "options",
            "depends_on",
            "description",
            "default",
            "in_list_view",
            "in_standard_filter",
        ):
            if key in field_def and doc.get(key) != field_def[key]:
                doc.set(key, field_def[key])
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(
            f"Failed to update Item custom field {custom_field_name}",
            "Setup Item Construction Fields",
        )


# ---------------------------------------------------------------------------
# Post-Migrate Health Check
# ---------------------------------------------------------------------------


def setup_construction_workspace_page():
    """Reconcile the Construction workspace page and sidebar.

    The Workspace document controls the main Construction home page. The
    Workspace Sidebar document controls the left navigation. Both must be
    reconciled from source files so cloud deployments do not depend on local
    database edits.
    """
    workspace_path = os.path.join(
        frappe.get_app_path("construction"), "workspace", "construction", "construction.json"
    )
    if os.path.exists(workspace_path):
        with open(workspace_path) as f:
            workspace_data = json.load(f)

        if frappe.db.exists("Workspace", "Construction"):
            workspace = frappe.get_doc("Workspace", "Construction")
            for fieldname in (
                "label",
                "title",
                "module",
                "icon",
                "public",
                "is_hidden",
                "content",
                "parent_page",
            ):
                if fieldname in workspace_data:
                    workspace.set(fieldname, workspace_data[fieldname])
            for child_table in (
                "links",
                "shortcuts",
                "charts",
                "number_cards",
                "quick_lists",
                "custom_blocks",
            ):
                if child_table in workspace_data:
                    workspace.set(child_table, [])
                    for row in workspace_data.get(child_table) or []:
                        workspace.append(child_table, row)
        else:
            workspace = frappe.get_doc(workspace_data)

        workspace.save(ignore_permissions=True)

    if frappe.db.table_exists("Workspace Sidebar"):
        setup_workspace_sidebar()


def verify_workspace_visibility():
    """Post-migrate health check for workspace visibility.

    Logs errors if the Construction workspace is not properly configured.
    Does NOT raise exceptions — migration should not fail due to a
    visibility check.

    Skips gracefully on Frappe versions without Workspace Sidebar.
    """
    errors = []

    # Check Workspace record exists
    if not frappe.db.exists("Workspace", "Construction"):
        errors.append("Workspace 'Construction' missing from tabWorkspace")
    else:
        try:
            # Get available columns - Workspace schema varies by Frappe version
            ws = frappe.db.get_value(
                "Workspace",
                "Construction",
                ["public", "is_hidden", "module"],
                as_dict=True,
            )
            if not ws.get("public"):
                errors.append("Workspace 'Construction' is not public")
            if ws.get("is_hidden"):
                errors.append("Workspace 'Construction' is hidden")
        except Exception as e:
            # Column may not exist in this Frappe version
            pass

    # Check Workspace Sidebar (v16+)
    if frappe.db.table_exists("Workspace Sidebar"):
        if not frappe.db.exists("Workspace Sidebar", "Construction"):
            errors.append("Workspace Sidebar 'Construction' missing")
        else:
            item_count = frappe.db.count(
                "Workspace Sidebar Item",
                filters={"parent": "Construction"},
            )
            if item_count == 0:
                errors.append("Workspace Sidebar 'Construction' has no items")

    # Check add_to_apps_screen hook
    apps_screen = frappe.get_hooks("add_to_apps_screen") or []
    has_construction = any(app.get("name") == "construction" for app in apps_screen if isinstance(app, dict))
    if not has_construction:
        errors.append("add_to_apps_screen missing 'construction' entry in hooks.py")

    if errors:
        frappe.log_error(
            "Workspace Visibility Health Check Failed:\n" + "\n".join(f"  - {e}" for e in errors),
            "Construction Workspace Health Check",
        )
    else:
        frappe.logger().info("Construction workspace health check: PASSED")


# Roles referenced by DocType permissions across the app (source of truth:
# doctype JSON perm blocks). These MUST exist in the database for permission
# assignment to work. Note: "Project Manager" here is the app's role defined
# by the DocType JSONs and is distinct from ERPNext's standard
# "Projects Manager" role.
CONSTRUCTION_ROLES = (
    ("Construction Owner", "Owns construction data; full rights on BOQ Cost Analysis and cost data."),
    ("Project Manager", "Manages projects; can create/submit analyses and certify stages."),
    ("Site Engineer", "Field execution role; read-only access to cost data."),
)


def seed_construction_roles():
    """Create app roles if missing. Idempotent — safe on every migrate."""
    created = []
    for role_name, description in CONSTRUCTION_ROLES:
        if frappe.db.exists("Role", {"role_name": role_name}):
            continue
        doc = frappe.new_doc("Role")
        doc.role_name = role_name
        doc.description = description
        doc.desk_access = 1
        doc.insert(ignore_permissions=True)
        created.append(role_name)

    if created:
        frappe.db.commit()
        frappe.logger().info(f"Construction roles seeded: {', '.join(created)}")
    return created
