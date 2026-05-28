(function () {
	"use strict";

	const childTables = {
		"Purchase Order": "items",
		"Purchase Receipt": "items",
		"Purchase Invoice": "items",
		"Sales Invoice": "items",
		"Stock Entry": "items",
		Timesheet: "time_logs",
		"Journal Entry": "accounts",
		"Material Request": "items",
	};

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

	const expenseGateDoctypes = [
		"Purchase Order Item",
		"Purchase Receipt Item",
		"Purchase Invoice Item",
		"Stock Entry Detail",
		"Journal Entry Account",
		"Material Request Item",
	];

	const cascadeFields = ["boq_header", "boq_structure", "boq_item", "boq_item_stage"];
	const directLaborDesignations = frappe.boot.direct_labor_designations || [];
	let lastKnownScopeToken = null;
	let tokenFetchInFlight = null;

	function cascadeMode() {
		return frappe.boot.enable_boq_cascade_filtering || "Off";
	}

	function cascadeEnabled() {
		return ["On", "Strict"].includes(cascadeMode());
	}

	function tableFieldFor(frm) {
		return childTables[frm.doc.doctype];
	}

	function getRow(cdt, cdn) {
		return locals[cdt] && locals[cdt][cdn];
	}

	function getGridRow(grid, cdt, cdn) {
		let row = getRow(cdt, cdn);
		if (row) return row;

		const gridRow =
			grid &&
			grid.grid_rows &&
			grid.grid_rows.find((candidate) => {
				return candidate && candidate.doc && candidate.doc.name === cdn;
			});
		return (gridRow && gridRow.doc) || null;
	}

	function getScope() {
		if (window.scopeContext && window.scopeContext.enabled) {
			return window.scopeContext.getCurrentScope() || {};
		}
		return (frappe.boot.scope_context && frappe.boot.scope_context.current) || {};
	}

	function rowProject(frm, row) {
		return (row && row.project) || frm.doc.project || getScope().project || null;
	}

	function withScope(filters) {
		if (!cascadeEnabled()) return filters;
		const scope = getScope();
		["company", "cost_center", "project"].forEach((fieldname) => {
			if (scope[fieldname] && !filters[fieldname]) {
				filters[fieldname] = scope[fieldname];
			}
		});
		return filters;
	}

	function withGate(frm, row, filters) {
		if (!cascadeEnabled()) return filters;
		filters.require_gate = true;
		filters.gate_open = gateOpen(frm, row) ? 1 : 0;
		return filters;
	}

	function gateOpen(frm, row) {
		if (!row) return false;
		if (expenseGateDoctypes.includes(row.doctype)) {
			return row.expense_category === "Direct";
		}
		if (row.doctype === "Sales Invoice Item") {
			return !!row.is_progress_billing;
		}
		if (row.doctype === "Timesheet Detail") {
			return !!row.designation && directLaborDesignations.includes(row.designation);
		}
		return true;
	}

	function showNotice(message, indicator) {
		ensureNoticeContainer();
		frappe.show_alert({ message: __(message), indicator: indicator || "orange" }, 5);
	}

	function ensureNoticeContainer() {
		if (document.getElementById("ct-boq-cascade-live-region")) return;
		const node = document.createElement("div");
		node.id = "ct-boq-cascade-live-region";
		node.setAttribute("aria-live", "polite");
		node.setAttribute("aria-atomic", "true");
		node.style.position = "absolute";
		node.style.width = "1px";
		node.style.height = "1px";
		node.style.overflow = "hidden";
		node.style.clip = "rect(1px, 1px, 1px, 1px)";
		document.body.appendChild(node);
	}

	function clearFields(cdt, cdn, fields) {
		fields.forEach((fieldname) => {
			const row = getRow(cdt, cdn);
			if (row && row[fieldname]) {
				frappe.model.set_value(cdt, cdn, fieldname, "");
			}
		});
	}

	function clearDownstream(frm, cdt, cdn, sourceField) {
		if (!cascadeEnabled()) {
			if (sourceField === "boq_item") {
				clearFields(cdt, cdn, ["boq_item_stage"]);
			}
			return;
		}
		if (sourceField === "boq_header") {
			clearFields(cdt, cdn, ["boq_structure", "boq_item", "boq_item_stage"]);
			showNotice("BOQ Structure, Item, and Stage have been cleared.");
		} else if (sourceField === "boq_structure") {
			clearFields(cdt, cdn, ["boq_item", "boq_item_stage"]);
		} else if (sourceField === "boq_item") {
			clearFields(cdt, cdn, ["boq_item_stage"]);
		}
		const tableField = tableFieldFor(frm);
		if (tableField) frm.refresh_field(tableField);
	}

	function clearAllBoqFields(frm, cdt, cdn, message) {
		clearFields(cdt, cdn, cascadeFields);
		if (message) showNotice(message);
		const tableField = tableFieldFor(frm);
		if (tableField) frm.refresh_field(tableField);
	}

	function buildHeaderFilters(frm, row) {
		return withScope(withGate(frm, row, {}));
	}

	function buildStructureFilters(frm, row) {
		const filters = {};
		if (row && row.boq_header) filters.boq_header = row.boq_header;
		return withScope(withGate(frm, row, filters));
	}

	function buildItemFilters(frm, row) {
		const filters = {};
		const project = rowProject(frm, row);
		if (project) filters.project = project;
		if (row && row.boq_header) filters.boq_header = row.boq_header;
		if (row && row.boq_structure) filters.structure = row.boq_structure;
		filters.require_boq_header = true;
		filters.require_structure = true;
		filters.allowed_statuses = ["Frozen", "Locked"];
		return withScope(withGate(frm, row, filters));
	}

	function buildStageFilters(frm, row) {
		const filters = {};
		if (row && row.boq_item) filters.boq_item = row.boq_item;
		if (row && row.boq_header) filters.boq_header = row.boq_header;
		if (row && row.boq_structure) filters.structure = row.boq_structure;
		filters.require_boq_item = true;
		return withScope(withGate(frm, row, filters));
	}

	function queryArgs(query, filters) {
		if (cascadeEnabled()) {
			filters.enforce_scope = true;
		}
		return {
			query: query,
			filters: filters,
		};
	}

	function setChildQueries(frm, tableField) {
		const grid = frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
		if (!grid) return;

		frm.set_query("boq_header", tableField, function (doc, cdt, cdn) {
			return queryArgs(
				"construction.api.boq_link_queries.get_boq_headers",
				buildHeaderFilters(frm, getGridRow(grid, cdt, cdn))
			);
		});

		frm.set_query("boq_structure", tableField, function (doc, cdt, cdn) {
			return queryArgs(
				"construction.api.boq_link_queries.get_boq_structures",
				buildStructureFilters(frm, getGridRow(grid, cdt, cdn))
			);
		});

		frm.set_query("boq_item", tableField, function (doc, cdt, cdn) {
			return queryArgs(
				"construction.api.boq_link_queries.get_boq_items",
				buildItemFilters(frm, getGridRow(grid, cdt, cdn))
			);
		});

		frm.set_query("boq_item_stage", tableField, function (doc, cdt, cdn) {
			return queryArgs(
				"construction.api.boq_link_queries.get_boq_item_stages",
				buildStageFilters(frm, getGridRow(grid, cdt, cdn))
			);
		});

		const boqHeaderField = grid.get_field("boq_header");
		if (boqHeaderField) {
			boqHeaderField.get_query = function (doc, cdt, cdn) {
				return queryArgs(
					"construction.api.boq_link_queries.get_boq_headers",
					buildHeaderFilters(frm, getGridRow(grid, cdt, cdn))
				);
			};
		}

		const boqStructureField = grid.get_field("boq_structure");
		if (boqStructureField) {
			boqStructureField.get_query = function (doc, cdt, cdn) {
				return queryArgs(
					"construction.api.boq_link_queries.get_boq_structures",
					buildStructureFilters(frm, getGridRow(grid, cdt, cdn))
				);
			};
		}

		const boqItemField = grid.get_field("boq_item");
		if (boqItemField) {
			boqItemField.get_query = function (doc, cdt, cdn) {
				return queryArgs(
					"construction.api.boq_link_queries.get_boq_items",
					buildItemFilters(frm, getGridRow(grid, cdt, cdn))
				);
			};
		}

		const boqStageField = grid.get_field("boq_item_stage");
		if (boqStageField) {
			boqStageField.get_query = function (doc, cdt, cdn) {
				return queryArgs(
					"construction.api.boq_link_queries.get_boq_item_stages",
					buildStageFilters(frm, getGridRow(grid, cdt, cdn))
				);
			};
		}
	}

	function fetchScopeToken() {
		if (tokenFetchInFlight) return tokenFetchInFlight;
		tokenFetchInFlight = Promise.resolve(
			frappe.call({ method: "construction.api.boq_link_queries.get_boq_scope_token" })
		)
			.then((r) => {
				const payload = r.message || {};
				lastKnownScopeToken = lastKnownScopeToken || payload.scope_token || null;
				return payload.scope_token || null;
			})
			.finally(() => {
				tokenFetchInFlight = null;
			});
		return tokenFetchInFlight;
	}

	function initializeScopeToken() {
		if (!cascadeEnabled()) return;
		fetchScopeToken().then((token) => {
			lastKnownScopeToken = token;
		});
	}

	function refreshBoqQueries(frm) {
		const tableField = tableFieldFor(frm);
		if (tableField) {
			setChildQueries(frm, tableField);
			frm.refresh_field(tableField);
		}
	}

	function rebindOnScopeChange(frm) {
		initializeScopeToken();
		refreshBoqQueries(frm);
		showNotice("Scope context changed. BOQ dropdowns have been refreshed.", "blue");
	}

	function guardSaveAgainstScopeDrift(frm) {
		if (!cascadeEnabled()) return Promise.resolve();
		return frappe
			.call({ method: "construction.api.boq_link_queries.get_boq_scope_token" })
			.then((r) => {
				const currentToken = (r.message || {}).scope_token || null;
				if (lastKnownScopeToken && currentToken && currentToken !== lastKnownScopeToken) {
					frappe.show_alert(
						{
							message: __(
								"Your scope context has changed. Reloading form to prevent invalid attribution."
							),
							indicator: "orange",
						},
						5
					);
					frm.reload_doc();
					return Promise.reject("scope_drift");
				}
				lastKnownScopeToken = currentToken;
				return currentToken;
			});
	}

	function installSaveGuard(frm) {
		if (!cascadeEnabled() || frm.__ct_boq_save_guard_installed) return;
		frm.__ct_boq_save_guard_installed = true;

		const originalSave = frm.save.bind(frm);
		frm.save = function () {
			const args = arguments;
			return guardSaveAgainstScopeDrift(frm).then(() => originalSave.apply(frm, args));
		};

		const originalSubmit = frm.submit && frm.submit.bind(frm);
		if (originalSubmit) {
			frm.submit = function () {
				const args = arguments;
				return guardSaveAgainstScopeDrift(frm).then(() => originalSubmit.apply(frm, args));
			};
		}
	}

	function applyGateClearing(frm, cdt, cdn) {
		if (!cascadeEnabled()) return;
		const row = getRow(cdt, cdn);
		if (!row) return;
		if (!gateOpen(frm, row)) {
			clearAllBoqFields(
				frm,
				cdt,
				cdn,
				"All BOQ fields have been cleared. Re-select if needed."
			);
		}
	}

	function syncTimesheetDesignation(frm) {
		if (!cascadeEnabled() || frm.doc.doctype !== "Timesheet") return Promise.resolve();
		const tableField = tableFieldFor(frm);
		if (!tableField || !frm.doc.employee) return Promise.resolve();

		return frappe.db.get_value("Employee", frm.doc.employee, "designation").then((r) => {
			const designation = (r.message && r.message.designation) || "";
			(frm.doc[tableField] || []).forEach((row) => {
				if (row.designation !== designation) {
					frappe.model.set_value(row.doctype, row.name, "designation", designation);
				}
			});
			frm.refresh_field(tableField);
		});
	}

	function wireParent(doctype, tableField) {
		frappe.ui.form.on(doctype, {
			setup(frm) {
				setChildQueries(frm, tableField);
				installSaveGuard(frm);
			},
			onload(frm) {
				initializeScopeToken();
				installSaveGuard(frm);
				syncTimesheetDesignation(frm);
			},
			refresh(frm) {
				setChildQueries(frm, tableField);
				installSaveGuard(frm);
				syncTimesheetDesignation(frm);
			},
		});
	}

	function wireChildEvents() {
		childDoctypes.forEach((childDoctype) => {
			frappe.ui.form.on(childDoctype, {
				boq_header(frm, cdt, cdn) {
					clearDownstream(frm, cdt, cdn, "boq_header");
				},
				boq_structure(frm, cdt, cdn) {
					clearDownstream(frm, cdt, cdn, "boq_structure");
				},
				boq_item(frm, cdt, cdn) {
					clearDownstream(frm, cdt, cdn, "boq_item");
				},
				expense_category(frm, cdt, cdn) {
					const row = getRow(cdt, cdn);
					if (row && row.expense_category !== "Direct") {
						if (cascadeEnabled()) {
							clearAllBoqFields(
								frm,
								cdt,
								cdn,
								"All BOQ fields have been cleared. Re-select if needed."
							);
						} else {
							clearFields(cdt, cdn, ["boq_item", "boq_item_stage"]);
						}
					}
				},
				is_progress_billing(frm, cdt, cdn) {
					applyGateClearing(frm, cdt, cdn);
				},
				employee(frm, cdt, cdn) {
					applyGateClearing(frm, cdt, cdn);
				},
				designation(frm, cdt, cdn) {
					applyGateClearing(frm, cdt, cdn);
				},
			});
		});
	}

	function wireScopeChange() {
		$(document).on("scope:changed.ct_boq", function () {
			const frm = cur_frm;
			if (frm && childTables[frm.doc.doctype]) {
				rebindOnScopeChange(frm);
			} else {
				initializeScopeToken();
			}
		});
	}

	frappe.ui.form.on("Timesheet", {
		employee(frm) {
			syncTimesheetDesignation(frm);
		},
	});

	Object.keys(childTables).forEach((doctype) => wireParent(doctype, childTables[doctype]));
	wireChildEvents();
	wireScopeChange();
	$(document).ready(initializeScopeToken);
})();
