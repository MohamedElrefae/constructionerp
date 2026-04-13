# Delete old DocTypes and Pages directly via SQL
# Run this via bench console

import frappe
frappe.init("construction.local")

# Connect to database
from frappe.database.mariadb import MariaDB
db = MariaDB()

# Delete old DocTypes
old_doctypes = ["LaborResource", "MaterialResource", "PlantResource", "CostItem"]
for dt in old_doctypes:
    try:
        db.sql(f"DELETE FROM `tabDocType` WHERE name = '{dt}'")
        db.sql(f"DELETE FROM `tabDocType Field` WHERE parent = '{dt}'")
        db.sql(f"DELETE FROM `tabDocType Action` WHERE parent = '{dt}'")
        db.sql(f"DELETE FROM `tabDocType Link` WHERE parent = '{dt}'")
        print(f"Deleted DocType: {dt}")
    except Exception as e:
        print(f"Error deleting {dt}: {e}")

# Delete old Pages
old_pages = ["materialresource", "plantresource", "costitem"]
for page in old_pages:
    try:
        db.sql(f"DELETE FROM `tabPage` WHERE name = '{page}'")
        db.sql(f"DELETE FROM `tabPage Link` WHERE parent = '{page}'")
        print(f"Deleted Page: {page}")
    except Exception as e:
        print(f"Error deleting {page}: {e}")

db.commit()
print("Cleanup complete!")