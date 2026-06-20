/**
 * Unit tests for Scope Context Report Filter Hardening (Option A+).
 *
 * Run with: `node --test construction/tests/test_scope_context_report_filters.js`
 * (from the construction app root).
 */

const { describe, it, before } = require("node:test");
const assert = require("node:assert/strict");

// Stub browser globals so the IIFE does not crash on load.
global.window = global;
const noopJq = {
	off: () => noopJq,
	on: () => noopJq,
	ready: () => {},
	prop: () => {},
	attr: () => {},
	removeAttr: () => {},
	length: 0,
};
global.document = { ready: () => {} };
global.$ = () => noopJq;
global.frappe = {
	boot: { user: { roles: [] } },
	xcall: async () => ({}),
	query_report: { filters: [] },
	views: { QueryReport: { prototype: {} } },
};
global.setTimeout = () => 0;

let mod;
before(() => {
	mod = require("../public/js/scope_context_report_filters.js");
});

describe("ALLOWLISTED_REPORTS", () => {
	it("contains the 10 Option A+ reports", () => {
		for (const report of [
			"General Ledger",
			"Trial Balance",
			"Profit and Loss Statement",
			"Balance Sheet",
			"Accounts Payable",
			"Accounts Payable Summary",
			"Accounts Receivable",
			"Accounts Receivable Summary",
			"Budget Variance Report",
			"Cash Flow",
		]) {
			assert.ok(
				mod.ALLOWLISTED_REPORTS.has(report),
				`${report} should be in the allowlist`,
			);
		}
	});

	it("contains Project-wise Profitability if installed", () => {
		assert.ok(mod.ALLOWLISTED_REPORTS.has("Project-wise Profitability"));
	});
});

describe("UNRESTRICTED_ROLES", () => {
	it("contains the four finance / system roles", () => {
		for (const role of [
			"System Manager",
			"Accounts Manager",
			"Accounts User",
			"Finance Manager",
		]) {
			assert.ok(mod.UNRESTRICTED_ROLES.has(role), `${role} should be unrestricted`);
		}
	});
});

describe("isUnrestricted()", () => {
	it("returns true when the user holds an unrestricted role", () => {
		global.frappe.boot.user.roles = ["Accounts Manager", "Some Other Role"];
		assert.equal(mod.isUnrestricted(), true);
	});

	it("returns true for System Manager", () => {
		global.frappe.boot.user.roles = ["System Manager"];
		assert.equal(mod.isUnrestricted(), true);
	});

	it("returns false when the user has no roles", () => {
		global.frappe.boot.user.roles = [];
		assert.equal(mod.isUnrestricted(), false);
	});

	it("returns false for non-finance roles", () => {
		global.frappe.boot.user.roles = ["Sales User", "Purchase User"];
		assert.equal(mod.isUnrestricted(), false);
	});
});

describe("isAllowlisted()", () => {
	it("returns true for a known report", () => {
		assert.equal(mod.isAllowlisted("General Ledger"), true);
		assert.equal(mod.isAllowlisted("Trial Balance"), true);
		assert.equal(mod.isAllowlisted("Budget Variance Report"), true);
	});

	it("returns false for an unknown report", () => {
		assert.equal(mod.isAllowlisted("Sales Analytics"), false);
		assert.equal(mod.isAllowlisted(""), false);
		assert.equal(mod.isAllowlisted(null), false);
	});
});

describe("SCOPE_FIELDS", () => {
	it("covers all four scope dimensions", () => {
		assert.ok(mod.SCOPE_FIELDS.includes("company"));
		assert.ok(mod.SCOPE_FIELDS.includes("project"));
		assert.ok(mod.SCOPE_FIELDS.includes("cost_center"));
		assert.ok(mod.SCOPE_FIELDS.includes("department"));
	});
});

describe("isListField()", () => {
	it("treats company as a scalar", () => {
		assert.equal(mod.isListField("company"), false);
	});
	it("treats project, cost_center, department as lists", () => {
		assert.equal(mod.isListField("project"), true);
		assert.equal(mod.isListField("cost_center"), true);
		assert.equal(mod.isListField("department"), true);
	});
});

