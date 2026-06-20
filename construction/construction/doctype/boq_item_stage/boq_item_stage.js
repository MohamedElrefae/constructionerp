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
				frm.set_value("project", scope_project);
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
		},

		before_save(frm) {
			localStorage.setItem(ONBOARDING_DISMISSED_KEY, "1");
		},

		project(frm) {
			frm.set_value("boq_header", "");
			frm.set_value("boq_structure", "");
			frm.set_value("boq_item", "");
			updateStageGuidance(frm);
		},

		boq_header(frm) {
			frm.set_value("boq_structure", "");
			frm.set_value("boq_item", "");
			updateStageGuidance(frm);
		},

		boq_structure(frm) {
			frm.set_value("boq_item", "");
			updateStageGuidance(frm);
		},

		boq_item(frm) {
			if (!frm.doc.boq_item) return;
			frappe.db
				.get_value("BOQ Item", frm.doc.boq_item, ["boq_header", "structure"])
				.then((r) => {
					const d = r?.message || {};
					if (d.boq_header && frm.doc.boq_header !== d.boq_header) {
						frm.set_value("boq_header", d.boq_header);
					}
					if (d.structure && frm.doc.boq_structure !== d.structure) {
						frm.set_value("boq_structure", d.structure);
					}
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
