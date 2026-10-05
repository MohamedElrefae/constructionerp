"""BOQ children inherit native parent authorization, independently of UI scope.

Returning True only allows Frappe's own child role/User Permission checks to
continue. It never grants permissions. Selected scope keeps its existing list
filter behavior; this module adds the missing document-parent boundary.
"""

import frappe

BOQ_CHILD_DOCTYPES = (
    "BOQ Item",
    "BOQ Structure",
    "BOQ Item Stage",
    "BOQ Quantity Revision",
    "BOQ Cost Analysis",
    "Variation Order",
)
WRITE_TYPES = {"write", "create", "delete", "submit", "cancel", "amend"}


def _headers(doc):
    headers = {doc.get("boq_header")}
    if doc.doctype != "BOQ Item" and doc.get("boq_item"):
        headers.add(frappe.db.get_value("BOQ Item", doc.boq_item, "boq_header"))
    structure = doc.get("structure") or doc.get("boq_structure")
    if structure:
        headers.add(frappe.db.get_value("BOQ Structure", structure, "boq_header"))
    return set(filter(None, headers))


def has_boq_parent_permission(doc, ptype, user=None, **kwargs):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    headers = _headers(doc)
    # A caller cannot move a forbidden existing child into an allowed parent
    # to make the first permission check pass.
    if not doc.is_new():
        stored = frappe.get_doc(doc.doctype, doc.name)
        headers.update(_headers(stored))
    if not headers:
        return doc.doctype == "BOQ Cost Analysis" and bool(doc.get("is_template"))
    parent_type = "write" if ptype in WRITE_TYPES else "read"
    return all(frappe.has_permission("BOQ Header", parent_type, doc=name, user=user) for name in headers)


def boq_parent_query_conditions(user, doctype=None):
    """Use native parent query permissions without materializing all headers."""
    if user == "Administrator" or doctype not in BOQ_CHILD_DOCTYPES:
        return ""
    from frappe.model.db_query import DatabaseQuery

    try:
        match = DatabaseQuery("BOQ Header", user=user).build_match_conditions()
    except frappe.PermissionError:
        return "1=0"
    # The table identifier comes exclusively from the fixed DocType allowlist;
    # match is the framework's escaped role/User Permission/shared predicate.
    parent = f"`tab{doctype}`.`boq_header`"
    condition = f"{parent} IN (SELECT `tabBOQ Header`.`name` FROM `tabBOQ Header`"
    if match:
        condition += " WHERE " + match
    condition += ")"
    if doctype == "BOQ Cost Analysis":
        condition = f"(({condition}) OR ({parent} IS NULL OR {parent} = '') AND `tabBOQ Cost Analysis`.`is_template` = 1)"
    return condition
