frappe.pages["construction-report-viewer"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "تقارير التكاليف",
		single_column: true,
	});

	const VIEWS = [
		["analysis_summary", "ملخص التحليلات"],
		["cost_vs_contract", "التكلفة مقابل التعاقد"],
		["resource_requirements", "الاحتياجات من الموارد"],
		["price_history", "سجل الأسعار"],
		["missing_analysis", "بنود بلا تحليل"],
		["integrity", "سلامة الأرصدة (مقيد)"],
	];

	const defaults = (frappe.boot.user && frappe.boot.user.defaults) || {};
	const default_company = defaults.company || defaults.Company || "";
	let current = "analysis_summary";

	VIEWS.forEach(([key, label]) => {
		page.add_button(__(label), () => {
			current = key;
			run();
		});
	});

	const $root = $(page.views.main.find(".layout-main-section"));
	$root.append(
		'<div class="row pt-3">' +
			'<div class="col-sm-3"><label>' + __("Company") + " (الشركة)</label>" +
			'<input class="form-control" data-f="company" value=""></div>' +
			'<div class="col-sm-3"><label>' + __("BOQ Header (optional)") + "</label>" +
			'<input class="form-control" data-f="boq_header"></div>' +
			'<div class="col-sm-2"><label>' + __("Page size") + "</label>" +
			'<input class="form-control" data-f="page_size" value="50"></div>' +
			'<div class="col-sm-4"><label>&nbsp;</label><br>' +
			'<button class="btn btn-primary btn-sm" data-a="run">' + __("View") + "</button> " +
			'<button class="btn btn-default btn-sm" data-a="export">' + __("Export") + "</button></div>" +
			"</div>" +
			'<div class="crv-basis pt-2 text-muted"></div>' +
			'<div class="crv-area pt-2" style="overflow:auto"></div>'
	);
	$root.find('[data-f="company"]').val(default_company);

	function esc(v) {
		return frappe.utils.escape_html(String(v == null ? "" : v));
	}

	function area() {
		return $root.find(".crv-area");
	}

	let seq = 0;
	function params(extra) {
		return Object.assign(
			{
				report: current,
				company: $root.find('[data-f="company"]').val(),
				boq_header: $root.find('[data-f="boq_header"]').val() || undefined,
				page_size: parseInt($root.find('[data-f="page_size"]').val(), 10) || 50,
			},
			extra || {}
		);
	}

	function run() {
		const my = ++seq;
		const company = $root.find('[data-f="company"]').val();
		if (!company && current !== "integrity") {
			area().text(__("Select a company first."));
			return;
		}
		area().html('<div class="text-muted" style="padding:12px">' + __("Loading") + "</div>");
		$root.find(".crv-basis").empty();
		const method =
			current === "integrity"
				? "construction.api.construction_reports.integrity_view"
				: "construction.api.construction_reports.report_view";
		const args =
			current === "integrity"
				? { boq_header: $root.find('[data-f="boq_header"]').val() }
				: params();
		frappe.call({
			method: method,
			args: args,
			callback: (r) => {
				if (my === seq) render(r && r.message);
			},
			error: (e) => {
				if (my !== seq) return;
				const text = e && e._error_message ? String(e._error_message) : __("Unable to load the view.");
				area().html('<div class="alert alert-danger">' + esc(text) + "</div>");
			},
		});
	}

	function render(out) {
		if (!out) {
			area().text(__("No data."));
			return;
		}
		if (out.note || out.basis) {
			$root.find(".crv-basis").text(out.note || out.basis);
		}
		if (out.structures || out.stored !== undefined) {
			render_integrity(out);
			return;
		}
		const cols = out.columns || [];
		const rows = out.rows || [];
		let info = __("Page {0}: {1} of {2} rows.", [out.page || 1, rows.length, out.row_count || 0]);
		if (out.has_more) info += " " + __("Narrow filters or export for the full set.");
		let html = "<p class=text-muted>" + esc(info) + "</p>";
		if (!rows.length) {
			area().html(html + "<p>" + __("No rows for these filters.") + "</p>");
			return;
		}
		html += '<div class="table-responsive"><table class="table table-hover"><thead><tr>';
		cols.forEach((c) => {
			html += "<th scope=col>" + esc(c) + "</th>";
		});
		html += "</tr></thead><tbody>";
		rows.forEach((row) => {
			html += "<tr>" + cols.map((c) => "<td>" + esc(row[c]) + "</td>").join("") + "</tr>";
		});
		html += "</tbody></table></div>";
		area().html(html);
	}

	function render_integrity(out) {
		let html = "<p>" + esc(__("Stored vs recomputed header totals; mismatches are investigation inputs, not repair orders.")) + "</p>";
		const mism = (out.mismatched_fields || []).join(", ");
		html += "<p>" + esc(__("Header {0}: mismatched fields: {1}.", [out.boq_header || "—", mism || __("none")])) + "</p>";
		const structs = out.structures || [];
		if (structs.length) {
			html += '<div class="table-responsive"><table class="table table-hover"><thead><tr><th>' +
				esc(__("Structure")) + "</th><th>" + esc(__("Mismatched fields")) + "</th></tr></thead><tbody>";
			structs.forEach((s) => {
				html += "<tr><td>" + esc(s.name || s.structure) + "</td><td>" +
					esc((s.mismatched_fields || []).join(", ")) + "</td></tr>";
			});
			html += "</tbody></table></div>";
		} else {
			html += "<p>" + esc(__("No structure mismatches recorded.")) + "</p>";
		}
		html += "<p class=text-muted>" + esc(__("Limit: {0}.", [out.aggregation_limit || "—"])) + "</p>";
		area().html(html);
	}

	$root.find('[data-a="run"]').on("click", run);
	$root.find('[data-a="export"]').on("click", () => {
		const company = $root.find('[data-f="company"]').val();
		if (!company) {
			area().text(__("Select a company first."));
			return;
		}
		frappe.call({
			method: "construction.api.construction_reports.report_export",
			args: params(),
			callback: (r) => {
				const m = r.message || {};
				if (m.file_url) {
					window.open(m.file_url);
					area().html('<div class="alert alert-success">' +
						esc(__("Exported {0} rows{1}.", [m.row_count || 0, m.truncated ? " (" + __("truncated at the export limit") + ")" : ""])) + "</div>");
				} else {
					area().html('<div class="alert alert-danger">' + esc(__("Export refused.")) + "</div>");
				}
			},
			error: () => {
				area().html('<div class="alert alert-danger">' + esc(__("Export request failed.")) + "</div>");
			},
		});
	});

	run();
};
