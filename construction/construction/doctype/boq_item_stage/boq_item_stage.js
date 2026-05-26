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
		const scope_project = window.scopeContext?.enabled ? window.scopeContext?.current?.project : null;
		if (scope_project && !frm.doc.project) {
			frm.set_value("project", scope_project);
		}
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
		frappe.db.get_value("BOQ Item", frm.doc.boq_item, ["boq_header", "structure"]).then((r) => {
			const d = r?.message || {};
			if (d.boq_header && frm.doc.boq_header !== d.boq_header) {
				frm.set_value("boq_header", d.boq_header);
			}
			if (d.structure && frm.doc.boq_structure !== d.structure) {
				frm.set_value("boq_structure", d.structure);
			}
		});
	},
});
