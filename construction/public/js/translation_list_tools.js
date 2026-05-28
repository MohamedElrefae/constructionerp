(function () {
	"use strict";

	function addFilter(listview, filter) {
		return listview.filter_area.add([filter]).then(() => listview.refresh());
	}

	function setupTranslationTools(listview) {
		if (
			!listview ||
			listview.doctype !== "Translation" ||
			listview.__ct_translation_tools_bound
		) {
			return;
		}
		listview.__ct_translation_tools_bound = true;

		listview.page.add_menu_item(__("Arabic Only"), () => {
			listview.filter_area.clear().then(() => {
				addFilter(listview, ["Translation", "language", "=", "ar"]);
			});
		});

		listview.page.add_menu_item(__("Missing Arabic (Prepare + Filter)"), () => {
			frappe
				.call({
					method: "construction.api.translation_tools.seed_missing_arabic_translations",
					args: { limit: 1000 },
					freeze: true,
					freeze_message: __("Preparing missing Arabic rows..."),
				})
				.then((r) => {
					const created = r?.message?.created || 0;
					return frappe
						.call({
							method: "construction.api.translation_tools.get_missing_arabic_translation_names",
							args: { limit: 1000 },
						})
						.then((res) => {
							const names = res?.message || [];
							frappe.show_alert({
								message: __("Prepared {0} rows. Missing Arabic now: {1}", [
									created,
									names.length,
								]),
								indicator: "green",
							});
							listview.filter_area.clear().then(() => {
								addFilter(listview, ["Translation", "language", "=", "ar"]).then(
									() => {
										if (names.length) {
											addFilter(listview, [
												"Translation",
												"name",
												"in",
												names,
											]);
										}
									}
								);
							});
						});
				});
		});

		listview.page.add_menu_item(__("Normalize Translation Keys"), () => {
			frappe
				.call({
					method: "construction.api.translation_tools.normalize_translation_keys",
					freeze: true,
					freeze_message: __("Normalizing translation records..."),
				})
				.then((r) => {
					const updated = r?.message?.updated || 0;
					frappe.show_alert({
						message: __("Normalized {0} translation records", [updated]),
						indicator: "green",
					});
					listview.refresh();
				});
		});
	}

	const existing = frappe.listview_settings?.Translation || {};
	const priorOnload = existing.onload;
	frappe.listview_settings = frappe.listview_settings || {};
	frappe.listview_settings.Translation = Object.assign({}, existing, {
		onload(listview) {
			if (priorOnload) priorOnload(listview);
			setupTranslationTools(listview);
		},
	});
})();
