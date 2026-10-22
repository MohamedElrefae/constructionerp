const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { after } = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");

// The native add-row dispatch is only meaningful against the REAL pinned Frappe
// dispatcher. In CI the vendor checkout is pinned by the workflow setup
// (frappe 2871914b69b6e14a4b023d9b7cc52dc3e269cc1b), so the dispatcher file is
// identified by its exact digest and a missing or mismatched vendor file MUST
// fail the job instead of silently falling back to the local mirror.
//
// An explicitly configured F44_PINNED_SCRIPT_MANAGER is authoritative: it names
// the ONE qualified vendor dispatcher, so a broken explicit value fails the run
// clearly instead of silently resolving a different (sibling) vendor file.
const PINNED_VENDOR_DISPATCHER_SHA256 =
	"e7204be9dc75381e7a979f7a46f4cc4b14cf0f7f27f18415b121ccc9e07ed025";
const PINNED_VENDOR_DISPATCHER_PATH = "frappe/public/js/frappe/form/script_manager.js";
const CI_MODE = Boolean(process.env.CI || process.env.GITHUB_ACTIONS);

function loadClient() {
	const source = fs.readFileSync(
		path.join(root, "construction", "public", "js", "timesheet_designation.js"),
		"utf8"
	);
	const module = { exports: {} };
	const context = vm.createContext({
		module,
		exports: module.exports,
		console,
		Promise,
		Object,
		Array,
		JSON,
		Math,
	});
	vm.runInContext(source, context, { filename: "timesheet_designation.js" });
	return module.exports;
}

function makeFrm(employee, rows, options) {
	const opts = options || {};
	return {
		doc: {
			doctype: "Timesheet",
			employee: employee || null,
			docstatus: opts.docstatus || 0,
			time_logs: rows || [],
		},
		fields_dict: {
			time_logs: { df: {} },
		},
		read_only: !!opts.read_only,
		refresh_calls: 0,
		refresh_field() {
			this.refresh_calls += 1;
		},
		is_readonly() {
			return this.read_only;
		},
	};
}

function makeApi() {
	const calls = [];
	const api = (employee) => {
		let resolve;
		let reject;
		const promise = new Promise((res, rej) => {
			resolve = res;
			reject = rej;
		});
		calls.push({ employee, resolve, reject });
		return promise;
	};
	return { api, calls };
}

const tick = () => new Promise((resolve) => setImmediate(resolve));

// ---------------------------------------------------------------------------
// Pinned dispatcher fidelity.
//
// The native form-backed grid emits (apps/frappe/frappe/public/js/frappe/form/grid.js::add_new_row):
//     this.frm.script_manager.trigger(this.df.fieldname + "_add", d.doctype, d.name)
// and the pinned ScriptManager resolves the handler (apps/frappe/frappe/public/js/
// frappe/form/script_manager.js::get_handlers) through:
//     frappe.ui.form.handlers[doctype][event_name]
// where `doctype` is the CHILD doctype the grid passed ("Timesheet Detail").
// A handler registered on the parent form is therefore NEVER resolved by the
// native event.
//
// The regression drives the ACTUAL pinned dispatcher when the vendor file is
// reachable (F44_PINNED_SCRIPT_MANAGER or a standard bench path) and otherwise
// the byte-faithful mirror of the same lookup.
//
// PROVENANCE: an explicitly configured F44_PINNED_SCRIPT_MANAGER is
// authoritative. When the variable is PRESENT in the environment it names the
// ONE qualified vendor dispatcher and only that path may be executed; a broken
// explicit value (missing, unreadable, a directory, empty) is a hard failure in
// EVERY mode and no sibling vendor checkout is substituted for it. Only an
// ABSENT variable leaves the standard bench discovery in place, and only that
// mode may fall back to the labelled local mirror.
// ---------------------------------------------------------------------------
const PINNED_DISPATCHER_ENV_KEY = "F44_PINNED_SCRIPT_MANAGER";
const PINNED_VENDOR_HEAD = "2871914b69b6e14a4b023d9b7cc52dc3e269cc1b";

