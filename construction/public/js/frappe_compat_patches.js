(function () {
	function patchTreeViewNewNodeGuard() {
		if (
			!window.frappe ||
			!frappe.views ||
			!frappe.views.TreeView ||
			!frappe.views.TreeView.prototype
		) {
			return false;
		}

		var proto = frappe.views.TreeView.prototype;
		if (proto.__ct_new_node_guard_patch) {
			return true;
		}

		var originalNewNode = proto.new_node;
		proto.new_node = function () {
			if (!this.tree || typeof this.tree.get_selected_node !== "function") {
				frappe.msgprint(__("Please select BOQ Header and load the tree first."));
				return;
			}
			return originalNewNode.apply(this, arguments);
		};

		proto.__ct_new_node_guard_patch = true;
		return true;
	}

	function patchSavedFiltersGroupLabel() {
		if (!window.frappe || !frappe.ui || !frappe.ui.Page || !frappe.ui.Page.prototype) {
			return false;
		}

		var proto = frappe.ui.Page.prototype;
		if (proto.__ct_saved_filters_group_patch) {
			return true;
		}

		var englishLabel = "Saved Filters";
		var englishDataLabel = encodeURIComponent(englishLabel);
		var translatedLabel = __(englishLabel);
		var translatedDataLabel = encodeURIComponent(translatedLabel);

		function isSavedFiltersLabel(label) {
			return label === englishLabel || label === translatedLabel;
		}

		function normalizeSavedFiltersGroup($group) {
			if (!$group || !$group.length) {
				return $group;
			}
			$group.attr("data-label", englishDataLabel);
			$group.attr("data-translated-label", translatedDataLabel);
			return $group;
		}

		var originalGetOrAdd = proto.get_or_add_inner_group_button;
		var originalGetInner = proto.get_inner_group_button;

		proto.get_or_add_inner_group_button = function (label, alignRight) {
			if (isSavedFiltersLabel(label)) {
				var $existing = this.inner_toolbar.find(
					'.inner-group-button[data-label="' + englishDataLabel + '"]'
				);
				if ($existing.length) {
					return normalizeSavedFiltersGroup($existing);
				}
			}

			var $group = originalGetOrAdd.call(this, label, alignRight);
			if (isSavedFiltersLabel(label)) {
				normalizeSavedFiltersGroup($group);
			}
			return $group;
		};

		proto.get_inner_group_button = function (label) {
			if (isSavedFiltersLabel(label)) {
				var $group = this.inner_toolbar.find(
					'.inner-group-button[data-label="' + englishDataLabel + '"]'
				);
				if ($group.length) {
					return normalizeSavedFiltersGroup($group);
				}
			}
			return originalGetInner.call(this, label);
		};

		normalizeSavedFiltersGroup(
			$('.inner-group-button[data-label="' + translatedDataLabel + '"]')
		);

		proto.__ct_saved_filters_group_patch = true;
		return true;
	}

	function patchSidebarWorkspaceNavigation() {
		if (
			!window.frappe ||
			!frappe.ui ||
			!frappe.ui.SidebarHeader ||
			!frappe.ui.SidebarHeader.prototype
		) {
			return false;
		}

		var proto = frappe.ui.SidebarHeader.prototype;
		if (proto.__ct_workspace_navigation_patch) return true;

		proto.add_app_item = function (item) {
			var icon = item.icon
				? frappe.utils.icon(item.icon)
				: item.icon_html || (item.icon_url ? '<img class="logo" src="' + item.icon_url + '">' : "");
			$(`<div class="dropdown-menu-item" data-name="${item.name}"
				data-app-route="${item.route || item.url || ""}">
				<a ${item.href ? `href="${item.href}"` : ""}>
					<div class="sidebar-item-icon">${icon}</div>
					<span class="menu-item-title">${item.label}</span>
				</a>
			</div>`).appendTo(this.dropdown_menu);
		};

		proto.setup_select_options = function () {
			this.dropdown_menu.find(".dropdown-menu-item").off("click").on("click", (e) => {
				var item = $(e.currentTarget);
				var name = item.attr("data-name");
				var currentItem = this.dropdown_items.find((entry) => entry.name == name);
				if (!currentItem) return;

				this.dropdown_menu.toggleClass("hidden");
				this.toggle_active();
				if (typeof currentItem.onClick === "function") {
					currentItem.onClick(item);
				} else if (currentItem.url) {
					frappe.set_route(currentItem.url);
				} else if (currentItem.route) {
					frappe.set_route(currentItem.route);
				}
			});
		};

		// Safety net: Frappe's built-in handler calls onClick unconditionally.
		// If our prototype override was not used, wrap it defensively.
		var originalSetupSelect = frappe.ui.SidebarHeader.prototype.setup_select_options;
		if (!proto.__ct_workspace_handler_wrapped && originalSetupSelect) {
			frappe.ui.SidebarHeader.prototype.setup_select_options = function () {
				originalSetupSelect.call(this);
				this.dropdown_menu.find(".dropdown-menu-item").off("click.ctsafe").on("click.ctsafe", (e) => {
					var item = $(e.currentTarget);
					var name = item.attr("data-name");
					var currentItem = this.dropdown_items.find((entry) => entry.name == name);
					if (!currentItem) return;
					if (typeof currentItem.onClick !== "function" && (currentItem.url || currentItem.route)) {
						e.preventDefault();
						e.stopPropagation();
						this.dropdown_menu.toggleClass("hidden");
						this.toggle_active();
						frappe.set_route(currentItem.url || currentItem.route);
					}
				});
			};
			proto.__ct_workspace_handler_wrapped = true;
		}

		proto.__ct_workspace_navigation_patch = true;
		return true;
	}

	function patchWorkspaceMenuNavigation() {
		if (
			!window.frappe ||
			!frappe.ui ||
			!frappe.ui.create_menu ||
			!frappe.ui.create_menu.prototype
		) {
			return false;
		}

		var proto = frappe.ui.create_menu.prototype;
		if (proto.__ct_workspace_menu_patch) return true;

		var originalAdd = proto.add_menu_item;
		proto.add_menu_item = function (item) {
			// Frappe gives workspace children no url when get_route_for_icon
			// returns undefined. Such items fall into the "no url, no onClick"
			// branch and do nothing. Give them a label-based workspace route.
			if (
				item &&
				!item.url &&
				!item.action &&
				!item.onClick &&
				!(item.items && item.items.length) &&
				item.label
			) {
				var label = item.label;
				item.onClick = function () {
					var slug = frappe.router && frappe.router.slug ? frappe.router.slug(label) : label.toLowerCase().replace(/ /g, "-");
					frappe.set_route("Workspaces", slug);
				};
			}
			return originalAdd.call(this, item);
		};

		proto.__ct_workspace_menu_patch = true;
		return true;
	}

	if (!patchSavedFiltersGroupLabel()) {
		$(document).on("app_ready", patchSavedFiltersGroupLabel);
		setTimeout(patchSavedFiltersGroupLabel, 1000);
	}

	if (!patchTreeViewNewNodeGuard()) {
		$(document).on("app_ready", patchTreeViewNewNodeGuard);
		setTimeout(patchTreeViewNewNodeGuard, 1000);
	}

	if (!patchSidebarWorkspaceNavigation()) {
		$(document).on("app_ready", patchSidebarWorkspaceNavigation);
		setTimeout(patchSidebarWorkspaceNavigation, 1000);
	}

	if (!patchWorkspaceMenuNavigation()) {
		$(document).on("app_ready", patchWorkspaceMenuNavigation);
		setTimeout(patchWorkspaceMenuNavigation, 1000);
	}
})();
