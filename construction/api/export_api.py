"""
Generic DocType Export API

Provides whitelisted endpoints for exporting any DocType record as Excel or PDF.
Used by the Global Export Menu (generic_export_menu.js) that auto-attaches to
every Frappe form page.

Endpoints
---------
export_doctype_excel(doctype, docname, column_config=None)
export_doctype_pdf(doctype, docname, column_config=None)
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import format_date, format_datetime, flt, cint, strip_html
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx


# ── Non-exportable fieldtypes ────────────────────────────────────────────────
NON_EXPORTABLE_FIELDTYPES = {
    "Section Break", "Column Break", "Tab Break",
    "Table", "Table MultiSelect",
    "HTML", "HTML Editor",
    "Button", "Attach", "Attach Image",
    "Signature", "Barcode", "Geolocation",
    "Fold", "Heading",
}

# ── System fields hidden by default ─────────────────────────────────────────
SYSTEM_FIELDS_HIDDEN_BY_DEFAULT = {
    "owner", "modified_by", "idx", "parent", "parenttype", "parentfield",
    "docstatus",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Public whitelisted endpoints
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def export_doctype_excel(doctype, docname, column_config=None):
    """
    Export a single document as an Excel file.

    Parameters
    ----------
    doctype : str
    docname : str
    column_config : str | None
        JSON-serialised list of ColumnConfig objects (field_key, label, width,
        visible, sort_order).  Only visible columns are exported.

    Returns
    -------
    dict  { "file_url": str } on success
    dict  { "error": str }   on failure
    """
    try:
        _check_global_export_enabled()
        doc = _get_doc_with_permission(doctype, docname)
        columns = _resolve_columns(doctype, column_config)
        if not columns:
            return {"error": _("No columns selected for export.")}

        rows = [_build_row(doctype, doc, columns)]
        xlsx_data = _make_xlsx(doctype, docname, columns, rows)
        file_url = _save_file(
            content=xlsx_data,
            fname=f"{_safe_filename(doctype)}_{_safe_filename(docname)}.xlsx",
            doctype=doctype,
            docname=docname,
            is_private=1,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return {"file_url": file_url}

    except frappe.PermissionError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "export_doctype_excel")
        return {"error": str(exc)}


@frappe.whitelist()
def export_doctype_list_excel(doctype, filters=None, column_config=None):
    """
    Export multiple documents (list/tree view) matching filters as an Excel file.
    """
    try:
        _check_global_export_enabled()
        # Verify read and export permissions on the DocType
        if not frappe.has_permission(doctype, ptype="read"):
            frappe.throw(_("You do not have permission to read {0}.").format(doctype), frappe.PermissionError)
        if not frappe.has_permission(doctype, ptype="export"):
            frappe.throw(_("You do not have export permission for {0}.").format(doctype), frappe.PermissionError)

        columns = _resolve_columns(doctype, column_config)
        if not columns:
            return {"error": _("No columns selected for export.")}

        parsed_filters = _sanitize_filters(doctype, filters)

        fields = [col["field_key"] for col in columns]
        if "name" not in fields:
            fields.append("name")

        records = frappe.get_list(doctype, filters=parsed_filters, fields=fields, limit=5000)

        rows = []
        for r in records:
            rows.append(_build_row(doctype, r, columns))

        xlsx_data = _make_xlsx(doctype, "List", columns, rows)
        file_url = _save_file(
            content=xlsx_data,
            fname=f"{_safe_filename(doctype)}_List_Export.xlsx",
            doctype=doctype,
            docname=None,
            is_private=1,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return {"file_url": file_url}

    except frappe.PermissionError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "export_doctype_list_excel")
        return {"error": str(exc)}


@frappe.whitelist()
def export_doctype_pdf(doctype, docname, column_config=None):
    """
    Export a single document as a PDF file.

    Parameters
    ----------
    doctype : str
    docname : str
    column_config : str | None
        JSON-serialised list of ColumnConfig objects.

    Returns
    -------
    dict  { "file_url": str } on success
    dict  { "error": str }   on failure
    """
    try:
        _check_global_export_enabled()
        doc = _get_doc_with_permission(doctype, docname)
        columns = _resolve_columns(doctype, column_config)
        if not columns:
            return {"error": _("No columns selected for export.")}

        row = _build_row(doctype, doc, columns)
        html = _render_pdf_template(doctype, docname, columns, row)
        pdf_bytes = get_pdf(html, {"page-size": "A4", "orientation": "Landscape"})
        file_url = _save_file(
            content=pdf_bytes,
            fname=f"{_safe_filename(doctype)}_{_safe_filename(docname)}.pdf",
            doctype=doctype,
            docname=docname,
            is_private=1,
            content_type="application/pdf",
        )
        return {"file_url": file_url}

    except frappe.PermissionError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "export_doctype_pdf")
        return {"error": str(exc)}


@frappe.whitelist()
def export_doctype_list_pdf(doctype, filters=None, column_config=None):
    """
    Export multiple documents (list/tree view) matching filters as a PDF file.
    """
    try:
        _check_global_export_enabled()
        if not frappe.has_permission(doctype, ptype="read"):
            frappe.throw(_("You do not have permission to read {0}.").format(doctype), frappe.PermissionError)
        if not frappe.has_permission(doctype, ptype="export"):
            frappe.throw(_("You do not have export permission for {0}.").format(doctype), frappe.PermissionError)

        columns = _resolve_columns(doctype, column_config)
        if not columns:
            return {"error": _("No columns selected for export.")}

        parsed_filters = _sanitize_filters(doctype, filters)

        fields = [col["field_key"] for col in columns]
        if "name" not in fields:
            fields.append("name")

        records = frappe.get_list(doctype, filters=parsed_filters, fields=fields, limit=1000)

        rows = []
        for r in records:
            rows.append(_build_row(doctype, r, columns))

        html = _render_list_pdf_template(doctype, columns, rows)
        pdf_bytes = get_pdf(html, {"page-size": "A4", "orientation": "Landscape"})
        file_url = _save_file(
            content=pdf_bytes,
            fname=f"{_safe_filename(doctype)}_List_Export.pdf",
            doctype=doctype,
            docname=None,
            is_private=1,
            content_type="application/pdf",
        )
        return {"file_url": file_url}

    except frappe.PermissionError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "export_doctype_list_pdf")
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_filters(doctype, filters):
    """
    Clean filters to only include valid docfield names or standard fields for the doctype.
    Prevents errors like 'You do not have permission to access field: DocType.doctype'
    when tree_view.args (e.g. {'doctype': 'Account', 'cmd': '...'}) is passed as filters.
    """
    if not filters:
        return {}
    parsed = filters
    if isinstance(filters, str):
        try:
            parsed = json.loads(filters)
        except Exception:
            parsed = filters

    IGNORED_KEYS = {"doctype", "cmd", "method", "is_root", "tree_method"}

    try:
        meta = frappe.get_meta(doctype)
        valid_fields = {df.fieldname for df in meta.fields} | {
            "name", "creation", "modified", "modified_by", "owner", "docstatus", "idx"
        }
        if meta.istable:
            valid_fields.update({"parent", "parenttype", "parentfield"})
    except Exception:
        valid_fields = None

    if isinstance(parsed, dict):
        sanitized = {}
        for k, v in parsed.items():
            if k in IGNORED_KEYS:
                continue
            if valid_fields is not None and k not in valid_fields:
                continue
            sanitized[k] = v
        return sanitized
    elif isinstance(parsed, list):
        sanitized = []
        for f in parsed:
            if isinstance(f, (list, tuple)):
                fname = f[1] if len(f) == 4 else (f[0] if len(f) >= 1 else None)
                if fname in IGNORED_KEYS:
                    continue
                if valid_fields is not None and fname not in valid_fields:
                    continue
                sanitized.append(f)
            elif isinstance(f, str):
                if f in IGNORED_KEYS:
                    continue
                if valid_fields is not None and f not in valid_fields:
                    continue
                sanitized.append(f)
        return sanitized
    return {}

def _check_global_export_enabled():
    """Raise PermissionError if the global export toggle is disabled."""
    try:
        settings = frappe.get_single("Construction Settings")
        if hasattr(settings, "enable_global_export_menu") and not settings.enable_global_export_menu:
            frappe.throw(_("Global Export Menu is disabled in Construction Settings."),
                         frappe.PermissionError)
    except frappe.DoesNotExistError:
        pass  # Settings doctype not yet migrated; allow export


def _get_doc_with_permission(doctype, docname):
    """
    Load the document and verify the user has both read AND export permission.
    Export permission is the correct gate for generating downloadable files.
    """
    if not frappe.has_permission(doctype, ptype="read", doc=docname):
        frappe.throw(
            _("You do not have permission to read {0} — {1}.").format(doctype, docname),
            frappe.PermissionError,
        )
    if not frappe.has_permission(doctype, ptype="export", doc=docname):
        frappe.throw(
            _("You do not have export permission for {0}.").format(doctype),
            frappe.PermissionError,
        )
    return frappe.get_doc(doctype, docname)


def _resolve_columns(doctype, column_config_json):
    """
    Return an ordered list of dicts { field_key, label, fieldtype, options }
    for the visible columns.

    When the caller provides column_config (the common path from PrintSettingsDialog),
    fieldtype and options are merged back in from meta so that _format_value can
    apply correct formatting even for user-reordered/hidden columns.
    """
    meta = frappe.get_meta(doctype)
    meta_field_map = {f.fieldname: f for f in meta.fields}

    if column_config_json:
        try:
            raw = json.loads(column_config_json)
            cols = []
            for c in raw:
                if not c.get("visible", True):
                    continue
                key = c.get("field_key", "")
                meta_f = meta_field_map.get(key)
                # H1: merge fieldtype / options from meta so formatting is applied
                cols.append({
                    "field_key": key,
                    "label": c.get("label") or (_(meta_f.label) if meta_f else key),
                    "fieldtype": c.get("fieldtype") or (meta_f.fieldtype if meta_f else "Data"),
                    "options": c.get("options") or (meta_f.options or "" if meta_f else ""),
                })
            return cols
        except (ValueError, TypeError):
            pass  # Fall through to auto-generate

    # Auto-generate from meta
    cols = []
    for f in meta.fields:
        if f.fieldtype in NON_EXPORTABLE_FIELDTYPES:
            continue
        if not f.fieldname:
            continue
        if f.hidden:
            continue
        if f.fieldname in SYSTEM_FIELDS_HIDDEN_BY_DEFAULT:
            continue
        cols.append({
            "field_key": f.fieldname,
            "label": _(f.label or f.fieldname),
            "fieldtype": f.fieldtype,
            "options": f.options or "",
        })
    return cols


def _build_row(doctype, doc, columns):
    """
    Build a dict mapping field_key → formatted display value for the doc/dict.
    """
    meta = frappe.get_meta(doctype)
    field_map = {f.fieldname: f for f in meta.fields}
    row = {}
    for col in columns:
        key = col["field_key"]
        # Works on both DocType documents and raw dicts from get_list
        raw = doc.get(key)
        # Use the fieldtype from the resolved column (preferred) or look it up
        fieldtype = col.get("fieldtype") or (field_map[key].fieldtype if key in field_map else "Data")
        row[key] = _format_value(raw, fieldtype, col.get("options", ""))
    return row


def _format_value(value, fieldtype, options=""):
    """
    Format a raw doc value according to its fieldtype for display in export.

    Parameters
    ----------
    value    : raw value from the document
    fieldtype: Frappe fieldtype string
    options  : field options string (used for Select label resolution)
    """
    if value is None or value == "":
        return ""

    if fieldtype == "Check":
        return _("Yes") if cint(value) else _("No")

    if fieldtype == "Date":
        try:
            return format_date(value)
        except Exception:
            return str(value)

    if fieldtype == "Datetime":
        try:
            return format_datetime(value)
        except Exception:
            return str(value)

    if fieldtype == "Currency":
        try:
            return "{:,.2f}".format(flt(value))
        except Exception:
            return str(value)

    if fieldtype in ("Float", "Percent"):
        try:
            return "{:.2f}".format(flt(value))
        except Exception:
            return str(value)

    if fieldtype == "Int":
        try:
            return str(int(flt(value)))
        except Exception:
            return str(value)

    if fieldtype in ("Text Editor", "HTML Editor"):
        # M5: use frappe.utils.strip_html to decode HTML entities correctly
        return strip_html(str(value)).strip()

    if fieldtype == "Select" and options:
        # L5: Select stores the raw value; return it as-is (options are the same
        # strings shown in the UI for Frappe Select fields).
        return str(value)

    # Default: plain string
    return str(value)


def _make_xlsx(doctype, docname, columns, rows):
    """Build in-memory Excel bytes using frappe's xlsxutils."""
    # L1: make_xlsx is imported at module level; no try/except needed
    header = [col.get("label", col["field_key"]) for col in columns]
    data_rows = []
    for row in rows:
        data_rows.append([row.get(col["field_key"], "") for col in columns])

    xlsx_file = make_xlsx([header] + data_rows, f"{doctype} Export")
    return xlsx_file.getvalue()


