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
    page_length: "int | float | str | None" = 20,
    search_fields: "list | str | None" = None,
    display_format: "str | None" = None,
    # Frappe's search_widget passes these additional kwargs — absorb them
    searchfield: "str | None" = None,
    start: "int | float | str | None" = 0,
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

    # --- Resolve requested fields once against live metadata ---
    # Stage 1A: a missing optional field (e.g. account_name_ar before Stage 1B)
    # must never turn a valid search into a silent empty result. The same
    # effective list drives OR conditions, SELECT projection, and labels, so
    # behavior cannot depend on how the framework handles unknown fields.
    meta = frappe.get_meta(doctype)
    effective_fields = [f for f in search_fields if f == "name" or meta.has_field(f)]

    # --- Stage 3: bilingual registry union (code + English + Arabic) ---
    # Mapped doctypes get their registry search fields added once, resolved
    # against live metadata; the single get_list below stays the only query.
    # Fail-closed: a registry/schema ValidationError must PROPAGATE (only an
    # import problem degrades silently).
    ar_field = None
    norm_field = None
    try:
        from construction.services.bilingual_service import AR_NORM_FIELD, get_mapping

        mapping = get_mapping(doctype)
    except ImportError:
        mapping = None
    if mapping and (mapping.get("search") or {}).get("enabled"):
        resolved = mapping.get("resolved") or {}
        for field in (mapping.get("search") or {}).get("fields") or []:
            if field and field != "name" and field not in effective_fields and meta.has_field(field):
                effective_fields.append(field)
        ar_field = resolved.get("arabic_field")
        if ar_field and meta.has_field(AR_NORM_FIELD):
            norm_field = AR_NORM_FIELD

    # --- Build OR search filters ---
    or_filters = []
    search_txt = txt.strip() if txt else ""

    if search_txt:
        for field in effective_fields:
            if field != "name":
                or_filters.append([field, "like", f"%{search_txt}%"])
        # Always include name field
        or_filters.append(["name", "like", f"%{search_txt}%"])
        if norm_field:
            # Server-authoritative Arabic normalization: the maintained
            # normalized search key is matched with the normalized query
            # text (Alef variants / tatweel / diacritics insensitive).
            from construction.services.bilingual_service import normalize_arabic

            or_filters.append([norm_field, "like", "%" + normalize_arabic(search_txt) + "%"])

    try:
        from construction.services.bilingual_service import _coerce_int

        search_txt = txt.strip() if txt else ""
        # Lower-bound client pagination inputs with the SAME strict-integer
        # semantics as the service (shared helper): non-integer values
        # raise frappe.ValidationError on both paths.
        page_length = min(max(_coerce_int(page_length, 1), 1), 200)  # MAX_PAGE_LENGTH parity
        start_i = max(_coerce_int(start, 0), 0)
        stop_i = start_i + page_length
        if not search_txt:
            # Blank query: plain bounded DB pagination — no ranking work;
            # page_length is clamped against unbounded client input.
            results = frappe.get_list(
                doctype,
                filters=filters,
                fields=["name"] + [f for f in effective_fields if f != "name"],
                limit_page_length=page_length,
                limit_start=start_i,
                order_by="modified desc",
            )
        else:
            from construction.services.bilingual_service import RANK_WINDOW

            # Bounded ranking window with a 5,001st-row probe: one extra
            # row is requested so an EXACTLY-full window is NOT flagged
            # (probe rows are dropped before ranking), and real overflow
            # is detected — then made LOUD (no silent truncation).
            results = frappe.get_list(
                doctype,
                filters=filters,
                or_filters=or_filters if or_filters else None,
                fields=["name"] + [f for f in effective_fields if f != "name"],
                limit_page_length=RANK_WINDOW + 1,
                limit_start=0,
                order_by="modified desc",
            )
            if len(results) > RANK_WINDOW:
                frappe.throw(
                    _("Search matches exceed the supported ranking window ({0}); refine the query").format(
                        RANK_WINDOW
                    ),
                    frappe.ValidationError,
                )
            results = results[:RANK_WINDOW]

        if search_txt:
            from construction.services.bilingual_registry import relevance_rank

        formatted_results = []
        is_ar = str(frappe.local.lang or "").lower().startswith("ar")
        for doc in results:
            label = _format_label(doc, display_format, effective_fields)
            # Arabic sessions prefer the Arabic display name when present
            # (fallback chain: Arabic -> English -> identity is handled by
            # the format itself otherwise).
            if is_ar and ar_field and doc.get(ar_field):
                label = str(doc.get(ar_field))
            formatted_results.append(
                {
                    "value": doc.name,
                    "label": label,
                    "description": doc.get("description", ""),
                    "_rank": (
                        relevance_rank(
                            [doc.get("name")] + [doc.get(f, "") for f in effective_fields if f != "name"],
                            search_txt,
                        )
                        if search_txt
                        else 3
                    ),
                }
            )

        if search_txt:
            formatted_results.sort(key=lambda r: (r["_rank"], r["value"]))
        for r in formatted_results:
            r.pop("_rank", None)

        # Ranked pagination over the bounded ranked window.
        return formatted_results[start_i:stop_i]

    except frappe.PermissionError:
        return []
    except frappe.ValidationError:
        # Fail-closed contract violations (registry/schema governance) must
        # surface, never degrade into a silently empty result.
        raise
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
