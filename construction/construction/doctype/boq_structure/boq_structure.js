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
				})
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
			false
		);
		setFieldInlineHint(
			frm,
			"parent_structure",
			hasHeader ? null : __("Select BOQ Header first"),
			isBlocked
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
			// Signal to generic_export_menu.js that this page has its own export menu.
			// frm-instance property (not window) prevents bleed across navigations.
			frm.__ct_has_manual_export = true;

			frm.toggle_enable(["boq_header"], frm.doc.__islocal);
			applyBoqGuidance(frm);

			let intro_txt = "";
			if (!frm.doc.__islocal && frm.doc.is_group == 1) {
				intro_txt += __(
					"Note: This is a Group node. BOQ Items are not created for groups."
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
					__("View")
				);

				frm.add_custom_button(
					__("BOQ Structure Tree"),
					function () {
						frappe.set_route("Tree", "BOQ Structure", {
							boq_header: frm.doc.boq_header,
						});
					},
					__("View")
				);

				// ── Export Menu (ConstructionExportMenu dropdown) ──
				// M4: Columns from shared module (boq_export_columns.js) — single source of truth.
				var BOQ_FULL_COLUMNS = window.BOQ_EXPORT_COLUMNS.full();

				var make_boq_export_callback = function (method, success_msg) {
					return function (column_config) {
						return new Promise(function (resolve, reject) {
							frappe.call({
								method: method,
								args: {
									boq_header: frm.doc.boq_header,
									column_config: JSON.stringify(column_config),
								},
								callback: function (r) {
									if (r.message && r.message.file_url) {
										window.open(r.message.file_url);
										frappe.show_alert({ message: __(success_msg), indicator: "green" });
										resolve();
									} else if (r.message && r.message.error) {
										frappe.show_alert({ message: r.message.error, indicator: "red" });
										reject(new Error(r.message.error));
									} else {
										resolve();
									}
								},
								error: function (err) { reject(err); },
							});
						});
					};
				};

				new ConstructionExportMenu(frm, [
					{
						label: __("Excel — Full BOQ"),
						icon: "fa fa-file-excel-o",
						action: function () {
							new PrintSettingsDialog({
								report_type: "BOQ_Structure_Full_Excel",
								columns: BOQ_FULL_COLUMNS,
								sample_data: [],
								export_callback: make_boq_export_callback(
									"construction.api.boq_api.export_boq_excel",
									"BOQ exported successfully"
								),
							}).show();
						},
					},
					{
						label: __("PDF — Full BOQ"),
						icon: "fa fa-file-pdf-o",
						action: function () {
							new PrintSettingsDialog({
								report_type: "BOQ_Structure_Full_PDF",
								columns: BOQ_FULL_COLUMNS,
								sample_data: [],
								export_callback: make_boq_export_callback(
									"construction.api.boq_api.export_boq_pdf",
									"BOQ PDF exported successfully"
								),
							}).show();
						},
					},
					{
						label: __("Print"),
						icon: "fa fa-print",
						separator_before: true,
						action: function () {
							frappe.set_route("print", "BOQ Header", frm.doc.boq_header);
						},
					},
				]);
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
					frm.events.convert_to_ledger(frm)
				);
			} else if (frm.doc.is_group == 0) {
				frm.add_custom_button(__("Convert to Group"), () =>
					frm.events.convert_to_group(frm)
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