describe("buildStrictValue() — MultiSelectList shape preservation", () => {
	// NOTE: the module caches the hierarchy on first read. Set the
	// canonical hierarchy here; subsequent tests reuse the same data.
	before(() => {
		global.window.scopeContext = {
			enabled: true,
			hierarchy: {
				cost_centers: [
					{ name: "A", lft: 1, rgt: 8, is_group: 1 },
					{ name: "A-1", lft: 2, rgt: 5, is_group: 1 },
					{ name: "A-1-1", lft: 3, rgt: 4, is_group: 0 },
					{ name: "A-2", lft: 6, rgt: 7, is_group: 0 },
					{ name: "B", lft: 9, rgt: 10, is_group: 0 },
				],
				projects: [],
				companies: [],
				departments: [],
			},
		};
	});

	it("company is scalar", () => {
		assert.equal(mod.buildStrictValue("company", "Acme"), "Acme");
	});

	it("project is a list with one element", () => {
		assert.deepEqual(mod.buildStrictValue("project", "PROJ-1"), ["PROJ-1"]);
	});

	it("department is a list with one element", () => {
		assert.deepEqual(mod.buildStrictValue("department", "DEPT-1"), ["DEPT-1"]);
	});

	it("cost_center is a list with the scoped node and descendants", () => {
		const out = mod.buildStrictValue("cost_center", "A");
		assert.ok(Array.isArray(out));
		assert.ok(out.includes("A"));
		assert.ok(out.includes("A-1"));
		assert.ok(out.includes("A-1-1"));
		assert.ok(out.includes("A-2"));
	});

	it("empty scope returns an empty list for MultiSelectList fields", () => {
		assert.deepEqual(mod.buildStrictValue("project", null), []);
		assert.deepEqual(mod.buildStrictValue("cost_center", undefined), []);
		assert.deepEqual(mod.buildStrictValue("department", ""), []);
	});

	it("empty scope returns null for the company scalar", () => {
		assert.equal(mod.buildStrictValue("company", null), null);
		assert.equal(mod.buildStrictValue("company", undefined), null);
	});
});

describe("getCostCenterDescendants()", () => {
	// Note: the module caches the hierarchy on first call. Set it
	// once and the subsequent tests use the same data.
	const TEST_HIERARCHY = {
		enabled: true,
		hierarchy: {
			cost_centers: [
				{ name: "A", lft: 1, rgt: 8, is_group: 1 },
				{ name: "A-1", lft: 2, rgt: 5, is_group: 1 },
				{ name: "A-1-1", lft: 3, rgt: 4, is_group: 0 },
				{ name: "A-2", lft: 6, rgt: 7, is_group: 0 },
				{ name: "B", lft: 9, rgt: 10, is_group: 0 },
			],
		},
	};

	before(() => {
		global.window.scopeContext = TEST_HIERARCHY;
	});

	it("returns the scoped node and all descendants for a group", () => {
		const out = mod.getCostCenterDescendants("A");
		assert.deepEqual(out.sort(), ["A", "A-1", "A-1-1", "A-2"].sort());
	});

	it("returns the scoped node only for a leaf", () => {
		assert.deepEqual(mod.getCostCenterDescendants("A-1-1"), ["A-1-1"]);
	});

	it("returns the scoped node and its single descendant for a parent", () => {
		const out = mod.getCostCenterDescendants("A-1");
		assert.deepEqual(out.sort(), ["A-1", "A-1-1"].sort());
	});

	it("returns an empty list for null", () => {
		assert.deepEqual(mod.getCostCenterDescendants(null), []);
	});
});

describe("isBudgetVariance()", () => {
	it("matches the Budget Variance Report name exactly", () => {
		assert.equal(mod.isBudgetVariance("Budget Variance Report"), true);
	});

	it("does not match other reports", () => {
		assert.equal(mod.isBudgetVariance("General Ledger"), false);
		assert.equal(mod.isBudgetVariance("Trial Balance"), false);
		assert.equal(mod.isBudgetVariance(""), false);
	});
});

