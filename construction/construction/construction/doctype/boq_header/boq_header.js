frappe.ui.form.on("BOQ Header", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				"View Tree",
				() => {
					frappe.set_route("Tree", "BOQ Structure", { boq_header: frm.doc.name });
				},
				"Actions"
			);

			frm.add_custom_button(
				"Advance Status",
				() => {
					const transitions = { Draft: "Pricing", Pricing: "Frozen", Frozen: "Locked" };
					const next = transitions[frm.doc.status];
					if (!next) {
						frappe.msgprint("BOQ is already Locked.");
						return;
					}
					frappe.confirm(`Advance status to <b>${next}</b>?`, () => {
						frappe.call({
							method: "construction.api.boq_api.advance_boq_status",
							args: { boq_header: frm.doc.name, target_status: next },
							callback(r) {
								if (r.message && r.message.success) {
									frm.reload_doc();
									frappe.show_alert({
										message: `Status → ${next}`,
										indicator: "green",
									});
								}
							},
						});
					});
				},
				"Actions"
			);

			frm.add_custom_button(
				"Export Excel",
				() => {
					frappe.call({
						method: "construction.api.boq_api.export_boq_excel",
						args: { boq_header: frm.doc.name },
						callback(r) {
							if (r.message && r.message.file_url) {
								window.open(r.message.file_url);
							}
						},
					});
				},
				"Actions"
			);

			if (frm.doc.status === "Draft") {
				frm.add_custom_button(
					"Import Excel",
					() => {
						const d = new frappe.ui.Dialog({
							title: "Import BOQ from Excel",
							fields: [
								{
									label: "Excel File",
									fieldname: "file_url",
									fieldtype: "Attach",
									reqd: 1,
								},
							],
							primary_action_label: "Import",
							primary_action(values) {
								frappe.call({
									method: "construction.api.boq_api.import_boq_excel",
									args: { file_url: values.file_url, boq_header: frm.doc.name },
									callback(r) {
										if (r.message && r.message.success) {
											d.hide();
											frm.reload_doc();
											frappe.show_alert({
												message: "Import successful",
												indicator: "green",
											});
										}
									},
								});
							},
						});
						d.show();
					},
					"Actions"
				);
			}
		}
	},
});
