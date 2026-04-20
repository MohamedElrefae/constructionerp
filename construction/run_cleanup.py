#!/usr/bin/env python
import sys

sys.path.insert(0, "/home/melre/construction-erp/apps/backend/frappe-bench/apps/frappe")

import frappe

frappe.init("construction.local")

# Delete old DocTypes
old_doctypes = ["LaborResource", "MaterialResource", "PlantResource", "CostItem"]
for dt in old_doctypes:
	try:
		frappe.db.sql(f"DELETE FROM `tabDocType` WHERE name = '{dt}'")
		frappe.db.sql(f"DELETE FROM `tabDocType Field` WHERE parent = '{dt}'")
		frappe.db.sql(f"DELETE FROM `tabDocType Action` WHERE parent = '{dt}'")
		frappe.db.sql(f"DELETE FROM `tabDocType Link` WHERE parent = '{dt}'")
		print(f"Deleted DocType: {dt}")
	except Exception as e:
		print(f"Error deleting {dt}: {e}")

# Delete old Pages
old_pages = ["materialresource", "plantresource", "costitem"]
for page in old_pages:
	try:
		frappe.db.sql(f"DELETE FROM `tabPage` WHERE name = '{page}'")
		frappe.db.sql(f"DELETE FROM `tabPage Link` WHERE parent = '{page}'")
		print(f"Deleted Page: {page}")
	except Exception as e:
		print(f"Error deleting {page}: {e}")

frappe.db.commit()
print("Cleanup complete!")
