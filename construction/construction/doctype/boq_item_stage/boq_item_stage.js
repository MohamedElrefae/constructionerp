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

	function markFieldBlocked(frm, fieldname, blocked, hint) {
		const field = frm.fields_dict && frm.fields_dict[fieldname];
		if (!field) return;
		field.df.only_select = !!blocked;
		field.__ct_boq_blocked = !!blocked;
		field.df.filter_description = blocked ? hint : "";
		if (typeof field.set_description === "function") {
			field.set_description(blocked ? hint : "");
		}
	}

	function updateStageGuidance(frm) {
		const hasProject = Boolean(frm.doc.project);
		const hasBoqHeader = Boolean(frm.doc.boq_header);
		const hasBoqStructure = Boolean(frm.doc.boq_structure);

		setFieldAccent(frm, "boq_header", !hasBoqHeader, !hasProject);
		markFieldBlocked(frm, "boq_header", !hasProject, __("Select Project first"));
		setFieldInlineHint(
			frm,
			"boq_header",
			hasProject && !hasBoqHeader ? __("Select BOQ Header first") : null,
			!hasProject
		);

		setFieldAccent(frm, "boq_structure", !hasBoqStructure, !hasBoqHeader);
		markFieldBlocked(frm, "boq_structure", !hasBoqHeader, __("Select BOQ Header first"));
		setFieldInlineHint(
			frm,
			"boq_structure",
			!hasBoqHeader
				? __("Select BOQ Header first")
				: !hasBoqStructure
				? __("Select BOQ Structure first")
				: null,
			!hasBoqHeader
		);

		setFieldAccent(frm, "boq_item", false, !hasBoqStructure);
		markFieldBlocked(
			frm,
			"boq_item",
			!hasBoqStructure,
			__("Select BOQ Structure first — items link to leaf structures only")
		);
		setFieldInlineHint(
			frm,
			"boq_item",
			!hasBoqStructure ? __("Select BOQ Structure first") : null,
			!hasBoqStructure
		);
		if (hasBoqStructure) {
			const field = frm.fields_dict && frm.fields_dict.boq_item;
			if (field && typeof field.set_description === "function") {
				field.set_description(__("BOQ Items are linked to leaf Structure nodes only."));
			}
		}
	}

	const ONBOARDING_DISMISSED_KEY = "ct_boq_stage_onboarding_dismissed";

	function showOnboardingBanner(frm) {
		if (localStorage.getItem(ONBOARDING_DISMISSED_KEY)) return;
		if (!frm.is_new()) return;
		const $banner = $(`
			<div class="ct-onboarding-banner" style="
				background: var(--ct-accent-bg, rgba(59,130,246,0.1));
				border: 1px solid var(--ct-accent, #3b82f6);
				border-radius: 6px;
				padding: 12px 16px;
				margin-bottom: 16px;
				display: flex;
				align-items: center;
				justify-content: space-between;
				font-size: 13px;
				color: var(--ct-text, #e2e8f0);
			">
				<span>${__(
					"Start with <b>Project</b> → <b>BOQ Header</b> → <b>BOQ Structure</b> → <b>BOQ Item</b>. Each field unlocks the next."
				)}</span>
				<button class="btn btn-xs btn-default ct-dismiss-onboarding" style="margin-left:12px">${__(
					"Got it"
				)}</button>
			</div>
		`);
		$banner.find(".ct-dismiss-onboarding").on("click", function () {
			$banner.slideUp(200, function () {
				$banner.remove();
			});
			localStorage.setItem(ONBOARDING_DISMISSED_KEY, "1");
		});
		frm.layout && frm.layout.show_message && frm.layout.show_message("onboarding", $banner);
		if (frm.layout && frm.layout.$wrapper) {
			frm.layout.$wrapper.find(".form-message").remove();
			frm.layout.$wrapper.find(".form-page > .form-layout").first().before($banner);
		}
	}

	const MAPPING_PLANNER_ROLES = ["System Manager", "Construction Owner", "Project Manager"];

	function isMappingPlanner() {
		return MAPPING_PLANNER_ROLES.some((role) => frappe.user.has_role(role));
	}

	function canManageStageMapping(frm) {
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

	function syncNewStageExecutionButtons(frm, project) {
		const group = __("Execution Location");
		if (typeof frm.remove_custom_button === "function") {
			frm.remove_custom_button(__("Select Execution Location"), group);
			frm.remove_custom_button(__("Use Inherited Default"), group);
		}
		if (!canManageStageMapping(frm) || !project) return;
		frm.add_custom_button(
			__("Select Execution Location"),
			() => openStagePickerDialog(frm, project, true),
			group
		);
		if (frm.doc.execution_node) {
			frm.add_custom_button(
				__("Use Inherited Default"),
				() => {
					frm.__ct_new_stage_override_label = null;
					frm.set_value("execution_node", "");
					if (frm.__ct_stage_preview_ctx) {
						renderStageNewPreviewBanner(frm, frm.__ct_stage_preview_ctx);
						syncNewStageExecutionButtons(frm, project);
					} else {
						refreshStageExecutionLocationUI(frm);
					}
				},
				group
			);
		}
	}

	function stageHasVisibleExecutionActivity(doc) {
		if (!doc) return false;
		return (
			flt(doc.measured_executed_qty) > 0 ||
			flt(doc.certified_qty) > 0 ||
			doc.stage_status === "Completed" ||
			doc.stage_status === "Certified"
		);
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

	function formatAuditAction(row) {
		const map = {
			set: () => __("Initial assignment"),
			change: () => __("Changed"),
			clear: () => __("Cleared"),
			set_on_create: () => __("Assigned on create"),
			inherit_on_create: () => __("Inherited on create"),
			initial_historical_map: () => __("Historical assignment"),
		};
		const base = map[row.action] ? map[row.action]() : row.action || "";
		if (row.historical_trigger) {
			return `${base} (${row.historical_trigger})`;
		}
		return base;
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

	function createPanelBase() {
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
		return panel;
	}

	function createWarningAlert(text) {
		const warn = document.createElement("div");
		warn.className = "ct-exec-loc-warning";
		warn.setAttribute("role", "alert");
		warn.style.marginBlockStart = "6px";
		warn.style.padding = "6px 10px";
		warn.style.borderRadius = "4px";
		warn.style.borderInlineStart = "3px solid var(--orange-500, #d97706)";
		warn.style.background = "var(--bg-orange, rgba(245, 158, 11, 0.14))";
		warn.style.color = "var(--text-on-orange, #92400e)";
		warn.textContent = text;
		return warn;
	}

	function clearExecutionPanel(host, fieldname) {
		if (host.parentNode) {
			host.parentNode
				.querySelectorAll(`.ct-exec-loc-panel[data-ct-exec-panel-for="${fieldname}"]`)
				.forEach((el) => el.remove());
		}
		host.querySelectorAll(".ct-exec-loc-panel").forEach((el) => el.remove());
	}

	function mountExecutionPanel(host, fieldname, panel) {
		panel.setAttribute("data-ct-exec-panel-for", fieldname);
		clearExecutionPanel(host, fieldname);
		if (host.parentNode) {
			host.parentNode.insertBefore(panel, host.nextSibling || null);
		} else {
			host.appendChild(panel);
		}
	}

	function renderStageExistingBanner(frm, ctx) {
		const host = getFieldContainer(frm, "execution_node");
		if (!host) return;

		const panel = createPanelBase();
		const statusRow = document.createElement("div");
		statusRow.className = "ct-exec-loc-summary";

		const assigned = ctx && ctx.assigned;
		const attribution = ctx && ctx.attribution;

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

			if (attribution && attribution.is_historical_assignment) {
				const hist = createBadge(
					__("Historical assignment"),
					"var(--bg-purple, rgba(124, 58, 237, 0.14))",
					"var(--text-on-purple, #6d28d9)"
				);
				hist.style.marginInlineStart = "6px";
				hist.style.marginInlineEnd = "0";
				statusRow.appendChild(hist);
			}
		} else {
			statusRow.appendChild(
				createBadge(
					__("Unmapped"),
					"var(--bg-light-gray, rgba(100, 116, 139, 0.16))",
					"var(--text-muted, #475569)"
				)
			);
		}
		panel.appendChild(statusRow);

		if (assigned && assigned.is_effectively_disabled) {
			panel.appendChild(createWarningAlert(formatDisabledReason(assigned.disabled_reason)));
		}

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

		mountExecutionPanel(host, "execution_node", panel);
	}

	function renderStageNewPreviewBanner(frm, previewResp) {
		const host = getFieldContainer(frm, "execution_node");
		if (!host) return;

		if (!frm.doc.boq_item && !frm.doc.execution_node) {
			clearExecutionPanel(host, "execution_node");
			return;
		}

		const panel = createPanelBase();

		if (frm.doc.execution_node) {
			const override = document.createElement("div");
			override.className = "ct-exec-loc-override";
			const label = frm.__ct_new_stage_override_label || frm.doc.execution_node;
			override.textContent = __("Explicit override selected for this new Stage: {0}", [
				label,
			]);
			panel.appendChild(override);
			mountExecutionPanel(host, "execution_node", panel);
			return;
		}

		const preview = previewResp && previewResp.preview;
		if (previewResp && previewResp.will_inherit && preview) {
			const info = document.createElement("div");
			info.className = "ct-exec-loc-preview";
			info.textContent = __("Will inherit from BOQ Item on save: {0}", [
				formatNodeLabel(preview),
			]);
			panel.appendChild(info);
		} else if (preview) {
			panel.appendChild(
				createWarningAlert(
					__(
						"Parent BOQ Item default ({0}) is disabled and will not be inherited. Stage will save unmapped.",
						[formatNodeLabel(preview)]
					)
				)
			);
		} else {
			const empty = document.createElement("div");
			empty.className = "ct-exec-loc-preview-empty";
			empty.style.color = "var(--text-muted, #64748b)";
			empty.textContent = __(
				"Parent BOQ Item has no planned execution location. Stage will save unmapped."
			);
			panel.appendChild(empty);
		}

		mountExecutionPanel(host, "execution_node", panel);
	}

	function buildStageAuditTableElement(rows) {
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
		wrapper.setAttribute("aria-labelledby", "ct-exec-stage-audit-caption");
		wrapper.style.overflow = "auto";
		wrapper.style.maxInlineSize = "100%";
		wrapper.style.maxBlockSize = "min(440px, 70vh)";

		const table = document.createElement("table");
		table.className = "table table-bordered table-sm";
		table.style.borderCollapse = "separate";
		table.style.borderSpacing = "0";
		table.style.marginBlockEnd = "0";

		const caption = document.createElement("caption");
		caption.id = "ct-exec-stage-audit-caption";
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
			const cells = [
				row.changed_on || "",
				formatAuditAction(row),
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

	function openStageAuditDialog(frm) {
		frappe.call({
			method: "construction.api.execution_mapping_api.get_execution_mapping_audit",
			type: "GET",
			args: {
				target_doctype: "BOQ Item Stage",
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
					body.replaceChildren(buildStageAuditTableElement(rows));
				}
			},
		});
	}

	function openStagePickerDialog(frm, project, isNewRecord) {
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
				const hasCurrent = Boolean(frm.doc.execution_node);
				const isHistoricalHint =
					!isNewRecord && !hasCurrent && stageHasVisibleExecutionActivity(frm.doc);
				const requiresReason = !isNewRecord && (hasCurrent || isHistoricalHint);
				const labelByName = Object.create(null);
				const options = [{ label: "", value: "" }].concat(
					nodes.map((node) => {
						const lbl = formatNodeLabel(node);
						labelByName[node.name] = lbl;
						return { label: escapeHtml(lbl), value: node.name };
					})
				);
				const fields = [];
				if (isHistoricalHint) {
					fields.push({ fieldname: "historical_note", fieldtype: "HTML" });
				}
				fields.push({
					fieldname: "execution_node",
					fieldtype: "Select",
					label: __("Execution Location"),
					options,
					default: frm.doc.execution_node || "",
					reqd: 1,
				});
				if (!isNewRecord) {
					fields.push({
						fieldname: "reason",
						fieldtype: "Small Text",
						label: __("Reason"),
						reqd: requiresReason ? 1 : 0,
					});
				}
				const d = new frappe.ui.Dialog({
					title: isNewRecord
						? __("Select Execution Location")
						: hasCurrent
						? __("Change Execution Location")
						: __("Set Execution Location"),
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
							frm.__ct_new_stage_override_label = labelByName[chosen] || chosen;
							frm.set_value("execution_node", chosen);
							renderStageNewPreviewBanner(frm, frm.__ct_stage_preview_ctx || null);
							syncNewStageExecutionButtons(frm, project);
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
							method: "construction.api.execution_mapping_api.set_stage_execution_node",
							type: "POST",
							freeze: true,
							args: {
								boq_item_stage: frm.doc.name,
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
										message:
											out && out.is_historical_assignment
												? __("Historical execution location assigned.")
												: __("Execution location updated."),
										indicator: "green",
									});
								}
							},
						});
					},
				});
				d.show();
				if (isHistoricalHint) {
					const noteHost =
						d.fields_dict.historical_note && d.fields_dict.historical_note.$wrapper[0];
					if (noteHost) {
						noteHost.replaceChildren(
							createWarningAlert(
								__(
									"This Stage already has execution activity. Saving will record a Historical assignment (reason required)."
								)
							)
						);
					}
				}
			},
		});
	}

	function openStageClearDialog(frm) {
		if (!ensureCleanFormBeforeMapping(frm)) return;
		const d = new frappe.ui.Dialog({
			title: __("Clear Execution Location"),
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
					method: "construction.api.execution_mapping_api.set_stage_execution_node",
					type: "POST",
					freeze: true,
					args: {
						boq_item_stage: frm.doc.name,
						execution_node: null,
						reason,
						expected_modified: frm.doc.modified,
					},
					callback() {
						d.hide();
						if (reloadFormSafelyAfterMapping(frm)) {
							frappe.show_alert({
								message: __("Execution location cleared."),
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
				"Are you sure you want to clear the execution location on this Stage?"
			);
			noteHost.replaceChildren(note);
		}
	}

	function refreshStageExecutionLocationUI(frm) {
		frm.set_df_property("execution_node", "read_only", 1);
		const reqId = (frm.__ct_exec_req_id || 0) + 1;
		frm.__ct_exec_req_id = reqId;

		if (frm.is_new()) {
			frm.__ct_last_boq_item = frm.doc.boq_item || "";
			if (!frm.doc.boq_item) {
				frm.__ct_stage_preview_ctx = null;
				renderStageNewPreviewBanner(frm, null);
				syncNewStageExecutionButtons(frm, frm.doc.project);
				return;
			}

			frappe.call({
				method: "construction.api.execution_mapping_api.get_new_stage_default_preview",
				type: "GET",
				args: { boq_item: frm.doc.boq_item },
				callback(r) {
					if (frm.__ct_exec_req_id !== reqId) return;
					const previewResp = (r && r.message) || {};
					frm.__ct_stage_preview_ctx = previewResp;
					renderStageNewPreviewBanner(frm, previewResp);
					syncNewStageExecutionButtons(frm, previewResp.project || frm.doc.project);
				},
			});
			return;
		}

		frappe.call({
			method: "construction.api.execution_mapping_api.get_mapping_display_context",
			type: "GET",
			args: {
				doctype: "BOQ Item Stage",
				name: frm.doc.name,
			},
			callback(r) {
				if (frm.__ct_exec_req_id !== reqId) return;
				const ctx = (r && r.message) || {};
				frm.__ct_exec_mapping_ctx = ctx;
				renderStageExistingBanner(frm, ctx);

				if (!canManageStageMapping(frm)) {
					return;
				}
				const hasCurrent = Boolean(frm.doc.execution_node);
				frm.add_custom_button(
					hasCurrent ? __("Change Execution Location") : __("Set Execution Location"),
					() => openStagePickerDialog(frm, ctx.project, false),
					__("Execution Location")
				);
				if (hasCurrent) {
					frm.add_custom_button(
						__("Clear Execution Location"),
						() => openStageClearDialog(frm),
						__("Execution Location")
					);
				}
				frm.add_custom_button(
					__("View Mapping History"),
					() => openStageAuditDialog(frm),
					__("Execution Location")
				);
			},
		});
	}

	frappe.ui.form.on("BOQ Item Stage", {
		setup(frm) {
			frm.set_query("boq_header", () => {
				const filters = {};
				if (frm.doc.project) filters.project = frm.doc.project;
				return {
					query: "construction.api.boq_link_queries.get_boq_headers",
					filters,
				};
			});

			frm.set_query("boq_structure", () => {
				const filters = {};
				if (frm.doc.boq_header) filters.boq_header = frm.doc.boq_header;
				return {
					query: "construction.api.boq_link_queries.get_boq_structures",
					filters,
				};
			});

			frm.set_query("boq_item", () => {
				const filters = {};
				if (frm.doc.project) filters.project = frm.doc.project;
				if (frm.doc.boq_header) filters.boq_header = frm.doc.boq_header;
				if (frm.doc.boq_structure) filters.structure = frm.doc.boq_structure;
				return {
					query: "construction.api.boq_link_queries.get_boq_items",
					filters,
				};
			});
		},

		onload(frm) {
			if (!frm.is_new()) return;
			const scope_project =
				window.scopeContext && window.scopeContext.enabled
					? window.scopeContext.getValidatedCurrentScope().project
					: null;
			if (scope_project && !frm.doc.project) {
				frm.__ct_syncing_boq_chain = true;
				Promise.resolve(frm.set_value("project", scope_project)).finally(() => {
					frm.__ct_syncing_boq_chain = false;
					updateStageGuidance(frm);
				});
			}

			$(document)
				.off("scope:changed.boqItemStage")
				.on("scope:changed.boqItemStage", function () {
					var new_project =
						window.scopeContext && window.scopeContext.enabled
							? window.scopeContext.getValidatedCurrentScope().project
							: null;
					if (!new_project) return;
					var current_project = frm.doc.project;
					if (new_project !== current_project) {
						frm.set_value("project", new_project);
						frm.set_value("boq_header", "");
						frm.set_value("boq_structure", "");
						frm.set_value("boq_item", "");
						updateStageGuidance(frm);
						frappe.show_alert({
							message: __(
								"Scope changed. Selected BOQ details have been cleared to prevent stale data."
							),
							indicator: "orange",
						});
					}
				});
		},

		onload_post_render(frm) {
			updateStageGuidance(frm);
			setTimeout(() => updateStageGuidance(frm), 150);
			setTimeout(() => updateStageGuidance(frm), 600);
		},

		refresh(frm) {
			render_stage_progress(frm);
			apply_stage_measurement_ui(frm);
			updateStageGuidance(frm);
			showOnboardingBanner(frm);
			refreshStageExecutionLocationUI(frm);
		},

		before_save(frm) {
			localStorage.setItem(ONBOARDING_DISMISSED_KEY, "1");
		},

		project(frm) {
			if (frm.__ct_syncing_boq_chain) return;
			frm.__ct_boq_item_lookup_id = (frm.__ct_boq_item_lookup_id || 0) + 1;
			frm.set_value("boq_header", "");
			frm.set_value("boq_structure", "");
			frm.set_value("boq_item", "");
			if (frm.is_new() && frm.doc.execution_node) {
				frm.__ct_new_stage_override_label = null;
				frm.set_value("execution_node", "");
			}
			updateStageGuidance(frm);
			refreshStageExecutionLocationUI(frm);
		},

		boq_header(frm) {
			if (frm.__ct_syncing_boq_chain) return;
			frm.__ct_boq_item_lookup_id = (frm.__ct_boq_item_lookup_id || 0) + 1;
			frm.set_value("boq_structure", "");
			frm.set_value("boq_item", "");
			if (frm.is_new() && frm.doc.execution_node) {
				frm.__ct_new_stage_override_label = null;
				frm.set_value("execution_node", "");
			}
			updateStageGuidance(frm);
			refreshStageExecutionLocationUI(frm);
		},

		boq_structure(frm) {
			if (frm.__ct_syncing_boq_chain) return;
			frm.__ct_boq_item_lookup_id = (frm.__ct_boq_item_lookup_id || 0) + 1;
			frm.set_value("boq_item", "");
			if (frm.is_new() && frm.doc.execution_node) {
				frm.__ct_new_stage_override_label = null;
				frm.set_value("execution_node", "");
			}
			updateStageGuidance(frm);
			refreshStageExecutionLocationUI(frm);
		},

		boq_item(frm) {
			const nextItem = frm.doc.boq_item || "";
			const lookupId = (frm.__ct_boq_item_lookup_id || 0) + 1;
			frm.__ct_boq_item_lookup_id = lookupId;
			if (frm.is_new() && frm.__ct_last_boq_item !== nextItem) {
				frm.__ct_last_boq_item = nextItem;
				frm.__ct_new_stage_override_label = null;
				if (frm.doc.execution_node) {
					frm.set_value("execution_node", "");
					syncNewStageExecutionButtons(frm, frm.doc.project);
				}
			}
			if (!nextItem) {
				refreshStageExecutionLocationUI(frm);
				return;
			}
			frappe.db
				.get_value("BOQ Item", nextItem, ["boq_header", "structure"])
				.then((r) => {
					if (
						frm.__ct_boq_item_lookup_id !== lookupId ||
						(frm.doc.boq_item || "") !== nextItem
					) {
						return;
					}
					const d = r?.message || {};
					const pending = [];
					frm.__ct_syncing_boq_chain = true;
					if (d.boq_header && frm.doc.boq_header !== d.boq_header) {
						pending.push(frm.set_value("boq_header", d.boq_header));
					}
					if (d.structure && frm.doc.boq_structure !== d.structure) {
						pending.push(frm.set_value("boq_structure", d.structure));
					}
					return Promise.all(pending).finally(() => {
						frm.__ct_syncing_boq_chain = false;
						if (
							frm.__ct_boq_item_lookup_id !== lookupId ||
							(frm.doc.boq_item || "") !== nextItem
						) {
							return;
						}
						updateStageGuidance(frm);
						refreshStageExecutionLocationUI(frm);
					});
				});
		},

		planned_qty(frm) {
			render_stage_progress(frm);
		},

		measured_executed_qty(frm) {
			render_stage_progress(frm);
		},

		certified_qty(frm) {
			render_stage_progress(frm);
		},

		percent_complete(frm) {
			render_stage_progress(frm);
		},
	});

	function apply_stage_measurement_ui(frm) {
		const can_certify =
			frappe.user.has_role("System Manager") ||
			frappe.user.has_role("Construction Owner") ||
			frappe.user.has_role("Project Manager");
		const is_accountant =
			frappe.user.has_role("Accountant") &&
			!frappe.user.has_role("System Manager") &&
			!frappe.user.has_role("Construction Owner") &&
			!frappe.user.has_role("Project Manager");
		const is_certified =
			frm.doc.stage_status === "Certified" || flt(frm.doc.certified_qty) > 0;
		const planning_locked = ["Frozen", "Locked"].includes(frm.doc.__boq_status || "");

		if (frm.doc.boq_header && !frm.doc.__boq_status_loaded && !frm.doc.__boq_status_loading) {
			frm.doc.__boq_status_loading = true;
			frappe.db.get_value("BOQ Header", frm.doc.boq_header, "status").then((r) => {
				frm.doc.__boq_status = r?.message?.status;
				frm.doc.__boq_status_loaded = true;
				frm.doc.__boq_status_loading = false;
				apply_stage_measurement_ui(frm);
			});
		}

		const identity_fields = [
			"project",
			"boq_header",
			"boq_structure",
			"boq_item",
			"stage_code",
			"stage_name",
			"planned_qty",
		];
		const execution_fields = [
			"measured_executed_qty",
			"percent_complete",
			"stage_status",
			"description",
		];

		identity_fields.forEach((fieldname) => {
			frm.set_df_property(fieldname, "read_only", is_certified || planning_locked);
		});
		execution_fields.forEach((fieldname) => {
			frm.set_df_property(fieldname, "read_only", is_certified || is_accountant);
		});
		frm.set_df_property(
			"certified_qty",
			"read_only",
			is_certified || is_accountant || !can_certify
		);

		if (is_certified) {
			frm.dashboard.set_headline(
				__("Certified stage is locked. Create an adjustment stage for corrections.")
			);
		} else if (!can_certify) {
			frm.dashboard.set_headline(
				__(
					"Measurement entry is available. Certification is limited to Project Manager roles."
				)
			);
		}
	}

	function render_stage_progress(frm) {
		const planned = flt(frm.doc.planned_qty);
		const measured = flt(frm.doc.measured_executed_qty);
		const certified = flt(frm.doc.certified_qty);
		const percent = flt(frm.doc.percent_complete);
		const measured_pct = planned ? Math.min((measured / planned) * 100, 999) : 0;
		const certified_pct = planned ? Math.min((certified / planned) * 100, 999) : 0;

		frm.dashboard.clear_headline();
		frm.dashboard.add_indicator(
			__("Measured {0}%").replace("{0}", measured_pct.toFixed(1)),
			measured > planned ? "orange" : "blue"
		);
		frm.dashboard.add_indicator(
			__("Certified {0}%").replace("{0}", certified_pct.toFixed(1)),
			certified > measured ? "red" : "green"
		);
		frm.dashboard.add_indicator(
			__("Progress {0}%").replace("{0}", percent.toFixed(1)),
			percent >= 100 ? "green" : "blue"
		);
	}
})();
