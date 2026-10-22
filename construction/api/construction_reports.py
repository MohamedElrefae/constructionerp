# F19 report views: permission-aware adapter over existing estimation services.
#
# The five helpers in ``boq_report_service`` are internal: raw SQL without
# caller authorization, unbounded result sets. This adapter is the only
# customer RPC boundary for the F19 views: allowlisted report identifier,
# scalar filters, explicit Company scope, per-row document authorization,
# bounded paging and exports. Finance ledgers are NOT included (finance-only
# boundary); the integrity view passes through the Administrator-only audit.

import frappe
from frappe import _

REPORTS = (
    "analysis_summary",
    "cost_vs_contract",
    "resource_requirements",
    "price_history",
    "missing_analysis",
)

PAGE_DEFAULT = 50
PAGE_MAX = 200
EXPORT_MAX = 2000


def _putlist(value, cap):
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = cap if cap == PAGE_DEFAULT else 0
    return max(1, min(n, cap))


@frappe.whitelist()
def report_view(
    report,
    company=None,
    boq_header=None,
    item_code=None,
    supplier=None,
    region=None,
    from_date=None,
    to_date=None,
    page=1,
    page_size=PAGE_DEFAULT,
):
    """Read-only, permission-checked projection of one existing estimation service."""
    if report not in REPORTS:
        frappe.throw(_("Unknown report '{0}'.").format(report), frappe.ValidationError)
    if not company or not frappe.db.exists("Company", company):
        frappe.throw(_("A valid company filter is required."))
    frappe.has_permission("Company", "read", doc=company, throw=True)
    from construction.overrides.boq_permissions import scope_company_allows

    if not scope_company_allows(company):
        frappe.throw(_("The selected scope does not permit this company."), frappe.PermissionError)
    if boq_header:
        if not frappe.db.exists("BOQ Header", boq_header):
            frappe.throw(_("BOQ Header {0} was not found.").format(boq_header))
        frappe.has_permission("BOQ Header", "read", doc=boq_header, throw=True)
        header_project = frappe.db.get_value("BOQ Header", boq_header, "project")
        header_company = frappe.db.get_value("Project", header_project, "company") if header_project else None
        if header_company and header_company != company:
            frappe.throw(_("Header company does not match the requested company."), frappe.PermissionError)

    from construction.services import boq_report_service as svc

    if report == "analysis_summary":
        rows = svc.get_boq_cost_analysis_summary(boq_header)
        rows = [r for r in rows if _readable("BOQ Cost Analysis", r.get("analysis_name"))]
        basis = "Submitted (docstatus 1) analyses including Superseded history; filter the analysis_status column for the current Approved view. Every returned row is separately permission-checked."
    elif report == "cost_vs_contract":
        rows = svc.get_boq_item_cost_vs_contract(boq_header)
        rows = [r for r in rows if _readable_item(r.get("boq_item"))]
        basis = "Current estimated direct cost vs contract rate; margin_pct is markup on direct cost % (undefined when cost is zero)."
    elif report == "resource_requirements":
        # Authorization is resolved BEFORE aggregation: the service only
        # aggregates contributions from BOQ Items the caller may read. The
        # aggregate query groups by stream/resource/UOM and therefore has no
        # single boq_item identity to filter on afterwards.
        authorized_items = []
        if boq_header:
            authorized_items = [
                it.name
                for it in frappe.get_all("BOQ Item", filters={"boq_header": boq_header}, fields=["name"])
                if _readable_item(it.name)
            ]
        rows = svc.get_resource_requirement_summary(boq_header, authorized_items=authorized_items)
        basis = "Contract-quantity resource plan (contract qty x factor x wastage / analysis qty); not a revised-quantity forecast."
    elif report == "price_history":
        rows = svc.get_resource_price_history(
            item_code=item_code or None,
            supplier=supplier or None,
            region=region or None,
            from_date=from_date,
            to_date=to_date,
        )
        rows = [r for r in rows if (r.get("company") or company) == company and _readable_rph(r)]
        rows = rows[:EXPORT_MAX]
        basis = "Active price history rows only, recorded currency/UOM shown; no cross-currency aggregation."
    else:
        rows = svc.get_boq_items_missing_analysis(boq_header)
        rows = [r for r in rows if _readable_item(r.get("boq_item"))]
        basis = "Items with no current approved analysis; no-analysis is not zero cost."

    total = len(rows)
    page = _putlist(page, 10**6)
    size = _putlist(page_size, PAGE_MAX)
    start = (page - 1) * size
    return {
        "report": report,
        "basis": basis,
        "effective_filters": {"company": company, "boq_header": boq_header},
        "columns": sorted({k for r in rows for k in r.keys()}) if rows else [],
        "rows": rows[start : start + size],
        "page": page,
        "page_size": size,
        "row_count": total,
        "has_more": start + size < total,
    }


@frappe.whitelist()
def report_export(
    report,
    company=None,
    boq_header=None,
    item_code=None,
    supplier=None,
    region=None,
    from_date=None,
    to_date=None,
):
    """Same boundary as the view; at most EXPORT_MAX rows, private download."""
    data = report_view(
        report,
        company=company,
        boq_header=boq_header,
        item_code=item_code,
        supplier=supplier,
        region=region,
        from_date=from_date,
        to_date=to_date,
        page=1,
        page_size=EXPORT_MAX,
    )
    import json as _json

    content = _json.dumps(
        {
            "report": report,
            "basis": data["basis"],
            "filters": data["effective_filters"],
            "rows": data["rows"],
        },
        default=str,
    )
    fname = f"F19_{report}_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.json"
    fpath = frappe.get_site_path("private", "files", fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": fname,
            "file_url": f"/private/files/{fname}",
            "attached_to_doctype": "BOQ Header" if boq_header else None,
            "attached_to_name": boq_header,
            "is_private": 1,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return {
        "success": True,
        "file_url": file_doc.file_url,
        "file_name": fname,
        "row_count": len(data["rows"]),
        "truncated": data["has_more"],
    }


@frappe.whitelist()
def integrity_view(boq_header):
    """Restricted read-only view of the rollup audit. Administrator only (service-enforced)."""
    from construction.services.boq_rollup_audit import audit_boq_rollups

    result = audit_boq_rollups(boq_header)
    return {
        "boq_header": result.get("boq_header"),
        "stored": result.get("header", {}).get("stored") if isinstance(result.get("header"), dict) else None,
        "computed": result.get("header", {}).get("computed")
        if isinstance(result.get("header"), dict)
        else None,
        "mismatched_fields": result.get("header", {}).get("mismatched_fields")
        if isinstance(result.get("header"), dict)
        else None,
        "structures": result.get("structures", []),
        "aggregation_limit": result.get("aggregation_limit"),
        "note": "Read-only. Discrepancies are investigation inputs; no repair action is included.",
        "raw": result,
    }


def _readable(doctype, name):
    if not name:
        return False
    try:
        return bool(frappe.has_permission(doctype, "read", doc=name))
    except Exception:
        return False


def _readable_item(name):
    return _readable("BOQ Item", name)


def _readable_rph(row):
    name = row.get("name")
    if not name:
        # No identity means the row cannot be authorized, so it does not pass. The old
        # `return True` here let any nameless row through, which is how price history reached
        # personas with no Resource Price History rights before the service selected `name`
        # (F21-D002).
        return False
    return _readable("Resource Price History", name)
