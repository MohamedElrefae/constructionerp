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
		const scope_project = window.scopeContext?.enabled
			? window.scopeContext?.current?.project
			: null;
		if (scope_project && !frm.doc.project) {
			frm.set_value("project", scope_project);
		}
	},

	refresh(frm) {
		render_stage_progress(frm);
		apply_stage_measurement_ui(frm);
	},

	project(frm) {
		frm.set_value("boq_header", "");
		frm.set_value("boq_structure", "");
		frm.set_value("boq_item", "");
	},

	boq_header(frm) {
		frm.set_value("boq_structure", "");
		frm.set_value("boq_item", "");
	},

	boq_structure(frm) {
		frm.set_value("boq_item", "");
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
	const can_certify = frappe.user.has_role("System Manager")
		|| frappe.user.has_role("Construction Owner")
		|| frappe.user.has_role("Project Manager");
	const is_accountant = frappe.user.has_role("Accountant")
		&& !frappe.user.has_role("System Manager")
		&& !frappe.user.has_role("Construction Owner")
		&& !frappe.user.has_role("Project Manager");
	const is_certified = frm.doc.stage_status === "Certified" || flt(frm.doc.certified_qty) > 0;
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

	const identity_fields = ["project", "boq_header", "boq_structure", "boq_item", "stage_code", "stage_name", "planned_qty"];
	const execution_fields = ["measured_executed_qty", "percent_complete", "stage_status", "description"];

	identity_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", is_certified || planning_locked);
	});
	execution_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", is_certified || is_accountant);
	});
	frm.set_df_property("certified_qty", "read_only", is_certified || is_accountant || !can_certify);

	if (is_certified) {
		frm.dashboard.set_headline(__("Certified stage is locked. Create an adjustment stage for corrections."));
	} else if (!can_certify) {
		frm.dashboard.set_headline(__("Measurement entry is available. Certification is limited to Project Manager roles."));
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
	frm.dashboard.add_indicator(__("Measured {0}%").replace("{0}", measured_pct.toFixed(1)), measured > planned ? "orange" : "blue");
	frm.dashboard.add_indicator(__("Certified {0}%").replace("{0}", certified_pct.toFixed(1)), certified > measured ? "red" : "green");
	frm.dashboard.add_indicator(__("Progress {0}%").replace("{0}", percent.toFixed(1)), percent >= 100 ? "green" : "blue");
}
