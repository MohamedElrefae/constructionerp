// PrintSettingsDialog, ColumnConfigManager, PreviewPanel are registered globally via hooks.py
// ConstructionExportMenu, ConstructionViewMenu are registered globally via bundle
// ViteFormConfig is attached globally via frappe.ui.form.on('*') in vite_layout_controls.js
// Do NOT call ViteFormConfig.attach(frm) here — it causes duplicate attach.

(function () {
	// NOTE: Project on BOQ Header is hidden by design — it is sourced exclusively
	// from Scope Context (server-validated in boq_header.py). Accent/pill guidance
	// therefore does not apply to this form; see USER_GUIDE §6.2.

	function getScopeProject() {
		return window.scopeContext && window.scopeContext.enabled
			? window.scopeContext.getValidatedCurrentScope().project || null
			: null;
	}

	function syncProjectFromScope(frm) {
		const scopeProject = getScopeProject();
		if (!frm.doc.project && scopeProject) {
			frm.set_value("project", scopeProject);
			return;
		}

		if (!frm.doc.project && frm.doc.project_name) {
			frm.set_value("project_name", "");
		}
	}

	function applyProjectGuidance(frm) {
		const projectField = frm.get_field && frm.get_field("project");
		if (projectField && projectField.$wrapper) {
			projectField.$wrapper.hide();
		}

		const scopeProject = getScopeProject();
		if (scopeProject && frm.is_new() && frm.doc.project !== scopeProject) {
			frm.set_value("project", scopeProject);
		}
	}

	function syncProjectName(frm) {
		if (!frm.doc.project) {
			if (frm.doc.project_name) {
				frm.set_value("project_name", "");
			}
			return;
		}

		frappe.call({
			method: "construction.api.scope_context_api.get_project_display_name",
			args: {
				project: frm.doc.project,
			},
			callback(r) {
				const projectName = r?.message?.project_name || frm.doc.project;
				if (frm.doc.project_name !== projectName) {
					frm.set_value("project_name", projectName);
				}
			},
		});
	}

	function renderTreeSummary(frm) {
		return;
	}

	frappe.ui.form.on("BOQ Header", {
		refresh(frm) {
			syncProjectFromScope(frm);
			syncProjectName(frm);
			if (!frm.is_new()) {
				render_vo_summary(frm);
				renderTreeSummary(frm);
				var BOQ_FULL_COLUMNS = [
					{
						field_key: "wbs_code",
						label: __("WBS Code"),
						default_width: 12,
						default_visible: true,
						default_sort_order: 0,
					},
					{
						field_key: "title",
						label: __("Title / Description"),
						default_width: 30,
						default_visible: true,
						default_sort_order: 1,
					},
					{
						field_key: "type",
						label: __("Type"),
						default_width: 6,
						default_visible: true,
						default_sort_order: 2,
					},
					{
						field_key: "unit",
						label: __("Unit"),
						default_width: 5,
						default_visible: true,
						default_sort_order: 3,
					},
					{
						field_key: "quantity",
						label: __("Quantity"),
						default_width: 8,
						default_visible: true,
						default_sort_order: 4,
					},
					{
						field_key: "contract_unit_price",
						label: __("Unit Price"),
						default_width: 10,
						default_visible: true,
						default_sort_order: 5,
					},
					{
						field_key: "factor",
						label: __("Factor"),
						default_width: 5,
						default_visible: true,
						default_sort_order: 6,
					},
					{
						field_key: "line_total",
						label: __("Line Total"),
						default_width: 10,
						default_visible: true,
						default_sort_order: 7,
					},
					{
						field_key: "owner_ref_no",
						label: __("Ref"),
						default_width: 9,
						default_visible: true,
						default_sort_order: 8,
					},
					{
						field_key: "owner_page",
						label: __("Owner Page"),
						default_width: 5,
						default_visible: false,
						default_sort_order: 9,
					},
					{
						field_key: "owner_file_ref",
						label: __("File Ref"),
						default_width: 5,
						default_visible: false,
						default_sort_order: 10,
					},
				];

				var BOQ_HEADER_COLUMNS = [
					{
						field_key: "name",
						label: __("BOQ ID"),
						default_width: 15,
						default_visible: true,
						default_sort_order: 0,
					},
					{
						field_key: "title",
						label: __("Title"),
						default_width: 20,
						default_visible: true,
						default_sort_order: 1,
					},
					{
						field_key: "project_name",
						label: __("Project"),
						default_width: 20,
						default_visible: true,
						default_sort_order: 2,
					},
					{
						field_key: "boq_type",
						label: __("BOQ Type"),
						default_width: 10,
						default_visible: true,
						default_sort_order: 3,
					},
					{
						field_key: "status",
						label: __("Status"),
						default_width: 10,
						default_visible: true,
						default_sort_order: 4,
					},
					{
						field_key: "version",
						label: __("Version"),
						default_width: 8,
						default_visible: true,
						default_sort_order: 5,
					},
					{
						field_key: "total_contract_value",
						label: __("Total Contract Value"),
						default_width: 15,
						default_visible: true,
						default_sort_order: 6,
					},
					{
						field_key: "total_budgeted_cost",
						label: __("Total Budgeted Cost"),
						default_width: 15,
						default_visible: true,
						default_sort_order: 7,
					},
					{
						field_key: "created_on",
						label: __("Created On"),
						default_width: 12,
						default_visible: false,
						default_sort_order: 8,
					},
					{
						field_key: "modified_on",
						label: __("Modified On"),
						default_width: 12,
						default_visible: false,
						default_sort_order: 9,
					},
				];

				// ── Helper: build export callback for frappe.call ──
				var make_export_callback = function (method, args_fn, success_msg) {
					return function (column_config) {
						return new Promise(function (resolve, reject) {
							frappe.call({
								method: method,
								args: args_fn(column_config),
								callback(r) {
									if (r.message && r.message.file_url) {
										window.open(r.message.file_url);
										frappe.show_alert({
											message: success_msg,
											indicator: "green",
										});
										resolve();
									} else if (r.message && r.message.error) {
										frappe.show_alert({
											message: r.message.error,
											indicator: "red",
										});
										reject(new Error(r.message.error));
									} else {
										resolve();
									}
								},
								error: function (err) {
									reject(err);
								},
							});
						});
					};
				};

				var header_args = function (column_config) {
					return {
						boq_header: frm.doc.name,
						column_config: JSON.stringify(column_config),
					};
				};

				var header_sample_data = [
					{
						project_name: frm.doc.project_name || "",
						boq_number: frm.doc.name || "",
						revision: frm.doc.revision || "",
						status: frm.doc.status || "",
						total_value: frm.doc.total_value || 0,
					},
				];

				// ── View Menu (standalone button with Tree / Table options) ──
				new ConstructionViewMenu(
					frm,
					[
						{
							label: __("Tree View"),
							icon: "fa fa-sitemap",
							value: "tree",
							action: function () {
								frappe.set_route("Tree", "BOQ Structure", {
									boq_header: frm.doc.name,
								});
							},
						},
						{
							label: __("Table View"),
							icon: "fa fa-table",
							value: "table",
							action: function () {
								frappe.set_route("List", "BOQ Structure", {
									boq_header: frm.doc.name,
								});
							},
						},
					],
					"tree"
				);

				// ── Export Menu (standalone dropdown with icon) ──
				new ConstructionExportMenu(frm, [
					{
						label: __("Excel - Header Only"),
						icon: "fa fa-file-excel-o",
						action: function () {
							new PrintSettingsDialog({
								report_type: "BOQ_Header_Excel",
								columns: BOQ_HEADER_COLUMNS,
								sample_data: header_sample_data,
								export_callback: make_export_callback(
									"construction.api.boq_api.export_boq_header_excel",
									header_args,
									"Header exported successfully"
								),
							}).show();
						},
					},
					{
						label: __("Excel - Full BOQ"),
						icon: "fa fa-file-excel-o",
						action: function () {
							new PrintSettingsDialog({
								report_type: "BOQ_Full_Excel",
								columns: BOQ_FULL_COLUMNS,
								sample_data: [],
								export_callback: make_export_callback(
									"construction.api.boq_api.export_boq_excel",
									header_args,
									"BOQ exported successfully"
								),
							}).show();
						},
					},
					{
						label: __("PDF - Header Only"),
						icon: "fa fa-file-pdf-o",
						separator_before: true,
						action: function () {
							new PrintSettingsDialog({
								report_type: "BOQ_Header_PDF",
								columns: BOQ_HEADER_COLUMNS,
								sample_data: header_sample_data,
								export_callback: make_export_callback(
									"construction.api.boq_api.export_boq_header_pdf",
									header_args,
									"Header PDF exported successfully"
								),
							}).show();
						},
					},
					{
						label: __("PDF - Full BOQ"),
						icon: "fa fa-file-pdf-o",
						action: function () {
							new PrintSettingsDialog({
								report_type: "BOQ_Full_PDF",
								columns: BOQ_FULL_COLUMNS,
								sample_data: [],
								export_callback: make_export_callback(
									"construction.api.boq_api.export_boq_pdf",
									header_args,
									"BOQ PDF exported successfully"
								),
							}).show();
						},
					},
					{
						label: __("Print - Header Only"),
						icon: "fa fa-print",
						separator_before: true,
						action: function () {
							frappe.set_route("print", "BOQ Header", frm.doc.name);
						},
					},
					{
						label: __("Print - Full BOQ"),
						icon: "fa fa-print",
						action: function () {
							frappe.call({
								method: "construction.api.boq_api.export_boq_pdf",
								args: { boq_header: frm.doc.name },
								freeze: true,
								freeze_message: "Generating Full BOQ PDF...",
								callback(r) {
									if (r.message && r.message.file_url) {
										var printWindow = window.open(r.message.file_url);
										if (printWindow) {
											printWindow.onload = function () {
												printWindow.print();
											};
										}
										frappe.show_alert({
											message: "Full BOQ PDF ready",
											indicator: "green",
										});
									} else if (r.message && r.message.error) {
										frappe.show_alert({
											message: r.message.error,
											indicator: "red",
										});
									}
								},
							});
						},
					},
				]);

				// ── Actions group (non-export actions only) ──
				frm.add_custom_button(
					__("Advance Status"),
					() => {
						const transitions = {
							Draft: "Pricing",
							Pricing: "Frozen",
							Frozen: "Locked",
						};
						const next = transitions[frm.doc.status];
						if (!next) {
							frappe.msgprint(__("BOQ is already Locked."));
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
											message: `Status \u2192 ${next}`,
											indicator: "green",
										});
									}
								},
							});
						});
					},
					__("Actions")
				);

				if (frm.doc.status === "Draft") {
					frm.add_custom_button(
						__("Import Excel"),
						() => {
							// K-01 repair (F16): explicit two-step preview -> confirm flow.
							// The API defaults to dry_run=1 (preview); the old handler
							// displayed "Import successful" for an unsaved preview.
							// This dialog validates first, shows row/error counts, and
							// commits only after explicit confirmation with the
							// confirmed import mode. A busy guard prevents duplicates.
							let busy = false;
							let last_preview = null;
							let last_file_url = null;
							const d = new frappe.ui.Dialog({
								title: __("Import BOQ from Excel"),
								fields: [
									{
										label: __("Excel File"),
										fieldname: "file_url",
										fieldtype: "Attach",
										reqd: 1,
									},
									{
										label: __("Import Mode"),
										fieldname: "import_mode",
										fieldtype: "Select",
										// F36-D003: options stay English enum codes on purpose.
										// They were translated for F22, but confirmed_import_mode
										// must be one of IMPORT_MODES ("Structured", …) and the
										// round-trip broke: the API returns English while the
										// control only accepted Arabic, so Confirm Import died on
										// empty mode. The Arabic description below explains the choice.
										options: ["Structured", "Semi-Structured", "Flat"],
										description: __(
											"Confirm the detected workbook layout before committing."
										),
										depends_on: "eval:doc.__show_commit",
									},
									{
										fieldname: "result_html",
										fieldtype: "HTML",
									},
								],
								primary_action_label: __("Validate"),
								primary_action(values) {
									if (busy) return;
									if (!values.file_url) {
										frappe.msgprint(__("Please attach an Excel file first."));
										return;
									}
									if (!d.__confirm_armed) {
										run_preview(values.file_url);
									} else {
										run_commit(values.file_url, values.import_mode);
									}
								},
							});

							// F36-D003: frappe.ui.Dialog does not initialise `doc`, so the
							// `depends_on: "eval:doc.__show_commit"` gate and every direct
							// `d.doc.__show_commit = …` assignment below threw
							// ("Cannot set properties of undefined") inside the preview
							// callback — after the API answered 200 — leaving the dialog
							// stuck on "Validating…" with the preview never rendered.
							// Initialise the backing object once, here.
							d.doc = d.doc || {};
							(d.doc = d.doc || {}).__show_commit = false;

							function set_result($node) {
								d.fields_dict.result_html.$wrapper.empty().append($node);
							}

							function show_info(text) {
								set_result($("<p>").addClass("text-muted").text(text));
							}

							function show_errors(errors) {
								const $wrap = $("<div>");
								$wrap.append(
									$("<p>")
										.addClass("text-danger")
										.text(
											__(
												"Validation found {0} blocking error(s). Fix the workbook and validate again. No records were saved.",
												[errors.length]
											)
										)
								);
								const $list = $("<ul>");
								(errors || []).slice(0, 50).forEach((e) => {
									const row = e.row_no ? `Row ${e.row_no}: ` : "";
									$list.append(
										$("<li>").text(row + (e.message || e.code || "Error"))
									);
								});
								$wrap.append($list);
								if ((errors || []).length > 50) {
									$wrap.append(
										$("<p>")
											.addClass("text-muted")
											.text(
												__(
													"Showing first 50 of {0} errors. Use the error report for the full list.",
													[errors.length]
												)
											)
									);
								}
								set_result($wrap);
							}

							function show_preview(msg) {
								const summary = msg.summary || {};
								const $wrap = $("<div>");
								$wrap.append(
									$("<p>").text(
										__(
											"Preview only — nothing saved yet. Rows: {0}, sections: {1}, items: {2}, warnings: {3}.",
											[
												summary.row_count || 0,
												summary.section_count || 0,
												summary.item_count || 0,
												(msg.warnings || []).length,
											]
										)
									)
								);
								if ((msg.warnings || []).length) {
									const $wlist = $("<ul>");
									(msg.warnings || []).slice(0, 20).forEach((w) => {
										$wlist.append(
											$("<li>").text(w.message || w.code || "Warning")
										);
									});
									$wrap.append(
										$("<p>").addClass("text-muted").text(__("Warnings:"))
									);
									$wrap.append($wlist);
								}
								$wrap.append(
									$("<p>").text(
										__(
											"Detected layout: {0}. Confirm the mode, then choose Confirm Import to save.",
											[msg.detected_import_mode || "—"]
										)
									)
								);
								set_result($wrap);
							}

							function run_preview(file_url) {
								last_file_url = file_url;
								busy = true;
								d.get_primary_btn().prop("disabled", true);
								show_info(__("Validating workbook…"));
								frappe.call({
									method: "construction.api.boq_api.import_boq_excel",
									args: {
										file_url: file_url,
										boq_header: frm.doc.name,
										dry_run: 1,
									},
									callback(r) {
										busy = false;
										d.get_primary_btn().prop("disabled", false);
										const msg = r.message;
										if (!msg) {
											show_info(
												__(
													"Validation failed without a server response. Nothing was saved."
												)
											);
											return;
										}
										if (msg.success && !(msg.errors || []).length) {
											last_preview = msg;
											d.set_value("import_mode", msg.detected_import_mode);
											d.__confirm_armed = true;
											(d.doc = d.doc || {}).__show_commit = true;
											d.refresh();
											// F36-D003: d.refresh() rebuilds the fields and drops staged
											// values that live only in the controls, not in doc, so
											// Confirm Import would die on mandatory validation
											// ("missing: Excel File") or on empty mode. Restore both.
											d.set_value("file_url", file_url);
											d.set_value("import_mode", msg.detected_import_mode);
											show_preview(msg);
											d.set_primary_action(
												__("Confirm Import"),
												d.primary_action
											);
										} else {
											show_errors(
												msg.errors || [
													{
														message:
															msg.error || __("Validation failed."),
													},
												]
											);
										}
									},
									error() {
										busy = false;
										d.get_primary_btn().prop("disabled", false);
										show_info(
											__("Validation request failed. Nothing was saved.")
										);
									},
								});
							}

							function run_commit(file_url, import_mode) {
								if (!last_preview || file_url !== last_file_url) {
									last_preview = null;
									d.__confirm_armed = false;
									(d.doc = d.doc || {}).__show_commit = false;
									d.refresh();
									d.set_primary_action(__("Validate"), d.primary_action);
									show_info(
										__(
											"The file changed since validation. Validate again before confirming import."
										)
									);
									return;
								}
								if (!import_mode) {
									frappe.msgprint(__("Please confirm the import mode."));
									return;
								}
								busy = true;
								d.get_primary_btn().prop("disabled", true);
								show_info(__("Committing import…"));
								frappe.call({
									method: "construction.api.boq_api.import_boq_excel",
									args: {
										file_url: file_url,
										boq_header: frm.doc.name,
										dry_run: 0,
										confirmed_import_mode: import_mode,
									},
									callback(r) {
										busy = false;
										d.get_primary_btn().prop("disabled", false);
										const msg = r.message;
										if (msg && msg.success && msg.dry_run === false) {
											if (msg.duplicate_suppressed) {
												const n_items =
													(msg.summary || {}).item_count || 0;
												d.hide();
												frm.reload_doc();
												frappe.show_alert({
													message: __(
														"Already imported: this file is recorded under batch {0} ({1} items). No duplicates created.",
														[msg.import_batch || "—", n_items]
													),
													indicator: "blue",
												});
											} else {
												const n_items = (msg.created_items || []).length;
												const n_struct = (msg.created_structures || [])
													.length;
												d.hide();
												frm.reload_doc();
												frappe.show_alert({
													message: __(
														"Imported {0} items in {1} structures (batch {2}).",
														[
															n_items,
															n_struct,
															msg.import_batch || "—",
														]
													),
													indicator: "green",
												});
											}
										} else {
											show_errors(
												(msg && msg.errors) || [
													{
														message:
															(msg && msg.error) ||
															__("Import failed."),
													},
												]
											);
											d.__confirm_armed = false;
											(d.doc = d.doc || {}).__show_commit = false;
											d.refresh();
											d.set_primary_action(__("Validate"), d.primary_action);
										}
									},
									error() {
										busy = false;
										d.get_primary_btn().prop("disabled", false);
										show_info(
											__(
												"Import request failed. Verify saved records before retrying; do not blindly repeat."
											)
										);
									},
								});
							}

							d.show();
						},
						__("Actions")
					);
				}

				// ── Variation Orders ──
				frm.add_custom_button(
					__("Variation Orders"),
					() => {
						frappe.set_route("List", "Variation Order", { boq_header: frm.doc.name });
					},
					__("Actions")
				);

				frappe.call({
					method: "construction.api.boq_api.is_variation_orders_enabled",
					callback(r) {
						const flag_on = r.message && r.message.enabled === true;
						if (!flag_on || frm.doc.status !== "Locked") {
							return;
						}
						frm.add_custom_button(
							__("New Variation Order"),
							() => open_new_vo_dialog(frm),
							__("Actions")
						);
					},
				});

				frm.add_custom_button(
					__("Revised BOQ View"),
					() => open_revised_boq_dialog(frm),
					__("Actions")
				);
			}
			applyProjectGuidance(frm);
		},
		onload_post_render(frm) {
			syncProjectFromScope(frm);
			syncProjectName(frm);
			applyProjectGuidance(frm);
			$(document)
				.off("scope:changed.boqHeader")
				.on("scope:changed.boqHeader", function () {
					syncProjectFromScope(frm);
					syncProjectName(frm);
					applyProjectGuidance(frm);
				});
			setTimeout(() => applyProjectGuidance(frm), 150);
			setTimeout(() => applyProjectGuidance(frm), 600);
		},
		project(frm) {
			syncProjectName(frm);
			applyProjectGuidance(frm);
		},
	});

	function open_new_vo_dialog(frm) {
		const d = new frappe.ui.Dialog({
			title: __("New Variation Order for {0}", [frm.doc.name]),
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Reason"),
					reqd: 1,
				},
				{
					fieldname: "description",
					fieldtype: "Small Text",
					label: __("Description"),
				},
				{
					fieldname: "engineer_name",
					fieldtype: "Data",
					label: __("Engineer Name"),
				},
			],
			primary_action_label: __("Create Draft VO"),
			primary_action(values) {
				frappe.call({
					method: "construction.api.boq_api.create_variation_order",
					args: {
						boq_header: frm.doc.name,
						reason: values.reason,
						description: values.description,
						engineer_name: values.engineer_name,
					},
					freeze: true,
					freeze_message: __("Creating Variation Order..."),
					callback(r) {
						if (r.message && r.message.success) {
							d.hide();
							frappe.show_alert({
								message: __("Created {0}", [
									r.message.vo_number || r.message.name,
								]),
								indicator: "green",
							});
							frappe.set_route("Form", "Variation Order", r.message.name);
						} else if (r.message && r.message.error) {
							frappe.msgprint({
								title: __("Could not create VO"),
								message: r.message.error,
								indicator: "red",
							});
						}
					},
				});
			},
		});
		d.show();
	}

	function render_vo_summary(frm) {
		if (!frm.doc.name) return;
		frappe.call({
			method: "construction.api.boq_api.get_variation_order_summary",
			args: { boq_header: frm.doc.name },
			callback(r) {
				const by_status = (r.message && r.message.by_status) || {};
				const keys = Object.keys(by_status);
				if (!keys.length) return;
				const currency = frappe.defaults.get_default("currency") || "EGP";
				keys.forEach((status) => {
					const rec = by_status[status];
					if (!rec || !rec.count) return;
					const total = flt(rec.total_delta);
					const label = total
						? __("{0} VOs ({1}) — Δ {2}", [
								rec.count,
								status,
								format_currency(total, currency),
						  ])
						: __("{0} VOs ({1})", [rec.count, status]);
					const indicator =
						status === "Approved by Client"
							? "green"
							: status === "Rejected"
							? "red"
							: status === "Draft"
							? "gray"
							: "blue";
					frm.dashboard.add_indicator(label, indicator);
				});
			},
		});
	}

	function open_revised_boq_dialog(frm) {
		frappe.call({
			method: "construction.api.boq_api.get_revised_boq_view",
			args: { boq_header: frm.doc.name },
			freeze: true,
			freeze_message: __("Loading revised BOQ view..."),
			callback(r) {
				const data = r.message || {};
				const contract_rows = data.contract_rows || [];
				const variation_rows = data.variation_rows || [];
				if (!contract_rows.length && !variation_rows.length) {
					frappe.msgprint({
						title: __("No Data"),
						message: __("No BOQ items found for this header."),
						indicator: "blue",
					});
					return;
				}
				const currency =
					frm.doc.currency || frappe.defaults.get_default("currency") || "EGP";
				let html = `<table class="table table-bordered table-hover">
				<thead><tr>
					<th>${__("WBS")}</th>
					<th>${__("Title")}</th>
					<th>${__("Contract Qty")}</th>
					<th>${__("VO Delta")}</th>
					<th>${__("Revised Qty")}</th>
					<th>${__("Unit Price")}</th>
					<th>${__("Contract Value")}</th>
					<th>${__("VO Δ Value")}</th>
					<th>${__("Revised Value")}</th>
				</tr></thead><tbody>`;
				let total_contract = 0,
					total_vo = 0,
					total_revised = 0;
				contract_rows.forEach((row) => {
					const cv = flt(row.contract_line_value);
					const vd = flt(row.vo_value_delta);
					const rv = flt(row.revised_value);
					total_contract += cv;
					total_vo += vd;
					total_revised += rv;
					html += `<tr>
					<td>${row.wbs_code || ""}</td>
					<td>${row.title || ""}</td>
					<td class="text-right">${format_number(row.contract_qty, null, 2)}</td>
					<td class="text-right">${format_number(row.vo_qty_delta, null, 2)}</td>
					<td class="text-right">${format_number(row.revised_qty, null, 2)}</td>
					<td class="text-right">${format_currency(row.contract_unit_price, currency)}</td>
					<td class="text-right">${format_currency(cv, currency)}</td>
					<td class="text-right">${format_currency(vd, currency)}</td>
					<td class="text-right">${format_currency(rv, currency)}</td>
				</tr>`;
				});
				if (variation_rows.length) {
					html += `<tr><td colspan="9"><strong>${__(
						"Variation Items (from approved VOs)"
					)}</strong></td></tr>`;
					variation_rows.forEach((row) => {
						const rv = flt(row.revised_line_value);
						total_revised += rv;
						html += `<tr>
						<td>${row.wbs_code || ""}</td>
						<td>${row.title || ""} <span class="text-muted">(${__("VO Item")})</span></td>
						<td class="text-right">—</td>
						<td class="text-right">${format_number(row.delta_qty, null, 2)}</td>
						<td class="text-right">${format_number(row.delta_qty, null, 2)}</td>
						<td class="text-right">${format_currency(row.revised_unit_price, currency)}</td>
						<td class="text-right">—</td>
						<td class="text-right">${format_currency(rv, currency)}</td>
						<td class="text-right">${format_currency(rv, currency)}</td>
					</tr>`;
					});
				}
				html += `</tbody>
				<tfoot><tr>
					<th colspan="6" class="text-right">${__("Totals")}</th>
					<th class="text-right">${format_currency(total_contract, currency)}</th>
					<th class="text-right">${format_currency(total_vo, currency)}</th>
					<th class="text-right">${format_currency(total_revised, currency)}</th>
				</tr></tfoot>
			</table>`;
				const d = new frappe.ui.Dialog({
					title: __("Revised BOQ — {0}", [frm.doc.name]),
					width: 900,
					fields: [
						{
							fieldname: "html_content",
							fieldtype: "HTML",
							options: html,
						},
					],
				});
				d.show();
			},
		});
	}
})();
