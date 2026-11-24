const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");

class MiniNode {
	constructor(tagName) {
		this.tagName = tagName.toUpperCase();
		this.attributes = Object.create(null);
		this.children = [];
		this.parentNode = null;
		this.style = {};
		this.className = "";
		this.id = "";
		this.textContent = "";
	}

	get childNodes() {
		return this.children;
	}

	setAttribute(name, value) {
		this.attributes[name] = String(value);
		if (name === "class") this.className = String(value);
		if (name === "id") this.id = String(value);
	}

	getAttribute(name) {
		if (name === "class" && this.className) return this.className;
		if (name === "id" && this.id) return this.id;
		return Object.prototype.hasOwnProperty.call(this.attributes, name)
			? this.attributes[name]
			: null;
	}

	appendChild(child) {
		child.parentNode = this;
		this.children.push(child);
		return child;
	}

	insertBefore(newNode, refNode) {
		newNode.parentNode = this;
		if (!refNode) {
			this.children.push(newNode);
			return newNode;
		}
		const idx = this.children.indexOf(refNode);
		if (idx === -1) {
			this.children.push(newNode);
		} else {
			this.children.splice(idx, 0, newNode);
		}
		return newNode;
	}

	get nextSibling() {
		if (!this.parentNode) return null;
		const idx = this.parentNode.children.indexOf(this);
		return idx >= 0 && idx + 1 < this.parentNode.children.length
			? this.parentNode.children[idx + 1]
			: null;
	}

	remove() {
		if (!this.parentNode) return;
		this.parentNode.children = this.parentNode.children.filter((c) => c !== this);
		this.parentNode = null;
	}

	replaceChildren(...nodes) {
		this.children = [];
		nodes.forEach((n) => this.appendChild(n));
	}

	_matches(selector) {
		const attrMatch = selector.match(/^(\.[\w-]+)?\[([^=\]]+)="([^"]*)"\]$/);
		if (attrMatch) {
			const [, clsPart, attrName, attrVal] = attrMatch;
			if (clsPart && !this._matches(clsPart)) return false;
			return this.getAttribute(attrName) === attrVal;
		}
		if (selector.startsWith(".")) {
			const cls = selector.slice(1);
			return (this.className || "").split(/\s+/).includes(cls);
		}
		return this.tagName === selector.toUpperCase();
	}

	querySelectorAll(selector) {
		const out = [];
		const walk = (node) => {
			for (const child of node.children) {
				if (child._matches(selector)) out.push(child);
				walk(child);
			}
		};
		walk(this);
		return out;
	}

	querySelector(selector) {
		return this.querySelectorAll(selector)[0] || null;
	}

	allText() {
		if (!this.children.length) return this.textContent || "";
		return (
			(this.textContent || "") +
			this.children.map((c) => c.allText()).join(" ")
		).trim();
	}
}

