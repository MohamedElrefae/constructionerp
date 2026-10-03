"""Transactional link resolution sidecar.

Delivers bilingual search over transactional doctypes (Sales Order, Purchase Invoice, ...)
without modifying the invariant triad ``{bilingual_service.py, search.py,
bilingual_registry.json}``.

Design contract: RFC ``docs/ai/work-items/transactional-link-resolution/RFC.md`` §§3–4.

Two legs:

1. **Master pre-resolution** (Arabic query) — resolve the query against the registered
   master's normalised Arabic column through the existing ranked path, capping the result at
   ``TOP_K_MASTER_MATCHES`` so ranking happens where the language actually is.
2. **Transaction fetch** — delegate to the unmodified ``searchable_link_search`` with
   ``txt=""`` and ``filters={link_field: ("in", ids)}`` so the naming-series columns are
   never matched against Arabic text (RFC §4.2, the ``txt`` correctness trap).

Parameter order mirrors ``frappe.desk.search.search_widget``'s custom-query call::

    frappe.call(query, doctype, txt, searchfield, start, page_length, filters, ...)

which is *not* the order of ``searchable_link_search``'s own signature. Binding to the
caller's order is what makes this endpoint work when driven by the real dropdown rather
than by keyword-invoking tests.
"""

from __future__ import annotations

import re

import frappe
from frappe import _

from construction.searchable_dropdown.api.search import searchable_link_search

__all__ = [
    "search_transactions",
    "TRANSACTION_LINK_CONFIG",
    "TOP_K_MASTER_MATCHES",
    "seed_required_targets",
]

