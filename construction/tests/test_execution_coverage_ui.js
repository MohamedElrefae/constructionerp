const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");

class MiniClassList {
	constructor(el) {
		this.el = el;
	}
	_set() {
		return new Set(
			String(this.el.className || "")
				.split(/\s+/)
				.filter(Boolean)
		);
	}
	_save(set) {
		this.el.className = Array.from(set).join(" ");
	}
	add(...cls) {
		const s = this._set();
		cls.forEach((c) => s.add(c));
		this._save(s);
	}
	remove(...cls) {
		const s = this._set();
		cls.forEach((c) => s.delete(c));
		this._save(s);
	}
	contains(c) {
		return this._set().has(c);
	}
}

class MiniEl {
	constructor(tagName) {
		this.tagName = tagName.toUpperCase();
		this.id = "";
		this.className = "";
		this.classList = new MiniClassList(this);
		this.attributes = Object.create(null);
		this.style = {};
		this.children = [];
		this.parentNode = null;
		this.listeners = Object.create(null);
		this.value = "";
		this.disabled = false;
		this.tabIndex = -1;
		this.focused = false;
		this._text = "";
	}
	set textContent(v) {
		this._text = String(v == null ? "" : v);
		this.children = [];
	}
	get textContent() {
		if (!this.children.length) return this._text;
		return this.children.map((c) => c.textContent).join("");
	}
	setAttribute(k, v) {
		this.attributes[k] = String(v);
		if (k === "id") this.id = String(v);
		if (k === "class") this.className = String(v);
		if (k === "tabindex") this.tabIndex = Number(v);
	}
	getAttribute(k) {
		if (k === "id") return this.id || null;
		if (k === "class") return this.className || null;
		return Object.prototype.hasOwnProperty.call(this.attributes, k)
			? this.attributes[k]
			: null;
	}
	appendChild(child) {
		child.parentNode = this;
		this.children.push(child);
		return child;
	}
	replaceChildren(...nodes) {
		this.children = [];
		this._text = "";
		nodes.forEach((n) => this.appendChild(n));
	}
	addEventListener(type, fn) {
		if (!this.listeners[type]) this.listeners[type] = [];
		this.listeners[type].push(fn);
	}
	dispatch(type, eventObj) {
		const ev = Object.assign(
			{ key: "", preventDefault() {}, stopPropagation() {} },
			eventObj || {}
		);
		(this.listeners[type] || []).forEach((fn) => fn(ev));
	}
	click() {
		if (!this.disabled) this.dispatch("click");
	}
	focus() {
		this.focused = true;
	}
	scrollIntoView() {}
	findAll(pred, out = []) {
		if (pred(this)) out.push(this);
		this.children.forEach((c) => c.findAll(pred, out));
		return out;
	}
	findOne(pred) {
		return this.findAll(pred)[0] || null;
	}
	allText() {
		const parts = [];
		if (this._text) parts.push(this._text);
		this.children.forEach((c) => parts.push(c.allText()));
		return parts.filter(Boolean).join(" ");
	}
}

