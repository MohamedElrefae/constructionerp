import frappe
from frappe import _


@frappe.whitelist()
def cleanup_old_doctypes():
	"""Delete old DocTypes and Pages from the database."""

	# Delete old DocTypes
	old_doctypes = ["LaborResource", "MaterialResource", "PlantResource", "CostItem"]

	for dt in old_doctypes:
		try:
			if frappe.db.exists("DocType", dt):
				frappe.delete_doc("DocType", dt, force=True)
				frappe.db.commit()
				print(f"Deleted DocType: {dt}")
		except Exception as e:
			print(f"Error deleting {dt}: {e}")

	# Delete old Pages
	old_pages = ["materialresource", "plantresource", "costitem"]

	for page in old_pages:
		try:
			if frappe.db.exists("Page", page):
				frappe.delete_doc("Page", page, force=True)
				frappe.db.commit()
				print(f"Deleted Page: {page}")
		except Exception as e:
			print(f"Error deleting {page}: {e}")

	return {"success": True, "message": "Cleanup complete!"}
