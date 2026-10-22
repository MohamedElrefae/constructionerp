const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");

function loadVfc() {
	const registrations = {};
	const confirmations = [];
	const settings = {};
	const document = {
		addEventListener() {},
		removeEventListener() {},
		getElementById() {
			return null;
		},
		querySelectorAll() {
			return [];
		},
		body: { appendChild() {} },
	};
	const window = {};
	const context = {
		window,
		document,
		localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
		setTimeout() {},
		clearTimeout() {},
		console,
		vfcDebugLog() {},
		__(message) {
			return message;
		},
		frappe: {
			ui: { form: { on: (doctype, events) => (registrations[doctype] = events) } },
			user_roles: [],
			session: { user: "test@example.com" },
			get_user_settings() {
				return settings[arguments[0]] || {};
			},
			model: {
				user_settings: {
					save(doctype, key, value) {
						settings[doctype] = { ...settings[doctype], [key]: value };
						return Promise.resolve();
					},
				},
			},
			confirm: (message) => confirmations.push(message),
			get_route_str: () => "Form/Purchase Order/PO-1",
			set_route() {},
			show_alert() {},
			router: { on() {} },
		},
	};
	vm.runInNewContext(
		fs.readFileSync(path.join(root, "construction/public/js/vite_layout_controls.js"), "utf8"),
		context
	);
	return { vfc: window._VFC, document, confirmations };
}

function makePanel(frm, checkboxes = []) {
	const panel = {
		isConnected: true,
		__vfc_frm: frm,
		getAttribute: (name) => (name === "data-doctype" ? frm.doctype : null),
		closest: () => panel,
		querySelectorAll: () => checkboxes,
		querySelector: () => null,
	};
	frm._vfc_panel = panel;
	return panel;
}

test("VFC section callbacks edit their rendering form after switching to same doctype", () => {
	const { vfc } = loadVfc();
	const formOne = { doctype: "Purchase Order", _vfc_temp_layout: [{ label: "One" }] };
	const formTwo = { doctype: "Purchase Order", _vfc_temp_layout: [{ label: "Two" }] };
	const panelOne = makePanel(formOne);
	makePanel(formTwo);
	const control = { value: "One edited", closest: () => panelOne };
	vfc._onSecLabelChange(control, "Purchase Order", 0);
	assert.equal(formOne._vfc_temp_layout[0].label, "One edited");
	assert.equal(formTwo._vfc_temp_layout[0].label, "Two");
});

test("VFC stale detached panel does not mutate its former form", () => {
	const { vfc } = loadVfc();
	const frm = { doctype: "Purchase Order", _vfc_temp_layout: [{ label: "Original" }] };
	const panel = makePanel(frm);
	panel.isConnected = false;
	const control = { value: "Stale edit", closest: () => panel };
	vfc._onSecLabelChange(control, frm.doctype, 0);
	assert.equal(frm._vfc_temp_layout[0].label, "Original");
});

test("VFC dirty status, Apply & Save, and route guard use the bound form panel", async () => {
	const { vfc, confirmations } = loadVfc();
	const frm = { doctype: "Purchase Order" };
	const otherFrm = { doctype: "Purchase Order" };
	const staged = { checked: false, disabled: false, getAttribute: () => "project" };
	const panel = makePanel(frm, [staged]);
	makePanel(otherFrm, []);
	const status = { textContent: "", style: {}, classList: { add() {}, remove() {} } };
	panel.querySelector = (selector) => {
		if (selector.startsWith("#vfc-status-")) return status;
		if (selector.includes(".vfc-pre-item")) return null;
		return { classList: { toggle() {} } };
	};
	assert.deepEqual(Array.from(vfc._dirtyFields(frm)), ["project"]);
	assert.deepEqual(Array.from(vfc._dirtyFields(otherFrm)), []);
	// The dirty indicator is updated from frm and remains actionable for Apply & Save.
	vfc._updateDirtyStatus(frm);
	assert.match(status.textContent, /Unsaved changes/);
	vfc._onRouteChange(frm);
	assert.equal(confirmations.length, 1);
	vfc._applyDensity = () => {};
	vfc._applyVisibility = () => ["project"];
	let closedForm;
	vfc._togglePanel = (savedFrm) => (closedForm = savedFrm);
	await vfc._applyAndSave(frm, "Purchase-Order");
	assert.equal(closedForm, frm);
	assert.equal(status.textContent, "Saved via user settings");
});

function loadLinkEnhancer() {
	const namespace = { ct_link_enhancer: {} };
	function $(element) {
		return {
			0: element.controlWrapper,
			on() {
				return this;
			},
			ready() {
				return this;
			},
			length: 1,
			hasClass: () => false,
			attr(name) {
				return element.attributes?.[name] || "";
			},
			closest(selector) {
				if (selector === ".frappe-control") return element.controlWrapper;
				if (selector === ".grid-row") return element.gridRow || { length: 0 };
				if (selector === ".link-field") return { length: 0 };
				return { length: 0 };
			},
		};
	}
	const context = {
		window: { cur_frm: null, cur_dialog: null, cur_list: null },
		document: {},
		$: $,
		setTimeout() {},
		console,
		__: (message) => message,
		frappe: {
			ui: { form: {} },
			boot: {},
			provide() {
				context.construction = namespace;
			},
		},
		MutationObserver: undefined,
	};
	vm.runInNewContext(
		fs.readFileSync(
			path.join(root, "construction/public/js/overrides/ct_link_control.js"),
			"utf8"
		),
		context
	);
	return { enhancer: namespace.ct_link_enhancer, window: context.window };
}

function ownsInput(input) {
	return { contains: (candidate) => candidate === input };
}