// The standard bench discovery, used ONLY when no explicit configuration was
// made (the variable is absent from the environment).
function benchSiblingDispatcherPaths() {
	return [
		path.resolve(
			root,
			"..",
			"frappe",
			"frappe",
			"public",
			"js",
			"frappe",
			"form",
			"script_manager.js"
		),
		path.resolve(
			root,
			"..",
			"..",
			"frappe",
			"frappe",
			"public",
			"js",
			"frappe",
			"form",
			"script_manager.js"
		),
	];
}

// Returns the explicitly configured path, or null when the variable is absent
// from the environment (no claim was made). An empty value is an explicit but
// unusable claim and fails immediately.
function explicitDispatcherPath() {
	const raw = process.env[PINNED_DISPATCHER_ENV_KEY];
	if (raw === undefined) {
		return null;
	}
	const value = String(raw).trim();
	if (!value) {
		throw new Error(
			PINNED_DISPATCHER_ENV_KEY +
				" is set but empty. The explicit pinned dispatcher configuration is " +
				"authoritative: it must name the qualified frappe checkout's " +
				PINNED_VENDOR_DISPATCHER_PATH +
				" (vendor HEAD " +
				PINNED_VENDOR_HEAD +
				"). Unset the variable to use the standard bench discovery."
		);
	}
	return value;
}

function assertRegularReadableFile(filePath, prefix, detail) {
	let stats = null;
	try {
		stats = fs.statSync(filePath);
	} catch (error) {
		stats = null;
	}
	if (!stats) {
		throw new Error(prefix + filePath + ", which does not exist. " + detail);
	}
	if (!stats.isFile()) {
		throw new Error(prefix + filePath + ", which is not a regular file. " + detail);
	}
	try {
		fs.accessSync(filePath, fs.constants.R_OK);
	} catch (error) {
		throw new Error(prefix + filePath + ", which is not readable. " + detail);
	}
	return filePath;
}

// Resolves the ONE vendor dispatcher file that may be executed.
// Throws when an explicit configuration is broken (an explicit claim is never
// replaced by a sibling vendor checkout). Returns null only when no explicit
// configuration was made AND no sibling vendor is reachable, which is the
// labelled local-mirror case.
function resolvePinnedDispatcherPath() {
	const explicit = explicitDispatcherPath();
	if (explicit !== null) {
		return assertRegularReadableFile(
			explicit,
			PINNED_DISPATCHER_ENV_KEY + " points at ",
			"The explicit pinned dispatcher configuration is authoritative: only this path may be " +
				"executed and no sibling vendor checkout (" +
				benchSiblingDispatcherPaths().join(", ") +
				") is substituted for it."
		);
	}
	const siblings = benchSiblingDispatcherPaths();
	const found = siblings.find((candidate) => fs.existsSync(candidate));
	if (!found) {
		if (CI_MODE) {
			throw new Error(
				"CI mode requires the pinned Frappe dispatcher: set F44_PINNED_SCRIPT_MANAGER to " +
					"the qualified frappe checkout's " +
					PINNED_VENDOR_DISPATCHER_PATH +
					" (vendor HEAD " +
					PINNED_VENDOR_HEAD +
					"). None of: " +
					siblings.join(", ")
			);
		}
		// Local unit layer only: the mirror of the same lookup is used, and the
		// test records that the pinned dispatcher was not exercised.
		return null;
	}
	return assertRegularReadableFile(
		found,
		"The standard bench discovery resolved ",
		"The standard bench discovery must resolve a regular readable file."
	);
}

