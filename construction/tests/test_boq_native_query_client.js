const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const { spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");

// ---------------------------------------------------------------------------
// F44 native BOQ query replacement — client regression.
//
// The reported defect (A1) is that the native BOQ Item dropdown of a
// Material Request offered an omitted BOQ Item because the effective query of
// the `boq_item` grid field was NOT the BOQ cascade query but ERPNext's
// accounting-dimension query:
//
//     {"query": "erpnext.controllers.queries.get_filtered_dimensions",
//      "filters": {"dimension": "boq_item", "company": "<company>"}}
//
// i.e. no omission / header / structure / status / scope filter at all.
//
// Cause (established against the pinned vendor):
//
//   * construction/install.py::setup_boq_accounting_dimension provisions an
//     ERPNext "Accounting Dimension" whose label is "BOQ Item", so ERPNext
//     derives the fieldname "boq_item" for it.
//   * erpnext/public/js/controllers/buying.js (BuyingController.onload ->
//     setup_queries) calls
//     erpnext.accounts.dimensions.setup_dimension_filters(frm, doctype), which
//     resolves an ASYNCHRONOUS server call and only afterwards calls
//     setup_child_filters(frm, "<Child DocType>", "<table>", "boq_item").
//   * setup_child_filters calls frm.set_query("boq_item", "<table>", fn), and
//     the pinned Frappe form.js::set_query writes
//     `grid.get_field(fieldname).get_query = fn`, i.e. it overwrites the query
//     that construction/public/js/boq_filters.js had installed.
//   * the pinned Frappe grid reads that value when a row control is created
//     (grid_row.js) and when a row is expanded (grid_row_form.js), so a row
//     expanded after the asynchronous dimension setup receives the ERPNext
//     query.
//
// The regression below reproduces that path with the REAL pinned vendor files
// (the ERPNext dimension setup is executed, not re-implemented) and fails when
// the BOQ cascade query is replaced.
//
// Provenance: every vendor file is digest-verified against the pinned vendor
// HEAD (Frappe 2871914b69b6e14a4b023d9b7cc52dc3e269cc1b, ERPNext
// 7474d9e786277383de1242ab882f16856d17a9c9). A missing or mismatched vendor
// file FAILS the run; it is never silently substituted.
// ---------------------------------------------------------------------------

// Pinned vendor files, keyed by vendor app and by the path INSIDE that app
// root (a bench app root holds the python package, e.g. apps/frappe/frappe/...).
const PINNED_VENDOR_FILES = {
	frappe: {
		"frappe/public/js/frappe/form/form.js":
			"3d883c7b6baf9113008b3c87a417350dd8fdafc60a102bd6e8321f8845b3e9cd",
		"frappe/public/js/frappe/form/grid.js":
			"1d0472f0e7fa1c37fe45bbbaf47b00a50205a59103dcac170896c032fd402118",
		"frappe/public/js/frappe/form/grid_row.js":
			"9e7de34e9a306b42509f40573ff678d799391b5f4c2d6bedf08f48c948a6be34",
		"frappe/public/js/frappe/form/grid_row_form.js":
			"6af04d1b1346e0a7c27925f868390ce83cdcdd89e2a4170ac72e95a9e359e4fb",
		"frappe/public/js/frappe/form/layout.js":
			"87425319ff0d6ae308f835a3ee8a9ae9cf54d90cda388feeda4cac75589ca1bf",
		"frappe/public/js/frappe/form/controls/link.js":
			"02a3405293ae6624030ecfbcc1a76a78b8e502aaa479de5c931e0e494075e2af",
	},
	erpnext: {
		"erpnext/public/js/utils/dimension_tree_filter.js":
			"7b3f32dfcd8145bb4604a8a4eb02940241512f2c3611283887fbfeb2e460146a",
		"erpnext/public/js/queries.js":
			"50a139ba5e4ac38ea1c3235583cf0ed220d81cecb3ac054dc3a0acb37a2116e5",
		"erpnext/buying/doctype/purchase_order_item/purchase_order_item.json":
			"0da8a88a96fd392500f20d86b0a3ecd1514fb4af92cce8b0b77657837b0de01c",
		"erpnext/stock/doctype/purchase_receipt_item/purchase_receipt_item.json":
			"7dfa7e834701f2b932623491dd8a3d7fd7b9430f55eb1c1cc07efe6ad661592e",
		"erpnext/accounts/doctype/purchase_invoice_item/purchase_invoice_item.json":
			"4c88eb2a1291dc59cfbd527a6505569dc6e90808dd860f886268c64f927ac4a9",
		"erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json":
			"73519a9dbb694e6ed2bcec41a8e4f80c7169a100278e1daf1f0675853739fd53",
		"erpnext/stock/doctype/stock_entry_detail/stock_entry_detail.json":
			"8f75633127931a5ac5f2713f8fdc2c531a2bc7ac504b40e3ab128513af9e1e4f",
		"erpnext/projects/doctype/timesheet_detail/timesheet_detail.json":
			"5ee38ef48f0df5fa68448137f79e434c0e9c42b379d6281f31e39f3991a716be",
		"erpnext/accounts/doctype/journal_entry_account/journal_entry_account.json":
			"d3abcfaea902140cd746af056e36c7cdea9bdd171775ff4c6c5941ca6cb4ae66",
		"erpnext/stock/doctype/material_request_item/material_request_item.json":
			"203485b3a735a882cd8e54133cb9952d7861e0d59ca8af4afd938c204a515b38",
	},
};

const VENDOR_ROOT_ENV = "F44_PINNED_VENDOR_ROOT";

// A child process of the hermetic vendor tests must not spawn children again.
const HERMETIC_CHILD_ENV = "F44_VENDOR_HERMETIC_CHILD";
const IS_HERMETIC_CHILD = process.env[HERMETIC_CHILD_ENV] === "1";

// The configured vendor root is AUTHORITATIVE.
//
// When F44_PINNED_VENDOR_ROOT is set it must name a directory that holds the
// pinned frappe/ and erpnext/ apps, and every pinned file must match its
// digest. A missing, empty, non-directory, unreadable or tampered root FAILS
// the run: the test never falls back to a sibling or mirror copy of the
// vendor, because such a fallback would silently qualify a different vendor
// than the reviewed one.
//
// Only an UNSET environment may use the sibling discovery of a bench layout.
function resolveVendorRoot() {
	const configured = process.env[VENDOR_ROOT_ENV];
	if (configured === undefined) {
		return null;
	}

	const trimmed = String(configured).trim();
	if (!trimmed) {
		throw new Error(
			VENDOR_ROOT_ENV +
				" is set but empty. The configured vendor root is authoritative and must " +
				"name the directory that holds the pinned frappe/ and erpnext/ apps."
		);
	}

	const resolved = path.resolve(trimmed);
	let stats = null;
	try {
		stats = fs.statSync(resolved);
	} catch (error) {
		throw new Error(
			VENDOR_ROOT_ENV + " points to " + resolved + " which cannot be read: " + error.message
		);
	}
	if (!stats.isDirectory()) {
		throw new Error(
			VENDOR_ROOT_ENV + " must point to a directory, but " + resolved + " is not one."
		);
	}
	for (const app of ["frappe", "erpnext"]) {
		const appRoot = path.join(resolved, app);
		let appStats = null;
		try {
			appStats = fs.statSync(appRoot);
		} catch (error) {
			throw new Error(
				VENDOR_ROOT_ENV +
					" must contain the pinned " +
					app +
					" app directory; " +
					appRoot +
					" cannot be read: " +
					error.message
			);
		}
		if (!appStats.isDirectory()) {
			throw new Error(
				VENDOR_ROOT_ENV +
					" must contain the pinned " +
					app +
					" app directory; " +
					appRoot +
					" is not a directory."
			);
		}
	}
	return resolved;
}

// Resolved at load time: an unusable configured root must fail the run before
// any test can report a green result.
const VENDOR_ROOT = resolveVendorRoot();

function vendorRoots() {
	if (VENDOR_ROOT) {
		// Authoritative: exactly one root, no sibling or mirror fallback.
		return [VENDOR_ROOT];
	}
	// Only an unset environment may use the verified sibling discovery of a
	// bench layout: <bench>/apps/construction -> <bench>/apps/<app>.
	return [path.resolve(root, ".."), path.resolve(root, "..", "..")];
}

// Reads a pinned vendor file. The key is "<vendor app>" plus the path inside
// that app root (a bench app root holds the python package, e.g.
// apps/frappe/frappe/public/js/...).
function readPinnedVendor(app, appRelative) {
	const expected = (PINNED_VENDOR_FILES[app] || {})[appRelative];
	if (!expected) {
		throw new Error("unpinned vendor file requested: " + app + "/" + appRelative);
	}
	const tried = [];
	for (const base of vendorRoots()) {
		const candidate = path.join(base, app, appRelative);
		if (!fs.existsSync(candidate)) {
			tried.push(candidate);
			continue;
		}
		let content = null;
		try {
			content = fs.readFileSync(candidate);
		} catch (error) {
			throw new Error(
				"pinned vendor file is not readable at " +
					candidate +
					": " +
					(error && error.message ? error.message : String(error))
			);
		}
		const actual = crypto.createHash("sha256").update(content).digest("hex");
		if (actual !== expected) {
			throw new Error(
				"pinned vendor file mismatch at " +
					candidate +
					": sha256 " +
					actual +
					" != pinned " +
					expected
			);
		}
		return content.toString("utf8");
	}
	throw new Error(
		"pinned vendor file not found: " +
			app +
			"/" +
			appRelative +
			" (tried " +
			tried.join(", ") +
			")"
	);
}
// The BOQ-enabled child grids of the app, and the ERPNext child doctype each
// one hosts. Mirrors construction/public/js/boq_filters.js (childTables).
const BOQ_PARENTS = [
	{ doctype: "Purchase Order", table: "items", child: "Purchase Order Item" },
	{ doctype: "Purchase Receipt", table: "items", child: "Purchase Receipt Item" },
	{ doctype: "Purchase Invoice", table: "items", child: "Purchase Invoice Item" },
	{ doctype: "Sales Invoice", table: "items", child: "Sales Invoice Item" },
	{ doctype: "Stock Entry", table: "items", child: "Stock Entry Detail" },
	{ doctype: "Timesheet", table: "time_logs", child: "Timesheet Detail" },
	{ doctype: "Journal Entry", table: "accounts", child: "Journal Entry Account" },
	{ doctype: "Material Request", table: "items", child: "Material Request Item" },
];

const VENDOR_JSON_FOR_CHILD = {
	"Purchase Order Item": "erpnext/buying/doctype/purchase_order_item/purchase_order_item.json",
	"Purchase Receipt Item":
		"erpnext/stock/doctype/purchase_receipt_item/purchase_receipt_item.json",
	"Purchase Invoice Item":
		"erpnext/accounts/doctype/purchase_invoice_item/purchase_invoice_item.json",
	"Sales Invoice Item": "erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json",
	"Stock Entry Detail": "erpnext/stock/doctype/stock_entry_detail/stock_entry_detail.json",
	"Timesheet Detail": "erpnext/projects/doctype/timesheet_detail/timesheet_detail.json",
	"Journal Entry Account":
		"erpnext/accounts/doctype/journal_entry_account/journal_entry_account.json",
	"Material Request Item":
		"erpnext/stock/doctype/material_request_item/material_request_item.json",
};

// The BOQ custom fields that construction/install.py adds to every
// BOQ_TRANSACTION_CHILD_DOCTYPES child doctype.
const APP_BOQ_CUSTOM_FIELDS = [
	{ fieldname: "boq_item", fieldtype: "Link", options: "BOQ Item" },
	{ fieldname: "boq_item_stage", fieldtype: "Link", options: "BOQ Item Stage" },
	{
		fieldname: "expense_category",
		fieldtype: "Select",
		options: "\nDirect\nIndirect\nOverhead\nCapital",
	},
];

const SCOPE = {
	company: "F44-20261018-426ECCCD-Company-A",
	project: "PROJ-0115",
	cost_center: null,
};

const BOQ_ITEM_QUERY = "construction.api.boq_link_queries.get_boq_items";
const ERPNEXT_DIMENSION_QUERY = "erpnext.controllers.queries.get_filtered_dimensions";

function buildChildMeta(childDoctype) {
	const relative = VENDOR_JSON_FOR_CHILD[childDoctype];
	const raw = JSON.parse(readPinnedVendor("erpnext", relative));
	const fields = raw.fields.map((field) => ({
		fieldname: field.fieldname,
		fieldtype: field.fieldtype,
		options: field.options || "",
	}));
	const present = new Set(fields.map((field) => field.fieldname));
	APP_BOQ_CUSTOM_FIELDS.forEach((field) => {
		if (!present.has(field.fieldname)) fields.push(field);
	});
	return fields;
}

function buildParentMeta(parent) {
	return [
		{ fieldname: "company", fieldtype: "Link", options: "Company" },
		{ fieldname: parent.table, fieldtype: "Table", options: parent.child },
	];
}

function makeJqueryStub() {
	function $(element) {
		const wrapper = {
			length: 0,
			0: element,
			on() {
				return wrapper;
			},
			off() {
				return wrapper;
			},
			ready(handler) {
				if (typeof handler === "function") handler();
				return wrapper;
			},
			find() {
				return wrapper;
			},
			first() {
				return wrapper;
			},
			append() {
				return wrapper;
			},
			remove() {
				return wrapper;
			},
			text() {
				return wrapper;
			},
			attr() {
				return wrapper;
			},
			toggleClass() {
				return wrapper;
			},
			addClass() {
				return wrapper;
			},
			removeClass() {
				return wrapper;
			},
			each() {
				return wrapper;
			},
		};
		return wrapper;
	}
	$.extend = function (target) {
		for (let index = 1; index < arguments.length; index += 1) {
			const source = arguments[index];
			if (!source) continue;
			Object.keys(source).forEach((key) => {
				target[key] = source[key];
			});
		}
		return target;
	};
	$.each = function (collection, callback) {
		if (Array.isArray(collection)) {
			collection.forEach((value, index) => callback(index, value));
		} else if (collection && typeof collection === "object") {
			Object.keys(collection).forEach((key) => callback(key, collection[key]));
		}
	};
	$.isPlainObject = function (value) {
		return !!value && typeof value === "object" && !Array.isArray(value);
	};
	return $;
}

function makeGrid() {
	return {
		fieldinfo: {},
		grid_rows_by_docname: {},
		docfields: [],
		// Pinned Frappe grid.js::get_field
		//   if (!this.fieldinfo[fieldname]) this.fieldinfo[fieldname] = {};
		//   return this.fieldinfo[fieldname];
		get_field(fieldname) {
			if (!this.fieldinfo[fieldname]) this.fieldinfo[fieldname] = {};
			return this.fieldinfo[fieldname];
		},
	};
}

// Pinned Frappe form.js::set_query
//   if (opt2) { this.fields_dict[opt1].grid.get_field(fieldname).get_query = opt2; }
//   else { if (this.fields_dict[fieldname]) this.fields_dict[fieldname].get_query = opt1; }
function makeFrm(parent, options) {
	const opts = options || {};
	const grid = makeGrid();
	const frm = {
		doc: {
			doctype: parent.doctype,
			company: opts.company === undefined ? SCOPE.company : opts.company,
			project: opts.project === undefined ? SCOPE.project : opts.project,
		},
		fields_dict: {},
		is_new: () => true,
		refresh_field() {},
		reload_doc() {},
		save() {
			return Promise.resolve();
		},
		submit() {
			return Promise.resolve();
		},
		set_query(fieldname, opt1, opt2) {
			if (opt2) {
				this.fields_dict[opt1].grid.get_field(fieldname).get_query = opt2;
			} else if (this.fields_dict[fieldname]) {
				this.fields_dict[fieldname].get_query = opt1;
			}
		},
	};
	frm.fields_dict[parent.table] = { df: {}, grid: grid, wrapper: {} };
	return frm;
}

function createSandbox(parent, options) {
	const opts = options || {};
	const registrations = {};
	const calls = [];
	const meta = {};
	meta[parent.doctype] = buildParentMeta(parent);
	meta[parent.child] = buildChildMeta(parent.child);

	const sandbox = {
		console: console,
		setTimeout: setTimeout,
		clearTimeout: clearTimeout,
		$: makeJqueryStub(),
		document: {
			getElementById: () => null,
			// The app announces its notices in a live region; the stub only
			// needs to accept the element it creates.
			createElement: () => ({
				id: "",
				style: {},
				setAttribute() {},
			}),
			body: { appendChild() {} },
			addEventListener() {},
			removeEventListener() {},
		},
		window: {
			scopeContext: {
				enabled: true,
				getValidatedCurrentScope: () => Object.assign({}, SCOPE),
			},
		},
		locals: {},
		__: (message) => message,
	};

	sandbox.frappe = {
		boot: {
			enable_boq_cascade_filtering: opts.cascadeMode || "On",
			direct_labor_designations: [],
		},
		provide(namespacePath) {
			const parts = namespacePath.split(".");
			let target = sandbox;
			parts.forEach((part) => {
				if (!target[part]) target[part] = {};
				target = target[part];
			});
			return target;
		},
		ui: {
			form: {
				on(doctype, fieldname, handler) {
					if (typeof fieldname === "object") {
						const events = fieldname;
						Object.keys(events).forEach((event) => {
							registrations[doctype] = registrations[doctype] || {};
							registrations[doctype][event] = registrations[doctype][event] || [];
							registrations[doctype][event].push(events[event]);
						});
						return;
					}
					registrations[doctype] = registrations[doctype] || {};
					registrations[doctype][fieldname] = registrations[doctype][fieldname] || [];
					registrations[doctype][fieldname].push(handler);
				},
			},
		},
		model: {
			set_value(cdt, cdn, fieldname, value) {
				const row = sandbox.locals[cdt] && sandbox.locals[cdt][cdn];
				if (row) row[fieldname] = value;
			},
			with_doctype(doctype, handler) {
				return handler();
			},
		},
		meta: {
			get_docfields(doctype) {
				return meta[doctype] || [];
			},
			has_field(doctype, fieldname) {
				return (meta[doctype] || []).some((field) => field.fieldname === fieldname);
			},
			get_docfield(doctype, fieldname) {
				return (meta[doctype] || []).find((field) => field.fieldname === fieldname);
			},
		},
		call(request) {
			const record = {
				method: request.method,
				args: request.args || {},
				callback: request.callback,
			};
			calls.push(record);
			let resolvePromise;
			const promise = new Promise((resolve) => {
				resolvePromise = resolve;
			});
			record.resolve = (message) => {
				if (record.callback) record.callback({ message: message });
				resolvePromise({ message: message });
			};
			if (request.method === "construction.api.boq_link_queries.get_boq_scope_token") {
				record.resolve({ scope_token: "scope-token-1" });
			}
			return promise;
		},
		show_alert(options) {
			// The user visible feedback of the app is recorded so that a
			// regression can assert that a closed search is explained.
			sandbox.frappe.ui_alert_shown.push(options);
		},
		router: { on() {} },
		ui_alert_shown: [],
	};

	const context = vm.createContext(sandbox);

	// The REAL pinned ERPNext accounting-dimension setup: this is the code that
	// overwrites the BOQ query, so it is executed, never re-implemented.
	vm.runInContext(readPinnedVendor("erpnext", "erpnext/public/js/queries.js"), context, {
		filename: "erpnext/public/js/queries.js",
	});
	vm.runInContext(
		readPinnedVendor("erpnext", "erpnext/public/js/utils/dimension_tree_filter.js"),
		context,
		{ filename: "erpnext/public/js/utils/dimension_tree_filter.js" }
	);
	// The app client under test.
	vm.runInContext(
		fs.readFileSync(path.join(root, "construction", "public", "js", "boq_filters.js"), "utf8"),
		context,
		{ filename: "construction/public/js/boq_filters.js" }
	);

	return {
		sandbox: sandbox,
		context: context,
		registrations: registrations,
		calls: calls,
		meta: meta,
	};
}

function fireHandlers(registrations, doctype, event, args) {
	const handlers = (registrations[doctype] || {})[event] || [];
	handlers.forEach((handler) => handler.apply(null, args || []));
}

// Pinned Frappe grid_row.js::make_control
//   field.get_query = this.grid.get_field(df.fieldname).get_query;
// The inline grid row control therefore inherits whatever the grid field info
// holds at the moment the control is created.
function makeInlineRowControl(grid, fieldname) {
	const control = { df: { fieldname: fieldname }, value: "" };
	control.get_query = grid.get_field(fieldname).get_query;
	return control;
}

// Pinned Frappe grid_row_form.js (expanded row)
//   for (var fieldname in this.row.grid.fieldinfo || {}) {
//       var fi = this.row.grid.fieldinfo[fieldname];
//       $.extend(me.fields_dict[fieldname], fi);
//   }
// The expanded row form copies the grid field info onto its controls.
function makeExpandedRowControl(grid, fieldname) {
	const control = { df: { fieldname: fieldname }, value: "" };
	const info = grid.fieldinfo[fieldname] || {};
	Object.keys(info).forEach((key) => {
		control[key] = info[key];
	});
	return control;
}

// Pinned Frappe controls/link.js::set_custom_query resolves the query of a
// Link control and drops the empty values from the filters.
function resolveSearchArgs(control, doc, cdt, cdn) {
	const args = {};
	const get_query = control.get_query || control.df.get_query;
	if (!get_query) return args;
	const resolved = get_query(doc, cdt, cdn);
	if (!resolved) return args;
	if (resolved.filters) {
		Object.keys(resolved.filters).forEach((key) => {
			const value = resolved.filters[key];
			if (value === "" || value === null || value === undefined) {
				delete resolved.filters[key];
			}
		});
	}
	Object.keys(resolved).forEach((key) => {
		args[key] = resolved[key];
	});
	return args;
}

const SCOPE_TOKEN_METHOD = "construction.api.boq_link_queries.get_boq_scope_token";
const DIMENSION_METHOD =
	"erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimensions";

// The Accounting Dimension that construction/install.py provisions for
// "BOQ Item" (ERPNext derives the fieldname "boq_item" from the label).
const BOQ_DIMENSION = { label: "BOQ Item", fieldname: "boq_item", document_type: "BOQ Item" };

// The pinned ERPNext get_dimensions(with_cost_center_and_project=True) also
// returns the native cost_center and project dimensions. ERPNext drops the
// "project" one in setup_filters, so the child grid receives the native
// cost_center dimension query next to the BOQ Item one.
const NATIVE_DIMENSIONS = [
	{ fieldname: "cost_center", document_type: "Cost Center" },
	{ fieldname: "project", document_type: "Project" },
];

// Runs the native form lifecycle the way the pinned Frappe ScriptManager does:
// "setup" runs immediately, then "onload", then "refresh". The pinned ERPNext
// buying controller (erpnext/public/js/controllers/buying.js ->
// BuyingController.onload -> setup_queries) starts the accounting-dimension
// setup during the "onload" trigger, so the vendor request is issued here and
// its answer lands later.
function runNativeFormLifecycle(env, frm, parent) {
	fireHandlers(env.registrations, parent.doctype, "setup", [frm]);
	fireHandlers(env.registrations, parent.doctype, "onload", [frm]);
	env.sandbox.erpnext.accounts.dimensions.setup_dimension_filters(frm, parent.doctype);
	fireHandlers(env.registrations, parent.doctype, "refresh", [frm]);
}

function landDimensionSetup(sandbox, calls) {
	const call = calls.find((candidate) => candidate.method === DIMENSION_METHOD);
	assert.ok(call, "the pinned ERPNext dimension setup must issue its server call");
	call.resolve([[BOQ_DIMENSION].concat(NATIVE_DIMENSIONS), {}]);
	return call;
}

function makeRow(childDoctype, options) {
	const opts = options || {};
	return {
		doctype: childDoctype,
		name: opts.name || "row-1",
		idx: 1,
		boq_header: opts.boq_header === undefined ? "BOQ-2026-9705" : opts.boq_header,
		boq_structure: opts.boq_structure === undefined ? "gu7goanfvi" : opts.boq_structure,
		expense_category: opts.expense_category || "Direct",
		project: opts.project || SCOPE.project,
	};
}

// The account of the current row, as the pinned ERPNext dimension query
// derives it: the first Link -> Account field of the child row.
function makeAccountRow(childDoctype, accountField, account, options) {
	const opts = options || {};
	const row = makeRow(childDoctype, opts);
	row[accountField] = account;
	return row;
}

// ---------------------------------------------------------------------------
// The pinned Frappe contract this correction depends on.
// ---------------------------------------------------------------------------

test("the pinned Frappe grid keeps a child Link query in the grid field info", () => {
	const gridSource = readPinnedVendor("frappe", "frappe/public/js/frappe/form/grid.js");
	assert.match(
		gridSource,
		/get_field\(fieldname\)\s*\{[\s\S]{0,200}this\.fieldinfo\[fieldname\]/,
		"grid.get_field must resolve the grid field info entry"
	);
	const rowSource = readPinnedVendor("frappe", "frappe/public/js/frappe/form/grid_row.js");
	assert.match(
		rowSource,
		/field\.get_query\s*=\s*this\.grid\.get_field\(df\.fieldname\)\.get_query/,
		"an inline grid row control must take its query from the grid field info"
	);
	const rowFormSource = readPinnedVendor(
		"frappe",
		"frappe/public/js/frappe/form/grid_row_form.js"
	);
	assert.match(
		rowFormSource,
		/me\.fields_dict\[fieldname\],\s*fi/,
		"an expanded row form must copy the grid field info onto its controls"
	);
	const formSource = readPinnedVendor("frappe", "frappe/public/js/frappe/form/form.js");
	assert.match(
		formSource,
		/this\.fields_dict\[opt1\]\.grid\.get_field\(fieldname\)\.get_query\s*=\s*opt2/,
		"frm.set_query on a child table must write the grid field info query"
	);
});

test("the pinned ERPNext dimension setup overwrites the child field query", () => {
	const dimensionSource = readPinnedVendor(
		"erpnext",
		"erpnext/public/js/utils/dimension_tree_filter.js"
	);
	assert.match(
		dimensionSource,
		/frm\.set_query\(dimension,\s*parentfield/,
		"the pinned ERPNext setup must install its query on the child field"
	);
	assert.match(
		dimensionSource,
		/frappe\.call\(\{[\s\S]{0,400}get_dimensions/,
		"the pinned ERPNext setup must resolve its dimensions asynchronously"
	);
});

// ---------------------------------------------------------------------------
// The regression.
// ---------------------------------------------------------------------------

test("the BOQ Item query survives the asynchronous ERPNext dimension setup", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	// The app installs the BOQ query during the native form lifecycle.
	runNativeFormLifecycle(env, frm, parent);

	const beforeLanding = grid.get_field("boq_item").get_query;
	assert.equal(typeof beforeLanding, "function", "the BOQ query must be installed");
	assert.equal(
		resolveSearchArgs({ get_query: beforeLanding }, frm.doc, parent.child, "row-1").query,
		BOQ_ITEM_QUERY
	);

	// ERPNext's accounting-dimension setup now answers.
	landDimensionSetup(env.sandbox, env.calls);

	const afterLanding = grid.get_field("boq_item").get_query;
	assert.equal(typeof afterLanding, "function");
	assert.equal(
		resolveSearchArgs({ get_query: afterLanding }, frm.doc, parent.child, "row-1").query,
		BOQ_ITEM_QUERY,
		"the native BOQ Item query must still be the BOQ cascade query after the " +
			"asynchronous ERPNext accounting-dimension setup"
	);

	// The vendor did try to replace the query; the correction did not discard
	// the native accounting-dimension query but kept it as the source of the
	// native account policy.
	const state = grid.__ct_boq_item_query_state;
	assert.ok(state, "the BOQ Item query must be pinned on the grid field info");
	assert.ok(
		state.nativeWrites >= 1,
		"the ERPNext accounting-dimension query must have been captured"
	);
	assert.equal(
		typeof state.nativeQuery,
		"function",
		"the native accounting-dimension query must be preserved, not discarded"
	);
});

test("the omission, header, structure, status and scope filters reach the native query", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.query, BOQ_ITEM_QUERY);
	assert.equal(args.filters.boq_header, "BOQ-2026-9705");
	assert.equal(args.filters.structure, "gu7goanfvi");
	assert.equal(args.filters.project, "PROJ-0115");
	assert.equal(args.filters.require_boq_header, true);
	assert.equal(args.filters.require_structure, true);
	assert.deepEqual(Array.from(args.filters.allowed_statuses), ["Frozen", "Locked"]);
	assert.equal(args.filters.exclude_zero_revised, true, "the omission gate must be requested");
	assert.equal(args.filters.enforce_scope, true, "the scope gate must be requested");
	assert.equal(args.filters.company, SCOPE.company);
});

test("the native grid control and the expanded row both receive the BOQ query", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	// A row that was created before the dimension setup answered.
	const inlineBefore = makeInlineRowControl(grid, "boq_item");
	assert.equal(
		resolveSearchArgs(inlineBefore, frm.doc, parent.child, "row-1").query,
		BOQ_ITEM_QUERY
	);

	// A row that is expanded after the dimension setup answered.
	const expanded = makeExpandedRowControl(grid, "boq_item");
	assert.equal(
		resolveSearchArgs(expanded, frm.doc, parent.child, "row-1").query,
		BOQ_ITEM_QUERY
	);
});

test("a native accounting dimension on an unrelated field keeps the ERPNext query", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	// "cost_center" is a native ERPNext accounting dimension of the child table.
	// It must keep the native dimension query: the BOQ correction is scoped to
	// the BOQ fields only.
	const nativeControl = makeExpandedRowControl(grid, "cost_center");
	const nativeArgs = resolveSearchArgs(nativeControl, frm.doc, parent.child, "row-1");
	assert.equal(nativeArgs.query, ERPNEXT_DIMENSION_QUERY);
	assert.equal(nativeArgs.filters.dimension, "cost_center");
});

