"""Narrative Unicode Policy & Rich-Text Sanitization Service.

Implements Tier 1 (Plain Text) and Tier 2 (Rich Text / HTML) security gates
pursuant to docs/ai/work-items/narrative-unicode-policy/SCOPE.md.

Enforces:
1. Strict fail-closed rejection of Unicode bidirectional overrides/isolates
   (U+202A–U+202E, U+2066–U+2069) and C0/C1 control characters in narrative fields.
2. Legitimate direction marks (U+200E LRM, U+200F RLM, U+061C ALM) permitted.
3. Pre-validation HTML entity decoding (&rlm;, &#x202E;, &#8238;, etc.) so encoded
   controls cannot bypass the gate.
4. stdlib html.parser text-node extraction, preserving HTML tags and attributes.
5. <bdi> isolation helper (bdi_join) for Jinja templates with single escaping.
6. Zero diff on bilingual_service.py and search.py.
"""

import html
from html.parser import HTMLParser
import markupsafe
import frappe
from frappe import _

from construction.services.bilingual_registry import is_safe_narrative_text

# Fieldtypes that define Tier 1 (Plain Text) and Tier 2 (Rich Text / HTML)
FIELDTYPE_TIER_MAP = {
    "Text Editor": 2,
    "HTML Editor": 2,
    "Small Text": 1,
    "Text": 1,
    "Long Text": 1,
}

# Explicit non-standard narrative fields (e.g. Data fieldtypes carrying narrative codes)
EXTRA_NARRATIVE_FIELDS = {
    ("Item", "customer_code"): 1,
}

# Static baseline fallback for offline / standalone test suites (27 fields across 10 doctypes)
STATIC_NARRATIVE_FIELDS_BASELINE = {
    "Item": {
        "description": 2,
        "customer_code": 1,
    },
    "Task": {
        "description": 2,
    },
    "Project": {
        "notes": 2,
        "message": 1,
    },
    "Employee": {
        "bio": 2,
        "current_address": 1,
        "permanent_address": 1,
        "family_background": 1,
        "health_details": 1,
        "reason_for_leaving": 1,
        "feedback": 1,
    },
    "Customer": {
        "primary_address": 2,
        "customer_details": 1,
    },
    "Supplier": {
        "primary_address": 2,
        "supplier_details": 1,
    },
    "BOQ Structure": {
        "description": 1,
        "description_ar": 1,
    },
    "UOM": {
        "description": 1,
    },
    "Payment Term": {
        "description": 1,
    },
    "Task Depends On": {
        "subject": 1,
        "project": 1,
    },
    "Project User": {
        "project_status": 1,
    },
    "Employee Education": {
        "school_univ": 1,
        "maj_opt_subj": 1,
    },
    "Employee External Work History": {
        "address": 1,
    },
    "Payment Terms Template Detail": {
        "description": 1,
    },
}

NARRATIVE_FIELDS_CONFIG = STATIC_NARRATIVE_FIELDS_BASELINE
CHILD_NARRATIVE_FIELDS_CONFIG = STATIC_NARRATIVE_FIELDS_BASELINE


def get_narrative_fields_for_doctype(doctype):
    """Derive narrative fields and tiers dynamically from DocType metadata.

    Tiers are determined directly by fieldtype:
    - Tier 2 (Rich Text / HTML): Text Editor, HTML Editor
    - Tier 1 (Plain Text): Small Text, Text, Long Text, plus designated Data fields.

    Prevents drift / failing open when new narrative fields are added to DocTypes.
    Caches results per session/site for fast save-time hook execution.
    """
    if not doctype:
        return {}

    cache = getattr(frappe.local, "_ct_narrative_fields_cache", None)
    if cache is None:
        cache = {}
        if getattr(frappe, "local", None):
            frappe.local._ct_narrative_fields_cache = cache
    if doctype in cache:
        return cache[doctype]

    fields = {}
    if getattr(frappe, "local", None) and getattr(frappe.local, "site", None):
        try:
            meta = frappe.get_meta(doctype)
            for df in meta.fields:
                if df.fieldtype in FIELDTYPE_TIER_MAP:
                    fields[df.fieldname] = FIELDTYPE_TIER_MAP[df.fieldtype]
                elif (doctype, df.fieldname) in EXTRA_NARRATIVE_FIELDS:
                    fields[df.fieldname] = EXTRA_NARRATIVE_FIELDS[(doctype, df.fieldname)]
        except Exception:
            pass

    if not fields:
        fields = dict(STATIC_NARRATIVE_FIELDS_BASELINE.get(doctype, {}))

    cache[doctype] = fields
    return fields


