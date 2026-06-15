/* ═══════════════════════════════════════════════════════════════════════
   vfc_layout_engine_tests.js — Browser Console Verification Suite
   ─────────────────────────────────────────────────────────────────────
   Run these from the Frappe Desk console while on a Project form.

   Quick start:
     VFCTest.runAll()

   Or run individually:
     VFCTest.checkDoubleAttach()
     VFCTest.checkOrphans()
     VFCTest.checkTabPanes()
     VFCTest.checkFieldVisibility()
     VFCTest.checkDebounce()
  ═══════════════════════════════════════════════════════════════════════ */

(function () {
	"use strict";

	const TEST = {
		_results: [],

		_log(pass, msg, detail) {
			const icon = pass ? "✅" : "❌";
			const line = `${icon} ${msg}`;
			this._results.push({ pass, msg, detail });
			if (detail) {
				console.log(line, detail);
			} else {
				console.log(line);
			}
		},

		_summary() {
			const passed = this._results.filter((r) => r.pass).length;
			const total = this._results.length;
			console.log(`\n📊 VFCTest Summary: ${passed}/${total} passed`);
			if (passed < total) {
				console.warn("⚠️ Some tests failed. Review the ❌ items above.");
			} else {
				console.log("🎉 All tests passed!");
			}
			return { passed, total, results: this._results };
		},

		/* ─────────────────────────────────────────────────────────
       Test 1: No orphaned field wrappers
       Ensures Patch B (safe-restore) is working.
    ───────────────────────────────────────────────────────── */
		checkOrphans() {
			this._results = [];
			console.log("\n🔍 VFCTest.checkOrphans() — looking for orphaned field wrappers…");

			if (!cur_frm) {
				this._log(false, "No cur_frm available. Open a form first.");
				return this._summary();
			}

			const orphans = [];
			const fields = Object.values(cur_frm.fields_dict);
			fields.forEach((f) => {
				const el = f.wrapper instanceof jQuery ? f.wrapper[0] : f.wrapper;
				if (el && !el.isConnected) {
					orphans.push(f.df.fieldname);
				}
			});

			if (orphans.length === 0) {
				this._log(true, "No orphaned wrappers found.", { totalFields: fields.length });
			} else {
				this._log(false, `Found ${orphans.length} orphaned wrapper(s).`, orphans);
			}
			return this._summary();
		},

		/* ─────────────────────────────────────────────────────────
       Test 2: Tab pane visibility state
       Ensures Patch C (tab watcher) is keeping active panes visible.
    ───────────────────────────────────────────────────────── */
		checkTabPanes() {
			this._results = [];
			console.log("\n🔍 VFCTest.checkTabPanes() — inspecting tab pane states…");

			const layoutRoot = document.querySelector(".form-layout");
			if (!layoutRoot) {
				this._log(false, "No .form-layout found on page.");
				return this._summary();
			}

			const panes = [...layoutRoot.querySelectorAll(".tab-pane")];
			if (!panes.length) {
				this._log(false, "No .tab-pane elements found — this may not be a tabbed form.");
				return this._summary();
			}

			const report = panes.map((p) => {
				const style = getComputedStyle(p);
				const rect = p.getBoundingClientRect();
				const isActive = p.classList.contains("active") || p.classList.contains("show");
				const hasHost = !!p.querySelector(".vfc-tab-pane-host");
				return {
					id: p.id,
					active: isActive,
					hasHost,
					display: style.display,
					visibility: style.visibility,
					height: Math.round(rect.height),
					width: Math.round(rect.width),
				};
			});

			console.table(report);

			const activePane = report.find((p) => p.active);
			if (!activePane) {
				this._log(false, "No active tab pane found.");
			} else if (activePane.display === "none" || activePane.visibility === "hidden") {
				this._log(false, "Active tab pane is hidden!", activePane);
			} else if (activePane.height < 10) {
				this._log(false, "Active tab pane has near-zero height.", activePane);
			} else {
				this._log(true, "Active tab pane is visible and has content.", activePane);
			}

			const hiddenButHost = report.filter(
				(p) => !p.active && p.hasHost && p.display !== "none",
			);
			if (hiddenButHost.length) {
				this._log(
					false,
					"Inactive pane(s) with VFC host are still visible (should be hidden).",
					hiddenButHost,
				);
			} else {
				this._log(true, "Inactive panes with VFC hosts are correctly hidden.");
			}

			return this._summary();
		},

		/* ─────────────────────────────────────────────────────────
       Test 3: Field wrapper visibility inside VFC cells
       Ensures fields are actually painted.
    ───────────────────────────────────────────────────────── */
		checkFieldVisibility() {
			this._results = [];
			console.log("\n🔍 VFCTest.checkFieldVisibility() — checking painted fields…");

			const cells = [...document.querySelectorAll(".vfc-le-cell")];
			if (!cells.length) {
				this._log(false, "No .vfc-le-cell elements found. VFC may not have attached.");
				return this._summary();
			}

			let visible = 0;
			let hidden = 0;
			const hiddenFields = [];

			cells.forEach((cell) => {
				const field = cell.querySelector("[data-vfc-managed='1'], .frappe-control");
				if (!field) return;
				const style = getComputedStyle(field);
				const rect = field.getBoundingClientRect();
				const isPainted =
					style.display !== "none" &&
					style.visibility !== "hidden" &&
					rect.height > 2 &&
					rect.width > 2;
				if (isPainted) {
					visible++;
				} else {
					hidden++;
					hiddenFields.push(
						cell.getAttribute("data-vfc-field") ||
							field.getAttribute("data-fieldname"),
					);
				}
			});

			console.log(
				`   Visible fields: ${visible}, Hidden fields: ${hidden}, Total cells: ${cells.length}`,
			);

			if (hidden === 0) {
				this._log(true, `All ${visible} VFC-managed fields are painted.`);
			} else {
				this._log(false, `${hidden} field(s) are hidden or zero-size.`, hiddenFields);
			}
			return this._summary();
		},

		/* ─────────────────────────────────────────────────────────
       Test 4: Debounce state
       Ensures Patch A (debounce) is active and no double-attach
       occurred within the last few seconds.
    ───────────────────────────────────────────────────────── */
		checkDebounce() {
			this._results = [];
			console.log("\n🔍 VFCTest.checkDebounce() — checking attach call pattern…");

			// The debounce wrapper lives in an IIFE; we can't directly inspect _pending,
			// but we can verify the global hook signature has changed by checking
			// that window.VFC_DISABLED exists as a concept (added in 1.29).
			if (typeof window.VFC_DISABLED !== "undefined") {
				this._log(true, "VFC_DISABLED flag is present (v1.29+ engine).");
			} else {
				this._log(false, "VFC_DISABLED flag missing — you may be running the old engine.");
			}

			// Ask user to check console history for multiple [LE] attach() lines
			console.log(
				"   💡 Tip: Filter console for '[LE] attach() triggered'. You should see it once per form load.",
			);
			return this._summary();
		},

		/* ─────────────────────────────────────────────────────────
       Test 5: Native section shells are NOT hidden on tabbed forms
       Ensures we haven't regressed native tab structure.
    ───────────────────────────────────────────────────────── */
		checkNativeShells() {
			this._results = [];
			console.log(
				"\n🔍 VFCTest.checkNativeShells() — ensuring native shells are preserved…",
			);

			const layoutRoot = document.querySelector(".form-layout");
			if (!layoutRoot) {
				this._log(false, "No .form-layout found.");
				return this._summary();
			}

			const nativeSections = [
				...layoutRoot.querySelectorAll(".form-section, .frappe-section"),
			];
			const visibleNative = nativeSections.filter((el) => {
				const s = getComputedStyle(el);
				const r = el.getBoundingClientRect();
				return (
					s.display !== "none" &&
					s.visibility !== "hidden" &&
					r.height > 1 &&
					r.width > 1
				);
			});

			console.log(
				`   Native sections total: ${nativeSections.length}, visible: ${visibleNative.length}`,
			);

			// For tabbed forms we expect native shells to remain visible (they hold the tabs)
			const hasTabs = !!layoutRoot.querySelector(".tab-pane");
			if (hasTabs && visibleNative.length === 0) {
				this._log(
					false,
					"All native sections are hidden on a tabbed form — this will break tabs.",
				);
			} else {
				this._log(true, "Native section shells are present.", {
					hasTabs,
					visibleNative: visibleNative.length,
				});
			}
			return this._summary();
		},

		/* ─────────────────────────────────────────────────────────
       Test 6: Full integration — run all checks
    ───────────────────────────────────────────────────────── */
		runAll() {
			this._results = [];
			console.log("\n═══════════════════════════════════════════════════════════");
			console.log("   VFC Layout Engine — Verification Suite v1.0");
			console.log("═══════════════════════════════════════════════════════════");

			this.checkDebounce();
			this.checkOrphans();
			this.checkTabPanes();
			this.checkFieldVisibility();
			this.checkNativeShells();

			const passed = this._results.filter((r) => r.pass).length;
			const total = this._results.length;
			console.log("\n═══════════════════════════════════════════════════════════");
			console.log(`   FINAL: ${passed}/${total} assertions passed`);
			console.log("═══════════════════════════════════════════════════════════");
			return { passed, total };
		},
	};

	window.VFCTest = TEST;
	console.log("[VFCTest] Test suite loaded. Run VFCTest.runAll() to verify.");
})();
