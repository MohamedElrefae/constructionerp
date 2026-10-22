// Timesheet direct-labor designation derivation (bounded TS correction).
//
// The direct-labor BOQ gate on Timesheet Detail depends on the row designation
// (`frappe.boot.direct_labor_designations.includes(doc.designation)`). The field
// is hidden and read-only, so it is derived from the selected employee through
// the whitelisted server helper: the acting user does not need Employee read
// permission and only the designation string is returned.
//
// The controller is exported for client regression tests (cache behaviour, race
// handling, event registration and the native add-row wiring are covered by
// construction/tests/test_timesheet_designation_client.js).
//
// Design rules enforced here:
//  * the cache is FORM-LOCAL (never written to frm.doc) and keyed by employee;
//  * every request carries a generation, and a response is applied only when it
//    is still the current request for the current employee;
//  * the rows are resolved at application time, so rows added/removed meanwhile
//    are handled;
//  * writability is re-checked at every mutation point (including cache hits and
//    clears), so a pending callback cannot mutate a submitted or read-only form;
//  * a failed request clears the cached state AND the stale row designation, while
//    an obsolete failure never clears a newer employee's valid state;
//  * changing the employee invalidates the previous designation immediately;
//  * the native add-row hook (the child field's `on_add_row`) is wired, so a row
//    added after the employee was selected is still derived.

(function (root) {
	const STATE_KEY = "__f44_ts_designation_state";

	function isWritable(frm) {
		if (!frm || !frm.doc) {
			return false;
		}
		if (frm.doc.docstatus) {
			// Submitted / cancelled documents are immutable.
			return false;
		}
		if (frm.read_only === true || frm.read_only === 1) {
			// Native read-only form state (workflow / boot / set_read_only).
			return false;
		}
		if (typeof frm.read_only === "function" && frm.read_only()) {
			return false;
		}
		if (typeof frm.is_readonly === "function" && frm.is_readonly()) {
			return false;
		}
		if (frm.is_readonly === true) {
			return false;
		}
		return true;
	}

	function createController(frm, api) {
		const state = frm[STATE_KEY] || (frm[STATE_KEY] = { cache: {}, generation: 0 });

		function currentRows(cdn) {
			const rows = (frm.doc && frm.doc.time_logs) || [];
			return cdn ? rows.filter((row) => row.name === cdn) : rows.slice();
		}

		function setRows(rows, designation) {
			if (!isWritable(frm)) {
				return false;
			}
			let changed = false;
			rows.forEach((row) => {
				if ((row.designation || null) !== designation) {
					row.designation = designation;
					changed = true;
				}
			});
			if (changed && frm.refresh_field) {
				frm.refresh_field("time_logs");
			}
			return changed;
		}

		function clearRows(cdn) {
			return setRows(currentRows(cdn), null);
		}

		function apply(cdn) {
			if (!isWritable(frm)) {
				return;
			}
			const employee = frm.doc.employee;
			if (!employee) {
				// No employee selected: drop any stale designation.
				state.generation += 1;
				clearRows(cdn);
				return;
			}
			if (Object.prototype.hasOwnProperty.call(state.cache, employee)) {
				setRows(currentRows(cdn), state.cache[employee]);
				return;
			}
			const generation = ++state.generation;
			const requested = employee;

			Promise.resolve()
				.then(() => api(requested))
				.then((response) => {
					if (frm[STATE_KEY] !== state) return;
					if (state.generation !== generation) return;
					if (!frm.doc || frm.doc.employee !== requested) return;
					if (!isWritable(frm)) return;
					const designation = (response && response.designation) || null;
					state.cache[requested] = designation;
					setRows(currentRows(cdn), designation);
				})
				.catch(() => {
					if (frm[STATE_KEY] !== state) return;
					if (state.generation !== generation) return;
					delete state.cache[requested];
					// The failed lookup must not leave a stale gate visible, but an
					// obsolete failure must not clear a newer employee's valid state.
					if (frm.doc && frm.doc.employee === requested) {
						clearRows(cdn);
					}
				});
		}

		return {
			apply: apply,
			clear: () => clearRows(),
			invalidate: () => {
				// The employee changed: the previous designation is stale now.
				state.generation += 1;
				clearRows();
			},
			state: state,
		};
	}

	function wireAddRow(frm, controller) {
		const df =
			frm.fields_dict && frm.fields_dict.time_logs ? frm.fields_dict.time_logs.df : null;
		if (!df) {
			return;
		}
		if (df.__f44_ts_add_row_wired) {
			// Installation is idempotent per form/field: a repeated refresh must not
			// wrap the handler again (one Add Row must trigger one derivation).
			df.__f44_ts_add_row_controller = controller;
			return;
		}
		const previous = df.on_add_row;
		df.__f44_ts_add_row_wired = true;
		df.__f44_ts_add_row_controller = controller;
		df.on_add_row = function () {
			if (typeof previous === "function") {
				// Keep the previous handler's context and arguments.
				previous.apply(this, arguments);
			}
			const active = df.__f44_ts_add_row_controller;
			if (active) {
				active.apply();
			}
		};
	}

	function install(frappeRef) {
		const fetchDesignation = (employee) =>
			frappeRef
				.call({
					method: "construction.services.timesheet_designation.get_timesheet_employee_designation",
					args: { employee: employee },
				})
				.then((response) => (response && response.message) || {});

		const controllerFor = (frm) => createController(frm, fetchDesignation);
		const handlers = {};

		handlers["Timesheet::employee"] = (frm) => {
			const controller = controllerFor(frm);
			controller.invalidate();
			controller.apply();
		};
		handlers["Timesheet::refresh"] = (frm) => {
			const controller = controllerFor(frm);
			wireAddRow(frm, controller);
			controller.apply();
		};
		handlers["Timesheet::time_logs"] = (frm) => controllerFor(frm).apply();
		handlers["Timesheet Detail::setup"] = (frm, cdt, cdn) => controllerFor(frm).apply(cdn);
		handlers["Timesheet Detail::refresh"] = (frm, cdt, cdn) => controllerFor(frm).apply(cdn);

		handlers["Timesheet Detail::time_logs_add"] = function (frm, cdt, cdn) {
			// Native form-backed grid add-row event (frappe form/grid.js::add_new_row ->
			// frm.script_manager.trigger("<fieldname>_add", doctype, name)). The row identity
			// is resolved from the live document, so a stale argument cannot mis-target.
			const controller = controllerFor(frm);
			controller.apply(cdn || null);
		};

		frappeRef.ui.form.on("Timesheet", {
			employee: handlers["Timesheet::employee"],
			refresh: handlers["Timesheet::refresh"],
			time_logs: handlers["Timesheet::time_logs"],
		});
		frappeRef.ui.form.on("Timesheet Detail", {
			setup: handlers["Timesheet Detail::setup"],
			refresh: handlers["Timesheet Detail::refresh"],
			// Pinned frappe ScriptManager.trigger(event_name, doctype, ...) resolves
			// frappe.ui.form.handlers[doctype][event_name] -> the CHILD doctype registry.
			time_logs_add: handlers["Timesheet Detail::time_logs_add"],
		});

		return handlers;
	}

	const controller = {
		createController: createController,
		install: install,
		isWritable: isWritable,
		STATE_KEY: STATE_KEY,
	};

	if (typeof module !== "undefined" && module.exports) {
		module.exports = controller;
	} else {
		root.f44TSDesignation = controller;
	}

	if (typeof frappe !== "undefined" && frappe.ui && frappe.ui.form) {
		install(frappe);
	}
})(typeof globalThis !== "undefined" ? globalThis : this);
