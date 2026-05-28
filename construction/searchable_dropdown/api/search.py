"""
Searchable Dropdown API
Enhanced search for Link fields with multi-field search and custom formatting.
"""

import frappe
from frappe import _


@frappe.whitelist()
def searchable_link_search(
    doctype: str,
    txt: str,
    filters: "dict | None" = None,
    page_length: int = 20,
    search_fields: "list | str | None" = None,
    display_format: "str | None" = None,
    # Frappe's search_widget passes these additional kwargs — absorb them
    searchfield: "str | None" = None,
    start: int = 0,
    link_fieldname: "str | None" = None,
    reference_doctype: "str | None" = None,
    query: "str | None" = None,
    ignore_user_permissions: "int | None" = None,
):
    """
    Enhanced search for searchable dropdown wrapper.
    Robust against Frappe v16 GET parameter serialization edge cases:
    - search_fields may arrive as a string (single-element list collapsed by browser)
    - filters may arrive as a JSON string
    - Pydantic v2 strict type validation

    Args:
        doctype: Target DocType (e.g., 'Account')
        txt: Search string
        filters: JSON dict of base filters (may arrive as string — handled)
        page_length: Max results (default 20)
        search_fields: List of fields to search (may arrive as string — handled)
        display_format: Format string, e.g. '{account_code} - {account_name}'

    Returns:
        List of dicts: [{value, label, description}, ...]
    """
    import json

    # --- Robust coercion for search_fields ---
    # When sent as GET params, ["name"] may collapse to just "name"
    if search_fields is None:
        search_fields = ["name"]
    elif isinstance(search_fields, str):
        # Could be a JSON string '["name", "account_name"]' or plain 'name'
        s = search_fields.strip()
        if s.startswith("["):
            try:
                search_fields = json.loads(s)
            except Exception:
                search_fields = [s]
        else:
            search_fields = [s]
    elif not isinstance(search_fields, list):
        search_fields = [str(search_fields)]

    # --- Robust coercion for display_format ---
    if not display_format:
        display_format = "{name}"

    # --- Robust coercion for filters ---
    # May arrive as None, dict, or JSON string
    if filters is None:
        filters = {}
    elif isinstance(filters, str):
        s = filters.strip()
        if s.startswith("{"):
            try:
                filters = json.loads(s)
            except Exception:
                filters = {}
        else:
            # Single non-JSON string — ignore safely
            filters = {}
    elif not isinstance(filters, dict):
        filters = {}

    # Strip out internal keys injected by SearchableDropdownEnhancer
    # (these are meta-keys for our API, not actual DB filters)
    for internal_key in ("doctype", "search_fields", "display_format"):
        filters.pop(internal_key, None)

    # --- Build OR search filters ---
    or_filters = []
    search_txt = txt.strip() if txt else ""

    if search_txt:
        for field in search_fields:
            if field != "name" and frappe.get_meta(doctype).has_field(field):
                or_filters.append([field, "like", f"%{search_txt}%"])
        # Always include name field
        or_filters.append(["name", "like", f"%{search_txt}%"])

    try:
        results = frappe.get_list(
            doctype,
            filters=filters,
            or_filters=or_filters if or_filters else None,
            fields=["name"] + [f for f in search_fields if f != "name"],
            limit_page_length=int(page_length),
            order_by="modified desc",
        )

        formatted_results = []
        for doc in results:
            label = _format_label(doc, display_format, search_fields)
            formatted_results.append(
                {"value": doc.name, "label": label, "description": doc.get("description", "")}
            )

        return formatted_results

    except frappe.PermissionError:
        return []
    except Exception as e:
        frappe.log_error(f"Searchable dropdown search error: {str(e)}")
        return []


def _format_label(doc: dict, display_format: str, search_fields: list) -> str:
    """
    Format label using display_format template.

    Args:
        doc: Document dict with field values
        display_format: Format string with {field_name} placeholders
        search_fields: Available fields for fallback

    Returns:
        Formatted label string
    """
    try:
        # Prepare format kwargs
        format_kwargs = {"name": doc.get("name", "")}

        for field in search_fields:
            format_kwargs[field] = doc.get(field, "")

        # Try to format with available fields
        label = display_format.format(**format_kwargs)

        # If result is empty or just separators, fallback to name
        clean_label = label.replace("-", "").strip()
        if not clean_label:
            return doc.get("name", "")

        return label

    except (KeyError, ValueError):
        # Fallback to name if format fails
        return doc.get("name", "")


@frappe.whitelist()
def get_recent_items(doctype: str, limit: int = 5):
    """
    Get recently used items for a doctype.
    Optional: for empty search state.

    Args:
        doctype: Target DocType
        limit: Number of items to return

    Returns:
        List of recent items
    """
    try:
        results = frappe.get_list(doctype, fields=["name"], limit_page_length=limit, order_by="modified desc")

        return [{"value": d.name, "label": d.name} for d in results]

    except frappe.PermissionError:
        return []