function loadPinnedDispatcher() {
	const vendorPath = resolvePinnedDispatcherPath();
	if (vendorPath === null) {
		return null;
	}
	const actual = crypto.createHash("sha256").update(fs.readFileSync(vendorPath)).digest("hex");
	if (actual !== PINNED_VENDOR_DISPATCHER_SHA256) {
		throw new Error(
			"pinned Frappe dispatcher mismatch at " +
				vendorPath +
				": sha256 " +
				actual +
				" != " +
				PINNED_VENDOR_DISPATCHER_SHA256
		);
	}
	const source = fs.readFileSync(vendorPath, "utf8");
	const $ = {
		extend: function (target, from) {
			return Object.assign(target, from);
		},
		each: function (obj, callback) {
			if (Array.isArray(obj)) {
				obj.forEach(function (value, index) {
					callback(index, value);
				});
			} else if (obj && typeof obj === "object") {
				Object.keys(obj).forEach(function (key) {
					callback(key, obj[key]);
				});
			}
		},
		isPlainObject: function (value) {
			return !!value && typeof value === "object" && !Array.isArray(value);
		},
	};
	const sandbox = {
		$: $,
		window: {},
		console: console,
		cur_frm: null,
		frappe: {
			provide: function (path) {
				// The pinned frappe.provide walks the namespace from the global object
				// (apps/frappe/frappe/public/js/frappe/provide.js::frappe.provide).
				const parts = path.split(".");
				let target = sandbox;
				parts.forEach(function (part) {
					if (!target[part]) {
						target[part] = {};
					}
					target = target[part];
				});
				return target;
			},
			ui: { form: {} },
			get_doc: function () {
				return {};
			},
			run_serially: function (tasks) {
				let chain = Promise.resolve();
				tasks.forEach(function (task) {
					chain = chain.then(task);
				});
				return chain;
			},
			after_server_call: function () {
				return Promise.resolve();
			},
		},
	};
	const context = vm.createContext(sandbox);
	vm.runInContext(source, context, { filename: vendorPath });
	return {
		form: sandbox.frappe.ui.form,
		ScriptManager: sandbox.frappe.ui.form.ScriptManager,
		path: vendorPath,
	};
}

function mirrorDispatcher() {
	const registry = {};
	const form = {
		handlers: registry,
		get_event_handler_list: function (doctype, fieldname) {
			registry[doctype] = registry[doctype] || {};
			registry[doctype][fieldname] = registry[doctype][fieldname] || [];
			return registry[doctype][fieldname];
		},
		on: function (doctype, fieldname, handler) {
			const add = function (fieldname, handler) {
				form.get_event_handler_list(doctype, fieldname).push(handler);
			};
			if (typeof fieldname === "object") {
				// The pinned frappe.ui.form.on walks the object form field by field
				// (script_manager.js::frappe.ui.form.on -> $.each).
				for (const field of Object.keys(fieldname)) {
					add(field, fieldname[field]);
				}
			} else {
				add(fieldname, handler);
			}
		},
	};
	return { form: form, path: "mirror" };
}

test("cache is form-local and reused for the same employee", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	assert.equal(calls.length, 1);
	calls[0].resolve({ designation: "Mason" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, "Mason");

	assert.equal(frm.doc.__f44_ts_designation_state, undefined);
	assert.ok(frm.__f44_ts_designation_state);

	ctl.apply();
	await tick();
	assert.equal(calls.length, 1);
	assert.equal(frm.doc.time_logs[0].designation, "Mason");
});

test("an out-of-order response for a previous employee is discarded", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	frm.doc.employee = "HR-EMP-2";
	ctl.apply();
	await tick();
	assert.equal(calls.length, 2);

	calls[0].resolve({ designation: "Mason" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, null);

	calls[1].resolve({ designation: "Carpenter" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, "Carpenter");
});

test("a delayed response cannot mutate a document submitted meanwhile", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	frm.doc.docstatus = 1; // submitted while the lookup is in flight
	calls[0].resolve({ designation: "Mason" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, null);
	assert.equal(frm.refresh_calls, 0);
});

test("a read-only draft form is never modified (native frm.read_only)", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }], { read_only: true });
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	assert.equal(calls.length, 0);
	assert.equal(frm.doc.time_logs[0].designation, null);
});

