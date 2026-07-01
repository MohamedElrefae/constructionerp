import frappe
from frappe import _
from frappe.utils import flt, today


def get_suggested_rate(item_code, supplier=None, project=None, company=None, region=None, as_of_date=None):
    """Get best suggested rate for an item.
    
    Priority order:
    1. Last submitted Purchase Invoice rate
    2. Last submitted Purchase Order rate
    3. Last other source (Import, Manual, etc.)
    4. Item Price (standard ERPNext)
    
    Excludes Cancelled history rows.
    Optionally filters by region and as-of date for price locking.
    Returns dict with rate, source, and source_document.
    """
    for source_label, source_doctype in (
        ("Last PI", "Purchase Invoice"),
        ("Last PO", "Purchase Order"),
    ):
        rate, source_doc = _get_last_history_rate(
            item_code,
            source_doctype=source_doctype,
            supplier=supplier,
            company=company,
            region=region,
            as_of_date=as_of_date,
        )
        if rate:
            return {"rate": rate, "source": source_label, "source_name": source_doc}

    rate, source_doc = _get_last_history_rate(
        item_code,
        exclude_source_doctypes=("Purchase Invoice", "Purchase Order"),
        supplier=supplier,
        company=company,
        region=region,
        as_of_date=as_of_date,
    )
    if rate:
        return {"rate": rate, "source": "Last Price History", "source_name": source_doc}

    rate = _get_item_price_rate(item_code)
    if rate:
        return {"rate": rate, "source": "Item Price", "source_name": None}

    return {"rate": 0, "source": "None", "source_name": None}


def _get_last_history_rate(
    item_code,
    source_doctype=None,
    exclude_source_doctypes=None,
    supplier=None,
    company=None,
    region=None,
    as_of_date=None,
):
    """Get the latest active Resource Price History rate for an item."""
    filters = {
        "item_code": item_code,
        "status": "Active",
    }
    if source_doctype:
        filters["source_doctype"] = source_doctype
    if supplier:
        filters["supplier"] = supplier
    if company:
        filters["company"] = company
    if region:
        filters["region"] = region

    if as_of_date:
        filters["price_date"] = ["<=", as_of_date]

    names = frappe.db.get_all(
        "Resource Price History",
        filters=filters,
        fields=["name", "source_name", "source_doctype"],
        order_by="price_date desc, modified desc",
        limit=20,
    )

    for row in names:
        if exclude_source_doctypes and row.source_doctype in exclude_source_doctypes:
            continue
        rate = frappe.db.get_value("Resource Price History", row.name, "rate")
        if rate:
            return flt(rate), row.source_name

    return None, None


def _get_item_price_rate(item_code):
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "buying": 1, "price_list": "Standard Buying"},
        "price_list_rate",
        order_by="valid_from desc",
    )
    return flt(price) if price else None


def capture_price_from_purchase_document(doc, method=None):
    """Hook handler: on_submit of Purchase Invoice or Purchase Order.
    
    Creates Resource Price History rows for each item row.
    """
    if doc.docstatus != 1:
        return

    if doc.doctype == "Purchase Invoice":
        source_doctype = "Purchase Invoice"
        items = doc.get("items") or []
    elif doc.doctype == "Purchase Order":
        source_doctype = "Purchase Order"
        items = doc.get("items") or []
    else:
        return

    for row in items:
        if not row.get("item_code"):
            continue
        if not row.get("rate") or flt(row.rate) <= 0:
            continue

        existing = frappe.db.get_value(
            "Resource Price History",
            {
                "source_doctype": source_doctype,
                "source_name": doc.name,
                "source_row": str(row.get("name", "")),
                "item_code": row.item_code,
            },
            "name",
        )
        if existing:
            continue

        history = frappe.new_doc("Resource Price History")
        history.item_code = row.item_code
        history.rate = flt(row.rate)
        history.uom = row.get("uom") or row.get("stock_uom")
        history.price_date = doc.get("posting_date") or doc.get("transaction_date") or today()
        history.supplier = doc.get("supplier")
        history.company = doc.get("company")
        history.project = doc.get("project")
        history.currency = doc.get("currency") or frappe.db.get_value("Company", doc.get("company"), "default_currency")
        history.source_doctype = source_doctype
        history.source_name = doc.name
        history.source_row = str(row.get("name", ""))
        history.status = "Active"
        history.flags.ignore_permissions = True
        history.insert()


def cancel_price_history_for_document(doc, method=None):
    """Hook handler: on_cancel of Purchase Invoice or Purchase Order.
    
    Marks matching history rows as Cancelled instead of deleting them.
    """
    if doc.doctype not in ("Purchase Invoice", "Purchase Order"):
        return

    source_doctype = doc.doctype
    rows = frappe.db.get_all(
        "Resource Price History",
        filters={
            "source_doctype": source_doctype,
            "source_name": doc.name,
            "status": "Active",
        },
        pluck="name",
    )
    for name in rows:
        frappe.db.set_value(
            "Resource Price History",
            name,
            {
                "status": "Cancelled",
                "cancelled_by": frappe.session.user,
                "cancelled_on": frappe.utils.now(),
            },
            update_modified=False,
        )
