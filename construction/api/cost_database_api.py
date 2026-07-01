import frappe
from frappe import _

from construction.services.cost_database_service import (
    bulk_reprice_analyses,
    generate_cost_database_template,
    import_cost_database_from_excel,
)


@frappe.whitelist()
def import_cost_database():
    """Whitelisted endpoint to import a cost database from an uploaded Excel file.

    Expects a multipart form upload with:
        - file: the .xlsx file
        - company: company name (required)
        - dry_run: "1" to validate only (optional, default "0")
        - auto_submit: "1" to auto-submit templates (optional, default "0")
        - region: default region (optional)
        - price_date: default price date YYYY-MM-DD (optional)

    Returns JSON result dict.
    """
    if not frappe.has_permission("Resource Price History", "create"):
        frappe.throw(_("Insufficient permission to import cost database"), frappe.PermissionError)

    uploaded_file = frappe.request.files.get("file")
    if not uploaded_file:
        frappe.throw(_("Excel file is required"), frappe.MandatoryError)

    company = frappe.form_dict.get("company")
    if not company:
        frappe.throw(_("company is required"), frappe.MandatoryError)

    dry_run = frappe.form_dict.get("dry_run", "0") in ("1", "true", "True")
    auto_submit = frappe.form_dict.get("auto_submit", "0") in ("1", "true", "True")
    region = frappe.form_dict.get("region")
    price_date = frappe.form_dict.get("price_date")

    file_content = uploaded_file.stream.read()
    if not file_content:
        frappe.throw(_("Uploaded file is empty"), frappe.ValidationError)

    result = import_cost_database_from_excel(
        file_content=file_content,
        file_name=uploaded_file.filename,
        company=company,
        dry_run=dry_run,
        auto_submit=auto_submit,
        region=region,
        price_date=price_date,
    )
    return result


@frappe.whitelist()
def download_cost_database_template(mode="blank"):
    """Whitelisted endpoint to download a cost database Excel template.

    Args:
        mode: "blank" (default) for headers and validation only, or "sample"
            for a pre-filled illustrative template.

    Returns the .xlsx file as a binary response with appropriate headers.
    """
    if mode not in ("blank", "sample"):
        frappe.throw(_("mode must be 'blank' or 'sample'"), frappe.ValidationError)

    try:
        content = generate_cost_database_template(mode=mode)
    except RuntimeError as e:
        frappe.throw(str(e), frappe.ValidationError)

    filename = f"cost_database_template_{mode}.xlsx"
    frappe.response["filename"] = filename
    frappe.response["filecontent"] = content
    frappe.response["type"] = "binary"
    frappe.response["content_type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@frappe.whitelist()
def reprice_cost_analyses():
    """Whitelisted endpoint to bulk reprice BOQ Cost Analysis detail rows.

    Accepts POST JSON body:
        {
            "boq_header": "...",
            "boq_item": "...",
            "item_code": "...",
            "resource_type": "Material",
            "cost_stream": "M",
            "company": "...",
            "region": "...",
            "as_of_date": "2026-06-01",
            "dry_run": false
        }

    Returns summary dict.
    """
    if not frappe.has_permission("BOQ Cost Analysis", "write"):
        frappe.throw(_("Insufficient permission to reprice analyses"), frappe.PermissionError)

    data = frappe.parse_json(frappe.request.data) if frappe.request.data else frappe.form_dict

    result = bulk_reprice_analyses(
        boq_header=data.get("boq_header"),
        boq_item=data.get("boq_item"),
        item_code=data.get("item_code"),
        resource_type=data.get("resource_type"),
        cost_stream=data.get("cost_stream"),
        company=data.get("company"),
        region=data.get("region"),
        as_of_date=data.get("as_of_date"),
        dry_run=data.get("dry_run", False),
    )
    return result