test("a pending response cannot mutate a form that became read-only", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	frm.read_only = true; // the form becomes read-only while the lookup is in flight
	calls[0].resolve({ designation: "Mason" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, null);
	assert.equal(frm.refresh_calls, 0);
});

test("changing the employee clears the previous designation immediately", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: "Mason" }]);
	const { api } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.invalidate();
	assert.equal(frm.doc.time_logs[0].designation, null);
	ctl.apply();
	await tick();
});

test("a failed lookup clears the stale designation but an obsolete failure is ignored", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: "Mason" }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	// A request for the current employee fails.
	ctl.apply();
	await tick();
	calls[0].reject(new Error("boom"));
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, null);

	// An obsolete failure must not clear a newer employee's valid state.
	frm.doc.employee = "HR-EMP-2";
	ctl.apply();
	await tick();
	calls[1].resolve({ designation: "Carpenter" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, "Carpenter");

	const stale = client.createController(frm, api);
	frm.doc.employee = "HR-EMP-3";
	stale.apply();
	await tick();
	frm.doc.employee = "HR-EMP-2";
	stale.apply();
	await tick();
	const last = calls[calls.length - 1];
	last.reject(new Error("stale failure"));
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, "Carpenter");
});

test("rows added before the response are all derived", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	const added = { name: "row-2", designation: null };
	frm.doc.time_logs.push(added);
	ctl.apply();
	await tick();
	// The second request supersedes the first one; the newest response wins.
	const last = calls[calls.length - 1];
	last.resolve({ designation: "Mason" });
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, "Mason");
	assert.equal(added.designation, "Mason");
});

test("a row removed before the response is handled", async () => {
	const client = loadClient();
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const { api, calls } = makeApi();
	const ctl = client.createController(frm, api);

	ctl.apply();
	await tick();
	frm.doc.time_logs.splice(0, 1);
	calls[0].resolve({ designation: "Mason" });
	await tick();
	assert.equal(frm.doc.time_logs.length, 0);
});

test("the native add-row hook is wired and derives the new row", async () => {
	const client = loadClient();
	const registrations = {};
	const fakeFrappe = {
		call: () => Promise.resolve({ message: { designation: "Mason" } }),
		ui: { form: { on: (doctype, events) => (registrations[doctype] = events) } },
	};
	const handlers = client.install(fakeFrappe);

	assert.ok(registrations["Timesheet"]);
	assert.ok(registrations["Timesheet Detail"]);
	assert.ok(registrations["Timesheet"].employee);
	assert.ok(registrations["Timesheet"].refresh);
	assert.ok(registrations["Timesheet"].time_logs);
	assert.ok(registrations["Timesheet Detail"].setup);
	assert.ok(registrations["Timesheet Detail"].refresh);

	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	const apiCalls = [];
	fakeFrappe.call = (opts) => {
		apiCalls.push(opts);
		return Promise.resolve({ message: { designation: "Mason" } });
	};

	// The refresh handler wires the native add-row hook.
	registrations["Timesheet"].refresh(frm);
	await tick();
	assert.equal(typeof frm.fields_dict.time_logs.df.on_add_row, "function");

	// Native "Add Row" -> the hook derives the freshly added row.
	const added = { name: "row-2", designation: null };
	frm.doc.time_logs.push(added);
	frm.fields_dict.time_logs.df.on_add_row(2);
	await tick();
	assert.equal(added.designation, "Mason");
	assert.equal(frm.doc.time_logs[0].designation, "Mason");
	assert.ok(apiCalls.length >= 1);
	assert.ok(handlers["Timesheet::employee"]);
});