function createCoverageHarness({
	scopedProject = "PROJ-1",
	routeOptions = null,
	searchQuery = "",
	isRtl = false,
	callResponder,
} = {}) {
	const rootEl = new MiniEl("div");
	const innerButtons = [];
	const alerts = [];
	const openedUrls = [];
	const routes = [];
	const docHandlers = Object.create(null);
	const wrapperHandlers = Object.create(null);
	const calls = [];
	let replacedUrl = null;

	const pageStub = {
		main: [rootEl],
		add_inner_button(label, fn, group) {
			innerButtons.push({ label, fn, group: group || null });
		},
	};

	const documentStub = {
		createElement(tag) {
			return new MiniEl(tag);
		},
	};

	function $(target) {
		const store = target === documentStub ? docHandlers : wrapperHandlers;
		return {
			off(ev) {
				String(ev || "")
					.split(/\s+/)
					.forEach((e) => {
						delete store[e];
					});
				return this;
			},
			on(ev, fn) {
				String(ev || "")
					.split(/\s+/)
					.forEach((e) => {
						store[e] = fn;
					});
				return this;
			},
		};
	}

	const win = {
		scopeContext: {
			enabled: true,
			supportsSaveConfirmation: true,
			_savePending: false,
			_saveQueued: false,
			_saveFailed: false,
			_conflict: null,
			_project: scopedProject,
			getValidatedCurrentScope() {
				return { project: this._project };
			},
		},
		location: { pathname: "/app/execution-coverage", search: searchQuery },
		history: {
			replaceState(_s, _t, url) {
				replacedUrl = url;
			},
		},
		open(url) {
			openedUrls.push(url);
		},
	};

	const frappeStub = {
		pages: { "execution-coverage": {} },
		route_options: routeOptions,
		ui: {
			make_app_page() {
				return pageStub;
			},
		},
		dom: { set_style() {} },
		utils: {
			is_rtl() {
				return isRtl;
			},
		},
		show_alert(opts) {
			alerts.push(opts);
		},
		set_route(...args) {
			routes.push(args);
		},
		call(opts) {
			calls.push(opts);
			if (callResponder) {
				const out = callResponder(opts);
				if (out && out._defer) {
					return out;
				}
				if (out && out._error) {
					if (opts.error) opts.error(out._error);
					return;
				}
				if (out && opts.callback) {
					opts.callback(out);
				}
			}
		},
	};

	function __(text, args) {
		let s = String(text);
		if (Array.isArray(args)) {
			args.forEach((val, idx) => {
				s = s.replace(`{${idx}}`, String(val));
			});
		}
		return s;
	}

	const context = vm.createContext({
		window: win,
		document: documentStub,
		URLSearchParams,
		frappe: frappeStub,
		$: $,
		__: __,
		setTimeout: (fn) => {
			fn();
			return 1;
		},
		clearTimeout: () => {},
		console,
	});

	const scriptPath = path.join(
		root,
		"construction/construction/page/execution_coverage/execution_coverage.js"
	);
	vm.runInContext(fs.readFileSync(scriptPath, "utf8"), context, { filename: scriptPath });
	frappeStub.pages["execution-coverage"].on_page_load({});

	return {
		rootEl,
		innerButtons,
		alerts,
		openedUrls,
		routes,
		calls,
		win,
		frappe: frappeStub,
		docHandlers,
		wrapperHandlers,
		getReplacedUrl: () => replacedUrl,
	};
}

function sampleResponse(overrides = {}) {
	return {
		message: Object.assign(
			{
				ok: true,
				limit_exceeded: false,
				project: "PROJ-1",
				view_mode: "stages",
				filter_conflict: null,
				disclaimer: "Mapping completeness reflects Stage-to-location link counts only.",
				headers: [
					{
						name: "BOQ-H1",
						title: "Contract BOQ",
						boq_type: "Contract",
						status: "Locked",
					},
					{ name: "BOQ-H2", title: "Tender BOQ", boq_type: "Tender", status: "Draft" },
				],
				summary: {
					total_stages: 3,
					healthy_linked: 1,
					unlinked: 1,
					link_issues: 1,
					disabled_links: 1,
					integrity_issues: 0,
					coverage_pct: 33.3,
					coverage_pct_display: "33.3%",
				},
				population_summary: {
					total_items: 3,
					total_stages: 3,
					items_with_stages: 2,
					items_without_stages: 1,
					items_with_matching_stages: 2,
					items_hidden_by_stage_filters: 0,
					partial_visibility: false,
					no_stages_label: "No Stages",
				},
				rows: [
					{
						name: "BOQ-STG-00001",
						stage_code: "S-01",
						stage_name: "<img src=x onerror=alert(1)> Pour",
						stage_status: "In Progress",
						mapping_state: "healthy_linked",
						mapping_state_label: "Healthy Linked",
						issue_code: null,
						issue_label: "",
						execution_node: "EBN-0002",
						node_display: "EBS-0002 — Tower A / Floor 1",
						boq_item: "BOQI-1",
						wbs_code: "1.1",
						item_title: "Concrete Footings",
						boq_header: "BOQ-H1",
						header_title: "Contract BOQ",
						header_type: "Contract",
						header_status: "Locked",
						planned_qty: 40.5,
						uom: "m3",
						item_planned_node_display: "EBS-0002 — Tower A / Floor 1",
					},
				],
				pagination: {
					page: 1,
					page_size: 50,
					total_rows: 1,
					total_pages: 1,
					has_prev: false,
					has_next: false,
				},
			},
			overrides
		),
	};
}

