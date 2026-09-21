"""Stage 7 report/print pilot — governed bilingual report rendering.

Construction-owned whitelisted API over the Stage-4 extension-point spike
(`construction.services.report_bilingual_extension`). It renders the
approved pilot reports' vendor `execute` output (read-only) in Arabic /
English / Both modes without editing any vendor file, Report DocType, or
runtime data. Site permissions are enforced by the vendor reports' own
execute paths; this module only post-processes the returned structures.

Pilot scope (owner decision 2026-09-21):
  General Ledger, Trial Balance, Accounts Receivable (Aging), plus one BOQ
  print/export surface (tracked separately; see the pilot doc).

Fail-closed: unknown report names are rejected rather than executed.
"""

import frappe

from construction.services.report_bilingual_extension import (
    load_account_arabic_mapping,
    normalize_mode,
    transform_report,
)

PILOT_REPORTS = {
    "General Ledger": "erpnext.accounts.report.general_ledger.general_ledger",
    "Trial Balance": "erpnext.accounts.report.trial_balance.trial_balance",
    "Accounts Receivable": "erpnext.accounts.report.accounts_receivable.accounts_receivable",
}


def _parse_filters(filters):
    import json

    if filters is None or filters == "":
        return frappe._dict()
    if not isinstance(filters, str):
        if not isinstance(filters, dict):
            frappe.throw(frappe._("Invalid filters: value must be a JSON object"))
        return frappe._dict(filters)
    try:
        v = json.loads(filters)
    except ValueError:
        frappe.throw(frappe._("Invalid filters: value must be a JSON object"))
    if v is None or not isinstance(v, dict):
        frappe.throw(frappe._("Invalid filters: value must be a JSON object"))
    return frappe._dict(v)


@frappe.whitelist()
def localized_report(report_name, filters=None, lang=None, mode=None):
    """Render a pilot financial report's output with Arabic account labels.

    - `report_name` must be in PILOT_REPORTS (fail-closed otherwise).
    - `mode`: `ar` (default for an ar* session), `en`, or `both`.
    - Vendor report `execute` runs read-only under the caller's permissions.
    - Returns {columns, data, mode, report_name} — source data untouched.
    """
    if report_name not in PILOT_REPORTS:
        frappe.throw(frappe._("Unsupported report: {0}").format(report_name))
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    filters = _parse_filters(filters)
    lang = mode or lang or (frappe.local.lang if getattr(frappe.local, "lang", None) else "en")
    mode = normalize_mode(lang)
    module = frappe.get_module(PILOT_REPORTS[report_name])
    execute = getattr(module, "execute", None) or (module if callable(module) else None)
    filters = _ensure_required(filters, report_name)
    _out = execute(filters=filters)
    _out = execute(filters=filters)
    if isinstance(_out, tuple) and len(_out) >= 2:
        # vendor execution already ran here (AR Aging returns a documented
        # 6-valued tuple); post-process only the bilingual contract surface.
        label_fields = _label_fields(report_name)
        mapping = _account_mapping(filters.get("company"))
        columns, data = transform_report(_out[0], _out[1], lang, mapping, label_fields)
        tail = [x for x in _out[2:]] if len(_out) > 2 else []
        payload = {"report_name": report_name, "mode": normalize_mode(lang), **_shaped(columns, data)}
        if tail:
            payload["tail"] = tail[:3]
        return payload
    return {"report_name": report_name, "mode": normalize_mode(lang), **_shaped(_out.columns, _out.data)}


def _ensure_required(filters, report_name):
    """Vendor-required fiscal year + date-window defaults (read-only)."""
    company = filters.get("company") or frappe.defaults.get_user_default("Company")

    if report_name == "General Ledger":
        fy = _resolve_fy(company)
        bounds = _fy_bounds(company)
        filters.setdefault("from_date", bounds["start"])
        filters.setdefault("to_date", bounds["end"])
        return filters

    if report_name == "Accounts Receivable":
        fy = _resolve_fy(company)
        bounds = _fy_bounds(company)
        filters.setdefault("report_date", bounds["end"])
        filters.setdefault("to_date", bounds["end"])
        filters.setdefault("fiscal_year", fy or filters.get("fiscal_year"))
        filters.setdefault("ageing_based_on", "Posting Date")
        return filters

    if report_name == "Trial Balance":
        if not filters.get("fiscal_year"):
            filters["fiscal_year"] = _resolve_fy(company)
    return filters


def _shaped(columns, data):
    return {"columns": columns, "data": data}


def _label_fields(report_name):
    from construction.services.report_bilingual_extension import REPORT_LABEL_FIELDS

    return REPORT_LABEL_FIELDS.get(report_name) or ["account", "account_name"]


def _account_mapping(company):
    return load_account_arabic_mapping(company)


def _fy_bounds(company):
    import datetime

    fy = _resolve_fy(company)
    fy_doc = (
        frappe.get_all(
            "Fiscal Year",
            filters={"name": fy, "disabled": 0},
            fields=["year_start_date", "year_end_date"],
            limit=1,
        )
        if fy
        else []
    )
    today = frappe.utils.today()
    if fy_doc and fy_doc[0].get("year_start_date"):
        start = str(fy_doc[0].get("year_start_date"))
        end = str(fy_doc[0].get("year_end_date")) if str(fy_doc[0].get("year_end_date")) >= today else today
        return {"start": start, "end": end}
    from datetime import date, timedelta

    return {"start": str(date.today() - timedelta(days=365)), "end": today}


def _resolve_fy(company):
    if not company:
        return None
    try:
        from erpnext.accounts.utils import get_fiscal_year

        fy = get_fiscal_year(company=company, raise_on_missing=False, boolean=0, verbose=0, as_dict=True)
        if fy:
            return fy.get("name") if isinstance(fy, dict) else fy[0]
    except Exception:
        pass
    fy_name = frappe.get_all(
        "Fiscal Year", filters={"disabled": 0}, fields=["name"], order_by="year_start_date desc", limit=1
    )
    return fy_name[0]["name"] if fy_name else None