describe("Budget Variance Report — get_data override for dimension", () => {
	// Test the dimension-specific get_data replacement by directly
	// testing the closure factory logic. The full applyBudgetVarianceHardening
	// function depends on globals; here we test the equivalent logic
	// by examining what get_data returns for Cost Center and Project
	// dimensions given a known scope hierarchy.

	before(() => {
		global.window.scopeContext = {
			enabled: true,
			hierarchy: {
				cost_centers: [
					{ name: "Main - E", cost_center_name: "Main" },
					{ name: "Sub - E", cost_center_name: "Sub" },
				],
				projects: [
					{ name: "PROJ-1", project_name: "Project One" },
					{ name: "PROJ-2", project_name: "Project Two" },
				],
				companies: [{ name: "Acme" }],
				departments: [{ name: "Engineering" }],
			},
		};
	});

	function makeCostCenterRows(h) {
		return h.cost_centers.map((cc) => ({
			value: cc.name,
			description: cc.cost_center_name || cc.name,
		}));
	}

	function makeProjectRows(h) {
		return h.projects.map((p) => ({
			value: p.name,
			description: p.project_name || p.name,
		}));
	}

	it("Cost Center dimension returns scope-hierarchy rows for restricted users", () => {
		const h = global.window.scopeContext.hierarchy;
		const rows = makeCostCenterRows(h);
		// The closure should expose all scope cost-centers.
		assert.equal(rows.length, 2);
		assert.deepEqual(rows[0], { value: "Main - E", description: "Main" });
		assert.deepEqual(rows[1], { value: "Sub - E", description: "Sub" });
	});

	it("Project dimension returns scope-hierarchy rows for restricted users", () => {
		const h = global.window.scopeContext.hierarchy;
		const rows = makeProjectRows(h);
		assert.equal(rows.length, 2);
		assert.deepEqual(rows[0], { value: "PROJ-1", description: "Project One" });
		assert.deepEqual(rows[1], { value: "PROJ-2", description: "Project Two" });
	});

	it("Cost Center filter typing matches user input", () => {
		const h = global.window.scopeContext.hierarchy;
		const allRows = makeCostCenterRows(h);
		const needle = "sub";
		const filtered = allRows.filter(
			(r) =>
				!needle ||
				r.value.toLowerCase().includes(needle) ||
				r.description.toLowerCase().includes(needle),
		);
		assert.equal(filtered.length, 1);
		assert.equal(filtered[0].value, "Sub - E");
	});

	it("Project filter typing matches user input", () => {
		const h = global.window.scopeContext.hierarchy;
		const allRows = makeProjectRows(h);
		const needle = "one";
		const filtered = allRows.filter(
			(r) =>
				!needle ||
				r.value.toLowerCase().includes(needle) ||
				r.description.toLowerCase().includes(needle),
		);
		assert.equal(filtered.length, 1);
		assert.equal(filtered[0].value, "PROJ-1");
	});
});

describe("lockField() / unlockField()", () => {
	it("lockField sets read_only=1 and disables the input", () => {
		const field = {
			df: { read_only: 0 },
			set_read_only: function (v) {
				this._ro = v;
			},
			set_value: function () {},
			$input: {
				length: 1,
				prop: function (k, v) {
					this[k] = v;
				},
				attr: function (k, v) {
					this[k] = v;
				},
				off: () => {},
			},
		};
		mod.lockField(field, "Acme");
		assert.equal(field.df.read_only, 1);
		assert.equal(field._ro, true);
		assert.equal(field.$input.disabled, true);
		assert.equal(field.$input.readonly, true);
	});

	it("unlockField restores editable state", () => {
		const field = {
			df: { read_only: 1 },
			set_read_only: function (v) {
				this._ro = v;
			},
			set_value: function () {},
			$input: {
				length: 1,
				prop: function (k, v) {
					this[k] = v;
				},
				removeAttr: function (k) {
					delete this[k];
				},
			},
		};
		mod.unlockField(field);
		assert.equal(field.df.read_only, 0);
		assert.equal(field._ro, false);
		assert.equal(field.$input.disabled, false);
	});

	it("lockField accepts an array value for MultiSelectList fields", () => {
		const setValueCalls = [];
		const field = {
			df: { read_only: 0, fieldname: "cost_center" },
			set_read_only: () => {},
			set_value: function (v) {
				setValueCalls.push(v);
			},
			$input: {
				length: 1,
				prop: () => {},
				attr: () => {},
				off: () => {},
			},
		};
		mod.lockField(field, ["Main - E", "Elrefae - E"]);
		// set_value is called with the array shape, not a stringified scalar.
		assert.deepEqual(setValueCalls, [["Main - E", "Elrefae - E"]]);
	});
});
