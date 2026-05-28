// ViteFormConfig is attached globally via frappe.ui.form.on('*') in vite_layout_controls.js
// Do NOT call ViteFormConfig.attach(frm) here — it causes duplicate attach.
frappe.ui.form.on("BOQ Item", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("View Stages"), () => {
			frappe.set_route("List", "BOQ Item Stage", {
				boq_item: frm.doc.name,
			});
		}, __("Stages"));

		frm.add_custom_button(__("Add Stage"), () => {
			frappe.new_doc("BOQ Item Stage", {
				boq_item: frm.doc.name,
			});
		}, __("Stages"));
	},
});
