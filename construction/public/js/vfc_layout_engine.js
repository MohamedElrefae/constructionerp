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

   Version: 1.20 | 2026-05-28
   Gate: Phase 2 — pilot active on BOQ Header and BOQ Item
════════════════════════════════════════════════════════════════════════ */

(function () {
	"use strict";

	/* ═══════════════════════════════════════════════════════════════════
     PILOT GUARD
     Phase 3: expanded to all construction DocTypes. Without a Form
     Layout Profile record, the engine is a no-op (graceful fallback).
     The engine works on flat-layout DocTypes. Tabbed DocTypes (those
     with Tab Break fields) are automatically skipped regardless of
     PILOT_DOCTYPES — this is a safety net.
  ═══════════════════════════════════════════════════════════════════ */
	const PILOT_DOCTYPES = new Set([
		"BOQ Header",
		"BOQ Item",
		"BOQ Item Stage",
		"BOQ Structure",
		"User Scope Context",
		"Construction Theme",
		"Modern Theme Settings",
		"User Desk Theme",
	]);

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
			console.log(`[LE] attach() triggered for: ${frm.doctype}`);
			const dt = frm.doctype;

			const layoutRoot = this._getLayoutRoot(frm);

			// Non-default density → render with density profile (bypasses PILOT/tab gates)
			if (layoutRoot) {
				const denClass = [...layoutRoot.classList].find((c) => /^vfc-density-\d+$/.test(c));
				if (denClass) {
					const density = parseInt(denClass.split("-").pop(), 10);
					if (density !== 2) {
						console.log(`[LE] Non-default density (${density}) — density rendering.`);
						this.renderWithDensity(frm, density);
						return;
					}
				}
			}

			// Pilot gate — only known flat-layout DocTypes
			if (!PILOT_DOCTYPES.has(dt)) {
				console.log(`[LE] ${dt} not in PILOT_DOCTYPES, skipping.`);
				return;
			}

			// Tab detection — DocTypes with Tab Break fields use Frappe's native tab
			// layout which the VFC engine would destroy. Skip them as a safety net.
			const hasTabs = (frm.meta?.fields || []).some((f) => f.fieldtype === "Tab Break");
			if (hasTabs) {
				console.log(`[LE] ${dt} has Tab Break fields (tabbed layout) — VFC engine skipped.`);
				return;
			}

			const key = frm.doctype + "__" + frm.docname;
			console.log(`[LE] Processing key: ${key}`);
			if (!this._retryTimers) this._retryTimers = new Map();
			if (!this._retryCounts) this._retryCounts = new Map();
			if (!this._attachTokens) this._attachTokens = new Map();
			const token = (this._attachTokens.get(key) || 0) + 1;
			this._attachTokens.set(key, token);

			// Clear any existing retry timers for this form key
			if (this._retryTimers.has(key)) {
				clearTimeout(this._retryTimers.get(key));
				this._retryTimers.delete(key);
			}

			try {
				// Fetch profile (cached after first call)
				console.log(`[LE] Fetching profile for ${dt}...`);
				const profile = await this._fetchProfile(dt);
				console.log(`[LE] Profile fetched for ${dt}:`, profile);

				if (this._attachTokens.get(key) !== token) {
					console.log(`[LE] Stale attach skipped for ${key}.`);
					return;
				}

				// No profile → native rendering, do nothing
				if (!profile) {
					console.log(`[LE] No profile found for ${dt}. Aborting VFC layout.`);
					return;
				}

				if (!layoutRoot || !layoutRoot.isConnected) {
					const retries = this._retryCounts.get(key) || 0;
					if (retries < 20) {
						this._retryCounts.set(key, retries + 1);
						console.log(
							`[LE] layoutRoot not found for ${key}. Scheduling retry ${
								retries + 1
							}/20 in 250ms...`
						);
						const timer = setTimeout(() => {
							this.attach(frm);
						}, 250);
						this._retryTimers.set(key, timer);
					} else {
						console.warn(
							`[LE] Retry limit reached. Could not find layoutRoot for ${key}.`
						);
						this._retryCounts.delete(key);
					}
					return;
				}

				// Re-inject on every refresh (field wrappers may be recreated)
				this._render(frm, profile, layoutRoot);
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
		_render(frm, profile, layoutRoot) {
			const dt = frm.doctype;

			// Remove any previously injected VFC sections for this frm
			this._clearSections(frm);

			// Mark form as VFC-active so density CSS only applies here
			layoutRoot.classList.add("vfc-active");

			// Collect known fieldnames (guard against unknown field refs)
			const knownFieldnames = new Set((frm.meta?.fields || []).map((f) => f.fieldname));

			// Build type map for O(1) fieldtype lookup
			const metaFieldTypeMap = {};
			const SKIP_TYPES = new Set(["Section Break", "Column Break", "Tab Break", "HTML", "Heading"]);
			(frm.meta?.fields || []).forEach((mf) => {
				if (mf.fieldname) metaFieldTypeMap[mf.fieldname] = mf.fieldtype;
			});

			// Build a Set of fieldnames assigned in this profile (excluding layout-only types)
			const assignedFieldnames = new Set();
			const profileHiddenFieldnames = new Set();
			(profile.sections || []).forEach((sec) => {
				(sec.fields || []).forEach((f) => {
					if (!f.fieldname) return;
					if (SKIP_TYPES.has(metaFieldTypeMap[f.fieldname])) return;
					assignedFieldnames.add(f.fieldname);
					if (f.visible === false) profileHiddenFieldnames.add(f.fieldname);
				});
			});

			// Sort sections by sort_order
			const sections = [...(profile.sections || [])].sort(
				(a, b) => (a.sort_order || 0) - (b.sort_order || 0)
			);

			const injectedContainers = [];

			// ── Hide ALL native Frappe section/column break elements ──
			// We'll reconstruct the visual layout ourselves.
			this._hideNativeLayoutShells(layoutRoot);

			// Determine effective column count from density override (if set)
			const densityOverride = layoutRoot.classList.contains("vfc-density-1") ? 1
				: layoutRoot.classList.contains("vfc-density-3") ? 3
				: layoutRoot.classList.contains("vfc-density-2") ? 2 : 0;

			// ── Build VFC section containers ──
			sections.forEach((sec) => {
				if (sec.visible === false) return;

				const effectiveColCount = densityOverride || Math.min(Math.max(sec.column_count || 2, 1), 3);
				const sectionEl = this._buildSectionEl(sec, frm, effectiveColCount);
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
						console.warn(
							`[LE] Profile '${profile.profile_name}': unknown fieldname '${fn}' on ${dt} — skipping`
						);
						return;
					}

					// Skip layout-only field types (breaks, tabs, HTML, headings)
					if (SKIP_TYPES.has(metaFieldTypeMap[fn])) return;

					const fieldObj = frm.fields_dict[fn];
					if (!fieldObj) {
						console.log(`[LE] FieldObj not found for ${fn}`);
						return;
					}

					// Handle profile-level visibility
					if (fld.visible === false) {
						frm.toggle_display(fn, false);
						return;
					}

					// Handle runtime visibility (user settings, permissions, depends_on)
					if (fieldObj.df && (fieldObj.df.hidden || fieldObj.df.invisible)) {
						console.log(`[LE] Skipping hidden field ${fn} (df.hidden=${fieldObj.df.hidden}, df.invisible=${fieldObj.df.invisible})`);
						return;
					}

					const wrapper = fieldObj.wrapper;
					if (!wrapper) {
						console.log(`[LE] Wrapper missing for ${fn}`);
						return;
					}

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
						this._restoreVisibleFieldWrapper(nativeEl);
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
				this._appendUnassigned(frm, layoutRoot, knownFieldnames, assignedFieldnames, profile);
			}

			// Store for cleanup on next render
			this._activeSections.set(frm.doctype + "__" + frm.docname, injectedContainers);

			// Setup MutationObserver to watch for field wrappers being pulled back by Frappe
			this._setupObserver(frm, layoutRoot, profile);

			const key = frm.doctype + "__" + frm.docname;
			const state = { assignedFieldnames, profileHiddenFieldnames };
			this._verifyAndRetry(frm, state, "immediate");
			this._scheduleValidationPasses(frm, state);
		},

		_getLayoutRoot(frm) {
			const candidates = [];
			const addCandidate = (el) => {
				if (el && !candidates.includes(el)) candidates.push(el);
			};

			frm.wrapper?.find?.(".form-layout")?.each((_, el) => addCandidate(el));
			if (frm.layout?.wrapper?.hasClass?.("form-layout")) {
				addCandidate(frm.layout.wrapper[0]);
			}
			frm.layout?.wrapper?.find?.(".form-layout")?.each((_, el) => addCandidate(el));
			addCandidate(frm.layout?.wrapper?.[0]);

			return candidates.find((el) => el.isConnected) || candidates[0] || null;
		},

		_getObserverRoot(frm, layoutRoot) {
			return frm.wrapper?.[0] || frm.page?.main?.[0] || layoutRoot;
		},

		_hideNativeLayoutShells(layoutRoot) {
			if (!layoutRoot) return 0;

			let count = 0;
			layoutRoot
				.querySelectorAll(
					".form-section, .frappe-section, .section-head, .section-body, .frappe-column, .form-column"
				)
				.forEach((el) => {
					if (el.closest(".vfc-le-section")) return;
					el.style.setProperty("display", "none", "important");
					el.setAttribute("data-vfc-hidden", "1");
					count += 1;
				});
			return count;
		},

		_clearValidationTimers(key) {
			if (!this._validationTimers) this._validationTimers = new Map();
			const timers = this._validationTimers.get(key) || [];
			timers.forEach((timer) => clearTimeout(timer));
			this._validationTimers.delete(key);
		},

		_scheduleValidationPasses(frm, state) {
			const key = frm.doctype + "__" + frm.docname;
			this._clearValidationTimers(key);

			const timers = [300, 750, 1500, 3000].map((delay) =>
				setTimeout(() => {
					this._verifyAndRetry(frm, state, `delayed-${delay}`);
				}, delay)
			);
			this._validationTimers.set(key, timers);
		},

		_verifyAndRetry(frm, state, phase) {
			const key = frm.doctype + "__" + frm.docname;
			if (!this._retryTimers) this._retryTimers = new Map();
			if (!this._retryCounts) this._retryCounts = new Map();

			if (this._retryTimers.has(key)) {
				clearTimeout(this._retryTimers.get(key));
				this._retryTimers.delete(key);
			}

			const layoutRoot = this._getLayoutRoot(frm);
			const hiddenNativeCount = this._hideNativeLayoutShells(layoutRoot);
			const missingFields = this._hasMissingFields(frm, state, phase);
			const visibleNativeCount = this._countVisibleNativeLayoutShells(layoutRoot);
			const hiddenEmptySectionCount = this._hideEmptyCustomSections(layoutRoot);
			const sectionSummary = this._getSectionSummary(layoutRoot);
			console.log(`[LE] Verification ${phase} complete. missingFields=${missingFields}`);
			if (hiddenNativeCount || visibleNativeCount) {
				console.log(
					`[LE] Verification ${phase}: hiddenNativeShells=${hiddenNativeCount}, visibleNativeShells=${visibleNativeCount}`
				);
			}
			if (hiddenEmptySectionCount) {
				console.log(
					`[LE] Verification ${phase}: hiddenEmptySections=${hiddenEmptySectionCount}`
				);
			}
			console.log(`[LE] Verification ${phase}: sections=${sectionSummary}`);

			if (missingFields) {
				const retries = this._retryCounts.get(key) || 0;
				if (retries < 20) {
					this._retryCounts.set(key, retries + 1);
					console.log(
						`[LE] Missing field wrappers detected for ${key}. Scheduling retry ${
							retries + 1
						}/20 in 250ms...`
					);
					const timer = setTimeout(() => {
						this.attach(frm);
					}, 250);
					this._retryTimers.set(key, timer);
				} else {
					console.warn(
						`[LE] Retry limit reached for ${key}. Some field wrappers could not be attached.`
					);
					this._retryCounts.delete(key);
				}
			} else if (phase === "delayed-3000") {
				this._retryCounts.delete(key);
				this._clearValidationTimers(key);
			}
		},

		_hasMissingFields(frm, state, phase) {
			const layoutRoot = this._getLayoutRoot(frm);
			if (!layoutRoot || !layoutRoot.isConnected) {
				console.log(`[LE] Verification ${phase}: current layoutRoot missing or detached`);
				return true;
			}

			for (const fn of state.assignedFieldnames) {
				const fieldObj = frm.fields_dict[fn];
				if (!fieldObj) continue;

				if (fieldObj.df && (fieldObj.df.hidden || fieldObj.df.invisible)) continue;
				if (state.profileHiddenFieldnames.has(fn)) continue;

				const wrapper = fieldObj.wrapper;
				if (!wrapper) {
					console.log(`[LE] Verification ${phase}: Wrapper missing for ${fn}`);
					return true;
				}

				const nativeEl = wrapper instanceof jQuery ? wrapper[0] : wrapper;
				if (!nativeEl) {
					console.log(`[LE] Verification ${phase}: nativeEl is falsy for ${fn}`);
					return true;
				}
				if (!nativeEl.isConnected) {
					console.log(
						`[LE] Verification ${phase}: nativeEl not connected to DOM for ${fn}`
					);
					return true;
				}

				const cell = nativeEl.parentNode;
				if (!cell?.classList?.contains("vfc-le-cell")) {
					console.log(
						`[LE] Verification ${phase}: nativeEl parent is NOT .vfc-le-cell for ${fn}`
					);
					return true;
				}

				const section = cell.closest(".vfc-le-section");
				if (!section || !layoutRoot.contains(section)) {
					console.log(
						`[LE] Verification ${phase}: ${fn} is not inside the current VFC section tree`
					);
					return true;
				}

				if (nativeEl.closest("[data-vfc-hidden='1']")) {
					console.log(
						`[LE] Verification ${phase}: ${fn} is inside a hidden native Frappe container`
					);
					return true;
				}

				const style = window.getComputedStyle(nativeEl);
				const rect = nativeEl.getBoundingClientRect();
				if (
					style.display === "none" ||
					style.visibility === "hidden" ||
					Number(style.opacity) === 0 ||
					rect.height < 2 ||
					rect.width < 2
				) {
					console.log(
						`[LE] Verification ${phase}: ${fn} is currently not painted. display=${
							style.display
						}, visibility=${style.visibility}, opacity=${
							style.opacity
						}, rect=${Math.round(rect.width)}x${Math.round(rect.height)}`
					);
				}
			}

			return false;
		},

		_countVisibleNativeLayoutShells(layoutRoot) {
			if (!layoutRoot) return 0;

			let count = 0;
			layoutRoot
				.querySelectorAll(
					".form-section, .frappe-section, .section-head, .section-body, .frappe-column, .form-column"
				)
				.forEach((el) => {
					if (el.closest(".vfc-le-section")) return;
					const style = window.getComputedStyle(el);
					const rect = el.getBoundingClientRect();
					if (
						style.display !== "none" &&
						style.visibility !== "hidden" &&
						rect.width > 1 &&
						rect.height > 1
					) {
						count += 1;
					}
				});
			return count;
		},

		_getSectionSummary(layoutRoot) {
			if (!layoutRoot) return "no-layout-root";

			return [...layoutRoot.querySelectorAll(".vfc-le-section")]
				.map((section) => {
					const label =
						section.querySelector(".vfc-le-section-head")?.textContent?.trim() ||
						"(no label)";
					const cells = [...section.querySelectorAll(".vfc-le-cell")];
					const managed = cells.filter((cell) =>
						cell.querySelector("[data-vfc-managed='1']")
					).length;
					const painted = cells.filter((cell) => {
						const field = cell.querySelector("[data-vfc-managed='1']");
						if (!field) return false;
						const style = window.getComputedStyle(field);
						const rect = field.getBoundingClientRect();
						return (
							style.display !== "none" &&
							style.visibility !== "hidden" &&
							Number(style.opacity) !== 0 &&
							rect.width > 1 &&
							rect.height > 1
						);
					}).length;
					return `${label}:${painted}/${managed}/${cells.length}`;
				})
				.join(", ");
		},

		_hideEmptyCustomSections(layoutRoot) {
			if (!layoutRoot) return 0;

			let hidden = 0;
			layoutRoot.querySelectorAll(".vfc-le-section").forEach((section) => {
				const cells = [...section.querySelectorAll(".vfc-le-cell")];
				const managed = cells.filter((cell) =>
					cell.querySelector("[data-vfc-managed='1']")
				).length;
				const painted = cells.filter((cell) => {
					const field = cell.querySelector("[data-vfc-managed='1']");
					if (!field) return false;
					const style = window.getComputedStyle(field);
					const rect = field.getBoundingClientRect();
					return (
						style.display !== "none" &&
						style.visibility !== "hidden" &&
						Number(style.opacity) !== 0 &&
						rect.width > 1 &&
						rect.height > 1
					);
				}).length;

				if (managed > 0 && painted === 0) {
					section.setAttribute("data-vfc-empty", "1");
					section.style.setProperty("display", "none", "important");
					hidden += 1;
				} else {
					section.removeAttribute("data-vfc-empty");
					section.style.removeProperty("display");
				}
			});
			return hidden;
		},

		_restoreVisibleFieldWrapper(nativeEl) {
			if (!nativeEl) return;

			nativeEl.classList.remove("hide-control", "hidden", "d-none");
			nativeEl.removeAttribute("hidden");
			nativeEl.setAttribute("data-vfc-managed", "1");
			nativeEl.style.setProperty("display", "block");
			nativeEl.style.setProperty("visibility", "visible", "important");
			nativeEl.style.setProperty("opacity", "1", "important");
			nativeEl.style.removeProperty("height");
			nativeEl.style.removeProperty("max-height");

			nativeEl
				.querySelectorAll(
					".control-label, .control-input-wrapper, .control-value, .control-input"
				)
				.forEach((el) => {
					el.classList.remove("hide-control", "hidden", "d-none");
					el.removeAttribute("hidden");
					el.style.setProperty("visibility", "visible", "important");
					el.style.setProperty("opacity", "1", "important");
				});
		},

		/* ─────────────────────────────────────────────────────────────
        _buildSectionEl(sec, frm, colCount) → HTMLElement
        Builds the VFC section card with header and CSS grid body.
        colCount is the effective column count (density override > profile).
     ───────────────────────────────────────────────────────────── */
		_buildSectionEl(sec, frm, colCount) {
			colCount = colCount || Math.min(Math.max(sec.column_count || 2, 1), 3);
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
       Column count is read from profile.unassigned_column_count (default 2).
    ───────────────────────────────────────────────────────────── */
		_appendUnassigned(frm, layoutRoot, knownFieldnames, assignedFieldnames, profile) {
			const SKIP_TYPES = new Set([
				"Section Break",
				"Column Break",
				"Tab Break",
				"HTML",
				"Heading",
			]);
			const unassigned = (frm.meta?.fields || []).filter(
				(f) =>
					f.fieldname &&
					!assignedFieldnames.has(f.fieldname) &&
					!SKIP_TYPES.has(f.fieldtype)
			);

			if (!unassigned.length) return;

			const colCount = Math.min(Math.max((profile.unassigned_column_count || 2), 1), 3);
			const secEl = document.createElement("div");
			secEl.className = "vfc-le-section vfc-le-unassigned";

			const head = document.createElement("div");
			head.className = "vfc-le-section-head";
			head.textContent = __("Other Fields");
			secEl.appendChild(head);

			const grid = document.createElement("div");
			grid.className = "vfc-le-grid";
			grid.style.gridTemplateColumns = `repeat(${colCount}, 1fr)`;
			secEl.appendChild(grid);

			unassigned.forEach((f) => {
				const fieldObj = frm.fields_dict[f.fieldname];
				if (!fieldObj || !fieldObj.wrapper) return;

				// Skip fields hidden by user settings, permissions, or depends_on
				if (fieldObj.df && (fieldObj.df.hidden || fieldObj.df.invisible)) return;

				const cell = document.createElement("div");
				cell.className = "vfc-le-cell";
				cell.setAttribute("data-vfc-field", f.fieldname);

				const nativeEl =
					fieldObj.wrapper instanceof jQuery ? fieldObj.wrapper[0] : fieldObj.wrapper;
				if (nativeEl && nativeEl.parentNode) {
					cell.appendChild(nativeEl);
					this._restoreVisibleFieldWrapper(nativeEl);
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
			const dt = frm.doctype;
			const layoutRoot = this._getLayoutRoot(frm);

			if (layoutRoot) {
				layoutRoot.classList.remove("vfc-active");
				layoutRoot.querySelectorAll(".vfc-le-section").forEach((el) => {
					// Move field wrappers back to their native parent before removing section
					el.querySelectorAll(".vfc-le-cell").forEach((cell) => {
						const fn = cell.getAttribute("data-vfc-field");
						if (fn && frm.fields_dict[fn]) {
							const fieldObj = frm.fields_dict[fn];
							const nativeWrapper =
								fieldObj.wrapper instanceof jQuery
									? fieldObj.wrapper[0]
									: fieldObj.wrapper;
							if (nativeWrapper && cell.contains(nativeWrapper)) {
								// Return to original native parent if still in DOM
								if (
									fieldObj._native_parent &&
									fieldObj._native_parent.isConnected
								) {
									fieldObj._native_parent.appendChild(nativeWrapper);
								}
							}
						}
					});
					el.remove();
				});
			}

			// Also clear any cached active sections for this doctype
			for (const k of this._activeSections.keys()) {
				if (k.startsWith(dt + "__")) {
					this._activeSections.delete(k);
				}
			}

			if (frm.docname) {
				this._clearValidationTimers(dt + "__" + frm.docname);
			}

			// Disconnect and delete any MutationObservers for this doctype
			if (this._observers) {
				for (const k of this._observers.keys()) {
					if (k.startsWith(dt + "__")) {
						this._observers.get(k).disconnect();
						this._observers.delete(k);
					}
				}
			}
		},

		/* ─────────────────────────────────────────────────────────────
       _setupObserver
       Watches the DOM to see if Frappe natively moves field wrappers
       back into hidden native sections, pulling them back out dynamically.
    ───────────────────────────────────────────────────────────── */
		_setupObserver(frm, layoutRoot) {
			const key = frm.doctype + "__" + frm.docname;
			if (!this._observers) {
				this._observers = new Map();
			}
			if (this._observers.has(key)) {
				return;
			}

			const observer = new MutationObserver((mutations) => {
				let needsReattach = false;
				for (const mutation of mutations) {
					if (mutation.type === "childList" && mutation.addedNodes.length) {
						for (const node of mutation.addedNodes) {
							if (node.nodeType !== 1) continue;
							const currentLayoutRoot = this._getLayoutRoot(frm);
							if (currentLayoutRoot) this._hideNativeLayoutShells(currentLayoutRoot);
							if (
								node.classList.contains("form-layout") ||
								node.querySelector?.(".form-layout")
							) {
								needsReattach = true;
								break;
							}
							if (
								node.classList.contains("frappe-control") ||
								node.querySelector?.(".frappe-control")
							) {
								const parent = node.parentNode;
								if (parent && !parent.classList.contains("vfc-le-cell")) {
									needsReattach = true;
									break;
								}
							}
						}
					}
					if (needsReattach) break;
				}

				if (needsReattach) {
					observer.disconnect();
					this._observers.delete(key);
					this.attach(frm);
				}
			});

			observer.observe(this._getObserverRoot(frm, layoutRoot), {
				childList: true,
				subtree: true,
			});
			this._observers.set(key, observer);
		},

		/* ─────────────────────────────────────────────────────────────
       invalidateCache(doctype)
       Call this after saving a profile to force re-fetch on next
       form open.
    ───────────────────────────────────────────────────────────── */
		_invalidateCache(doctype) {
			this._cache.delete(doctype);
		},

		/* ─────────────────────────────────────────────────────────────
       renderWithDensity(frm, colCount)
       Renders the form with a dynamic (virtual) profile at the
       specified column count.  Bypasses PILOT / tab gates so that
       density works on EVERY DocType.
    ───────────────────────────────────────────────────────────── */
		renderWithDensity(frm, colCount) {
			const layoutRoot = this._getLayoutRoot(frm);
			if (!layoutRoot) return;

			this._clearSections(frm);
			layoutRoot.classList.add("vfc-active");

			// Build a virtual profile from the current form meta fields
			const profile = this._buildDensityProfile(frm, colCount);
			if (!profile) return;

			// Hide ALL native shells INCLUDING tab structure
			this._hideNativeLayoutShells(layoutRoot);
			layoutRoot.querySelectorAll(".nav-tabs, .tab-content, .tab-pane").forEach((el) => {
				if (el.closest(".vfc-le-section")) return;
				el.style.setProperty("display", "none", "important");
				el.setAttribute("data-vfc-hidden", "1");
			});

			const knownFieldnames = new Set((frm.meta?.fields || []).map((f) => f.fieldname));
			const SKIP_TYPES = new Set(["Section Break", "Column Break", "Tab Break", "HTML", "Heading"]);
			const metaFieldTypeMap = {};
			(frm.meta?.fields || []).forEach((mf) => {
				if (mf.fieldname) metaFieldTypeMap[mf.fieldname] = mf.fieldtype;
			});

			const injectedContainers = [];

			profile.sections.forEach((sec) => {
				if (sec.visible === false) return;

				const sectionEl = this._buildSectionEl(sec, frm, colCount);
				const gridEl = sectionEl.querySelector(".vfc-le-grid");

				const fields = [...(sec.fields || [])].sort(
					(a, b) => (a.sort_order || 0) - (b.sort_order || 0)
				);
				let hasVisibleField = false;

				fields.forEach((fld) => {
					const fn = fld.fieldname;
					if (!knownFieldnames.has(fn)) return;
					if (SKIP_TYPES.has(metaFieldTypeMap[fn])) return;

					const fieldObj = frm.fields_dict[fn];
					if (!fieldObj) return;

					if (fld.visible === false) {
						frm.toggle_display(fn, false);
						return;
					}

					if (fieldObj.df && (fieldObj.df.hidden || fieldObj.df.invisible)) return;

					const wrapper = fieldObj.wrapper;
					if (!wrapper) return;

					const cell = document.createElement("div");
					cell.className = "vfc-le-cell";
					cell.style.gridColumn = "1";
					cell.setAttribute("data-vfc-field", fn);

					const nativeEl = wrapper instanceof jQuery ? wrapper[0] : wrapper;
					if (nativeEl && nativeEl.parentNode) {
						if (!fieldObj._native_parent) {
							fieldObj._native_parent = nativeEl.parentNode;
						}
						cell.appendChild(nativeEl);
						this._restoreVisibleFieldWrapper(nativeEl);
					}

					gridEl.appendChild(cell);
					hasVisibleField = true;
				});

				if (hasVisibleField || sec.collapsible) {
					layoutRoot.appendChild(sectionEl);
					injectedContainers.push(sectionEl);
				}
			});

			this._activeSections.set(frm.doctype + "__" + frm.docname, injectedContainers);
		},

		/* ─────────────────────────────────────────────────────────────
       restoreNative(frm)
       Removes all VFC sections and restores Frappe's native layout.
    ───────────────────────────────────────────────────────────── */
		restoreNative(frm) {
			this._clearSections(frm);
		},

		/* ─────────────────────────────────────────────────────────────
       _buildDensityProfile(frm, colCount) → profile object
       Groups frm.meta.fields by Section Break into a virtual profile.
    ───────────────────────────────────────────────────────────── */
		_buildDensityProfile(frm, colCount) {
			const fields = frm.meta?.fields || [];
			if (!fields.length) return null;

			const sections = [];
			let currentSection = null;
			const SKIP_TYPES = new Set(["Section Break", "Column Break", "Tab Break"]);

			fields.forEach((df, i) => {
				if (df.fieldtype === "Tab Break" || df.fieldtype === "HTML" || df.fieldtype === "Heading") return;

				if (df.fieldtype === "Section Break") {
					currentSection = {
						fieldname: df.fieldname || `sec_${i}`,
						id: df.fieldname || `sec_${i}`,
						label: df.label || "",
						column_count: colCount || 2,
						visible: true,
						collapsible: !!df.collapsible,
						collapsed_by_default: !!df.collapsed_by_default,
						fields: [],
					};
					sections.push(currentSection);
					return;
				}

				if (SKIP_TYPES.has(df.fieldtype)) return;

				if (!currentSection) {
					currentSection = {
						fieldname: "_default",
						id: "_default",
						label: "",
						column_count: colCount || 2,
						visible: true,
						collapsible: false,
						fields: [],
					};
					sections.push(currentSection);
				}

				currentSection.fields.push({
					fieldname: df.fieldname,
					visible: !df.hidden,
					sort_order: i,
					col: 1,
				});
			});

			return {
				profile_name: "_density",
				column_count: colCount || 2,
				sections: sections.filter((s) => s.fields.length > 0),
				unassigned_policy: "discard",
			};
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
		onload_post_render(frm) {
			setTimeout(() => {
				try {
					LayoutEngine.attach(frm);
				} catch (err) {
					console.warn("[LE] attach error:", err);
				}
			}, 50);
		},
	});

	/* ═══════════════════════════════════════════════════════════════════
     EXPOSE globally for vfc_sections_tab.js and console debugging
  ═══════════════════════════════════════════════════════════════════ */
	window.VFCLayoutEngine = LayoutEngine;
	console.log("[LE] vfc_layout_engine.js parsed and initialized successfully.");
})();