test("a blank company that is selected later keeps the BOQ query effective", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent, { company: "" });
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	// The company is chosen after the form was rendered. A company change does
	// not re-run the app lifecycle, so the query that is effective for the
	// dropdown is the one that was installed before the dimension setup
	// answered.
	frm.doc.company = SCOPE.company;

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");
	assert.equal(args.query, BOQ_ITEM_QUERY);
	assert.equal(args.filters.company, SCOPE.company);
});

test("repeated company changes and a reload keep the BOQ query effective", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	frm.doc.company = "F44-20261018-426ECCCD-Company-B";
	frm.doc.company = SCOPE.company;

	let control = makeExpandedRowControl(grid, "boq_item");
	assert.equal(resolveSearchArgs(control, frm.doc, parent.child, "row-1").query, BOQ_ITEM_QUERY);

	// A reload builds a new grid; the app installs the query again on refresh
	// and the dimension setup of the reloaded form answers afterwards.
	const reloaded = makeFrm(parent);
	reloaded.doc[parent.table] = [row];
	env.sandbox.locals[parent.child] = { "row-1": row };
	runNativeFormLifecycle(env, reloaded, parent);
	landDimensionSetup(env.sandbox, env.calls);

	control = makeExpandedRowControl(reloaded.fields_dict[parent.table].grid, "boq_item");
	assert.equal(
		resolveSearchArgs(control, reloaded.doc, parent.child, "row-1").query,
		BOQ_ITEM_QUERY
	);
});

