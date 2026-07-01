frappe.provide("frappe.listview_settings");

(function () {
	const settings = frappe.listview_settings["Item"] || {};

	const add_fields = settings.add_fields || [];
	for (const fieldname of [
		"is_construction_resource",
		"construction_resource_type",
		"default_cost_stream",
	]) {
		if (!add_fields.includes(fieldname)) {
			add_fields.push(fieldname);
		}
	}

	settings.add_fields = add_fields;
	settings.formatters = Object.assign({}, settings.formatters, {
		is_construction_resource(value) {
			const enabled = cint(value) ? 1 : 0;
			const label = enabled ? __("Yes") : __("No");
			return `<a class="filterable ellipsis" data-filter="is_construction_resource,=,${enabled}">
				${frappe.utils.escape_html(label)}
			</a>`;
		},
	});

	frappe.listview_settings["Item"] = settings;
})();
