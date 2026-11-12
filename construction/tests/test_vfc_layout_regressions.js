/**
 * VFC Layout Regressions
 *
 * Covers two acceptance criteria from PLAN.md §7 that the independent review
 * found had no committed test (FINAL_REVIEW.md MAJOR-1 / MAJOR-2):
 *
 *   AC-5  P0-2 — VFC must never strip the `hide-control` class that Frappe
 *                applies to a control it wants hidden.
 *   AC-6  P0-3 — the profile merge must never pull a field the user placed
 *                back into its native section.
 *
 * The two app files under test are IIFEs that attach to `window`, so they are
 * executed in a `vm` sandbox with the minimal globals they touch at parse
 * time (`frappe.ui.form.on`, `window`, `vfcDebugLog`). That is the same
 * technique the browser test suite uses conceptually, and it lets these run
 * under the repo's existing `node --test` convention
 * (see PROFESSIONAL_ENGINEERING_STANDARD.md §16).
 *
 * Run:
 *   cd /home/mohamed/frappe-bench/apps/construction
 *   node --test construction/tests/test_vfc_layout_regressions.js
 *
 * Feature: vfc-gate-off-and-p0-fixes
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const JS_DIR = path.join(__dirname, "..", "public", "js");

// ---------------------------------------------------------------------------
// Sandbox loader
// ---------------------------------------------------------------------------

/**
 * Executes an IIFE app script in an isolated context and returns `window`.
 *
 * Only the globals the script actually touches at parse time are supplied.
 * If a future edit adds a new parse-time dependency this will throw, which is
 * the desired signal — the test must not silently start testing a stub.
 */
function loadScript(fileName, extraGlobals) {
	const src = fs.readFileSync(path.join(JS_DIR, fileName), "utf8");
	const sandbox = Object.assign(
		{
			window: {},
			frappe: {
				ui: { form: { on: () => {} } },
				_: (s) => s,
				boot: {},
				call: () => Promise.resolve({}),
				confirm: () => {},
				show_alert: () => {},
			},
			vfcDebugLog: () => {},
			__: (s) => s,
			console,
			setTimeout,
			clearTimeout,
			Set,
			Map,
			JSON,
			Math,
			Date,
			Array,
			Object,
			String,
			Number,
			Boolean,
			RegExp,
			Promise,
			Error,
			parseInt,
			parseFloat,
			isNaN,
			isFinite,
		},
		extraGlobals || {}
	);
	vm.createContext(sandbox);
	vm.runInContext(src, sandbox, { filename: fileName });
	return sandbox.window;
}

const engineWindow = loadScript("vfc_layout_engine.js");
const controlsWindow = loadScript("vite_layout_controls.js");

const LayoutEngine = engineWindow.VFCLayoutEngine;
const VFC = controlsWindow._VFC;

// ---------------------------------------------------------------------------
// Minimal DOM stand-ins
// ---------------------------------------------------------------------------

/**
 * A field wrapper stand-in: just enough surface for
 * `_restoreVisibleFieldWrapper`. `children` is a plain array, which satisfies
 * the `querySelectorAll(...).forEach(...)` call in the implementation.
 */
function makeWrapper(classes, children) {
	const cls = new Set(classes || []);
	const attrs = {};
	const styles = {};
	const kids = children || [];
	return {
		classList: {
			contains: (c) => cls.has(c),
			add: (c) => cls.add(c),
			remove: function () {
				for (let i = 0; i < arguments.length; i++) cls.delete(arguments[i]);
			},
			_snapshot: () => Array.from(cls).sort(),
		},
		setAttribute: (k, v) => {
			attrs[k] = String(v);
		},
		removeAttribute: (k) => {
			delete attrs[k];
		},
		getAttribute: (k) => (Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null),
		hasAttribute: (k) => Object.prototype.hasOwnProperty.call(attrs, k),
		style: {
			removeProperty: (k) => {
				delete styles[k];
			},
			setProperty: (k, v) => {
				styles[k] = v;
			},
			_snapshot: () => Object.assign({}, styles),
		},
		querySelectorAll: () => kids,
		_attrs: attrs,
		_children: kids,
	};
}

