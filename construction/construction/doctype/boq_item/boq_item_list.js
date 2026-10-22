frappe.listview_settings["BOQ Item"] = {
	add_fields: [
		"structure",
		"boq_header",
		"item_type",
		"quantity",
		"unit",
		"contract_unit_price",
		"line_total",
	],
	get_indicator: function (doc) {
		if (doc.line_total && doc.contract_unit_price) {
			return [__("Priced"), "green", "line_total,>,"];
		}
		return [__("Unpriced"), "orange", "line_total,=,0|line_total,is,null"];
	},
	onload: function (listview) {
		listview.page.show_form();
		if (listview.page.page_form) {
			listview.page.page_form.removeClass("hide").css("display", "flex");
		}
	},
};
