// Variation Order list view — status indicator, standard filters, and
// feature-flag awareness.

frappe.listview_settings["Variation Order"] = {
	add_fields: ["status", "boq_header", "project", "vo_number", "total_contract_delta"],

	get_indicator(doc) {
		const status = doc.status;
		switch (status) {
			case "Draft":
				return [__("Draft"), "gray", "status,=,Draft"];
			case "Submitted":
				return [__("Submitted"), "blue", "status,=,Submitted"];
			case "Approved by Engineer":
				return [__("Engineer Approved"), "orange", "status,=,Approved by Engineer"];
			case "Approved by Client":
				return [__("Client Approved"), "green", "status,=,Approved by Client"];
			case "Rejected":
				return [__("Rejected"), "red", "status,=,Rejected"];
			default:
				return [status || "Unknown", "gray", `status,=,${status}`];
		}
	},

	formatters: {
		total_contract_delta(value) {
			const v = flt(value);
			if (!v) return "";
			const cls = v > 0 ? "text-success" : "text-danger";
			const sign = v > 0 ? "+" : "";
			return `<span class="${cls}">${sign}${format_currency(v, frappe.defaults.get_default("currency") || "EGP")}</span>`;
		},
	},

	onload(listview) {
		// Restrict the BOQ Header filter to Locked BOQs on the standard filter bar
		if (listview.page.fields_dict.boq_header) {
			listview.page.fields_dict.boq_header.get_query = () => ({
				query: "construction.api.boq_link_queries.get_boq_headers",
				filters: { allowed_statuses: ["Locked"] },
			});
		}

		// Feature flag awareness: warn the user if the rollout flag is off
		frappe.call({
			method: "construction.api.boq_api.is_variation_orders_enabled",
			callback(r) {
				if (r.message && r.message.enabled === false) {
					listview.page.set_indicator(
						__("Variation Orders are disabled by Construction Settings"),
						"orange"
					);
				}
			},
		});
	},
};