function createHarness(scriptRelPath, { roles = [], callResponder = null, dbGetValue = null } = {}) {
	const handlers = {};
	const dialogs = [];
	const calls = [];
	const alerts = [];
	const msgprints = [];
	const fieldContainers = Object.create(null);

	const documentStub = {
		createElement: (tag) => new MiniNode(tag),
		querySelector: (sel) => {
			const m = sel.match(/data-fieldname="([^"]+)"/);
			if (m && fieldContainers[m[1]]) return fieldContainers[m[1]];
			return null;
		},
	};

	const jqueryStub = () => {
		const chain = {
			length: 0,
			toggleClass: () => chain,
			find: () => chain,
			first: () => chain,
			remove: () => chain,
			append: () => chain,
			before: () => chain,
			off: () => chain,
			on: () => chain,
			slideUp: () => chain,
		};
		return chain;
	};

	class MockDialog {
		constructor(opts) {
			this.opts = opts;
			this.shown = false;
			this.hidden = false;
			this.fields_dict = {};
			(opts.fields || []).forEach((f) => {
				const node = new MiniNode("div");
				this.fields_dict[f.fieldname] = { df: f, $wrapper: [node] };
			});
			dialogs.push(this);
		}
		show() {
			this.shown = true;
		}
		hide() {
			this.hidden = true;
		}
		submit(values) {
			return this.opts.primary_action(values);
		}
	}

	const frappeStub = {
		boot: { enable_boq_cascade_filtering: "Off", scope_context: {} },
		user: {
			has_role: (role) => roles.includes(role),
		},
		ui: {
			Dialog: MockDialog,
			form: {
				on(doctype, map) {
					handlers[doctype] = map;
				},
			},
		},
		db: {
			get_value: (...args) => (dbGetValue ? dbGetValue(...args) : Promise.resolve({ message: {} })),
		},
		call(opts) {
			calls.push({ method: opts.method, type: opts.type, freeze: Boolean(opts.freeze), args: opts.args });
			if (callResponder) {
				const resp = callResponder(opts);
				if (resp !== undefined && typeof opts.callback === "function") {
					opts.callback(resp);
				}
			}
		},
		show_alert(opts) {
			alerts.push(opts);
		},
		msgprint(msg) {
			msgprints.push(msg);
		},
		set_route() {},
		new_doc() {},
	};

	const __ = (text, args) => {
		if (!Array.isArray(args)) return text;
		return args.reduce((acc, val, idx) => acc.replace(`{${idx}}`, String(val)), text);
	};

	const context = vm.createContext({
		window: {},
		document: documentStub,
		localStorage: { getItem: () => "1", setItem: () => {} },
		setTimeout: () => 0,
		$: jqueryStub,
		jQuery: jqueryStub,
		frappe: frappeStub,
		__: __,
		flt: (v) => Number(v || 0),
	});

	const code = fs.readFileSync(path.join(root, scriptRelPath), "utf8");
	vm.runInContext(code, context, { filename: scriptRelPath });

	function makeFrm({ doc, isNew = false, writePerm = true, dirty = false, fieldname }) {
		const formColumn = new MiniNode("div");
		formColumn.className = "form-column";
		const controlWrapper = new MiniNode("div");
		controlWrapper.className = "frappe-control hide-control";
		formColumn.appendChild(controlWrapper);
		fieldContainers[fieldname] = controlWrapper;
		const buttons = [];
		const dfProps = [];
		const setValues = [];
		let isDirty = dirty;
		let reloaded = 0;
		const frm = {
			doc: { ...doc },
			is_new: () => isNew,
			is_dirty: () => isDirty,
			setDirty(flag) {
				isDirty = Boolean(flag);
			},
			perm: [{ write: writePerm ? 1 : 0 }],
			fields_dict: {
				[fieldname]: { df: {}, $wrapper: [controlWrapper] },
			},
			dashboard: {
				hide() {},
				clear_headline() {},
				set_headline() {},
				add_indicator() {},
			},
			set_query() {},
			set_df_property(f, p, v) {
				dfProps.push([f, p, v]);
			},
			set_value(f, v) {
				frm.doc[f] = v;
				setValues.push([f, v]);
				return Promise.resolve();
			},
			add_custom_button(label, action, group) {
				buttons.push({ label, action, group });
			},
			remove_custom_button(label, group) {
				for (let i = buttons.length - 1; i >= 0; i--) {
					if (buttons[i].label === label && (!group || buttons[i].group === group)) {
						buttons.splice(i, 1);
					}
				}
			},
			reload_doc() {
				reloaded += 1;
			},
			_buttons: buttons,
			_dfProps: dfProps,
			_setValues: setValues,
			_control: controlWrapper,
			_container: formColumn,
			_getReloaded: () => reloaded,
		};
		return frm;
	}

	return { handlers, dialogs, calls, alerts, msgprints, makeFrm };
}

test("BOQ Item: Accountant sees location, disabled-ancestor alert, product rule, and zero planner actions", () => {
	const h = createHarness("construction/construction/doctype/boq_item/boq_item.js", {
		roles: ["Accountant"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item",
						name: "BOQ-ITEM-001",
						project: "PROJ-1",
						assigned: {
							node: "EBN-0003",
							ebs_code: "EBS-0003",
							title: "Floor 2",
							full_path: "Building A / Floor 2",
							is_effectively_disabled: true,
							disabled_reason: "ancestor",
						},
						attribution: {
							action: "set",
							is_historical_assignment: false,
							mapped_by: "owner@example.test",
							mapped_on: "2026-11-24 10:00:00",
						},
					},
				};
			}
		},
	});

	const frm = h.makeFrm({
		doc: { name: "BOQ-ITEM-001", boq_header: "BOQ-H-1", planned_execution_node: "EBN-0003" },
		isNew: false,
		writePerm: false,
		fieldname: "planned_execution_node",
	});

	h.handlers["BOQ Item"].refresh(frm);

	const text = frm._container.allText();
	assert.match(text, /EBS-0003/);
	assert.match(text, /Building A \/ Floor 2/);
	assert.match(
		text,
		/Changing the BOQ Item's planned location affects future Stages only; existing Stage locations remain unchanged\./
	);

	const alertEl = frm._container.querySelector(".ct-exec-loc-warning");
	assert.ok(alertEl);
	assert.equal(alertEl.getAttribute("role"), "alert");
	assert.match(alertEl.textContent, /disabled ancestor branch/);

	const execButtons = frm._buttons.filter((b) => b.group === "Execution Location");
	assert.equal(execButtons.length, 0);
	assert.deepEqual(
		h.calls.map((c) => c.method),
		["construction.api.execution_mapping_api.get_mapping_display_context"]
	);
});

