// ViteFormConfig is attached globally via frappe.ui.form.on('*') in vite_layout_controls.js
// Do NOT call ViteFormConfig.attach(frm) here — it causes duplicate attach.
(function () {
	function cascadeEnabled() {
		return ["On", "Strict"].includes(frappe.boot.enable_boq_cascade_filtering || "Off");
	}

	function getScope() {
		if (window.scopeContext && window.scopeContext.enabled) {
			return window.scopeContext.getValidatedCurrentScope() || {};
		}
		return (frappe.boot.scope_context && frappe.boot.scope_context.current) || {};
	}

	function withScope(filters) {
		if (!cascadeEnabled()) return filters;
		const scope = getScope();
		["company", "cost_center", "project"].forEach((fieldname) => {
			if (scope[fieldname] && !filters[fieldname]) {
				filters[fieldname] = scope[fieldname];
			}
		});
		filters.enforce_scope = true;
		return filters;
	}

	function bindBoqItemQueries(frm) {
		frm.set_query("boq_header", function () {
			return {
				query: "construction.api.boq_link_queries.get_boq_headers",
				filters: withScope({}),
			};
		});

		frm.set_query("structure", function () {
			return {
				query: "construction.api.boq_link_queries.get_boq_structures",
				filters: withScope({
					boq_header: frm.doc.boq_header,
					require_boq_header: 1,
				}),
			};
		});
	}

	function clearStructureIfNeeded(frm) {
		if (frm.doc.structure) {
			frm.set_value("structure", "");
		}
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
				}),
			);
		}
	}

	function setFieldAccent(frm, fieldname, active, blocked) {
		const $wrapper = $(`.frappe-control[data-fieldname="${fieldname}"]`);
		if (!$wrapper.length) return;

		$wrapper.toggleClass("ct-boq-step-accent", !!active);
		$wrapper.toggleClass("ct-boq-step-blocked", !!blocked);
	}

	function setStructureBlocking(frm, blocked) {
		const field = frm.fields_dict && frm.fields_dict.structure;
		if (!field) return;
		field.df.only_select = !!blocked;
		field.__ct_boq_blocked = !!blocked;
		field.df.filter_description = blocked ? __("Select BOQ Header first") : "";
		if (typeof field.set_description === "function") {
			field.set_description(
				blocked
					? __("Select BOQ Header first")
					: __(
							"BOQ Items are linked to leaf Structure nodes only. If no structures appear, ensure a leaf-level Structure exists.",
						),
			);
		}
	}

	function renderLeafBreadcrumb(frm) {
		if (!frm.doc.boq_header) return;
		frappe.db.get_value("BOQ Header", frm.doc.boq_header, "project").then((r) => {
			const projectName = (r && r.message && r.message.project) || "";
			const breadcrumb = [];
			if (projectName) breadcrumb.push(projectName);
			if (frm.doc.boq_header) breadcrumb.push(frm.doc.boq_header);
			if (frm.doc.structure) breadcrumb.push(frm.doc.structure);
			breadcrumb.push(frm.doc.name || __("BOQ Item"));
			frm.dashboard.set_headline(breadcrumb.join(" → "));
		});
	}

	function updateBoqGuidance(frm) {
		const hasHeader = Boolean(frm.doc.boq_header);
		setFieldAccent(frm, "boq_header", !hasHeader, false);
		setFieldAccent(frm, "structure", false, !hasHeader);
		setStructureBlocking(frm, !hasHeader);
		setFieldInlineHint(
			frm,
			"boq_header",
			hasHeader ? null : __("Select BOQ Header first"),
			false,
		);
		setFieldInlineHint(
			frm,
			"structure",
			hasHeader ? null : __("Select BOQ Header first"),
			!hasHeader,
		);
	}

	function showCreateStructureDialog(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Create Leaf Structure"),
			fields: [
				{
					fieldname: "title",
					fieldtype: "Data",
					label: __("Structure Title"),
					reqd: 1,
				},
				{
					fieldname: "wbs_code",
					fieldtype: "Data",
					label: __("WBS Code"),
				},
			],
			primary_action_label: __("Create"),
			primary_action(values) {
				frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "BOQ Structure",
							title: values.title,
							wbs_code: values.wbs_code || "",
							boq_header: frm.doc.boq_header,
							is_group: 0,
						},
					},
					callback(r) {
						if (r.message) {
							d.hide();
							frm.set_value("structure", r.message.name).then(() => {
								frm.refresh();
							});
							frappe.show_alert({
								message: __("Structure {0} created", [r.message.name]),
								indicator: "green",
							});
						}
					},
				});
			},
		});
		d.show();
	}

	frappe.ui.form.on("BOQ Item", {
		setup(frm) {
			bindBoqItemQueries(frm);
		},

		refresh(frm) {
			bindBoqItemQueries(frm);
			updateBoqGuidance(frm);

			if (frm.is_new()) {
				return;
			}

			renderLeafBreadcrumb(frm);

			// Hide the native dashboard/connections bar as the stages function already exists in the topbar
			if (frm.dashboard) {
				frm.dashboard.hide();
			}

			frm.add_custom_button(
				__("Variation Orders"),
				() => {
					frappe.set_route("List", "Variation Order", {
						boq_header: frm.doc.boq_header,
					});
				},
				__("View"),
			);

			frm.add_custom_button(
				__("View Stages"),
				() => {
					frappe.set_route("List", "BOQ Item Stage", {
						boq_item: frm.doc.name,
					});
				},
				__("Stages"),
			);

			frm.add_custom_button(
				__("Add Stage"),
				() => {
					frappe.new_doc("BOQ Item Stage", {
						boq_item: frm.doc.name,
					});
				},
				__("Stages"),
			);

			if (frm.doc.boq_header && !frm.doc.structure) {
				frm.add_custom_button(
					__("Create Leaf Structure"),
					() => showCreateStructureDialog(frm),
					__("Create"),
				);
			}
		},

		onload_post_render(frm) {
			bindBoqItemQueries(frm);
			updateBoqGuidance(frm);
			setTimeout(() => updateBoqGuidance(frm), 150);
			setTimeout(() => updateBoqGuidance(frm), 600);
		},

		boq_header(frm) {
			clearStructureIfNeeded(frm);
			updateBoqGuidance(frm);
			renderLeafBreadcrumb(frm);
		},

		structure(frm) {
			renderLeafBreadcrumb(frm);
		},
	});
})();
