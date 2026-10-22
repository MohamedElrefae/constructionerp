frappe.pages["cost-database-workbench"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "منصة قاعدة بيانات التكاليف",
		single_column: true,
	});

	const defaults = (frappe.boot.user && frappe.boot.user.defaults) || {};
	const default_company = defaults.company || defaults.Company || "";

	page.set_primary_action(__("Import section"), () => show_section("import"));
	page.add_button(__("Reprice section"), () => show_section("reprice"));

	const $root = $(page.views.main.find(".layout-main-section"));
	$root.append('<div class="cdb-area pt-3"></div>');
	const $area = $root.find(".cdb-area");

	function esc(v) {
		return frappe.utils.escape_html(String(v == null ? "" : v));
	}

	function show_section(which) {
		if (which === "reprice") {
			render_reprice();
		} else {
			render_import();
		}
	}

	let busy = false;
	function set_busy($btn, label) {
		busy = true;
		$btn.prop("disabled", true)
			.data("label", $btn.text())
			.text(label || __("Working…"));
	}
	function clear_busy($btn) {
		busy = false;
		$btn.prop("disabled", false).text($btn.data("label") || $btn.text());
	}

	function csrf() {
		return frappe.csrf_token;
	}

	function post_multipart(file_bytes, file_name, fields) {
		const form = new FormData();
		form.append(
			"file",
			new Blob([file_bytes], {
				type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			}),
			file_name
		);
		Object.keys(fields || {}).forEach((k) => form.append(k, fields[k]));
		return fetch("/api/method/construction.api.cost_database_api.import_cost_database", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": csrf() },
			body: form,
		}).then((r) => r.json().then((j) => ({ status: r.status, body: j })));
	}

	// ─── Import section ───
	let held_file = null;
	let held_name = "";
	let last_preview = null;

	function render_import() {
		held_file = null;
		last_preview = null;
		$area.html(
			'<div class="row">' +
				'<div class="col-sm-4"><label>' +
				__("Company") +
				" (الشركة)</label>" +
				'<input class="form-control" data-f="company" value="' +
				esc(default_company) +
				'"></div>' +
				'<div class="col-sm-4"><label>' +
				__("Workbook (.xlsx)") +
				"</label>" +
				'<input type="file" class="form-control" data-f="file" accept=".xlsx"></div>' +
				'<div class="col-sm-4"><label>&nbsp;</label><br>' +
				'<button class="btn btn-default btn-sm" data-a="template">' +
				__("Download template") +
				"</button> " +
				'<button class="btn btn-primary btn-sm" data-a="validate">' +
				__("Validate (preview)") +
				"</button> " +
				'<button class="btn btn-success btn-sm" data-a="commit" disabled>' +
				__("Confirm import") +
				"</button></div>" +
				"</div>" +
				'<div class="cdb-result pt-3"></div>'
		);
		const $res = $area.find(".cdb-result");
		$area.find('[data-a="template"]').on("click", () => {
			window.open(
				"/api/method/construction.api.cost_database_api.download_cost_database_template?mode=blank"
			);
		});
		$area.find('[data-f="file"]').on("change", (e) => {
			const f = e.target.files && e.target.files[0];
			held_file = null;
			last_preview = null;
			$area.find('[data-a="commit"]').prop("disabled", true);
			$res.empty();
			if (!f) return;
			const rd = new FileReader();
			rd.onload = () => {
				held_file = rd.result;
				held_name = f.name;
			};
			rd.readAsArrayBuffer(f);
		});
		$area.find('[data-a="validate"]').on("click", (e) => {
			if (busy) return;
			const company = $area.find('[data-f="company"]').val();
			if (!company) {
				$res.text(__("Select a company first."));
				return;
			}
			if (!held_file) {
				$res.text(__("Choose a workbook file first."));
				return;
			}
			const $btn = $(e.target);
			set_busy($btn);
			$res.html(
				'<div class="text-muted">' + __("Validating… nothing saved yet.") + "</div>"
			);
			post_multipart(held_file, held_name, { company: company, dry_run: "1" })
				.then(({ status, body }) => {
					clear_busy($btn);
					render_import_result($res, $area, status, body && body.message, company);
				})
				.catch(() => {
					clear_busy($btn);
					$res.text(__("Validation request failed. Nothing was saved."));
				});
		});
		$area.find('[data-a="commit"]').on("click", (e) => {
			if (busy || !last_preview) return;
			const company = $area.find('[data-f="company"]').val();
			const $btn = $(e.target);
			set_busy($btn, __("Committing…"));
			post_multipart(held_file, held_name, { company: company, dry_run: "0" })
				.then(({ status, body }) => {
					clear_busy($btn);
					const m = body && body.message;
					if (status === 200 && m && m.success) {
						const c = m.records_created || {};
						$res.html(
							'<div class="alert alert-success">' +
								esc(
									__("Committed: {0} items, {1} price rows, {2} templates.", [
										(c.items || []).length,
										(c.resource_price_history || []).length,
										(c.boq_cost_analysis_templates || []).length,
									])
								) +
								"</div>"
						);
						last_preview = null;
						$area.find('[data-a="commit"]').prop("disabled", true);
					} else {
						render_import_result($res, $area, status, m, company);
					}
				})
				.catch(() => {
					clear_busy($btn);
					$res.text(
						__(
							"Commit request failed with unknown outcome. Check Resource Price History before retrying; do not blindly repeat."
						)
					);
				});
		});
	}

	function render_import_result($res, $area, status, m, company) {
		if (status !== 200 || !m) {
			$res.html(
				'<div class="alert alert-danger">' +
					esc(__("Request refused (HTTP {0}). Nothing was saved.", [status])) +
					"</div>"
			);
			return;
		}
		if (!m.success) {
			let html =
				'<div class="alert alert-danger">' +
				esc(__("Validation found blocking errors. No records were saved.")) +
				"<ul>";
			(m.errors || []).slice(0, 30).forEach((e) => {
				html += "<li>" + esc(e) + "</li>";
			});
			html += "</ul></div>";
			$res.html(html);
			return;
		}
		const p = m.proposed_creates || { items: [], uoms: [] };
		let html =
			'<div class="alert alert-info">' +
			esc(__("Preview only — nothing saved yet for company {0}.", [company])) +
			"<br>" +
			esc(
				__("Proposed new Items: {0}. Proposed new UOMs: {1}.", [
					(p.items || []).length,
					(p.uoms || []).length,
				])
			) +
			"</div>";
		if ((p.items || []).length) {
			html +=
				"<p><b>" +
				esc(__("New Items (shared masters — review before confirming):")) +
				"</b> " +
				esc((p.items || []).slice(0, 20).join(", ")) +
				"</p>";
		}
		if ((p.uoms || []).length) {
			html +=
				"<p><b>" +
				esc(__("New UOMs (global):")) +
				"</b> " +
				esc((p.uoms || []).join(", ")) +
				"</p>";
		}
		html +=
			"<p class=text-muted>" +
			esc(
				__(
					"Shared Items with conflicting names or flags are refused, never renamed. Confirm to commit."
				)
			) +
			"</p>";
		$res.html(html);
		last_preview = m;
		$area.find('[data-a="commit"]').prop("disabled", false);
	}

	// ─── Reprice section ───
	function render_reprice() {
		$area.html(
			'<div class="row">' +
				'<div class="col-sm-3"><label>' +
				__("Company (required)") +
				"</label>" +
				'<input class="form-control" data-f="company" value="' +
				esc(default_company) +
				'"></div>' +
				'<div class="col-sm-3"><label>' +
				__("BOQ Header (optional)") +
				"</label>" +
				'<input class="form-control" data-f="boq_header"></div>' +
				'<div class="col-sm-3"><label>' +
				__("Item code (optional)") +
				"</label>" +
				'<input class="form-control" data-f="item_code"></div>' +
				'<div class="col-sm-3"><label>&nbsp;</label><br>' +
				'<button class="btn btn-primary btn-sm" data-a="preview">' +
				__("Preview repricing") +
				"</button> " +
				'<button class="btn btn-success btn-sm" data-a="commit" disabled>' +
				__("Confirm repricing") +
				"</button></div>" +
				"</div>" +
				'<div class="cdb-result pt-3"></div>'
		);
		const $res = $area.find(".cdb-result");
		let preview = null;
		function filters() {
			const o = { company: $area.find('[data-f="company"]').val() };
			[
				"boq_header",
				"boq_item",
				"item_code",
				"resource_type",
				"cost_stream",
				"region",
				"as_of_date",
			].forEach((k) => {
				const v = $area.find(`[data-f="${k}"]`).val();
				if (v) o[k] = v;
			});
			return o;
		}
		$area.find('[data-a="preview"]').on("click", (e) => {
			if (busy) return;
			const f = filters();
			if (!f.company) {
				$res.text(__("Company is required."));
				return;
			}
			const $btn = $(e.target);
			set_busy($btn);
			$res.html(
				'<div class="text-muted">' +
					__("Loading prospective changes… nothing saved.") +
					"</div>"
			);
			frappe.call({
				method: "construction.api.cost_database_api.reprice_cost_analyses",
				args: Object.assign({ dry_run: true }, f),
				callback: (r) => {
					clear_busy($btn);
					const m = r.message;
					if (!m) {
						$res.text(__("Preview failed. Nothing was saved."));
						return;
					}
					preview = m;
					let html =
						"<p>" +
						esc(
							__(
								"Prospective only: {0} analyses, {1} rows to update, {2} unchanged.",
								[
									m.analyses_touched || 0,
									m.details_updated || 0,
									m.details_unchanged || 0,
								]
							)
						) +
						"</p>";
					if ((m.errors || []).length) {
						html +=
							'<div class="alert alert-danger"><ul>' +
							m.errors
								.slice(0, 20)
								.map((x) => "<li>" + esc(x) + "</li>")
								.join("") +
							"</ul></div>";
					} else {
						$area.find('[data-a="commit"]').prop("disabled", false);
					}
					$res.html(html);
				},
				error: () => {
					clear_busy($btn);
					$res.text(__("Preview request failed. Nothing was saved."));
				},
			});
		});
		$area.find('[data-a="commit"]').on("click", (e) => {
			if (busy || !preview) return;
			const $btn = $(e.target);
			set_busy($btn, __("Committing…"));
			frappe.call({
				method: "construction.api.cost_database_api.reprice_cost_analyses",
				args: Object.assign({ dry_run: false }, filters()),
				callback: (r) => {
					clear_busy($btn);
					const m = r.message || {};
					$res.html(
						'<div class="alert alert-success">' +
							esc(
								__("Repriced: {0} analyses, {1} rows updated, {2} unchanged.", [
									m.analyses_touched || 0,
									m.details_updated || 0,
									m.details_unchanged || 0,
								])
							) +
							"</div>"
					);
					preview = null;
					$area.find('[data-a="commit"]').prop("disabled", true);
				},
				error: () => {
					clear_busy($btn);
					$res.text(
						__(
							"Commit request failed with unknown outcome. Check analyses before retrying; do not blindly repeat."
						)
					);
				},
			});
		});
	}

	render_import();
};
