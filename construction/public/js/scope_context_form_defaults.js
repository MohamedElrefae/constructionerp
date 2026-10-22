(function () {
	"use strict";

	function applyProjectAccent(frm) {
		if (!frappe.meta.has_field(frm.meta, "project")) return;
		const hasProject = Boolean(frm.doc.project);
		const $wrapper = $(`.frappe-control[data-fieldname="project"]`);
		if (!$wrapper.length) return;

		$wrapper.toggleClass("ct-boq-step-accent", !hasProject);
		$wrapper.toggleClass("ct-boq-step-blocked", false);

		const $help = $wrapper.find(".help").first();
		if ($help.length) {
			$wrapper.toggleClass("ct-boq-has-inline-hint", !hasProject);
			$help.find(".ct-boq-inline-hint").remove();
			if (!hasProject) {
				$help.append(
					$("<span>", {
						class: "ct-boq-inline-hint",
						text: __("Select Project first"),
						title: __("Select Project first"),
					})
				);
			}
		}
	}

	frappe.ui.form.on("*", {
		onload: function (frm) {
			if (!window.scopeContext || !window.scopeContext.enabled) return;
			if (!frm.is_new()) return;

			var dims = window.scopeContext.enabledDimensions;
			var scope = window.scopeContext.getValidatedCurrentScope();
			var meta = frm.meta;

			function set_default_silently(fieldname, value) {
				frm.doc[fieldname] = value;
				frm.refresh_field(fieldname);
			}

			if (
				dims.company &&
				scope.company &&
				frappe.meta.has_field(meta, "company") &&
				!frm.doc.company
			) {
				set_default_silently("company", scope.company);
			}
			if (
				dims.cost_center &&
				scope.cost_center &&
				frappe.meta.has_field(meta, "cost_center") &&
				!frm.doc.cost_center
			) {
				set_default_silently("cost_center", scope.cost_center);
			}
			if (
				dims.project &&
				scope.project &&
				frappe.meta.has_field(meta, "project") &&
				!frm.doc.project
			) {
				set_default_silently("project", scope.project);
			}
			if (
				dims.department &&
				scope.department &&
				frappe.meta.has_field(meta, "department") &&
				!frm.doc.department
			) {
				set_default_silently("department", scope.department);
			}
		},

		onload_post_render: function (frm) {
			if (!window.scopeContext || !window.scopeContext.enabled) return;
			if (!frm.is_new()) return;
			applyProjectAccent(frm);
			setTimeout(() => applyProjectAccent(frm), 150);
			setTimeout(() => applyProjectAccent(frm), 600);
		},

		project: function (frm) {
			if (!window.scopeContext || !window.scopeContext.enabled) return;
			applyProjectAccent(frm);
		},
	});
})();
