(function () {
	"use strict";

	const STYLE_ID = "ct-native-frappe-controls-compat";
	const VERSION = "9";

	window.ctNativeFrappeControlsCompat = {
		version: VERSION,
		stylesInstalled: false,
		listViewPatched: false,
		currentListMenuRepaired: false,
		currentListToolbarRepaired: false,
		columnWidthsMenuRepaired: false,
		listColumnResizeInstalled: false,
		columnResizeHandleCount: 0,
	};

	console.info("[CT Native Compat] loaded v" + VERSION);

	function installStyles() {
		const existing = document.getElementById(STYLE_ID);
		if (existing) existing.remove();

		const style = document.createElement("style");
		style.id = STYLE_ID;
		style.textContent = `
/* Keep Construction theme visual only. Frappe native controls must remain usable. */
html.ct-enterprise .page-actions,
html.ct-enterprise .page-head-actions,
html.ct-enterprise .standard-actions,
html.ct-enterprise .custom-actions {
	overflow: visible !important;
	pointer-events: auto !important;
}

html.ct-enterprise .page-actions .dropdown,
html.ct-enterprise .page-head-actions .dropdown,
html.ct-enterprise .standard-actions .dropdown,
html.ct-enterprise .custom-actions .dropdown,
html.ct-enterprise .page-actions .btn-group,
html.ct-enterprise .page-head-actions .btn-group,
html.ct-enterprise .standard-actions .btn-group,
html.ct-enterprise .custom-actions .btn-group {
	overflow: visible !important;
	pointer-events: auto !important;
}

html.ct-enterprise .page-actions .dropdown-menu,
html.ct-enterprise .page-head-actions .dropdown-menu,
html.ct-enterprise .standard-actions .dropdown-menu,
html.ct-enterprise .custom-actions .dropdown-menu {
	display: none;
	overflow: visible !important;
	pointer-events: auto !important;
	z-index: 1055 !important;
}

html.ct-enterprise .page-actions .dropdown-menu.show,
html.ct-enterprise .page-head-actions .dropdown-menu.show,
html.ct-enterprise .standard-actions .dropdown-menu.show,
html.ct-enterprise .custom-actions .dropdown-menu.show,
html.ct-enterprise .page-actions .dropdown.open .dropdown-menu,
html.ct-enterprise .page-head-actions .dropdown.open .dropdown-menu,
html.ct-enterprise .standard-actions .dropdown.open .dropdown-menu,
html.ct-enterprise .custom-actions .dropdown.open .dropdown-menu {
	display: block !important;
}

html.ct-enterprise .page-actions .menu-btn-group .dropdown-menu a,
html.ct-enterprise .page-head-actions .menu-btn-group .dropdown-menu a,
html.ct-enterprise .standard-actions .menu-btn-group .dropdown-menu a,
html.ct-enterprise .custom-actions .menu-btn-group .dropdown-menu a {
	pointer-events: auto !important;
}

html.ct-enterprise .inner-toolbar,
html.ct-enterprise .custom-actions {
	overflow: visible !important;
	pointer-events: auto !important;
}

html.ct-enterprise .ct-native-list-settings {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	visibility: visible !important;
	opacity: 1 !important;
	pointer-events: auto !important;
	white-space: nowrap !important;
}

html.ct-enterprise .list-row-head .list-row-col {
	position: relative !important;
	overflow: visible !important;
}

html.ct-enterprise .frappe-list .result,
html.ct-enterprise .frappe-list .result .list-row-container,
html.ct-enterprise .frappe-list .result .list-row-head,
html.ct-enterprise .frappe-list .result .list-row-head .level-left {
	overflow: visible !important;
}

html.ct-enterprise .ct-list-resize-handle {
	position: absolute !important;
	top: 0 !important;
	bottom: 0 !important;
	inset-inline-end: -6px !important;
	width: 14px !important;
	z-index: 25 !important;
	cursor: col-resize !important;
	pointer-events: auto !important;
	border-inline-end: 2px solid transparent !important;
}

html.ct-enterprise .ct-list-resize-handle:hover,
html.ct-enterprise .ct-list-resize-handle.ct-active {
	border-inline-end-color: var(--ct-primary, var(--primary)) !important;
	background: color-mix(in srgb, var(--ct-primary, var(--primary)) 18%, transparent) !important;
}

html.ct-enterprise.ct-list-resizing,
html.ct-enterprise.ct-list-resizing * {
	cursor: col-resize !important;
	user-select: none !important;
}

/* Child table native "Configure Columns" gear. */
html.ct-enterprise .form-grid .grid-heading-row,
html.ct-enterprise .form-grid .grid-heading-row .grid-row,
html.ct-enterprise .form-grid .grid-heading-row .grid-static-col {
	overflow: visible !important;
}

html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer,
html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer a {
	cursor: pointer !important;
	pointer-events: auto !important;
	opacity: 1 !important;
	visibility: visible !important;
}

html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer a {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	min-width: 24px !important;
	min-height: 24px !important;
	color: var(--ct-text, var(--text)) !important;
}

html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer svg,
html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer .icon {
	opacity: 0.8 !important;
	visibility: visible !important;
	pointer-events: none !important;
}

html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer:hover svg,
html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer:hover .icon {
	opacity: 1 !important;
	color: var(--ct-primary, var(--primary)) !important;
}

/* Frappe DataTable resize / rearrange affordances. */
html.ct-enterprise .datatable .dt-header,
html.ct-enterprise .datatable .dt-cell--header,
html.ct-enterprise .datatable .dt-cell__content {
	overflow: visible !important;
}

html.ct-enterprise .datatable .dt-cell__resize-handle {
	display: block !important;
	opacity: 1 !important;
	visibility: visible !important;
	pointer-events: auto !important;
	z-index: 4 !important;
	width: 8px !important;
	cursor: col-resize !important;
}

html.ct-enterprise .datatable .dt-cell__resize-handle:hover {
	background: var(--ct-primary, var(--primary)) !important;
}

/* Native settings dialogs: preserve Frappe drag/reorder/check controls. */
html.ct-enterprise .modal [data-fieldname="fields_html"] .control-input-wrapper,
html.ct-enterprise .modal .selected-fields {
	display: block !important;
	overflow: visible !important;
	pointer-events: auto !important;
}

html.ct-enterprise .modal .fields_order,
html.ct-enterprise .modal .fields_order.sortable,
html.ct-enterprise .modal .fields_order.sortable-handle {
	align-items: center !important;
	min-height: 32px !important;
	overflow: visible !important;
	cursor: grab !important;
	pointer-events: auto !important;
	opacity: 1 !important;
	visibility: visible !important;
}

html.ct-enterprise .modal .fields_order .row {
	width: 100% !important;
	min-width: 0 !important;
}

html.ct-enterprise .modal .sortable-handle,
html.ct-enterprise .modal .fields_order svg,
html.ct-enterprise .modal .fields_order .icon,
html.ct-enterprise .modal .remove-field,
html.ct-enterprise .modal .add-new-fields {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	opacity: 1 !important;
	visibility: visible !important;
	pointer-events: auto !important;
	cursor: pointer !important;
	color: var(--ct-text, var(--text-color, var(--text))) !important;
}

html.ct-enterprise .modal .sortable-handle,
html.ct-enterprise .modal .fields_order .col-1:first-child a {
	cursor: grab !important;
}

html.ct-enterprise .modal .column-width,
html.ct-enterprise .modal .sticky-column,
html.ct-enterprise .modal .unit-checkbox,
html.ct-enterprise .modal [data-fieldname="fields"] .checkbox,
html.ct-enterprise .modal [data-fieldname="fields_html"] .checkbox {
	pointer-events: auto !important;
	opacity: 1 !important;
	visibility: visible !important;
}

html.ct-enterprise .modal .column-width {
	display: inline-block !important;
	width: 80px !important;
	min-width: 64px !important;
	height: 24px !important;
	text-align: right !important;
}

html.ct-enterprise .modal .sticky-column {
	display: inline-block !important;
	width: 18px !important;
	height: 18px !important;
	margin: 6px auto !important;
}

html.ct-enterprise .form-grid .grid-heading-row .grid-static-col.pointer {
	display: flex !important;
	flex: 0 0 32px !important;
	max-width: 32px !important;
	align-items: center !important;
	justify-content: center !important;
}
`;
		document.head.appendChild(style);
		window.ctNativeFrappeControlsCompat.stylesInstalled = true;
	}

	function patchListViewMenu() {
		if (!window.frappe || !frappe.views || !frappe.views.ListView) return;
		const proto = frappe.views.ListView.prototype;
		if (!proto || proto.__ct_native_menu_patched) return;

		const originalGetMenuItems = proto.get_menu_items;
		if (typeof originalGetMenuItems !== "function") return;

		proto.get_menu_items = function () {
			const items = originalGetMenuItems.apply(this, arguments) || [];
			const hasListSettings = items.some((item) => item && item.label === __("List Settings"));
			if (hasListSettings) return items;

			items.push({
				label: __("List Settings"),
				standard: true,
				action: () => {
					if (frappe.user && frappe.user.has_role && frappe.user.has_role("System Manager")) {
						this.show_list_settings();
					} else {
						frappe.msgprint({
							title: __("Permission Required"),
							indicator: "orange",
							message: __(
								"List Settings is a native Frappe system-level setting. You need the System Manager role to change list columns globally."
							),
						});
					}
				},
			});
			return items;
		};

		proto.__ct_native_menu_patched = true;
		window.ctNativeFrappeControlsCompat.listViewPatched = true;
	}

	function patchListViewRenderHooks() {
		if (!window.frappe || !frappe.views || !frappe.views.ListView) return;
		const proto = frappe.views.ListView.prototype;
		if (!proto || proto.__ct_native_resize_render_patched) return;

		["render_header", "render_list"].forEach((methodName) => {
			const original = proto[methodName];
			if (typeof original !== "function") return;
			proto[methodName] = function () {
				const result = original.apply(this, arguments);
				setTimeout(() => installListColumnResizeHandles(this), 0);
				setTimeout(() => installListColumnResizeHandles(this), 150);
				return result;
			};
		});

		proto.__ct_native_resize_render_patched = true;
	}

	function markNativeSettingsButtons() {
		if (!window.frappe || !frappe.views || !frappe.views.ListView) return;
		$(".page-actions .menu-btn-group, .page-head-actions .menu-btn-group").attr(
			"data-ct-native-menu",
			"1"
		);
		$(".grid-heading-row .grid-static-col.pointer").attr(
			"title",
			__("Configure Columns")
		);
	}

	function canUseSystemListSettings() {
		return !!(frappe.user && frappe.user.has_role && frappe.user.has_role("System Manager"));
	}

	function showListSettingsPermissionMessage() {
		frappe.msgprint({
			title: __("Permission Required"),
			indicator: "orange",
			message: __(
				"List Settings is a native Frappe system-level setting. You need the System Manager role to change list columns globally."
			),
		});
	}

	function openCurrentListSettings(listview) {
		if (!listview) return;
		if (canUseSystemListSettings()) {
			listview.show_list_settings();
		} else {
			showListSettingsPermissionMessage();
		}
	}

	function repairCurrentListMenu() {
		const listview = getCurrentListView();
		if (!listview || !listview.page || !listview.page.menu) return;

		const label = __("List Settings");
		const encoded = encodeURIComponent(label);
		const exists = listview.page.menu.find(
			`li[data-label="${encoded}"], li > a.grey-link > span[data-label="${encoded}"], li > a.grey-link > .menu-item-label`
		);
		const exactExists = exists.filter(function () {
			return ($(this).text() || "").trim() === label;
		});
		if (exactExists.length) {
			window.ctNativeFrappeControlsCompat.currentListMenuRepaired = true;
		} else {
			listview.page.add_menu_item(label, () => openCurrentListSettings(listview), true);
		}

		addListColumnWidthsMenuItem(listview);
		window.ctNativeFrappeControlsCompat.currentListMenuRepaired = true;
	}

	function getCurrentListView() {
		const route = frappe.get_route ? frappe.get_route() || [] : [];
		if (route[0] !== "List" || !route[1]) return null;

		if (frappe.get_list_view) {
			const listview = frappe.get_list_view(route[1]);
			if (listview && listview.page) return listview;
		}
		if (window.cur_list && window.cur_list.page && window.cur_list.doctype === route[1]) {
			return window.cur_list;
		}
		return null;
	}

	function repairCurrentListToolbar() {
		const listview = getCurrentListView();
		if (!listview || !listview.page || !listview.page.add_inner_button) return;

		const label = __("List Settings");
		const encoded = encodeURIComponent(label);
		const exists = listview.page.inner_toolbar.find(
			`button[data-label="${encoded}"], .inner-group-button[data-label="${encoded}"]`
		);
		if (exists.length) {
			addListColumnWidthsButton(listview);
			window.ctNativeFrappeControlsCompat.currentListToolbarRepaired = true;
			return;
		}

		const button = listview.page.add_inner_button(label, () => openCurrentListSettings(listview));
		button &&
			button
				.addClass("ct-native-list-settings")
				.attr("title", __("Configure visible columns, column order, and list settings"));
		if (listview.page.inner_toolbar) {
			listview.page.inner_toolbar.removeClass("hide hidden").css({
				display: "",
				visibility: "visible",
				opacity: 1,
			});
		}
		addListColumnWidthsButton(listview);
		window.ctNativeFrappeControlsCompat.currentListToolbarRepaired = true;
	}

	function getListWidthStorageKey(listview) {
		const user = frappe.session && frappe.session.user ? frappe.session.user : "guest";
		return ["ct_list_column_widths", user, listview.doctype].join(":");
	}

	function getStoredListWidths(listview) {
		try {
			return JSON.parse(localStorage.getItem(getListWidthStorageKey(listview)) || "{}") || {};
		} catch (e) {
			return {};
		}
	}

	function saveStoredListWidths(listview, widths) {
		localStorage.setItem(getListWidthStorageKey(listview), JSON.stringify(widths || {}));
	}

	function getResizableListColumns(listview) {
		if (!listview || !Array.isArray(listview.columns)) return [];
		return listview.columns
			.filter((col) => col && col.df && col.df.fieldname)
			.map((col) => ({
				fieldname: col.df.fieldname,
				label: __(col.df.label || col.df.fieldname, null, col.df.parent),
			}));
	}

	function cssEscape(value) {
		if (window.CSS && CSS.escape) return CSS.escape(value);
		return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
	}

	function applyListColumnWidths(listview) {
		if (!listview || !listview.$result) return;
		const widths = getStoredListWidths(listview);
		Object.keys(widths).forEach((fieldname) => {
			const width = Math.max(60, Math.min(800, cint(widths[fieldname]) || 0));
			if (!width) return;
			listview.$result.find(`.level-left .list-row-col.${cssEscape(fieldname)}`).css({
				width: width + "px",
				minWidth: width + "px",
				maxWidth: width + "px",
				flex: "0 0 " + width + "px",
			});
		});
	}

	function installListColumnResizeHandles(listview) {
		if (!listview || !listview.$result || frappe.is_mobile()) return;
		const columns = getResizableListColumns(listview);
		if (!columns.length) return;

		applyListColumnWidths(listview);

		const header = listview.$result.find(".list-row-head").first();
		if (!header.length) return;
		header.find(".ct-list-resize-handle").remove();

		columns.forEach((col) => {
			const cell = header.find(`.list-row-col.${cssEscape(col.fieldname)}`).first();
			if (!cell.length) return;

			const handle = $('<span class="ct-list-resize-handle" aria-hidden="true"></span>');
			handle.attr("title", __("Drag to resize column"));
			handle.attr("data-fieldname", col.fieldname);
			cell.append(handle);
		});
		window.ctNativeFrappeControlsCompat.listColumnResizeInstalled = true;
		window.ctNativeFrappeControlsCompat.columnResizeHandleCount =
			header.find(".ct-list-resize-handle").length;
	}

	function installListResizeDelegatedEvents() {
		$(document)
			.off("click.ctListResizeHandle")
			.on("click.ctListResizeHandle", ".ct-list-resize-handle", (event) => {
				event.preventDefault();
				event.stopPropagation();
			});

		$(document)
			.off("mousedown.ctListResizeHandle")
			.on("mousedown.ctListResizeHandle", ".ct-list-resize-handle", function (event) {
				const listview = getCurrentListView();
				if (!listview) return;
				const fieldname = $(this).attr("data-fieldname");
				if (!fieldname) return;
				const headerCell = $(this).closest(".list-row-col");

				event.preventDefault();
				event.stopPropagation();
				const startX = event.pageX;
				const startWidth = headerCell.outerWidth();
				const isRtl = $("html").attr("dir") === "rtl" || $("body").css("direction") === "rtl";
				$(this).addClass("ct-active");
				$("html").addClass("ct-list-resizing");

				$(document)
					.off(".ctListResizeDrag")
					.on("mousemove.ctListResizeDrag", (moveEvent) => {
						const delta = isRtl ? startX - moveEvent.pageX : moveEvent.pageX - startX;
						const width = Math.max(60, Math.min(800, Math.round(startWidth + delta)));
						const widths = getStoredListWidths(listview);
						widths[fieldname] = width;
						saveStoredListWidths(listview, widths);
						applyListColumnWidths(listview);
					})
					.on("mouseup.ctListResizeDrag", () => {
						$(".ct-list-resize-handle.ct-active").removeClass("ct-active");
						$("html").removeClass("ct-list-resizing");
						$(document).off(".ctListResizeDrag");
					});
			});
	}

	function addListColumnWidthsMenuItem(listview) {
		if (!listview || !listview.page || !listview.page.menu) return;
		const label = __("Column Widths");
		const encoded = encodeURIComponent(label);
		const exists = listview.page.menu
			.find(`li > a.grey-link > span[data-label="${encoded}"], li > a.grey-link > .menu-item-label`)
			.filter(function () {
				return ($(this).text() || "").trim() === label;
			});
		if (exists.length) return;

		listview.page.add_menu_item(label, () => showListColumnWidthsDialog(listview), true);
		window.ctNativeFrappeControlsCompat.columnWidthsMenuRepaired = true;
	}

	function addListColumnWidthsButton(listview) {
		if (!listview || !listview.page || !listview.page.add_inner_button) return;
		const label = __("Column Widths");
		const encoded = encodeURIComponent(label);
		const exists = listview.page.inner_toolbar.find(
			`button[data-label="${encoded}"], .inner-group-button[data-label="${encoded}"]`
		);
		if (exists.length) return;

		const button = listview.page.add_inner_button(label, () => showListColumnWidthsDialog(listview));
		button &&
			button
				.addClass("ct-native-column-widths")
				.attr("title", __("Set list column widths"));
		if (listview.page.inner_toolbar) {
			listview.page.inner_toolbar.removeClass("hide hidden").css({
				display: "",
				visibility: "visible",
				opacity: 1,
			});
		}
		window.ctNativeFrappeControlsCompat.columnWidthsMenuRepaired = true;
	}

	function showListColumnWidthsDialog(listview) {
		const columns = getResizableListColumns(listview);
		const widths = getStoredListWidths(listview);
		const fields = columns.map((col) => ({
			label: col.label,
			fieldname: col.fieldname,
			fieldtype: "Int",
			default: cint(widths[col.fieldname]) || "",
			description: __("Width in pixels. Leave empty to use automatic width."),
		}));

		const dialog = new frappe.ui.Dialog({
			title: __("{0} Column Widths", [__(listview.doctype)]),
			fields,
		});
		dialog.set_primary_action(__("Apply"), () => {
			const values = dialog.get_values() || {};
			const nextWidths = {};
			columns.forEach((col) => {
				const width = cint(values[col.fieldname]);
				if (width) nextWidths[col.fieldname] = Math.max(60, Math.min(800, width));
			});
			saveStoredListWidths(listview, nextWidths);
			applyListColumnWidths(listview);
			installListColumnResizeHandles(listview);
			dialog.hide();
		});
		dialog.set_secondary_action_label(__("Reset"));
		dialog.set_secondary_action(() => {
			saveStoredListWidths(listview, {});
			location.reload();
		});
		dialog.show();
	}

	function refreshCompat() {
		try {
			installStyles();
			patchListViewMenu();
			patchListViewRenderHooks();
			installListResizeDelegatedEvents();
			markNativeSettingsButtons();
			repairCurrentListMenu();
			repairCurrentListToolbar();
			installListColumnResizeHandles(getCurrentListView());
		} catch (e) {
			console.warn("[CT Native Compat] refresh skipped", e);
		}
	}

	function refreshCompatRepeatedly() {
		refreshCompat();
		[250, 750, 1500, 3000, 5000].forEach(function (delay) {
			setTimeout(refreshCompat, delay);
		});
	}

	$(document).on("page-change form-refresh list-refresh", function () {
		refreshCompatRepeatedly();
	});

	$(document).ready(function () {
		refreshCompatRepeatedly();
	});
})();