test("BOQ Item: Construction Owner can change location with mandatory reason and inspect XSS-safe audit table", () => {
	const h = createHarness("construction/construction/doctype/boq_item/boq_item.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item",
						name: "BOQ-ITEM-001",
						project: "PROJ-1",
						assigned: {
							node: "EBN-0001",
							ebs_code: "EBS-0001",
							title: "Building A",
							full_path: "Site / Building A",
							is_effectively_disabled: false,
							disabled_reason: null,
						},
						attribution: null,
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return {
					message: [
						{ name: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" },
					],
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.set_item_planned_execution_node") {
				return { message: { changed: true, action: "change" } };
			}
			if (opts.method === "construction.api.execution_mapping_api.get_execution_mapping_audit") {
				return {
					message: [
						{
							changed_on: "2026-11-24 12:00:00",
							action: "change",
							old_ebs_code: "EBS-0001",
							old_path_snapshot: "Site / Building A",
							new_ebs_code: "EBS-0002",
							new_path_snapshot: "Site / <script>alert(1)</script>",
							reason: "<img src=x onerror=alert(1)> Shift phase 2",
							changed_by: "owner@example.test",
						},
					],
				};
			}
		},
	});

	const frm = h.makeFrm({
		doc: {
			name: "BOQ-ITEM-001",
			boq_header: "BOQ-H-1",
			planned_execution_node: "EBN-0001",
			modified: "2026-11-24 11:00:00.000000",
		},
		isNew: false,
		writePerm: true,
		fieldname: "planned_execution_node",
	});

	h.handlers["BOQ Item"].refresh(frm);

	const execButtons = frm._buttons.filter((b) => b.group === "Execution Location");
	assert.deepEqual(
		execButtons.map((b) => b.label),
		["Change Planned Location", "Clear Planned Location", "View Mapping History"]
	);

	// Open Change Planned Location dialog: blank reason must be rejected client-side.
	execButtons[0].action();
	const pickerDlg = h.dialogs[0];
	assert.ok(pickerDlg.shown);
	pickerDlg.submit({ execution_node: "EBN-0002", reason: "   " });
	assert.equal(h.msgprints.at(-1), "Reason is required for this change.");

	// Submitting with a reason sends POST with expected_modified and reloads form.
	pickerDlg.submit({ execution_node: "EBN-0002", reason: "Phase 2 shifts to B" });
	const postCall = h.calls.find(
		(c) => c.method === "construction.api.execution_mapping_api.set_item_planned_execution_node"
	);
	assert.equal(postCall.type, "POST");
	assert.deepEqual(
		{ ...postCall.args },
		{
			boq_item: "BOQ-ITEM-001",
			execution_node: "EBN-0002",
			reason: "Phase 2 shifts to B",
			expected_modified: "2026-11-24 11:00:00.000000",
		}
	);
	assert.equal(frm._getReloaded(), 1);

	// Open View Mapping History dialog: verify accessible semantic table & XSS-safe textContent.
	execButtons[2].action();
	const auditDlg = h.dialogs[1];
	const auditBody = auditDlg.fields_dict.history_html.$wrapper[0];
	const region = auditBody.querySelector(".ct-exec-audit-table-wrap");
	assert.equal(region.getAttribute("role"), "region");
	assert.equal(region.getAttribute("tabindex"), "0");
	assert.ok(auditBody.querySelector("caption"));
	const ths = auditBody.querySelectorAll("th");
	assert.equal(ths.length, 6);
	assert.ok(ths.every((th) => th.getAttribute("scope") === "col"));
	// No <script> or <img> element created — untrusted payload remains literal text.
	assert.equal(auditBody.querySelectorAll("script").length, 0);
	assert.equal(auditBody.querySelectorAll("img").length, 0);
	assert.match(auditBody.allText(), /<script>alert\(1\)<\/script>/);
	assert.match(auditBody.allText(), /<img src=x onerror=alert\(1\)>/);
});

