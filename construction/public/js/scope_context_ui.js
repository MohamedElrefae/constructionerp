(function () {
	"use strict";

	function initialize() {
		if (!window.scopeContext || !window.ctTopbar) return false;

		console.log("[ScopeContext UI] enabled=" + window.scopeContext.enabled);

		var sc = window.scopeContext;
		// The core object is always present so downstream integrations can make
		// safe feature-flag checks.  Do not register a visible selector when the
		// server has disabled the feature, though.
		if (!sc.enabled) return true;

		function populateDropdown(
			$context,
			id,
			items,
			valueField,
			labelField,
			placeholder,
			currentValue
		) {
			var $menu = $context ? $context.find("#" + id + "-menu") : $("#" + id + "-menu");
			var $label = $context ? $context.find("#" + id + "-label") : $("#" + id + "-label");
			if (!$menu.length || !$label.length) return;
			$menu.empty();

			var currentLabel = placeholder || "\u2014";
			$menu.append(
				'<a class="dropdown-item" href="#" data-value="">' +
					(placeholder || "\u2014") +
					"</a>"
			);

			(items || []).forEach(function (item) {
				var val = item[valueField || "name"] || "";
				var label = item[labelField || valueField || "name"] || "";
				if (val === currentValue) {
					currentLabel = label;
				}
				var $item = $('<a class="dropdown-item" href="#"></a>');
				$item.attr("data-value", val);
				$item.text(label);
				$menu.append($item);
			});

			$label.text(currentLabel);
		}

		function filterBy(items, field, value) {
			if (!value) return items || [];
			return (items || []).filter(function (item) {
				return item[field] === value;
			});
		}

		function getDescendantCCNames(ccName) {
			if (!ccName) return [];
			var scopeCC = (sc.hierarchy.cost_centers || []).find(function (cc) {
				return cc.name === ccName;
			});
			if (!scopeCC) return [ccName];
			return (sc.hierarchy.cost_centers || [])
				.filter(function (cc) {
					return cc.lft >= scopeCC.lft && cc.rgt <= scopeCC.rgt;
				})
				.map(function (cc) {
					return cc.name;
				});
		}

		function renderDropdown(id, placeholder) {
			return (
				'<div class="dropdown ct-scope-dropdown" id="' +
				id +
				'-wrapper">' +
				'<button class="btn-reset nav-link text-muted dropdown-toggle ct-scope-btn" type="button" aria-haspopup="true" aria-expanded="false">' +
				'<span id="' +
				id +
				'-label">' +
				placeholder +
				"</span></button>" +
				'<div class="dropdown-menu" id="' +
				id +
				'-menu"></div>' +
				"</div>"
			);
		}

		function render() {
			var h = sc.hierarchy || {};
			var dims = sc.enabledDimensions || {};
			var parts = [
				'<div class="ct-scope-selectors" style="display:flex;align-items:center;gap:4px;">',
			];
			var sep = false;

			if (dims.company) {
				parts.push(renderDropdown("ct-scope-company", "Company"));
				sep = true;
			}
			if (dims.cost_center) {
				if (sep) parts.push('<span class="ct-scope-separator text-muted">\u203a</span>');
				parts.push(renderDropdown("ct-scope-cost-center", "Cost Center"));
				sep = true;
			}
			if (dims.project) {
				if (sep) parts.push('<span class="ct-scope-separator text-muted">\u203a</span>');
				parts.push(renderDropdown("ct-scope-project", "Project"));
				sep = true;
			}
			if (dims.department) {
				if (sep) parts.push('<span class="ct-scope-separator text-muted">\u203a</span>');
				parts.push(renderDropdown("ct-scope-department", "Department"));
			}

			parts.push("</div>");
			return parts.join("\n");
		}

		function updateSelects(element) {
			var $el = element
				? $(element)
				: $(".ct-topbar-item[data-ct-topbar='scope-context-selectors']");
			if (!$el.length) return;

			var h = sc.hierarchy || {};
			var cur = sc.getValidatedCurrentScope();
			var dims = sc.enabledDimensions || {};

			$el.each(function () {
				var $container = $(this);
				if (dims.company) {
					populateDropdown(
						$container,
						"ct-scope-company",
						h.companies,
						"name",
						"company_name",
						"Company",
						cur.company
					);
				}

				if (dims.cost_center) {
					var filteredCC = filterBy(h.cost_centers, "company", cur.company);
					populateDropdown(
						$container,
						"ct-scope-cost-center",
						filteredCC,
						"name",
						"cost_center_name",
						"Cost Center",
						cur.cost_center
					);
				}

				if (dims.project) {
					var filteredProjects;
					if (cur.cost_center) {
						var descendantCCs = getDescendantCCNames(cur.cost_center);
						filteredProjects = (h.projects || []).filter(function (p) {
							return (
								p.company === cur.company &&
								descendantCCs.indexOf(p.cost_center) !== -1
							);
						});
					} else {
						filteredProjects = filterBy(h.projects, "company", cur.company);
					}
					populateDropdown(
						$container,
						"ct-scope-project",
						filteredProjects,
						"name",
						"project_name",
						"Project",
						cur.project
					);
				}

				if (dims.department) {
					var filteredDepts;
					if (cur.cost_center) {
						var descendantCCsD = getDescendantCCNames(cur.cost_center);
						filteredDepts = (h.departments || []).filter(function (d) {
							return (
								d.company === cur.company &&
								descendantCCsD.indexOf(d.cost_center) !== -1
							);
						});
					} else {
						filteredDepts = filterBy(h.departments, "company", cur.company);
					}
					populateDropdown(
						$container,
						"ct-scope-department",
						filteredDepts,
						"name",
						"department_name",
						"Department",
						cur.department
					);
				}
			});
		}

		function _showFirstLoginModal() {
			if (sc.getValidatedCurrentScope().company) return;
			var companies = (sc.hierarchy && sc.hierarchy.companies) || [];
			if (companies.length === 0) {
				frappe.show_alert({
					message: __("No companies assigned. Contact your administrator."),
					indicator: "red",
				});
				return;
			}
			if (companies.length === 1) {
				sc.setCompany(companies[0].name);
				return;
			}

			var dialog = new frappe.ui.Dialog({
				title: __("Select Your Working Company"),
				fields: [
					{
						fieldname: "company",
						fieldtype: "Link",
						options: "Company",
						label: __("Company"),
						reqd: 1,
						get_query: function () {
							return {
								filters: [
									[
										"name",
										"in",
										companies.map(function (c) {
											return c.name;
										}),
									],
								],
							};
						},
					},
				],
				primary_action_label: __("Confirm"),
				primary_action: function (values) {
					sc.setCompany(values.company);
					dialog.hide();
					dialog.$wrapper.find(".modal-backdrop").remove();
				},
			});

			dialog.show();
			dialog.get_close_btn().hide();
		}

		function setup(element) {
			var $el = $(element);
			updateSelects($el);

			var dims = sc.enabledDimensions || {};

			$el.on("click.ctScope", ".dropdown-toggle", function (e) {
				e.preventDefault();
				e.stopPropagation();
				var $btn = $(this);
				var $wrapper = $btn.closest(".dropdown");
				var $menu = $wrapper.find(".dropdown-menu");

				var isOpen = $menu.hasClass("show");

				$(".ct-scope-dropdown .dropdown-menu.show").removeClass("show");
				$('.ct-scope-dropdown .dropdown-toggle[aria-expanded="true"]').attr(
					"aria-expanded",
					"false"
				);

				if (!isOpen) {
					$menu.addClass("show");
					$btn.attr("aria-expanded", "true");
					var rect = $btn[0].getBoundingClientRect();
					$menu.css({
						position: "fixed",
						top: rect.bottom + 4 + "px",
						left: rect.left + "px",
						right: "auto",
						bottom: "auto",
						transform: "none",
					});
				}
			});

			$el.on("click.ctScope", ".dropdown-item", function (e) {
				e.preventDefault();
				e.stopPropagation();
				var $item = $(this);
				var val = $item.attr("data-value");
				var $wrapper = $item.closest(".dropdown");
				var id = $wrapper.attr("id").replace("-wrapper", "");

				$wrapper.find(".dropdown-menu").removeClass("show");
				$wrapper.find(".dropdown-toggle").attr("aria-expanded", "false");

				if (id === "ct-scope-company") sc.setCompany(val);
				else if (id === "ct-scope-cost-center") sc.setCostCenter(val);
				else if (id === "ct-scope-project") sc.setProject(val);
				else if (id === "ct-scope-department") sc.setDepartment(val);
			});

			$(document)
				.off("click.scopeContextDropdown")
				.on("click.scopeContextDropdown", function (e) {
					if (!$(e.target).closest(".ct-scope-dropdown").length) {
						$(".ct-scope-dropdown .dropdown-menu.show").removeClass("show");
						$(".ct-scope-dropdown .dropdown-toggle").attr("aria-expanded", "false");
					}
				});

			$(document)
				.off("scope:changed.scopeContextUI")
				.on("scope:changed.scopeContextUI", function (e, payload) {
					updateSelects();
				});

			if (dims.company) {
				_showFirstLoginModal();
			}
		}

		function teardown(element) {
			$(element).off(".ctScope");
		}

		window.ctTopbar.register({
			id: "scope-context-selectors",
			order: 20,
			render: render,
			setup: setup,
			teardown: teardown,
		});
		return true;
	}

	if (!initialize()) {
		var retryCount = 0;
		var retryTimer = setInterval(function () {
			if (initialize() || ++retryCount >= 50) {
				clearInterval(retryTimer);
			}
		}, 200);
	}
})();