def _render_pdf_template(doctype, docname, columns, row):
    """Render the generic export PDF Jinja template."""
    company = frappe.defaults.get_global_default("company") or ""
    from frappe.utils import now_datetime
    export_date = format_datetime(now_datetime())

    template_path = "construction/templates/generic_export_pdf.html"
    return frappe.render_template(
        template_path,
        {
            "doctype": doctype,
            "docname": docname,
            "columns": columns,
            "row": row,
            "company": company,
            "export_date": export_date,
        },
    )


def _render_list_pdf_template(doctype, columns, rows):
    """Render the generic export list PDF Jinja template."""
    company = frappe.defaults.get_global_default("company") or ""
    from frappe.utils import now_datetime
    export_date = format_datetime(now_datetime())

    template_path = "construction/templates/generic_export_list_pdf.html"
    return frappe.render_template(
        template_path,
        {
            "doctype": doctype,
            "columns": columns,
            "rows": rows,
            "company": company,
            "export_date": export_date,
        },
    )


def _save_file(content, fname, doctype, docname, is_private=1, content_type=None):
    """Save binary content as a Frappe File and return its file_url."""
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "is_private": is_private,
        "content": content,
    })
    # Save the file. Uses insert() instead of save(ignore_permissions=True)
    # to enforce proper user write permissions on files.
    file_doc.insert(ignore_permissions=False)
    return file_doc.file_url


def _safe_filename(value):
    """Strip non-alphanumeric characters from a string for use in filenames."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(value))
