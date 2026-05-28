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
          "project", "project_name", "boq_type", "status", "title", "version",
          "total_contract_value", "total_estimated_value", "total_budgeted_cost",
          "locked_by", "locked_date",
        ],
      },
      {
        key: "Manager",
        name: __("Manager View"),
        desc: __("Summary: Project, Status, Totals, Lock info"),
        fields: [
          "project", "status", "title", "version",
          "total_contract_value", "total_estimated_value",
          "total_budgeted_cost", "locked_by", "locked_date",
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
          "project", "title", "status",
          "total_contract_value", "total_estimated_value", "total_budgeted_cost",
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
        fields: ["boq_header", "structure", "item_type", "quantity", "unit", "factor", "has_stages"],
      },
      {
        key: "Accountant",
        name: __("Accountant View"),
        desc: __("Pricing and totals — hides engineering fields"),
        // Verified against boq_item.json 2026-05-28
        fields: [
          "boq_header", "unit", "quantity",
          "contract_unit_price", "factor", "line_total",
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
        fields: ["boq_item", "boq_header", "project", "stage_name", "stage_status", "percent_complete"],
      },
    ],
  };

  /* ══════════════════════════════════════════════════════════════
     SVG ICONS (inline — no external dependency)
  ══════════════════════════════════════════════════════════════ */
  const ICON_GRID = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="1" y="1" width="6" height="6" rx="1.5"/><rect x="9" y="1" width="6" height="6" rx="1.5"/><rect x="1" y="9" width="6" height="6" rx="1.5"/><rect x="9" y="9" width="6" height="6" rx="1.5"/></svg>`;
  const ICON_EYE  = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="8" cy="8" r="3"/><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z"/></svg>`;
  const ICON_COL  = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="1" width="14" height="14" rx="2"/><line x1="8" y1="1" x2="8" y2="15"/></svg>`;
  const ICON_PRE  = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 4h12M4 8h8M6 12h4"/></svg>`;
  const ICON_X    = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="2" x2="14" y2="14"/><line x1="14" y1="2" x2="2" y2="14"/></svg>`;

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
      const pageHead = frm.page.page_actions?.[0] || frm.page.$page?.find(".page-actions")?.[0];

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
        <div class="vfc-panel-head">
          <div class="vfc-panel-icon">${ICON_GRID}</div>
          <div>
            <div class="vfc-panel-title">${__("Form Config")}</div>
            <div class="vfc-panel-sub">${__(dt)}</div>
          </div>
          <button class="vfc-close-btn" data-vfc-close="${panelId}" title="${__("Close")}">${ICON_X}</button>
        </div>

        <!-- Tabs -->
        <div class="vfc-tabs">
          <div class="vfc-tab vfc-tab-active" data-vfc-tab="layout" data-panel="${panelId}">
            ${ICON_COL} ${__("Layout")}
          </div>
          <div class="vfc-tab" data-vfc-tab="fields" data-panel="${panelId}">
            ${ICON_EYE} ${__("Fields")}
          </div>
          ${hasPresets ? `
          <div class="vfc-tab" data-vfc-tab="presets" data-panel="${panelId}">
            ${ICON_PRE} ${__("Presets")}
          </div>` : ""}
        </div>

        <!-- Body -->
        <div class="vfc-body">

          <!-- Tab: Layout -->
          <div class="vfc-tab-pane" data-vfc-pane="layout" style="display:block">
            <div style="margin-bottom:16px">
              <div class="vfc-section-title" style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:10px">
                ${ICON_COL} ${__("Column Density")}
              </div>
              <div class="vfc-density-seg" data-panel="${panelId}">
                <div class="vfc-den-opt" data-den="1" title="${__("1 Column — stacked, easy reading")}">
                  <svg width="28" height="22" viewBox="0 0 28 22"><rect x="2" y="2" width="24" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="9" width="24" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="16" width="24" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>
                  ${__("1 Column")}
                </div>
                <div class="vfc-den-opt" data-den="2" title="${__("2 Columns — balanced default")}">
                  <svg width="28" height="22" viewBox="0 0 28 22"><rect x="2" y="2" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="15" y="2" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="9" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="15" y="9" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="2" y="16" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/><rect x="15" y="16" width="11" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>
                  ${__("2 Columns")}
                </div>
                <div class="vfc-den-opt" data-den="3" title="${__("3 Columns — dense, wide screens")}">
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
              <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:8px">${__("Preview")}</div>
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

          <!-- Tab: Presets -->
          ${hasPresets ? `
          <div class="vfc-tab-pane" data-vfc-pane="presets" style="display:none">
            <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ct-text-muted);margin-bottom:8px">
              ${ICON_PRE} ${__("Layout Presets")}
            </div>
            <div style="font-size:10px;color:var(--ct-text-muted);margin-bottom:10px;line-height:1.6">
              ${__("Select a preset, then click Apply & Save. Synced across devices.")}
            </div>
            <div id="vfc-pre-list-${dtId}"></div>
          </div>` : ""}

        </div><!-- /vfc-body -->

        <!-- Footer -->
        <div class="vfc-foot">
          <span class="vfc-foot-hint">${__("Saved via user settings")}</span>
          <button class="btn btn-default btn-sm" data-vfc-close="${panelId}">${__("Close")}</button>
          <button class="btn btn-primary btn-sm" data-vfc-apply="${dtId}">${__("Apply & Save")}</button>
        </div>
      `;

      document.body.appendChild(panel);
      frm._vfc_panel = panel;

      // Wire up events
      this._wirePanel(frm, panel, dtId, fields);
    },

    /* ─────────────────────────────────────────────────────────
       _wirePanel — attach all event listeners to the panel
    ───────────────────────────────────────────────────────── */
    _wirePanel(frm, panel, dtId, fields) {
      const dt = frm.doctype;

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
      panel.querySelectorAll(".vfc-tab").forEach((t) => t.classList.remove("vfc-tab-active"));
      panel.querySelectorAll(".vfc-tab-pane").forEach((p) => (p.style.display = "none"));
      panel.querySelector(`[data-vfc-tab="${name}"]`)?.classList.add("vfc-tab-active");
      panel.querySelector(`[data-vfc-pane="${name}"]`).style.display = "block";
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
      const knownFieldnames = new Set(
        (frm.meta?.fields || []).map((f) => f.fieldname)
      );

      // Unknown-field guard: warn once per unknown field, then skip
      hiddenFields.forEach((fn) => {
        if (!knownFieldnames.has(fn)) {
          console.warn(`[VFC] _renderFieldList: unknown fieldname "${fn}" on ${frm.doctype} — skipping`);
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
      const visible = optional.filter((f) => !hiddenFields.includes(f.fieldname)).length + required.length;
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
      const visibleCount = Array.from(allChecks).filter((c) => c.checked && !c.disabled).length;
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
      panel.querySelectorAll(".vfc-pre-item").forEach((i) => i.classList.remove("vfc-pre-active"));
      el.classList.add("vfc-pre-active");

      // Preview in fields tab: update checkboxes
      const key = el.getAttribute("data-preset-key");
      const preset = PRESET_REGISTRY[doctype]?.find((p) => p.key === key);
      if (!preset) return;

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
        opt.classList.toggle("vfc-den-active", parseInt(opt.getAttribute("data-den"), 10) === n);
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

      if (!quiet) {
        frappe.show_alert({ message: __("Column density set to {0}", [n]), indicator: "blue" }, 2);
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
      const knownFieldnames = new Set(
        (frm.meta?.fields || []).map((f) => f.fieldname)
      );

      // 1. Restore density
      const den = loadDensity(dt);
      this._applyDensity(frm, den, true);

      // 2. Restore field visibility (unknown-field guard: skip + single warn)
      const settings = loadUserSettings(dt);
      const hiddenFields = settings.vfc_hidden_fields || [];
      hiddenFields.forEach((fn) => {
        if (!knownFieldnames.has(fn)) {
          console.warn(`[VFC] _restoreState: unknown fieldname "${fn}" on ${dt} — skipping`);
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
      return (frm.meta?.fields || []).filter(
        (f) => f.fieldname && f.label
      );
    },

    _countVisibleFields(frm) {
      const settings = loadUserSettings(frm.doctype);
      const hidden = settings.vfc_hidden_fields || [];
      const SKIP = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading"];
      const all = this._getFormFields(frm).filter((f) => !SKIP.includes(f.fieldtype));
      return all.filter((f) => !hidden.includes(f.fieldname)).length;
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