test("BOQ Item Stage: Site Engineer on new Stage sees read-only inherited preview without mutating field or getting buttons", () => {
	const h = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Site Engineer"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_new_stage_default_preview") {
				return {
					message: {
						boq_item: "BOQ-ITEM-001",
						project: "PROJ-1",
						will_inherit: true,
						preview: {
							node: "EBN-0001",
							ebs_code: "EBS-0001",
							full_path: "Site / Building A",
						},
					},
				};
			}
		},
	});

	const frm = h.makeFrm({
		doc: { boq_item: "BOQ-ITEM-001", project: "PROJ-1", execution_node: "" },
		isNew: true,
		writePerm: true,
		fieldname: "execution_node",
	});

	h.handlers["BOQ Item Stage"].refresh(frm);

	assert.equal(frm.doc.execution_node, "");
	assert.equal(frm._setValues.length, 0);
	assert.match(
		frm._container.allText(),
		/Will inherit from BOQ Item on save: EBS-0001 — Site \/ Building A/
	);
	assert.equal(
		frm._buttons.filter((b) => b.group === "Execution Location").length,
		0
	);
});

test("BOQ Item Stage: disabled parent default shows alert on new Stage; measured unmapped Stage requires reason for Historical assignment", () => {
	const h = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_new_stage_default_preview") {
				return {
					message: {
						boq_item: "BOQ-ITEM-001",
						project: "PROJ-1",
						will_inherit: false,
						preview: {
							node: "EBN-0009",
							ebs_code: "EBS-0009",
							full_path: "Disabled Wing / Floor 1",
						},
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item Stage",
						name: "BOQ-STG-00010",
						project: "PROJ-1",
						assigned: null,
						attribution: null,
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return {
					message: [
						{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" },
					],
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.set_stage_execution_node") {
				return {
					message: {
						changed: true,
						action: "initial_historical_map",
						is_historical_assignment: true,
					},
				};
			}
		},
	});

	// 1. New Stage with disabled parent default shows role="alert" warning.
	const newFrm = h.makeFrm({
		doc: { boq_item: "BOQ-ITEM-001", project: "PROJ-1", execution_node: "" },
		isNew: true,
		writePerm: true,
		fieldname: "execution_node",
	});
	h.handlers["BOQ Item Stage"].refresh(newFrm);
	const warn = newFrm._container.querySelector(".ct-exec-loc-warning");
	assert.ok(warn);
	assert.equal(warn.getAttribute("role"), "alert");
	assert.match(warn.textContent, /is disabled and will not be inherited/);

	// 2. Existing unmapped Stage with measured_executed_qty > 0 prompts Historical assignment + requires reason.
	const existingFrm = h.makeFrm({
		doc: {
			name: "BOQ-STG-00010",
			boq_item: "BOQ-ITEM-001",
			project: "PROJ-1",
			execution_node: "",
			measured_executed_qty: 25,
			certified_qty: 0,
			stage_status: "In Progress",
			modified: "2026-11-24 14:00:00.000000",
		},
		isNew: false,
		writePerm: true,
		fieldname: "execution_node",
	});
	h.handlers["BOQ Item Stage"].refresh(existingFrm);
	const setBtn = existingFrm._buttons.find((b) => b.label === "Set Execution Location");
	assert.ok(setBtn);
	setBtn.action();
	const dlg = h.dialogs.at(-1);
	assert.match(
		dlg.fields_dict.historical_note.$wrapper[0].allText(),
		/Historical assignment \(reason required\)/
	);
	dlg.submit({ execution_node: "EBN-0002", reason: "" });
	assert.equal(h.msgprints.at(-1), "Reason is required for this change.");

	dlg.submit({ execution_node: "EBN-0002", reason: "Legacy work done in Building B" });
	assert.equal(h.alerts.at(-1).message, "Historical execution location assigned.");
	assert.equal(existingFrm._getReloaded(), 1);
});