test("repeated refreshes wire the native add-row hook exactly once", async () => {
	const client = loadClient();
	const registrations = {};
	const apiCalls = [];
	const fakeFrappe = {
		call: (opts) => {
			apiCalls.push(opts);
			return Promise.resolve({ message: { designation: "Mason" } });
		},
		ui: { form: { on: (doctype, events) => (registrations[doctype] = events) } },
	};
	client.install(fakeFrappe);

	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	let originalCalls = 0;
	let originalArgs = null;
	frm.fields_dict.time_logs.df.on_add_row = function (...args) {
		originalCalls += 1;
		originalArgs = args;
	};

	// Three refreshes must not wrap the handler three times.
	registrations["Timesheet"].refresh(frm);
	registrations["Timesheet"].refresh(frm);
	registrations["Timesheet"].refresh(frm);
	await tick();

	// A different employee makes the next derivation need a fresh lookup, so the
	// lookup count for the added row is measured exactly.
	frm.doc.employee = "HR-EMP-2";
	const lookupsBefore = apiCalls.length;
	const added = { name: "row-2", designation: null };
	frm.doc.time_logs.push(added);
	frm.fields_dict.time_logs.df.on_add_row(2);
	await tick();

	assert.equal(originalCalls, 1);
	assert.deepEqual(originalArgs, [2]);
	assert.equal(apiCalls.length - lookupsBefore, 1);
	assert.equal(added.designation, "Mason");
	assert.equal(frm.doc.time_logs[0].designation, "Mason");
});

test("the native time_logs_add dispatch resolves on the child registry and derives the new row", async () => {
	const client = loadClient();
	const pinned = loadPinnedDispatcher();
	if (CI_MODE) {
		assert.ok(pinned, "CI mode must exercise the pinned vendor dispatcher");
	}
	const dispatcher = pinned || mirrorDispatcher();
	const apiCalls = [];
	const fakeFrappe = {
		call: (options) => {
			apiCalls.push(options);
			return Promise.resolve({ message: { designation: "Mason" } });
		},
		ui: { form: dispatcher.form },
	};
	client.install(fakeFrappe);

	// The pinned lookup is frappe.ui.form.handlers[doctype][event_name] with the
	// CHILD doctype, so the handler must exist on the child registry only.
	const childRegistry = dispatcher.form.handlers["Timesheet Detail"] || {};
	assert.equal(
		(childRegistry.time_logs_add || []).length,
		1,
		"one handler on the child registry"
	);
	const parentRegistry = dispatcher.form.handlers["Timesheet"] || {};
	assert.equal(
		(parentRegistry.time_logs_add || []).length,
		0,
		"no handler on the parent registry"
	);

	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: null }]);
	frm.fields_dict.time_logs.df.on_add_row = () => {};
	const added = { name: "row-2", designation: null };
	frm.doc.time_logs.push(added);

	if (pinned) {
		// Drive the ACTUAL pinned ScriptManager (grid.js -> trigger -> get_handlers).
		const manager = new dispatcher.ScriptManager({ frm: frm });
		await manager.trigger("time_logs_add", "Timesheet Detail", "row-2");
	} else {
		const handlers = dispatcher.form.handlers["Timesheet Detail"]["time_logs_add"];
		handlers.forEach((handler) => handler(frm, "Timesheet Detail", "row-2"));
	}
	await tick();
	assert.equal(apiCalls.length, 1, "one designation lookup");
	assert.equal(added.designation, "Mason", "the added row derives its designation");
});

test("the employee handler clears the previous designation before fetching", async () => {
	const client = loadClient();
	const registrations = {};
	const fakeFrappe = {
		call: () => Promise.resolve({ message: { designation: "Mason" } }),
		ui: { form: { on: (doctype, events) => (registrations[doctype] = events) } },
	};
	client.install(fakeFrappe);
	const frm = makeFrm("HR-EMP-1", [{ name: "row-1", designation: "Old" }]);
	registrations["Timesheet"].employee(frm);
	assert.equal(frm.doc.time_logs[0].designation, null);
	await tick();
	assert.equal(frm.doc.time_logs[0].designation, "Mason");
});

