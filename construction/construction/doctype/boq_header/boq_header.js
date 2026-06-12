// PrintSettingsDialog, ColumnConfigManager, PreviewPanel are registered globally via hooks.py
// ConstructionExportMenu, ConstructionViewMenu are registered globally via bundle
// ViteFormConfig is attached globally via frappe.ui.form.on('*') in vite_layout_controls.js
// Do NOT call ViteFormConfig.attach(frm) here — it causes duplicate attach.

(function () {
	function setFieldAccent(frm, fieldname, active, blocked) {
		const $wrapper = $(`.frappe-control[data-fieldname="${fieldname}"]`);
		if (!$wrapper.length) return;
		$wrapper.toggleClass("ct-boq-step-accent", !!active);
		$wrapper.toggleClass("ct-boq-step-blocked", !!blocked);
	}

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

	function getScopeProject() {
		return window.scopeContext?.enabled ? window.scopeContext?.current?.project || null : null;
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
		if (!frm.doc.name) return;
		frappe.call({
			method: "construction.api.boq_api.get_boq_tree_summary",
			args: { boq_header: frm.doc.name },
			callback(r) {
				const nodes = r.message || [];
				if (!nodes.length) return;
				let html = '<div class="ct-boq-tree-summary" style="margin-top:16px;padding:12px;background:var(--ct-bg-2,#1a2332);border-radius:6px;border:1px solid var(--ct-border,rgba(148,163,184,0.12))">';
				html += '<h6 style="margin:0 0 8px;color:var(--ct-text-muted,#64748b);font-size:11px;text-transform:uppercase">' + __("WBS Tree") + '</h6>';
				nodes.forEach((n) => {
					const indent = Math.max(0, (n.lft > 0 ? Math.floor(Math.log2(n.rgt - n.lft + 1)) : 0)) * 16;
					const icon = n.is_group ? "📁" : "📄";
					const count = n.item_count ? ' <span style="color:var(--ct-accent,#3b82f6);font-size:11px">(' + n.item_count + ' items)</span>' : '';
					html += '<div style="padding:3px 0;padding-left:' + indent + 'px;font-size:12px">' + icon + ' <b>' + (n.wbs_code || '-') + '</b> ' + (n.title || n.name) + count + '</div>';
				});
				html += '</div>';
				const $page = frm.$wrapper.find(".form-page:visible").first();
				const $existing = $page.find(".ct-boq-tree-summary");
				if ($existing.length) $existing.replaceWith(html);
				else $page.find(".form-layout").first().after(html);
			},
		});
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
					label: "WBS Code",
					default_width: 12,
					default_visible: true,
					default_sort_order: 0,
				},
				{
					field_key: "title",
					label: "Title / Description",
					default_width: 30,
					default_visible: true,
					default_sort_order: 1,
				},
				{
					field_key: "type",
					label: "Type",
					default_width: 6,
					default_visible: true,
					default_sort_order: 2,
				},
				{
					field_key: "unit",
					label: "Unit",
					default_width: 5,
					default_visible: true,
					default_sort_order: 3,
				},
				{
					field_key: "quantity",
					label: "Quantity",
					default_width: 8,
					default_visible: true,
					default_sort_order: 4,
				},
				{
					field_key: "contract_unit_price",
					label: "Unit Price",
					default_width: 10,
					default_visible: true,
					default_sort_order: 5,
				},
				{
					field_key: "factor",
					label: "Factor",
					default_width: 5,
					default_visible: true,
					default_sort_order: 6,
				},
				{
					field_key: "line_total",
					label: "Line Total",
					default_width: 10,
					default_visible: true,
					default_sort_order: 7,
				},
				{
					field_key: "owner_ref_no",
					label: "Ref",
					default_width: 9,
					default_visible: true,
					default_sort_order: 8,
				},
				{
					field_key: "owner_page",
					label: "Owner Page",
					default_width: 5,
					default_visible: false,
					default_sort_order: 9,
				},
				{
					field_key: "owner_file_ref",
					label: "File Ref",
					default_width: 5,
					default_visible: false,
					default_sort_order: 10,
				},
			];

			var BOQ_HEADER_COLUMNS = [
				{
					field_key: "name",
					label: "BOQ ID",
					default_width: 15,
					default_visible: true,
					default_sort_order: 0,
				},
				{
					field_key: "title",
					label: "Title",
					default_width: 20,
					default_visible: true,
					default_sort_order: 1,
				},
				{
					field_key: "project_name",
					label: "Project",
					default_width: 20,
					default_visible: true,
					default_sort_order: 2,
				},
				{
					field_key: "boq_type",
					label: "BOQ Type",
					default_width: 10,
					default_visible: true,
					default_sort_order: 3,
				},
				{
					field_key: "status",
					label: "Status",
					default_width: 10,
					default_visible: true,
					default_sort_order: 4,
				},
				{
					field_key: "version",
					label: "Version",
					default_width: 8,
					default_visible: true,
					default_sort_order: 5,
				},
				{
					field_key: "total_contract_value",
					label: "Total Contract Value",
					default_width: 15,
					default_visible: true,
					default_sort_order: 6,
				},
				{
					field_key: "total_budgeted_cost",
					label: "Total Budgeted Cost",
					default_width: 15,
					default_visible: true,
					default_sort_order: 7,
				},
				{
					field_key: "created_on",
					label: "Created On",
					default_width: 12,
					default_visible: false,
					default_sort_order: 8,
				},
				{
					field_key: "modified_on",
					label: "Modified On",
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
				return { boq_header: frm.doc.name, column_config: JSON.stringify(column_config) };
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
							message: __("Created {0}", [r.message.vo_number || r.message.name]),
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
					? __("{0} VOs ({1}) — Δ {2}", [rec.count, status, format_currency(total, currency)])
					: __("{0} VOs ({1})", [rec.count, status]);
				const indicator = status === "Approved by Client"
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
			const currency = frm.doc.currency || frappe.defaults.get_default("currency") || "EGP";
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
			let total_contract = 0, total_vo = 0, total_revised = 0;
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
				html += `<tr><td colspan="9"><strong>${__("Variation Items (from approved VOs)")}</strong></td></tr>`;
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