test("Execution Coverage renders KPIs, disabled/integrity breakdown, accessible responsive table, and escapes XSS literally", () => {
	const h = createCoverageHarness({
		callResponder(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return {
					message: {
						nodes: [
							{
								name: "EBN-0001",
								ebs_code: "EBS-0001",
								title: "Tower A",
								depth: 1,
								disabled: 0,
							},
							{
								name: "EBN-0002",
								ebs_code: "EBS-0002",
								title: "Floor 1",
								depth: 2,
								disabled: 0,
							},
						],
					},
				};
			}
			if (opts.method === "construction.api.execution_coverage_api.get_execution_coverage") {
				return sampleResponse();
			}
		},
	});

	const fullText = h.rootEl.allText();
	assert.match(fullText, /33\.3%/);
	assert.match(fullText, /Disabled Links: 1/);
	assert.match(fullText, /Integrity Issues: 0/);
	assert.match(fullText, /Mapping completeness reflects Stage-to-location link counts only/);

	// Responsive table ARIA & semantic structure
	const region = h.rootEl.findOne((el) => el.getAttribute("data-role") === "table-wrap");
	assert.equal(region.getAttribute("role"), "region");
	assert.equal(region.getAttribute("tabindex"), "0");
	assert.equal(region.getAttribute("aria-labelledby"), "ct-cov-table-caption");
	const caption = region.findOne((el) => el.tagName === "CAPTION");
	assert.equal(caption.id, "ct-cov-table-caption");
	const colHeaders = region.findAll(
		(el) => el.tagName === "TH" && el.getAttribute("scope") === "col"
	);
	assert.ok(colHeaders.length >= 7);
	const rowHeaders = region.findAll(
		(el) => el.tagName === "TH" && el.getAttribute("scope") === "row"
	);
	assert.equal(rowHeaders.length, 1);

	// XSS probe stays literal text, zero <img> element created
	assert.equal(region.findAll((el) => el.tagName === "IMG").length, 0);
	assert.match(rowHeaders[0].allText(), /<img src=x onerror=alert\(1\)> Pour/);
});

test("Contradictory filter conflict renders alert banner and Clear Location Filter resolves it", () => {
	let phase = 0;
	const h = createCoverageHarness({
		routeOptions: { project: "PROJ-1", execution_node: "EBN-0002", mapping_state: "unlinked" },
		callResponder(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return {
					message: {
						nodes: [
							{ name: "EBN-0002", ebs_code: "EBS-0002", title: "Floor 1", depth: 1 },
						],
					},
				};
			}
			if (opts.method === "construction.api.execution_coverage_api.get_execution_coverage") {
				phase += 1;
				if (opts.args.execution_node && opts.args.mapping_state === "unlinked") {
					return sampleResponse({
						filter_conflict: {
							code: "node_with_unlinked",
							message: "Contradictory location + unmapped filter.",
						},
						summary: {
							total_stages: 0,
							healthy_linked: 0,
							unlinked: 0,
							link_issues: 0,
							disabled_links: 0,
							integrity_issues: 0,
							coverage_pct: null,
							coverage_pct_display: "N/A",
						},
						rows: [],
						pagination: {
							page: 1,
							page_size: 50,
							total_rows: 0,
							total_pages: 1,
							has_prev: false,
							has_next: false,
						},
					});
				}
				return sampleResponse();
			}
		},
	});

	const banner = h.rootEl.findOne((el) => el.getAttribute("data-role") === "filter-conflict");
	assert.equal(banner.getAttribute("role"), "alert");
	assert.ok(!banner.classList.contains("d-none"));
	assert.match(banner.allText(), /Contradictory location \+ unmapped filter/);

	// Click Clear Location Filter -> reloads without execution_node and clears banner
	const clearBtn = h.rootEl.findOne(
		(el) => el.getAttribute("data-action") === "clear-location-filter"
	);
	clearBtn.click();
	const lastCovCall = h.calls
		.filter(
			(c) => c.method === "construction.api.execution_coverage_api.get_execution_coverage"
		)
		.pop();
	assert.equal(lastCovCall.args.execution_node, undefined);
	assert.equal(lastCovCall.args.mapping_state, "unlinked");
	assert.ok(banner.classList.contains("d-none"));
});