// ---------------------------------------------------------------------------
// Explicit pinned dispatcher configuration — provenance reliability.
//
// F44_PINNED_SCRIPT_MANAGER is an explicit operator claim about WHERE the
// qualified vendor dispatcher lives. When the variable is PRESENT it is
// authoritative: only that path may be executed. A broken explicit value
// (missing, unreadable, a directory, empty) must fail the run clearly instead
// of silently resolving a different (sibling) vendor checkout, which is what
// the earlier first-existing-candidate loader did.
//
// The regressions below execute the REAL loader in a child process against a
// controlled bench-shaped probe layout: the probe holds a copy of this test
// file, a copy of the client and (when a qualified vendor is reachable) a copy
// of the qualified vendor dispatcher. The proven behaviour is therefore the
// loader's own behaviour on a real filesystem, not a re-implementation of it.
// The parent environment is never mutated: every scenario runs in its own
// child process with an explicit environment.
// ---------------------------------------------------------------------------

// Selects the native dispatch test inside the probe copy. The probe's own
// regression tests do not match this pattern, so a probe never recurses.
const PROBE_NATIVE_DISPATCH_PATTERN = "the native time_logs_add dispatch resolves";

const probeRoots = [];

after(() => {
	probeRoots.forEach((directory) => {
		try {
			fs.rmSync(directory, { recursive: true, force: true });
		} catch (error) {
			// the probe layout is disposable; a cleanup failure is not a test failure
		}
	});
});

// Locates a vendor dispatcher whose bytes match the pinned digest. Used only to
// build the controlled probe layout below.
function qualifiedDispatcherSource() {
	const candidates = [
		process.env[PINNED_DISPATCHER_ENV_KEY],
		path.resolve(
			root,
			"..",
			"frappe",
			"frappe",
			"public",
			"js",
			"frappe",
			"form",
			"script_manager.js"
		),
		path.resolve(
			root,
			"..",
			"..",
			"frappe",
			"frappe",
			"public",
			"js",
			"frappe",
			"form",
			"script_manager.js"
		),
	].filter(Boolean);
	for (const candidate of candidates) {
		try {
			const digest = crypto
				.createHash("sha256")
				.update(fs.readFileSync(candidate))
				.digest("hex");
			if (digest === PINNED_VENDOR_DISPATCHER_SHA256) {
				return candidate;
			}
		} catch (error) {
			// not a readable file: try the next candidate
		}
	}
	return null;
}

// Builds the controlled probe layout:
//
//   <tmp>/apps/construction/construction/tests/test_timesheet_designation_client.js
//   <tmp>/apps/construction/construction/public/js/timesheet_designation.js
//   <tmp>/apps/frappe/frappe/public/js/frappe/form/script_manager.js   (optional sibling)
//
// The probe copy of this file is the real loader code and the sibling, when
// present, is the real qualified vendor dispatcher.
function createProbe(options) {
	const opts = options || {};
	const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "f44-dispatcher-probe-"));
	probeRoots.push(tmpRoot);
	const appRoot = path.join(tmpRoot, "apps", "construction");
	const testsDir = path.join(appRoot, "construction", "tests");
	const clientDir = path.join(appRoot, "construction", "public", "js");
	fs.mkdirSync(testsDir, { recursive: true });
	fs.mkdirSync(clientDir, { recursive: true });
	const testFile = path.join(testsDir, path.basename(__filename));
	fs.copyFileSync(__filename, testFile);
	fs.copyFileSync(
		path.join(root, "construction", "public", "js", "timesheet_designation.js"),
		path.join(clientDir, "timesheet_designation.js")
	);
	const probe = { tmpRoot: tmpRoot, appRoot: appRoot, testFile: testFile, vendorFile: null };
	const source = opts.vendor === false ? null : qualifiedDispatcherSource();
	if (source) {
		const vendorDir = path.join(
			tmpRoot,
			"apps",
			"frappe",
			"frappe",
			"public",
			"js",
			"frappe",
			"form"
		);
		fs.mkdirSync(vendorDir, { recursive: true });
		probe.vendorFile = path.join(vendorDir, "script_manager.js");
		fs.copyFileSync(source, probe.vendorFile);
	}
	return probe;
}