// ===========================================================================
// AC-5 / P0-2 — `hide-control` must never be stripped
// ===========================================================================

describe("AC-5 P0-2: _restoreVisibleFieldWrapper never strips hide-control", function () {
	/**
	 * This is the defect. Frappe applies `.hide-control` whenever a control's
	 * display status is "None" — for a permlevel restriction, or for an empty
	 * read-only field under System Settings.hide_empty_read_only_fields
	 * (base_control.js get_status -> refresh). In both paths `df.hidden` is
	 * NOT set, so the guard above this function cannot see it.
	 */
	it("keeps hide-control on the wrapper while still marking it managed", function () {
		const el = makeWrapper(["frappe-control", "hide-control"]);

		LayoutEngine._restoreVisibleFieldWrapper(el, { df: {} });

		assert.ok(
			el.classList.contains("hide-control"),
			"hide-control must survive: the engine must not overrule Frappe's decision to hide a control"
		);
		assert.equal(
			el.getAttribute("data-vfc-managed"),
			"1",
			"the field must still be tracked as managed so section-empty accounting works"
		);
	});

	it("keeps hide-control on descendants (label / input wrapper)", function () {
		const child = makeWrapper(["control-label", "hide-control"]);
		const el = makeWrapper(["frappe-control"], [child]);

		LayoutEngine._restoreVisibleFieldWrapper(el, { df: {} });

		assert.ok(
			child.classList.contains("hide-control"),
			"hide-control on a descendant must survive too — stripping only the wrapper would still reveal the field"
		);
	});

	/**
	 * Negative control: proves the function still does its actual job for a
	 * control Frappe wants visible. Without this, a fix that simply did
	 * nothing would satisfy the two assertions above.
	 */
	it("still restores a control Frappe has NOT hidden", function () {
		const el = makeWrapper(["frappe-control", "hidden", "d-none"]);
		el.setAttribute("hidden", "");

		LayoutEngine._restoreVisibleFieldWrapper(el, { df: {} });

		assert.equal(
			el.classList.contains("hide-control"),
			false,
			"a control without hide-control must not gain one"
		);
		assert.equal(el.classList.contains("hidden"), false, "hidden must be cleared");
		assert.equal(el.classList.contains("d-none"), false, "d-none must be cleared");
		assert.equal(
			el.hasAttribute("hidden"),
			false,
			"the hidden attribute must be cleared"
		);
		assert.equal(el.getAttribute("data-vfc-managed"), "1", "must be marked managed");
	});

	/**
	 * The pre-existing guards must survive the fix — these are the cases the
	 * function was always supposed to leave alone.
	 */
	it("returns early and does not mark managed when df.hidden is set", function () {
		const el = makeWrapper(["frappe-control"]);

		LayoutEngine._restoreVisibleFieldWrapper(el, { df: { hidden: 1 } });

		assert.equal(
			el.getAttribute("data-vfc-managed"),
			null,
			"a df.hidden control must be skipped entirely"
		);
	});

	it("returns early when hidden_due_to_dependency is set", function () {
		const el = makeWrapper(["frappe-control"]);

		LayoutEngine._restoreVisibleFieldWrapper(el, {
			df: { hidden_due_to_dependency: 1 },
		});

		assert.equal(
			el.getAttribute("data-vfc-managed"),
			null,
			"a dependency-hidden control must be skipped entirely"
		);
	});

	it("is a no-op for a missing element", function () {
		assert.doesNotThrow(function () {
			LayoutEngine._restoreVisibleFieldWrapper(null, { df: {} });
		});
	});
});

// ===========================================================================
// AC-6 / P0-3 — merge must not pull a user-placed field back to native
// ===========================================================================