test("every BOQ enabled parent keeps its BOQ queries after the dimension setup", () => {
	BOQ_PARENTS.forEach((parent) => {
		const env = createSandbox(parent);
		const frm = makeFrm(parent);
		const grid = frm.fields_dict[parent.table].grid;
		const row = makeRow(parent.child);
		env.sandbox.locals[parent.child] = { "row-1": row };
		frm.doc[parent.table] = [row];

		runNativeFormLifecycle(env, frm, parent);
		landDimensionSetup(env.sandbox, env.calls);

		["boq_header", "boq_structure", "boq_item", "boq_item_stage"].forEach((fieldname) => {
			const control = makeExpandedRowControl(grid, fieldname);
			const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");
			assert.equal(
				args.query,
				"construction.api.boq_link_queries.get_boq_" +
					{
						boq_header: "headers",
						boq_structure: "structures",
						boq_item: "items",
						boq_item_stage: "item_stages",
					}[fieldname],
				parent.doctype + "." + fieldname + " must keep the BOQ cascade query"
			);
		});
	});
});

test("the scope token request of the app is not confused with the dimension request", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);

	runNativeFormLifecycle(env, frm, parent);

	const scopeCall = env.calls.find((call) => call.method === SCOPE_TOKEN_METHOD);
	assert.ok(scopeCall, "the app must request its BOQ scope token");
	const dimensionCall = env.calls.find((call) => call.method === DIMENSION_METHOD);
	assert.ok(dimensionCall, "the pinned ERPNext dimension setup must request the dimensions");
});

// ---------------------------------------------------------------------------
// The native accounting-dimension policy must survive the BOQ correction.
//
// ERPNext installs `erpnext.controllers.queries.get_filtered_dimensions` for
// the "boq_item" field and that query applies the Accounting Dimension Filter
// of the row's account (Allow / Restrict). The BOQ cascade query replaces it,
// so the account of the row must reach the server, which applies the native
// policy on top of the BOQ gates.
// ---------------------------------------------------------------------------

test("the row account reaches the BOQ Item query so the native policy applies", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Journal Entry");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.query, BOQ_ITEM_QUERY, "the BOQ cascade query must stay effective");
	assert.equal(
		args.filters.account,
		"Expense - F44 - ABC",
		"the account of the row must reach the server so that the native " +
			"Accounting Dimension Filter policy is applied"
	);
	// The BOQ gates stay in place next to the native policy.
	assert.equal(args.filters.boq_header, "BOQ-2026-9705");
	assert.equal(args.filters.structure, "gu7goanfvi");
	assert.equal(args.filters.exclude_zero_revised, true);
	assert.equal(args.filters.enforce_scope, true);
});

test("the row account of a Material Request reaches the BOQ Item query", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "expense_account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.query, BOQ_ITEM_QUERY);
	assert.equal(args.filters.account, "Expense - F44 - ABC");
});

test("a row without an account carries no account filter", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.query, BOQ_ITEM_QUERY);
	assert.equal(
		args.filters.account,
		undefined,
		"without an account on the row there is no native dimension policy"
	);
});

test("the inline grid control of a row with an account carries the account", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Journal Entry");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const inline = makeInlineRowControl(grid, "boq_item");
	const args = resolveSearchArgs(inline, frm.doc, parent.child, "row-1");
	assert.equal(args.query, BOQ_ITEM_QUERY);
	assert.equal(args.filters.account, "Expense - F44 - ABC");
});

test("only the BOQ Item field is pinned, the other BOQ fields stay native", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Journal Entry");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	// The correction must not freeze foreign writers on fields that ERPNext
	// never touches: a foreign query on those fields stays effective.
	["boq_header", "boq_structure", "boq_item_stage"].forEach((fieldname) => {
		const foreign = function () {
			return { query: "foreign.query", filters: {} };
		};
		grid.get_field(fieldname).get_query = foreign;
		const control = makeExpandedRowControl(grid, fieldname);
		const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");
		assert.equal(
			args.query,
			"foreign.query",
			fieldname + " must not freeze a foreign query writer"
		);
	});

	// The BOQ Item field stays pinned.
	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");
	assert.equal(args.query, BOQ_ITEM_QUERY);
});

// ---------------------------------------------------------------------------
// A native query failure must never become an account-less successful search.
//
// The pinned ERPNext query reads the row from `locals` and throws when the row
// is not registered there. The app still finds the row in the grid (its
// supported fallback), so the BOQ filters are available; the native per-account
// Accounting Dimension Filter is NOT. Continuing without it would offer every
// BOQ Item of the header to a row whose account may be restricted, so the
// search must be closed instead.
// ---------------------------------------------------------------------------

test("a native account-query error closes the BOQ Item search instead of dropping the policy", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Journal Entry");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];
	grid.grid_rows = [{ doc: row }];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	// The real pinned native query fails for a row that is not in `locals`.
	const native = grid.__ct_boq_item_query_state.nativeQuery;
	assert.equal(typeof native, "function", "the pinned native query must be captured");
	delete env.sandbox.locals[parent.child]["row-1"];
	assert.throws(
		() => native(frm.doc, parent.child, "row-1"),
		"the actual pinned native query must fail for a row that is not in locals"
	);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.query, BOQ_ITEM_QUERY, "the BOQ cascade query stays effective");
	// The row is still found through the grid fallback, so the BOQ gates stay
	// in place.
	assert.equal(args.filters.boq_header, "BOQ-2026-9705");
	assert.equal(args.filters.structure, "gu7goanfvi");
	assert.equal(args.filters.exclude_zero_revised, true);
	// The native policy is unknown, so no account is claimed ...
	assert.equal(
		args.filters.account,
		undefined,
		"a failed native query must not be reported as an account-less row"
	);
	// ... and the search is closed instead of continuing without the policy.
	assert.equal(args.filters.require_gate, true, "a failed native query must close the search");
	assert.equal(args.filters.gate_open, 0, "a failed native query must close the search");
	// The user is told why the dropdown stays empty.
	assert.ok(
		env.sandbox.frappe.ui_alert_shown.length > 0,
		"the user must be notified when the native policy is unavailable"
	);
});

test("a malformed native query answer closes the BOQ Item search", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Journal Entry");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	// An answer that does not belong to the BOQ Item dimension cannot carry the
	// native policy of that dimension.
	grid.__ct_boq_item_query_state.nativeQuery = function () {
		return {
			query: ERPNEXT_DIMENSION_QUERY,
			filters: { dimension: "cost_center", account: "Expense - F44 - ABC" },
		};
	};

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(
		args.filters.account,
		undefined,
		"an unrecognised native answer must not be reported as an account-less row"
	);
	assert.equal(
		args.filters.require_gate,
		true,
		"an unrecognised native answer must close the search"
	);
	assert.equal(args.filters.gate_open, 0, "an unrecognised native answer must close the search");
});

test("a healthy native account keeps the search open and carries the account", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Journal Entry");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeAccountRow(parent.child, "account", "Expense - F44 - ABC");
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.filters.account, "Expense - F44 - ABC");
	assert.equal(args.filters.require_gate, true);
	assert.equal(args.filters.gate_open, 1, "a healthy row must keep the search open");
	assert.equal(
		env.sandbox.frappe.ui_alert_shown.length,
		0,
		"a healthy row must not report an unavailable native policy"
	);
});

