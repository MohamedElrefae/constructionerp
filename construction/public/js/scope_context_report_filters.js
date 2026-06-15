/* eslint-disable */
/**
 * Scope Context Report Filter Lock
 *
 * When the Scope Context feature is enabled, report filters for company,
 * cost_center, project, and department are locked to the active top-bar scope
 * context. Changing the scope in the top bar updates the filters and refreshes
 * the report automatically.
 *
 * This prevents restricted users from triggering unauthorized Link lookups
 * and guarantees the top bar remains the single source of truth.
 */
(function () {
	"use strict";

	const SCOPE_FIELDS = ["company", "cost_center", "project", "department"];

	function getScope() {
		if (window.scopeContext && window.scopeContext.enabled) {
			return window.scopeContext.getValidatedCurrentScope();
		}
		return {};
	}

	function applyScopeToReportFilters(report) {
		const scope = getScope();
		if (!scope || Object.keys(scope).length === 0) return;

		(report.filters || []).forEach(function (field) {
			if (!SCOPE_FIELDS.includes(field.df.fieldname)) return;

			const scopedValue = scope[field.df.fieldname];

			// Lock the field so users cannot manually edit it in the report.
			field.df.read_only = 1;
			if (typeof field.set_read_only === "function") {
				field.set_read_only(true);
			}

			// Disable the underlying input to block focus/click triggered Link lookups.
			const $input = field.$input;
			if ($input && $input.length) {
				$input.prop("disabled", true);
				$input.attr("readonly", true);
				$input.off("focus click");
			}

			// Set the value from scope context if available.
			if (scopedValue) {
				field.set_value(scopedValue);
			}
		});
	}

	function patchSetupFilters() {
		if (!frappe.views || !frappe.views.QueryReport) return;
		if (frappe.views.QueryReport.prototype.__ct_scope_patched) return;

		const originalSetupFilters = frappe.views.QueryReport.prototype.setup_filters;
		frappe.views.QueryReport.prototype.setup_filters = function () {
			originalSetupFilters.call(this);
			if (window.scopeContext && window.scopeContext.enabled) {
				applyScopeToReportFilters(this);
			}
		};

		frappe.views.QueryReport.prototype.__ct_scope_patched = true;
	}

	function bindScopeChange() {
		$(document).off("scope:changed.ct_report_filters").on("scope:changed.ct_report_filters", function () {
			if (!window.scopeContext || !window.scopeContext.enabled) return;
			if (!frappe.query_report || !frappe.query_report.filters) return;

			const scope = getScope();
			let changed = false;

			frappe.query_report.filters.forEach(function (field) {
				if (!SCOPE_FIELDS.includes(field.df.fieldname)) return;
				const scopedValue = scope[field.df.fieldname];
				if (scopedValue && field.get_value() !== scopedValue) {
					field.set_value(scopedValue);
					changed = true;
				}
			});

			if (changed) {
				frappe.query_report.refresh(true);
			}
		});
	}

	// Patch after the Frappe report bundle is loaded.
	$(document).ready(function () {
		// Delay to ensure QueryReport prototype is available.
		setTimeout(patchSetupFilters, 0);
		setTimeout(patchSetupFilters, 500);
		bindScopeChange();
	});
})();
