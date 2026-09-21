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

from construction.services.report_bilingual_extension import bilingualize_report, normalize_mode

PILOT_REPORTS = {
    "General Ledger": "erpnext.accounts.report.general_ledger.general_ledger",
    "Trial Balance": "erpnext.accounts.report.trial_balance.trial_balance",
    "Accounts Receivable": "erpnext.accounts.report.accounts_receivable.accounts_receivable",
}


def _parse_filters(filters):
    import json

    if filters is None or filters == "":
        return None
    if not isinstance(filters, str):
        if not isinstance(filters, dict):
            frappe.throw(frappe._("Invalid filters: value must be a JSON object"))
        return filters
    try:
        v = json.loads(filters)
    except ValueError:
        frappe.throw(frappe._("Invalid filters: value must be a JSON object"))
    if v is None or not isinstance(v, dict):
        frappe.throw(frappe._("Invalid filters: value must be a JSON object"))
    return v


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
    columns, data = bilingualize_report(execute, filters or {}, lang, report_name)
    return {"report_name": report_name, "mode": normalize_mode(lang), "columns": columns, "data": data}
