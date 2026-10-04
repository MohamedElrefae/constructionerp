"""Tier 4 bilingual dispatch for the standard desk Link search endpoint.

Work item: `bilingual-desk-link-dispatch` (SCOPE.md decisions A1-A6).

The stock desk Link control posts to ``frappe.desk.search.search_link``
(`frappe/public/js/frappe/form/controls/link.js:474`), which is rebound to
:func:`search_link` through ``override_whitelisted_methods`` so that the vendor
endpoint keeps owning the English/permission/title-field behaviour while the
Arabic half of a bilingual search is resolved through the registry.

Two dispatch shapes:

* **Latin / unregistered / custom-query** - the vendor result object is
  returned unchanged (literal passthrough, decision A3.2-A3.3).
* **Arabic on a registered doctype (A6)** - the registry half runs *alone*
  over a query plan that folds the stock endpoint's own search fields and
  its ``enabled``/``disabled`` constraints into the single permission-aware
  ``frappe.get_list``. The vendor baseline is skipped because paying for it
  *and* the registry half cannot fit the Two-Tier SLA's universal 1.50 ms
  ceiling (measured: 1.789 ms on Company, 2.505 ms on UOM with the A3 shape;
  0.878 ms with A6). The plan falls back to the A3 merge whenever the vendor
  must keep owning the query: a client ``searchfield``, ``query``,
  ``ignore_user_permissions``, or filters the registry half cannot apply
  faithfully (list-shaped or unparseable JSON).

Dormant defects this design makes unreachable rather than fixed in vendor code:

* D4a - ``search_widget`` re-binds *kwargs only*, so a custom query must expose
  the canonical positional order. :func:`dispatcher` does.
* D4b - ``build_for_autosuggest`` indexes tuples, never dict rows.
  :func:`as_autosuggest_rows` converts at the single integration boundary for
  both the master and the transactional sidecar producer.
"""

from __future__ import annotations

import json
import re

import frappe
from frappe.desk.search import (
    build_for_autosuggest,
    get_std_fields_list,
    search_link as _vendor_search_link,
)

from construction.services.bilingual_registry import default_registry_path, load_registry

_ARABIC_RE = re.compile(
    "[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufbff\ufe70-\ufeff]"
)


def contains_arabic(txt):
    """True when the query text carries Arabic-script characters."""
    return isinstance(txt, str) and bool(_ARABIC_RE.search(txt))


def _registry_data():
    """Request-scoped, signature-checked registry read.

    Mirrors ``bilingual_service.get_registry``: the JSON is parsed once per
    request instead of once per query (about 0.16 ms per parse, material for
    the A6 SLA headroom), re-read when the file's mtime/size signature changes,
    and re-validated fail-closed. The cache is keyed by the loader function
    object itself, so a patched loader (the fail-closed tests) is always
    consulted rather than served from a stale entry.
    """
    import os

    sig = None
    try:
        st = os.stat(default_registry_path())
        sig = (st.st_mtime_ns, st.st_size, str(default_registry_path()))
    except OSError:
        pass
    cache = getattr(frappe.local, "ct_desk_link_registry_cache", None)
    if cache and cache.get("loader") is load_registry and cache.get("sig") == sig:
        return cache.get("data")
    data, errors = load_registry()
    data = data if not errors and isinstance(data, dict) else None
    frappe.local.ct_desk_link_registry_cache = {
        "loader": load_registry,
        "sig": sig,
        "data": data,
    }
    return data


def active_registry_entry(doctype):
    """Return the registry entry for `doctype`, else None (fail-closed)."""
    if not isinstance(doctype, str) or not doctype:
        return None
    data = _registry_data()
    if data is None:
        return None
    entry = (data.get("doctypes") or {}).get(doctype)
    if not isinstance(entry, dict) or entry.get("state") != "active":
        return None
    return entry


def as_autosuggest_rows(rows):
    """Convert dict-shaped search rows into the tuple rows build_for_autosuggest takes."""
    converted = []
    for row in rows or []:
        if isinstance(row, dict):
            value = row.get("value")
            label = row.get("label")
            description = row.get("description")
            converted.append(
                (
                    str(value) if value is not None else "",
                    str(label) if label not in (None, "") else str(value or ""),
                    str(description) if description is not None else "",
                )
            )
        else:
            converted.append(tuple(row))
    return converted


def vendor_search_fields(doctype):
    """Superset of the fields the stock endpoint can match a query against.

    Mirrors both vendor shapes: the SQL ``or_filters`` built at
    `frappe/desk/search.py:169-179` (``name`` + title field + search fields)
    and the Python-side regex over the standard field list used for a
    translated doctype (`frappe/desk/search.py:321-336`, 227-236). Folding
    this list into the registry query is what lets A6 skip the vendor baseline
    without losing a row the stock endpoint would have returned.
    """
    meta = frappe.get_meta(doctype)
    names = ["name"]
    if meta.title_field:
        names.append(str(meta.title_field).strip())
    names.extend(str(field).strip() for field in get_std_fields_list(meta, "name"))
    if meta.search_fields:
        names.extend(part.strip() for part in str(meta.search_fields).split(","))
    fields = []
    for name in names:
        if name and name not in fields and (name == "name" or meta.has_field(name)):
            fields.append(name)
    return fields


def normalize_client_filters(filters):
    """Return ``(filters_dict, usable)`` for the registry half.

    ``usable`` is False when the registry half cannot apply the filters the way
    the stock endpoint would (list-shaped filter tuples, invalid JSON, anything
    that is not a mapping) - those queries must stay on the vendor path.
    """
    if filters is None or filters == "":
        return {}, True
    if isinstance(filters, dict):
        return dict(filters), True
    if isinstance(filters, str):
        try:
            parsed = json.loads(filters)
        except (TypeError, ValueError):
            return {}, False
        if isinstance(parsed, dict):
            return dict(parsed), True
        return {}, False
    return {}, False