describe("AC-6 P0-3: _mergeProfileWithNativeSections preserves user placement", function () {
	/**
	 * Native layout: `project_name` belongs to section `sb1`.
	 * User profile: the user moved `project_name` into their own `sec_custom`.
	 *
	 * The old implementation built `nativeFieldnames` from EVERY field of a
	 * native section the profile did not carry, then filtered those names out
	 * of all merged sections — destroying the user's arrangement on each
	 * save/load. It is why the live database showed user sections with 0 fields.
	 */
	function nativeProfile() {
		return {
			version: 1,
			unassigned_policy: "append",
			unassigned_column_count: 2,
			sections: [
				{
					id: "sb1",
					fieldname: "sb1",
					label: "General",
					column_count: 2,
					sort_order: 1,
					visible: true,
					fields: [
						{ fieldname: "naming_series", col: 1, sort_order: 1 },
						{ fieldname: "project_name", col: 2, sort_order: 2 },
					],
				},
				{
					id: "sb2",
					fieldname: "sb2",
					label: "Details",
					column_count: 2,
					sort_order: 2,
					visible: true,
					fields: [{ fieldname: "status", col: 1, sort_order: 1 }],
				},
			],
		};
	}

	function userProfileWithProjectNameInCustomSection() {
		return {
			version: 1,
			unassigned_policy: "append",
			sections: [
				{
					id: "sec_custom",
					fieldname: "sec_custom",
					label: "My Section",
					column_count: 2,
					sort_order: 1,
					visible: true,
					fields: [{ fieldname: "project_name", col: 1, sort_order: 1 }],
				},
			],
		};
	}

	function sectionById(merged, id) {
		return (merged.sections || []).find((s) => s.id === id || s.fieldname === id);
	}

	function fieldnamesOf(section) {
		return ((section && section.fields) || []).map((f) => f.fieldname);
	}

	it("keeps a user-placed field in the section the user put it in", function () {
		const merged = VFC._mergeProfileWithNativeSections(
			userProfileWithProjectNameInCustomSection(),
			nativeProfile()
		);

		const custom = sectionById(merged, "sec_custom");
		assert.ok(custom, "the user's custom section must still exist");
		assert.ok(
			fieldnamesOf(custom).includes("project_name"),
			"project_name must stay where the user placed it — this is the data-loss defect"
		);
	});

	it("does not also duplicate the field into its native section", function () {
		const merged = VFC._mergeProfileWithNativeSections(
			userProfileWithProjectNameInCustomSection(),
			nativeProfile()
		);

		const native = sectionById(merged, "sb1");
		assert.ok(native, "the native section must still be present");
		assert.ok(
			!fieldnamesOf(native).includes("project_name"),
			"project_name must not be re-homed to sb1 — the user placed it elsewhere"
		);
	});

	/**
	 * Negative control: the merge must still ADOPT fields the user never
	 * placed. Without this, a fix that simply stopped merging would satisfy
	 * the assertions above while breaking profile loading entirely.
	 */
	it("still adopts native fields the user has NOT placed", function () {
		const merged = VFC._mergeProfileWithNativeSections(
			userProfileWithProjectNameInCustomSection(),
			nativeProfile()
		);

		const native = sectionById(merged, "sb1");
		assert.ok(
			fieldnamesOf(native).includes("naming_series"),
			"unplaced native fields must still be adopted, or profile loading regresses"
		);
	});

	it("preserves the custom section's own identity and ordering", function () {
		const merged = VFC._mergeProfileWithNativeSections(
			userProfileWithProjectNameInCustomSection(),
			nativeProfile()
		);

		assert.equal(merged.sections[0].id, "sec_custom", "user section must come first");
		assert.equal(
			merged.sections[0].label,
			"My Section",
			"the user's label must not be overwritten by a native label"
		);
	});

	it("does not duplicate a field across sections", function () {
		const merged = VFC._mergeProfileWithNativeSections(
			userProfileWithProjectNameInCustomSection(),
			nativeProfile()
		);

		const seen = new Set();
		const dupes = [];
		(merged.sections || []).forEach((sec) => {
			fieldnamesOf(sec).forEach((fn) => {
				if (seen.has(fn)) dupes.push(fn);
				seen.add(fn);
			});
		});
		assert.deepEqual(dupes, [], "a field may appear in exactly one section");
	});
});
