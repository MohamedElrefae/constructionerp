/* eslint-disable */
/**
 * Scope Context Report Filter Hardening (Option A+)
 *
 * When the Scope Context feature is enabled, this module:
 *   1. Restricts scope-locking to an explicit allowlist of financial
 *      reports (per the Option A+ plan) so we never silently mutate
 *      behavior of unrelated custom or third-party reports.
 *   2. Skips locking when the current user holds an unrestricted
 *      finance/system role — those users keep normal Link / MultiSelectList
 *      selection ability.
 *   3. Probes the user's read permission on Company / Project / Cost Center
 *      (cached for the session) and only locks the fields the user cannot
 *      safely browse.
 *   4. Preserves the list shape of MultiSelectList filters — it never
 *      converts them to plain Data fields, which would break reports
 *      that expect arrays. Specifically:
 *        - `company` is a Link → scalar.
 *        - `project` is a MultiSelectList → list `[scope.project]`.
 *        - `cost_center` is a MultiSelectList → list `[scope.cost_center,
 *          *descendants via lft/rgt]`.
 *        - `department` is a MultiSelectList → list `[scope.department]`.
 *   5. Disables the underlying input DOM element so that focus/click
 *      cannot trigger a search_link request, and re-applies whenever
 *      the top-bar scope context changes.
 *   6. For the Budget Variance Report only, replaces the dynamic
 *      `budget_against_filter.get_data` with a closure that returns
 *      scope-hierarchy rows when the user cannot browse the dimension.
 *
 * Convention: this script is loaded after scope_context.js and before
 * the late Frappe bundle. Bump ?v= on hooks.py when modifying.
 */
