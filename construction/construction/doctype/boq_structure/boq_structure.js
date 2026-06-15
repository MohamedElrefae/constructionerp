(function () {
	function setFieldInlineHint(frm, fieldname, hint, blocked) {
		const $wrapper = $(`.frappe-control[data-fieldname="${fieldname}"]`);
		if (!$wrapper.length) return;
		const $help = $wrapper.find(".help").first();
		if (!$help.length) return;
		$wrapper.toggleClass("ct-boq-has-inline-hint", !!hint);
		$wrapper.toggleClass("ct-boq-inline-hint-blocked", !!blocked);
		$help.find(".ct-boq-inline-hint").remove();
		if (hint) {
			$help.append(
				$("<span>", {
					class: "ct-boq-inline-hint",
					text: hint,
					title: hint,
				}),
			);
		}
	}

	function applyBoqGuidance(frm) {
		const hasHeader = Boolean(frm.doc.boq_header);
		const isBlocked = !hasHeader;

		setFieldInlineHint(
			frm,
			"boq_header",
			hasHeader ? null : __("Select BOQ Header first"),
			false,
		);
		setFieldInlineHint(
			frm,
			"parent_structure",
			hasHeader ? null : __("Select BOQ Header first"),
			isBlocked,
		);

		const $boq_header = $(`.frappe-control[data-fieldname="boq_header"]`);
		if ($boq_header.length) {
			$boq_header.toggleClass("ct-boq-step-accent", isBlocked);
		}

		const $parent_structure = $(`.frappe-control[data-fieldname="parent_structure"]`);
		if ($parent_structure.length) {
			$parent_structure.toggleClass("ct-boq-step-blocked", isBlocked);
		}

		const psField = frm.fields_dict && frm.fields_dict.parent_structure;
		if (psField) {
			psField.__ct_boq_blocked = isBlocked;
			psField.df.only_select = isBlocked;
			psField.df.filter_description = isBlocked ? __("Select BOQ Header first") : "";
			if (typeof psField.set_description === "function") {
				psField.set_description(isBlocked ? __("Select BOQ Header first") : "");
			}
		}
	}

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
			applyBoqGuidance(frm);

			let intro_txt = "";
			if (!frm.doc.__islocal && frm.doc.is_group == 1) {
				intro_txt += __(
					"Note: This is a Group node. BOQ Items are not created for groups.",
				);
			}
			frm.set_intro(intro_txt);

			frm.events.hide_unhide_group_ledger(frm);

			if (!frm.doc.__islocal) {
				frm.add_custom_button(
					__("Variation Orders"),
					function () {
						frappe.set_route("List", "Variation Order", {
							boq_header: frm.doc.boq_header,
						});
					},
					__("View"),
				);

				frm.add_custom_button(
					__("BOQ Structure Tree"),
					function () {
						frappe.set_route("Tree", "BOQ Structure", {
							boq_header: frm.doc.boq_header,
						});
					},
					__("View"),
				);

				frm.add_custom_button(
					__("Export to Excel"),
					function () {
						frappe.call({
							method: "construction.api.boq_api.export_boq_excel",
							args: { boq_header: frm.doc.boq_header },
							callback(r) {
								if (r.message && r.message.file_url) {
									window.open(r.message.file_url);
								}
							},
						});
					},
					__("Export"),
				);

				frm.add_custom_button(
					__("Export to PDF"),
					function () {
						frappe.call({
							method: "construction.api.boq_api.export_boq_pdf",
							args: { boq_header: frm.doc.boq_header },
							callback(r) {
								if (r.message && r.message.file_url) {
									window.open(r.message.file_url);
								}
							},
						});
					},
					__("Export"),
				);

				frm.add_custom_button(
					__("Print"),
					function () {
						frappe.set_route("print", "BOQ Header", frm.doc.boq_header);
					},
					__("Export"),
				);
			}
		},

		boq_header: function (frm) {
			applyBoqGuidance(frm);
		},

		onload_post_render: function (frm) {
			applyBoqGuidance(frm);
			setTimeout(function () {
				applyBoqGuidance(frm);
			}, 150);
			setTimeout(function () {
				applyBoqGuidance(frm);
			}, 600);
		},

		hide_unhide_group_ledger: function (frm) {
			if (frm.doc.__islocal) return;
			if (frm.doc.is_group == 1) {
				frm.add_custom_button(__("Convert to Non-Group"), () =>
					frm.events.convert_to_ledger(frm),
				);
			} else if (frm.doc.is_group == 0) {
				frm.add_custom_button(__("Convert to Group"), () =>
					frm.events.convert_to_group(frm),
				);
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
})();
