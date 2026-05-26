import frappe


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_headers(doctype, txt, searchfield, start, page_len, filters):
	conditions = ["docstatus < 2"]
	values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if filters and filters.get("project"):
		conditions.append("project = %(project)s")
		values["project"] = filters.get("project")

	where_clause = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT name, title, project
		FROM `tabBOQ Header`
		WHERE {where_clause}
			AND (name LIKE %(txt)s OR title LIKE %(txt)s)
		ORDER BY modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_structures(doctype, txt, searchfield, start, page_len, filters):
	conditions = ["docstatus < 2", "is_group = 0"]
	values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if filters and filters.get("boq_header"):
		conditions.append("boq_header = %(boq_header)s")
		values["boq_header"] = filters.get("boq_header")

	where_clause = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT name, title, wbs_code
		FROM `tabBOQ Structure`
		WHERE {where_clause}
			AND (name LIKE %(txt)s OR title LIKE %(txt)s OR wbs_code LIKE %(txt)s)
		ORDER BY modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_items(doctype, txt, searchfield, start, page_len, filters):
	conditions = ["i.docstatus < 2"]
	values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if filters and filters.get("project"):
		conditions.append("h.project = %(project)s")
		values["project"] = filters.get("project")

	if filters and filters.get("boq_header"):
		conditions.append("i.boq_header = %(boq_header)s")
		values["boq_header"] = filters.get("boq_header")

	if filters and filters.get("structure"):
		conditions.append("i.structure = %(structure)s")
		values["structure"] = filters.get("structure")

	if filters and filters.get("allowed_statuses"):
		conditions.append("h.status IN %(allowed_statuses)s")
		values["allowed_statuses"] = tuple(filters.get("allowed_statuses"))

	where_clause = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT i.name, h.title, i.quantity, h.project
		FROM `tabBOQ Item` i
		INNER JOIN `tabBOQ Header` h ON h.name = i.boq_header
		WHERE {where_clause}
			AND (i.name LIKE %(txt)s OR h.title LIKE %(txt)s)
		ORDER BY i.modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_boq_item_stages(doctype, txt, searchfield, start, page_len, filters):
	conditions = ["docstatus < 2"]
	values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if filters and filters.get("boq_item"):
		conditions.append("boq_item = %(boq_item)s")
		values["boq_item"] = filters.get("boq_item")

	where_clause = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT name, stage_code, stage_name, planned_qty
		FROM `tabBOQ Item Stage`
		WHERE {where_clause}
			AND (name LIKE %(txt)s OR stage_code LIKE %(txt)s OR stage_name LIKE %(txt)s)
		ORDER BY modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)
