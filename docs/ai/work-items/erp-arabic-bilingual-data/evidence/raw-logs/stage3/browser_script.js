// Construction bilingual pilot — Account form/tree browser verification (Stage 3).
//
// MANUAL browser verification script (frappe desk console), complements the
// automated bench tests, which cannot execute the shipped JavaScript.
//
// How to run:
//   1. Sign into the authorized TEST site as a user with read access to
//      Account (e.g. Accounts User), session language `ar` for the Arabic
//      assertions and `en` for the English assertions.
//   2. Open the browser devtools console on an Account form and on the
//      Chart of Accounts tree, paste this whole file, and press Enter.
//   3. Every check appends to `window.ct_bilingual_results`; the script
//      finishes with a summary. Any `false` result is a failure.
//
// Coverage (maps to the AI-R P1 test-envelope findings):
//   - identity section renders with wrapped labels and live data,
//   - the Arabic label renderer never appends the English internal name,
//   - rendered values are HTML-escaped (XSS),
//   - English session shows the English name.

(function () {
	window.ct_bilingual_results = [];
	function check(name, fn) {
		let ok = null;
		let err = null;
		try {
			ok = fn();
		} catch (e) {
			err = e && e.message;
			ok = false;
		}
		// ok === true → pass, ok === false → fail, ok === null → skip
		window.ct_bilingual_results.push({ name: name, ok: ok, error: err });
		const tag = ok === false ? "FAIL" : ok === true ? "PASS" : "SKIP";
		console.log(tag + " " + name + (err ? " — " + err : ""));
		return ok;
	}

	// ---- pure label logic (mirrors account_tree.js ct_account_label) ----
	function esc(s) {
		return frappe.utils.escape_html(String(s == null ? "" : s));
	}
	function label_for(data, lang) {
		const is_ar =
			String(lang || "")
				.toLowerCase()
				.indexOf("ar") === 0;
		const arabic = data && data.account_name_ar;
		const english = data && data.account_name;
		const identity = (data && data.value) || "";
		return esc(is_ar ? arabic || english || identity : english || arabic || identity);
	}

	check("arabic label uses arabic name without internal name", function () {
		const out = label_for(
			{
				account_name_ar: "عربي",
				account_name: "English Name",
				value: "1100 - English Name - TC",
			},
			"ar"
		);
		return out === "عربي" && out.indexOf("1100") === -1 && out.indexOf("English Name") === -1;
	});

	check(
		"arabic fallback to english, then identity — still no internal-name append",
		function () {
			const a = label_for({ account_name: "English Name", value: "1100 - X - TC" }, "ar");
			const b = label_for({ value: "1100 - X - TC" }, "ar");
			return a === "English Name" && b === "1100 - X - TC";
		}
	);

	check("english session prefers english then arabic", function () {
		const a = label_for(
			{ account_name_ar: "عربي", account_name: "English", value: "x" },
			"en"
		);
		const b = label_for({ account_name_ar: "عربي", value: "x" }, "en");
		return a === "English" && b === "عربي";
	});

	check("labels are HTML-escaped (XSS)", function () {
		const out = label_for(
			{ account_name_ar: "<script>alert(1)</script>", account_name: "ok", value: "v" },
			"ar"
		);
		return out.indexOf("<script>") === -1 && out.indexOf("&lt;script&gt;") !== -1;
	});

	// ---- live form section (must run while an Account form is open) ----
	check("identity section renders on the open Account form", function () {
		const frm = cur_frm;
		if (!frm || frm.doctype !== "Account" || frm.is_new()) return null; // skipped
		const $w =
			frm.fields_dict.ct_bilingual_identity &&
			frm.fields_dict.ct_bilingual_identity.$wrapper;
		if (!$w) return false;
		return (
			$w.find(".ct-bi-en").text().length > 0 &&
			$w.find(".ct-bi-ar").text().length > 0 &&
			$w.find(".ct-bi-complete").text().length > 0
		);
	});

	check("identity section text nodes are escaped (no raw HTML injection)", function () {
		const frm = cur_frm;
		if (!frm || frm.doctype !== "Account" || frm.is_new()) return null;
		const $w =
			frm.fields_dict.ct_bilingual_identity &&
			frm.fields_dict.ct_bilingual_identity.$wrapper;
		if (!$w) return null;
		// .text() was used for every value cell; assert no injected elements
		return $w.find(".ct-bi-row span").children().length === 0;
	});

	// ---- live tree (uses the evidence host tree when present) ----
	check("tree labels show arabic without internal name (arabic session)", function () {
		const tree = window.ct_tree || window.cur_tree;
		if (!tree || !tree.nodes) return null; // skipped off-tree
		const lang = (frappe.boot && frappe.boot.lang) || "en";
		if (String(lang).toLowerCase().indexOf("ar") !== 0) return null;
		const with_ar = Object.values(tree.nodes).find(function (n) {
			return n.data && n.data.account_name_ar;
		});
		if (!with_ar) return false;
		const text = with_ar.$tree_link.find(".tree-label").text().trim();
		return (
			text === with_ar.data.account_name_ar &&
			text.indexOf("(" + with_ar.label + ")") === -1 &&
			text.indexOf(with_ar.data.account_name) === -1
		);
	});

	const failed = window.ct_bilingual_results.filter(function (r) {
		return r.ok === false;
	}).length;
	const skipped = window.ct_bilingual_results.filter(function (r) {
		return r.ok === null;
	}).length;
	console.log(
		"ct_bilingual_results: %d checks, %d failed, %d skipped",
		window.ct_bilingual_results.length,
		failed,
		skipped
	);
	return { total: window.ct_bilingual_results.length, failed: failed, skipped: skipped };
})();
