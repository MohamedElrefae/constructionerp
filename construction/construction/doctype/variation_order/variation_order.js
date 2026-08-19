// Variation Order form — extends Frappe form with workflow actions,
// link filters, and dashboard indicators.
//
// All status changes go through the server (transition_variation_order) so
// the controller's state machine, FIDIC 25 percent rule, and signed-PDF
// gate remain authoritative.

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

	function applyVOBoqGuidance(frm) {
		const field = frm.fields_dict && frm.fields_dict.boq_header;
		if (field) {
			field.__ct_boq_blocked = false;
		}
		const hasHeader = Boolean(frm.doc.boq_header);
		setFieldAccent(frm, "boq_header", !hasHeader, false);
		setFieldInlineHint(
			frm,
			"boq_header",
			hasHeader ? null : __("Select BOQ Header first"),
			false
		);
	}

	frappe.ui.form.on("Variation Order", {
		setup(frm) {
			frm.set_query("boq_header", () => {
				const filters = { allowed_statuses: ["Locked"] };
				if (frm.doc.project) filters.project = frm.doc.project;
				return {
					query: "construction.api.boq_link_queries.get_boq_headers",
					filters,
				};
			});

			frm.set_query("boq_structure", "lines", function (doc, cdt, cdn) {
				const row = frappe.get_doc(cdt, cdn);
				if (!doc.boq_header) {
					return { filters: { name: "" } };
				}
				if (row.line_type === "New Item") {
					return { filters: { boq_header: doc.boq_header, is_group: 1 } };
				}
				return {
					query: "construction.api.boq_link_queries.get_boq_structures",
					filters: { boq_header: doc.boq_header, exclude_zero_revised: true },
				};
			});

			frm.set_query("boq_item", "lines", function (doc, cdt, cdn) {
				const row = frappe.get_doc(cdt, cdn);
				if (!doc.boq_header) {
					return { filters: { name: "" } };
				}
				const filters = {
					boq_header: doc.boq_header,
					is_variation_item: 0,
					exclude_zero_revised: true,
				};
				if (row.boq_structure) {
					filters.structure = row.boq_structure;
				}
				return {
					query: "construction.api.boq_link_queries.get_boq_items",
					filters,
				};
			});
		},

		onload(frm) {
			if (frm.is_new()) {
				frm.doc.__vo_lines_locked = false;
			}
			const scope_project =
				window.scopeContext && window.scopeContext.enabled
					? window.scopeContext.getValidatedCurrentScope().project
					: null;
			if (scope_project && !frm.doc.project) {
				frm.set_value("project", scope_project);
			}
		},

		refresh(frm) {
			apply_variation_order_status_ui(frm);
			apply_variation_order_workflow_buttons(frm);
			render_variation_order_indicators(frm);
			applyVOBoqGuidance(frm);
		},

		boq_header(frm) {
			applyVOBoqGuidance(frm);
			if (!frm.doc.boq_header) return;
			frappe.db.get_value("BOQ Header", frm.doc.boq_header, "status").then((r) => {
				const status = r?.message?.status;
				if (status && status !== "Locked" && !frm.is_new()) {
					frappe.show_alert({
						message: __(
							"BOQ Header status is {0}; VO can only be saved against Locked BOQs.",
							[status]
						),
						indicator: "orange",
					});
				}
			});
		},

		status(frm) {
			apply_variation_order_status_ui(frm);
			render_variation_order_indicators(frm);
		},
		onload_post_render(frm) {
			applyVOBoqGuidance(frm);
			setTimeout(() => applyVOBoqGuidance(frm), 150);
			setTimeout(() => applyVOBoqGuidance(frm), 600);

			$(document)
				.off("scope:changed.variationOrder")
				.on("scope:changed.variationOrder", function () {
					var new_project =
						window.scopeContext && window.scopeContext.enabled
							? window.scopeContext.getValidatedCurrentScope().project
							: null;
					if (!new_project) return;
					var current_project = frm.doc.project;
					if (new_project !== current_project) {
						frm.set_value("project", new_project);
						frm.set_value("boq_header", "");
						frm.doc.lines = [];
						frm.refresh_field("lines");
						frappe.show_alert({
							message: __(
								"Scope changed. Selected BOQ and VO lines have been cleared to prevent stale data."
							),
							indicator: "orange",
						});
					}
				});
		},
	});

	frappe.ui.form.on("VO Line", {
		line_type(frm, cdt, cdn) {
			const row = frappe.get_doc(cdt, cdn);
			// Reset link fields that don't make sense for the chosen line type
			if (row.line_type === "New Item") {
				row.boq_item = "";
			} else {
				row.title = "";
				row.unit = "";
				row.owner_page = "";
				row.owner_ref_no = "";
				row.owner_file_ref = "";
				row.revised_unit_price = 0;
			}
			row.boq_structure = "";
			frm.refresh_field("lines", cdt, cdn);
			apply_vo_line_readonly_state(frm, cdt, cdn);
		},

		boq_structure(frm, cdt, cdn) {
			const row = frappe.get_doc(cdt, cdn);
			if (row.line_type !== "New Item" && row.boq_structure) {
				// Auto-fill boq_item for existing items if boq_structure leaf is selected
				frappe.db
					.get_value("BOQ Item", { structure: row.boq_structure }, "name")
					.then((r) => {
						const item_name = r?.message?.name || "";
						if (item_name && row.boq_item !== item_name) {
							frappe.model.set_value(cdt, cdn, "boq_item", item_name);
						}
					});
			}
			apply_vo_line_readonly_state(frm, cdt, cdn);
		},

		boq_item(frm, cdt, cdn) {
			const row = frappe.get_doc(cdt, cdn);
			if (row.boq_item) {
				// Fetch all relevant data from BOQ Item
				frappe.db
					.get_value("BOQ Item", row.boq_item, [
						"structure",
						"current_revised_qty",
						"quantity",
						"contract_unit_price",
						"title",
						"unit",
					])
					.then((r) => {
						const item = r?.message || {};
						if (item.structure && !row.boq_structure) {
							frappe.model.set_value(cdt, cdn, "boq_structure", item.structure);
						}
						frappe.model.set_value(
							cdt,
							cdn,
							"previous_qty",
							item.current_revised_qty || 0
						);
						frappe.model.set_value(cdt, cdn, "contract_qty", item.quantity || 0);
						frappe.model.set_value(
							cdt,
							cdn,
							"contract_unit_price",
							item.contract_unit_price || 0
						);
						if (!row.title && item.title) {
							frappe.model.set_value(cdt, cdn, "title", item.title);
						}
						if (!row.unit && item.unit) {
							frappe.model.set_value(cdt, cdn, "unit", item.unit);
						}
					});
			}
			apply_vo_line_readonly_state(frm, cdt, cdn);
		},

		revised_qty(frm, cdt, cdn) {
			const row = frappe.get_doc(cdt, cdn);
			const previous_qty = flt(row.previous_qty);
			const contract_qty = flt(row.contract_qty);
			const revised_qty = flt(row.revised_qty);
			const delta_qty = revised_qty - previous_qty;
			const delta_from_contract = revised_qty - contract_qty;

			if (flt(row.delta_qty) !== delta_qty) {
				frappe.model.set_value(cdt, cdn, "delta_qty", delta_qty);
			}
			if (flt(row.delta_from_contract_qty) !== delta_from_contract) {
				frappe.model.set_value(cdt, cdn, "delta_from_contract_qty", delta_from_contract);
			}

			// Compute change % from contract (FIDIC rule)
			let change_pct = 0;
			if (contract_qty > 0) {
				change_pct = (Math.abs(delta_from_contract) / contract_qty) * 100;
			} else if (revised_qty > 0) {
				change_pct = 100; // New variation item
			}
			frappe.model.set_value(cdt, cdn, "change_pct_from_contract", change_pct);

			// Rate change triggered
			const rate_change = change_pct > 25 ? 1 : 0;
			frappe.model.set_value(cdt, cdn, "rate_change_triggered", rate_change);

			// If not triggered and not new item, reset unit price to contract
			if (!rate_change && row.line_type !== "New Item" && row.line_type !== "Omission") {
				frappe.model.set_value(cdt, cdn, "revised_unit_price", row.contract_unit_price);
			}
		},

		form_render(frm, cdt, cdn) {
			apply_vo_line_readonly_state(frm, cdt, cdn);
		},
	});

	function apply_variation_order_status_ui(frm) {
		const status = frm.doc.status || "Draft";
		const is_locked_view = ["Approved by Client", "Rejected"].includes(status);
		// P0-1: Lines editable only in Draft and Submitted
		const lines_locked = !["Draft", "Submitted"].includes(status);

		// VO Header fields become read-only after final approval / rejection
		const header_readonly_fields = [
			"boq_header",
			"vo_number",
			"vo_date",
			"description",
			"reason",
			"engineer_name",
			"client_approval_document",
			"client_approval_ref",
		];
		header_readonly_fields.forEach((fieldname) => {
			frm.set_df_property(fieldname, "read_only", is_locked_view ? 1 : 0);
		});

		// Lines table — locked once status is Engineer Approved or beyond
		frm.set_df_property("lines", "cannot_add_rows", lines_locked);
		frm.set_df_property("lines", "cannot_delete_rows", lines_locked);
		frm.set_df_property("lines", "read_only", 0);

		frm.doc.__vo_lines_locked = lines_locked;
	}

	function apply_variation_order_workflow_buttons(frm) {
		if (frm.is_new()) return;

		// Clear prior workflow buttons so refresh() is idempotent
		["Submit to Engineer", "Approve by Engineer", "Approve by Client", "Reject"].forEach(
			(label) => {
				frm.remove_custom_button(label, __("Workflow"));
			}
		);

		const status = frm.doc.status || "Draft";

		if (status === "Draft") {
			frm.add_custom_button(
				__("Submit to Engineer"),
				() => transition_variation_order(frm, "Submitted"),
				__("Workflow")
			);
			frm.add_custom_button(
				__("Reject"),
				() => transition_variation_order(frm, "Rejected"),
				__("Workflow")
			);
		} else if (status === "Submitted") {
			frm.add_custom_button(
				__("Approve by Engineer"),
				() => transition_variation_order(frm, "Approved by Engineer"),
				__("Workflow")
			);
			frm.add_custom_button(
				__("Reject"),
				() => transition_variation_order(frm, "Rejected"),
				__("Workflow")
			);
		} else if (status === "Approved by Engineer") {
			frm.add_custom_button(
				__("Approve by Client"),
				() => prompt_client_approval(frm),
				__("Workflow")
			);
			frm.add_custom_button(
				__("Reject"),
				() => transition_variation_order(frm, "Rejected"),
				__("Workflow")
			);
		} else if (status === "Approved by Client") {
			frm.add_custom_button(
				__("Create Material Request"),
				() => create_mr_for_vo(frm),
				__("Create")
			);
		}
	}

	function create_mr_for_vo(frm) {
		frappe.call({
			method: "construction.api.boq_api.create_material_request_for_vo",
			args: { vo_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Creating Material Request..."),
			callback(r) {
				if (r.message && r.message.success) {
					frappe.show_alert({
						message: __("Material Request {0} created", [r.message.material_request]),
						indicator: "green",
					});
					frappe.set_route("Form", "Material Request", r.message.material_request);
				} else if (r.message && r.message.error) {
					frappe.msgprint({
						title: __("Could not create Material Request"),
						message: r.message.error,
						indicator: "red",
					});
				}
			},
		});
	}

	function transition_variation_order(frm, new_status) {
		frappe.call({
			method: "construction.api.boq_api.transition_variation_order",
			args: { vo_name: frm.doc.name, new_status: new_status },
			freeze: true,
			freeze_message: __("Transitioning Variation Order..."),
			callback(r) {
				if (r.message && r.message.success) {
					frm.reload_doc();
					frappe.show_alert({
						message: __("Status → {0}", [r.message.status]),
						indicator: "green",
					});
				} else if (r.message && r.message.error) {
					frappe.msgprint({
						title: __("Transition blocked"),
						message: r.message.error,
						indicator: "red",
					});
				}
			},
		});
	}

	function prompt_client_approval(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Approve by Client"),
			fields: [
				{
					fieldname: "client_approval_document",
					fieldtype: "Attach",
					label: __("Signed client approval PDF"),
					reqd: 1,
					description: __(
						"A signed PDF from the client is required before final approval."
					),
				},
				{
					fieldname: "client_approval_ref",
					fieldtype: "Data",
					label: __("Client Approval Ref"),
				},
			],
			primary_action_label: __("Approve"),
			primary_action(values) {
				if (!values.client_approval_document) {
					frappe.msgprint({
						title: __("Missing PDF"),
						message: __("Signed client approval PDF is required."),
						indicator: "red",
					});
					return;
				}
				if (!String(values.client_approval_document).toLowerCase().endsWith(".pdf")) {
					frappe.msgprint({
						title: __("Wrong file type"),
						message: __("Client approval document must be a PDF."),
						indicator: "red",
					});
					return;
				}
				frappe.call({
					method: "construction.api.boq_api.transition_variation_order",
					args: {
						vo_name: frm.doc.name,
						new_status: "Approved by Client",
						client_approval_document: values.client_approval_document,
					},
					freeze: true,
					freeze_message: __("Approving Variation Order by Client..."),
					callback(r) {
						if (r.message && r.message.success) {
							d.hide();
							frm.reload_doc();
							frappe.show_alert({
								message: __("Approved by Client"),
								indicator: "green",
							});
						} else if (r.message && r.message.error) {
							frappe.msgprint({
								title: __("Approval blocked"),
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

	function render_variation_order_indicators(frm) {
		frm.dashboard.clear_headline();
		const status = frm.doc.status || "Draft";
		const headline = {
			Draft: __("Draft — fill in VO lines and Submit to Engineer to start approval."),
			Submitted: __("Submitted — awaiting Engineer approval."),
			"Approved by Engineer": __("Engineer approved — awaiting signed client approval PDF."),
			"Approved by Client": __(
				"Client approved — variation items and revised quantities are now in effect."
			),
			Rejected: __("Rejected — VO is locked; create a new VO if needed."),
		}[status];
		if (headline) {
			frm.dashboard.set_headline(headline);
		}
		const delta = flt(frm.doc.total_contract_delta);
		if (delta) {
			const currency = frm.doc.currency || frappe.defaults.get_default("currency") || "EGP";
			const indicator = delta > 0 ? "blue" : "orange";
			const label =
				delta > 0
					? __("Contract +{0}", [format_currency(delta, currency)])
					: __("Contract {0}", [format_currency(delta, currency)]);
			frm.dashboard.add_indicator(label, indicator);
		}
	}

	function apply_vo_line_readonly_state(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row) return;
		const grid = frm.get_field("lines").grid;
		const grid_row = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
		if (!grid_row) return;
		const status = frm.doc.status || "Draft";
		// P0-1: Lines editable only in Draft and Submitted
		const is_editable = ["Draft", "Submitted"].includes(status);
		const line_type = row.line_type;
		const is_existing = ["Quantity Change", "Omission"].includes(line_type);
		const is_new_item = line_type === "New Item";
		const is_omission = line_type === "Omission";

		grid_row.toggle_editable("boq_structure", is_editable);
		grid_row.toggle_editable("boq_item", is_editable && is_existing);
		grid_row.toggle_editable("title", is_editable && is_new_item);
		grid_row.toggle_editable("unit", is_editable && is_new_item);
		grid_row.toggle_editable("revised_qty", is_editable && !is_omission);
		grid_row.toggle_editable(
			"revised_unit_price",
			is_editable && (is_new_item || row.rate_change_triggered)
		);
		grid_row.toggle_editable("owner_page", is_editable && is_new_item);
		grid_row.toggle_editable("owner_ref_no", is_editable && is_new_item);
		grid_row.toggle_editable("owner_file_ref", is_editable && is_new_item);
		grid_row.toggle_editable("rate_change_justification", is_editable);
		grid_row.toggle_editable("notes", is_editable);
	}
})();