test("a healthy row without an account keeps the search open", () => {
	const parent = BOQ_PARENTS.find((entry) => entry.doctype === "Material Request");
	const env = createSandbox(parent);
	const frm = makeFrm(parent);
	const grid = frm.fields_dict[parent.table].grid;
	const row = makeRow(parent.child);
	env.sandbox.locals[parent.child] = { "row-1": row };
	frm.doc[parent.table] = [row];

	runNativeFormLifecycle(env, frm, parent);
	landDimensionSetup(env.sandbox, env.calls);

	const control = makeExpandedRowControl(grid, "boq_item");
	const args = resolveSearchArgs(control, frm.doc, parent.child, "row-1");

	assert.equal(args.filters.account, undefined);
	assert.equal(args.filters.require_gate, true);
	assert.equal(args.filters.gate_open, 1, "a healthy row must keep the search open");
	assert.equal(
		env.sandbox.frappe.ui_alert_shown.length,
		0,
		"a healthy row must not report an unavailable native policy"
	);
});

// ---------------------------------------------------------------------------
// Hermetic vendor-root controls.
//
// The configured vendor root is authoritative. These controls build a
// SYNTHETIC bench layout with valid pinned vendor data and prove that an
// explicit unusable root (missing / empty / a file / without the vendor apps /
// tampered) FAILS the run instead of silently falling back to the valid
// sibling data that is present in the very same layout.
// ---------------------------------------------------------------------------

function sourceVendorRoot() {
	for (const base of vendorRoots()) {
		if (
			fs.existsSync(path.join(base, "frappe")) &&
			fs.existsSync(path.join(base, "erpnext"))
		) {
			return base;
		}
	}
	throw new Error("no pinned vendor root is available to build the hermetic layout");
}

// A synthetic bench layout: <base>/apps/{construction,frappe,erpnext}.
function buildHermeticLayout() {
	const base = fs.mkdtempSync(path.join(os.tmpdir(), "f44-vendor-hermetic-"));
	const appsDir = path.join(base, "apps");
	const appRoot = path.join(appsDir, "construction");
	fs.mkdirSync(path.join(appRoot, "construction", "public", "js"), { recursive: true });
	fs.mkdirSync(path.join(appRoot, "construction", "tests"), { recursive: true });
	fs.copyFileSync(
		path.join(root, "construction", "public", "js", "boq_filters.js"),
		path.join(appRoot, "construction", "public", "js", "boq_filters.js")
	);
	fs.copyFileSync(
		__filename,
		path.join(appRoot, "construction", "tests", "test_boq_native_query_client.js")
	);
	const source = sourceVendorRoot();
	Object.keys(PINNED_VENDOR_FILES).forEach((app) => {
		Object.keys(PINNED_VENDOR_FILES[app]).forEach((relative) => {
			const target = path.join(appsDir, app, relative);
			fs.mkdirSync(path.dirname(target), { recursive: true });
			fs.copyFileSync(path.join(source, app, relative), target);
		});
	});
	return { base: base, appsDir: appsDir, appRoot: appRoot };
}

// Runs the vendor control of the test file in a child process with the given
// vendor root configuration. `undefined` removes the variable entirely.
//
// Only the vendor control test is selected, so the child result depends on the
// vendor resolution ALONE and not on the correctness of the app source under
// test. A harness that has no vendor control (or that resolves the vendor
// root by falling back to a sibling) therefore cannot pass the controls below.
function runHermeticChild(layout, vendorRootValue) {
	const env = Object.assign({}, process.env);
	if (vendorRootValue === undefined) {
		delete env[VENDOR_ROOT_ENV];
	} else {
		env[VENDOR_ROOT_ENV] = vendorRootValue;
	}
	env[HERMETIC_CHILD_ENV] = "1";
	return spawnSync(
		process.execPath,
		[
			"--test",
			"--test-isolation=none",
			"--test-name-pattern=" + VENDOR_CONTROL_TEST,
			path.join(layout.appRoot, "construction", "tests", "test_boq_native_query_client.js"),
		],
		{
			cwd: path.join(layout.appRoot, "construction", "tests"),
			env: env,
			encoding: "utf8",
		}
	);
}

const HERMETIC_SKIP = IS_HERMETIC_CHILD ? "hermetic child process" : false;

// The vendor control is the only part of this file that the hermetic controls
// below execute in a child process. It resolves the vendor root and reads
// EVERY pinned vendor file, so it proves the resolution alone.
const VENDOR_CONTROL_TEST = "the configured vendor root resolves every pinned vendor file";

test(VENDOR_CONTROL_TEST, () => {
	Object.keys(PINNED_VENDOR_FILES).forEach((app) => {
		Object.keys(PINNED_VENDOR_FILES[app]).forEach((relative) => {
			const content = readPinnedVendor(app, relative);
			assert.ok(
				content.length > 0,
				app + "/" + relative + " must resolve to the pinned vendor content"
			);
		});
	});
});

test("an unset vendor root uses the verified sibling discovery", { skip: HERMETIC_SKIP }, () => {
	const layout = buildHermeticLayout();
	try {
		const result = runHermeticChild(layout, undefined);
		assert.equal(
			result.status,
			0,
			"the sibling discovery must work with valid vendor data:\n" +
				result.stdout +
				result.stderr
		);
	} finally {
		fs.rmSync(layout.base, { recursive: true, force: true });
	}
});

test(
	"an explicit missing vendor root fails the run although sibling data is valid",
	{ skip: HERMETIC_SKIP },
	() => {
		const layout = buildHermeticLayout();
		try {
			const result = runHermeticChild(layout, path.join(layout.base, "does-not-exist"));
			assert.notEqual(
				result.status,
				0,
				"a configured vendor root that does not exist must fail the run:\n" +
					result.stdout +
					result.stderr
			);
			assert.match(
				result.stderr + result.stdout,
				new RegExp(VENDOR_ROOT_ENV),
				"the failure must name the configured vendor root"
			);
		} finally {
			fs.rmSync(layout.base, { recursive: true, force: true });
		}
	}
);

test(
	"an explicit empty vendor root fails the run although sibling data is valid",
	{ skip: HERMETIC_SKIP },
	() => {
		const layout = buildHermeticLayout();
		try {
			const result = runHermeticChild(layout, "");
			assert.notEqual(
				result.status,
				0,
				"a configured but empty vendor root must fail the run:\n" +
					result.stdout +
					result.stderr
			);
			assert.match(
				result.stderr + result.stdout,
				new RegExp(VENDOR_ROOT_ENV),
				"the failure must name the configured vendor root"
			);
		} finally {
			fs.rmSync(layout.base, { recursive: true, force: true });
		}
	}
);

test("an explicit vendor root that is a file fails the run", { skip: HERMETIC_SKIP }, () => {
	const layout = buildHermeticLayout();
	try {
		const asFile = path.join(layout.base, "not-a-directory");
		fs.writeFileSync(asFile, "not a directory\n");
		const result = runHermeticChild(layout, asFile);
		assert.notEqual(
			result.status,
			0,
			"a configured vendor root that is a file must fail the run:\n" +
				result.stdout +
				result.stderr
		);
	} finally {
		fs.rmSync(layout.base, { recursive: true, force: true });
	}
});

test(
	"an explicit vendor root without the pinned apps fails the run",
	{ skip: HERMETIC_SKIP },
	() => {
		const layout = buildHermeticLayout();
		try {
			const emptyRoot = path.join(layout.base, "empty-root");
			fs.mkdirSync(emptyRoot, { recursive: true });
			const result = runHermeticChild(layout, emptyRoot);
			assert.notEqual(
				result.status,
				0,
				"a configured vendor root without the pinned apps must fail the run:\n" +
					result.stdout +
					result.stderr
			);
		} finally {
			fs.rmSync(layout.base, { recursive: true, force: true });
		}
	}
);

test(
	"an explicit tampered vendor root fails the run although sibling data is valid",
	{ skip: HERMETIC_SKIP },
	() => {
		const layout = buildHermeticLayout();
		try {
			const tamperedApps = path.join(layout.base, "tampered-apps");
			fs.cpSync(layout.appsDir, tamperedApps, { recursive: true });
			const tamperedFile = path.join(
				tamperedApps,
				"frappe",
				"frappe/public/js/frappe/form/form.js"
			);
			fs.appendFileSync(tamperedFile, "\n// tampered by the hermetic control\n");
			const result = runHermeticChild(layout, tamperedApps);
			assert.notEqual(
				result.status,
				0,
				"a tampered pinned vendor file must fail the run:\n" +
					result.stdout +
					result.stderr
			);
			assert.match(
				result.stderr + result.stdout,
				/pinned vendor file mismatch/,
				"the failure must report the digest mismatch"
			);
		} finally {
			fs.rmSync(layout.base, { recursive: true, force: true });
		}
	}
);

// ===========================================================================
// F44 CT unified dropdown — the BOQ Header prerequisite of a transaction row.
//
// ISOLATED CLIENT TEST. It loads the REAL app asset
// (construction/public/js/overrides/ct_link_control.js) into a Node vm
// sandbox, with a purpose-built DOM/jQuery stub and a control built from the
// REAL pinned Frappe control contract.
//
// It is NOT a browser test: no Frappe page, no site, no database, no browser
// process, no acceptance runtime. It therefore proves the CLIENT decision
// (the themed dropdown opens / stays closed) and nothing about pointer
// usability of a running site. The residual browser checklist stays open.
//
// The reported defect (F44 TS3 / historical-reference acceptance):
//
//   The CT unified dropdown of the "BOQ Structure" field of a transaction
//   child row was blocked even when that row already carried a BOQ Header.
//   The cause is in the app asset itself:
//
//     ct_link_control.js::hasBoqHeader(field)
//         const doc = (field && field.frm && field.frm.doc) || field.doc || null;
//         return Boolean(doc && doc.boq_header);
//
//   The pinned Frappe grid builds a child row control with the CHILD ROW
//   document and the PARENT form (grid_row.js::make_control -> `doc: this.doc`,
//   `frm: this.grid.frm`), so `field.frm.doc` is the PARENT transaction, which
//   owns no `boq_header`; the BOQ Header of a transaction row lives on the ROW
//   document. The blocked flag was therefore always true in a transaction grid
//   row, and the themed dropdown (openDropdown) returned before it opened.
//
//   The sibling helpers of the same file already resolve the row first
//   (getCurrentGridRowDoc), which is why the search arguments of the dropdown
//   were correct while the dropdown itself could not be opened.
//
// The regression below drives the REAL asset and fails on the unpatched base.
//
// PROVENANCE: every pinned vendor file is digest-verified against the pinned
// vendor HEAD (Frappe 2871914b69b6e14a4b023d9b7cc52dc3e269cc1b). A missing or
// mismatched vendor file FAILS the run; it is never silently substituted.
// ===========================================================================

// Pinned Frappe files that define the control contract the regression assumes.
const CT_PINNED_VENDOR_FILES = {
	frappe: {
		"frappe/public/js/frappe/form/grid_row.js":
			"9e7de34e9a306b42509f40573ff678d799391b5f4c2d6bedf08f48c948a6be34",
		"frappe/public/js/frappe/form/grid_row_form.js":
			"6af04d1b1346e0a7c27925f868390ce83cdcdd89e2a4170ac72e95a9e359e4fb",
		"frappe/public/js/frappe/form/layout.js":
			"87425319ff0d6ae308f835a3ee8a9ae9cf54d90cda388feeda4cac75589ca1bf",
		"frappe/public/js/frappe/form/controls/link.js":
			"02a3405293ae6624030ecfbcc1a76a78b8e502aaa479de5c931e0e494075e2af",
	},
};

// The exact contract of the pinned Frappe that the stub reproduces. When the
// pinned vendor changes, this guard fails instead of silently testing a
// contract the product no longer has.
const CT_PINNED_CONTRACT = [
	{
		file: "frappe/public/js/frappe/form/grid_row.js",
		fragments: ["doc: this.doc,", "frm: this.grid.frm,", "grid_row: this,"],
	},
	{
		file: "frappe/public/js/frappe/form/grid_row_form.js",
		fragments: ["frm: this.row.frm,", "grid_row: this.row,"],
	},
];

// ---------------------------------------------------------------------------
// A minimal DOM. It implements only what the app asset uses, and it is
// deliberately explicit so that a stub defect cannot turn into a false pass:
// every assertion below is about a value the PRODUCTION code produced.
// ---------------------------------------------------------------------------

const CT_VOID_TAGS = new Set(["input", "br", "img", "hr", "meta", "link", "path"]);

class MiniNode {
	constructor(tagName) {
		this.tagName = String(tagName || "div").toUpperCase();
		this.attributes = Object.create(null);
		this.childNodes = [];
		this.parentNode = null;
		this.style = Object.create(null);
		this.textContent = "";
		this.innerHTML = "";
		this.value = "";
		this._handlers = Object.create(null);
		this._data = Object.create(null);
	}

	setAttribute(name, value) {
		this.attributes[name] = String(value);
	}

	getAttribute(name) {
		return Object.prototype.hasOwnProperty.call(this.attributes, name)
			? this.attributes[name]
			: null;
	}

	hasAttribute(name) {
		return Object.prototype.hasOwnProperty.call(this.attributes, name);
	}

	appendChild(node) {
		node.parentNode = this;
		this.childNodes.push(node);
		return node;
	}

	get children() {
		return this.childNodes.filter((node) => node instanceof MiniNode);
	}

	getBoundingClientRect() {
		return { top: 100, left: 100, bottom: 130, right: 300, width: 200, height: 30 };
	}