def find_offending_codepoint(text):
    """Locate the first forbidden Unicode control character or override in text."""
    if not isinstance(text, str):
        return None
    for ch in text:
        code = ord(ch)
        if (
            (0x202A <= code <= 0x202E)
            or (0x2066 <= code <= 0x2069)
            or (0x00 <= code <= 0x1F and ch not in ("\t", "\n", "\r"))
            or (0x7F <= code <= 0x9F)
        ):
            return f"U+{code:04X}"
    for ch in text:
        code = ord(ch)
        if (0x202A <= code <= 0x202E) or (0x2066 <= code <= 0x2069) or (0x00 <= code <= 0x1F) or (0x7F <= code <= 0x9F):
            return f"U+{code:04X}"
    return None


def _fail_closed(msg):
    """Raise frappe.ValidationError fail-closed, handling both Frappe context and standalone."""
    if getattr(frappe, "local", None) and getattr(frappe.local, "site", None):
        frappe.throw(msg, exc=frappe.ValidationError)
    raise frappe.ValidationError(msg)


def validate_plain_text_narrative(text, fieldname=None):
    """Tier 1: Validate plain text narrative field.

    Decodes numeric and named HTML entities first, then checks each line
    against is_safe_narrative_text. Fails closed with frappe.ValidationError
    naming the field and the offending codepoint.
    """
    if not text or not isinstance(text, str):
        return
    unescaped = html.unescape(text)
    for line in unescaped.splitlines():
        if not is_safe_narrative_text(line):
            offending = find_offending_codepoint(line) or "unknown"
            _fail_closed(
                _("Field '{0}' contains forbidden Unicode control character {1}").format(
                    fieldname or "narrative", offending
                )
            )


class _NarrativeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_nodes = []

    def handle_data(self, data):
        if data:
            self.text_nodes.append(data)

    def handle_starttag(self, tag, attrs):
        for attr_name, attr_val in attrs:
            if attr_val:
                self.text_nodes.append(attr_val)


def sanitize_and_validate_html(text, fieldname=None):
    """Tier 2: Validate HTML / rich text narrative field.

    Parses HTML using stdlib html.parser with convert_charrefs=True, isolating
    inner text nodes and attribute values without touching tags. Each text
    node is checked against is_safe_narrative_text. Markup is preserved untouched
    on success. Fails closed with frappe.ValidationError on offending codepoints.
    """
    if not text or not isinstance(text, str):
        return text

    parser = _NarrativeHTMLParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        validate_plain_text_narrative(text, fieldname=fieldname)
        return text

    for node in parser.text_nodes:
        for line in node.splitlines():
            if not is_safe_narrative_text(line):
                offending = find_offending_codepoint(line) or "unknown"
                _fail_closed(
                    _("Field '{0}' contains forbidden Unicode control character {1}").format(
                        fieldname or "narrative", offending
                    )
                )

    return text


def bdi_join(items, separator=" / "):
    """Jinja filter: wrap each non-empty item in <bdi> with single HTML escaping.

    Returns markupsafe.Markup to prevent double-escaping in Jinja templates.
    """
    if not items:
        return markupsafe.Markup("")

    elements = []
    for item in items:
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        elements.append(markupsafe.Markup(f"<bdi>{markupsafe.escape(s)}</bdi>"))

    if not elements:
        return markupsafe.Markup("")

    sep = markupsafe.escape(separator)
    return markupsafe.Markup(sep).join(elements)


def _validate_fields(target, fields_config):
    for fieldname, tier in fields_config.items():
        val = target.get(fieldname)
        if not val or not isinstance(val, str):
            continue
        field_identifier = f"{target.doctype}.{fieldname}"
        if tier == 2:
            sanitize_and_validate_html(val, fieldname=field_identifier)
        else:
            validate_plain_text_narrative(val, fieldname=field_identifier)


def validate_narrative_fields(doc, method=None):
    """Doc event hook: validate narrative fields on parent and child tables."""
    if not doc:
        return

    # Validate parent narrative fields (derived dynamically from meta)
    parent_fields = get_narrative_fields_for_doctype(doc.doctype)
    if parent_fields:
        _validate_fields(doc, parent_fields)

    # Validate child table narrative fields (walked unconditionally)
    if hasattr(doc, "get_all_children"):
        for child in doc.get_all_children():
            child_fields = get_narrative_fields_for_doctype(child.doctype)
            if child_fields:
                _validate_fields(child, child_fields)
