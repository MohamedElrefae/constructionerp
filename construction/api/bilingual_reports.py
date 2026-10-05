"""Stage 7 report/print pilot — governed bilingual report rendering.

Construction-owned whitelisted API over the Stage-4 extension-point spike
(`construction.services.report_bilingual_extension`). It renders the
approved pilot reports' vendor `execute` output (read-only) in Arabic /
English / Both modes without editing any vendor file, Report DocType, or
runtime data. Native report and company authorization runs before resolving
the vendor module; vendor execution then produces the structures to transform.

Pilot scope (owner decision 2026-09-21):
  General Ledger, Trial Balance, Accounts Receivable (Aging), plus one BOQ
  print/export surface (tracked separately; see the pilot doc).

Statement expansion (owner decision 2026-10-05, Tier 5E):
  Balance Sheet, Profit and Loss Statement — same fail-closed boundary, the
  service layer's existing label-field entries, and read-only period defaults
  for the vendor `get_period_list` contract.

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
    "Balance Sheet": "erpnext.accounts.report.balance_sheet.balance_sheet",
    "Profit and Loss Statement": "erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement",
}

STATEMENT_REPORTS = ("Balance Sheet", "Profit and Loss Statement")


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
    - Native report/company permission checks precede vendor execution.
    - Returns {columns, data, mode, report_name} — source data untouched.
    """
    if report_name not in PILOT_REPORTS:
        frappe.throw(frappe._("Unsupported report: {0}").format(report_name))
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    filters = _parse_filters(filters)
    _check_report_access(report_name, filters)
    lang = mode or lang or (frappe.local.lang if getattr(frappe.local, "lang", None) else "en")
    mode = normalize_mode(lang)
    module = frappe.get_module(PILOT_REPORTS[report_name])
    execute = getattr(module, "execute", None) or (module if callable(module) else None)
    filters = _ensure_required(filters, report_name)
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


def _check_report_access(report_name, filters):
    from frappe.desk.query_report import get_report_doc, validate_filters_permissions

    # Direct vendor execute() does not run query_report.run's authorization.
    # Honor Report roles, report permission and disabled state, then bind the
    # selected/default company to native document permissions before any SQL.
    get_report_doc(report_name)
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    if not isinstance(company, str) or not company.strip():
        frappe.throw(frappe._("Please select a company."))
    frappe.get_doc("Company", company).check_permission("read")
    filters["company"] = company
    validate_filters_permissions(report_name, filters, frappe.session.user)


def _ensure_required(filters, report_name):
    """Vendor-required fiscal year + date-window defaults (read-only)."""
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    reference_date = (
        filters.get("from_date")
        or filters.get("period_start_date")
        or filters.get("report_date")
        or filters.get("to_date")
        or frappe.utils.today()
    )

    if report_name == "General Ledger":
        if not (filters.get("from_date") and filters.get("to_date")):
            bounds = _fy_bounds(company, reference_date)
            filters.setdefault("from_date", bounds["start"])
            filters.setdefault("to_date", bounds["end"])
        return filters

    if report_name == "Accounts Receivable":
        fy = filters.get("fiscal_year") or _resolve_fy(company, reference_date)
        bounds = _fy_bounds(company, reference_date)
        filters.setdefault("report_date", bounds["end"])
        filters.setdefault("to_date", bounds["end"])
        filters.setdefault("fiscal_year", fy or filters.get("fiscal_year"))
        filters.setdefault("ageing_based_on", "Posting Date")
        return filters

    if report_name == "Trial Balance":
        if not filters.get("fiscal_year"):
            filters["fiscal_year"] = _resolve_fy(company, reference_date)
        return filters

    if report_name in STATEMENT_REPORTS:
        # R4 (Tier 5E): read-only defaults for the vendor get_period_list
        # contract — caller-supplied values always win (setdefault only).
        filters.setdefault("periodicity", "Yearly")
        filters.setdefault("accumulated_values", 0)
        filters.setdefault("filter_based_on", "Date Range")
        if filters.get("filter_based_on") == "Fiscal Year":
            if not (filters.get("from_fiscal_year") and filters.get("to_fiscal_year")):
                fy = filters.get("fiscal_year") or _resolve_fy(company, reference_date)
                filters.setdefault("from_fiscal_year", fy)
                filters.setdefault("to_fiscal_year", fy)
        else:
            filters.setdefault("period_start_date", filters.get("from_date"))
            filters.setdefault("period_end_date", filters.get("to_date"))
            if not (filters.get("period_start_date") and filters.get("period_end_date")):
                bounds = _fy_bounds(company, reference_date)
                filters["period_start_date"] = filters.get("period_start_date") or bounds["start"]
                filters["period_end_date"] = filters.get("period_end_date") or bounds["end"]
        return filters

    return filters


def _shaped(columns, data):
    return {"columns": columns, "data": data}


def _label_fields(report_name):
    from construction.services.report_bilingual_extension import REPORT_LABEL_FIELDS

    return REPORT_LABEL_FIELDS.get(report_name) or ["account", "account_name"]


def _account_mapping(company):
    return load_account_arabic_mapping(company)


def _fy_bounds(company, reference_date=None):
    fy = _fiscal_year(company, reference_date)
    return {"start": str(fy.year_start_date), "end": str(fy.year_end_date)}


def _resolve_fy(company, reference_date=None):
    return _fiscal_year(company, reference_date).name


def _fiscal_year(company, reference_date=None):
    from erpnext.accounts.utils import get_fiscal_year

    # Without a date ERPNext returns its newest configured year, including
    # future years. Keep the requested reporting period and company together;
    # missing configuration must not silently select an unrelated year.
    return get_fiscal_year(
        date=reference_date or frappe.utils.today(),
        company=company,
        verbose=0,
        as_dict=True,
        raise_on_missing=True,
    )