function linkControlHarness({ gridField, dialogField, listField } = {}) {
	const wrapper = { fieldobj: undefined };
	const wrapperQuery = { 0: wrapper, length: 1, attr: () => "boq_item" };
	const input = {
		attributes: { "data-fieldname": "boq_item" },
		controlWrapper: wrapperQuery,
		getAttribute(name) {
			return this.attributes[name] || null;
		},
		setAttribute(name, value) {
			this.attributes[name] = value;
		},
		closest(selector) {
			if (selector === ".frappe-control") return wrapperQuery;
			if (selector === ".grid-row")
				return gridField
					? { length: 1, data: () => ({ fields_dict: { boq_item: gridField } }) }
					: { length: 0 };
			return { length: 0 };
		},
	};
	if (gridField?.owned) gridField.wrapper = ownsInput(input);
	if (dialogField?.owned) dialogField.$wrapper = ownsInput(input);
	if (listField?.owned) listField.wrapper = ownsInput(input);
	input.gridRow = gridField
		? { length: 1, data: () => ({ fields_dict: { boq_item: gridField } }) }
		: { length: 0 };
	return input;
}

test("link enhancer does not borrow a same-named field from the active form", () => {
	const { enhancer, window } = loadLinkEnhancer();
	window.cur_frm = { fields_dict: { boq_item: { df: { fieldtype: "Link" } } } };
	const input = linkControlHarness();
	enhancer.enhanceLink(input);
	assert.equal(input.getAttribute("data-ct-link-enhanced"), null);
});

test("link enhancer accepts only locally owned grid, dialog, and list controls", () => {
	const { enhancer, window } = loadLinkEnhancer();
	window.cur_frm = { fields_dict: { boq_item: { df: { fieldtype: "Link" } } } };
	const gridInput = linkControlHarness({
		gridField: { df: { fieldtype: "Link", options: "Project" } },
	});
	enhancer.enhanceLink(gridInput);
	assert.equal(gridInput.getAttribute("data-ct-link-enhanced"), null);

	window.cur_dialog = {
		fields_dict: {
			boq_item: {
				df: { fieldtype: "Link", options: "Project" },
				$wrapper: { contains: () => false },
			},
		},
	};
	const unrelatedDialogInput = linkControlHarness();
	enhancer.enhanceLink(unrelatedDialogInput);
	assert.equal(unrelatedDialogInput.getAttribute("data-ct-link-enhanced"), null);

	window.cur_dialog = {
		fields_dict: { boq_item: { df: { fieldtype: "Link", options: "Project" }, owned: true } },
	};
	const dialogInput = linkControlHarness({
		dialogField: window.cur_dialog.fields_dict.boq_item,
	});
	enhancer.enhanceLink(dialogInput);
	assert.equal(dialogInput.getAttribute("data-ct-link-enhanced"), "1");

	window.cur_list = {
		page: {
			fields_dict: {
				boq_item: {
					df: { fieldtype: "Link", options: "Project" },
					wrapper: { contains: () => false },
				},
			},
		},
	};
	const unrelatedListInput = linkControlHarness();
	enhancer.enhanceLink(unrelatedListInput);
	assert.equal(unrelatedListInput.getAttribute("data-ct-link-enhanced"), null);

	window.cur_list = {
		page: {
			fields_dict: {
				boq_item: { df: { fieldtype: "Link", options: "Project" }, owned: true },
			},
		},
	};
	const listInput = linkControlHarness({ listField: window.cur_list.page.fields_dict.boq_item });
	enhancer.enhanceLink(listInput);
	assert.equal(listInput.getAttribute("data-ct-link-enhanced"), "1");
});

test("BOQ scope refresh updates all mounted forms and prunes a removed form", () => {
	const handlers = {};
	const documentEvents = {};
	const routeHandlers = [];
	const alerts = [];
	let notice;
	const document = {
		getElementById: () => notice || null,
		createElement: () => (notice = { style: {}, setAttribute() {} }),
		body: { appendChild() {} },
	};
	const context = {
		document,
		window: {},
		console,
		setTimeout() {},
		clearTimeout() {},
		__: (message) => message,
		frappe: {
			boot: { enable_boq_cascade_filtering: "Off" },
			ui: { form: { on: (doctype, events) => (handlers[doctype] = events) } },
			router: { on: (_event, handler) => routeHandlers.push(handler) },
			show_alert: (alert) => alerts.push(alert),
		},
		$: (target) => ({
			on(event, handler) {
				if (target === document) documentEvents[event] = handler;
			},
			ready() {},
		}),
	};
	vm.runInNewContext(
		fs.readFileSync(path.join(root, "construction/public/js/boq_filters.js"), "utf8"),
		context
	);
	function makeForm(isConnected) {
		return {
			doc: { doctype: "Purchase Order", items: [] },
			wrapper: [{ isConnected }],
			fields_dict: { items: { grid: { get_field: () => null } } },
			set_query() {},
			refresh_field() {
				this.refreshCount = (this.refreshCount || 0) + 1;
			},
		};
	}
	const formA = makeForm(true);
	const formB = makeForm(true);
	const removedForm = makeForm(false);
	const missingWrapperForm = makeForm(true);
	missingWrapperForm.wrapper = null;
	[formA, formB, removedForm, missingWrapperForm].forEach((frm) =>
		handlers["Purchase Order"].setup(frm)
	);
	documentEvents["scope:changed.ct_boq"]();
	assert.equal(formA.refreshCount, 1);
	assert.equal(formB.refreshCount, 1);
	assert.equal(removedForm.refreshCount, undefined);
	assert.equal(missingWrapperForm.refreshCount, undefined);
	assert.equal(routeHandlers.length, 1);
});
