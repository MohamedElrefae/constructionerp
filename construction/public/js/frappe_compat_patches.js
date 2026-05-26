(function () {
	function patchTreeViewNewNodeGuard() {
		if (!window.frappe || !frappe.views || !frappe.views.TreeView || !frappe.views.TreeView.prototype) {
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

	if (!patchSavedFiltersGroupLabel()) {
		$(document).on("app_ready", patchSavedFiltersGroupLabel);
		setTimeout(patchSavedFiltersGroupLabel, 1000);
	}

	if (!patchTreeViewNewNodeGuard()) {
		$(document).on("app_ready", patchTreeViewNewNodeGuard);
		setTimeout(patchTreeViewNewNodeGuard, 1000);
	}
})();