// Runs the probe copy in a child process so the loader observes exactly the
// environment under test. The parent environment is never mutated, so no
// scenario can pollute another test.
function runProbe(probe, env) {
	const childEnv = Object.assign({}, process.env);
	[PINNED_DISPATCHER_ENV_KEY, "CI", "GITHUB_ACTIONS"].forEach((key) => {
		delete childEnv[key];
	});
	Object.keys(env || {}).forEach((key) => {
		const value = env[key];
		if (value === null) {
			delete childEnv[key];
		} else {
			childEnv[key] = String(value);
		}
	});
	return new Promise((resolve) => {
		const child = spawn(
			process.execPath,
			[
				"--test",
				"--test-isolation=none",
				"--test-name-pattern",
				PROBE_NATIVE_DISPATCH_PATTERN,
				probe.testFile,
			],
			{ cwd: path.dirname(probe.testFile), env: childEnv }
		);
		let output = "";
		child.stdout.on("data", (chunk) => {
			output += chunk.toString();
		});
		child.stderr.on("data", (chunk) => {
			output += chunk.toString();
		});
		child.on("close", (code) => {
			resolve({ code: code, output: output });
		});
	});
}

function skipWithoutVendor(t) {
	t.skip(
		"no qualified Frappe dispatcher is reachable in this environment to build the sibling vendor probe"
	);
}

test("the qualified vendor dispatcher is exercised when the explicit path is unset (standard bench discovery retained)", async (t) => {
	const probe = createProbe({});
	if (!probe.vendorFile) {
		skipWithoutVendor(t);
		return;
	}
	const result = await runProbe(probe, {
		[PINNED_DISPATCHER_ENV_KEY]: null,
		CI: "true",
		GITHUB_ACTIONS: "true",
	});
	assert.equal(
		result.code,
		0,
		"with the explicit path unset the standard bench discovery must still resolve the sibling vendor:\n" +
			result.output
	);
});

test("an explicit pinned dispatcher path is authoritative: a missing path fails closed even when a valid sibling vendor exists", async (t) => {
	const probe = createProbe({});
	if (!probe.vendorFile) {
		skipWithoutVendor(t);
		return;
	}
	const missing = path.join(probe.tmpRoot, "absent-vendor", "script_manager.js");
	const result = await runProbe(probe, {
		[PINNED_DISPATCHER_ENV_KEY]: missing,
		CI: "true",
		GITHUB_ACTIONS: "true",
	});
	assert.notEqual(
		result.code,
		0,
		"a missing explicit path must fail the run instead of silently using the sibling vendor:\n" +
			result.output
	);
	assert.match(result.output, /F44_PINNED_SCRIPT_MANAGER/);
	assert.match(result.output, /does not exist/);
});

test("an explicit pinned dispatcher path that is not a regular file fails closed", async () => {
	const probe = createProbe({});
	const directory = path.join(probe.tmpRoot, "vendor-directory");
	fs.mkdirSync(directory, { recursive: true });
	const result = await runProbe(probe, { [PINNED_DISPATCHER_ENV_KEY]: directory });
	assert.notEqual(
		result.code,
		0,
		"an explicit path that is a directory must fail the run:\n" + result.output
	);
	assert.match(result.output, /not a regular file/);
});

test("an explicit pinned dispatcher path that is not readable fails closed", async (t) => {
	if (typeof process.getuid === "function" && process.getuid() === 0) {
		// root bypasses the read permission bits, so the case cannot be produced
		t.skip("the unreadable-file case cannot be produced as root");
		return;
	}
	const probe = createProbe({});
	const unreadable = path.join(probe.tmpRoot, "unreadable-script_manager.js");
	fs.writeFileSync(unreadable, "// not readable\n", { mode: 0o000 });
	const result = await runProbe(probe, { [PINNED_DISPATCHER_ENV_KEY]: unreadable });
	assert.notEqual(
		result.code,
		0,
		"an explicit path that is not readable must fail the run:\n" + result.output
	);
	assert.match(result.output, /not readable/);
});

