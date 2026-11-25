frappe.pages["execution-coverage"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Execution Coverage"),
		single_column: true,
	});

	const VALID_VIEW_MODES = ["stages", "items", "no_stages"];
	const VALID_MAPPING_STATES = ["all", "healthy_linked", "unlinked", "link_issues"];
	const VALID_STAGE_STATUSES = [
		"Not Started",
		"In Progress",
		"Completed",
		"Certified",
		"On Hold",
	];
	const PAGE_SIZE_DEFAULT = 50;

	const state = {
		project: "",
		boq_header: "",
		boq_structure: "",
		boq_item: "",
		execution_node: "",
		mapping_state: "all",
		stage_status: "",
		search: "",
		view_mode: "stages",
		page: 1,
		page_size: PAGE_SIZE_DEFAULT,
		generation: 0,
		tree_generation: 0,
		tree_project: "",
		tree_nodes: [],
		headers: [],
		structures: [],
		last_response: null,
		search_timer: null,
	};

	if (frappe.dom && typeof frappe.dom.set_style === "function") {
		frappe.dom.set_style(
			[
				".ct-exec-coverage { padding-block: 12px 24px; }",
				".ct-cov-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; align-items: end; padding: 12px; border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; background: var(--card-bg, #ffffff); margin-block-end: 12px; }",
				".ct-cov-field { display: flex; flex-direction: column; gap: 4px; min-inline-size: 0; }",
				".ct-cov-field label { font-size: 11.5px; font-weight: 600; color: var(--text-muted, #64748b); margin: 0; }",
				".ct-cov-field select.form-control { block-size: 34px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; appearance: auto; }",
				".ct-cov-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-block-end: 10px; }",
				".ct-cov-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 12px; background: var(--bg-blue, rgba(37, 99, 235, 0.12)); color: var(--text-on-blue, #1d4ed8); border: 1px solid rgba(37, 99, 235, 0.25); }",
				".ct-cov-chip button { border: 0; background: transparent; color: inherit; cursor: pointer; font-weight: 700; padding: 0 2px; line-height: 1; }",
				".ct-cov-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-block-end: 10px; }",
				".ct-cov-kpi { padding: 10px 12px; border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; background: var(--card-bg, #ffffff); text-align: start; }",
				".ct-cov-kpi-label { font-size: 11.5px; color: var(--text-muted, #64748b); margin-block-end: 4px; }",
				".ct-cov-kpi-value { font-size: 20px; font-weight: 700; line-height: 1.2; }",
				".ct-cov-kpi-sub { font-size: 11px; color: var(--text-muted, #64748b); margin-block-start: 4px; }",
				".ct-cov-disclaimer { font-size: 12px; color: var(--text-muted, #64748b); padding: 8px 12px; border-inline-start: 3px solid var(--border-color, #94a3b8); background: var(--subtle-fg, rgba(148, 163, 184, 0.08)); border-radius: 4px; margin-block-end: 12px; text-align: start; }",
				".ct-cov-tablist { display: flex; overflow-x: auto; gap: 4px; border-block-end: 1px solid var(--border-color, #d1d8dd); margin-block-end: 12px; }",
				".ct-cov-tab { position: relative; flex: none; border: 0; background: transparent; padding: 8px 14px; font-size: 13px; color: var(--text-muted, #64748b); cursor: pointer; white-space: nowrap; }",
				'.ct-cov-tab[aria-selected="true"] { color: var(--text-color, #111827); }',
				'.ct-cov-tab[aria-selected="true"]::after { content: ""; position: absolute; inset-inline: 0; inset-block-end: 0; border-block-end: 3px solid var(--primary, #2563eb); }',
				".ct-cov-tab-count { display: inline-block; margin-inline-start: 6px; padding: 1px 6px; border-radius: 999px; font-size: 11px; background: var(--subtle-fg, rgba(148, 163, 184, 0.16)); }",
				".ct-cov-table-wrap { overflow: auto; max-inline-size: 100%; max-block-size: min(560px, 72vh); container-type: inline-size; border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; background: var(--card-bg, #ffffff); }",
				".ct-cov-table { inline-size: 100%; border-collapse: separate; border-spacing: 0; margin: 0; font-size: 12.5px; }",
				".ct-cov-table caption { caption-side: top; font-weight: 600; padding: 8px 12px; text-align: start; color: var(--text-color, #111827); border-block-end: 1px solid var(--border-color, #d1d8dd); }",
				".ct-cov-table thead { position: sticky; inset-block-start: 0; z-index: 2; background: var(--subtle-fg, #f8fafc); }",
				".ct-cov-table th, .ct-cov-table td { padding: 8px 10px; border-block-end: 1px solid var(--border-color, #e2e8f0); text-align: start; vertical-align: top; }",
				".ct-cov-table thead th { white-space: nowrap; font-weight: 600; }",
				".ct-cov-table tbody th { position: sticky; inset-inline-start: 0; z-index: 1; background: var(--card-bg, #ffffff); font-weight: 600; }",
				".ct-cov-num { text-align: end; font-variant-numeric: tabular-nums; white-space: nowrap; }",
				".ct-cov-badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }",
				".ct-cov-badge-green { background: rgba(22, 163, 74, 0.14); color: #15803d; }",
				".ct-cov-badge-gray { background: rgba(100, 116, 139, 0.16); color: #475569; }",
				".ct-cov-badge-orange { background: rgba(245, 158, 11, 0.16); color: #92400e; }",
				".ct-cov-badge-red { background: rgba(220, 38, 38, 0.14); color: #b91c1c; }",
				".ct-cov-badge-blue { background: rgba(37, 99, 235, 0.14); color: #1d4ed8; }",
				".ct-cov-link-btn { border: 0; background: transparent; padding: 0; color: var(--primary, #2563eb); text-align: start; cursor: pointer; text-decoration: underline; }",
				".ct-cov-pagination { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-block-start: 10px; font-size: 12.5px; }",
				"@container (width < 600px) {",
				"  .ct-cov-table, .ct-cov-table thead, .ct-cov-table tbody, .ct-cov-table tr, .ct-cov-table th, .ct-cov-table td { display: block; }",
				"  .ct-cov-table thead { display: none; }",
				"  .ct-cov-table tr { margin-block-end: 10px; border: 1px solid var(--border-color, #d1d8dd); border-radius: 6px; }",
				"  .ct-cov-table tbody th { position: sticky; inset-block-start: 0; z-index: 2; background: var(--subtle-fg, #f1f5f9); }",
				"  .ct-cov-table td { display: flex; justify-content: space-between; gap: 8px; }",
				'  .ct-cov-table td::before { content: attr(data-label) ": "; font-weight: 600; color: var(--text-muted, #64748b); }',
				"}",
			].join("\n"),
			"execution-coverage-page-style"
		);
	}

	const rootEl = page.main && page.main[0] ? page.main[0] : document.createElement("div");
	const container = document.createElement("div");
	container.className = "ct-exec-coverage";

	// Alert / status banner
	const statusBanner = document.createElement("div");
	statusBanner.className = "alert alert-info d-none";
	statusBanner.setAttribute("data-role", "status");
	statusBanner.setAttribute("role", "status");
	container.appendChild(statusBanner);

	// Contradictory filter conflict alert (execution_node + unlinked)
	const conflictBanner = document.createElement("div");
	conflictBanner.className = "alert alert-warning d-none";
	conflictBanner.setAttribute("data-role", "filter-conflict");
	conflictBanner.setAttribute("role", "alert");
	const conflictText = document.createElement("div");
	conflictText.setAttribute("data-role", "conflict-text");
	conflictText.style.marginBlockEnd = "8px";
	conflictBanner.appendChild(conflictText);
	const conflictActions = document.createElement("div");
	conflictActions.style.display = "flex";
	conflictActions.style.flexWrap = "wrap";
	conflictActions.style.gap = "8px";
	const clearLocBtn = document.createElement("button");
	clearLocBtn.type = "button";
	clearLocBtn.className = "btn btn-default btn-sm";
	clearLocBtn.setAttribute("data-action", "clear-location-filter");
	clearLocBtn.textContent = __("Clear Location Filter");
	const showAllStatesBtn = document.createElement("button");
	showAllStatesBtn.type = "button";
	showAllStatesBtn.className = "btn btn-primary btn-sm";
	showAllStatesBtn.setAttribute("data-action", "show-all-mapping-states");
	showAllStatesBtn.textContent = __("Show All Mapping Statuses");
	conflictActions.appendChild(clearLocBtn);
	conflictActions.appendChild(showAllStatesBtn);
	conflictBanner.appendChild(conflictActions);
	container.appendChild(conflictBanner);

	// Filter bar
	const filterBar = document.createElement("div");
	filterBar.className = "ct-cov-filters";
	filterBar.setAttribute("data-role", "filters");

	function makeFilterSelect(id, labelText, name) {
		const wrap = document.createElement("div");
		wrap.className = "ct-cov-field";
		const lbl = document.createElement("label");
		lbl.setAttribute("for", id);
		lbl.textContent = labelText;
		const sel = document.createElement("select");
		sel.id = id;
		sel.className = "form-control input-sm";
		sel.setAttribute("data-filter", name);
		wrap.appendChild(lbl);
		wrap.appendChild(sel);
		filterBar.appendChild(wrap);
		return sel;
	}

	const headerSelect = makeFilterSelect("ct-cov-boq-header", __("BOQ Header"), "boq_header");
	const structureSelect = makeFilterSelect(
		"ct-cov-boq-structure",
		__("BOQ Structure"),
		"boq_structure"
	);
	const nodeSelect = makeFilterSelect(
		"ct-cov-exec-node",
		__("Execution Location"),
		"execution_node"
	);
	const stateSelect = makeFilterSelect(
		"ct-cov-mapping-state",
		__("Mapping Status"),
		"mapping_state"
	);
	const statusSelect = makeFilterSelect(
		"ct-cov-stage-status",
		__("Stage Status"),
		"stage_status"
	);

	const searchWrap = document.createElement("div");
	searchWrap.className = "ct-cov-field";
	const searchLabel = document.createElement("label");
	searchLabel.setAttribute("for", "ct-cov-search");
	searchLabel.textContent = __("Search");
	const searchInput = document.createElement("input");
	searchInput.id = "ct-cov-search";
	searchInput.type = "search";
	searchInput.className = "form-control input-sm";
	searchInput.setAttribute("data-filter", "search");
	searchInput.placeholder = __("Stage, BOQ Item, WBS, or Location...");
	searchWrap.appendChild(searchLabel);
	searchWrap.appendChild(searchInput);
	filterBar.appendChild(searchWrap);

	container.appendChild(filterBar);

	// Populate static select options
	function setSelectOptions(selectEl, items, selectedValue) {
		selectEl.replaceChildren();
		items.forEach((item) => {
			const opt = document.createElement("option");
			opt.value = item.value;
			opt.textContent = item.label;
			if (item.value === (selectedValue || "")) {
				opt.selected = true;
			}
			selectEl.appendChild(opt);
		});
		selectEl.value = selectedValue || "";
	}

	setSelectOptions(
		stateSelect,
		[
			{ value: "all", label: __("All") },
			{ value: "healthy_linked", label: __("Healthy Linked") },
			{ value: "unlinked", label: __("Unmapped") },
			{ value: "link_issues", label: __("Needs Review") },
		],
		"all"
	);

	function formatStageStatus(status) {
		const map = {
			"Not Started": () => __("Not Started"),
			"In Progress": () => __("In Progress"),
			Completed: () => __("Completed"),
			Certified: () => __("Certified"),
			"On Hold": () => __("On Hold"),
		};
		return map[status] ? map[status]() : status || "";
	}

	setSelectOptions(
		statusSelect,
		[
			{ value: "", label: __("All") },
			{ value: "Not Started", label: __("Not Started") },
			{ value: "In Progress", label: __("In Progress") },
			{ value: "Completed", label: __("Completed") },
			{ value: "Certified", label: __("Certified") },
			{ value: "On Hold", label: __("On Hold") },
		],
		""
	);

	// Active drilldown chips
	const chipsRow = document.createElement("div");
	chipsRow.className = "ct-cov-chips d-none";
	chipsRow.setAttribute("data-role", "chips");
	container.appendChild(chipsRow);

	// KPI strip
	const kpiRow = document.createElement("div");
	kpiRow.className = "ct-cov-kpis d-none";
	kpiRow.setAttribute("data-role", "kpis");
	container.appendChild(kpiRow);

	// Visible non-financial disclaimer
	const disclaimerEl = document.createElement("div");
	disclaimerEl.className = "ct-cov-disclaimer d-none";
	disclaimerEl.setAttribute("data-role", "disclaimer");
	container.appendChild(disclaimerEl);

	// Accessible Tabs (selection by activation; no aria-controls per modern tabs guidance)
	const tablistEl = document.createElement("div");
	tablistEl.className = "ct-cov-tablist";
	tablistEl.setAttribute("role", "tablist");
	tablistEl.setAttribute("aria-label", __("Execution Coverage Views"));
	const tabButtons = {};
	const tabDefs = [
		{ id: "ct-cov-tab-stages", mode: "stages", label: __("Stages") },
		{ id: "ct-cov-tab-items", mode: "items", label: __("Items Summary") },
		{ id: "ct-cov-tab-no-stages", mode: "no_stages", label: __("No Stages") },
	];
	tabDefs.forEach((def) => {
		const btn = document.createElement("button");
		btn.type = "button";
		btn.id = def.id;
		btn.className = "ct-cov-tab";
		btn.setAttribute("role", "tab");
		btn.setAttribute("data-view-mode", def.mode);
		btn.setAttribute("aria-selected", def.mode === "stages" ? "true" : "false");
		btn.tabIndex = def.mode === "stages" ? 0 : -1;
		const labelSpan = document.createElement("span");
		labelSpan.className = "ct-cov-tab-label";
		labelSpan.textContent = def.label;
		const countSpan = document.createElement("span");
		countSpan.className = "ct-cov-tab-count";
		countSpan.textContent = "0";
		btn.appendChild(labelSpan);
		btn.appendChild(countSpan);
		tablistEl.appendChild(btn);
		tabButtons[def.mode] = { btn, labelSpan, countSpan };
	});
	container.appendChild(tablistEl);

	// Tabpanel & responsive table container
	const tabPanel = document.createElement("div");
	tabPanel.setAttribute("role", "tabpanel");
	tabPanel.setAttribute("aria-labelledby", "ct-cov-tab-stages");
	tabPanel.setAttribute("data-role", "tabpanel");

	const tableWrap = document.createElement("div");
	tableWrap.className = "ct-cov-table-wrap";
	tableWrap.setAttribute("tabindex", "0");
	tableWrap.setAttribute("role", "region");
	tableWrap.setAttribute("aria-labelledby", "ct-cov-table-caption");
	tableWrap.setAttribute("data-role", "table-wrap");
	tabPanel.appendChild(tableWrap);

	const paginationBar = document.createElement("div");
	paginationBar.className = "ct-cov-pagination d-none";
	paginationBar.setAttribute("data-role", "pagination");
	const pageInfo = document.createElement("span");
	pageInfo.setAttribute("data-role", "page-info");
	const pageBtnGroup = document.createElement("div");
	pageBtnGroup.style.display = "flex";
	pageBtnGroup.style.gap = "6px";
	const prevBtn = document.createElement("button");
	prevBtn.type = "button";
	prevBtn.className = "btn btn-default btn-sm";
	prevBtn.setAttribute("data-action", "prev-page");
	prevBtn.textContent = __("Previous");
	const nextBtn = document.createElement("button");
	nextBtn.type = "button";
	nextBtn.className = "btn btn-default btn-sm";
	nextBtn.setAttribute("data-action", "next-page");
	nextBtn.textContent = __("Next");
	pageBtnGroup.appendChild(prevBtn);
	pageBtnGroup.appendChild(nextBtn);
	paginationBar.appendChild(pageInfo);
	paginationBar.appendChild(pageBtnGroup);
	tabPanel.appendChild(paginationBar);

	container.appendChild(tabPanel);
	rootEl.appendChild(container);

	// Helper: build query params for both URL sync and authorized streaming export
	function buildFilterParams(extra) {
		const params = new URLSearchParams();
		if (state.project) params.set("project", state.project);
		if (state.boq_header) params.set("boq_header", state.boq_header);
		if (state.boq_structure) params.set("boq_structure", state.boq_structure);
		if (state.boq_item) params.set("boq_item", state.boq_item);
		if (state.execution_node) params.set("execution_node", state.execution_node);
		if (state.mapping_state && state.mapping_state !== "all") {
			params.set("mapping_state", state.mapping_state);
		}
		if (state.stage_status) params.set("stage_status", state.stage_status);
		if (state.search) params.set("search", state.search);
		if (state.view_mode) params.set("view_mode", state.view_mode);
		if (extra) {
			Object.keys(extra).forEach((k) => {
				if (extra[k] != null && extra[k] !== "") {
					params.set(k, String(extra[k]));
				}
			});
		}
		return params;
	}

	function buildExportUrl(format) {
		const params = buildFilterParams({ export_format: format });
		return (
			"/api/method/construction.api.execution_coverage_api.export_execution_coverage?" +
			params.toString()
		);
	}

	function triggerExport(format) {
		if (!state.project) {
			frappe.show_alert({
				message: __("Select a Project in the top bar before exporting."),
				indicator: "orange",
			});
			return;
		}
		if (state.last_response && state.last_response.limit_exceeded) {
			frappe.show_alert({
				message: __("Narrow filters before exporting."),
				indicator: "orange",
			});
			return;
		}
		const url = buildExportUrl(format);
		if (typeof window.open === "function") {
			window.open(url, "_blank", "noopener");
		}
	}

	function syncUrlQuery() {
		if (
			typeof window === "undefined" ||
			!window.history ||
			typeof window.history.replaceState !== "function" ||
			!window.location
		) {
			return;
		}
		const params = buildFilterParams();
		const qs = params.toString();
		const nextUrl = window.location.pathname + (qs ? "?" + qs : "");
		try {
			window.history.replaceState(null, "", nextUrl);
		} catch (_err) {
			// Ignore history API restrictions in embedded test environments.
		}
	}

	// Register page actions
	if (typeof page.add_inner_button === "function") {
		page.add_inner_button(__("Download CSV"), () => triggerExport("csv"), __("Export"));
		page.add_inner_button(__("Download Excel"), () => triggerExport("xlsx"), __("Export"));
		page.add_inner_button(__("Execution Tree"), () => {
			if (typeof frappe.set_route === "function") {
				frappe.set_route("execution-breakdown");
			}
		});
		page.add_inner_button(__("Reset Filters"), () => resetFilters());
	}

	function setStatus(message, kind) {
		statusBanner.className = "alert " + (kind || "alert-info") + (message ? "" : " d-none");
		statusBanner.textContent = message || "";
	}

	function clearContent() {
		kpiRow.classList.add("d-none");
		kpiRow.replaceChildren();
		disclaimerEl.classList.add("d-none");
		disclaimerEl.textContent = "";
		conflictBanner.classList.add("d-none");
		conflictText.textContent = "";
		tableWrap.replaceChildren();
		paginationBar.classList.add("d-none");
	}

	function updateTabSelectionUI() {
		tabDefs.forEach((def) => {
			const entry = tabButtons[def.mode];
			const selected = def.mode === state.view_mode;
			entry.btn.setAttribute("aria-selected", selected ? "true" : "false");
			entry.btn.tabIndex = selected ? 0 : -1;
			if (selected) {
				tabPanel.setAttribute("aria-labelledby", def.id);
				if (typeof entry.btn.scrollIntoView === "function") {
					entry.btn.scrollIntoView({ block: "nearest", inline: "nearest" });
				}
			}
		});
	}

	function renderChips() {
		chipsRow.replaceChildren();
		const items = [];
		if (state.boq_structure) {
			const structObj = (state.structures || []).find((s) => s.name === state.boq_structure);
			const sDisplay = structObj
				? (structObj.wbs_code ? structObj.wbs_code + " — " : "") +
				  (structObj.title || structObj.name)
				: state.boq_structure;
			items.push({ key: "boq_structure", label: __("BOQ Structure") + ": " + sDisplay });
		}
		if (state.boq_item) {
			items.push({ key: "boq_item", label: __("BOQ Item") + ": " + state.boq_item });
		}
		if (state.execution_node) {
			const nodeObj = (state.tree_nodes || []).find((n) => n.name === state.execution_node);
			const display = nodeObj
				? (nodeObj.ebs_code ? nodeObj.ebs_code + " — " : "") +
				  (nodeObj.title || nodeObj.name)
				: state.execution_node;
			items.push({
				key: "execution_node",
				label: __("Execution Location") + ": " + display,
			});
		}
		if (!items.length) {
			chipsRow.classList.add("d-none");
			return;
		}
		chipsRow.classList.remove("d-none");
		items.forEach((chip) => {
			const el = document.createElement("span");
			el.className = "ct-cov-chip";
			const txt = document.createElement("span");
			txt.textContent = chip.label;
			const closeBtn = document.createElement("button");
			closeBtn.type = "button";
			closeBtn.setAttribute("aria-label", __("Clear filter"));
			closeBtn.setAttribute("data-clear-filter", chip.key);
			closeBtn.textContent = "×";
			closeBtn.addEventListener("click", () => {
				state[chip.key] = "";
				if (chip.key === "execution_node") nodeSelect.value = "";
				if (chip.key === "boq_structure") structureSelect.value = "";
				state.page = 1;
				loadCoverage();
			});
			el.appendChild(txt);
			el.appendChild(closeBtn);
			chipsRow.appendChild(el);
		});
	}

	function renderKpis(data) {
		kpiRow.replaceChildren();
		const summary = data.summary;
		const pop = data.population_summary;
		if (!summary || !pop) {
			kpiRow.classList.add("d-none");
			return;
		}
		kpiRow.classList.remove("d-none");

		function addCard(label, value, subText) {
			const card = document.createElement("div");
			card.className = "ct-cov-kpi";
			const lEl = document.createElement("div");
			lEl.className = "ct-cov-kpi-label";
			lEl.textContent = label;
			const vEl = document.createElement("div");
			vEl.className = "ct-cov-kpi-value";
			vEl.textContent = String(value);
			card.appendChild(lEl);
			card.appendChild(vEl);
			if (subText) {
				const sEl = document.createElement("div");
				sEl.className = "ct-cov-kpi-sub";
				sEl.textContent = subText;
				card.appendChild(sEl);
			}
			kpiRow.appendChild(card);
		}

		addCard(__("Matching Stages"), summary.total_stages);
		addCard(__("Healthy Linked"), summary.healthy_linked);
		addCard(__("Unmapped"), summary.unlinked);
		addCard(
			__("Needs Review"),
			summary.link_issues,
			__("Disabled Links") +
				": " +
				summary.disabled_links +
				" · " +
				__("Integrity Issues") +
				": " +
				summary.integrity_issues
		);
		addCard(__("Mapping Completeness"), summary.coverage_pct_display);
		const noStagesSub =
			pop.items_hidden_by_stage_filters > 0
				? __("Zero Matching Stages") + ": " + pop.items_hidden_by_stage_filters
				: __("BOQ Items in Scope") + ": " + pop.total_items;
		addCard(pop.no_stages_label || __("No Stages"), pop.items_without_stages, noStagesSub);

		// Update tab counts & dynamic partial-visibility label
		tabButtons.stages.countSpan.textContent = String(summary.total_stages);
		tabButtons.items.countSpan.textContent = String(pop.total_items);
		tabButtons.no_stages.labelSpan.textContent = pop.no_stages_label || __("No Stages");
		tabButtons.no_stages.countSpan.textContent = String(pop.items_without_stages);
	}

	function makeBadge(text, variant) {
		const b = document.createElement("span");
		b.className = "ct-cov-badge ct-cov-badge-" + variant;
		b.textContent = text || "";
		return b;
	}

	function makeDocLink(doctype, name, text) {
		const a = document.createElement("a");
		const slug = doctype.toLowerCase().replace(/\s+/g, "-");
		a.href = "/app/" + slug + "/" + encodeURIComponent(name);
		a.textContent = text || name;
		a.addEventListener("click", (e) => {
			if (typeof frappe.set_route === "function") {
				e.preventDefault();
				frappe.set_route("Form", doctype, name);
			}
		});
		return a;
	}

	function stateBadgeVariant(stateKey) {
		if (stateKey === "healthy_linked") return "green";
		if (stateKey === "unlinked") return "gray";
		return "orange";
	}

	function groupBadgeVariant(groupKey) {
		if (groupKey === "full") return "green";
		if (groupKey === "partial") return "blue";
		if (groupKey === "needs_review") return "orange";
		if (groupKey === "filtered_out") return "gray";
		if (groupKey === "no_stages") return "gray";
		return "red";
	}

	function formatQty(val, uom) {
		const num = Number(val || 0);
		const text = Number.isInteger(num) ? String(num) : String(Math.round(num * 1000) / 1000);
		return uom ? text + " " + uom : text;
	}

	function renderTable(data) {
		tableWrap.replaceChildren();
		const rows = data.rows || [];
		const mode = data.view_mode || state.view_mode;
		const pop = data.population_summary || {};

		if (!rows.length) {
			const empty = document.createElement("p");
			empty.className = "text-muted";
			empty.style.padding = "18px 14px";
			empty.style.margin = "0";
			empty.textContent = __("No matching records found for the current filters.");
			tableWrap.appendChild(empty);
			return;
		}

		let captionText = __("Stages");
		let columns = [];
		if (mode === "stages") {
			captionText = __("Stages");
			columns = [
				{ label: __("Stage"), isRowHeader: true },
				{ label: __("Mapping Status") },
				{ label: __("Execution Location") },
				{ label: __("BOQ Item") },
				{ label: __("BOQ Header") },
				{ label: __("Planned Qty"), numeric: true },
				{ label: __("Stage Status") },
				{ label: __("Item Planning Default") },
			];
		} else if (mode === "items") {
			captionText = __("Items Summary");
			columns = [
				{ label: __("BOQ Item"), isRowHeader: true },
				{ label: __("Item Group") },
				{ label: __("BOQ Header") },
				{ label: __("Matching Stages"), numeric: true },
				{ label: __("Healthy Linked"), numeric: true },
				{ label: __("Unmapped"), numeric: true },
				{ label: __("Needs Review"), numeric: true },
				{ label: __("Item Qty"), numeric: true },
				{ label: __("Stage Planned Qty Sum (Single Item)"), numeric: true },
				{ label: __("Item Planning Default") },
				{ label: __("Actions") },
			];
		} else {
			captionText = pop.no_stages_label || __("No Stages");
			columns = [
				{ label: __("BOQ Item"), isRowHeader: true },
				{ label: __("BOQ Header") },
				{ label: __("Item Qty"), numeric: true },
				{ label: __("Item Planning Default") },
				{ label: __("Status") },
			];
		}

		const table = document.createElement("table");
		table.className = "ct-cov-table";
		const caption = document.createElement("caption");
		caption.id = "ct-cov-table-caption";
		caption.textContent = captionText;
		table.appendChild(caption);

		const thead = document.createElement("thead");
		const htr = document.createElement("tr");
		columns.forEach((col) => {
			const th = document.createElement("th");
			th.setAttribute("scope", "col");
			if (col.numeric) th.className = "ct-cov-num";
			th.textContent = col.label;
			htr.appendChild(th);
		});
		thead.appendChild(htr);
		table.appendChild(thead);

		const tbody = document.createElement("tbody");
		rows.forEach((row) => {
			const tr = document.createElement("tr");

			function addCell(colIndex, contentNodeOrText, numeric) {
				const col = columns[colIndex];
				const cell = document.createElement(col.isRowHeader ? "th" : "td");
				if (col.isRowHeader) {
					cell.setAttribute("scope", "row");
				} else {
					cell.setAttribute("data-label", col.label);
				}
				if (numeric || col.numeric) cell.className = "ct-cov-num";
				if (
					typeof contentNodeOrText === "string" ||
					typeof contentNodeOrText === "number"
				) {
					cell.textContent = String(contentNodeOrText);
				} else if (contentNodeOrText) {
					cell.appendChild(contentNodeOrText);
				}
				tr.appendChild(cell);
			}

			if (mode === "stages") {
				const stageWrap = document.createElement("div");
				const stgLabel =
					(row.stage_code ? row.stage_code + " — " : "") + (row.stage_name || row.name);
				stageWrap.appendChild(makeDocLink("BOQ Item Stage", row.name, stgLabel));
				addCell(0, stageWrap);

				const stateWrap = document.createElement("div");
				stateWrap.appendChild(
					makeBadge(
						row.mapping_state_label || row.mapping_state,
						stateBadgeVariant(row.mapping_state)
					)
				);
				if (row.issue_label) {
					const iss = document.createElement("div");
					iss.style.fontSize = "11px";
					iss.style.marginBlockStart = "3px";
					iss.style.color = "var(--text-muted, #64748b)";
					iss.textContent = row.issue_label;
					stateWrap.appendChild(iss);
				}
				addCell(1, stateWrap);

				if (row.execution_node && row.node_display) {
					const locBtn = document.createElement("button");
					locBtn.type = "button";
					locBtn.className = "ct-cov-link-btn";
					locBtn.textContent = row.node_display;
					locBtn.addEventListener("click", () => {
						state.execution_node = row.execution_node;
						nodeSelect.value = row.execution_node;
						state.page = 1;
						loadCoverage();
					});
					addCell(2, locBtn);
				} else {
					addCell(2, "—");
				}

				const itemWrap = document.createElement("div");
				const itemLabel =
					(row.wbs_code ? row.wbs_code + " — " : "") + (row.item_title || row.boq_item);
				itemWrap.appendChild(makeDocLink("BOQ Item", row.boq_item, itemLabel));
				addCell(3, itemWrap);

				const hdrText =
					(row.header_title || row.boq_header) +
					(row.header_type || row.header_status
						? " (" +
						  [row.header_type, row.header_status].filter(Boolean).join(" · ") +
						  ")"
						: "");
				addCell(4, hdrText);
				addCell(5, formatQty(row.planned_qty, row.uom), true);
				addCell(6, formatStageStatus(row.stage_status));
				addCell(7, row.item_planned_node_display || "—");
			} else if (mode === "items") {
				const itemWrap = document.createElement("div");
				const itemLabel =
					(row.wbs_code ? row.wbs_code + " — " : "") + (row.item_title || row.name);
				itemWrap.appendChild(makeDocLink("BOQ Item", row.name, itemLabel));
				addCell(0, itemWrap);

				addCell(
					1,
					makeBadge(
						row.filtered_group_label || row.filtered_group,
						groupBadgeVariant(row.filtered_group)
					)
				);

				const hdrText =
					(row.header_title || row.boq_header) +
					(row.header_type || row.header_status
						? " (" +
						  [row.header_type, row.header_status].filter(Boolean).join(" · ") +
						  ")"
						: "");
				addCell(2, hdrText);
				addCell(
					3,
					String(row.matching_stages) + " / " + String(row.total_item_stages),
					true
				);
				addCell(4, row.healthy_linked, true);
				addCell(5, row.unlinked, true);
				addCell(6, row.link_issues, true);
				addCell(7, formatQty(row.item_quantity, row.uom), true);
				addCell(8, formatQty(row.stage_planned_qty_sum, row.uom), true);
				addCell(9, row.planned_node_display || "—");

				const drillBtn = document.createElement("button");
				drillBtn.type = "button";
				drillBtn.className = "btn btn-default btn-xs";
				drillBtn.textContent = __("View Stages");
				drillBtn.addEventListener("click", () => {
					state.boq_item = row.name;
					state.view_mode = "stages";
					state.page = 1;
					updateTabSelectionUI();
					loadCoverage();
				});
				addCell(10, drillBtn);
			} else {
				const itemWrap = document.createElement("div");
				const itemLabel =
					(row.wbs_code ? row.wbs_code + " — " : "") + (row.item_title || row.name);
				itemWrap.appendChild(makeDocLink("BOQ Item", row.name, itemLabel));
				addCell(0, itemWrap);

				const hdrText =
					(row.header_title || row.boq_header) +
					(row.header_type || row.header_status
						? " (" +
						  [row.header_type, row.header_status].filter(Boolean).join(" · ") +
						  ")"
						: "");
				addCell(1, hdrText);
				addCell(2, formatQty(row.item_quantity, row.uom), true);
				addCell(3, row.planned_node_display || "—");
				addCell(
					4,
					makeBadge(row.status_label || pop.no_stages_label || __("No Stages"), "gray")
				);
			}

			tbody.appendChild(tr);
		});
		table.appendChild(tbody);
		tableWrap.appendChild(table);
	}

	function renderPagination(pagination) {
		if (!pagination || pagination.total_rows === 0) {
			paginationBar.classList.add("d-none");
			return;
		}
		paginationBar.classList.remove("d-none");
		pageInfo.textContent = __("Page {0} of {1} ({2} rows)", [
			pagination.page,
			pagination.total_pages,
			pagination.total_rows,
		]);
		prevBtn.disabled = !pagination.has_prev;
		nextBtn.disabled = !pagination.has_next;
	}

	function updateHeaderOptions(headers) {
		state.headers = headers || [];
		const opts = [{ value: "", label: __("All BOQ Headers") }].concat(
			state.headers.map((h) => ({
				value: h.name,
				label:
					(h.title || h.name) +
					(h.boq_type || h.status
						? " (" + [h.boq_type, h.status].filter(Boolean).join(" · ") + ")"
						: ""),
			}))
		);
		setSelectOptions(headerSelect, opts, state.boq_header);
	}

	function updateStructureOptions(structures) {
		state.structures = structures || [];
		const multiHeader = !state.boq_header && (state.headers || []).length > 1;
		const opts = [{ value: "", label: __("All BOQ Structures") }].concat(
			state.structures.map((s) => {
				const indent = s.depth && s.depth > 1 ? "\u00A0\u00A0".repeat(s.depth - 1) : "";
				const code = s.wbs_code ? s.wbs_code + " — " : "";
				const groupTag = s.is_group ? " [" + __("Group") + "]" : "";
				const hdrSuffix = multiHeader && s.header_title ? " (" + s.header_title + ")" : "";
				return {
					value: s.name,
					label: indent + code + (s.title || s.name) + groupTag + hdrSuffix,
				};
			})
		);
		setSelectOptions(structureSelect, opts, state.boq_structure);
		renderChips();
	}

	function updateNodeOptions(nodes) {
		state.tree_nodes = nodes || [];
		const opts = [{ value: "", label: __("All Execution Locations") }].concat(
			state.tree_nodes.map((node) => {
				const indent =
					node.depth && node.depth > 1 ? "\u00A0\u00A0".repeat(node.depth - 1) : "";
				const code = node.ebs_code ? node.ebs_code + " — " : "";
				const disabledTag = node.disabled ? " [" + __("Disabled") + "]" : "";
				return {
					value: node.name,
					label: indent + code + (node.title || node.name) + disabledTag,
				};
			})
		);
		setSelectOptions(nodeSelect, opts, state.execution_node);
		renderChips();
	}

	function loadTreeNodesForProject(project) {
		if (!project) {
			state.tree_project = "";
			updateNodeOptions([]);
			return;
		}
		if (state.tree_project === project && state.tree_nodes.length) {
			return;
		}
		const treeGen = ++state.tree_generation;
		state.tree_project = project;
		frappe.call({
			method: "construction.api.execution_tree_api.get_tree",
			type: "GET",
			args: { project },
			callback(r) {
				if (state.tree_generation !== treeGen || state.project !== project) return;
				const nodes = (r && r.message && r.message.nodes) || [];
				updateNodeOptions(nodes);
			},
		});
	}

	function loadCoverage() {
		const targetProject = String(state.project || "").trim();
		const generation = ++state.generation;
		state.last_response = null;
		renderChips();
		updateTabSelectionUI();
		syncUrlQuery();

		if (!targetProject) {
			clearContent();
			setStatus(
				__("Select a Project in the top bar to view execution coverage."),
				"alert-info"
			);
			return;
		}

		setStatus(__("Loading…"), "alert-info");
		loadTreeNodesForProject(targetProject);

		const args = {
			project: targetProject,
			mapping_state: state.mapping_state || "all",
			view_mode: state.view_mode || "stages",
			page: state.page,
			page_size: state.page_size,
		};
		if (state.boq_header) args.boq_header = state.boq_header;
		if (state.boq_structure) args.boq_structure = state.boq_structure;
		if (state.boq_item) args.boq_item = state.boq_item;
		if (state.execution_node) args.execution_node = state.execution_node;
		if (state.stage_status) args.stage_status = state.stage_status;
		if (state.search) args.search = state.search;

		frappe.call({
			method: "construction.api.execution_coverage_api.get_execution_coverage",
			type: "GET",
			args,
			callback(r) {
				if (state.generation !== generation || state.project !== targetProject) return;
				const data = r && r.message;
				if (!data) {
					clearContent();
					setStatus(__("Not permitted."), "alert-danger");
					return;
				}
				state.last_response = data;
				updateHeaderOptions(data.headers || []);
				updateStructureOptions(data.structures || []);

				if (data.limit_exceeded) {
					clearContent();
					setStatus(
						data.message ||
							__("Too many records match the current scope. Narrow filters."),
						"alert-warning"
					);
					return;
				}

				setStatus("", "alert-info");

				if (data.filter_conflict) {
					conflictText.textContent = data.filter_conflict.message || "";
					conflictBanner.classList.remove("d-none");
				} else {
					conflictBanner.classList.add("d-none");
					conflictText.textContent = "";
				}

				renderKpis(data);
				if (data.disclaimer) {
					disclaimerEl.textContent = data.disclaimer;
					disclaimerEl.classList.remove("d-none");
				} else {
					disclaimerEl.classList.add("d-none");
				}
				renderTable(data);
				renderPagination(data.pagination);
			},
			error() {
				if (state.generation !== generation || state.project !== targetProject) return;
				clearContent();
				setStatus(__("Not permitted."), "alert-danger");
			},
		});
	}

	function resetFilters() {
		state.boq_header = "";
		state.boq_structure = "";
		state.boq_item = "";
		state.execution_node = "";
		state.mapping_state = "all";
		state.stage_status = "";
		state.search = "";
		state.page = 1;
		headerSelect.value = "";
		structureSelect.value = "";
		nodeSelect.value = "";
		stateSelect.value = "all";
		statusSelect.value = "";
		searchInput.value = "";
		loadCoverage();
	}

	function applyIncomingRouteParams() {
		const routeOpts = frappe.route_options ? Object.assign({}, frappe.route_options) : {};
		if (frappe.route_options) {
			frappe.route_options = null;
		}
		const urlParams =
			typeof window !== "undefined" && window.location && window.location.search
				? new URLSearchParams(window.location.search)
				: new URLSearchParams();

		function pick(key) {
			if (routeOpts[key] != null && String(routeOpts[key]).trim() !== "") {
				return String(routeOpts[key]).trim();
			}
			const q = urlParams.get(key);
			return q && q.trim() ? q.trim() : "";
		}

		const incomingProject = pick("project");
		if (incomingProject) state.project = incomingProject;
		const incomingHeader = pick("boq_header");
		if (incomingHeader) state.boq_header = incomingHeader;
		const incomingStruct = pick("boq_structure");
		if (incomingStruct) state.boq_structure = incomingStruct;
		const incomingItem = pick("boq_item");
		if (incomingItem) state.boq_item = incomingItem;
		const incomingNode = pick("execution_node");
		if (incomingNode) state.execution_node = incomingNode;
		const incomingState = pick("mapping_state");
		if (incomingState && VALID_MAPPING_STATES.includes(incomingState)) {
			state.mapping_state = incomingState;
		}
		const incomingStatus = pick("stage_status");
		if (incomingStatus && VALID_STAGE_STATUSES.includes(incomingStatus)) {
			state.stage_status = incomingStatus;
		}
		const incomingSearch = pick("search");
		if (incomingSearch) state.search = incomingSearch;
		const incomingView = pick("view_mode");
		if (incomingView && VALID_VIEW_MODES.includes(incomingView)) {
			state.view_mode = incomingView;
		}

		headerSelect.value = state.boq_header;
		structureSelect.value = state.boq_structure;
		nodeSelect.value = state.execution_node;
		stateSelect.value = state.mapping_state;
		statusSelect.value = state.stage_status;
		searchInput.value = state.search;
	}

	// Event bindings
	headerSelect.addEventListener("change", () => {
		state.boq_header = headerSelect.value || "";
		state.boq_structure = "";
		state.boq_item = "";
		structureSelect.value = "";
		state.page = 1;
		loadCoverage();
	});

	structureSelect.addEventListener("change", () => {
		state.boq_structure = structureSelect.value || "";
		state.boq_item = "";
		state.page = 1;
		loadCoverage();
	});

	nodeSelect.addEventListener("change", () => {
		state.execution_node = nodeSelect.value || "";
		state.page = 1;
		loadCoverage();
	});

	stateSelect.addEventListener("change", () => {
		state.mapping_state = stateSelect.value || "all";
		state.page = 1;
		loadCoverage();
	});

	statusSelect.addEventListener("change", () => {
		state.stage_status = statusSelect.value || "";
		state.page = 1;
		loadCoverage();
	});

	searchInput.addEventListener("input", () => {
		if (state.search_timer) clearTimeout(state.search_timer);
		state.search_timer = setTimeout(() => {
			state.search = (searchInput.value || "").trim();
			state.page = 1;
			loadCoverage();
		}, 250);
	});

	searchInput.addEventListener("keydown", (e) => {
		if (e.key === "Enter") {
			if (state.search_timer) clearTimeout(state.search_timer);
			state.search = (searchInput.value || "").trim();
			state.page = 1;
			loadCoverage();
		}
	});

	clearLocBtn.addEventListener("click", () => {
		state.execution_node = "";
		nodeSelect.value = "";
		state.page = 1;
		loadCoverage();
	});

	showAllStatesBtn.addEventListener("click", () => {
		state.mapping_state = "all";
		stateSelect.value = "all";
		state.page = 1;
		loadCoverage();
	});

	// Tabs: selection by activation (click / Enter / Space); arrow keys move focus
	tabDefs.forEach((def, idx) => {
		const btn = tabButtons[def.mode].btn;
		btn.addEventListener("click", () => {
			if (state.view_mode === def.mode) return;
			state.view_mode = def.mode;
			state.page = 1;
			updateTabSelectionUI();
			loadCoverage();
		});
		btn.addEventListener("keydown", (e) => {
			const isRtl =
				frappe.utils && typeof frappe.utils.is_rtl === "function" && frappe.utils.is_rtl();
			const nextKey = isRtl ? "ArrowLeft" : "ArrowRight";
			const prevKey = isRtl ? "ArrowRight" : "ArrowLeft";
			let targetIdx = null;
			if (e.key === nextKey) targetIdx = (idx + 1) % tabDefs.length;
			else if (e.key === prevKey) targetIdx = (idx - 1 + tabDefs.length) % tabDefs.length;
			else if (e.key === "Home") targetIdx = 0;
			else if (e.key === "End") targetIdx = tabDefs.length - 1;
			if (targetIdx !== null) {
				e.preventDefault();
				tabButtons[tabDefs[targetIdx].mode].btn.focus();
			}
		});
	});

	prevBtn.addEventListener("click", () => {
		if (state.page > 1) {
			state.page -= 1;
			loadCoverage();
		}
	});

	nextBtn.addEventListener("click", () => {
		const pag = state.last_response && state.last_response.pagination;
		if (pag && pag.has_next) {
			state.page += 1;
			loadCoverage();
		}
	});

	function syncScope() {
		const scope = window.scopeContext;
		if (
			scope &&
			(!scope.supportsSaveConfirmation ||
				scope._savePending ||
				scope._saveQueued ||
				scope._saveFailed)
		) {
			++state.generation;
			clearContent();
			setStatus(
				scope._conflict
					? __("Another session changed the scope. Choose how to resolve it.")
					: scope._saveFailed
					? __("Could not confirm the scope. Retry or refresh the page.")
					: __("Saving scope…"),
				"alert-info"
			);
			return;
		}
		const current = scope && scope.enabled && scope.getValidatedCurrentScope();
		const scopedProject = (current && current.project) || "";
		if (scopedProject && scopedProject !== state.project) {
			state.project = scopedProject;
			state.boq_header = "";
			state.boq_structure = "";
			state.boq_item = "";
			state.execution_node = "";
			state.tree_project = "";
			state.tree_nodes = [];
			state.page = 1;
			headerSelect.value = "";
			structureSelect.value = "";
			nodeSelect.value = "";
		} else if (!state.project && scopedProject) {
			state.project = scopedProject;
		}
		loadCoverage();
	}

	const scopeEvents =
		"scope:changed.executionCoverage scope:save_confirmed.executionCoverage scope:save_failed.executionCoverage scope:save_conflict.executionCoverage";

	function showPage() {
		applyIncomingRouteParams();
		$(document).off(scopeEvents).on(scopeEvents, syncScope);
		syncScope();
	}

	function hidePage() {
		$(document).off(scopeEvents);
		if (state.search_timer) clearTimeout(state.search_timer);
		++state.generation;
	}

	$(wrapper).on("show", showPage).on("hide", hidePage);
	showPage();
};