	focus() {
		this._focused = true;
	}
}

function classListOf(node) {
	const raw = node.getAttribute("class");
	return raw ? String(raw).split(/\s+/).filter(Boolean) : [];
}

function setClassList(node, list) {
	node.setAttribute("class", list.join(" "));
}

// A small tag-soup parser for the markup the app asset builds. It is not a
// general HTML parser; it covers the tags and attributes the asset uses.
function parseMiniHtml(html) {
	const root = new MiniNode("#fragment");
	const stack = [root];
	const pattern = /<\/?([a-zA-Z0-9-]+)((?:\s+[a-zA-Z0-9_:.-]+(?:="[^"]*")?)*)\s*(\/?)>|([^<]+)/g;
	let match = null;
	while ((match = pattern.exec(html)) !== null) {
		if (match[4] !== undefined) {
			const text = match[4];
			if (text.trim()) stack[stack.length - 1].textContent += text;
			continue;
		}
		const tag = match[1].toLowerCase();
		if (match[0].startsWith("</")) {
			if (stack.length > 1) stack.pop();
			continue;
		}
		const node = new MiniNode(tag);
		const attributePattern = /([a-zA-Z0-9_:.-]+)(?:="([^"]*)")?/g;
		let attribute = null;
		while ((attribute = attributePattern.exec(match[2] || "")) !== null) {
			node.setAttribute(attribute[1], attribute[2] === undefined ? "" : attribute[2]);
		}
		stack[stack.length - 1].appendChild(node);
		const selfClosing = match[3] === "/" || CT_VOID_TAGS.has(tag);
		if (!selfClosing) stack.push(node);
	}
	return root;
}

// Selector support: an optional tag, `.class` tokens, `[attr]` /
// `[attr="value"]` tokens, the `:visible` pseudo class and the descendant
// combinator. It is the subset the app asset uses.
function matchesCompound(node, compound) {
	let rest = String(compound);
	const tagMatch = rest.match(/^[a-zA-Z][a-zA-Z0-9-]*/);
	if (tagMatch) {
		if (node.tagName !== tagMatch[0].toUpperCase()) return false;
		rest = rest.slice(tagMatch[0].length);
	}
	const tokens = rest.match(/\.[^\s.[\]]+|\[[^\]]*\]|:[^\s.[\]]+/g) || [];
	for (const part of tokens) {
		if (part.startsWith(".")) {
			if (!classListOf(node).includes(part.slice(1))) return false;
		} else if (part.startsWith("[")) {
			const body = part.slice(1, -1);
			const equals = body.indexOf("=");
			if (equals === -1) {
				if (!node.hasAttribute(body)) return false;
			} else {
				const name = body.slice(0, equals);
				const wanted = body.slice(equals + 1).replace(/^["']|["']$/g, "");
				if (node.getAttribute(name) !== wanted) return false;
			}
		} else if (part.startsWith(":")) {
			if (part === ":visible") {
				// An element counts as visible only once the code has shown it
				// explicitly; the theme hides the native control with an
				// explicit display value, so the rule stays deterministic.
				if (node.style.display === undefined || node.style.display === "none") {
					return false;
				}
			} else {
				return false;
			}
		}
	}
	return true;
}

function matchesSelector(node, selector) {
	const compounds = String(selector).trim().split(/\s+/).filter(Boolean);
	if (!compounds.length) return false;
	if (!matchesCompound(node, compounds[compounds.length - 1])) return false;
	let index = compounds.length - 2;
	let ancestor = node.parentNode;
	while (index >= 0 && ancestor) {
		if (matchesCompound(ancestor, compounds[index])) index -= 1;
		ancestor = ancestor.parentNode;
	}
	return index < 0;
}

function collectDescendants(node, visit) {
	node.children.forEach((child) => {
		visit(child);
		collectDescendants(child, visit);
	});
}

class MiniJQuery {
	constructor(nodes) {
		this.nodes = nodes;
		this.length = nodes.length;
		// jQuery exposes the nodes as index properties; the app asset uses
		// them (for example $btn[0].getBoundingClientRect()).
		nodes.forEach((node, index) => {
			this[index] = node;
		});
	}

	get(index) {
		return this.nodes[index];
	}

	each(handler) {
		this.nodes.forEach((node, index) => handler.call(node, index, node));
		return this;
	}

	first() {
		return new MiniJQuery(this.nodes.slice(0, 1));
	}

	closest(selector) {
		const found = [];
		this.nodes.forEach((node) => {
			let current = node;
			while (current) {
				if (matchesSelector(current, selector)) {
					found.push(current);
					return;
				}
				current = current.parentNode;
			}
		});
		return new MiniJQuery(found);
	}

	find(selector) {
		const found = [];
		this.nodes.forEach((node) => {
			collectDescendants(node, (candidate) => {
				if (matchesSelector(candidate, selector)) found.push(candidate);
			});
		});
		return new MiniJQuery(found);
	}

	parent() {
		return new MiniJQuery(
			this.nodes.map((node) => node.parentNode).filter((node) => Boolean(node))
		);
	}

	append(child) {
		this.nodes.forEach((node) => {
			if (typeof child === "string") {
				parseMiniHtml(child).children.forEach((parsed) => node.appendChild(parsed));
			} else if (child instanceof MiniNode) {
				node.appendChild(child);
			} else if (child && child.nodes) {
				child.nodes.forEach((parsed) => node.appendChild(parsed));
			}
		});
		return this;
	}

	hasClass(name) {
		return this.nodes.some((node) => classListOf(node).includes(name));
	}

	addClass(name) {
		this.nodes.forEach((node) => {
			const list = classListOf(node);
			if (!list.includes(name)) list.push(name);
			setClassList(node, list);
		});
		return this;
	}

	removeClass(name) {
		this.nodes.forEach((node) => {
			setClassList(
				node,
				classListOf(node).filter((entry) => entry !== name)
			);
		});
		return this;
	}

	toggleClass(name, force) {
		const shouldAdd = force === undefined ? !this.hasClass(name) : Boolean(force);
		return shouldAdd ? this.addClass(name) : this.removeClass(name);
	}

	attr(name, value) {
		if (value === undefined) {
			const node = this.nodes[0];
			return node ? node.getAttribute(name) : undefined;
		}
		this.nodes.forEach((node) => node.setAttribute(name, value));
		return this;
	}

	css(properties, value) {
		if (typeof properties === "string") {
			const node = this.nodes[0];
			return node ? node.style[properties] : undefined;
		}
		Object.keys(properties).forEach((key) => {
			this.nodes.forEach((node) => {
				node.style[key] = properties[key];
			});
		});
		return this;
	}

	hide() {
		return this.css({ display: "none" });
	}

	show() {
		return this.css({ display: "block" });
	}

	text(value) {
		if (value === undefined) {
			return this.nodes.map((node) => node.textContent).join("");
		}
		this.nodes.forEach((node) => {
			node.textContent = value;
			node.childNodes = [];
		});
		return this;
	}

	html(value) {
		if (value === undefined) {
			return this.nodes.map((node) => node.innerHTML).join("");
		}
		this.nodes.forEach((node) => {
			node.innerHTML = value;
			node.childNodes = [];
		});
		return this;
	}

	empty() {
		this.nodes.forEach((node) => {
			node.childNodes = [];
			node.textContent = "";
			node.innerHTML = "";
		});
		return this;
	}

	val(value) {
		if (value === undefined) {
			const node = this.nodes[0];
			return node ? node.value : undefined;
		}
		this.nodes.forEach((node) => {
			node.value = value;
		});
		return this;
	}

	on(events, handler) {
		const names = String(events).split(/\s+/).filter(Boolean);
		this.nodes.forEach((node) => {
			names.forEach((name) => {
				const key = name.split(".")[0];
				node._handlers[key] = node._handlers[key] || [];
				node._handlers[key].push(handler);
			});
		});
		return this;
	}

	off() {
		return this;
	}

	trigger(name) {
		const event = {
			target: this.nodes[0],
			currentTarget: this.nodes[0],
			preventDefault() {},
			stopPropagation() {},
		};
		this.nodes.forEach((node) => {
			(node._handlers[name] || []).forEach((handler) => handler.call(node, event));
		});
		return this;
	}

	is(selector) {
		return this.nodes.some((node) => matchesSelector(node, selector));
	}

	data(key, value) {
		if (value === undefined) {
			const node = this.nodes[0];
			return node ? node._data[key] : undefined;
		}
		this.nodes.forEach((node) => {
			node._data[key] = value;
		});
		return this;
	}

	focus() {
		this.nodes.forEach((node) => node.focus());
		return this;
	}

	ready(handler) {
		if (typeof handler === "function") handler();
		return this;
	}
}

// The document of the sandbox. `body` holds the scenario DOM.
function makeMiniDocument() {
	const document = {
		body: new MiniNode("body"),
		parentNode: null,
		_handlers: Object.create(null),
		_data: Object.create(null),
		getElementById: () => null,
		createElement: (tag) => new MiniNode(tag),
		addEventListener() {},
		removeEventListener() {},
	};
	return document;
}

// ---------------------------------------------------------------------------
// The scenario: a control built exactly like the pinned Frappe builds it.
// ---------------------------------------------------------------------------

const CT_SEARCH_METHOD = "frappe.desk.search.search_link";
const CT_STRUCTURE_QUERY = "construction.api.boq_link_queries.get_boq_structures";

function makeControlLinkClass() {
	// The request contract of the field is the REAL pinned one.
	//
	// The prototype of this class is chained to the prototype of the pinned
	// native Link control (see buildCtScenario), so get_search_args,
	// set_custom_query, apply_link_field_filters, parse_filters, get_options
	// and get_reference_doctype are the PINNED code. The harness never
	// substitutes a stub for the native contract: a stub would hide exactly
	// the defects this regression exists for.
	//
	// Only the three methods that need a live desk (on_input, validate and
	// validate_link_and_fetch) are replaced: they are not part of the request
	// contract under test, and the pinned ones need a focused input, an
	// awesomplete instance and a navigator.
	return class ControlLink {
		on_input() {
			this.native_on_input_calls = (this.native_on_input_calls || 0) + 1;
		}

		validate(value) {
			return value;
		}

		validate_link_and_fetch(value) {
			return Promise.resolve(value);
		}
	};
}

// The options the server returns for the BOQ cascade search.
const CT_SEARCH_RESULT = [
	{ value: "slovbsiufr", label: "F44-HIST-OWNED Line 73c1bc" },
	{ value: "gu7goanfvi", label: "F44-HIST-OWNED Group 73c1bc" },
];

// The client metadata of the doctypes of the scenario.
//
// The desk receives the DocFields of a doctype (including its Custom Fields)
// from the server, so `frappe.meta.get_docfield` is the authoritative source
// of the question "does the SCHEMA of this row own a boq_header field?".
// The app installs the `boq_header` custom field on the transaction child
// doctypes (construction/install.py::_get_boq_custom_fields_for_doctype); the
// VO Line carries no such field.
const CT_DOCTYPE_FIELDS = {
	"Material Request Item": ["boq_header", "boq_structure", "boq_item", "boq_item_stage"],
	"Journal Entry Account": ["boq_header", "boq_structure", "boq_item", "boq_item_stage"],
	"Purchase Order Item": ["boq_header", "boq_structure", "boq_item", "boq_item_stage"],
	"VO Line": ["boq_structure", "boq_item"],
	"Variation Order": ["boq_header", "project", "vo_number"],
	"BOQ Item": ["boq_header", "structure", "boq_item"],
};

function makeCtMeta() {
	const docfieldMap = {};
	Object.keys(CT_DOCTYPE_FIELDS).forEach((doctype) => {
		const fields = {};
		CT_DOCTYPE_FIELDS[doctype].forEach((fieldname) => {
			fields[fieldname] = { fieldname: fieldname, parent: doctype, fieldtype: "Link" };
		});
		docfieldMap[doctype] = fields;
	});
	return {
		docfield_map: docfieldMap,
		get_docfield(doctype, fieldname) {
			const fields = docfieldMap[doctype];
			return (fields && fields[fieldname]) || null;
		},
	};
}

// The jQuery helpers the pinned native Link control uses.
//
// The CT harness itself does not need them, but the REAL pinned native method
// (frappe/public/js/frappe/form/controls/link.js::set_custom_query) does, so
// the regression can execute the native contract instead of a stub.
MiniJQuery.each = function (collection, callback) {
	if (Array.isArray(collection)) {
		collection.forEach((value, index) => callback(index, value));
	} else if (collection && typeof collection === "object") {
		Object.keys(collection).forEach((key) => callback(key, collection[key]));
	}
};

MiniJQuery.extend = function (target) {
	for (let index = 1; index < arguments.length; index += 1) {
		const source = arguments[index];
		if (!source) continue;
		Object.keys(source).forEach((key) => {
			target[key] = source[key];
		});
	}
	return target;
};

MiniJQuery.isPlainObject = function (value) {
	return Boolean(value) && typeof value === "object" && !Array.isArray(value);
};

// Builds one scenario and loads the REAL app asset into a fresh sandbox.
function buildCtScenario(options) {
	const opts = options || {};
	const ControlLink = makeControlLinkClass();
	const grid = makeGrid();
	const calls = [];
	const permissions = {
		can_read: opts.can_read === undefined ? true : opts.can_read,
		can_select: opts.can_select === undefined ? true : opts.can_select,
		can_create: opts.can_create === undefined ? true : opts.can_create,
	};

	const rowDoc = opts.rowDoc;
	const parentDoc = opts.parentDoc;
	const fieldname = opts.fieldname || "boq_structure";
	const df = {
		fieldname: fieldname,
		fieldtype: "Link",
		options: opts.options || "BOQ Structure",
		label: opts.label || "BOQ Structure",
		reqd: 0,
		hidden: 0,
		read_only: 0,
	};

	const control = new ControlLink();
	control.df = df;
	control.value = opts.value === undefined ? "" : opts.value;
	control.get_value = function () {
		return this.value;
	};
	control.get_label_value = function () {
		return this.value;
	};
	control.set_value = function (next) {
		this.value = next;
		return Promise.resolve();
	};
	control.set_description = function () {};

	const gridRow = { doc: rowDoc, grid: grid };
	const frm = { doc: parentDoc };

	if (opts.expanded) {
		// The expanded row form builds its controls from a layout that carries
		// the row (grid_row_form.js). The pinned layout.refresh() attaches the
		// row document to the controls (layout.js::attach_doc_and_docfields),
		// so the control owns the row document as well.
		control.frm = frm;
		control.doc = rowDoc;
		control.doctype = rowDoc ? rowDoc.doctype : "";
		control.docname = rowDoc ? rowDoc.name : "";
		control.layout = { grid_row: gridRow, doctype: rowDoc ? rowDoc.doctype : "" };
	} else if (opts.standalone) {
		// A form control owns the form document; row and form are the same
		// object there.
		control.doc = parentDoc;
		control.doctype = parentDoc ? parentDoc.doctype : "";
		control.docname = parentDoc ? parentDoc.name : "";
		control.frm = frm;
	} else {
		// The inline grid row control (grid_row.js::make_control).
		control.doc = rowDoc;
		control.doctype = rowDoc ? rowDoc.doctype : "";
		control.docname = rowDoc ? rowDoc.name : "";
		control.frm = frm;
		control.grid = grid;
		control.grid_row = gridRow;
	}

	// The row the native query resolves for a given row name. The native BOQ
	// queries of the app resolve the row of the grid
	// (construction/public/js/boq_filters.js::getGridRow).
	const resolveNativeRow = (cdn) => {
		if (opts.rows && Object.prototype.hasOwnProperty.call(opts.rows, cdn)) {
			return opts.rows[cdn];
		}
		if (rowDoc && cdn === rowDoc.name) return rowDoc;
		return null;
	};

	// The native query of the grid field (boq_filters.js installs it through
	// frm.set_query). The CT control copies it onto the row control; it must
	// not be replaced by the themed control.
	//
	// The default answer is the REAL native answer of the app for a BOQ
	// Structure field of a transaction grid row
	// (construction/public/js/boq_filters.js::buildStructureFilters): the
	// header of the row, the require_gate / gate_open gates and the scope
	// enforcement. The themed dropdown has to carry that answer into its
	// request.
	const nativeCalls = [];
	// The app installs its BOQ cascade query on the BOQ link fields only; a
	// link to another doctype carries no query at all.
	const isBoqLinkField = ["BOQ Header", "BOQ Structure", "BOQ Item", "BOQ Item Stage"].includes(
		df.options
	);
	if (opts.native !== "missing" && (opts.native !== undefined || isBoqLinkField)) {
		const isSentinel = ["malformed", "undefined"].includes(opts.native);
		if (!isSentinel && (typeof opts.native === "object" || typeof opts.native === "string")) {
			// The pinned native contract also accepts a plain object and a
			// string as the query of a control; neither of them is asked with
			// an identity, so no native call is recorded.
			grid.get_field(fieldname).get_query = opts.native;
		} else {
			grid.get_field(fieldname).get_query = function (doc, cdt, cdn) {
				nativeCalls.push({ doc: doc, cdt: cdt, cdn: cdn });
				if (typeof opts.native === "function") return opts.native(doc, cdt, cdn);
				if (opts.native === "malformed") return { not_a_policy: true };
				if (opts.native === "undefined") return undefined;
				const row = resolveNativeRow(cdn);
				const filters = { require_gate: true, gate_open: 0, enforce_scope: true };
				if (row && row.boq_header) {
					filters.boq_header = row.boq_header;
					filters.gate_open = 1;
				}
				return { query: CT_STRUCTURE_QUERY, filters: filters };
			};
		}
		control.get_query = grid.get_field(fieldname).get_query;
	}

	// The DOM: a grid row with a themed Link control inside it.
	const document = makeMiniDocument();
	const gridRowElement = new MiniNode("div");
	gridRowElement.setAttribute("class", "grid-row");
	gridRowElement.setAttribute("data-row-index", "1");
	const controlElement = new MiniNode("div");
	controlElement.setAttribute("class", "frappe-control");
	controlElement.setAttribute("data-fieldtype", "Link");
	controlElement.setAttribute("data-fieldname", fieldname);
	const linkFieldElement = new MiniNode("div");
	linkFieldElement.setAttribute("class", "link-field");
	const inputElement = new MiniNode("input");
	inputElement.setAttribute("class", "form-control");
	inputElement.setAttribute("name", fieldname);
	inputElement.setAttribute("data-fieldname", fieldname);
	linkFieldElement.appendChild(inputElement);
	controlElement.appendChild(linkFieldElement);
	gridRowElement.appendChild(controlElement);
	document.body.appendChild(gridRowElement);
	controlElement.fieldobj = control;
	gridRowElement._data.grid_row = gridRow;

	const sandbox = {
		console: console,
		// The asset uses timers for its deferred synchronisation. Running them
		// immediately keeps the test deterministic.
		setTimeout: (handler) => {
			if (typeof handler === "function") handler();
			return 0;
		},
		clearTimeout: () => {},
		document: document,
		window: { innerHeight: 900 },
		locals: {},
		__: (message) => message,
		cint: (value) => {
			const parsed = parseInt(value, 10);
			return Number.isNaN(parsed) ? 0 : parsed;
		},
		MutationObserver: class {
			observe() {}
			disconnect() {}
		},
	};
	sandbox.$ = function (element) {
		if (element instanceof MiniNode) return new MiniJQuery([element]);
		if (element === document) return new MiniJQuery([document]);
		if (typeof element === "string") {
			const trimmed = element.trim();
			if (trimmed.startsWith("<")) {
				return new MiniJQuery(parseMiniHtml(trimmed).children);
			}
			const found = [];
			collectDescendants(document.body, (candidate) => {
				if (matchesSelector(candidate, trimmed)) found.push(candidate);
			});
			return new MiniJQuery(found);
		}
		return new MiniJQuery([]);
	};
	// The jQuery helpers the pinned native Link control uses.
	sandbox.$.each = MiniJQuery.each;
	sandbox.$.extend = MiniJQuery.extend;
	sandbox.$.isPlainObject = MiniJQuery.isPlainObject;
	sandbox.frappe = {
		boot: {
			enable_boq_cascade_filtering: "On",
			sysdefaults: {},
		},
		provide(namespacePath) {
			const parts = namespacePath.split(".");
			let target = sandbox;
			parts.forEach((part) => {
				if (!target[part]) target[part] = {};
				target = target[part];
			});
			return target;
		},
		ui: { form: { ControlLink: ControlLink } },
		model: {
			can_read: () => permissions.can_read,
			can_select: () => permissions.can_select,
			can_create: () => permissions.can_create,
			set_value(cdt, cdn, fieldname, value) {
				const row = sandbox.locals[cdt] && sandbox.locals[cdt][cdn];
				if (row) row[fieldname] = value;
			},
		},
		utils: {
			escape_html: (value) =>
				String(value === undefined || value === null ? "" : value)
					.replace(/&/g, "&amp;")
					.replace(/</g, "&lt;")
					.replace(/>/g, "&gt;"),
			// A minimal evaluator for the `eval:` values of the link_filters.
			// It resolves a dotted path on the document of the control, which is
			// the shape the pinned native contract evaluates.
			eval(expression, evalContext) {
				const match = /^doc((?:\.[A-Za-z_][A-Za-z0-9_]*)+)$/.exec(
					String(expression || "").trim()
				);
				if (!match) return undefined;
				let value = evalContext && evalContext.doc ? evalContext.doc : null;
				const parts = match[1].split(".").slice(1);
				for (const part of parts) {
					if (value === null || value === undefined) return undefined;
					value = value[part];
				}
				return value;
			},
		},
		call(request) {
			const record = {
				method: request.method,
				type: request.type,
				args: request.args || {},
			};
			calls.push(record);
			if (request.callback) {
				request.callback({ message: CT_SEARCH_RESULT.slice() });
			}
			return Promise.resolve({ message: [] });
		},
	};

	// The live client metadata of the doctypes. `meta: false` reproduces an
	// environment in which the meta of the row doctype is not loaded, so the
	// app must fall back to its explicit known context.
	if (opts.meta !== false) {
		sandbox.frappe.meta = makeCtMeta();
	}

	const context = vm.createContext(sandbox);

	// The REAL pinned native Link control.
	//
	// The regression must exercise the ACTUAL native contract of the field
	// (df.filters, df.link_filters and the plain object / string / function
	// get_query), not a stub of it: the pinned vendor file is digest verified
	// above and is executed here as it is. It is ALWAYS loaded.
	//
	// The prototype of the harness class is chained to the prototype of the
	// pinned class, so the request contract of the control is the pinned code
	// and the production code never needs a stub compatibility layer.
	const source = readPinnedVendor(
		"frappe",
		"frappe/public/js/frappe/form/controls/link.js"
	).replace(/^import\s+.*$/m, "");
	sandbox.frappe.ui.form.ControlData = class ControlData {};
	// The pinned file extends the Awesomplete prototype when the library is
	// present; the import of the library is not part of the contract under
	// test, so a placeholder carries the same effect.
	sandbox.Awesomplete = function Awesomplete() {};
	vm.runInContext(source, context, {
		filename: "frappe/public/js/frappe/form/controls/link.js",
	});
	Object.setPrototypeOf(ControlLink.prototype, sandbox.frappe.ui.form.ControlLink.prototype);
	if (opts.foreignClass) {
		// A control of a FOREIGN class: the class carries no native contract
		// at all. The production must close the search; it must never fall
		// back to a request of its own.
		Object.setPrototypeOf(ControlLink.prototype, Object.prototype);
	}
	// The theme patches the class of the control.
	sandbox.frappe.ui.form.ControlLink = ControlLink;

	vm.runInContext(
		fs.readFileSync(
			path.join(root, "construction", "public", "js", "overrides", "ct_link_control.js"),
			"utf8"
		),
		context,
		{ filename: "construction/public/js/overrides/ct_link_control.js" }
	);

	const dropdown = sandbox.$(".ct-unified-dropdown");
	const button = dropdown.find(".ct-dropdown-btn");
	const searches = () => calls.filter((call) => call.method === CT_SEARCH_METHOD);

	return {
		sandbox: sandbox,
		control: control,
		grid: grid,
		calls: calls,
		nativeCalls: nativeCalls,
		searches: searches,
		button: button,
		menu: dropdown.find(".ct-dropdown-menu"),
		list: dropdown.find(".ct-dropdown-list"),
		label: dropdown.find(".ct-dropdown-label"),
		input: inputElement,
		clickDropdown() {
			button.trigger("click");
			return searches();
		},
	};
}

// ---------------------------------------------------------------------------
// The regression cases.
// ---------------------------------------------------------------------------

test("the pinned Frappe control contract of the CT dropdown regression still holds", () => {
	CT_PINNED_CONTRACT.forEach((entry) => {
		const source = readPinnedVendor("frappe", entry.file);
		entry.fragments.forEach((fragment) => {
			assert.ok(
				source.includes(fragment),
				"the pinned " + entry.file + " no longer contains " + JSON.stringify(fragment)
			);
		});
	});
	// The pinned vendor files themselves must be the reviewed ones.
	Object.keys(CT_PINNED_VENDOR_FILES.frappe).forEach((appRelative) => {
		assert.ok(readPinnedVendor("frappe", appRelative).length > 0);
	});
});

test("the CT dropdown of a collapsed transaction grid row opens when the row carries a BOQ Header", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: {
			doctype: "Material Request Item",
			name: "ffep258hpd",
			boq_header: "BOQ-2026-10723",
			boq_structure: "",
		},
	});

	// The native patched entry point runs on every native link search.
	scenario.control.on_input({});
	assert.equal(
		scenario.control.__ct_boq_blocked,
		false,
		"a row that carries a BOQ Header must not be blocked"
	);
	assert.equal(scenario.control.df.only_select, false);

	// The themed dropdown opens and searches with the row's own BOQ Header.
	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown did not open");
	assert.equal(searches[0].args.query, CT_STRUCTURE_QUERY);
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
	assert.equal(searches[0].args.reference_doctype, "Material Request Item");
	assert.equal(searches[0].args.doctype, "BOQ Structure");
	assert.equal(searches[0].args.link_fieldname, "boq_structure");

	// The offered options are the ones of the row's BOQ Header.
	const offered = scenario.list
		.find(".dropdown-item[data-value]")
		.nodes.map((node) => node.getAttribute("data-value"));
	assert.deepEqual(offered, ["slovbsiufr", "gu7goanfvi"]);
});

