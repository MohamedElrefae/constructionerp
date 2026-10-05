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

Statement expansion (owner decision 2026-10-05, Tier 5E):
  Balance Sheet, Profit and Loss Statement — same fail-closed boundary, the
  service layer's existing label-field entries, and read-only period defaults
  for the vendor `get_period_list` contract.

Statement expansion II (owner decision 2026-10-05, Stage 7 extension):
  Accounts Payable Summary, Accounts Receivable Summary and Cash Flow join
  the allowlist under the unchanged fail-closed / single-execute / role-gate
  contract, and every allowlisted report renders localized column headers in
  `ar` / `both` modes from the governed `COLUMN_LABELS` map (values harvested
  read-only from the site's approved `tabTranslation` ar rows; see the work
  item SCOPE for provenance and the recorded ambiguity resolutions).

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
    "Accounts Receivable Summary": (
        "erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary"
    ),
    "Accounts Payable Summary": (
        "erpnext.accounts.report.accounts_payable_summary.accounts_payable_summary"
    ),
    "Cash Flow": "erpnext.accounts.report.cash_flow.cash_flow",
}

STATEMENT_REPORTS = ("Balance Sheet", "Profit and Loss Statement")

# Stage 7 extension: these reports consume the same vendor `get_period_list`
# contract (filter_based_on / periodicity / period dates), so they share the
# read-only defaults branch below.
PERIOD_CONTRACT_REPORTS = STATEMENT_REPORTS + ("Cash Flow",)

# Stage 7 extension: AR/AP Summary subclass the vendor ReceivablePayableReport
# and need its `report_date` window defaults instead of the period contract.
RECEIVABLE_PAYABLE_SUMMARY_REPORTS = (
    "Accounts Receivable Summary",
    "Accounts Payable Summary",
)

# Governed column-header map (R1, Stage 7 extension).
#
# Values are the site's approved `tabTranslation` rows for `language='ar'`,
# harvested read-only on 2026-10-05 and pinned here so the report path stays
# deterministic (no runtime translation-cache dependency, no DB read, stable
# while the translation catalog is being harmonized elsewhere). Ambiguities
# were resolved and recorded in the work item SCOPE:
#   Posting Date -> تاريخ الترحيل (not تاريخ القيد), Balance -> الرصيد
#   (not الموازنة), Party -> الطرف (not الطرف المعني), Section -> القسم
#   (not الجزء), Invoiced Amount -> قيمة الفواتير (sole approved row).
# Labels whose only approved row was empty or malformed (GL Entry, Age (Days),
# Against Voucher Type, Transaction Currency, Opening (Dr)) are deliberately
# absent and pass through untranslated (fail-open per column), as do labels
# whose approved rows compete without a recorded resolution (Grand Total).
COLUMN_LABELS = {
    "Posting Date": "تاريخ الترحيل",
    "Account": "الحساب",
    "Account Name": "اسم الحساب",
    "Account Number": "رقم الحساب",
    "Currency": "العملة",
    "Debit": "مدين",
    "Credit": "دائن",
    "Balance": "الرصيد",
    "Closing Balance": "الرصيد الختامي",
    "Voucher Type": "نوع السند",
    "Voucher Subtype": "النوع الفرعي للسند",
    "Voucher No": "رقم السند",
    "Against Account": "مقابل الحساب",
    "Against Voucher No": "مقابل رقم السند",
    "Party Type": "نوع الطرف",
    "Party": "الطرف",
    "Party Name": "اسم الطرف",
    "Customer Name": "اسم العميل",
    "Supplier Name": "اسم المورد",
    "Outstanding Amount": "المبلغ المستحق",
    "Invoiced Amount": "قيمة الفواتير",
    "Paid Amount": "المبلغ المدفوع",
    "Advance Amount": "المبلغ مقدما",
    "Due Date": "تاريخ الاستحقاق",
    "Credit Note": "إشعار دائن",
    "Debit Note": "إشعار مدين",
    "Section": "القسم",
    "Cost Center": "مركز التكلفة",
    "Project": "المشروع",
}


