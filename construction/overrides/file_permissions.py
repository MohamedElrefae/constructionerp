"""Additional authorization for construction attachments and report exports.

Native File access includes owner/share allowances. Construction attachments
must also satisfy their current parent and selected scope; generated export
ownership alone does not authorize access after scope/row rights change.
Unrelated files continue through native permission checks.
"""

import json
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

import frappe

BOQ_PARENT_DOCTYPES = (
    "BOQ Header",
    "BOQ Item",
    "BOQ Structure",
    "BOQ Item Stage",
    "BOQ Quantity Revision",
    "BOQ Cost Analysis",
    "Variation Order",
    "VO Line",
)


def is_boq_attached(file_doc):
    return bool(file_doc) and file_doc.get("attached_to_doctype") in BOQ_PARENT_DOCTYPES


def is_construction_export(doc):
    """Recognize generated report URLs even if File metadata is renamed."""
    if not doc:
        return False
    names = [
        doc.get("file_name") or "",
        PurePosixPath(unquote(urlsplit(doc.get("file_url") or "").path)).name,
    ]
    return any(name.startswith("F19_") and name.endswith(".json") for name in names)


def _standalone_export_readable(doc, user):
    if user == "Guest" or doc.get("owner") != user or not doc.get("is_private"):
        return False
    try:
        payload = json.loads(doc.get_content())
        company = payload.get("filters", {}).get("company")
        from construction.overrides.boq_permissions import scope_company_allows

        if not company or not frappe.has_permission("Company", "read", doc=company, user=user):
            return False
        if not scope_company_allows(company, user):
            return False
        rows = payload.get("rows")
        if payload.get("report") != "price_history" or not isinstance(rows, list) or len(rows) > 2000:
            return False
        for row in rows:
            name = row.get("name")
            if not name or not frappe.has_permission("Resource Price History", "read", doc=name, user=user):
                return False
            if frappe.db.get_value("Resource Price History", name, "company") != company:
                return False
        return True
    except Exception:
        return False


def has_file_parent_permission(doc, ptype, user=None, **kwargs):
    """Deny unauthorized File access using requested AND stored attachments.

    True delegates to native File rights; it does not grant a role permission.
    Unattached generated exports additionally require owner and live row/scope
    authorization. Ordinary users cannot remove their protection metadata.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    candidates = [doc]
    if not doc.is_new() and doc.name and frappe.db.exists("File", doc.name):
        stored = frappe.get_doc("File", doc.name)
        candidates.append(stored)
        if is_construction_export(stored) and (not is_construction_export(doc) or not doc.get("is_private")):
            return False
    for candidate in candidates:
        if is_construction_export(candidate) and not is_boq_attached(candidate):
            if not _standalone_export_readable(candidate, user):
                return False
            continue
        if not is_boq_attached(candidate):
            continue
        attached_dt = candidate.get("attached_to_doctype")
        attached_dn = candidate.get("attached_to_name")
        if not attached_dn or not frappe.db.exists(attached_dt, attached_dn):
            return False
        parent_type = "write" if ptype in ("write", "delete") else "read"
        if not frappe.has_permission(attached_dt, parent_type, doc=attached_dn, user=user):
            return False
    return True