test("the CT dropdown of an expanded transaction grid row opens when the row carries a BOQ Header", () => {
	const scenario = buildCtScenario({
		expanded: true,
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: {
			doctype: "Material Request Item",
			name: "ffep258hpd",
			boq_header: "BOQ-2026-10723",
			boq_structure: "",
		},
	});

	scenario.control.on_input({});
	assert.equal(scenario.control.__ct_boq_blocked, false);

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown of the expanded row did not open");
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
	assert.equal(searches[0].args.reference_doctype, "Material Request Item");
});

test("the CT dropdown of a transaction grid row stays closed without a BOQ Header", () => {
	// Three shapes of a row without a BOQ Header: a persisted row (the server
	// sends the field as null), a cleared row and a row that was never touched.
	const shapes = [
		{ doctype: "Material Request Item", name: "ffep258hpd", boq_header: null },
		{ doctype: "Material Request Item", name: "ffep258hpd", boq_header: "" },
		{ doctype: "Material Request Item", name: "ffep258hpd" },
	];

	shapes.forEach((rowDoc) => {
		const scenario = buildCtScenario({
			parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
			rowDoc: rowDoc,
		});

		scenario.control.on_input({});
		assert.equal(
			scenario.control.__ct_boq_blocked,
			true,
			"a row without a BOQ Header must stay blocked"
		);
		assert.equal(scenario.control.df.only_select, true);
		assert.equal(scenario.clickDropdown().length, 0, "the dropdown must not open");
	});
});