test("BOQ Item Stage: Accountant sees Historical assignment badge with zero planner buttons; Planner can override on new Stage and reset to inherited default", () => {
	// 1. Accountant on historically assigned Stage sees badge, zero buttons, zero audit/picker calls.
	const hAcct = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Accountant"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item Stage",
						name: "BOQ-STG-00011",
						project: "PROJ-1",
						assigned: {
							node: "EBN-0001",
							ebs_code: "EBS-0001",
							full_path: "Site / Building A",
							is_effectively_disabled: false,
							disabled_reason: null,
						},
						attribution: {
							action: "initial_historical_map",
							is_historical_assignment: true,
							mapped_by: "owner@example.test",
							mapped_on: "2026-11-24 15:00:00",
						},
					},
				};
			}
		},
	});
	const acctFrm = hAcct.makeFrm({
		doc: { name: "BOQ-STG-00011", boq_item: "BOQ-ITEM-001", project: "PROJ-1", execution_node: "EBN-0001" },
		isNew: false,
		writePerm: false,
		fieldname: "execution_node",
	});
	hAcct.handlers["BOQ Item Stage"].refresh(acctFrm);
	assert.match(acctFrm._container.allText(), /Historical assignment/);
	assert.match(acctFrm._container.allText(), /Site \/ Building A/);
	assert.equal(acctFrm._buttons.filter((b) => b.group === "Execution Location").length, 0);
	assert.deepEqual(
		hAcct.calls.map((c) => c.method),
		["construction.api.execution_mapping_api.get_mapping_display_context"]
	);

	// 2. Planner on new Stage can select explicit override and revert to inherited default.
	const hOwner = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_new_stage_default_preview") {
				return {
					message: {
						boq_item: "BOQ-ITEM-001",
						project: "PROJ-1",
						will_inherit: true,
						preview: { node: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return {
					message: [
						{ name: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" },
					],
				};
			}
		},
	});
	const newFrm = hOwner.makeFrm({
		doc: { boq_item: "BOQ-ITEM-001", project: "PROJ-1", execution_node: "" },
		isNew: true,
		writePerm: true,
		fieldname: "execution_node",
	});
	hOwner.handlers["BOQ Item Stage"].refresh(newFrm);
	const selBtn = newFrm._buttons.find((b) => b.label === "Select Execution Location");
	assert.ok(selBtn);
	selBtn.action();
	hOwner.dialogs[0].submit({ execution_node: "EBN-0002" });
	assert.equal(newFrm.doc.execution_node, "EBN-0002");
	assert.match(newFrm._container.allText(), /Explicit override selected for this new Stage: EBS-0002 — Site \/ Building B/);
});

test("Dirty form guard: blocks Item & Stage change/clear writes so unsaved edits are never discarded", () => {
	// 1. Dirty BOQ Item blocks both Change and Clear (before opening dialog AND if dirtied while dialog is open).
	const hItem = createHarness("construction/construction/doctype/boq_item/boq_item.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item",
						name: "BOQ-ITEM-001",
						project: "PROJ-1",
						assigned: { node: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						attribution: null,
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return { message: [{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" }] };
			}
		},
	});
	const itemFrm = hItem.makeFrm({
		doc: { name: "BOQ-ITEM-001", boq_header: "BOQ-H-1", planned_execution_node: "EBN-0001", modified: "2026-11-24 10:00:00" },
		isNew: false,
		writePerm: true,
		dirty: true,
		fieldname: "planned_execution_node",
	});
	hItem.handlers["BOQ Item"].refresh(itemFrm);
	const itemChangeBtn = itemFrm._buttons.find((b) => b.label === "Change Planned Location");
	const itemClearBtn = itemFrm._buttons.find((b) => b.label === "Clear Planned Location");
	itemChangeBtn.action();
	itemClearBtn.action();
	assert.equal(hItem.dialogs.length, 0);
	assert.equal(hItem.msgprints.length, 2);
	assert.match(hItem.msgprints[0].message, /save or discard your unsaved form changes/);
	assert.equal(
		hItem.calls.filter((c) => c.method === "construction.api.execution_mapping_api.set_item_planned_execution_node").length,
		0
	);

	// 2. Dirty BOQ Item Stage blocks both Change and Clear, and also blocks submit if dirtied while dialog is open.
	const hStage = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item Stage",
						name: "BOQ-STG-00010",
						project: "PROJ-1",
						assigned: { node: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						attribution: null,
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return { message: [{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" }] };
			}
		},
	});
	const stageFrm = hStage.makeFrm({
		doc: { name: "BOQ-STG-00010", boq_item: "BOQ-ITEM-001", execution_node: "EBN-0001", modified: "2026-11-24 10:00:00" },
		isNew: false,
		writePerm: true,
		dirty: true,
		fieldname: "execution_node",
	});
	hStage.handlers["BOQ Item Stage"].refresh(stageFrm);
	const stgChangeBtn = stageFrm._buttons.find((b) => b.label === "Change Execution Location");
	const stgClearBtn = stageFrm._buttons.find((b) => b.label === "Clear Execution Location");
	stgChangeBtn.action();
	stgClearBtn.action();
	assert.equal(hStage.dialogs.length, 0);
	assert.equal(hStage.msgprints.length, 2);

	// If opened clean and then dirtied before submitting Clear, submission is also blocked!
	stageFrm.setDirty(false);
	stgClearBtn.action();
	assert.equal(hStage.dialogs.length, 1);
	stageFrm.setDirty(true);
	hStage.dialogs[0].submit({ reason: "Clear location" });
	assert.equal(stageFrm._getReloaded(), 0);
	assert.equal(
		hStage.calls.filter((c) => c.method === "construction.api.execution_mapping_api.set_stage_execution_node").length,
		0
	);
});

test("Picker HTML boundary escaping: Select labels escape markup while preview keeps literal text", () => {
	const evilPath = 'Site / <img src=x onerror="window.__xss=1"> & <b>Tower "A"</b>';
	const expectedEscaped =
		"EBS-0099 — Site / &lt;img src=x onerror=&quot;window.__xss=1&quot;&gt; &amp; &lt;b&gt;Tower &quot;A&quot;&lt;/b&gt;";

	// 1. BOQ Item picker escapes Select option labels.
	const hItem = createHarness("construction/construction/doctype/boq_item/boq_item.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return { message: { doctype: "BOQ Item", name: "BOQ-ITEM-001", project: "PROJ-1", assigned: null } };
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return { message: [{ name: "EBN-0099", ebs_code: "EBS-0099", full_path: evilPath }] };
			}
		},
	});
	const itemFrm = hItem.makeFrm({
		doc: { name: "BOQ-ITEM-001", boq_header: "BOQ-H-1", planned_execution_node: "" },
		isNew: false,
		writePerm: true,
		fieldname: "planned_execution_node",
	});
	hItem.handlers["BOQ Item"].refresh(itemFrm);
	itemFrm._buttons.find((b) => b.label === "Set Planned Location").action();
	const itemSelectOpts = hItem.dialogs[0].opts.fields.find((f) => f.fieldname === "execution_node").options;
	assert.equal(itemSelectOpts[1].label, expectedEscaped);

	// 2. BOQ Item Stage picker escapes Select option labels AND preserves raw literal text in preview banner.
	const hStage = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_new_stage_default_preview") {
				return { message: { boq_item: "BOQ-ITEM-001", project: "PROJ-1", will_inherit: false, preview: null } };
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return { message: [{ name: "EBN-0099", ebs_code: "EBS-0099", full_path: evilPath }] };
			}
		},
	});
	const stageFrm = hStage.makeFrm({
		doc: { boq_item: "BOQ-ITEM-001", project: "PROJ-1", execution_node: "" },
		isNew: true,
		writePerm: true,
		fieldname: "execution_node",
	});
	hStage.handlers["BOQ Item Stage"].refresh(stageFrm);
	stageFrm._buttons.find((b) => b.label === "Select Execution Location").action();
	const stageSelectOpts = hStage.dialogs[0].opts.fields.find((f) => f.fieldname === "execution_node").options;
	assert.equal(stageSelectOpts[1].label, expectedEscaped);

	// Submitting override shows raw literal text in textContent preview (no double-escaping & no HTML elements).
	hStage.dialogs[0].submit({ execution_node: "EBN-0099" });
	assert.equal(stageFrm._container.querySelectorAll("img").length, 0);
	assert.ok(stageFrm._container.allText().includes(`EBS-0099 — ${evilPath}`));
	assert.ok(!stageFrm._container.allText().includes("&lt;img"));
});

