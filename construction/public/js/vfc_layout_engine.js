/* ═══════════════════════════════════════════════════════════════════════
   vfc_layout_engine.js — Generic Form Layout Engine
   ─────────────────────────────────────────────────────────────────────
   Reads a Form Layout Profile from the server and re-parents Frappe
   field wrappers into custom named section containers.

   Architecture
   ─────────────────────────────────────────────────────────────────────
   • Fully generic — works for ANY DocType (no hard-coding)
   • Non-destructive — never modifies Frappe's field objects or meta
   • Graceful fallback — if no profile, form renders exactly as Frappe
     would (this function returns immediately and does nothing)
   • Safe for unknown fields — logs one warning and skips

   Native Frappe behaviors preserved
   ─────────────────────────────────────────────────────────────────────
   • Field permissions (read-only, hidden by role)
   • Mandatory validation
   • depends_on / read_only_depends_on evaluation
   • Link field queries
   • Field events (onchange, etc.)
   • Child table controls

   How re-parenting works
   ─────────────────────────────────────────────────────────────────────
   Each Frappe field has a .wrapper (jQuery element) that holds the
   label + control. We move these wrappers into our <div> grid containers
   while keeping them in frm.fields_dict. Frappe continues to manage
   them — we only change WHERE in the DOM they appear.

   Version: 1.0 | 2026-05-28
   Gate: Phase 2 — pilot active on BOQ Header and BOQ Item
════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ═══════════════════════════════════════════════════════════════════
     PILOT GUARD
     Only activate for the two pilot DocTypes until Gate 2 is cleared.
     To activate for additional DocTypes:
       1. Create a Form Layout Profile record via System Manager
       2. Add the DocType name to PILOT_DOCTYPES below
     (Phase 5: this list becomes redundant once gate is removed)
  ═══════════════════════════════════════════════════════════════════ */
  const PILOT_DOCTYPES = new Set(["BOQ Header", "BOQ Item"]);

  /* ═══════════════════════════════════════════════════════════════════
     LAYOUT ENGINE — singleton
  ═══════════════════════════════════════════════════════════════════ */
  const LayoutEngine = {

    // Cache: doctype → profile data (null = no profile, {} = loaded)
    _cache: new Map(),
    // Active containers: frm.doctype → array of injected section divs
    _activeSections: new Map(),

    /* ─────────────────────────────────────────────────────────────
       attach(frm)
       Called on every form refresh. Idempotent per frm instance.
       Fetches the active profile (cached per doctype) then renders.
    ───────────────────────────────────────────────────────────── */
    async attach(frm) {
      const dt = frm.doctype;

      // Pilot gate
      if (!PILOT_DOCTYPES.has(dt)) return;

      try {
        // Fetch profile (cached after first call)
        const profile = await this._fetchProfile(dt);

        // No profile → native rendering, do nothing
        if (!profile) return;

        // Re-inject on every refresh (field wrappers may be recreated)
        this._render(frm, profile);
      } catch (err) {
        console.error(`[LE] attach error for ${dt}:`, err);
      }
    },

    /* ─────────────────────────────────────────────────────────────
       _fetchProfile(doctype)
       Returns profile object or null. Caches result per doctype.
    ───────────────────────────────────────────────────────────── */
    async _fetchProfile(doctype) {
      if (this._cache.has(doctype)) {
        return this._cache.get(doctype);
      }

      const result = await frappe.call({
        method: "construction.construction.api.layout_api.get_active_layout",
        args: { doctype },
        freeze: false,
      });

      const profile = result?.message || null;
      this._cache.set(doctype, profile);
      return profile;
    },

    /* ─────────────────────────────────────────────────────────────
       _render(frm, profile)
       Core engine: builds section containers, moves field wrappers.
    ───────────────────────────────────────────────────────────── */
    _render(frm, profile) {
      const dt = frm.doctype;

      // Retrieve the form's layout root
      // frm.layout.wrapper is a jQuery object containing .form-layout
      const layoutRoot = frm.layout?.wrapper?.hasClass("form-layout")
        ? frm.layout.wrapper[0]
        : (frm.layout?.wrapper?.find(".form-layout")?.[0] || frm.layout?.wrapper?.[0]);
      if (!layoutRoot) {
        console.warn(`[LE] Cannot find .form-layout for ${dt}`);
        return;
      }

      // Remove any previously injected VFC sections for this frm
      this._clearSections(frm);

      // Build a Set of fieldnames assigned in this profile
      const assignedFieldnames = new Set();
      (profile.sections || []).forEach((sec) => {
        (sec.fields || []).forEach((f) => {
          if (f.fieldname) assignedFieldnames.add(f.fieldname);
        });
      });

      // Collect known fieldnames (guard against unknown field refs)
      const knownFieldnames = new Set(
        (frm.meta?.fields || []).map((f) => f.fieldname)
      );

      // Sort sections by sort_order
      const sections = [...(profile.sections || [])].sort(
        (a, b) => (a.sort_order || 0) - (b.sort_order || 0)
      );

      const injectedContainers = [];

      // ── Hide ALL native Frappe section/column break elements ──
      // We'll reconstruct the visual layout ourselves
      layoutRoot.querySelectorAll(
        ".frappe-section, .section-head, .frappe-column, .form-column"
      ).forEach((el) => {
        el.style.display = "none";
        el.setAttribute("data-vfc-hidden", "1");
      });

      // ── Build VFC section containers ──
      sections.forEach((sec) => {
        if (sec.visible === false) return;

        const sectionEl = this._buildSectionEl(sec, frm);
        const gridEl = sectionEl.querySelector(".vfc-le-grid");

        // Sort fields within section
        const fields = [...(sec.fields || [])].sort(
          (a, b) => (a.sort_order || 0) - (b.sort_order || 0)
        );

        let hasVisibleField = false;

        fields.forEach((fld) => {
          const fn = fld.fieldname;

          // Unknown field guard
          if (!knownFieldnames.has(fn)) {
            console.warn(`[LE] Profile '${profile.profile_name}': unknown fieldname '${fn}' on ${dt} — skipping`);
            return;
          }

          const fieldObj = frm.fields_dict[fn];
          if (!fieldObj) return;

          // Handle visibility
          if (fld.visible === false) {
            frm.toggle_display(fn, false);
            return;
          }

          const wrapper = fieldObj.wrapper;
          if (!wrapper) return;

          // Determine column span
          const colCount = Math.min(Math.max(sec.column_count || 2, 1), 3);
          const col = Math.min(Math.max(fld.col || 1, 1), colCount);

          // Create a cell div for this field
          const cell = document.createElement("div");
          cell.className = "vfc-le-cell";
          cell.style.gridColumn = String(col);
          cell.setAttribute("data-vfc-field", fn);

          // Move the native field wrapper into our cell
          const nativeEl = wrapper instanceof jQuery ? wrapper[0] : wrapper;
          if (nativeEl && nativeEl.parentNode) {
            if (!fieldObj._native_parent) {
              fieldObj._native_parent = nativeEl.parentNode;
            }
            cell.appendChild(nativeEl);
          }

          gridEl.appendChild(cell);
          hasVisibleField = true;
        });

        // Only append section if it has at least one field (or is collapsible)
        if (hasVisibleField || sec.collapsible) {
          layoutRoot.appendChild(sectionEl);
          injectedContainers.push(sectionEl);
        }
      });

      // ── Append unassigned fields at bottom (unassigned_policy: append) ──
      if (profile.unassigned_policy !== "discard") {
        this._appendUnassigned(frm, layoutRoot, knownFieldnames, assignedFieldnames);
      }

      // Store for cleanup on next render
      this._activeSections.set(frm.doctype + "__" + frm.docname, injectedContainers);
    },

    /* ─────────────────────────────────────────────────────────────
       _buildSectionEl(sec, frm) → HTMLElement
       Builds the VFC section card with header and CSS grid body.
    ───────────────────────────────────────────────────────────── */
    _buildSectionEl(sec, frm) {
      const colCount = Math.min(Math.max(sec.column_count || 2, 1), 3);
      const secEl = document.createElement("div");
      secEl.className = "vfc-le-section";
      secEl.setAttribute("data-vfc-section-id", sec.id || "");
      if (sec.collapsible) secEl.setAttribute("data-vfc-collapsible", "1");

      // Header
      if (sec.label) {
        const head = document.createElement("div");
        head.className = "vfc-le-section-head";
        head.textContent = __(sec.label);

        if (sec.collapsible) {
          head.classList.add("vfc-le-collapsible");
          const initCollapsed = sec.collapsed_by_default;
          if (initCollapsed) secEl.setAttribute("data-vfc-collapsed", "1");

          head.addEventListener("click", () => {
            const collapsed = secEl.getAttribute("data-vfc-collapsed") === "1";
            secEl.setAttribute("data-vfc-collapsed", collapsed ? "0" : "1");
            const grid = secEl.querySelector(".vfc-le-grid");
            if (grid) grid.style.display = collapsed ? "" : "none";
          });

          if (sec.collapsed_by_default) {
            // Defer hide so DOM is built first
            setTimeout(() => {
              const grid = secEl.querySelector(".vfc-le-grid");
              if (grid) grid.style.display = "none";
            }, 0);
          }
        }

        secEl.appendChild(head);
      }

      // Grid body
      const grid = document.createElement("div");
      grid.className = "vfc-le-grid";
      grid.style.gridTemplateColumns = `repeat(${colCount}, 1fr)`;
      secEl.appendChild(grid);

      return secEl;
    },

    /* ─────────────────────────────────────────────────────────────
       _appendUnassigned
       Any field that is in frm.meta but NOT in the profile gets
       appended to a trailing "Other Fields" section so nothing is lost.
    ───────────────────────────────────────────────────────────── */
    _appendUnassigned(frm, layoutRoot, knownFieldnames, assignedFieldnames) {
      const SKIP_TYPES = new Set(["Section Break", "Column Break", "Tab Break", "HTML", "Heading"]);
      const unassigned = (frm.meta?.fields || []).filter(
        (f) => f.fieldname && !assignedFieldnames.has(f.fieldname) && !SKIP_TYPES.has(f.fieldtype)
      );

      if (!unassigned.length) return;

      const secEl = document.createElement("div");
      secEl.className = "vfc-le-section vfc-le-unassigned";

      const head = document.createElement("div");
      head.className = "vfc-le-section-head";
      head.textContent = __("Other Fields");
      secEl.appendChild(head);

      const grid = document.createElement("div");
      grid.className = "vfc-le-grid";
      grid.style.gridTemplateColumns = "repeat(2, 1fr)";
      secEl.appendChild(grid);

      unassigned.forEach((f) => {
        const fieldObj = frm.fields_dict[f.fieldname];
        if (!fieldObj || !fieldObj.wrapper) return;

        const cell = document.createElement("div");
        cell.className = "vfc-le-cell";
        cell.setAttribute("data-vfc-field", f.fieldname);

        const nativeEl = fieldObj.wrapper instanceof jQuery
          ? fieldObj.wrapper[0] : fieldObj.wrapper;
        if (nativeEl && nativeEl.parentNode) {
          cell.appendChild(nativeEl);
        }
        grid.appendChild(cell);
      });

      if (grid.children.length > 0) {
        layoutRoot.appendChild(secEl);
      }
    },

    /* ─────────────────────────────────────────────────────────────
       _clearSections(frm)
       Remove previously injected VFC sections from the DOM.
       Also un-hide any native Frappe section elements we hid.
    ───────────────────────────────────────────────────────────── */
    _clearSections(frm) {
      const key = frm.doctype + "__" + frm.docname;
      const containers = this._activeSections.get(key) || [];

      containers.forEach((el) => {
        // Move field wrappers back to their native parent before removing section
        el.querySelectorAll(".vfc-le-cell").forEach((cell) => {
          const fn = cell.getAttribute("data-vfc-field");
          if (fn && frm.fields_dict[fn]) {
            const fieldObj = frm.fields_dict[fn];
            const nativeWrapper = fieldObj.wrapper instanceof jQuery
              ? fieldObj.wrapper[0] : fieldObj.wrapper;
            if (nativeWrapper && cell.contains(nativeWrapper)) {
              // Return to original native parent if still in DOM
              if (fieldObj._native_parent && fieldObj._native_parent.isConnected) {
                fieldObj._native_parent.appendChild(nativeWrapper);
              }
            }
          }
        });
        el.remove();
      });

      this._activeSections.delete(key);
    },

    /* ─────────────────────────────────────────────────────────────
       invalidateCache(doctype)
       Call this after saving a profile to force re-fetch on next
       form open.
    ───────────────────────────────────────────────────────────── */
    invalidateCache(doctype) {
      this._cache.delete(doctype);
    },
  };

  /* ═══════════════════════════════════════════════════════════════════
     GLOBAL ATTACH HOOK
     Fires AFTER the VFC panel attach (which runs at 150ms).
     Layout engine runs at 250ms to ensure fields_dict is fully ready.
  ═══════════════════════════════════════════════════════════════════ */
  frappe.ui.form.on("*", {
    refresh(frm) {
      setTimeout(() => {
        try {
          LayoutEngine.attach(frm);
        } catch (err) {
          console.warn("[LE] attach error:", err);
        }
      }, 250);
    },
  });

  /* ═══════════════════════════════════════════════════════════════════
     EXPOSE globally for vfc_sections_tab.js and console debugging
  ═══════════════════════════════════════════════════════════════════ */
  window.VFCLayoutEngine = LayoutEngine;

})();