test("the CT dropdown of a transaction grid row stays closed after the BOQ Header is cleared", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: {
			doctype: "Material Request Item",
			name: "ffep258hpd",
			boq_header: "BOQ-2026-10723",
			boq_structure: "",
		},
	});

	scenario.control.on_input({});
	assert.equal(scenario.control.__ct_boq_blocked, false);

	// The user clears the BOQ Header of the same row.
	scenario.control.doc.boq_header = "";
	scenario.control.on_input({});
	assert.equal(scenario.control.__ct_boq_blocked, true);
	assert.equal(scenario.clickDropdown().length, 0, "the dropdown must not open");
});

test("the CT dropdown of a standalone BOQ Item form is not blocked", () => {
	// Parent mode: the control owns the form document, which carries the BOQ
	// Header itself.
	const formDoc = {
		doctype: "BOQ Item",
		name: "BOQI-BOQ-2026-10723-10724",
		boq_header: "BOQ-2026-10723",
	};
	const scenario = buildCtScenario({
		standalone: true,
		fieldname: "structure",
		options: "BOQ Structure",
		parentDoc: formDoc,
		rowDoc: formDoc,
	});

	scenario.control.on_input({});
	assert.equal(scenario.control.__ct_boq_blocked, false);
	assert.equal(scenario.control.df.only_select, false);
});

test("a child row without its own BOQ Header field keeps the parent document resolution", () => {
	// A VO Line row carries no BOQ Header field; the BOQ Header of the
	// Variation Order parent is the context, exactly as before the change.
	const scenario = buildCtScenario({
		parentDoc: {
			doctype: "Variation Order",
			name: "VO-BOQ-2026-10723-VO-001",
			boq_header: "BOQ-2026-10723",
		},
		rowDoc: { doctype: "VO Line", name: "vo-line-1", boq_structure: "" },
	});

	scenario.control.on_input({});
	assert.equal(scenario.control.__ct_boq_blocked, false);
	assert.equal(scenario.control.df.only_select, false);
});

test("an unrelated grid row without a BOQ Header stays closed", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Journal Entry", name: "ACC-JV-2026-00003" },
		rowDoc: { doctype: "Journal Entry Account", name: "je-account-1" },
	});

	scenario.control.on_input({});
	assert.equal(scenario.control.__ct_boq_blocked, true);
	assert.equal(scenario.clickDropdown().length, 0, "the dropdown must not open");
});

test("the native query of the grid field and the permission gates of the CT dropdown are unchanged", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: {
			doctype: "Material Request Item",
			name: "ffep258hpd",
			boq_header: "BOQ-2026-10723",
			boq_structure: "",
		},
	});

	// The native query of the grid field is copied onto the control, never
	// replaced by the themed control.
	assert.equal(
		scenario.control.get_query,
		scenario.grid.get_field("boq_structure").get_query,
		"the native query of the grid field must survive"
	);

	// The dropdown is not disabled and the search keeps the native scope
	// enforcement of the app.
	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(searches[0].args.filters.enforce_scope, true);
	assert.equal(scenario.control.df.read_only, 0);
	assert.equal(scenario.input.getAttribute("disabled"), null);
});

test("a user without read or select permission on the target doctype keeps the control disabled", () => {
	const scenario = buildCtScenario({
		can_read: false,
		can_select: false,
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: {
			doctype: "Material Request Item",
			name: "ffep258hpd",
			boq_header: "BOQ-2026-10723",
			boq_structure: "",
		},
	});

	// The permission gate of the theme is unchanged: the control is made
	// read-only instead of offering a search that would be denied.
	assert.equal(scenario.control.df.read_only, 1);
	assert.equal(scenario.clickDropdown().length, 0, "a denied control must not search");
});

// ---------------------------------------------------------------------------
// The F44 CT grid link correction, round 2.
//
// CT-R1: the themed BOQ search must go through the AUTHORITATIVE native query
// of the control, asked with the identity of the edited row, and it must fail
// CLOSED when that native policy is missing, throws or is malformed. Every
// assertion below is made on the ACTUAL OUTGOING REQUEST, never on a callback
// identity: the identity of the native query proves nothing about the policy
// that reaches the server.
//
// CT-R2: the gate, the prerequisite and the outgoing query must read ONE
// effective context, so they cannot disagree about the row, the parent
// document or the BOQ Header of the control.
// ---------------------------------------------------------------------------

const CT_ITEM_QUERY = "construction.api.boq_link_queries.get_boq_items";
const CT_HEADER_QUERY = "construction.api.boq_link_queries.get_boq_headers";

function ctMaterialRequestRow(overrides) {
	return Object.assign(
		{
			doctype: "Material Request Item",
			name: "ffep258hpd",
			boq_header: "BOQ-2026-10723",
			boq_structure: "",
		},
		overrides || {}
	);
}

test("the themed BOQ search of a transaction grid row carries the native gate of the row", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.equal(searches[0].args.query, CT_STRUCTURE_QUERY, "the native query must survive");
	assert.equal(
		searches[0].args.filters.require_gate,
		true,
		"the native require_gate of the row must reach the request"
	);
	assert.equal(
		searches[0].args.filters.gate_open,
		1,
		"the native gate_open of the row must reach the request"
	);
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
	assert.equal(searches[0].args.filters.enforce_scope, true);
});

test("a closed native gate reaches the themed search unchanged", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({
			query: CT_STRUCTURE_QUERY,
			filters: { boq_header: "BOQ-2026-10723", require_gate: true, gate_open: false },
		}),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.equal(
		searches[0].args.filters.require_gate,
		true,
		"the native require_gate must reach the request"
	);
	assert.equal(
		searches[0].args.filters.gate_open,
		false,
		"a closed native gate must not become an open themed search"
	);
});

test("a native policy that throws closes the themed search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: () => {
			throw new Error("the native policy of the row is not available");
		},
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a throwing native policy must close the search instead of sending one"
	);
	assert.ok(
		scenario.list.html().indexOf("No options available") !== -1,
		"the closed search must be reported to the user"
	);
});

test("a malformed native answer closes the themed search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: "malformed",
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a malformed native answer must close the search instead of sending one"
	);
});

test("an undefined native answer closes the themed search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: "undefined",
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"an undefined native answer must close the search instead of sending one"
	);
});

test("a missing native policy closes the themed search of a grid row", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: "missing",
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"the BOQ policy of a grid row is mandatory: without it the search stays closed"
	);
});

test("the themed search carries the native per-account policy of the row", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({
			query: CT_ITEM_QUERY,
			filters: {
				boq_header: "BOQ-2026-10723",
				require_gate: true,
				gate_open: 1,
				account: "Expense - F44 - ABC",
			},
		}),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(
		searches[0].args.filters.account,
		"Expense - F44 - ABC",
		"the native per-account policy must reach the request"
	);
	assert.equal(searches[0].args.query, CT_ITEM_QUERY, "the native query must not be dropped");
});

test("the themed search asks the native query with the identity of the edited row", () => {
	const parentDoc = { doctype: "Material Request", name: "MAT-MR-2026-00018" };
	const scenario = buildCtScenario({
		parentDoc: parentDoc,
		rowDoc: ctMaterialRequestRow(),
	});

	scenario.clickDropdown();
	assert.equal(scenario.nativeCalls.length, 1, "the native query must be asked exactly once");
	assert.equal(
		scenario.nativeCalls[0].cdt,
		"Material Request Item",
		"the native query must be asked with the doctype of the ROW"
	);
	assert.equal(
		scenario.nativeCalls[0].cdn,
		"ffep258hpd",
		"the native query must be asked with the name of the edited ROW"
	);
	assert.equal(
		scenario.nativeCalls[0].doc,
		parentDoc,
		"the native query must be asked with the parent document, like the native control"
	);
});