test("Tabs use selection-by-activation, honor partial-visibility No visible Stages label, and support Item->Stages drilldown", () => {
	const h = createCoverageHarness({
		callResponder(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return { message: { nodes: [] } };
			}
			if (opts.method === "construction.api.execution_coverage_api.get_execution_coverage") {
				if (opts.args.view_mode === "items") {
					return sampleResponse({
						view_mode: "items",
						population_summary: {
							total_items: 2,
							total_stages: 1,
							items_with_stages: 1,
							items_without_stages: 1,
							items_with_matching_stages: 0,
							items_hidden_by_stage_filters: 1,
							partial_visibility: true,
							no_stages_label: "No visible Stages",
						},
						rows: [
							{
								name: "BOQI-HIDDEN",
								boq_header: "BOQ-H1",
								header_title: "Contract BOQ",
								header_type: "Contract",
								header_status: "Locked",
								wbs_code: "1.2",
								item_title: "Rebar",
								filtered_group: "filtered_out",
								filtered_group_label: "Zero Matching Stages",
								total_item_stages: 2,
								matching_stages: 0,
								healthy_linked: 0,
								unlinked: 0,
								link_issues: 0,
								item_quantity: 500,
								stage_planned_qty_sum: 0,
								uom: "kg",
								planned_node_display: "",
							},
						],
					});
				}
				return sampleResponse({
					population_summary: {
						total_items: 2,
						total_stages: 1,
						items_with_stages: 1,
						items_without_stages: 1,
						items_with_matching_stages: 1,
						items_hidden_by_stage_filters: 0,
						partial_visibility: true,
						no_stages_label: "No visible Stages",
					},
				});
			}
		},
	});

	const tabs = h.rootEl.findAll((el) => el.getAttribute("role") === "tab");
	assert.equal(tabs.length, 3);
	// No aria-controls per modern tabs guidance
	tabs.forEach((t) => assert.equal(t.getAttribute("aria-controls"), null));

	// ArrowRight moves focus to Items Summary WITHOUT firing a new RPC (selection by activation!)
	const callsBeforeArrow = h.calls.length;
	tabs[0].dispatch("keydown", { key: "ArrowRight" });
	assert.equal(tabs[1].focused, true);
	assert.equal(h.calls.length, callsBeforeArrow);

	// Activating Items Summary tab loads view_mode="items" and shows "No visible Stages" + "Zero Matching Stages"
	tabs[1].click();
	assert.equal(tabs[1].getAttribute("aria-selected"), "true");
	assert.equal(tabs[0].getAttribute("aria-selected"), "false");
	assert.match(tabs[2].allText(), /No visible Stages/);
	assert.match(h.rootEl.allText(), /Zero Matching Stages/);

	// Clicking View Stages on BOQI-HIDDEN drills down into Stages tab with boq_item filter
	const viewStagesBtn = h.rootEl.findOne(
		(el) => el.tagName === "BUTTON" && el.textContent === "View Stages"
	);
	assert.ok(viewStagesBtn);
	viewStagesBtn.click();
	const lastCall = h.calls
		.filter(
			(c) => c.method === "construction.api.execution_coverage_api.get_execution_coverage"
		)
		.pop();
	assert.equal(lastCall.args.view_mode, "stages");
	assert.equal(lastCall.args.boq_item, "BOQI-HIDDEN");
	assert.equal(tabs[0].getAttribute("aria-selected"), "true");
});