test("New Stage override lifecycle: select -> Use Inherited Default without reload, and select -> switch BOQ Item resets override", async () => {
	const h = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_new_stage_default_preview") {
				if (opts.args.boq_item === "BOQ-ITEM-1") {
					return {
						message: {
							boq_item: "BOQ-ITEM-1",
							project: "PROJ-1",
							will_inherit: true,
							preview: { node: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						},
					};
				}
				return {
					message: {
						boq_item: "BOQ-ITEM-2",
						project: "PROJ-1",
						will_inherit: true,
						preview: { node: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" },
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return {
					message: [
						{ name: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" },
					],
				};
			}
		},
	});

	const frm = h.makeFrm({
		doc: { boq_item: "BOQ-ITEM-1", project: "PROJ-1", boq_header: "BOQ-H-1", boq_structure: "STR-1", execution_node: "" },
		isNew: true,
		writePerm: true,
		fieldname: "execution_node",
	});

	// Initial state: only Select Execution Location button, no Use Inherited Default.
	h.handlers["BOQ Item Stage"].refresh(frm);
	assert.deepEqual(
		frm._buttons.filter((b) => b.group === "Execution Location").map((b) => b.label),
		["Select Execution Location"]
	);

	// Step A: Select override -> Use Inherited Default appears IMMEDIATELY without reload!
	frm._buttons.find((b) => b.label === "Select Execution Location").action();
	h.dialogs.at(-1).submit({ execution_node: "EBN-0002" });
	assert.equal(frm.doc.execution_node, "EBN-0002");
	assert.deepEqual(
		frm._buttons.filter((b) => b.group === "Execution Location").map((b) => b.label),
		["Select Execution Location", "Use Inherited Default"]
	);

	// Click Use Inherited Default -> returns immediately to inherited preview and removes Use Inherited Default!
	frm._buttons.find((b) => b.label === "Use Inherited Default").action();
	assert.equal(frm.doc.execution_node, "");
	assert.match(frm._container.allText(), /Will inherit from BOQ Item on save: EBS-0001 — Site \/ Building A/);
	assert.deepEqual(
		frm._buttons.filter((b) => b.group === "Execution Location").map((b) => b.label),
		["Select Execution Location"]
	);

	// Step B: Select override again, then switch BOQ Item within the SAME project -> override resets and preview updates!
	frm._buttons.find((b) => b.label === "Select Execution Location").action();
	h.dialogs.at(-1).submit({ execution_node: "EBN-0001" });
	assert.equal(frm.doc.execution_node, "EBN-0001");
	assert.ok(frm._buttons.some((b) => b.label === "Use Inherited Default"));

	frm.doc.boq_item = "BOQ-ITEM-2";
	h.handlers["BOQ Item Stage"].boq_item(frm);
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(frm.doc.execution_node, "");
	assert.match(frm._container.allText(), /Will inherit from BOQ Item on save: EBS-0002 — Site \/ Building B/);
	assert.deepEqual(
		frm._buttons.filter((b) => b.group === "Execution Location").map((b) => b.label),
		["Select Execution Location"]
	);
});

test("Delayed mapping POST response does not reload or discard edits made after submission (Item & Stage change/clear)", () => {
	const pendingCallbacks = [];

	// 1. BOQ Item: delayed change & clear responses preserve post-submit edits and use freeze: true.
	const hItem = createHarness("construction/construction/doctype/boq_item/boq_item.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item",
						name: "BOQ-ITEM-001",
						project: "PROJ-1",
						assigned: { node: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						attribution: null,
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return { message: [{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" }] };
			}
			if (opts.method === "construction.api.execution_mapping_api.set_item_planned_execution_node") {
				pendingCallbacks.push(opts.callback);
				return undefined; // Delay response!
			}
		},
	});
	const itemFrm = hItem.makeFrm({
		doc: {
			name: "BOQ-ITEM-001",
			boq_header: "BOQ-H-1",
			planned_execution_node: "EBN-0001",
			description: "Initial",
			modified: "2026-11-24 10:00:00",
		},
		isNew: false,
		writePerm: true,
		dirty: false,
		fieldname: "planned_execution_node",
	});
	hItem.handlers["BOQ Item"].refresh(itemFrm);

	// Change Planned Location -> submit while clean -> user edits form during slow request -> response arrives.
	itemFrm._buttons.find((b) => b.label === "Change Planned Location").action();
	hItem.dialogs.at(-1).submit({ execution_node: "EBN-0002", reason: "Move to B" });
	assert.equal(hItem.calls.at(-1).freeze, true);
	itemFrm.doc.description = "Edited during slow item change";
	itemFrm.setDirty(true);
	pendingCallbacks.pop()({ message: { changed: true, action: "change" } });
	assert.equal(itemFrm._getReloaded(), 0);
	assert.equal(itemFrm.doc.description, "Edited during slow item change");
	assert.equal(hItem.alerts.at(-1).indicator, "orange");

	// Clear Planned Location -> submit while clean -> user edits form during slow request -> response arrives.
	itemFrm.setDirty(false);
	itemFrm._buttons.find((b) => b.label === "Clear Planned Location").action();
	hItem.dialogs.at(-1).submit({ reason: "Clear item default" });
	assert.equal(hItem.calls.at(-1).freeze, true);
	itemFrm.doc.description = "Edited during slow item clear";
	itemFrm.setDirty(true);
	pendingCallbacks.pop()({ message: { changed: true, action: "clear" } });
	assert.equal(itemFrm._getReloaded(), 0);
	assert.equal(itemFrm.doc.description, "Edited during slow item clear");
	assert.equal(hItem.alerts.at(-1).indicator, "orange");

	// 2. BOQ Item Stage: delayed change & clear responses preserve post-submit edits and use freeze: true.
	const hStage = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_mapping_display_context") {
				return {
					message: {
						doctype: "BOQ Item Stage",
						name: "BOQ-STG-00010",
						project: "PROJ-1",
						assigned: { node: "EBN-0001", ebs_code: "EBS-0001", full_path: "Site / Building A" },
						attribution: null,
					},
				};
			}
			if (opts.method === "construction.api.execution_mapping_api.get_eligible_execution_nodes") {
				return { message: [{ name: "EBN-0002", ebs_code: "EBS-0002", full_path: "Site / Building B" }] };
			}
			if (opts.method === "construction.api.execution_mapping_api.set_stage_execution_node") {
				pendingCallbacks.push(opts.callback);
				return undefined; // Delay response!
			}
		},
	});
	const stageFrm = hStage.makeFrm({
		doc: {
			name: "BOQ-STG-00010",
			boq_item: "BOQ-ITEM-001",
			execution_node: "EBN-0001",
			description: "Initial stage",
			modified: "2026-11-24 10:00:00",
		},
		isNew: false,
		writePerm: true,
		dirty: false,
		fieldname: "execution_node",
	});
	hStage.handlers["BOQ Item Stage"].refresh(stageFrm);

	stageFrm._buttons.find((b) => b.label === "Change Execution Location").action();
	hStage.dialogs.at(-1).submit({ execution_node: "EBN-0002", reason: "Move stage to B" });
	assert.equal(hStage.calls.at(-1).freeze, true);
	stageFrm.doc.description = "Edited during slow stage change";
	stageFrm.setDirty(true);
	pendingCallbacks.pop()({ message: { changed: true, action: "change", is_historical_assignment: false } });
	assert.equal(stageFrm._getReloaded(), 0);
	assert.equal(stageFrm.doc.description, "Edited during slow stage change");
	assert.equal(hStage.alerts.at(-1).indicator, "orange");

	stageFrm.setDirty(false);
	stageFrm._buttons.find((b) => b.label === "Clear Execution Location").action();
	hStage.dialogs.at(-1).submit({ reason: "Clear stage location" });
	assert.equal(hStage.calls.at(-1).freeze, true);
	stageFrm.doc.description = "Edited during slow stage clear";
	stageFrm.setDirty(true);
	pendingCallbacks.pop()({ message: { changed: true, action: "clear" } });
	assert.equal(stageFrm._getReloaded(), 0);
	assert.equal(stageFrm.doc.description, "Edited during slow stage clear");
	assert.equal(hStage.alerts.at(-1).indicator, "orange");
});

