/* ═══════════════════════════════════════════════════════════════════
   vite_layout_controls.js — Global Form Config (Vite UI)
   Attaches to EVERY Frappe form automatically via frappe.ui.form.on('*')
   Injects a "Form Config" button into the page head.
   Clicking opens a 340px slide-in panel (3 tabs: Layout / Fields / Presets)
   Persistence:
     - Column density → localStorage (pure visual, fast read)
     - Field visibility → frappe.model.user_settings (server-side, cross-device)
     - Layout presets  → frappe.model.user_settings (server-side, cross-device)
   Version: 1.0 | 2026-05-28
═══════════════════════════════════════════════════════════════════ */

(function () {
	"use strict";

	/* ══════════════════════════════════════════════════════════════
     PRESET REGISTRY
     DocType → array of preset config objects.
     Add new DocTypes here without touching any other code.
  ══════════════════════════════════════════════════════════════ */
	const PRESET_REGISTRY = {
		"BOQ Header": [
			{
				key: "Default",
				name: __("Default (All Fields)"),
				desc: __("All fields — Admin / Power User"),
				fields: [
					"project",
					"project_name",
					"boq_type",
					"status",
					"title",
					"version",
					"total_contract_value",
					"total_estimated_value",
					"total_budgeted_cost",
					"locked_by",
					"locked_date",
				],
			},
			{
				key: "Manager",
				name: __("Manager View"),
				desc: __("Summary: Project, Status, Totals, Lock info"),
				fields: [
					"project",
					"status",
					"title",
					"version",
					"total_contract_value",
					"total_estimated_value",
					"total_budgeted_cost",
					"locked_by",
					"locked_date",
				],
			},
			{
				key: "Engineer",
				name: __("Engineer View"),
				desc: __("Quantities + Stages — hides financial totals"),
				fields: ["project", "project_name", "title", "status", "boq_type"],
			},
			{
				key: "Accountant",
				name: __("Accountant View"),
				desc: __("Costs + Values — hides engineering fields"),
				fields: [
					"project",
					"title",
					"status",
					"total_contract_value",
					"total_estimated_value",
					"total_budgeted_cost",
				],
			},
			{
				key: "Compact",
				name: __("Compact (Minimal)"),
				desc: __("Project, Title, Status only — mobile / quick view"),
				fields: ["project", "title", "status"],
			},
		],

		"BOQ Item": [
			{
				key: "Default",
				name: __("Default (All Fields)"),
				desc: __("All fields visible"),
				fields: null, // null = show all fields
			},
			{
				key: "Engineer",
				name: __("Engineer View"),
				desc: __("Structure, header, type, quantities — hides pricing fields"),
				// Verified against boq_item.json 2026-05-28
				fields: [
					"boq_header",
					"structure",
					"item_type",
					"quantity",
					"unit",
					"factor",
					"has_stages",
				],
			},
			{
				key: "Accountant",
				name: __("Accountant View"),
				desc: __("Pricing and totals — hides engineering fields"),
				// Verified against boq_item.json 2026-05-28
				fields: [
					"boq_header",
					"unit",
					"quantity",
					"contract_unit_price",
					"factor",
					"line_total",
					"owner_ref_no",
				],
			},
		],

		"BOQ Item Stage": [
			{
				key: "Default",
				name: __("Default (All Fields)"),
				desc: __("All fields visible"),
				fields: null,
			},
			{
				key: "Site",
				name: __("Site View"),
				desc: __("Stage identity and completion — hides notes"),
				// Verified against boq_item_stage.json 2026-05-28
				fields: [
					"boq_item",
					"boq_header",
					"project",
					"stage_name",
					"stage_status",
					"percent_complete",
				],
			},
		],
	};

	/* ══════════════════════════════════════════════════════════════
     SVG ICONS (inline — no external dependency)
  ══════════════════════════════════════════════════════════════ */
	const ICON_GRID = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="1" y="1" width="6" height="6" rx="1.5"/><rect x="9" y="1" width="6" height="6" rx="1.5"/><rect x="1" y="9" width="6" height="6" rx="1.5"/><rect x="9" y="9" width="6" height="6" rx="1.5"/></svg>`;
	const ICON_EYE = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="8" cy="8" r="3"/><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z"/></svg>`;
	const ICON_COL = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="1" width="14" height="14" rx="2"/><line x1="8" y1="1" x2="8" y2="15"/></svg>`;
	const ICON_PRE = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 4h12M4 8h8M6 12h4"/></svg>`;
	const ICON_X = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="2" x2="14" y2="14"/><line x1="14" y1="2" x2="2" y2="14"/></svg>`;
	const ICON_MAXIMIZE = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="12" height="12" rx="1.5"/></svg>`;
	const ICON_RESTORE = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="10" height="10" rx="1"/><path d="M2 6v8h8"/></svg>`;

	/* ══════════════════════════════════════════════════════════════
     STORAGE HELPERS
  ══════════════════════════════════════════════════════════════ */
	function lsKey(doctype, key) {
		return `vfc_${doctype.replace(/\s/g, "_")}_${key}`;
	}

	function loadDensity(doctype) {
		return parseInt(localStorage.getItem(lsKey(doctype, "density")) || "2", 10);
	}

	function saveDensity(doctype, n) {
		localStorage.setItem(lsKey(doctype, "density"), String(n));
	}

	function loadUserSettings(doctype) {
		try {
			return frappe.get_user_settings(doctype) || {};
		} catch (e) {
			return {};
		}
	}

	function saveUserSettings(doctype, key, value) {
		try {
			frappe.model.user_settings.save(doctype, key, value);
		} catch (e) {
			console.warn("[VFC] frappe.model.user_settings.save failed:", e);
		}
	}

	/* ══════════════════════════════════════════════════════════════
     ViteFormConfig — main controller class
  ══════════════════════════════════════════════════════════════ */
	const VFC = {
		/* ─────────────────────────────────────────────────────────
       attach(frm)
       Called on every form refresh. Idempotent.
    ───────────────────────────────────────────────────────── */
		attach(frm) {
			console.log("[VFC] attach() called for:", frm.doctype);
			// Idempotency: only inject once per frm instance
			if (frm._vfc_attached) {
				// On subsequent refreshes, just re-apply saved state
				this._restoreState(frm);
				return;
			}
			frm._vfc_attached = true;

			this._injectButton(frm);
			this._buildPanel(frm);
			this._restoreState(frm);

			// Escape key closes panel
			if (!VFC._escListenerAttached) {
				document.addEventListener("keydown", (e) => {
					if (e.key === "Escape") VFC._closeAll();
				});
				VFC._escListenerAttached = true;
			}
		},

		/* ─────────────────────────────────────────────────────────
       _injectButton(frm)
       Adds the Form Config button to the page head.
    ───────────────────────────────────────────────────────── */
		_injectButton(frm) {
			const pageHead =
				frm.page.page_actions?.[0] || frm.page.$page?.find(".page-actions")?.[0];

			// Use Frappe's native button API to add it to the right side of page head
			frm.page.add_inner_button(
				`${ICON_GRID} ${__("Form Config")}`,
				() => this._togglePanel(frm),
				null,
				"vfc-btn"
			);

			// Find the button we just added and enhance it
			setTimeout(() => {
				const btn = frm.page.inner_toolbar
					?.find("button")
					.filter((_, el) => el.innerHTML.includes("Form Config"))
					.get(0);

				if (btn) {
					btn.classList.add("vfc-btn");
					frm._vfc_btn = btn;

					// Add badge
					const badge = document.createElement("span");
					badge.className = "vfc-badge";
					badge.id = `vfc-badge-${frm.doctype.replace(/\s/g, "-")}`;
					badge.textContent = this._countVisibleFields(frm);
					btn.style.position = "relative";
					btn.appendChild(badge);
				}
			}, 100);
		},

		/* ─────────────────────────────────────────────────────────
       _buildPanel(frm)
       Builds the slide-in config panel DOM.
    ───────────────────────────────────────────────────────── */
		_buildPanel(frm) {
			const dt = frm.doctype;
			const dtId = dt.replace(/\s/g, "-");
			const hasPresets = !!PRESET_REGISTRY[dt];
			const fields = this._getFormFields(frm);

			const panelId = `vfc-panel-${dtId}`;

			// Remove existing panel if any
			document.getElementById(panelId)?.remove();

			const panel = document.createElement("div");
			panel.id = panelId;
			panel.className = "vfc-panel";
			panel.setAttribute("data-doctype", dt);

			panel.innerHTML = `
        <!-- Head -->
        <div class="vfc-panel-head" style="cursor:move;user-select:none">
          <div class="vfc-panel-icon">${ICON_GRID}</div>
          <div>
            <div class="vfc-panel-title">${__("Form Config")}</div>
            <div class="vfc-panel-sub">${__(dt)}</div>
          </div>
          <button class="vfc-maximize-btn" title="${__("Maximize")}">${ICON_MAXIMIZE}</button>
          <button class="vfc-close-btn" data-vfc-close="${panelId}" title="${__(
				"Close"
			)}">${ICON_X}</button>
        </div>

        <!-- Tabs -->
        <div class="vfc-tabs">
          <div class="vfc-tab vfc-tab-active" data-vfc-tab="layout" data-panel="${panelId}">
            ${ICON_COL} ${__("Layout")}
          </div>
          <div class="vfc-tab" data-vfc-tab="fields" data-panel="${panelId}">
            ${ICON_EYE} ${__("Fields")}
          </div>
          <div class="vfc-tab" data-vfc-tab="sections" data-panel="${panelId}">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:text-bottom;margin-right:2px"><rect x="1" y="1" width="14" height="14" rx="2"/><line x1="1" y1="5" x2="15" y2="5"/><line x1="1" y1="10" x2="15" y2="10"/></svg> ${__(
				"Sections"
			)}
          </div>
          ${
				hasPresets
					? `
          <div class="vfc-tab" data-vfc-tab="presets" data-panel="${panelId}">
            ${ICON_PRE} ${__("Presets")}
          </div>`
					: ""
			}
        </div>

        <!-- Body -->
        <div class="vfc-body">

          <!-- Tab: Layout -->
          <div class="vfc-tab-pane" data-vfc-pane="layout" style="display:flex">
            <div style="margin-bottom:16px">
              <div class="vfc-section-title" style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:10px">
                ${ICON_COL} ${__("Column Density")}
              </div>
              <div class="vfc-density-seg" data-panel="${panelId}">
                <div class="vfc-den-opt" data-den="1" title="${__(
					"1 Column — stacked, easy reading"
				)}">
                  <svg width="28" height="22" viewBox="0 0 28 22"><rect x="2" y="2" width="24" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="9" width="24" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="16" width="24" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>
                  ${__("1 Column")}
                </div>
                <div class="vfc-den-opt" data-den="2" title="${__(
					"2 Columns — balanced default"
				)}">
                  <svg width="28" height="22" viewBox="0 0 28 22"><rect x="2" y="2" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="15" y="2" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="9" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="15" y="9" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="16" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="15" y="16" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>
                  ${__("2 Columns")}
                </div>
                <div class="vfc-den-opt" data-den="3" title="${__(
					"3 Columns — dense, wide screens"
				)}">
                  <svg width="28" height="22" viewBox="0 0 28 22"><rect x="2" y="2" width="6" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="11" y="2" width="6" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="20" y="2" width="6" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="9" width="6" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="11" y="9" width="6" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="20" y="9" width="6" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>
                  ${__("3 Columns")}
                </div>
              </div>
              <div style="font-size:10px;color:var(--ct-text-muted);margin-top:8px;line-height:1.6">
                ${__("Saved per-browser. Changes apply immediately.")}
              </div>
            </div>

            <!-- Live mini preview -->
            <div style="margin-top:4px">
              <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:8px">${__(
					"Preview"
				)}</div>
              <div id="vfc-den-preview-${dtId}" style="border:1px solid var(--ct-border);border-radius:6px;padding:10px;background:var(--ct-bg-elevated)">
                <div id="vfc-den-preview-rows-${dtId}"></div>
              </div>
            </div>
          </div>

          <!-- Tab: Fields -->
          <div class="vfc-tab-pane" data-vfc-pane="fields" style="display:none">
            <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:8px;display:flex;align-items:center;gap:6px">
              ${ICON_EYE} ${__("Field Visibility")}
              <span id="vfc-vis-cnt-${dtId}" style="margin-left:auto;background:var(--ct-primary);color:#fff;border-radius:99px;padding:0 7px;font-size:9px;font-weight:800"></span>
            </div>
            <div style="font-size:10px;color:var(--ct-text-muted);margin-bottom:10px;line-height:1.6">
              ${__("Toggle field visibility. Required fields (★) cannot be hidden.")}
            </div>
            <div id="vfc-vis-list-${dtId}"></div>
          </div>

          <!-- Tab: Sections -->
          <div class="vfc-tab-pane" data-vfc-pane="sections" style="display:none">
            <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:8px;display:flex;align-items:center;gap:6px">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="1" width="14" height="14" rx="2"/><line x1="1" y1="5" x2="15" y2="5"/><line x1="1" y1="10" x2="15" y2="10"/></svg>
              ${__("Manage Sections")}
              <button class="btn btn-default btn-xs vfc-btn-add-section" id="vfc-add-sec-btn-${dtId}" style="margin-left:auto;padding:2px 8px;font-size:10px">${__(
				"+ Add Section"
			)}</button>
            </div>
            <div style="font-size:10px;color:var(--ct-text-muted);margin-bottom:12px;line-height:1.6">
              ${__(
					"Drag sections to reorder. Drag fields inside/between sections to arrange columns. Set 1, 2, or 3 columns per section."
				)}
            </div>
            <div id="vfc-sec-list-${dtId}" class="vfc-sec-list-container" style="display:flex;flex-direction:column;gap:12px;flex:1;overflow-y:auto;padding-right:4px"></div>
          </div>

          <!-- Tab: Presets -->
          ${
				hasPresets
					? `
          <div class="vfc-tab-pane" data-vfc-pane="presets" style="display:none">
            <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:8px">
              ${ICON_PRE} ${__("Layout Presets")}
            </div>
            <div style="font-size:10px;color:var(--ct-text-muted);margin-bottom:10px;line-height:1.6">
              ${__("Select a preset, then click Apply & Save. Synced across devices.")}
            </div>
            <div id="vfc-pre-list-${dtId}"></div>
          </div>`
					: ""
			}

        </div><!-- /vfc-body -->

        <!-- Footer -->
        <div class="vfc-foot">
          <span class="vfc-foot-hint">${__("Saved via user settings")}</span>
          <button class="btn btn-default btn-sm" data-vfc-close="${panelId}">${__(
				"Close"
			)}</button>
          <button class="btn btn-primary btn-sm" data-vfc-apply="${dtId}">${__(
				"Apply & Save"
			)}</button>
        </div>
        <div class="vfc-resize-handle" style="position:absolute;right:0;bottom:0;width:15px;height:15px;cursor:se-resize;background:transparent;z-index:201"></div>
      `;

			document.body.appendChild(panel);
			frm._vfc_panel = panel;

			// Make panel draggable and resizable
			this._makeDraggableAndResizable(panel);

			// Wire up events
			this._wirePanel(frm, panel, dtId, fields);
		},

		/* ─────────────────────────────────────────────────────────
       _wirePanel — attach all event listeners to the panel
    ───────────────────────────────────────────────────────── */
		_wirePanel(frm, panel, dtId, fields) {
			const dt = frm.doctype;

			// Maximize button
			const maxBtn = panel.querySelector(`.vfc-maximize-btn`);
			if (maxBtn) {
				maxBtn.addEventListener("click", () => {
					const isMax = panel.classList.toggle("vfc-panel-maximized");
					maxBtn.innerHTML = isMax ? ICON_RESTORE : ICON_MAXIMIZE;
					maxBtn.setAttribute("title", isMax ? __("Restore") : __("Maximize"));

					if (isMax) {
						panel.dataset.prevLeft = panel.style.left;
						panel.dataset.prevTop = panel.style.top;
						panel.dataset.prevWidth = panel.style.width;
						panel.dataset.prevHeight = panel.style.height;

						panel.style.left = "";
						panel.style.top = "";
						panel.style.width = "";
						panel.style.height = "";
					} else {
						panel.style.left = panel.dataset.prevLeft || "";
						panel.style.top = panel.dataset.prevTop || "";
						panel.style.width = panel.dataset.prevWidth || "";
						panel.style.height = panel.dataset.prevHeight || "";
					}
				});
			}

			// Close buttons
			panel.querySelectorAll("[data-vfc-close]").forEach((el) => {
				el.addEventListener("click", () => this._togglePanel(frm, false));
			});

			// Tab switching
			panel.querySelectorAll(".vfc-tab").forEach((tab) => {
				tab.addEventListener("click", () => {
					const name = tab.getAttribute("data-vfc-tab");
					this._switchTab(panel, name);
					if (name === "fields") this._renderFieldList(frm, dtId, fields);
					if (name === "presets") this._renderPresetList(frm, dtId);
					if (name === "layout") this._renderDensityPreview(dtId, loadDensity(dt));
					if (name === "sections") this._renderSectionsTab(frm, dtId);
				});
			});

			// Density options
			panel.querySelectorAll(".vfc-den-opt").forEach((opt) => {
				opt.addEventListener("click", () => {
					const n = parseInt(opt.getAttribute("data-den"), 10);
					this._applyDensity(frm, n);
					this._renderDensityPreview(dtId, n);
				});
			});

			// Add section button
			const addSecBtn = panel.querySelector(`#vfc-add-sec-btn-${dtId}`);
			if (addSecBtn) {
				addSecBtn.addEventListener("click", () => this._addSectionPrompt(frm, dtId));
			}

			// Apply & Save button
			const applyBtn = panel.querySelector(`[data-vfc-apply="${dtId}"]`);
			if (applyBtn) {
				applyBtn.addEventListener("click", () => this._applyAndSave(frm, dtId));
			}

			// Initial render
			this._renderFieldList(frm, dtId, fields);
			this._renderPresetList(frm, dtId);
			this._renderDensityPreview(dtId, loadDensity(dt));
		},

		/* ─────────────────────────────────────────────────────────
       _switchTab
    ───────────────────────────────────────────────────────── */
		_switchTab(panel, name) {
			panel
				.querySelectorAll(".vfc-tab")
				.forEach((t) => t.classList.remove("vfc-tab-active"));
			panel.querySelectorAll(".vfc-tab-pane").forEach((p) => (p.style.display = "none"));
			panel.querySelector(`[data-vfc-tab="${name}"]`)?.classList.add("vfc-tab-active");
			panel.querySelector(`[data-vfc-pane="${name}"]`).style.display = "flex";
		},

		/* ─────────────────────────────────────────────────────────
       _renderFieldList — build the field visibility checklist
    ───────────────────────────────────────────────────────── */
		_renderFieldList(frm, dtId, fields) {
			const container = document.getElementById(`vfc-vis-list-${dtId}`);
			const cntEl = document.getElementById(`vfc-vis-cnt-${dtId}`);
			if (!container) return;

			const settings = loadUserSettings(frm.doctype);
			const hiddenFields = settings.vfc_hidden_fields || [];
			const knownFieldnames = new Set((frm.meta?.fields || []).map((f) => f.fieldname));

			// Unknown-field guard: warn once per unknown field, then skip
			hiddenFields.forEach((fn) => {
				if (!knownFieldnames.has(fn)) {
					console.warn(
						`[VFC] _renderFieldList: unknown fieldname "${fn}" on ${frm.doctype} — skipping`
					);
				}
			});

			const SKIP_TYPES = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading"];
			const renderable = fields.filter((f) => !SKIP_TYPES.includes(f.fieldtype));

			const required = renderable.filter((f) => f.reqd);
			const optional = renderable.filter((f) => !f.reqd);

			let html = "";

			if (required.length) {
				required.forEach((f) => {
					html += `
            <label class="vfc-vis-item" style="cursor:default">
              <input type="checkbox" checked disabled style="opacity:.45;cursor:not-allowed" />
              <span class="vfc-vis-label">★ ${__(f.label || f.fieldname)}</span>
              <span class="vfc-vis-type">${f.fieldtype}</span>
            </label>`;
				});
				html += `<div style="height:1px;background:var(--ct-border);margin:6px 0"></div>`;
			}

			optional.forEach((f) => {
				const isHidden = hiddenFields.includes(f.fieldname);
				html += `
          <label class="vfc-vis-item" for="vfc_vc_${dtId}_${f.fieldname}">
            <input type="checkbox" id="vfc_vc_${dtId}_${f.fieldname}"
              data-field="${f.fieldname}" class="vfc-vis-check"
              ${isHidden ? "" : "checked"}
              onchange="window._VFC._onVisChange(this, '${frm.doctype}')" />
            <span class="vfc-vis-label">${__(f.label || f.fieldname)}</span>
            <span class="vfc-vis-type">${f.fieldtype}</span>
          </label>`;
			});

			container.innerHTML = html;

			// Update count badge
			const visible =
				optional.filter((f) => !hiddenFields.includes(f.fieldname)).length +
				required.length;
			if (cntEl) cntEl.textContent = visible;
		},

		/* ─────────────────────────────────────────────────────────
       _onVisChange — called when a visibility checkbox changes
    ───────────────────────────────────────────────────────── */
		_onVisChange(checkbox, doctype) {
			const fieldname = checkbox.getAttribute("data-field");
			const show = checkbox.checked;

			// Live toggle on the form
			if (frappe.ui.form && cur_frm && cur_frm.doctype === doctype) {
				cur_frm.toggle_display(fieldname, show);
			}

			// Update badge
			const dtId = doctype.replace(/\s/g, "-");
			const allChecks = document.querySelectorAll(`[id^="vfc_vc_${dtId}_"]`);
			const visibleCount = Array.from(allChecks).filter(
				(c) => c.checked && !c.disabled
			).length;
			const reqCount = cur_frm?.fields_dict
				? Object.values(cur_frm.fields_dict).filter((f) => f.df?.reqd).length
				: 0;
			const badge = document.getElementById(`vfc-badge-${doctype.replace(/\s/g, "-")}`);
			const cntEl = document.getElementById(`vfc-vis-cnt-${dtId}`);
			if (badge) badge.textContent = visibleCount + reqCount;
			if (cntEl) cntEl.textContent = visibleCount + reqCount;
		},

		/* ─────────────────────────────────────────────────────────
       _renderPresetList
    ───────────────────────────────────────────────────────── */
		_renderPresetList(frm, dtId) {
			const container = document.getElementById(`vfc-pre-list-${dtId}`);
			if (!container) return;
			const presets = PRESET_REGISTRY[frm.doctype];
			if (!presets) return;

			const settings = loadUserSettings(frm.doctype);
			const curPreset = settings.vfc_preset || "Default";

			container.innerHTML = presets
				.map(
					(p) => `
          <div class="vfc-pre-item${p.key === curPreset ? " vfc-pre-active" : ""}"
               data-preset-key="${p.key}"
               onclick="window._VFC._selectPreset(this, '${frm.doctype}', '${dtId}')">
            <div class="vfc-pre-dot"></div>
            <div>
              <div class="vfc-pre-name">${p.name}</div>
              <div class="vfc-pre-desc">${p.desc}</div>
            </div>
          </div>`
				)
				.join("");
		},

		_selectPreset(el, doctype, dtId) {
			const panel = el.closest(".vfc-panel");
			panel
				.querySelectorAll(".vfc-pre-item")
				.forEach((i) => i.classList.remove("vfc-pre-active"));
			el.classList.add("vfc-pre-active");

			// Preview in fields tab: update checkboxes
			const key = el.getAttribute("data-preset-key");
			const preset = PRESET_REGISTRY[doctype]?.find((p) => p.key === key);
			if (!preset) return;

			const fieldnames = new Set(
				[...document.querySelectorAll(`[id^="vfc_vc_${dtId}_"]`)]
					.filter((cb) => !cb.disabled)
					.map((cb) => cb.getAttribute("data-field"))
			);

			if (preset.fields) {
				preset.fields.forEach((fn) => {
					if (!fieldnames.has(fn)) {
						console.warn(`[VFC] Preset '${key}' references unknown field '${fn}' on ${doctype} — skipping`);
					}
				});
			}

			document.querySelectorAll(`[id^="vfc_vc_${dtId}_"]`).forEach((cb) => {
				if (cb.disabled) return;
				const fn = cb.getAttribute("data-field");
				cb.checked = preset.fields === null ? true : preset.fields.includes(fn);
			});
		},

		/* ─────────────────────────────────────────────────────────
       _renderDensityPreview — mini schematic of column layout
    ───────────────────────────────────────────────────────── */
		_renderDensityPreview(dtId, n) {
			const container = document.getElementById(`vfc-den-preview-rows-${dtId}`);
			if (!container) return;
			const cols = n === 1 ? 1 : n === 3 ? 3 : 2;
			let html = "";
			for (let r = 0; r < 3; r++) {
				html += `<div style="display:flex;gap:5px;margin-bottom:5px">`;
				for (let c = 0; c < cols; c++) {
					html += `<div style="flex:1;height:16px;background:var(--ct-primary-light);border:1px solid rgba(37,99,235,.2);border-radius:3px"></div>`;
				}
				html += `</div>`;
			}
			container.innerHTML = html;

			// Highlight active density button
			const panel = document.querySelector(`[data-vfc-pane="layout"]`);
			if (!panel) return;
			document.querySelectorAll(".vfc-den-opt").forEach((opt) => {
				opt.classList.toggle(
					"vfc-den-active",
					parseInt(opt.getAttribute("data-den"), 10) === n
				);
			});
		},

		/* ─────────────────────────────────────────────────────────
       _applyDensity — CSS class on layout container + save
    ───────────────────────────────────────────────────────── */
		_applyDensity(frm, n, quiet) {
			const container = frm.layout?.wrapper?.[0] || frm.$wrapper?.find(".form-layout")?.[0];
			if (!container) return;
			container.classList.remove("vfc-density-1", "vfc-density-2", "vfc-density-3");
			container.classList.add(`vfc-density-${n}`);
			saveDensity(frm.doctype, n);

			// Live-update VFC grids when engine is active
			if (container.classList.contains("vfc-active")) {
				container.querySelectorAll(".vfc-le-grid").forEach((grid) => {
					grid.style.gridTemplateColumns = `repeat(${n}, 1fr)`;
				});
			}

			// Re-trigger layout engine to recalculate column widths live
			if (window.VFCLayoutEngine) {
				window.VFCLayoutEngine.attach(frm);
			}

			if (!quiet) {
				frappe.show_alert(
					{ message: __("Column density set to {0}", [n]), indicator: "blue" },
					2
				);
			}
		},

		/* ─────────────────────────────────────────────────────────
       _applyVisibility — apply all checkbox states to the form
    ───────────────────────────────────────────────────────── */
		_applyVisibility(frm, dtId) {
			const hiddenFields = [];
			document.querySelectorAll(`[id^="vfc_vc_${dtId}_"]`).forEach((cb) => {
				if (cb.disabled) return;
				const fn = cb.getAttribute("data-field");
				const show = cb.checked;
				frm.toggle_display(fn, show);
				if (!show) hiddenFields.push(fn);
			});
			return hiddenFields;
		},

		/* ─────────────────────────────────────────────────────────
       _applyAndSave — main Apply & Save button handler
    ───────────────────────────────────────────────────────── */
		_applyAndSave(frm, dtId) {
			const dt = frm.doctype;

			// 1. Apply density
			const den = loadDensity(dt); // already saved on click
			this._applyDensity(frm, den, true);

			// 2. Apply visibility + save hidden list
			const hiddenFields = this._applyVisibility(frm, dtId);
			saveUserSettings(dt, "vfc_hidden_fields", hiddenFields);

			// 3. Apply preset (if one is selected)
			const activePreset = frm._vfc_panel?.querySelector(".vfc-pre-item.vfc-pre-active");
			if (activePreset) {
				const key = activePreset.getAttribute("data-preset-key");
				saveUserSettings(dt, "vfc_preset", key);
			}

			// 4. Save sections layout if modified (System Manager only)
			const isSystemManager =
				frappe.user_roles.includes("System Manager") ||
				frappe.session.user === "Administrator";
			if (isSystemManager && frm._vfc_temp_layout) {
				// Extract unassigned column count before filtering out the virtual section
				let unassignedColCount = 2;
				const saveableSections = frm._vfc_temp_layout.filter((sec) => {
					if (sec._unassigned) {
						unassignedColCount = sec.column_count || 2;
						return false;
					}
					return true;
				});

				const sectionsPayload = {
					version: 1,
					unassigned_policy: frm._vfc_unassigned_policy || "append",
					unassigned_column_count: unassignedColCount,
					sections: saveableSections,
				};

				frappe.call({
					method: "construction.construction.api.layout_api.save_layout",
					args: {
						doctype: dt,
						profile_name: "Default",
						is_default: 1,
						priority: 10,
						sections_json: JSON.stringify(sectionsPayload),
					},
					callback(r) {
						if (r.message && r.message.status) {
							if (window.VFCLayoutEngine) {
								window.VFCLayoutEngine.invalidateCache(dt);
								window.VFCLayoutEngine.attach(frm);
							}
						}
					},
				});
			}

			frappe.show_alert({ message: __("Form Config saved"), indicator: "green" }, 3);
			this._togglePanel(frm, false);
		},

		/* ─────────────────────────────────────────────────────────
       _restoreState — re-apply saved state on every refresh
       Called by attach() on every form refresh.
    ───────────────────────────────────────────────────────── */
		_restoreState(frm) {
			const dt = frm.doctype;
			const dtId = dt.replace(/\s/g, "-");
			const knownFieldnames = new Set((frm.meta?.fields || []).map((f) => f.fieldname));

			// 1. Restore density
			const den = loadDensity(dt);
			this._applyDensity(frm, den, true);

			// 2. Restore field visibility (unknown-field guard: skip + single warn)
			const settings = loadUserSettings(dt);
			const hiddenFields = settings.vfc_hidden_fields || [];
			hiddenFields.forEach((fn) => {
				if (!knownFieldnames.has(fn)) {
					console.warn(
						`[VFC] _restoreState: unknown fieldname "${fn}" on ${dt} — skipping`
					);
					return;
				}
				frm.toggle_display(fn, false);
			});

			// 3. Update badge
			const allFields = this._getFormFields(frm);
			const SKIP = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading"];
			const renderable = allFields.filter((f) => !SKIP.includes(f.fieldtype));
			const visible = renderable.filter((f) => !hiddenFields.includes(f.fieldname)).length;
			const badge = document.getElementById(`vfc-badge-${dtId}`);
			if (badge) badge.textContent = visible;
		},

		/* ─────────────────────────────────────────────────────────
       _togglePanel
    ───────────────────────────────────────────────────────── */
		_togglePanel(frm, forceState) {
			const panel = frm._vfc_panel;
			if (!panel) return;
			const isOpen = panel.classList.contains("vfc-panel-open");
			const shouldOpen = forceState !== undefined ? forceState : !isOpen;

			let backdrop = document.getElementById("vfc-backdrop");
			if (!backdrop) {
				backdrop = document.createElement("div");
				backdrop.id = "vfc-backdrop";
				backdrop.className = "vfc-backdrop";
				document.body.appendChild(backdrop);
				backdrop.addEventListener("click", () => VFC._closeAll());
			}

			if (shouldOpen) {
				// Close any other open panels first
				VFC._closeAll();
				panel.classList.add("vfc-panel-open");
				backdrop.classList.add("vfc-backdrop-open");
				frm._vfc_btn?.classList.add("vfc-open");
				frm._vfc_panel_open = true;

				// Position panel in viewport center dynamically if not moved yet
				if (!panel.dataset.wasMoved) {
					panel.style.transform = "scale(1)";
					const width = panel.offsetWidth || 420;
					const height = panel.offsetHeight || 520;
					panel.style.left = `${(window.innerWidth - width) / 2}px`;
					panel.style.top = `${(window.innerHeight - height) / 2}px`;
				}
			} else {
				panel.classList.remove("vfc-panel-open");
				backdrop.classList.remove("vfc-backdrop-open");
				frm._vfc_btn?.classList.remove("vfc-open");
				frm._vfc_panel_open = false;
			}
		},

		_closeAll() {
			document.querySelectorAll(".vfc-panel.vfc-panel-open").forEach((p) => {
				p.classList.remove("vfc-panel-open");
			});
			document.querySelectorAll(".vfc-btn.vfc-open").forEach((b) => {
				b.classList.remove("vfc-open");
			});
			document.getElementById("vfc-backdrop")?.classList.remove("vfc-backdrop-open");
		},

		/* ─────────────────────────────────────────────────────────
       _getFormFields — returns frm.meta.fields array
    ───────────────────────────────────────────────────────── */
		_getFormFields(frm) {
			return (frm.meta?.fields || []).filter((f) => f.fieldname && f.label);
		},

		_countVisibleFields(frm) {
			const settings = loadUserSettings(frm.doctype);
			const hidden = settings.vfc_hidden_fields || [];
			const SKIP = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading"];
			const all = this._getFormFields(frm).filter((f) => !SKIP.includes(f.fieldtype));
			return all.filter((f) => !hidden.includes(f.fieldname)).length;
		},

		/* ─────────────────────────────────────────────────────────
       Sections Editor Tab Handlers
    ───────────────────────────────────────────────────────── */
		async _renderSectionsTab(frm, dtId) {
			const container = document.getElementById(`vfc-sec-list-${dtId}`);
			if (!container) return;

			container.innerHTML = `<div style="text-align:center;padding:20px;color:var(--ct-text-muted)">${__(
				"Loading sections..."
			)}</div>`;

			// Load SortableJS dynamically if not already present
			if (typeof Sortable === "undefined") {
				await frappe.require(
					"https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"
				);
			}

			// Fetch active profile or build default
			let profile = null;
			try {
				profile = window.VFCLayoutEngine
					? await window.VFCLayoutEngine._fetchProfile(frm.doctype)
					: null;
			} catch (err) {
				console.warn("[VFC] Error fetching profile:", err);
			}

			if (!profile || !profile.sections || !profile.sections.length) {
				const fallbackFields = this._getFormFields(frm).filter((f) => {
					const SKIP_TYPES = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading"];
					return !SKIP_TYPES.includes(f.fieldtype);
				});
				profile = {
					sections: [
						{
							id: "sec_default_1",
							label: "General Info",
							column_count: 2,
							sort_order: 1,
							visible: true,
							collapsible: false,
							collapsed_by_default: false,
							fields: fallbackFields.map((f, idx) => ({
								fieldname: f.fieldname,
								col: (idx % 2) + 1,
								sort_order: idx + 1,
								visible: true,
							})),
						},
					],
				};
			}

			// Filter out layout-only field types from profile sections
			const SKIP_TYPES = new Set(["Section Break", "Column Break", "Tab Break", "HTML", "Heading"]);
			const cleanSections = JSON.parse(JSON.stringify(profile.sections)).map((sec) => {
				sec.fields = (sec.fields || []).filter((f) => !SKIP_TYPES.has(
					(frm.meta?.fields || []).find((mf) => mf.fieldname === f.fieldname)?.fieldtype
				));
				return sec;
			});
			frm._vfc_temp_layout = cleanSections;
			this._appendUnassignedSection(frm, dtId, profile);
			this._renderSectionsListHTML(frm, dtId);
		},

		_appendUnassignedSection(frm, dtId, profile) {
			const SKIP_TYPES = new Set(["Section Break", "Column Break", "Tab Break", "HTML", "Heading"]);
			const assignedFieldnames = new Set();
			(frm._vfc_temp_layout || []).forEach((sec) => {
				(sec.fields || []).forEach((f) => {
					if (f.fieldname) assignedFieldnames.add(f.fieldname);
				});
			});

			const unassigned = (frm.meta?.fields || [])
				.filter((f) => f.fieldname && !assignedFieldnames.has(f.fieldname) && !SKIP_TYPES.has(f.fieldtype))
				.map((f, idx) => ({
					fieldname: f.fieldname,
					col: (idx % 2) + 1,
					sort_order: idx + 1,
					visible: true,
				}));

			if (!unassigned.length) {
				frm._vfc_unassigned_idx = -1;
				return;
			}

			const unassignedColCount = profile.unassigned_column_count || 2;

			// Store the unassigned policy for the save step
			frm._vfc_unassigned_policy = profile.unassigned_policy || "append";

			const unassignedSec = {
				id: "_unassigned",
				label: __("Unassigned Fields"),
				column_count: unassignedColCount,
				sort_order: (frm._vfc_temp_layout.length || 0) + 1,
				visible: true,
				collapsible: false,
				_unassigned: true,
				fields: unassigned,
			};

			frm._vfc_temp_layout.push(unassignedSec);
			frm._vfc_unassigned_idx = frm._vfc_temp_layout.length - 1;
		},

		_renderSectionsListHTML(frm, dtId) {
			const container = document.getElementById(`vfc-sec-list-${dtId}`);
			if (!container) return;

			const sections = frm._vfc_temp_layout || [];
			if (!sections.length) {
				container.innerHTML = `<div style="text-align:center;padding:20px;color:var(--ct-text-muted)">${__(
					"No sections defined."
				)}</div>`;
				return;
			}

			let html = "";
			sections.forEach((sec, sIdx) => {
				const totalFields = (sec.fields || []).length;
				const fieldsHtml = (sec.fields || [])
					.map((fld, fIdx) => {
						const first = fIdx === 0;
						const last = fIdx === totalFields - 1;
						return `
            <div class="vfc-sec-field-item" data-fieldname="${
				fld.fieldname
			}" style="display:flex;align-items:center;background:var(--ct-bg-3);border:1px solid var(--ct-border);padding:6px 8px;border-radius:4px;font-size:11px;cursor:grab;margin-bottom:4px;gap:6px">
              <span class="vfc-sort-handle" style="color:var(--ct-text-muted);cursor:grab">☰</span>
              <span class="vfc-arrow-controls" style="display:inline-flex;gap:2px">
                <button class="btn btn-default btn-xs" onclick="window._VFC._moveFieldUp('${frm.doctype}', ${sIdx}, '${fld.fieldname}')" ${first ? "disabled style='opacity:0.3'" : ""} style="padding:0 4px;font-size:10px;line-height:1.4" title="${__("Move Up")}">▲</button>
                <button class="btn btn-default btn-xs" onclick="window._VFC._moveFieldDown('${frm.doctype}', ${sIdx}, '${fld.fieldname}')" ${last ? "disabled style='opacity:0.3'" : ""} style="padding:0 4px;font-size:10px;line-height:1.4" title="${__("Move Down")}">▼</button>
              </span>
              <span style="font-weight:600;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${__(
					fld.fieldname
				)}</span>
              <select onchange="window._VFC._onFieldColChange(this, '${frm.doctype}', ${sIdx}, '${
							fld.fieldname
						}')" style="background:var(--ct-surface);border:1px solid var(--ct-border);border-radius:3px;font-size:9px;padding:1px 3px">
                <option value="1" ${fld.col == 1 ? "selected" : ""}>Col 1</option>
                <option value="2" ${fld.col == 2 ? "selected" : ""}>Col 2</option>
                <option value="3" ${fld.col == 3 ? "selected" : ""}>Col 3</option>
              </select>
            </div>
          `;
					})
					.join("");

				const totalSections = sections.length;
				const secFirst = sIdx === 0;
				const secLast = sIdx === totalSections - 1;

				const unassignedCls = sec._unassigned ? " vfc-sec-item-unassigned" : "";
				html += `
          <div class="vfc-sec-item${unassignedCls}" data-section-idx="${sIdx}" style="border:1px solid var(--ct-border);border-radius:6px;background:var(--ct-bg-elevated);padding:10px;display:flex;flex-direction:column;gap:8px">
            <div style="display:flex;align-items:center;gap:6px">
              <span class="vfc-sec-sort-handle" style="color:var(--ct-text-muted);cursor:grab;font-size:14px">☰</span>
              <span class="vfc-arrow-controls" style="display:inline-flex;gap:2px">
                <button class="btn btn-default btn-xs" onclick="window._VFC._moveSectionUp('${frm.doctype}', ${sIdx})" ${secFirst ? "disabled style='opacity:0.3'" : ""} style="padding:0 4px;font-size:10px;line-height:1.4" title="${__("Move Up")}">▲</button>
                <button class="btn btn-default btn-xs" onclick="window._VFC._moveSectionDown('${frm.doctype}', ${sIdx})" ${secLast ? "disabled style='opacity:0.3'" : ""} style="padding:0 4px;font-size:10px;line-height:1.4" title="${__("Move Down")}">▼</button>
              </span>
              <input type="text" value="${sec.label || ""}" placeholder="${__(
					"Section Name"
				)}" onchange="window._VFC._onSecLabelChange(this, '${
					frm.doctype
				}', ${sIdx})" style="font-size:12px;font-weight:700;background:transparent;border:none;border-bottom:1px dashed var(--ct-border);color:var(--ct-text);flex:1;padding:2px" />

              <select onchange="window._VFC._onSecColCountChange(this, '${
					frm.doctype
				}', ${sIdx})" style="background:var(--ct-surface);border:1px solid var(--ct-border);border-radius:3px;font-size:10px;padding:2px 4px">
                <option value="1" ${sec.column_count == 1 ? "selected" : ""}>1 Col</option>
                <option value="2" ${sec.column_count == 2 ? "selected" : ""}>2 Cols</option>
                <option value="3" ${sec.column_count == 3 ? "selected" : ""}>3 Cols</option>
              </select>

              <label style="display:inline-flex;align-items:center;font-size:10px;color:var(--ct-text-secondary);gap:2px;cursor:pointer;user-select:none;margin:0" title="${__(
					"Allow section to be collapsed"
				)}">
                <input type="checkbox" ${
					sec.collapsible ? "checked" : ""
				} onchange="window._VFC._onSecCollapsibleChange(this, '${
					frm.doctype
				}', ${sIdx})" style="width:12px;height:12px" />
                Colps
              </label>

              <label style="display:inline-flex;align-items:center;font-size:10px;color:var(--ct-text-secondary);gap:2px;cursor:pointer;user-select:none;margin:0" title="${__(
					"Collapse by default initially"
				)}">
                <input type="checkbox" ${
					sec.collapsed_by_default ? "checked" : ""
				} onchange="window._VFC._onSecCollapsedByDefaultChange(this, '${
					frm.doctype
				}', ${sIdx})" style="width:12px;height:12px" ${
					sec.collapsible ? "" : "disabled"
				} />
                Clpsd
              </label>

              <button class="btn btn-default btn-xs" onclick="window._VFC._deleteSection('${
					frm.doctype
				}', ${sIdx})" style="padding:2px 5px;color:var(--ct-danger);border-color:transparent;background:transparent" title="${__(
					"Delete Section"
				)}">✕</button>
            </div>

            <div class="vfc-sec-fields-list" data-section-idx="${sIdx}" style="min-height:30px;background:rgba(0,0,0,0.02);border:1px dashed var(--ct-border);border-radius:4px;padding:6px 6px 2px">
              ${
					fieldsHtml ||
					`<div style="text-align:center;padding:8px;font-size:10px;color:var(--ct-text-muted);font-style:italic">${__(
						"Drag fields here"
					)}</div>`
				}
            </div>
          </div>
        `;
			});

			// Store Sortable instances keyed by container for cleanup
			if (!window._vfc_sortables) window._vfc_sortables = new Map();
			const sortableKey = `vfc-sec-list-${dtId}`;
			if (window._vfc_sortables.has(sortableKey)) {
				window._vfc_sortables.get(sortableKey).forEach((s) => s.destroy());
			}
			const instances = [];

			container.innerHTML = html;

			// Initialize SortableJS
			if (typeof Sortable !== "undefined") {
				instances.push(new Sortable(container, {
					handle: ".vfc-sec-sort-handle",
					animation: 150,
					onEnd: (evt) => {
						const newOrder = [];
						container.querySelectorAll(".vfc-sec-item").forEach((el) => {
							const idx = parseInt(el.getAttribute("data-section-idx"), 10);
							newOrder.push(frm._vfc_temp_layout[idx]);
						});
						newOrder.forEach((sec, idx) => {
							sec.sort_order = idx + 1;
						});
						frm._vfc_temp_layout = newOrder;
						this._renderSectionsListHTML(frm, dtId);
					},
				}));

				container.querySelectorAll(".vfc-sec-fields-list").forEach((listEl) => {
					instances.push(new Sortable(listEl, {
						group: `vfc-fields-${dtId}`,
						handle: ".vfc-sort-handle",
						animation: 150,
						onEnd: (evt) => {
							const updatedLayout = [];
							container.querySelectorAll(".vfc-sec-item").forEach((secEl) => {
								const sIdx = parseInt(secEl.getAttribute("data-section-idx"), 10);
								const originalSec = frm._vfc_temp_layout[sIdx];
								const newFields = [];

								secEl
									.querySelectorAll(".vfc-sec-field-item")
									.forEach((fieldEl, fIdx) => {
										const fieldname = fieldEl.getAttribute("data-fieldname");
										let originalField = null;
										for (let s of frm._vfc_temp_layout) {
											let found = (s.fields || []).find(
												(f) => f.fieldname === fieldname
											);
											if (found) {
												originalField = found;
												break;
											}
										}
										newFields.push({
											fieldname: fieldname,
											col: originalField ? originalField.col : 1,
											sort_order: fIdx + 1,
											visible: true,
										});
									});

								originalSec.fields = newFields;
								updatedLayout.push(originalSec);
							});

							frm._vfc_temp_layout = updatedLayout;
							this._renderSectionsListHTML(frm, dtId);
						},
					}));
				});
			}

			if (instances.length) {
				window._vfc_sortables.set(sortableKey, instances);
			}
		},

		_onFieldColChange(select, doctype, sIdx, fieldname) {
			if (cur_frm && cur_frm.doctype === doctype && cur_frm._vfc_temp_layout) {
				const field = (cur_frm._vfc_temp_layout[sIdx].fields || []).find(
					(f) => f.fieldname === fieldname
				);
				if (field) {
					field.col = parseInt(select.value, 10);
				}
			}
		},

		_onSecLabelChange(input, doctype, sIdx) {
			if (cur_frm && cur_frm.doctype === doctype && cur_frm._vfc_temp_layout) {
				if (cur_frm._vfc_temp_layout[sIdx]._unassigned) return;
				cur_frm._vfc_temp_layout[sIdx].label = input.value;
			}
		},

		_onSecColCountChange(select, doctype, sIdx) {
			if (cur_frm && cur_frm.doctype === doctype && cur_frm._vfc_temp_layout) {
				cur_frm._vfc_temp_layout[sIdx].column_count = parseInt(select.value, 10);
			}
		},

		_onSecCollapsibleChange(checkbox, doctype, sIdx) {
			if (cur_frm && cur_frm.doctype === doctype && cur_frm._vfc_temp_layout) {
				cur_frm._vfc_temp_layout[sIdx].collapsible = checkbox.checked;
			}
		},

		_deleteSection(doctype, sIdx) {
			if (cur_frm && cur_frm.doctype === doctype && cur_frm._vfc_temp_layout) {
				if (cur_frm._vfc_temp_layout[sIdx]._unassigned) return;
				const deletedSec = cur_frm._vfc_temp_layout[sIdx];
				const fieldsToMove = deletedSec.fields || [];

				cur_frm._vfc_temp_layout.splice(sIdx, 1);

				if (fieldsToMove.length) {
					if (!cur_frm._vfc_temp_layout.length) {
						cur_frm._vfc_temp_layout.push({
							id: "sec_default_moved",
							label: "General Info",
							column_count: 2,
							sort_order: 1,
							visible: true,
							collapsible: false,
							collapsed_by_default: false,
							fields: [],
						});
					}
					cur_frm._vfc_temp_layout[0].fields = (
						cur_frm._vfc_temp_layout[0].fields || []
					).concat(fieldsToMove);
				}

				const dtId = doctype.replace(/\s/g, "-");
				this._renderSectionsListHTML(cur_frm, dtId);
			}
		},

		_addSectionPrompt(frm, dtId) {
			frappe.prompt(
				[
					{
						label: "Section Label",
						fieldname: "label",
						fieldtype: "Data",
						reqd: 1,
					},
					{
						label: "Columns",
						fieldname: "column_count",
						fieldtype: "Select",
						options: "1\n2\n3",
						default: "2",
					},
					{
						label: "Collapsible",
						fieldname: "collapsible",
						fieldtype: "Check",
						default: 0,
					},
					{
						label: "Collapsed by Default",
						fieldname: "collapsed_by_default",
						fieldtype: "Check",
						default: 0,
						depends_on: "eval:doc.collapsible",
					},
				],
				(values) => {
					const newSec = {
						id: "sec_" + Math.random().toString(36).substring(2, 9),
						label: values.label,
						column_count: parseInt(values.column_count, 10),
						sort_order: frm._vfc_temp_layout.length + 1,
						visible: true,
						collapsible: !!values.collapsible,
						collapsed_by_default: !!values.collapsed_by_default,
						fields: [],
					};
					frm._vfc_temp_layout.push(newSec);
					this._renderSectionsListHTML(frm, dtId);
				},
				__("Add New Section"),
				__("Add")
			);
		},

		_onSecCollapsedByDefaultChange(checkbox, doctype, sIdx) {
			if (cur_frm && cur_frm.doctype === doctype && cur_frm._vfc_temp_layout) {
				cur_frm._vfc_temp_layout[sIdx].collapsed_by_default = checkbox.checked;
			}
		},

		/* ─────────────────────────────────────────────────────────
        Field and Section move handlers (Phase 4 — touch arrow controls)
     ───────────────────────────────────────────────────────── */

		_moveFieldUp(doctype, sIdx, fieldname) {
			if (!cur_frm || cur_frm.doctype !== doctype || !cur_frm._vfc_temp_layout) return;
			const fields = cur_frm._vfc_temp_layout[sIdx].fields || [];
			const idx = fields.findIndex((f) => f.fieldname === fieldname);
			if (idx <= 0) return;
			[fields[idx - 1], fields[idx]] = [fields[idx], fields[idx - 1]];
			fields.forEach((f, i) => (f.sort_order = i + 1));
			this._renderSectionsListHTML(cur_frm, doctype.replace(/\s/g, "-"));
		},

		_moveFieldDown(doctype, sIdx, fieldname) {
			if (!cur_frm || cur_frm.doctype !== doctype || !cur_frm._vfc_temp_layout) return;
			const fields = cur_frm._vfc_temp_layout[sIdx].fields || [];
			const idx = fields.findIndex((f) => f.fieldname === fieldname);
			if (idx < 0 || idx >= fields.length - 1) return;
			[fields[idx], fields[idx + 1]] = [fields[idx + 1], fields[idx]];
			fields.forEach((f, i) => (f.sort_order = i + 1));
			this._renderSectionsListHTML(cur_frm, doctype.replace(/\s/g, "-"));
		},

		_moveSectionUp(doctype, sIdx) {
			if (!cur_frm || cur_frm.doctype !== doctype || !cur_frm._vfc_temp_layout) return;
			if (sIdx <= 0) return;
			const layout = cur_frm._vfc_temp_layout;
			[layout[sIdx - 1], layout[sIdx]] = [layout[sIdx], layout[sIdx - 1]];
			layout.forEach((s, i) => (s.sort_order = i + 1));
			this._renderSectionsListHTML(cur_frm, doctype.replace(/\s/g, "-"));
		},

		_moveSectionDown(doctype, sIdx) {
			if (!cur_frm || cur_frm.doctype !== doctype || !cur_frm._vfc_temp_layout) return;
			const layout = cur_frm._vfc_temp_layout;
			if (sIdx < 0 || sIdx >= layout.length - 1) return;
			[layout[sIdx], layout[sIdx + 1]] = [layout[sIdx + 1], layout[sIdx]];
			layout.forEach((s, i) => (s.sort_order = i + 1));
			this._renderSectionsListHTML(cur_frm, doctype.replace(/\s/g, "-"));
		},

		_makeDraggableAndResizable(panel) {
			const head = panel.querySelector(".vfc-panel-head");
			const handle = panel.querySelector(".vfc-resize-handle");

			// Draggable logic
			head.addEventListener("mousedown", (e) => {
				if (
					e.target.closest("button") ||
					e.target.closest("input") ||
					e.target.closest("select")
				)
					return;
				if (panel.classList.contains("vfc-panel-maximized")) return;
				e.preventDefault();

				panel.dataset.wasMoved = "true";
				panel.style.transition = "none"; // Disable transitions during drag

				const rect = panel.getBoundingClientRect();
				panel.style.transform = "scale(1)";
				panel.style.left = `${rect.left}px`;
				panel.style.top = `${rect.top}px`;

				const startX = e.clientX;
				const startY = e.clientY;
				const startLeft = rect.left;
				const startTop = rect.top;

				function onMouseMove(moveEvent) {
					const deltaX = moveEvent.clientX - startX;
					const deltaY = moveEvent.clientY - startY;
					panel.style.left = `${startLeft + deltaX}px`;
					panel.style.top = `${startTop + deltaY}px`;
				}

				function onMouseUp() {
					panel.style.transition = ""; // Restore transitions
					document.removeEventListener("mousemove", onMouseMove);
					document.removeEventListener("mouseup", onMouseUp);
				}

				document.addEventListener("mousemove", onMouseMove);
				document.addEventListener("mouseup", onMouseUp);
			});

			// Resizable logic
			handle.addEventListener("mousedown", (e) => {
				if (panel.classList.contains("vfc-panel-maximized")) return;
				e.preventDefault();
				e.stopPropagation();

				panel.dataset.wasMoved = "true";
				panel.style.transition = "none"; // Disable transitions during resize

				const rect = panel.getBoundingClientRect();
				panel.style.transform = "scale(1)";
				panel.style.left = `${rect.left}px`;
				panel.style.top = `${rect.top}px`;

				const startWidth = rect.width;
				const startHeight = rect.height;
				const startX = e.clientX;
				const startY = e.clientY;

				function onMouseMove(moveEvent) {
					const newWidth = Math.max(340, startWidth + (moveEvent.clientX - startX));
					const newHeight = Math.max(400, startHeight + (moveEvent.clientY - startY));
					panel.style.width = `${newWidth}px`;
					panel.style.height = `${newHeight}px`;
				}

				function onMouseUp() {
					panel.style.transition = ""; // Restore transitions
					document.removeEventListener("mousemove", onMouseMove);
					document.removeEventListener("mouseup", onMouseUp);
				}

				document.addEventListener("mousemove", onMouseMove);
				document.addEventListener("mouseup", onMouseUp);
			});
		},
	};

	/* ══════════════════════════════════════════════════════════════
     GLOBAL ATTACH HOOK — fires on EVERY form in the app
  ══════════════════════════════════════════════════════════════ */
	frappe.ui.form.on("*", {
		refresh(frm) {
			// Small delay ensures Frappe has fully rendered the page head
			setTimeout(() => {
				try {
					VFC.attach(frm);
				} catch (err) {
					console.warn("[VFC] attach error:", err);
				}
			}, 150);
		},
	});

	/* ══════════════════════════════════════════════════════════════
     EXPOSE — for inline event handlers (onclick="window._VFC...")
  ══════════════════════════════════════════════════════════════ */
	window._VFC = VFC;
	window.ViteFormConfig = VFC;
})();