def _field_list(value):
    """Client ``search_fields`` accepted as a list or a single field name."""
    if not value:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except (TypeError, ValueError):
                return [stripped]
            return [str(f) for f in parsed] if isinstance(parsed, list) else [stripped]
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple)):
        return [str(f) for f in value]
    return [str(value)]


def arabic_plan(doctype, filters, searchfield, ignore_user_permissions):
    """A6 query plan: one permission-aware query carrying the vendor's semantics.

    Returns the filter mapping the registry half should run, or None when the
    vendor path must keep owning the query (documented A3 fallback):
    an explicit ``searchfield``, ``ignore_user_permissions`` (its validation is
    the vendor's job per A4), or filters the registry half cannot apply
    faithfully.
    """
    if searchfield or ignore_user_permissions:
        return None
    client, usable = normalize_client_filters(filters)
    if not usable:
        return None
    meta = frappe.get_meta(doctype)
    if client.pop("include_disabled", None) in (1, True, "1"):
        include_disabled = True
    else:
        include_disabled = False
    if not include_disabled:
        if meta.has_field("enabled"):
            client.setdefault("enabled", 1)
        if meta.has_field("disabled"):
            client.setdefault("disabled", ["!=", 1])
    fields = vendor_search_fields(doctype)
    for extra in _field_list(client.pop("search_fields", None)):
        if (extra == "name" or meta.has_field(extra)) and extra not in fields:
            fields.append(extra)
    client["search_fields"] = fields
    if not client.get("display_format") and meta.title_field and meta.has_field(meta.title_field):
        client["display_format"] = "{" + meta.title_field + "}"
    return client


def dispatcher(
    doctype,
    txt,
    searchfield,
    start,
    page_length,
    filters,
    *,
    as_dict=False,
    reference_doctype=None,
    ignore_user_permissions=None,
    link_fieldname=None,
):
    """Bilingual search rows in the canonical ``search_widget`` positional order.

    D4a-proof: the first six slots are exactly the positional arguments
    ``frappe/desk/search.py:115-124`` sends, and every downstream call is made by
    keyword. Returns tuples so the vendor ``build_for_autosuggest`` accepts them
    (D4b).
    """
    from construction.searchable_dropdown.api.search import searchable_link_search

    client_filters = dict(filters) if isinstance(filters, dict) else {}
    search_fields = client_filters.get("search_fields")
    display_format = client_filters.get("display_format")
    rows = searchable_link_search(
        doctype=doctype,
        txt=txt or "",
        filters=client_filters,
        page_length=page_length,
        search_fields=search_fields,
        display_format=display_format,
        searchfield=searchfield,
        start=start,
        link_fieldname=link_fieldname,
        reference_doctype=reference_doctype,
        ignore_user_permissions=(
            None if ignore_user_permissions is None else int(bool(ignore_user_permissions))
        ),
    )
    return as_autosuggest_rows(rows)


def merge_results(baseline, extra, page_length):
    """Vendor rows first, Arabic rows appended, de-duplicated by value, capped."""
    merged = list(baseline or [])
    seen = {row.get("value") for row in merged if isinstance(row, dict)}
    for row in extra or []:
        if not isinstance(row, dict):
            continue
        value = row.get("value")
        if value in seen:
            continue
        seen.add(value)
        merged.append(row)
    try:
        limit = int(page_length)
    except (TypeError, ValueError):
        limit = 0
    return merged[:limit] if limit > 0 else merged


@frappe.whitelist()
def search_link(
    doctype: str,
    txt: str,
    query: "str | None" = None,
    filters: "str | dict | list | None" = None,
    page_length: int = 10,
    searchfield: "str | None" = None,
    reference_doctype: "str | None" = None,
    ignore_user_permissions: bool = False,
    *,
    link_fieldname: "str | None" = None,
):
    """Bilingual entry point bound over ``frappe.desk.search.search_link``.

    Passthrough conditions are evaluated in the cheapest order first, so a
    Latin query costs one regex and never touches the registry file: the
    non-bilingual path returns the vendor result object unchanged. An Arabic
    query on a registered doctype runs the A6 plan (registry half only, vendor
    fields folded in) and only falls back to the A3 vendor+merge shape when the
    vendor has to own the query.
    """
    passthrough = dict(
        query=query,
        filters=filters,
        page_length=page_length,
        searchfield=searchfield,
        reference_doctype=reference_doctype,
        ignore_user_permissions=ignore_user_permissions,
        link_fieldname=link_fieldname,
    )
    if query or not contains_arabic(txt):
        return _vendor_search_link(doctype, txt, **passthrough)
    if active_registry_entry(doctype) is None:
        return _vendor_search_link(doctype, txt, **passthrough)

    plan = arabic_plan(doctype, filters, searchfield, ignore_user_permissions)
    if plan is None:
        baseline = _vendor_search_link(doctype, txt, **passthrough)
        client, usable = normalize_client_filters(filters)
        if searchfield or not usable:
            return baseline
        rows = dispatcher(
            doctype,
            txt,
            searchfield,
            0,
            page_length,
            client,
            reference_doctype=reference_doctype,
            ignore_user_permissions=ignore_user_permissions,
            link_fieldname=link_fieldname,
        )
        return merge_results(baseline, build_for_autosuggest(rows, doctype=doctype), page_length)

    rows = dispatcher(
        doctype,
        txt,
        searchfield,
        0,
        page_length,
        plan,
        reference_doctype=reference_doctype,
        ignore_user_permissions=ignore_user_permissions,
        link_fieldname=link_fieldname,
    )
    return build_for_autosuggest(rows, doctype=doctype)
