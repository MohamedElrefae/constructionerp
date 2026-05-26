(function () {
	const childTables = {
		"Purchase Order": "items",
		"Purchase Receipt": "items",
		"Purchase Invoice": "items",
		"Sales Invoice": "items",
		"Stock Entry": "items",
		"Timesheet": "time_logs",
		"Journal Entry": "accounts",
		"Material Request": "items",
	};

	function rowProject(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		return (row && row.project) || frm.doc.project || null;
	}

	function setChildQueries(frm, tableField) {
		const grid = frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
		if (!grid) {
			return;
		}

		const boqItemField = grid.get_field("boq_item");
		if (boqItemField) {
			boqItemField.get_query = function (doc, cdt, cdn) {
				const filters = {};
				const project = rowProject(frm, cdt, cdn);
				if (project) {
					filters.project = project;
				}
				filters.allowed_statuses = ["Frozen", "Locked"];
				return {
					query: "construction.api.boq_link_queries.get_boq_items",
					filters,
				};
			};
		}

		const boqStageField = grid.get_field("boq_item_stage");
		if (boqStageField) {
			boqStageField.get_query = function (doc, cdt, cdn) {
				const row = locals[cdt] && locals[cdt][cdn];
				const filters = {};
				if (row && row.boq_item) {
					filters.boq_item = row.boq_item;
				}
				return {
					query: "construction.api.boq_link_queries.get_boq_item_stages",
					filters,
				};
			};
		}
	}

	function toggleRowFields(frm, tableField, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row) {
			return;
		}

		if (row.expense_category && row.expense_category !== "Direct") {
			frappe.model.set_value(cdt, cdn, "boq_item", "");
			frappe.model.set_value(cdt, cdn, "boq_item_stage", "");
		}
		if (!row.boq_item && row.boq_item_stage) {
			frappe.model.set_value(cdt, cdn, "boq_item_stage", "");
		}
		frm.refresh_field(tableField);
	}

	function wireParent(doctype, tableField) {
		frappe.ui.form.on(doctype, {
			setup(frm) {
				setChildQueries(frm, tableField);
			},
			refresh(frm) {
				setChildQueries(frm, tableField);
			},
		});
	}

	function wireChildEvents() {
		const childDoctypes = [
			"Purchase Order Item",
			"Purchase Receipt Item",
			"Purchase Invoice Item",
			"Sales Invoice Item",
			"Stock Entry Detail",
			"Timesheet Detail",
			"Journal Entry Account",
			"Material Request Item",
		];

		childDoctypes.forEach((childDoctype) => {
			frappe.ui.form.on(childDoctype, {
				boq_item(frm, cdt, cdn) {
					const row = locals[cdt] && locals[cdt][cdn];
					if (row && !row.boq_item) {
						frappe.model.set_value(cdt, cdn, "boq_item_stage", "");
					}
				},
				expense_category(frm, cdt, cdn) {
					const tableField = childTables[frm.doc.doctype];
					if (tableField) {
						toggleRowFields(frm, tableField, cdt, cdn);
					}
				},
			});
		});
	}

	Object.keys(childTables).forEach((doctype) => wireParent(doctype, childTables[doctype]));
	wireChildEvents();
})();