test("an empty explicit pinned dispatcher path fails closed", async () => {
	const probe = createProbe({});
	const result = await runProbe(probe, { [PINNED_DISPATCHER_ENV_KEY]: "   " });
	assert.notEqual(result.code, 0, "an empty explicit path must fail the run:\n" + result.output);
	assert.match(result.output, /set but empty/);
});

test("a valid explicit pinned dispatcher path is digest-verified and drives the real dispatcher", async (t) => {
	const probe = createProbe({});
	if (!probe.vendorFile) {
		skipWithoutVendor(t);
		return;
	}
	const result = await runProbe(probe, {
		[PINNED_DISPATCHER_ENV_KEY]: probe.vendorFile,
		CI: "true",
		GITHUB_ACTIONS: "true",
	});
	assert.equal(
		result.code,
		0,
		"a valid explicit path must be digest-verified and executed:\n" + result.output
	);
});

test("the explicit path is executed instead of a sibling vendor checkout", async (t) => {
	const probe = createProbe({});
	if (!probe.vendorFile) {
		skipWithoutVendor(t);
		return;
	}
	// The sibling vendor is tampered: a loader that preferred the sibling over
	// the explicit configuration would fail the digest check. The explicit path
	// holds the qualified bytes, so the run must succeed.
	const explicit = path.join(probe.tmpRoot, "qualified-script_manager.js");
	fs.copyFileSync(probe.vendorFile, explicit);
	fs.appendFileSync(probe.vendorFile, "\n// tampered sibling vendor\n");
	const result = await runProbe(probe, {
		[PINNED_DISPATCHER_ENV_KEY]: explicit,
		CI: "true",
		GITHUB_ACTIONS: "true",
	});
	assert.equal(
		result.code,
		0,
		"the explicit path must be executed, not the sibling vendor checkout:\n" + result.output
	);
});

test("a tampered explicit pinned dispatcher path is rejected even when a valid sibling vendor exists", async (t) => {
	const probe = createProbe({});
	if (!probe.vendorFile) {
		skipWithoutVendor(t);
		return;
	}
	const tampered = path.join(probe.tmpRoot, "tampered-script_manager.js");
	fs.copyFileSync(probe.vendorFile, tampered);
	fs.appendFileSync(tampered, "\n// tampered explicit vendor\n");
	const result = await runProbe(probe, {
		[PINNED_DISPATCHER_ENV_KEY]: tampered,
		CI: "true",
		GITHUB_ACTIONS: "true",
	});
	assert.notEqual(
		result.code,
		0,
		"a tampered explicit path must fail the run instead of falling back to the sibling vendor:\n" +
			result.output
	);
	assert.match(result.output, /mismatch/);
});

test("CI mode with no reachable pinned dispatcher fails closed", async () => {
	const probe = createProbe({ vendor: false });
	const result = await runProbe(probe, {
		[PINNED_DISPATCHER_ENV_KEY]: null,
		CI: "true",
		GITHUB_ACTIONS: "true",
	});
	assert.notEqual(
		result.code,
		0,
		"CI mode without a reachable pinned dispatcher must fail the run:\n" + result.output
	);
	assert.match(result.output, /CI mode requires the pinned Frappe dispatcher/);
});

test("a local run without an explicit path and without a sibling vendor keeps the labelled local mirror behavior", async () => {
	const probe = createProbe({ vendor: false });
	const result = await runProbe(probe, { [PINNED_DISPATCHER_ENV_KEY]: null });
	assert.equal(
		result.code,
		0,
		"outside CI mode the labelled local mirror behavior must be retained:\n" + result.output
	);
});