(function (root) {
	"use strict";

	// ─── Configuration ───────────────────────────────────────────────

	// Explicit allowlist. Reports NOT in this set are untouched.
	const ALLOWLISTED_REPORTS = new Set([
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
		"Project-wise Profitability",
	]);

	// Dimensions that get scope-locked in the allowlisted reports.
	const SCOPE_FIELDS = ["company", "cost_center", "project", "department"];

	// Roles allowed to keep the original Link / MultiSelectList behavior.
	// Mirrors scope_report.UNRESTRICTED_REPORT_ROLES.
	const UNRESTRICTED_ROLES = new Set([
		"System Manager",
		"Accounts Manager",
		"Accounts User",
		"Finance Manager",
	]);

	// Fieldtypes per dimension. Used to decide the right value shape.
	const SCALAR_FIELDS = new Set(["company"]);
	const LIST_FIELDS = new Set(["project", "cost_center", "department"]);

	// ─── Session-scoped state ────────────────────────────────────────

	let _perms = null; // {Company, Project, Cost Center, Account}
	let _hierarchy = null; // {companies, cost_centers, projects, departments}

	function loadPermissions() {
		if (_perms) return _perms;
		_perms = { Company: false, Project: false, "Cost Center": false, Account: false };
		try {
			frappe
				.xcall("construction.api.scope_context_api.get_scope_dimension_permissions")
				.then(function (r) {
					if (r) _perms = r;
					if (frappe.query_report && frappe.query_report.filters) {
						applyScopeToReportFilters(frappe.query_report);
					}
				});
		} catch (e) {
			// Keep deny defaults.
		}
		return _perms;
	}

	function loadHierarchy() {
		if (_hierarchy) return _hierarchy;
		_hierarchy = (window.scopeContext && window.scopeContext.hierarchy) || null;
		return _hierarchy;
	}

	function canRead(doctypeLabel) {
		const perms = _perms || {};
		return !!perms[doctypeLabel];
	}

	// ─── Helpers ─────────────────────────────────────────────────────

	function isUnrestricted() {
		if (!frappe.boot || !frappe.boot.user) return false;
		const roles = new Set(frappe.boot.user.roles || []);
		for (const r of UNRESTRICTED_ROLES) {
			if (roles.has(r)) return true;
		}
		return false;
	}

	function getScope() {
		if (window.scopeContext && window.scopeContext.enabled) {
			return window.scopeContext.getValidatedCurrentScope() || {};
		}
		return {};
	}

	function getActiveReportName() {
		if (!frappe.query_report) return null;
		return (
			frappe.query_report.report_name ||
			(frappe.query_report.get_title && frappe.query_report.get_title()) ||
			null
		);
	}

	function isAllowlisted(reportName) {
		return Boolean(reportName) && ALLOWLISTED_REPORTS.has(reportName);
	}

	function isListField(fieldname) {
		return LIST_FIELDS.has(fieldname);
	}

	// ─── Cost Center descendant expansion ───────────────────────────

	function getCostCenterDescendants(scopedCostCenter) {
		if (!scopedCostCenter) return [];
		const h = loadHierarchy();
		if (!h || !Array.isArray(h.cost_centers)) return [scopedCostCenter];

		const node = h.cost_centers.find((cc) => cc.name === scopedCostCenter);
		if (!node || node.lft == null || node.rgt == null) {
			return [scopedCostCenter];
		}
		const lft = node.lft;
		const rgt = node.rgt;
		return h.cost_centers
			.filter((cc) => cc.lft != null && cc.rgt != null && cc.lft >= lft && cc.rgt <= rgt)
			.map((cc) => cc.name);
	}

	// ─── Build the strict value for a scope field ───────────────────

	function buildStrictValue(fieldname, scopedValue) {
		if (!scopedValue) {
			return isListField(fieldname) ? [] : null;
		}
		if (fieldname === "company") return scopedValue;
		if (fieldname === "cost_center") return getCostCenterDescendants(scopedValue);
		if (fieldname === "project") return [scopedValue];
		if (fieldname === "department") return [scopedValue];
		return scopedValue;
	}

	// ─── Field-level hardening ───────────────────────────────────────

	function lockField(field, scopedValue) {
		field.df.read_only = 1;
		if (typeof field.set_read_only === "function") {
			field.set_read_only(true);
		}
		const $input = field.$input;
		if ($input && $input.length) {
			$input.prop("disabled", true);
			$input.attr("readonly", true);
			$input.attr("aria-readonly", "true");
			$input.off("focus click keydown mousedown");
		}
		if (scopedValue !== undefined && scopedValue !== null) {
			field.set_value(scopedValue);
		}
	}

	function unlockField(field) {
		field.df.read_only = 0;
		if (typeof field.set_read_only === "function") {
			field.set_read_only(false);
		}
		const $input = field.$input;
		if ($input && $input.length) {
			$input.prop("disabled", false);
			$input.removeAttr("readonly");
			$input.removeAttr("aria-readonly");
		}
	}

	// ─── Budget Variance Report special case ────────────────────────

	function isBudgetVariance(reportName) {
		return reportName === "Budget Variance Report";
	}

	function applyBudgetVarianceHardening(report) {
		if (!report || !report.filters) return;
		const scope = getScope();
		const companyField = (report.filters || []).find(
			(f) => f && f.df && f.df.fieldname === "company",
		);
		if (companyField && scope.company && !canRead("Company")) {
			lockField(companyField, scope.company);
		}
		const budgetAgainstField = (report.filters || []).find(
			(f) => f && f.df && f.df.fieldname === "budget_against",
		);
		const budgetAgainstFilterField = (report.filters || []).find(
			(f) => f && f.df && f.df.fieldname === "budget_against_filter",
		);
		if (!budgetAgainstFilterField) return;

		// Determine the dimension the user picked (default: Cost Center).
		let dimension = "Cost Center";
		if (budgetAgainstField && typeof budgetAgainstField.get_value === "function") {
			const v = budgetAgainstField.get_value();
			if (v) dimension = v;
		}

		// Decide which DocType the dimension maps to. ERPNext ships
		// these as the canonical choices.
		const doctypeByDimension = {
			"Cost Center": "Cost Center",
			Project: "Project",
			"Cost Center (Projects)": "Cost Center",
		};
		const doctype = doctypeByDimension[dimension] || "Cost Center";

		// If the user cannot browse the dimension, replace get_data
		// with a closure over the scope hierarchy.
		if (!canRead(doctype)) {
			const h = loadHierarchy();
			const rows =
				h && Array.isArray(h.cost_centers) && dimension === "Cost Center"
					? h.cost_centers.map((cc) => ({
							value: cc.name,
							description: cc.cost_center_name || cc.name,
						}))
					: h && Array.isArray(h.projects) && dimension === "Project"
					? h.projects.map((p) => ({
							value: p.name,
							description: p.project_name || p.name,
						}))
					: [];

			budgetAgainstFilterField.get_data = function (txt) {
				const needle = (txt || "").toLowerCase();
				return rows.filter(
					(r) =>
						!needle ||
						r.value.toLowerCase().includes(needle) ||
						r.description.toLowerCase().includes(needle),
				);
			};
			// Lock with the scoped value for the chosen dimension.
			const scopedForDim =
				dimension === "Project" ? scope.project : scope.cost_center;
			lockField(budgetAgainstFilterField, scopedForDim || null);
		} else {
			// Finance / permitted user: keep the original get_data.
			if (scope[dimension === "Project" ? "project" : "cost_center"]) {
				budgetAgainstFilterField.set_value(
					scope[dimension === "Project" ? "project" : "cost_center"],
				);
			}
		}
	}

	// ─── Apply scope to a report's filters ──────────────────────────

	function applyScopeToReportFilters(report) {
		if (!report || !report.filters) return;
		if (isUnrestricted()) return;
		const reportName = report.report_name || getActiveReportName();
		if (!isAllowlisted(reportName)) return;

		// Pre-load perms and hierarchy so the first call already has values.
		loadPermissions();
		loadHierarchy();

		// Budget Variance Report has its own filter shape — handle separately.
		if (isBudgetVariance(reportName)) {
			applyBudgetVarianceHardening(report);
			return;
		}

		const scope = getScope();
		if (!scope || Object.keys(scope).length === 0) return;

		(report.filters || []).forEach(function (field) {
			if (!field || !field.df) return;
			const fieldname = field.df.fieldname;
			if (!SCOPE_FIELDS.includes(fieldname)) return;

			// Decide whether this dimension should be locked for the
			// current user. We lock if the user cannot read the
			// underlying DocType (so a search_link would 403).
			let shouldLock = false;
			if (fieldname === "company" && !canRead("Company")) shouldLock = true;
			if (fieldname === "project" && !canRead("Project")) shouldLock = true;
			if (fieldname === "cost_center" && !canRead("Cost Center")) shouldLock = true;
			// department is a MultiSelectList; if the user cannot read
			// the Department DocType we lock the filter.
			if (fieldname === "department" && !canRead("Department")) shouldLock = true;

			if (shouldLock) {
				// Build the strict value with the right shape:
				//   company → scalar
				//   project / cost_center / department → list
				const strict = buildStrictValue(fieldname, scope[fieldname]);
				lockField(field, strict);
			} else {
				// Finance / permitted user: leave Link / MultiSelectList
				// untouched but pre-fill the value from scope if present
				// and the user has not chosen anything else.
				if (scope[fieldname]) {
					const existing = field.get_value();
					if (!existing || (Array.isArray(existing) && existing.length === 0)) {
						field.set_value(buildStrictValue(fieldname, scope[fieldname]));
					}
				}
			}
		});
	}

	// ─── Lifecycle hooks ─────────────────────────────────────────────

	function patchSetupFilters() {
		if (!frappe.views || !frappe.views.QueryReport) return;
		if (frappe.views.QueryReport.prototype.__ct_scope_patched_v2) return;

		const originalSetupFilters = frappe.views.QueryReport.prototype.setup_filters;
		frappe.views.QueryReport.prototype.setup_filters = function () {
			originalSetupFilters.call(this);
			this.report_name = this.report_name || (this.report && this.report.name);
			applyScopeToReportFilters(this);
		};
		frappe.views.QueryReport.prototype.__ct_scope_patched_v2 = true;
	}

	function bindScopeChange() {
		$(document)
			.off("scope:changed.ct_report_filters")
			.on("scope:changed.ct_report_filters", function () {
				if (!window.scopeContext || !window.scopeContext.enabled) return;
				if (!frappe.query_report || !frappe.query_report.filters) return;
				applyScopeToReportFilters(frappe.query_report);
				frappe.query_report.refresh(true);
			});
	}

	// ─── Boot ────────────────────────────────────────────────────────

	$(document).ready(function () {
		setTimeout(patchSetupFilters, 0);
		setTimeout(patchSetupFilters, 500);
		bindScopeChange();
	});

	// ─── Test-only export ────────────────────────────────────────────
	// Exposed for the Node test runner (`node --test`). In the browser
	// this is a no-op; in Node, the test file requires the source and
	// inspects the internals.
	if (typeof module !== "undefined" && module.exports) {
		module.exports = {
			ALLOWLISTED_REPORTS,
			UNRESTRICTED_ROLES,
			SCOPE_FIELDS,
			SCALAR_FIELDS,
			LIST_FIELDS,
			isUnrestricted,
			isAllowlisted,
			isListField,
			isBudgetVariance,
			buildStrictValue,
			getCostCenterDescendants,
			lockField,
			unlockField,
		};
	}
})(typeof window !== "undefined" ? window : globalThis);
