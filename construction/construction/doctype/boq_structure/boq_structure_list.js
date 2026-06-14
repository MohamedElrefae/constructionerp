frappe.listview_settings["BOQ Structure"] = {
	add_fields: ["item_count", "total_contract_value", "total_budgeted_cost", "boq_header", "project", "parent_structure", "wbs_code"],

	onload(listview) {
		if (listview.__ct_boq_structure_columns_applied) return;
		listview.__ct_boq_structure_columns_applied = true;
		listview.list_view_settings = listview.list_view_settings || {};
		listview.list_view_settings.fields = JSON.stringify([
			{ fieldname: "title" },
			{ fieldname: "item_count" },
			{ fieldname: "total_contract_value" },
			{ fieldname: "total_budgeted_cost" },
			{ fieldname: "is_group" },
			{ fieldname: "boq_header" },
			{ fieldname: "project" },
			{ fieldname: "parent_structure" },
			{ fieldname: "wbs_code" },
		]);
		listview.refresh_columns(listview.meta, listview.list_view_settings);
	},
};