test("Export actions build authorized CSV/XLSX URLs and block export when limit_exceeded is true", () => {
	let exceed = false;
	const h = createCoverageHarness({
		routeOptions: { project: "PROJ-1", execution_node: "EBN-0002" },
		callResponder(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return { message: { nodes: [] } };
			}
			if (opts.method === "construction.api.execution_coverage_api.get_execution_coverage") {
				if (exceed) {
					return {
						message: {
							ok: false,
							limit_exceeded: true,
							limit_type: "stages",
							limit: 3000,
							message: "Too many records match. Narrow filters.",
							headers: [],
						},
					};
				}
				return sampleResponse();
			}
		},
	});

	const csvBtn = h.innerButtons.find((b) => b.label === "Download CSV");
	const xlsxBtn = h.innerButtons.find((b) => b.label === "Download Excel");
	csvBtn.fn();
	xlsxBtn.fn();
	assert.equal(h.openedUrls.length, 2);
	assert.match(
		h.openedUrls[0],
		/export_execution_coverage\?.*project=PROJ-1.*execution_node=EBN-0002.*export_format=csv/
	);
	assert.match(
		h.openedUrls[1],
		/export_execution_coverage\?.*project=PROJ-1.*execution_node=EBN-0002.*export_format=xlsx/
	);

	// When limit_exceeded triggers, export refuses cleanly without opening a download URL
	exceed = true;
	const stateSel = h.rootEl.findOne((el) => el.getAttribute("data-filter") === "mapping_state");
	stateSel.value = "healthy_linked";
	stateSel.dispatch("change");
	csvBtn.fn();
	assert.equal(h.openedUrls.length, 2);
	assert.ok(h.alerts.some((a) => /Narrow filters before exporting/.test(a.message)));
});

test("Stale out-of-order coverage response is ignored after a newer filter change", () => {
	const pending = [];
	const h = createCoverageHarness({
		callResponder(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return { message: { nodes: [] } };
			}
			if (opts.method === "construction.api.execution_coverage_api.get_execution_coverage") {
				pending.push(opts);
				return { _defer: true };
			}
		},
	});

	// Trigger a second request before the first finishes
	const stateSel = h.rootEl.findOne((el) => el.getAttribute("data-filter") === "mapping_state");
	stateSel.value = "unlinked";
	stateSel.dispatch("change");
	assert.equal(pending.length, 2);

	// Deliver newer request (#2) FIRST, then older stale request (#1) SECOND
	pending[1].callback(
		sampleResponse({
			summary: {
				total_stages: 1,
				healthy_linked: 0,
				unlinked: 1,
				link_issues: 0,
				disabled_links: 0,
				integrity_issues: 0,
				coverage_pct: 0.0,
				coverage_pct_display: "0.0%",
			},
		})
	);
	assert.match(h.rootEl.allText(), /0\.0%/);

	pending[0].callback(
		sampleResponse({
			summary: {
				total_stages: 99,
				healthy_linked: 99,
				unlinked: 0,
				link_issues: 0,
				disabled_links: 0,
				integrity_issues: 0,
				coverage_pct: 100.0,
				coverage_pct_display: "100.0%",
			},
		})
	);
	// Must still show 0.0%, NOT stale 100.0%!
	assert.match(h.rootEl.allText(), /0\.0%/);
	assert.ok(!h.rootEl.allText().includes("100.0%"));
});