test("the expanded grid row asks the native query with the same row identity", () => {
	const parentDoc = { doctype: "Material Request", name: "MAT-MR-2026-00018" };
	const scenario = buildCtScenario({
		expanded: true,
		parentDoc: parentDoc,
		rowDoc: ctMaterialRequestRow(),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(scenario.nativeCalls.length, 1);
	assert.equal(scenario.nativeCalls[0].cdt, "Material Request Item");
	assert.equal(
		scenario.nativeCalls[0].cdn,
		"ffep258hpd",
		"the expanded row must be resolved, not the undefined control docname"
	);
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
});

test("the themed search of a row does not use the policy of another row", () => {
	const rowA = ctMaterialRequestRow({ name: "row-a", boq_header: "HEADER-A" });
	const rowB = ctMaterialRequestRow({ name: "row-b", boq_header: "HEADER-B" });
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: rowA,
		rows: { "row-a": rowA, "row-b": rowB },
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(
		searches[0].args.filters.boq_header,
		"HEADER-A",
		"the request must carry the policy of the EDITED row"
	);
	assert.equal(scenario.nativeCalls[0].cdn, "row-a");
});

test("the gate, the prerequisite and the request agree on the VO Line parent header", () => {
	const parentDoc = {
		doctype: "Variation Order",
		name: "VO-BOQ-2026-10723-VO-001",
		boq_header: "BOQ-2026-10723",
	};
	const scenario = buildCtScenario({
		parentDoc: parentDoc,
		rowDoc: { doctype: "VO Line", name: "vo-line-1", boq_structure: "" },
	});

	scenario.control.on_input({});
	assert.equal(
		scenario.control.__ct_boq_blocked,
		false,
		"a VO Line row inherits the BOQ Header of its Variation Order"
	);

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the prerequisite must not refuse the parent owned header");
	assert.equal(
		searches[0].args.filters.boq_header,
		"BOQ-2026-10723",
		"the request must carry the BOQ Header of the parent document"
	);
	assert.equal(scenario.nativeCalls[0].cdt, "VO Line");
	assert.equal(scenario.nativeCalls[0].cdn, "vo-line-1");
	assert.equal(scenario.nativeCalls[0].doc, parentDoc);
});

test("a new transaction row does not borrow the header of an unrelated parent", () => {
	// The schema of the row owns a boq_header field, so the row decides. A row
	// without a value must NOT inherit the header of an unrelated parent.
	[true, false].forEach((withMeta) => {
		const scenario = buildCtScenario({
			meta: withMeta,
			parentDoc: {
				doctype: "Variation Order",
				name: "VO-BOQ-2026-10723-VO-001",
				boq_header: "PARENT-HEADER",
			},
			rowDoc: { doctype: "Material Request Item", name: "new-row" },
		});

		scenario.control.on_input({});
		assert.equal(
			scenario.control.__ct_boq_blocked,
			true,
			"a row without its own BOQ Header must stay closed (meta: " + withMeta + ")"
		);
		assert.equal(
			scenario.clickDropdown().length,
			0,
			"no structure may be offered for a row without a BOQ Header"
		);
	});
});

test("the standalone BOQ Item form uses the native query of the form", () => {
	const formDoc = {
		doctype: "BOQ Item",
		name: "BOQI-BOQ-2026-10723-10724",
		boq_header: "BOQ-2026-10723",
	};
	const scenario = buildCtScenario({
		standalone: true,
		fieldname: "structure",
		options: "BOQ Structure",
		parentDoc: formDoc,
		rowDoc: formDoc,
		native: () => ({
			query: CT_STRUCTURE_QUERY,
			filters: { boq_header: "BOQ-2026-10723", require_boq_header: 1 },
		}),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(searches[0].args.query, CT_STRUCTURE_QUERY);
	assert.equal(searches[0].args.filters.require_boq_header, 1);
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
});

test("a form level BOQ link without a native policy keeps the cascade policy of the app", () => {
	// The BOQ Cost Analysis form has no client script, so the app never gave
	// a native query for its BOQ Structure field. The narrow cascade policy of
	// the app stays in force; the search must not become a plain link search.
	const formDoc = {
		doctype: "BOQ Cost Analysis",
		name: "COST-ANALYSIS-1",
		boq_header: "BOQ-2026-10723",
	};
	const scenario = buildCtScenario({
		standalone: true,
		fieldname: "boq_structure",
		options: "BOQ Structure",
		parentDoc: formDoc,
		rowDoc: formDoc,
		native: "missing",
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(searches[0].args.query, CT_STRUCTURE_QUERY);
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
	assert.equal(
		searches[0].args.filters.enforce_scope,
		true,
		"the scope enforcement of the app must stay in force"
	);
});

test("a link that is not a BOQ link keeps the native behaviour of the control", () => {
	const scenario = buildCtScenario({
		options: "Customer",
		fieldname: "customer",
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(searches[0].args.doctype, "Customer");
	assert.equal(
		scenario.nativeCalls.length,
		0,
		"a non-BOQ link must not be routed through the BOQ native policy"
	);
});

test("the native query of the BOQ Header field is not narrowed by the row header", () => {
	const scenario = buildCtScenario({
		fieldname: "boq_header",
		options: "BOQ Header",
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({
			query: CT_HEADER_QUERY,
			filters: { require_gate: true, gate_open: 1, allowed_statuses: ["Locked"] },
		}),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1);
	assert.equal(searches[0].args.query, CT_HEADER_QUERY);
	assert.equal(
		searches[0].args.filters.boq_header,
		undefined,
		"the list of BOQ Headers must not be filtered by the header of the row"
	);
	assert.equal(
		searches[0].args.filters.allowed_statuses[0],
		"Locked",
		"the native status policy of the header list must reach the request"
	);
});

// ---------------------------------------------------------------------------
// The F44 CT grid link correction, round 3.
//
// CT-R4: the native policy of the control is NEVER overwritten. A value the
//         native policy constrains is kept (a set of allowed values is
//         intersected with the policy of the app), and a conflict between the
//         native policy and the context of the control CLOSES the search
//         instead of silently choosing one of the two.
//
// CT-R5: the native contract of the FIELD reaches the outgoing request: the
//         DocField filters, the operator filters of the link_filters and the
//         plain object / string / function get_query. The REAL pinned native
//         method is executed for it, not a stub.
//
// CT-R6: an ABSENT native policy and a FAILED native policy are different
//         facts: a failed or malformed policy closes the search everywhere,
//         and only an absent policy of a documented root form context may use
//         the reviewed narrow fallback of the app.
// ---------------------------------------------------------------------------

test("PRIMARY2: native Locked-only policy is not widened to Frozen", () => {
	const s = buildCtScenario({
		fieldname: "boq_item",
		options: "BOQ Item",
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({ query: CT_ITEM_QUERY, filters: { allowed_statuses: ["Locked"] } }),
	});
	const calls = s.clickDropdown();
	assert.ok(
		calls.length === 0 || !calls[0].args.filters.allowed_statuses.includes("Frozen"),
		"Cascade widened native allowed_statuses"
	);
});
test("PRIMARY2: conflicting native header is not overwritten", () => {
	const s = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({
			query: CT_STRUCTURE_QUERY,
			filters: { boq_header: "POLICY-ONLY-HEADER" },
		}),
	});
	const calls = s.clickDropdown();
	assert.ok(
		calls.length === 0 || calls[0].args.filters.boq_header === "POLICY-ONLY-HEADER",
		"Effective context replaced native header restriction"
	);
});
test("PRIMARY2: native DocField filters reach themed request", () => {
	const s = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	s.control.df.filters = { cost_center: "AUTHORIZED-COST-CENTER" };
	const calls = s.clickDropdown();
	assert.ok(
		calls.length === 0 || calls[0].args.filters.cost_center === "AUTHORIZED-COST-CENTER",
		"Native df.filters dropped"
	);
});
test("PRIMARY2: standalone throwing policy cannot fall back", () => {
	const d = { doctype: "BOQ Item", name: "BI", boq_header: "H" };
	const s = buildCtScenario({
		standalone: true,
		parentDoc: d,
		rowDoc: d,
		native: () => {
			throw new Error("policy unavailable");
		},
	});
	assert.equal(
		s.clickDropdown().length,
		0,
		"Existing standalone policy failure used independent cascade"
	);
});

test("the status policy of the control is not widened by the policy of the app", () => {
	const scenario = buildCtScenario({
		fieldname: "boq_item",
		options: "BOQ Item",
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({
			query: CT_ITEM_QUERY,
			filters: { allowed_statuses: ["Locked"], boq_header: "BOQ-2026-10723" },
		}),
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.deepEqual(
		Array.from(searches[0].args.filters.allowed_statuses),
		["Locked"],
		"the native status policy must not be widened"
	);
	assert.equal(
		searches[0].args.filters.boq_header,
		"BOQ-2026-10723",
		"the native header must survive the policy of the app"
	);
});

test("a native policy that conflicts with the context of the control closes the search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({ query: CT_STRUCTURE_QUERY, filters: { boq_header: "OTHER-HEADER" } }),
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"two different headers cannot be composed: the search must be closed"
	);
});

test("the DocField filters of the control reach the request", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.filters = { cost_center: "AUTHORIZED-COST-CENTER" };

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.equal(
		searches[0].args.filters.cost_center,
		"AUTHORIZED-COST-CENTER",
		"the filters of the DocField are a restriction of the field"
	);
});

test("the operator filters of the link_filters of the control reach the request", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.link_filters = JSON.stringify([
		["Material Request Item", "project", "=", "PROJ-0115"],
	]);

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.deepEqual(
		Array.from(searches[0].args.filters.project),
		["=", "PROJ-0115"],
		"an operator filter must keep its operator and its value"
	);
});

test("an unusable link_filters of the control closes the search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.link_filters = "{not json";

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a link_filters that cannot be read must not silently widen the search"
	);
});

test("a native query given as a plain object reaches the request", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: { filters: { boq_header: "BOQ-2026-10723" } },
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.equal(
		searches[0].args.filters.boq_header,
		"BOQ-2026-10723",
		"the filters of a plain object query must reach the request"
	);
	assert.equal(
		searches[0].args.query,
		CT_STRUCTURE_QUERY,
		"the query of the app is used when the native answer carries none"
	);
});

test("a native query given as a string reaches the request", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: CT_STRUCTURE_QUERY,
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the themed dropdown must issue the search");
	assert.equal(searches[0].args.query, CT_STRUCTURE_QUERY);
	assert.equal(
		searches[0].args.filters.boq_header,
		"BOQ-2026-10723",
		"the policy of the app narrows a native query without filters"
	);
});

test("the real pinned native method applies the DocField restrictions of the control", () => {
	const scenario = buildCtScenario({
		realNative: true,
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.filters = { cost_center: "AUTHORIZED-COST-CENTER" };
	scenario.control.df.link_filters = JSON.stringify([
		["Material Request Item", "project", "=", "PROJ-0115"],
	]);

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the real native contract must produce a request");
	assert.equal(
		searches[0].args.filters.cost_center,
		"AUTHORIZED-COST-CENTER",
		"the real native method must apply the filters of the DocField"
	);
	assert.deepEqual(
		Array.from(searches[0].args.filters.project),
		["=", "PROJ-0115"],
		"the real native method must apply the operator filters of the link_filters"
	);
	assert.equal(
		scenario.nativeCalls.length,
		1,
		"the native query must be asked exactly once, with the row identity"
	);
	assert.equal(scenario.nativeCalls[0].cdn, "ffep258hpd");
	assert.equal(scenario.nativeCalls[0].cdt, "Material Request Item");
});

test("the themed request carries the request of the real pinned native control", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.filters = { cost_center: "AUTHORIZED-COST-CENTER" };
	scenario.control.df.link_filters = JSON.stringify([
		["Material Request Item", "project", "=", "PROJ-0115"],
	]);

	// The request of the REAL pinned native control, asked with the identity
	// of the same row.
	const nativeRequest = scenario.control.get_search_args("");
	const themed = scenario.clickDropdown();

	assert.equal(themed.length, 1, "the themed dropdown must issue the search");
	assert.ok(nativeRequest, "the real native control must build a request");
	assert.equal(
		themed[0].args.query,
		nativeRequest.query,
		"the native query must reach the themed request"
	);
	// Every restriction of the native request reaches the themed request.
	Object.keys(nativeRequest.filters || {}).forEach((key) => {
		assert.deepEqual(
			JSON.parse(JSON.stringify(themed[0].args.filters[key])),
			JSON.parse(JSON.stringify(nativeRequest.filters[key])),
			"the native restriction " + key + " must reach the themed request"
		);
	});
});

test("a failed native policy closes the search of a form level link", () => {
	const formDoc = { doctype: "BOQ Item", name: "BI", boq_header: "BOQ-2026-10723" };
	const scenario = buildCtScenario({
		standalone: true,
		parentDoc: formDoc,
		rowDoc: formDoc,
		native: () => {
			throw new Error("the native policy of the form is not available");
		},
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a failed policy must close the search of a form level link as well"
	);
});

test("a malformed native policy closes the search of a form level link", () => {
	const formDoc = { doctype: "BOQ Item", name: "BI", boq_header: "BOQ-2026-10723" };
	const scenario = buildCtScenario({
		standalone: true,
		parentDoc: formDoc,
		rowDoc: formDoc,
		native: "malformed",
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a malformed policy must close the search of a form level link as well"
	);
});

test("an absent native policy of a form level link uses the narrow fallback of the app", () => {
	const formDoc = {
		doctype: "BOQ Cost Analysis",
		name: "COST-1",
		boq_header: "BOQ-2026-10723",
	};
	const scenario = buildCtScenario({
		standalone: true,
		fieldname: "boq_structure",
		options: "BOQ Structure",
		parentDoc: formDoc,
		rowDoc: formDoc,
		native: "missing",
	});

	const searches = scenario.clickDropdown();
	assert.equal(searches.length, 1, "the narrow fallback of the app must be used");
	assert.equal(searches[0].args.query, CT_STRUCTURE_QUERY);
	assert.equal(searches[0].args.filters.boq_header, "BOQ-2026-10723");
	assert.equal(searches[0].args.filters.enforce_scope, true);
});

test("an absent native policy of a grid row closes the search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MAT-MR-2026-00018" },
		rowDoc: ctMaterialRequestRow(),
		native: "missing",
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"the policy of a grid row is mandatory: an absent policy closes the search"
	);
});

test("a native answer with a list of operator filters closes the search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
		native: () => ({ query: CT_STRUCTURE_QUERY, filters: [["cost_center", "=", "CC-1"]] }),
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a list of operator filters must never be converted into an object"
	);
});

// ---------------------------------------------------------------------------
// The F44 CT native-only correction, round 4 (this round).
//
// CT-R7: the SUPPLIED restrictions of the field are validated BEFORE the
//         native contract runs. The pinned native contract swallows a
//         malformed link_filters (it logs the error and returns {}), and a
//         swallowed restriction is a WIDENED search.
//
// CT-R8: there is NO fallback for a native contract that failed. A native
//         method that is not available in the class of the control and a
//         native method that threw both close the search; the production
//         carries no second implementation of the native contract.
// ---------------------------------------------------------------------------

test("a malformed link_filters closes the search before the native contract runs", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.link_filters = "[not-valid-json";

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a link_filters that cannot be read must not silently widen the search"
	);
});

test("a link_filters with an unusable operator closes the search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.link_filters = JSON.stringify([
		["Material Request Item", "project", "not-an-operator", "PROJ-0115"],
	]);

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a restriction with an unusable operator must not silently widen the search"
	);
});

test("a link_filters with an unevaluable eval: value closes the search", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.link_filters = JSON.stringify([
		["Material Request Item", "project", "=", "eval:doc.does_not_exist"],
	]);

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a restriction that cannot be evaluated must not silently widen the search"
	);
});

test("a native contract that threw closes the search and is never replaced", () => {
	const scenario = buildCtScenario({
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});
	scenario.control.df.link_filters = JSON.stringify([
		["Material Request Item", "cost_center", "=", "AUTHORIZED"],
	]);
	scenario.sandbox.frappe.ui.form.ControlLink.prototype.apply_link_field_filters = function () {
		throw new Error("native filter evaluation unavailable");
	};

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"a native contract that failed must not be replaced by a request of the app"
	);
});

test("a control of a foreign class without the native contract closes the search", () => {
	const scenario = buildCtScenario({
		foreignClass: true,
		parentDoc: { doctype: "Material Request", name: "MR" },
		rowDoc: ctMaterialRequestRow(),
	});

	assert.equal(
		scenario.clickDropdown().length,
		0,
		"the production must not carry a second implementation of the native contract"
	);
});
