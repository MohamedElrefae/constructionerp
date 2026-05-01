import frappe

frappe.init("construction.local")
frappe.connect()
doctypes = frappe.get_all("DocType", filters={"module": "construction"}, fields=["name", "app_name"])
for d in doctypes:
	print(f"{d.name} -> {d.app_name}")
frappe.destroy()
