(function () {
	"use strict";

	var typography_fields = [
		"desk_font_family",
		"desk_font_size",
		"desk_font_weight",
		"sidebar_font_family",
		"sidebar_font_size",
		"sidebar_font_weight",
		"navbar_font_family",
		"navbar_font_size",
		"navbar_font_weight",
		"form_font_family",
		"form_font_size",
		"form_font_weight",
		"list_font_family",
		"list_font_size",
		"list_font_weight",
		"menu_font_family",
		"menu_font_size",
		"menu_font_weight",
	];

	frappe.ui.form.on("User Desk Theme", {
		refresh: function (frm) {
			hide_raw_typography_fields(frm);
			add_open_typography_button(frm);
			bind_typography_saved_event(frm);
		},
	});

	function hide_raw_typography_fields(frm) {
		["typography_section", "component_typography_section"]
			.concat(typography_fields)
			.forEach(function (fieldname) {
				if (frm.fields_dict[fieldname]) {
					frm.toggle_display(fieldname, false);
				}
			});
	}

	function add_open_typography_button(frm) {
		frm.add_custom_button(__("Open Typography Settings"), function () {
			if (window.ctTypography && window.ctTypography.showDialog) {
				window.ctTypography.showDialog();
			} else if (window.ctShowTypographySettings) {
				window.ctShowTypographySettings();
			} else {
				frappe.msgprint(__("Typography settings are still loading. Please try again."));
			}
		}).addClass("btn-primary");
	}

	function bind_typography_saved_event(frm) {
		if (frm._ct_typography_saved_bound || !window.jQuery) return;
		frm._ct_typography_saved_bound = true;

		$(document).on("ct-typography-saved.user-desk-theme", function () {
			if (frm.doc && frm.doc.user === frappe.session.user) {
				frm.reload_doc();
			}
		});
	}
})();
