// Construction bilingual pilot — Account tree label renderer (Stage 3).
//
// Loaded via doctype_tree_js hook AFTER the vendor account_tree.js, so it
// can wrap frappe.treeview_settings["Account"] instead of replacing it:
// - data source: governed wrapper `get_account_tree_children` (vendor query
//   reused; bilingual label fields merged in ONE extra batched query —
//   never one query per node).
// - label: construction-owned renderer. Arabic sessions show the Arabic
//   name (fallback English, then the language-neutral identity) WITHOUT
//   appending the English internal name in parentheses; English sessions
//   show the English name (fallback Arabic, then identity). Stable node
//   identity (`data-label` / node.label = document name) is untouched.
// - All labels are HTML-escaped before insertion (rendered values are
//   never trusted HTML).

(function () {
	const settings = frappe.treeview_settings && frappe.treeview_settings["Account"];
	if (!settings) return;

	function ct_esc(s) {
		return frappe.utils.escape_html(String(s == null ? "" : s));
	}

	function ct_session_lang() {
		return (
			(frappe.boot && frappe.boot.lang) ||
			(frappe.user_defaults && frappe.user_defaults.language) ||
			"en"
		);
	}

	function ct_account_label(data) {
		const lang = ct_session_lang();
		const arabic = data && data.account_name_ar;
		const english = data && data.account_name;
		const identity = (data && data.value) || (data && data.name) || "";
		const is_ar =
			String(lang || "")
				.toLowerCase()
				.indexOf("ar") === 0;
		if (is_ar) {
			return ct_esc(arabic || english || identity);
		}
		return ct_esc(english || arabic || identity);
	}

	settings.get_tree_nodes = "construction.services.bilingual_service.get_account_tree_children";
	settings.get_label = function (node) {
		const data = node && (node.data || node);
		return ct_account_label(data);
	};
})();
