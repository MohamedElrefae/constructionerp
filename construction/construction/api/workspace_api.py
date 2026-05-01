import json

import frappe


def update_construction_workspace():
	"""Update the Construction workspace to show theme DocTypes"""
	ws = frappe.get_doc("Workspace", "Construction")

	# Clear existing shortcuts and links
	ws.shortcuts = []
	ws.links = []

	# Add BOQ Management section
	ws.append("links", {"type": "Card Break", "label": "BOQ Management", "hidden": 0})

	# Add BOQ links
	for doctype in ["BOQ Header", "BOQ Structure", "BOQ Item"]:
		ws.append(
			"links",
			{"type": "Link", "label": doctype, "link_to": doctype, "link_type": "DocType", "hidden": 0},
		)

	# Add Theme Settings section
	ws.append("links", {"type": "Card Break", "label": "Theme Settings", "hidden": 0})

	# Add Theme links
	for doctype in ["Construction Theme", "Modern Theme Settings"]:
		ws.append(
			"links",
			{"type": "Link", "label": doctype, "link_to": doctype, "link_type": "DocType", "hidden": 0},
		)

	# Add shortcuts
	for doctype in ["BOQ Header", "BOQ Structure", "Construction Theme", "Modern Theme Settings"]:
		ws.append(
			"shortcuts",
			{
				"label": doctype,
				"link_to": doctype,
				"type": "DocType",
				"doc_view": "List",
				"color": "Green" if "BOQ" in doctype else "Blue",
			},
		)

	# Build content JSON with shortcuts
	content = [
		{"type": "header", "data": {"text": '<span class="h4"><b>Construction ERP</b></span>', "col": 12}},
		{
			"type": "paragraph",
			"data": {"text": "BOQ Management, Cost Estimation, and Project Management", "col": 12},
		},
	]

	# Add shortcuts to content
	col = 0
	for shortcut in ws.shortcuts:
		if col >= 12:
			col = 0
		content.append({"type": "shortcut", "data": {"shortcut_name": shortcut.label, "col": 3}})
		col += 3

	ws.content = json.dumps(content)
	ws.save()
	frappe.db.commit()

	return {"status": "success", "message": "Workspace updated with all sections"}
