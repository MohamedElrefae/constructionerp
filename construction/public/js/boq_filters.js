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
	const mountedBoqForms = new Set();
	let lastKnownScopeToken = null;
	let tokenFetchInFlight = null;

	function debounce(fn, wait) {
		let timer;
		return function (...args) {
			clearTimeout(timer);
			timer = setTimeout(() => fn.apply(this, args), wait);
		};
	}

	function setGridAccent(frm, cdt, cdn, fieldname, active, blocked) {
		const grid =
			frm.fields_dict[tableFieldFor(frm)] && frm.fields_dict[tableFieldFor(frm)].grid;
		if (!grid) return;
		const gridRow = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
		if (!gridRow) return;
		const $wrapper =
			gridRow.wrapper &&
			$(gridRow.wrapper).find(`.frappe-control[data-fieldname="${fieldname}"]`);
		if (!$wrapper || !$wrapper.length) return;
		$wrapper.toggleClass("ct-boq-step-accent", !!active);
		$wrapper.toggleClass("ct-boq-step-blocked", !!blocked);
	}

	function markGridFieldBlocked(frm, cdt, cdn, fieldname, blocked, hint) {
		const tableField = tableFieldFor(frm);
		if (!tableField) return;
		const grid = frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
		if (!grid) return;
		const gridRow = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
		if (!gridRow || !gridRow.fields_dict) return;
		const field = gridRow.fields_dict[fieldname];
		if (!field) return;
		field.df.only_select = !!blocked;
		field.__ct_boq_blocked = !!blocked;
		field.df.filter_description = blocked ? hint : "";
		if (typeof field.set_description === "function") {
			field.set_description(blocked ? hint : "");
		}
	}

	function setGridInlineHint(frm, cdt, cdn, fieldname, hint, blocked) {
		const grid =
			frm.fields_dict[tableFieldFor(frm)] && frm.fields_dict[tableFieldFor(frm)].grid;
		if (!grid) return;
		const gridRow = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
		if (!gridRow) return;
		const $wrapper =
			gridRow.wrapper &&
			$(gridRow.wrapper).find(`.frappe-control[data-fieldname="${fieldname}"]`);
		if (!$wrapper || !$wrapper.length) return;
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

	function applyGridGuidance(frm, cdt, cdn) {
		const row = getRow(cdt, cdn);
		if (!row) return;
		const gateIsOpen = gateOpen(frm, row);
		const hasProject = Boolean(rowProject(frm, row));
		const hasBoqHeader = Boolean(row.boq_header);
		const hasBoqStructure = Boolean(row.boq_structure);
		const hasBoqItem = Boolean(row.boq_item);
		const hasBoqItemStage = Boolean(row.boq_item_stage);

		// Gate closed → all BOQ fields muted (no accent, not blocked — just visually inert)
		if (!gateIsOpen) {
			["boq_header", "boq_structure", "boq_item", "boq_item_stage"].forEach((fn) => {
				setGridAccent(frm, cdt, cdn, fn, false, false);
				markGridFieldBlocked(frm, cdt, cdn, fn, false, "");
				setGridInlineHint(frm, cdt, cdn, fn, null, false);
			});
			return;
		}

		// boq_header: accent when project set but header empty; blocked when project empty
		setGridAccent(frm, cdt, cdn, "boq_header", !hasBoqHeader && hasProject, !hasProject);
		markGridFieldBlocked(frm, cdt, cdn, "boq_header", !hasProject, __("Select Project first"));
		setGridInlineHint(
			frm,
			cdt,
			cdn,
			"boq_header",
			!hasProject
				? __("Select Project first")
				: !hasBoqHeader
				? __("Select BOQ Header first")
				: null,
			!hasProject
		);

		// boq_structure: blocked when header empty; accent when header set but structure empty
		setGridAccent(
			frm,
			cdt,
			cdn,
			"boq_structure",
			!hasBoqStructure && hasBoqHeader,
			!hasBoqHeader
		);
		markGridFieldBlocked(
			frm,
			cdt,
			cdn,
			"boq_structure",
			!hasBoqHeader,
			__("Select BOQ Header first")
		);
		setGridInlineHint(
			frm,
			cdt,
			cdn,
			"boq_structure",
			!hasBoqHeader
				? __("Select BOQ Header first")
				: !hasBoqStructure
				? __("Select BOQ Structure first")
				: null,
			!hasBoqHeader
		);

		// boq_item: blocked when structure empty; accent when structure set but item empty
		setGridAccent(frm, cdt, cdn, "boq_item", !hasBoqItem && hasBoqStructure, !hasBoqStructure);
		markGridFieldBlocked(
			frm,
			cdt,
			cdn,
			"boq_item",
			!hasBoqStructure,
			__("Select BOQ Structure first — items link to leaf structures only")
		);
		setGridInlineHint(
			frm,
			cdt,
			cdn,
			"boq_item",
			!hasBoqStructure
				? __("Select BOQ Structure first")
				: !hasBoqItem
				? __("Select BOQ Item first")
				: null,
			!hasBoqStructure
		);
		if (hasBoqStructure) {
			const tableField = tableFieldFor(frm);
			const grid =
				tableField && frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
			const gridRow = grid && grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
			const field = gridRow && gridRow.fields_dict && gridRow.fields_dict["boq_item"];
			if (field && typeof field.set_description === "function") {
				field.set_description(__("BOQ Items are linked to leaf Structure nodes only."));
			}
		}

		// boq_item_stage: accented when item is set but stage not yet chosen; blocked when no item
		setGridAccent(
			frm,
			cdt,
			cdn,
			"boq_item_stage",
			!hasBoqItemStage && hasBoqItem,
			!hasBoqItem
		);
		markGridFieldBlocked(
			frm,
			cdt,
			cdn,
			"boq_item_stage",
			!hasBoqItem,
			__("Select BOQ Item first")
		);
		setGridInlineHint(
			frm,
			cdt,
			cdn,
			"boq_item_stage",
			!hasBoqItem ? __("Select BOQ Item first") : null,
			!hasBoqItem
		);
	}

	const applyGridGuidanceDebounced = debounce(function (frm, cdt, cdn) {
		applyGridGuidance(frm, cdt, cdn);
	}, 50);

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
			return window.scopeContext.getValidatedCurrentScope();
		}
		return {};
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
		filters.exclude_zero_revised = true;
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

	// ---------------------------------------------------------------------------
	// The BOQ Item Link query of the child grids.
	//
	// Frappe stores the query of a child-table Link field in the grid field info
	// (`grid.fieldinfo[fieldname]`): `frm.set_query(field, parent, fn)` writes
	// `grid.get_field(field).get_query = fn`, and both the inline grid control
	// (grid_row.js) and the expanded row form (grid_row_form.js) copy that
	// value onto the field control when the row is created or expanded.
	//
	// ERPNext provisions an accounting dimension for the BOQ Item DocType
	// (construction/install.py::setup_boq_accounting_dimension derives the
	// fieldname "boq_item" from the dimension label) and installs its own query
	// for that field from an ASYNCHRONOUS server callback
	// (erpnext/public/js/utils/dimension_tree_filter.js::setup_child_filters),
	// i.e. after this file installed the BOQ query. That overwrite dropped the
	// BOQ omission / header / structure / status / scope filters and let an
	// omitted BOQ Item be offered in the native dropdown.
	//
	// "boq_item" is the ONLY colliding field: it is the only BOQ field that
	// ERPNext treats as an accounting dimension. The other three BOQ fields
	// keep the plain native query mechanism, so no foreign writer is frozen
	// anywhere else.
	//
	// The pinned ERPNext query is NOT discarded. It carries the account of the
	// current row, and that account selects the applicable Accounting
	// Dimension Filter (Allow / Restrict) of the "BOQ Item" dimension. The
	// composed query therefore keeps BOTH policies:
	//   * the BOQ cascade filters (omission / header / structure / status /
	//     scope), and
	//   * the native per-account dimension restriction, applied on the server by
	//     construction/api/boq_link_queries.py::get_boq_items.
	//
	// The native query is asked for the account of the current row. When it
	// cannot answer, the search is CLOSED: the BOQ query never continues
	// without the native per-account policy.
	// ---------------------------------------------------------------------------
	// The accounting dimension that ERPNext provisions for the BOQ Item DocType
	// (construction/install.py::setup_boq_accounting_dimension derives the
	// fieldname "boq_item" from the dimension label). The native query of the
	// "boq_item" field answers for exactly this dimension.
	const BOQ_ITEM_DIMENSION = "boq_item";

	function boqItemQueryState(grid) {
		if (!grid.__ct_boq_item_query_state) {
			grid.__ct_boq_item_query_state = {
				appQuery: null,
				nativeQuery: null,
				nativeWrites: 0,
				pinned: false,
				nativePolicyUnavailableNotified: false,
			};
		}
		return grid.__ct_boq_item_query_state;
	}

	// The outcome of the captured native ERPNext query.
	//
	//   { account: "<account>" }  the native per-account policy applies.
	//   { account: null }         no native policy applies: no native query is
	//                              installed, or the row carries no account.
	//   { account: null, failed: true }
	//                              the native policy could NOT be determined.
	//
	// A failure must NEVER be reported as "no native policy". Reporting it that
	// way drops the per-account Accounting Dimension Filter (Allow / Restrict)
	// of the BOQ Item dimension and silently widens the search. The caller
	// closes the search instead of continuing without the policy.
	function nativeRowAccount(state, doc, cdt, cdn) {
		if (!state.nativeQuery) return { account: null };

		let nativeArgs = null;
		try {
			nativeArgs = state.nativeQuery(doc, cdt, cdn);
		} catch (error) {
			// The pinned vendor query reads the row from `locals` and fails when
			// the row is not registered there. The failure is reported, not
			// swallowed: the caller closes the search.
			return { account: null, failed: true, error: error };
		}

		const nativeFilters = nativeArgs && nativeArgs.filters;
		if (!nativeFilters || typeof nativeFilters !== "object") {
			// An unrecognised answer: the native policy is unknown.
			return { account: null, failed: true, error: null };
		}
		if (nativeFilters.dimension !== BOQ_ITEM_DIMENSION) {
			// The captured query does not answer for the BOQ Item dimension, so
			// the native policy of that dimension cannot be determined.
			return { account: null, failed: true, error: null };
		}

		const account = nativeFilters.account;
		if (account === undefined || account === null || account === "") {
			// A row without an account has no native dimension policy.
			return { account: null };
		}
		if (typeof account !== "string") {
			return { account: null, failed: true, error: null };
		}
		return { account: account };
	}

	// The native policy could not be determined. The user is told once that the
	// dropdown was closed and the cause is logged for support. The search
	// itself is closed by the caller, so no BOQ Item is ever offered without the
	// native per-account restriction.
	function notifyNativePolicyUnavailable(state, error) {
		if (error && typeof console !== "undefined" && console && console.error) {
			console.error("[BOQ] the native accounting dimension policy is unavailable", error);
		}
		if (state.nativePolicyUnavailableNotified) return;
		state.nativePolicyUnavailableNotified = true;
		showNotice(
			"BOQ Item dropdown closed: the accounting dimension filter of the row could not be applied.",
			"red"
		);
	}

	function pinBoqItemQuery(grid, appQueryFn) {
		const info = grid.get_field("boq_item");
		if (!info) return;
		const state = boqItemQueryState(grid);
		state.appQuery = appQueryFn;
		if (!state.pinned) {
			// The vendor may have installed its query before this app ran.
			const existing = info.get_query;
			if (typeof existing === "function") {
				state.nativeQuery = existing;
				state.nativeWrites += 1;
			}
			state.pinned = true;
		}
		Object.defineProperty(info, "get_query", {
			configurable: true,
			enumerable: true,
			get() {
				return function (doc, cdt, cdn) {
					const args = (state.appQuery && state.appQuery(doc, cdt, cdn)) || {};
					const filters = Object.assign({}, args.filters);
					const native = nativeRowAccount(state, doc, cdt, cdn);
					if (native.failed) {
						// The native per-account Accounting Dimension Filter could
						// not be determined. Continuing would offer BOQ Items
						// without that policy, so the search is closed explicitly
						// (the server denies every item of a closed gate) instead
						// of failing open with an account-less search.
						notifyNativePolicyUnavailable(state, native.error);
						filters.require_gate = true;
						filters.gate_open = 0;
						return { query: args.query, filters: filters };
					}
					if (native.account) filters.account = native.account;
					return { query: args.query, filters: filters };
				};
			},
			set(value) {
				// The pinned ERPNext accounting-dimension setup writes its query
				// here. It is kept as the source of the native account policy
				// instead of replacing the BOQ cascade query.
				if (typeof value === "function") {
					state.nativeQuery = value;
					state.nativeWrites += 1;
				}
			},
		});
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

		frm.set_query("boq_item_stage", tableField, function (doc, cdt, cdn) {
			return queryArgs(
				"construction.api.boq_link_queries.get_boq_item_stages",
				buildStageFilters(frm, getGridRow(grid, cdt, cdn))
			);
		});

		// The BOQ Item field is pinned (see pinBoqItemQuery): it is the only BOQ
		// field that ERPNext installs an accounting-dimension query on.
		pinBoqItemQuery(grid, function (doc, cdt, cdn) {
			return queryArgs(
				"construction.api.boq_link_queries.get_boq_items",
				buildItemFilters(frm, getGridRow(grid, cdt, cdn))
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
					frappe.call({
						method: "construction.api.boq_link_queries.log_boq_scope_drift",
						args: {
							form_doctype: frm.doc.doctype,
							form_name: frm.doc.name,
							previous_scope: lastKnownScopeToken,
							current_scope: currentToken,
						},
						async: true,
						freeze: false,
					});
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
				trackBoqForm(frm);
				setChildQueries(frm, tableField);
				installSaveGuard(frm);
			},
			onload(frm) {
				trackBoqForm(frm);
				initializeScopeToken();
				installSaveGuard(frm);
				syncTimesheetDesignation(frm);
			},
			refresh(frm) {
				trackBoqForm(frm);
				setChildQueries(frm, tableField);
				installSaveGuard(frm);
				syncTimesheetDesignation(frm);
				(frm.doc[tableField] || []).forEach((row) => {
					applyGridGuidance(frm, row.doctype, row.name);
				});
				setTimeout(() => applyCollapsedRowsGuidance(frm), 200);
			},
			onload_post_render(frm) {
				const tableField = tableFieldFor(frm);
				const grid = frm.fields_dict[tableField] && frm.fields_dict[tableField].grid;
				if (!grid) return;
				(frm.doc[tableField] || []).forEach((row) => {
					applyGridGuidance(frm, row.doctype, row.name);
				});
				setTimeout(() => {
					(frm.doc[tableField] || []).forEach((row) => {
						applyGridGuidance(frm, row.doctype, row.name);
					});
				}, 150);
				setTimeout(() => {
					(frm.doc[tableField] || []).forEach((row) => {
						applyGridGuidance(frm, row.doctype, row.name);
					});
					applyCollapsedRowsGuidance(frm);
				}, 600);
			},
			project(frm) {
				const tableField = tableFieldFor(frm);
				if (!tableField) return;
				(frm.doc[tableField] || []).forEach((row) => {
					clearFields(row.doctype, row.name, [
						"boq_header",
						"boq_structure",
						"boq_item",
						"boq_item_stage",
					]);
					applyGridGuidance(frm, row.doctype, row.name);
				});
				frm.refresh_field(tableField);
			},
		});
	}

	function wireChildEvents() {
		childDoctypes.forEach((childDoctype) => {
			frappe.ui.form.on(childDoctype, {
				form_render(frm, cdt, cdn) {
					applyGridGuidance(frm, cdt, cdn);
					setTimeout(() => applyCollapsedRowsGuidance(frm), 100);
				},
				boq_header(frm, cdt, cdn) {
					clearDownstream(frm, cdt, cdn, "boq_header");
					applyGridGuidance(frm, cdt, cdn);
				},
				boq_structure(frm, cdt, cdn) {
					clearDownstream(frm, cdt, cdn, "boq_structure");
					applyGridGuidance(frm, cdt, cdn);
				},
				boq_item(frm, cdt, cdn) {
					clearDownstream(frm, cdt, cdn, "boq_item");
					applyGridGuidance(frm, cdt, cdn);
				},
				boq_item_stage(frm, cdt, cdn) {
					applyGridGuidance(frm, cdt, cdn);
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
					applyGridGuidanceDebounced(frm, cdt, cdn);
				},
				is_progress_billing(frm, cdt, cdn) {
					applyGateClearing(frm, cdt, cdn);
					applyGridGuidance(frm, cdt, cdn);
				},
				employee(frm, cdt, cdn) {
					applyGateClearing(frm, cdt, cdn);
					applyGridGuidanceDebounced(frm, cdt, cdn);
				},
				designation(frm, cdt, cdn) {
					applyGateClearing(frm, cdt, cdn);
					applyGridGuidance(frm, cdt, cdn);
				},
			});
		});
	}

	function wireScopeChange() {
		frappe.router.on("change", pruneUnmountedBoqForms);
		$(document).on("scope:changed.ct_boq", function () {
			const forms = pruneUnmountedBoqForms();
			if (!forms.length) initializeScopeToken();
			forms.forEach(rebindOnScopeChange);
		});
	}

	function trackBoqForm(frm) {
		if (frm && childTables[frm.doc?.doctype]) mountedBoqForms.add(frm);
	}

	function pruneUnmountedBoqForms() {
		const mounted = [];
		mountedBoqForms.forEach((frm) => {
			const wrapper = frm.wrapper && (frm.wrapper[0] || frm.wrapper);
			if (!wrapper || !wrapper.isConnected) {
				mountedBoqForms.delete(frm);
				return;
			}
			if (!childTables[frm.doc?.doctype]) {
				mountedBoqForms.delete(frm);
				return;
			}
			mounted.push(frm);
		});
		return mounted;
	}

	function applyCollapsedRowsGuidance(frm) {
		const tableField = tableFieldFor(frm);
		if (!tableField) return;
		const $grid = $(frm.fields_dict[tableField] && frm.fields_dict[tableField].wrapper);
		if (!$grid.length) return;
		const rows = frm.doc[tableField] || [];
		$grid.find(".grid-row:not(.open)").each(function () {
			const $row = $(this);
			const dataRowIndex = $row.attr("data-row-index");
			const row = rows[parseInt(dataRowIndex, 10)];
			if (!row) return;
			const gateIsOpen = gateOpen(frm, row);
			const hasProject = Boolean(rowProject(frm, row));
			const hasBoqHeader = Boolean(row.boq_header);
			const hasBoqStructure = Boolean(row.boq_structure);
			const hasBoqItem = Boolean(row.boq_item);
			const anyBlocked =
				gateIsOpen && (!hasProject || !hasBoqHeader || !hasBoqStructure || !hasBoqItem);
			$row.toggleClass("ct-boq-row-blocked", !!anyBlocked);
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