_ARABIC_RE = re.compile(
    "[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

TOP_K_MASTER_MATCHES = 100

# v1 bound (RFC §3.3): exactly one primary party link per target doctype.
# ``filters`` in the delegation path is an AND map, and ``or_filters`` inside
# searchable_link_search is derived from ``txt`` alone, so serving two link
# fields would require an OR the delegation path cannot express.
# ``seed_required`` targets are recorded so a zero-row table can never yield a
# vacuous pass (RFC §7.2).
TRANSACTION_LINK_CONFIG = {
    "Sales Order": {"link_field": "customer", "master_doctype": "Customer"},
    "Sales Invoice": {"link_field": "customer", "master_doctype": "Customer"},
    "Material Request": {"link_field": "customer", "master_doctype": "Customer"},
    "Purchase Order": {
        "link_field": "supplier",
        "master_doctype": "Supplier",
        "seed_required": True,
    },
    "Purchase Invoice": {"link_field": "supplier", "master_doctype": "Supplier"},
    "Purchase Receipt": {"link_field": "supplier", "master_doctype": "Supplier"},
    "Stock Entry": {"link_field": "supplier", "master_doctype": "Supplier"},
}

# Keys the client may not influence: they are structural to the resolution, and a
# client-supplied value colliding on the link field would silently drop the gate.
_META_KEYS = ("doctype", "search_fields", "display_format", "searchfield", "query")


def seed_required_targets() -> list[str]:
    """Targets that must hold rows before their assertions can mean anything."""
    return sorted(k for k, v in TRANSACTION_LINK_CONFIG.items() if v.get("seed_required"))


def _contains_arabic(txt: str) -> bool:
    return bool(txt) and bool(_ARABIC_RE.search(txt))


def _native_search_fields(doctype: str) -> list[str]:
    """Reproduce ``search_widget``'s own field derivation (frappe/desk/search.py).

    Native builds ``["name"] + [title_field] + meta.get_search_fields()``. Mirroring it is
    what makes the Latin path agree with native ``search_link``: without it the delegation
    default is ``search_fields = ["name"]`` and a query like ``Acme`` would match only the
    naming series (RFC §7.1, property 3).
    """
    meta = frappe.get_meta(doctype)
    fields = ["name"]
    if meta.title_field:
        fields.append(meta.title_field)
    if meta.search_fields:
        fields.extend(meta.get_search_fields())
    seen: set[str] = set()
    ordered: list[str] = []
    for field in fields:
        field = (field or "").strip()
        if field and field not in seen:
            seen.add(field)
            ordered.append(field)
    return ordered


def _sanitize_client_filters(raw, link_field: str) -> dict:
    """Drop structural keys and everything the client must not decide (RFC §6).

    The resolved gate is written back *after* sanitisation so no client-supplied
    ``link_field`` can overwrite or remove it.
    """
    if raw is None:
        filters: dict = {}
    elif isinstance(raw, dict):
        filters = dict(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if text.startswith("{"):
            try:
                filters = dict(frappe.parse_json(text))
            except Exception:
                filters = {}
        else:
            filters = {}
    else:
        filters = {}

    for key in list(filters):
        if key in _META_KEYS or key == link_field:
            filters.pop(key, None)
    return filters


def _resolve_master_ids(master_doctype: str, txt: str) -> list[str]:
    """Top-K master IDs for ``txt``, ranked by the existing relevance ranking."""
    matches = searchable_link_search(
        doctype=master_doctype,
        txt=txt,
        filters={},
        search_fields=_native_search_fields(master_doctype),
        page_length=TOP_K_MASTER_MATCHES,
        display_format="{name}",
    )
    return [
        row.get("value")
        for row in (matches or [])[:TOP_K_MASTER_MATCHES]
        if row.get("value")
    ]


def _arabic_label_map(doctype: str, names: list[str]) -> dict[str, str]:
    """``name -> Arabic label`` for the returned rows, using the registry mapping."""
    if not names:
        return {}
    try:
        from construction.services.bilingual_service import get_mapping
    except ImportError:
        return {}

    mapping = get_mapping(doctype)
    if not mapping:
        return {}
    arabic_field = (mapping.get("resolved") or {}).get("arabic_field")
    if not arabic_field:
        return {}

    rows = frappe.get_all(
        doctype,
        filters={"name": ("in", list(names))},
        fields=["name", arabic_field],
    )
    return {
        row["name"]: str(row.get(arabic_field) or "")
        for row in rows
        if row.get(arabic_field)
    }


def _enrich(results: list[dict], target_doctype: str, link_field: str, master_doctype: str) -> list[dict]:
    """Attach the master's Arabic label to each transaction row (§2.4).

    Transaction rows carry no Arabic identity of their own, so the label has to come from
    the master that was resolved.
    """
    if not results:
        return results

    names = [row.get("value") for row in results if row.get("value")]
    if not names:
        return results

    link_values = frappe.get_all(
        target_doctype,
        filters={"name": ("in", names)},
        fields=["name", link_field],
    )
    master_names = {row.get(link_field) for row in link_values if row.get(link_field)}
    if not master_names:
        return results

    labels = _arabic_label_map(master_doctype, list(master_names))
    if not labels:
        return results

    value_to_label = {
        row["name"]: labels.get(row.get(link_field))
        for row in link_values
        if row.get(link_field) in labels
    }
    for row in results:
        arabic = value_to_label.get(row.get("value"))
        if arabic:
            row["description"] = arabic
            row["label"] = f"{row.get('label') or row.get('value')} — {arabic}"
    return results


@frappe.whitelist()
def search_transactions(
    doctype: str,
    txt: str = "",
    searchfield: str | None = None,
    start: "int | float | str | None" = 0,
    page_length: "int | float | str | None" = 20,
    filters=None,
    as_dict: bool = False,
    reference_doctype: str | None = None,
    ignore_user_permissions=None,
    link_fieldname: str | None = None,
    **_ignored,
):
    """Bilingual transactional link search entry point.

    Rejects any target doctype outside :data:`TRANSACTION_LINK_CONFIG`; the allow-list is
    server-authoritative and never trusts the client route (RFC §2.4).
    """
    if not doctype or doctype not in TRANSACTION_LINK_CONFIG:
        return []

    config = TRANSACTION_LINK_CONFIG[doctype]
    link_field = config["link_field"]
    master_doctype = config["master_doctype"]

    meta = frappe.get_meta(doctype)
    if not meta.has_field(link_field):
        raise frappe.ValidationError(
            _("Link field {0} is missing on {1}").format(link_field, doctype)
        )

    search_fields = _native_search_fields(doctype)
    client_filters = _sanitize_client_filters(filters, link_field)
    query = (txt or "").strip()

    if not query:
        return searchable_link_search(
            doctype=doctype,
            txt="",
            filters=client_filters,
            search_fields=search_fields,
            page_length=page_length,
            start=start,
            display_format="{name}",
        )

    if not _contains_arabic(query):
        return searchable_link_search(
            doctype=doctype,
            txt=query,
            filters=client_filters,
            search_fields=search_fields,
            page_length=page_length,
            start=start,
            display_format="{name}",
        )

    resolved_ids = _resolve_master_ids(master_doctype, query)
    if not resolved_ids:
        return []

    gate = {link_field: ("in", resolved_ids)}
    gate.update(client_filters)

    results = searchable_link_search(
        doctype=doctype,
        txt="",
        filters=gate,
        search_fields=search_fields,
        page_length=page_length,
        start=start,
        display_format="{name}",
    )
    return _enrich(results, doctype, link_field, master_doctype)