test("New Stage rapid BOQ Item A -> B switch ignores late out-of-order lookup response for A", async () => {
	const resolvers = Object.create(null);
	const h = createHarness("construction/construction/doctype/boq_item_stage/boq_item_stage.js", {
		roles: ["Construction Owner"],
		dbGetValue(_dt, itemName) {
			return new Promise((resolve) => {
				resolvers[itemName] = resolve;
			});
		},
		callResponder(opts) {
			if (opts.method === "construction.api.execution_mapping_api.get_new_stage_default_preview") {
				const isB = opts.args.boq_item === "BOQ-ITEM-B";
				return {
					message: {
						boq_item: opts.args.boq_item,
						project: "PROJ-1",
						will_inherit: true,
						preview: isB
							? { node: "EBN-B", ebs_code: "EBS-B", full_path: "Site / Building B" }
							: { node: "EBN-A", ebs_code: "EBS-A", full_path: "Site / Building A" },
					},
				};
			}
		},
	});

	const frm = h.makeFrm({
		doc: { project: "PROJ-1", boq_header: "", boq_structure: "", boq_item: "", execution_node: "" },
		isNew: true,
		writePerm: true,
		fieldname: "execution_node",
	});

	// Rapidly select Item A, then immediately switch to Item B before Item A's DB lookup returns.
	frm.doc.boq_item = "BOQ-ITEM-A";
	h.handlers["BOQ Item Stage"].boq_item(frm);

	frm.doc.boq_item = "BOQ-ITEM-B";
	h.handlers["BOQ Item Stage"].boq_item(frm);

	// Deliver responses in REVERSE order: Item B resolves first, then stale Item A resolves late!
	resolvers["BOQ-ITEM-B"]({ message: { boq_header: "BOQ-H-B", structure: "STR-B" } });
	await new Promise((resolve) => setImmediate(resolve));
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(frm.doc.boq_item, "BOQ-ITEM-B");
	assert.equal(frm.doc.boq_header, "BOQ-H-B");
	assert.equal(frm.doc.boq_structure, "STR-B");
	assert.match(frm._container.allText(), /EBS-B — Site \/ Building B/);

	// Now deliver stale Item A response late — must be ignored completely!
	resolvers["BOQ-ITEM-A"]({ message: { boq_header: "BOQ-H-A", structure: "STR-A" } });
	await new Promise((resolve) => setImmediate(resolve));
	await new Promise((resolve) => setImmediate(resolve));

	assert.equal(frm.doc.boq_item, "BOQ-ITEM-B");
	assert.equal(frm.doc.boq_header, "BOQ-H-B");
	assert.equal(frm.doc.boq_structure, "STR-B");
	assert.match(frm._container.allText(), /EBS-B — Site \/ Building B/);
	assert.ok(!frm._container.allText().includes("Building A"));
});
