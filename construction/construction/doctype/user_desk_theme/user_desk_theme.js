frappe.ui.form.on("User Desk Theme", {
	refresh(frm) {
		prepare_typography_form(frm);
		add_typography_dialog_action(frm);
		bind_typography_saved_event(frm);
		sync_current_user_typography(frm);
	},

	after_save(frm) {
		if (is_current_user_theme(frm)) {
			apply_current_form_typography(frm);
		}
	},
});

const TYPOGRAPHY_FIELDS = [
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

function prepare_typography_form(frm) {
	frm.$wrapper.addClass("ct-typography-form");

	const api = window.ctTypography || {};
	const desk_options = api.deskFontOptions ||
		"System Default\nInter\nArial\nHelvetica\nTahoma\nVerdana\nTrebuchet MS\nGeorgia\nTimes New Roman\nCourier New\nRoboto\nOpen Sans\nLato\nMontserrat\nPoppins\nNoto Sans\nNoto Sans Arabic\nCairo\nTajawal\nAlmarai";
	const component_options = api.componentFontOptions || ("Inherit\n" + desk_options);

	set_select_options(frm, "desk_font_family", desk_options);
	["sidebar", "navbar", "form", "list", "menu"].forEach((component) => {
		set_select_options(frm, `${component}_font_family`, component_options);
	});

	if (
		window.construction &&
		construction.ct_select_enhancer &&
		construction.ct_select_enhancer.scan
	) {
		setTimeout(() => construction.ct_select_enhancer.scan(), 100);
	}
}

function add_typography_dialog_action(frm) {
	if (!window.ctTypography || !window.ctTypography.showDialog) return;

	frm.add_custom_button(__("Typography Settings"), () => {
		window.ctTypography.showDialog();
	}, __("View"));
}

function sync_current_user_typography(frm) {
	if (!is_current_user_theme(frm) || !window.ctTypography || !window.ctTypography.load) return;

	window.ctTypography.load((settings) => {
		apply_settings_to_form(frm, settings);
	});
}

function bind_typography_saved_event(frm) {
	if (frm._ct_typography_saved_bound || !window.jQuery) return;
	frm._ct_typography_saved_bound = true;

	$(document).on("ct-typography-saved.user-desk-theme", (_event, settings) => {
		if (is_current_user_theme(frm)) {
			apply_settings_to_form(frm, settings);
		}
	});
}

function apply_current_form_typography(frm) {
	const api = window.ctTypography || {};
	if (!api.apply) return;

	const settings = {};
	TYPOGRAPHY_FIELDS.forEach((fieldname) => {
		settings[fieldname] = frm.doc[fieldname];
	});
	const normalized = api.apply(settings);
	if (frappe.boot) {
		frappe.boot.construction_typography = normalized;
	}
}

function set_select_options(frm, fieldname, options) {
	const field = frm.fields_dict[fieldname];
	if (!field || !field.df) return;

	field.df.options = options;
	if (field.refresh) {
		field.refresh();
	}
}

function is_current_user_theme(frm) {
	return frm.doc && frm.doc.user && frappe.session && frm.doc.user === frappe.session.user;
}

function apply_settings_to_form(frm, settings) {
	if (!settings) return;
	TYPOGRAPHY_FIELDS.forEach((fieldname) => {
		if (frm.doc[fieldname] != null && String(frm.doc[fieldname]) === String(settings[fieldname])) return;
		if (settings[fieldname] == null) return;
		frm.doc[fieldname] = settings[fieldname];
		frm.refresh_field(fieldname);
	});
}