test("Execution Breakdown View Coverage action routes to execution-coverage with project and execution_node", () => {
	let treeHtml = "";
	let clickHandler = null;
	const routes = [];
	const frappeStub = {
		pages: { "execution-breakdown": {} },
		route_options: null,
		ui: {
			make_app_page() {
				return { main: [{}] };
			},
		},
		dom: { set_style() {} },
		utils: {
			escape_html: (s) => String(s),
			is_rtl: () => false,
			icon: () => "",
		},
		set_route(...args) {
			routes.push(args);
		},
		call(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return Promise.resolve({
					message: {
						project: "PROJ-9",
						company: "Comp",
						actions: {},
						nodes: [
							{
								name: "EBN-0099",
								title: "Floor 3",
								ebs_code: "EBS-0099",
								parent_node: null,
								is_group: 0,
								disabled: 0,
							},
						],
					},
				});
			}
			return Promise.resolve({ message: {} });
		},
	};

	function makeJqNode(role) {
		const node = {
			0: { contains: () => false },
			length: 1,
			append(v) {
				if (role === "tree" && typeof v === "string") treeHtml += v;
				return node;
			},
			find(sel) {
				if (sel === '[data-role="tree"]') return treeNode;
				return makeJqNode(sel);
			},
			removeClass() {
				return node;
			},
			addClass() {
				return node;
			},
			toggleClass() {
				return node;
			},
			text() {
				return node;
			},
			empty() {
				if (role === "tree") treeHtml = "";
				return node;
			},
			html(v) {
				if (role === "tree") treeHtml = v;
				return node;
			},
			attr() {
				return node;
			},
			trigger() {
				return node;
			},
			off() {
				return node;
			},
			on(ev, sel, fn) {
				if (ev === "click" && sel === "[data-action]") {
					clickHandler = fn;
				}
				return node;
			},
		};
		return node;
	}
	const treeNode = makeJqNode("tree");
	const rootNode = makeJqNode("root");
	const $ = (arg) => {
		if (arg && typeof arg === "object" && arg._isBtn) {
			return { attr: (k) => arg[k] };
		}
		return rootNode;
	};
	const win = {
		scopeContext: {
			enabled: true,
			supportsSaveConfirmation: true,
			getValidatedCurrentScope: () => ({ project: "PROJ-9" }),
		},
	};
	const ctx = vm.createContext({
		window: win,
		document: { activeElement: null },
		frappe: frappeStub,
		$: $,
		__: (x) => x,
		console,
	});
	const treeScript = path.join(
		root,
		"construction/construction/page/execution_breakdown/execution_breakdown.js"
	);
	vm.runInContext(fs.readFileSync(treeScript, "utf8"), ctx, { filename: treeScript });
	frappeStub.pages["execution-breakdown"].on_page_load({});

	return new Promise((resolve) => setTimeout(resolve, 10)).then(() => {
		assert.match(treeHtml, /data-action="view-coverage"/);
		assert.match(treeHtml, /View Coverage/);
		assert.ok(clickHandler);
		clickHandler.call({
			_isBtn: true,
			"data-action": "view-coverage",
			"data-name": "EBN-0099",
		});
		assert.deepEqual(
			{
				project: frappeStub.route_options.project,
				execution_node: frappeStub.route_options.execution_node,
			},
			{
				project: "PROJ-9",
				execution_node: "EBN-0099",
			}
		);
		assert.deepEqual(
			routes.map((r) => Array.from(r)),
			[["execution-coverage"]]
		);
	});
});

test("BOQ Structure filter selector scopes to readable structures, filters descendants, and propagates to CSV and XLSX exports", () => {
	const h = createCoverageHarness({
		callResponder(opts) {
			if (opts.method === "construction.api.execution_tree_api.get_tree") {
				return { message: { nodes: [] } };
			}
			if (opts.method === "construction.api.execution_coverage_api.get_execution_coverage") {
				return sampleResponse({
					structures: [
						{
							name: "STR-GRP-1",
							title: "Civil Works",
							wbs_code: "1",
							boq_header: "BOQ-H1",
							header_title: "Contract BOQ",
							is_group: true,
							depth: 1,
						},
						{
							name: "STR-LEAF-1",
							title: "Concrete Footings",
							wbs_code: "1.1",
							boq_header: "BOQ-H1",
							header_title: "Contract BOQ",
							is_group: false,
							depth: 2,
						},
					],
				});
			}
		},
	});

	const structSel = h.rootEl.findOne((el) => el.getAttribute("data-filter") === "boq_structure");
	assert.ok(structSel, "BOQ Structure select control must exist in filter bar");
	assert.equal(structSel.children.length, 3); // All BOQ Structures + STR-GRP-1 + STR-LEAF-1
	assert.match(structSel.children[1].textContent, /1 — Civil Works \[Group\]/);

	// Select the group Structure -> triggers reload with boq_structure="STR-GRP-1"
	structSel.value = "STR-GRP-1";
	structSel.dispatch("change");
	const lastCovCall = h.calls
		.filter(
			(c) => c.method === "construction.api.execution_coverage_api.get_execution_coverage"
		)
		.pop();
	assert.equal(lastCovCall.args.boq_structure, "STR-GRP-1");

	// Chip reflects selected structure
	const chips = h.rootEl.findOne((el) => el.getAttribute("data-role") === "chips");
	assert.match(chips.allText(), /1 — Civil Works/);

	// Both CSV and XLSX export URLs carry boq_structure=STR-GRP-1
	h.innerButtons.find((b) => b.label === "Download CSV").fn();
	h.innerButtons.find((b) => b.label === "Download Excel").fn();
	assert.equal(h.openedUrls.length, 2);
	assert.match(h.openedUrls[0], /boq_structure=STR-GRP-1.*export_format=csv/);
	assert.match(h.openedUrls[1], /boq_structure=STR-GRP-1.*export_format=xlsx/);
});
