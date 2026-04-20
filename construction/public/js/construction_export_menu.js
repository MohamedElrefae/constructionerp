/**
 * ConstructionExportMenu
 *
 * Reusable export dropdown menu for the entire Construction app.
 * Renders a styled dropdown button with icons for Excel, PDF, and Print options.
 * Can be used on any Frappe form page by passing export definitions.
 *
 * Usage:
 *   var menu = new ConstructionExportMenu(frm, export_items);
 *   // export_items is an array of { label, icon, action, separator_before }
 *
 * Icons use Font Awesome (available in Frappe).
 */
class ConstructionExportMenu {
	/**
	 * @param {Object} frm - Frappe form object
	 * @param {Array} items - Array of menu item definitions:
	 *   { label: string, icon: string (fa class), action: Function, separator_before?: boolean }
	 */
	constructor(frm, items) {
		this.frm = frm;
		this.items = items || [];
		this._$btn_group = null;
		this.render();
	}

	render() {
		// Remove any existing export menu
		this.frm.page.custom_actions.find(".construction-export-menu").remove();

		var $group = $(
			'<div class="btn-group construction-export-menu" style="margin-left:8px;"></div>'
		);

		// Main button
		var $btn = $(
			'<button class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">' +
				'<span class="hidden-xs">' +
				'<i class="fa fa-download" style="margin-right:4px;"></i> ' +
				__("Export") +
				"</span>" +
				'<span class="visible-xs"><i class="fa fa-download"></i></span>' +
				' <span class="caret"></span>' +
				"</button>"
		);

		var $menu = $(
			'<ul class="dropdown-menu dropdown-menu-right" style="min-width:220px;"></ul>'
		);

		var self = this;
		this.items.forEach(function (item) {
			if (item.separator_before) {
				$menu.append('<li class="divider" role="separator"></li>');
			}
			var icon_html = item.icon
				? '<i class="' +
				  item.icon +
				  '" style="width:18px;margin-right:6px;text-align:center;"></i>'
				: "";
			var $li = $(
				'<li><a href="#" style="display:flex;align-items:center;padding:6px 16px;">' +
					icon_html +
					item.label +
					"</a></li>"
			);
			$li.find("a").on("click", function (e) {
				e.preventDefault();
				if (item.action) item.action();
			});
			$menu.append($li);
		});

		$group.append($btn).append($menu);

		// Insert after the Rename button area (before Actions dropdown)
		// We prepend to custom_actions so it appears in the toolbar
		this.frm.page.custom_actions.prepend($group);

		this._$btn_group = $group;
	}

	destroy() {
		if (this._$btn_group) {
			this._$btn_group.remove();
			this._$btn_group = null;
		}
	}
}

/**
 * ConstructionViewMenu
 *
 * Reusable view-mode toggle button for the Construction app.
 * Shows a dropdown with view options (Tree, Table, etc.)
 *
 * Usage:
 *   var view_menu = new ConstructionViewMenu(frm, view_items, current_view);
 */
class ConstructionViewMenu {
	/**
	 * @param {Object} frm - Frappe form object
	 * @param {Array} items - Array of view definitions:
	 *   { label: string, icon: string, value: string, action: Function }
	 * @param {string} [current_view] - Currently active view value
	 */
	constructor(frm, items, current_view) {
		this.frm = frm;
		this.items = items || [];
		this.current_view = current_view || (items.length > 0 ? items[0].value : "");
		this._$btn_group = null;
		this.render();
	}

	render() {
		// Remove any existing view menu
		this.frm.page.custom_actions.find(".construction-view-menu").remove();

		var self = this;
		var current_item = this.items.find(function (i) {
			return i.value === self.current_view;
		});
		var current_icon = current_item ? current_item.icon : "fa fa-eye";
		var current_label = current_item ? current_item.label : __("View");

		var $group = $(
			'<div class="btn-group construction-view-menu" style="margin-left:8px;"></div>'
		);

		var $btn = $(
			'<button class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">' +
				'<span class="hidden-xs">' +
				'<i class="' +
				current_icon +
				'" style="margin-right:4px;"></i> ' +
				current_label +
				"</span>" +
				'<span class="visible-xs"><i class="' +
				current_icon +
				'"></i></span>' +
				' <span class="caret"></span>' +
				"</button>"
		);

		var $menu = $(
			'<ul class="dropdown-menu dropdown-menu-right" style="min-width:180px;"></ul>'
		);

		this.items.forEach(function (item) {
			var icon_html = item.icon
				? '<i class="' +
				  item.icon +
				  '" style="width:18px;margin-right:6px;text-align:center;"></i>'
				: "";
			var active_class =
				item.value === self.current_view
					? ' style="display:flex;align-items:center;padding:6px 16px;font-weight:bold;background:#f0f4f7;"'
					: ' style="display:flex;align-items:center;padding:6px 16px;"';
			var check_html =
				item.value === self.current_view
					? '<i class="fa fa-check" style="margin-left:auto;color:#36b37e;"></i>'
					: "";
			var $li = $(
				'<li><a href="#"' +
					active_class +
					">" +
					icon_html +
					item.label +
					check_html +
					"</a></li>"
			);
			$li.find("a").on("click", function (e) {
				e.preventDefault();
				self.current_view = item.value;
				if (item.action) item.action();
			});
			$menu.append($li);
		});

		$group.append($btn).append($menu);

		// Prepend so it appears before export menu
		this.frm.page.custom_actions.prepend($group);

		this._$btn_group = $group;
	}

	destroy() {
		if (this._$btn_group) {
			this._$btn_group.remove();
			this._$btn_group = null;
		}
	}
}

// Node.js compatibility for testing
if (typeof module !== "undefined") {
	module.exports = {
		ConstructionExportMenu: ConstructionExportMenu,
		ConstructionViewMenu: ConstructionViewMenu,
	};
}
