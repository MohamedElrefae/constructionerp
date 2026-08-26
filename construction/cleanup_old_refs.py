import frappe
from frappe import _


def cleanup_old_doctypes():
    """Delete old DocTypes and Pages from the database (CLI/migration use only)."""
    frappe.only_for("System Manager")

    logger = frappe.logger("construction")

    # Delete old DocTypes
    old_doctypes = ["LaborResource", "MaterialResource", "PlantResource", "CostItem"]

    for dt in old_doctypes:
        try:
            if frappe.db.exists("DocType", dt):
                frappe.delete_doc("DocType", dt, ignore_permissions=False)
                logger.info(f"Deleted legacy DocType: {dt}")
        except Exception as e:
            logger.warning(f"Error deleting legacy DocType {dt}: {e}")

    # Delete old Pages
    old_pages = ["materialresource", "plantresource", "costitem"]

    for page in old_pages:
        try:
            if frappe.db.exists("Page", page):
                frappe.delete_doc("Page", page, ignore_permissions=False)
                logger.info(f"Deleted legacy Page: {page}")
        except Exception as e:
            logger.warning(f"Error deleting legacy Page {page}: {e}")

    return {"success": True, "message": "Cleanup complete!"}