def localize_column_label(label, lang):
    """Localize one column header for `mode` (pure, fail-open per column).

    Vendor reports build currency-suffixed labels ("Debit (SAR)"), so the map
    is keyed on the English base label and any " (...)" suffix is preserved
    verbatim: "Debit (SAR)" -> "مدين (SAR)". Unmapped labels (including
    "Age (Days)", whose base "Age" is not mapped) pass through unchanged.
    `both` mirrors the cell convention: "Debit (SAR) — مدين (SAR)".
    """
    mode = normalize_mode(lang)
    if mode == "en" or not isinstance(label, str) or not label:
        return label
    base, sep, rest = label.partition(" (")
    arabic = COLUMN_LABELS.get(base.strip())
    if not arabic:
        return label
    ar_label = f"{arabic} ({rest}" if sep else arabic
    if mode == "both":
        return f"{label} — {ar_label}"
    return ar_label


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
    if isinstance(_out, tuple) and len(_out) >= 2:
        # vendor execution already ran here (AR Aging returns a documented
        # 6-valued tuple); post-process only the bilingual contract surface.
        label_fields = _label_fields(report_name)
        mapping = _account_mapping(filters.get("company"))
        columns, data = transform_report(_out[0], _out[1], lang, mapping, label_fields)
        tail = [x for x in _out[2:]] if len(_out) > 2 else []
        payload = {
            "report_name": report_name,
            "mode": normalize_mode(lang),
            **_shaped(_localize_columns(columns, lang), data),
        }
        if tail:
            payload["tail"] = tail[:3]
        return payload
    return {
        "report_name": report_name,
        "mode": normalize_mode(lang),
        **_shaped(_localize_columns(_out.columns, lang), _out.data),
    }


def _localize_columns(columns, lang):
    """Return a fresh column list with `ar`/`both` header labels localized.

    Pure: never mutates the vendor/transform structures it receives (new
    dicts are built per column); `en` mode returns the input unchanged.
    """
    if normalize_mode(lang) == "en" or not columns:
        return columns
    localized = []
    for col in columns:
        if isinstance(col, dict):
            col = dict(col)
            label = col.get("label")
            if isinstance(label, str) and label:
                col["label"] = localize_column_label(label, lang)
            localized.append(col)
        else:
            localized.append(col)
    return localized


def _ensure_required(filters, report_name):
    """Vendor-required fiscal year + date-window defaults (read-only)."""
    company = filters.get("company") or frappe.defaults.get_user_default("Company")

    if report_name == "General Ledger":
        if not (filters.get("from_date") and filters.get("to_date")):
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

    if report_name in RECEIVABLE_PAYABLE_SUMMARY_REPORTS:
        # Stage 7 extension: the AR/AP Summary reports subclass the vendor
        # ReceivablePayableReport, whose ageing window is driven by
        # `report_date` (its __init__ would otherwise default to today).
        bounds = _fy_bounds(company)
        filters.setdefault("report_date", filters.get("to_date") or bounds["end"])
        filters.setdefault("to_date", filters.get("report_date") or bounds["end"])
        filters.setdefault("ageing_based_on", "Posting Date")
        filters.setdefault("fiscal_year", _resolve_fy(company))
        return filters

    if report_name in PERIOD_CONTRACT_REPORTS:
        # R4 (Tier 5E): read-only defaults for the vendor get_period_list
        # contract — caller-supplied values always win (setdefault only).
        filters.setdefault("periodicity", "Yearly")
        filters.setdefault("accumulated_values", 0)
        filters.setdefault("filter_based_on", "Date Range")
        if filters.get("filter_based_on") == "Fiscal Year":
            fy = _resolve_fy(company)
            filters.setdefault("from_fiscal_year", filters.get("fiscal_year") or fy)
            filters.setdefault("to_fiscal_year", filters.get("fiscal_year") or fy)
        else:
            bounds = _fy_bounds(company)
            filters.setdefault("period_start_date", filters.get("from_date") or bounds["start"])
            filters.setdefault("period_end_date", filters.get("to_date") or bounds["end"])
        return filters

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
