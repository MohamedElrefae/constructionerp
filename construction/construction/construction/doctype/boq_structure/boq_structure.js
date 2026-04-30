frappe.ui.form.on("BOQ Structure", {
	onload: function (frm) {
		frm.set_query("parent_structure", function () {
			return {
				filters: {
					boq_header: frm.doc.boq_header,
					is_group: 1,
				},
			};
		});
	},
	refresh: function (frm) {
		frm.toggle_enable(["boq_header"], frm.doc.__islocal);

		let intro_txt = "";
		if (!frm.doc.__islocal && frm.doc.is_group == 1) {
			intro_txt += __("Note: This is a Group node. BOQ Items are not created for groups.");
		}
		frm.set_intro(intro_txt);

		frm.events.hide_unhide_group_ledger(frm);

		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("BOQ Structure Tree"), function () {
				frappe.set_route("Tree", "BOQ Structure", {
					boq_header: frm.doc.boq_header,
				});
			});
		}
	},
	hide_unhide_group_ledger: function (frm) {
		if (frm.doc.__islocal) return;
		if (frm.doc.is_group == 1) {
			frm.add_custom_button(__("Convert to Non-Group"), () =>
				frm.events.convert_to_ledger(frm)
			);
		} else if (frm.doc.is_group == 0) {
			frm.add_custom_button(__("Convert to Group"), () => frm.events.convert_to_group(frm));
		}
	},
	convert_to_group: function (frm) {
		frm.call("convert_ledger_to_group").then((r) => {
			if (r.message === 1) {
				frm.refresh();
			}
		});
	},
	convert_to_ledger: function (frm) {
		frm.call("convert_group_to_ledger").then((r) => {
			if (r.message === 1) {
				frm.refresh();
			}
		});
	},
});
