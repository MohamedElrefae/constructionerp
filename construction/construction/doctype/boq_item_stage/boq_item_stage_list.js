frappe.listview_settings["BOQ Item Stage"] = {
	add_fields: [
		"stage_status",
		"planned_qty",
		"measured_executed_qty",
		"certified_qty",
		"percent_complete",
	],

	get_indicator(doc) {
		if (doc.stage_status === "Certified" || flt(doc.certified_qty) > 0) {
			return [__("Certified"), "green", "stage_status,=,Certified"];
		}
		if (flt(doc.measured_executed_qty) > flt(doc.planned_qty)) {
			return [__("Over Measured"), "orange", "measured_executed_qty,>,planned_qty"];
		}
		if (doc.stage_status === "Completed" || flt(doc.percent_complete) >= 100) {
			return [__("Completed"), "blue", "stage_status,=,Completed"];
		}
		if (doc.stage_status === "On Hold") {
			return [__("On Hold"), "gray", "stage_status,=,On Hold"];
		}
		if (doc.stage_status === "In Progress" || flt(doc.measured_executed_qty) > 0) {
			return [__("In Progress"), "blue", "stage_status,=,In Progress"];
		}
		return [__("Not Started"), "gray", "stage_status,=,Not Started"];
	},
};
