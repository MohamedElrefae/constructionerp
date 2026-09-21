frappe.pages["bilingual-report-viewer"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Bilingual Report Viewer",
		single_column: true,
	});

	const reports = ["Trial Balance", "General Ledger", "Accounts Receivable"];
	const modes = ["ar", "en", "both"];

	page.add_field({
		label: "النوع",
		fieldtype: "Select",
		options: reports.join("\n"),
		default: "Trial Balance",
		fieldname: "report",
		change: run,
	});
	page.add_field({
		label: "الوضع",
		fieldtype: "Select",
		options: modes.join("\n"),
		default: "ar",
		fieldname: "mode",
		change: run,
	});
	page.add_field({
		label: "الشركة",
		fieldtype: "Link",
		options: "Company",
		fieldname: "company",
		change: run,
	});
	page.add_field({
		label: "من تاريخ",
		fieldtype: "Date",
		fieldname: "from_date",
		default: "2026-01-01",
		change: run,
	});
	page.add_field({
		label: "إلى تاريخ",
		fieldtype: "Date",
		fieldname: "to_date",
		default: frappe.datetime.get_today(),
		change: run,
	});
	page.set_primary_action("عرض", () => run());

	const $body = page.views.main.find(".layout-main-section");
	$body.append('<div class="bilingual-report-area pt-3" style="overflow:auto"></div>');

	function esc(v) {
		return frappe.utils.escape_html(String(v == null ? "" : v));
	}

	function area() {
		return $(page.views.main.find(".layout-main-section")).find(".bilingual-report-area");
	}

		let __seq = 0;
	let run_seq = 0;
	function run() {
		const name = page.fields_dict.report.get_value() || "Trial Balance";
		const mode = page.fields_dict.mode.get_value() || "ar";
		let company = page.fields_dict.company.get_value();
		if (!company) {
			const d = (frappe.boot.user && frappe.boot.user.defaults) || {};
			company = d.company || d.Company || "Elrefae";
		}
		const from = page.fields_dict.from_date.get_value();
		const to = page.fields_dict.to_date.get_value();
		const my = ++run_seq;
		area().html('<div class="text-muted" style="padding:12px">' + __("Loading") + "</div>");
		frappe.call({
			method: "construction.api.bilingual_reports.localized_report",
			args: {
				report_name: name,
				mode: mode,
				filters: JSON.stringify({
					company: company,
					from_date: from,
					to_date: to,
					report_date: to,
					ageing_based_on: "Posting Date",
					party_type: "Customer",
					group_by_party: true,
				}),
			},
			callback: (r) => { if (my === run_seq) safe_render(r && r.message); },
			error: (e) => {
				const text = e && e._error_message ? e._error_message : (e ? frappe.utils.escape_html(JSON.stringify(e).slice(0, 140)) : "error");
				area().html('<div class="text-muted" style="padding:12px">خطأ في التقرير: ' + (text || "") + "</div>");
			},
		});
	}

	function safe_render(out) {
		try {
			const cols = (out && out.columns) || [];
			const rows = (out && out.data) || [];
			if (!rows.length) {
				area().html('<div class="text-muted" style="padding:12px">' + __("No Data") + "</div>");
				return;
			}
			let head = "<tr>";
			cols.forEach((c) => {
				head += "<th scope=col>" + esc(c && (c.label || c.fieldname)) + "</th>";
			});
			head += "</tr>";
			let body = "";
			for (const row of rows) {
				if (Array.isArray(row)) {
					body += "<tr>" + Array.from({length: cols.length}).map((_, i) => "<td>" + esc(row[i]) + "</td>").join("") + "</tr>";
				} else if (row && typeof row === "object") {
					body += "<tr>" + cols.map((c) => "<td>" + esc(row[c.fieldname]) + "</td>").join("") + "</tr>";
				}
			}
			area().html(
				'<div class="table-responsive"><table class="table table-hover bilingual-report-table"><thead>' +
					head +
					"</thead><tbody>" +
					body +
					"</tbody></table></div>"
			);
		} catch (e) {
			area().html("<div class=text-muted>render error: " + esc(String(e)) + "</div>");
		}
	}
};
