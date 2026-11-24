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
				})
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
							"BOQ Items are linked to leaf Structure nodes only. If no structures appear, ensure a leaf-level Structure exists."
					  )
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
			false
		);
		setFieldInlineHint(
			frm,
			"structure",
			hasHeader ? null : __("Select BOQ Header first"),
			!hasHeader
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

	const MAPPING_PLANNER_ROLES = ["System Manager", "Construction Owner", "Project Manager"];

	function isMappingPlanner() {
		return MAPPING_PLANNER_ROLES.some((role) => frappe.user.has_role(role));
	}

	function canManageItemMapping(frm) {
		return isMappingPlanner() && Boolean(frm.perm && frm.perm[0] && frm.perm[0].write);
	}

	function escapeHtml(text) {
		return String(text == null ? "" : text)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;");
	}

	function ensureCleanFormBeforeMapping(frm) {
		if (typeof frm.is_dirty === "function" && frm.is_dirty()) {
			frappe.msgprint({
				title: __("Unsaved Changes"),
				message: __(
					"Please save or discard your unsaved form changes before updating the execution location."
				),
				indicator: "orange",
			});
			return false;
		}
		return true;
	}

	function reloadFormSafelyAfterMapping(frm) {
		if (typeof frm.is_dirty === "function" && frm.is_dirty()) {
			frappe.show_alert({
				message: __(
					"Execution location was saved, but the form has unsaved edits. Save or discard your edits and reload."
				),
				indicator: "orange",
			});
			return false;
		}
		frm.reload_doc();
		return true;
	}

	function formatNodeLabel(node) {
		if (!node) return "";
		const code = node.ebs_code ? `${node.ebs_code} — ` : "";
		return `${code}${node.full_path || node.title || node.node || node.name || ""}`;
	}

	function formatDisabledReason(disabledReason) {
		if (disabledReason === "ancestor") {
			return __("Linked execution location is under a disabled ancestor branch.");
		}
		if (disabledReason === "missing") {
			return __("Linked execution location no longer exists.");
		}
		return __("Linked execution location is disabled.");
	}

	function formatAuditAction(action) {
		const map = {
			set: () => __("Initial assignment"),
			change: () => __("Changed"),
			clear: () => __("Cleared"),
			set_on_create: () => __("Assigned on create"),
			inherit_on_create: () => __("Inherited on create"),
			initial_historical_map: () => __("Historical assignment"),
		};
		return map[action] ? map[action]() : action || "";
	}

	function getFieldContainer(frm, fieldname) {
		const field = frm.fields_dict && frm.fields_dict[fieldname];
		if (field && field.$wrapper && field.$wrapper[0]) {
			return field.$wrapper[0];
		}
		return document.querySelector(`.frappe-control[data-fieldname="${fieldname}"]`);
	}

	function createBadge(text, bg, fg) {
		const badge = document.createElement("span");
		badge.className = "ct-exec-loc-badge";
		badge.textContent = text;
		badge.style.display = "inline-block";
		badge.style.padding = "2px 8px";
		badge.style.borderRadius = "999px";
		badge.style.fontSize = "11px";
		badge.style.fontWeight = "600";
		badge.style.marginInlineEnd = "6px";
		badge.style.background = bg;
		badge.style.color = fg;
		return badge;
	}

	function mountExecutionPanel(host, fieldname, panel) {
		panel.setAttribute("data-ct-exec-panel-for", fieldname);
		const parent = host.parentNode;
		if (parent) {
			parent
				.querySelectorAll(`.ct-exec-loc-panel[data-ct-exec-panel-for="${fieldname}"]`)
				.forEach((el) => el.remove());
			host.querySelectorAll(".ct-exec-loc-panel").forEach((el) => el.remove());
			parent.insertBefore(panel, host.nextSibling || null);
		} else {
			host.querySelectorAll(".ct-exec-loc-panel").forEach((el) => el.remove());
			host.appendChild(panel);
		}
	}

	function renderItemExecutionBanner(frm, ctx) {
		const host = getFieldContainer(frm, "planned_execution_node");
		if (!host) return;

		const panel = document.createElement("div");
		panel.className = "ct-exec-loc-panel";
		panel.setAttribute("role", "status");
		panel.setAttribute("aria-live", "polite");
		panel.style.marginBlockStart = "6px";
		panel.style.padding = "10px 12px";
		panel.style.borderRadius = "6px";
		panel.style.border = "1px solid var(--border-color, #d1d8dd)";
		panel.style.background = "var(--subtle-fg, rgba(148, 163, 184, 0.08))";
		panel.style.fontSize = "12.5px";
		panel.style.lineHeight = "1.5";
		panel.style.textAlign = "start";

		const statusRow = document.createElement("div");
		statusRow.className = "ct-exec-loc-summary";

		const assigned = ctx && ctx.assigned;
		if (assigned) {
			if (assigned.ebs_code) {
				statusRow.appendChild(
					createBadge(
						assigned.ebs_code,
						"var(--bg-blue, rgba(37, 99, 235, 0.14))",
						"var(--text-on-blue, #1d4ed8)"
					)
				);
			}
			const pathSpan = document.createElement("strong");
			pathSpan.className = "ct-exec-loc-path";
			pathSpan.textContent = assigned.full_path || assigned.title || assigned.node || "";
			statusRow.appendChild(pathSpan);
		} else if (!frm.is_new()) {
			statusRow.appendChild(
				createBadge(
					__("Unmapped"),
					"var(--bg-light-gray, rgba(100, 116, 139, 0.16))",
					"var(--text-muted, #475569)"
				)
			);
		} else if (frm.doc.planned_execution_node) {
			const pendingSpan = document.createElement("strong");
			pendingSpan.textContent =
				frm.__ct_new_item_location_label || frm.doc.planned_execution_node;
			statusRow.appendChild(pendingSpan);
		}
		if (statusRow.childNodes.length) {
			panel.appendChild(statusRow);
		}

		if (assigned && assigned.is_effectively_disabled) {
			const warn = document.createElement("div");
			warn.className = "ct-exec-loc-warning";
			warn.setAttribute("role", "alert");
			warn.style.marginBlockStart = "6px";
			warn.style.padding = "6px 10px";
			warn.style.borderRadius = "4px";
			warn.style.borderInlineStart = "3px solid var(--orange-500, #d97706)";
			warn.style.background = "var(--bg-orange, rgba(245, 158, 11, 0.14))";
			warn.style.color = "var(--text-on-orange, #92400e)";
			warn.textContent = formatDisabledReason(assigned.disabled_reason);
			panel.appendChild(warn);
		}

		const attribution = ctx && ctx.attribution;
		if (assigned && attribution && attribution.mapped_by) {
			const meta = document.createElement("div");
			meta.className = "ct-exec-loc-meta";
			meta.style.marginBlockStart = "4px";
			meta.style.fontSize = "11.5px";
			meta.style.color = "var(--text-muted, #64748b)";
			const when = attribution.mapped_on ? ` · ${attribution.mapped_on}` : "";
			meta.textContent = `${__("Mapped by {0}", [attribution.mapped_by])}${when}`;
			panel.appendChild(meta);
		}

		const ruleNote = document.createElement("div");
		ruleNote.className = "ct-exec-loc-product-rule";
		ruleNote.style.marginBlockStart = "6px";
		ruleNote.style.fontSize = "12px";
		ruleNote.style.color = "var(--text-muted, #64748b)";
		ruleNote.textContent = __(
			"Changing the BOQ Item's planned location affects future Stages only; existing Stage locations remain unchanged."
		);
		panel.appendChild(ruleNote);

		mountExecutionPanel(host, "planned_execution_node", panel);
	}

	function buildAuditTableElement(rows) {
		const container = document.createElement("div");
		if (!rows || !rows.length) {
			const empty = document.createElement("p");
			empty.className = "text-muted";
			empty.textContent = __("No mapping history recorded yet.");
			container.appendChild(empty);
			return container;
		}

		const wrapper = document.createElement("div");
		wrapper.className = "ct-exec-audit-table-wrap";
		wrapper.setAttribute("tabindex", "0");
		wrapper.setAttribute("role", "region");
		wrapper.setAttribute("aria-labelledby", "ct-exec-item-audit-caption");
		wrapper.style.overflow = "auto";
		wrapper.style.maxInlineSize = "100%";
		wrapper.style.maxBlockSize = "min(440px, 70vh)";

		const table = document.createElement("table");
		table.className = "table table-bordered table-sm";
		table.style.borderCollapse = "separate";
		table.style.borderSpacing = "0";
		table.style.marginBlockEnd = "0";

		const caption = document.createElement("caption");
		caption.id = "ct-exec-item-audit-caption";
		caption.style.captionSide = "top";
		caption.style.fontWeight = "600";
		caption.style.paddingBlockEnd = "6px";
		caption.style.textAlign = "start";
		caption.textContent = __("Execution Mapping History");
		table.appendChild(caption);

		const thead = document.createElement("thead");
		thead.style.position = "sticky";
		thead.style.insetBlockStart = "0";
		thead.style.zIndex = "1";
		thead.style.background = "var(--card-bg, #ffffff)";

		const headRow = document.createElement("tr");
		[
			__("Date"),
			__("Action"),
			__("From"),
			__("To"),
			__("Reason"),
			__("Changed By"),
		].forEach((label) => {
			const th = document.createElement("th");
			th.setAttribute("scope", "col");
			th.style.whiteSpace = "nowrap";
			th.textContent = label;
			headRow.appendChild(th);
		});
		thead.appendChild(headRow);
		table.appendChild(thead);

		const tbody = document.createElement("tbody");
		rows.forEach((row) => {
			const tr = document.createElement("tr");
			const fromText = row.old_path_snapshot
				? `${row.old_ebs_code ? `${row.old_ebs_code} — ` : ""}${row.old_path_snapshot}`
				: "—";
			const toText = row.new_path_snapshot
				? `${row.new_ebs_code ? `${row.new_ebs_code} — ` : ""}${row.new_path_snapshot}`
				: "—";
			const actionText = formatAuditAction(row.action);
			const cells = [
				row.changed_on || "",
				actionText,
				fromText,
				toText,
				row.reason || "—",
				row.changed_by || "",
			];
			cells.forEach((value) => {
				const td = document.createElement("td");
				td.textContent = value;
				tr.appendChild(td);
			});
			tbody.appendChild(tr);
		});
		table.appendChild(tbody);
		wrapper.appendChild(table);
		container.appendChild(wrapper);
		return container;
	}

	function openItemAuditDialog(frm) {
		frappe.call({
			method: "construction.api.execution_mapping_api.get_execution_mapping_audit",
			type: "GET",
			args: {
				target_doctype: "BOQ Item",
				target_name: frm.doc.name,
			},
			callback(r) {
				const rows = (r && r.message) || [];
				const d = new frappe.ui.Dialog({
					title: __("Execution Mapping History"),
					size: "large",
					fields: [{ fieldname: "history_html", fieldtype: "HTML" }],
				});
				d.show();
				const body = d.fields_dict.history_html && d.fields_dict.history_html.$wrapper[0];
				if (body) {
					body.replaceChildren(buildAuditTableElement(rows));
				}
			},
		});
	}

	function openItemPickerDialog(frm, project, isNewRecord) {
		if (!project) return;
		if (!isNewRecord && !ensureCleanFormBeforeMapping(frm)) return;
		frappe.call({
			method: "construction.api.execution_mapping_api.get_eligible_execution_nodes",
			type: "GET",
			args: { project },
			callback(r) {
				const nodes = (r && r.message) || [];
				if (!nodes.length) {
					frappe.show_alert({
						message: __("No eligible active leaf execution locations found for this project."),
						indicator: "orange",
					});
					return;
				}
				const hasCurrent = Boolean(frm.doc.planned_execution_node);
				const requiresReason = !isNewRecord && hasCurrent;
				const labelByName = Object.create(null);
				const options = [{ label: "", value: "" }].concat(
					nodes.map((node) => {
						const rawLabel = formatNodeLabel(node);
						labelByName[node.name] = rawLabel;
						return {
							label: escapeHtml(rawLabel),
							value: node.name,
						};
					})
				);
				const fields = [
					{
						fieldname: "rule_banner",
						fieldtype: "HTML",
					},
					{
						fieldname: "execution_node",
						fieldtype: "Select",
						label: __("Planned Execution Location"),
						options,
						default: frm.doc.planned_execution_node || "",
						reqd: 1,
					},
				];
				if (!isNewRecord) {
					fields.push({
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Reason"),
						reqd: requiresReason ? 1 : 0,
					});
				}
				const d = new frappe.ui.Dialog({
					title: hasCurrent ? __("Change Planned Location") : __("Set Planned Location"),
					fields,
					primary_action_label: __("Save"),
					primary_action(values) {
						const chosen = (values.execution_node || "").trim();
						if (!chosen) {
							frappe.msgprint(__("Please select an execution location."));
							return;
						}
						if (isNewRecord) {
							d.hide();
							frm.__ct_new_item_location_label = labelByName[chosen] || chosen;
							frm.set_value("planned_execution_node", chosen);
							renderItemExecutionBanner(frm, null);
							return;
						}
						if (!ensureCleanFormBeforeMapping(frm)) {
							return;
						}
						const reason = (values.reason || "").trim();
						if (requiresReason && !reason) {
							frappe.msgprint(__("Reason is required for this change."));
							return;
						}
						frappe.call({
							method: "construction.api.execution_mapping_api.set_item_planned_execution_node",
							type: "POST",
							freeze: true,
							args: {
								boq_item: frm.doc.name,
								execution_node: chosen,
								reason,
								expected_modified: frm.doc.modified,
							},
							callback(res) {
								const out = res && res.message;
								d.hide();
								if (out && out.changed === false) {
									frappe.show_alert({
										message: __("No changes detected."),
										indicator: "blue",
									});
									return;
								}
								if (reloadFormSafelyAfterMapping(frm)) {
									frappe.show_alert({
										message: __("Planned execution location updated."),
										indicator: "green",
									});
								}
							},
						});
					},
				});
				d.show();
				const ruleHost = d.fields_dict.rule_banner && d.fields_dict.rule_banner.$wrapper[0];
				if (ruleHost) {
					const note = document.createElement("p");
					note.className = "text-muted";
					note.style.marginBlockEnd = "8px";
					note.textContent = __(
						"Changing the BOQ Item's planned location affects future Stages only; existing Stage locations remain unchanged."
					);
					ruleHost.replaceChildren(note);
				}
			},
		});
	}

	function openItemClearDialog(frm) {
		if (!ensureCleanFormBeforeMapping(frm)) return;
		const d = new frappe.ui.Dialog({
			title: __("Clear Planned Location"),
			fields: [
				{ fieldname: "confirm_note", fieldtype: "HTML" },
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Reason"),
					reqd: 1,
				},
			],
			primary_action_label: __("Clear"),
			primary_action(values) {
				if (!ensureCleanFormBeforeMapping(frm)) {
					return;
				}
				const reason = (values.reason || "").trim();
				if (!reason) {
					frappe.msgprint(__("Reason is required for this change."));
					return;
				}
				frappe.call({
					method: "construction.api.execution_mapping_api.set_item_planned_execution_node",
					type: "POST",
					freeze: true,
					args: {
						boq_item: frm.doc.name,
						execution_node: null,
						reason,
						expected_modified: frm.doc.modified,
					},
					callback() {
						d.hide();
						if (reloadFormSafelyAfterMapping(frm)) {
							frappe.show_alert({
								message: __("Planned execution location cleared."),
								indicator: "green",
							});
						}
					},
				});
			},
		});
		d.show();
		const noteHost = d.fields_dict.confirm_note && d.fields_dict.confirm_note.$wrapper[0];
		if (noteHost) {
			const note = document.createElement("p");
			note.textContent = __(
				"Are you sure you want to clear the planned execution location? Existing Stage locations will remain unchanged."
			);
			noteHost.replaceChildren(note);
		}
	}

	function refreshItemExecutionLocationUI(frm) {
		frm.set_df_property("planned_execution_node", "read_only", 1);
		const reqId = (frm.__ct_exec_req_id || 0) + 1;
		frm.__ct_exec_req_id = reqId;

		if (frm.is_new()) {
			renderItemExecutionBanner(frm, null);
			if (canManageItemMapping(frm) && frm.doc.boq_header) {
				frm.add_custom_button(
					__("Set Planned Location"),
					() => {
						frappe.db
							.get_value("BOQ Header", frm.doc.boq_header, "project")
							.then((r) => {
								const proj = r && r.message && r.message.project;
								if (proj) {
									openItemPickerDialog(frm, proj, true);
								}
							});
					},
					__("Execution Location")
				);
			}
			return;
		}

		frappe.call({
			method: "construction.api.execution_mapping_api.get_mapping_display_context",
			type: "GET",
			args: {
				doctype: "BOQ Item",
				name: frm.doc.name,
			},
			callback(r) {
				if (frm.__ct_exec_req_id !== reqId) return;
				const ctx = (r && r.message) || {};
				frm.__ct_exec_mapping_ctx = ctx;
				renderItemExecutionBanner(frm, ctx);

				if (!canManageItemMapping(frm)) {
					return;
				}
				const hasCurrent = Boolean(frm.doc.planned_execution_node);
				frm.add_custom_button(
					hasCurrent ? __("Change Planned Location") : __("Set Planned Location"),
					() => openItemPickerDialog(frm, ctx.project, false),
					__("Execution Location")
				);
				if (hasCurrent) {
					frm.add_custom_button(
						__("Clear Planned Location"),
						() => openItemClearDialog(frm),
						__("Execution Location")
					);
				}
				frm.add_custom_button(
					__("View Mapping History"),
					() => openItemAuditDialog(frm),
					__("Execution Location")
				);
			},
		});
	}

	frappe.ui.form.on("BOQ Item", {
		setup(frm) {
			bindBoqItemQueries(frm);
		},

		refresh(frm) {
			bindBoqItemQueries(frm);
			updateBoqGuidance(frm);
			refreshItemExecutionLocationUI(frm);

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
				__("View")
			);

			frm.add_custom_button(
				__("View Stages"),
				() => {
					frappe.set_route("List", "BOQ Item Stage", {
						boq_item: frm.doc.name,
					});
				},
				__("Stages")
			);

			frm.add_custom_button(
				__("Add Stage"),
				() => {
					frappe.new_doc("BOQ Item Stage", {
						boq_item: frm.doc.name,
					});
				},
				__("Stages")
			);

			if (frm.doc.boq_header && !frm.doc.structure) {
				frm.add_custom_button(
					__("Create Leaf Structure"),
					() => showCreateStructureDialog(frm),
					__("Create")
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
			if (frm.is_new() && frm.doc.planned_execution_node) {
				frm.__ct_new_item_location_label = null;
				frm.set_value("planned_execution_node", "");
			}
			updateBoqGuidance(frm);
			renderLeafBreadcrumb(frm);
			if (frm.is_new()) {
				refreshItemExecutionLocationUI(frm);
			}
		},

		structure(frm) {
			renderLeafBreadcrumb(frm);
		},
	});
})();
