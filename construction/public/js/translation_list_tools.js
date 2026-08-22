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

		listview.page.add_menu_item(__("Filter Missing Arabic"), () => {
			frappe
				.call({
					method: "construction.api.translation_tools.get_missing_arabic_translation_sources",
					args: { limit: 1000 },
					freeze: true,
					freeze_message: __("Finding source texts missing Arabic..."),
				})
				.then((res) => {
					const sources = res?.message || [];
					frappe.show_alert({
						message: __("{0} source texts still have no Arabic entry", [sources.length]),
						indicator: "orange",
					});
					listview.filter_area.clear().then(() => {
						if (sources.length) {
							addFilter(listview, ["Translation", "source_text", "in", sources]);
						} else {
							addFilter(listview, ["Translation", "language", "=", "ar"]);
						}
					});
				});
		});

		listview.page.add_menu_item(__("Filter Placeholder (Junk) Arabic"), () => {
			frappe
				.call({
					method: "construction.api.translation_tools.get_placeholder_arabic_translation_sources",
					args: { limit: 1000 },
					freeze: true,
					freeze_message: __("Finding placeholder translations..."),
				})
				.then((res) => {
					const sources = res?.message || [];
					frappe.show_alert({
						message: __("{0} source texts still have placeholders", [sources.length]),
						indicator: sources.length ? "red" : "green",
					});
					listview.filter_area.clear().then(() => {
						if (sources.length) {
							addFilter(listview, ["Translation", "source_text", "in", sources]);
						}
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

		listview.page.add_menu_item(__("Preview Glossary Corrections"), () => {
			frappe
				.call({
					method: "construction.api.translation_tools.apply_glossary_corrections",
					args: { dry_run: 1 },
					freeze: true,
					freeze_message: __("Checking against the Egyptian glossary..."),
				})
				.then((r) => {
					const res = r?.message || {};
					const preview = res.preview || [];
					if (!preview.length) {
						frappe.show_alert({
							message: __("All glossary terms already match"),
							indicator: "green",
						});
						return;
					}
					frappe.msgprint({
						title: __("Glossary corrections preview"),
						indicator: "orange",
						message: preview
							.slice(0, 40)
							.map(
								(x) =>
									`<b>${frappe.utils.xss_safe(x.source_text)}</b><br>` +
									`${frappe.utils.xss_safe(x.before)} → <b>${frappe.utils.xss_safe(x.after)}</b>`
							)
							.join("<hr>"),
					});
				});
		});

		listview.page.add_menu_item(__("Apply Glossary Corrections"), () => {
			frappe.confirm(
				__(
					"Overwrite any mismatching Arabic rows with the canonical Egyptian glossary? This is explicit and non-reversible."
				),
				() => {
					frappe
						.call({
							method: "construction.api.translation_tools.apply_glossary_corrections",
							args: { dry_run: 0 },
							freeze: true,
							freeze_message: __("Applying glossary corrections..."),
						})
						.then((r) => {
							const res = r?.message || {};
							frappe.show_alert({
								message: __("Updated {0} rows from {1} checked", [
									res.updated || 0,
									res.checked || 0,
								]),
								indicator: "green",
							});
							listview.refresh();
						});
				}
			);
		});

		listview.page.add_menu_item(__("Import Review Queue"), () => {
			frappe
				.call({
					method: "construction.api.translation_tools.import_review_queue",
					args: { dry_run: 1 },
					freeze: true,
					freeze_message: __("Previewing review-queue import..."),
				})
				.then((r) => {
					const res = r?.message || {};
					const preview = res.preview || [];
					if (!preview.length) {
						frappe.show_alert({
							message: __("Review queue has {0} entries, nothing new to apply", [
								res.total || 0,
							]),
							indicator: "green",
						});
						return;
					}
					frappe.confirm(
						__(
							"Import {0} reviewed translation(s) from the queue? Existing rows will be updated to the reviewed value.",
							[preview.length]
						),
						() => {
							frappe
								.call({
									method: "construction.api.translation_tools.import_review_queue",
									args: { dry_run: 0 },
									freeze: true,
									freeze_message: __("Importing review queue..."),
								})
								.then((res2) => {
									const rr = res2?.message || {};
									frappe.show_alert({
										message: __(
											"Imported {0} created, {1} updated from {2} total",
											[rr.created || 0, rr.updated || 0, rr.total || 0]
										),
										indicator: "green",
									});
									listview.refresh();
								});
						}
					);
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
