(function () {
	"use strict";
	function enforce() {
		var f = document.querySelectorAll.bind(document);
		var bg =
			getComputedStyle(document.documentElement)
				.getPropertyValue("--ct-bg-elevated")
				.trim() || "#111827";
		var tx =
			getComputedStyle(document.documentElement).getPropertyValue("--ct-text").trim() ||
			"#f8fafc";
		var t2 =
			getComputedStyle(document.documentElement)
				.getPropertyValue("--ct-text-secondary")
				.trim() || "#94a3b8";
		var br =
			getComputedStyle(document.documentElement).getPropertyValue("--ct-border").trim() ||
			"rgba(148,163,184,0.18)";
		var pr =
			getComputedStyle(document.documentElement).getPropertyValue("--ct-primary").trim() ||
			"#2563eb";

		// Fix 1: Make .page-form a seamless unified bar
		f(".page-form").forEach(function (pf) {
			pf.style.setProperty("gap", "0", "important");
			pf.style.setProperty("column-gap", "0", "important");
			pf.style.setProperty("row-gap", "0", "important");
			pf.style.setProperty("align-items", "center", "important");
		});

		// Fix 2: All wrappers transparent
		f(
			".page-form .standard-filter-section,.page-form .filter-section,.page-form .filter-area,.page-form .frappe-control,.page-form .frappe-control .control-input,.page-form .frappe-control .control-input-wrapper,.page-form .link-field,.page-form .link-field.ui-front,.page-form .input-group,.page-form .filter-field,.page-form .awesomplete"
		).forEach(function (e) {
			e.style.setProperty("background", "transparent", "important");
			e.style.setProperty("background-color", "transparent", "important");
			e.style.setProperty("border", "none", "important");
			e.style.setProperty("border-radius", "0", "important");
			e.style.setProperty("box-shadow", "none", "important");
			e.style.setProperty("padding", "0", "important");
			e.style.setProperty("margin", "0", "important");
		});

		// Fix 3: All inputs unified
		f(
			'.page-form select,.page-form select.form-control,.page-form input.form-control,.page-form input.input-with-feedback,.page-form .link-field input,.page-form .multiselect-list .form-control,.page-form .awesomplete input,.page-form input[data-fieldtype="Date"],.page-form input.hasDatepicker'
		).forEach(function (e) {
			e.style.setProperty("height", "30px", "important");
			e.style.setProperty("background-color", bg, "important");
			e.style.setProperty("color", tx, "important");
			e.style.setProperty("border-top", "1px solid " + br, "important");
			e.style.setProperty("border-right", "1px solid " + br, "important");
			e.style.setProperty("border-bottom", "1px solid " + br, "important");
			e.style.setProperty("border-left", "3px solid " + pr, "important");
			e.style.setProperty("border-radius", "6px", "important");
			e.style.setProperty("box-shadow", "none", "important");
			e.style.setProperty("outline", "none", "important");
			if (e.tagName === "SELECT") {
				e.style.setProperty("appearance", "none", "important");
				e.style.setProperty("padding", "2px 26px 2px 8px", "important");
			}
		});

		// Fix 4: Hide select icon
		f(
			".page-form .frappe-control .select-icon,.page-form .frappe-control .select-icon svg,.page-form .frappe-control .select-icon use,.page-form .frappe-control .placeholder"
		).forEach(function (e) {
			e.style.setProperty("display", "none", "important");
		});

		// Fix 5: Buttons unified
		f(
			'.page-form .filter-selector,.page-form .filter-selector .btn,.page-form .filter-button,.page-form [data-action="add-filter"]'
		).forEach(function (e) {
			e.style.setProperty("height", "30px", "important");
			e.style.setProperty("background", bg, "important");
			e.style.setProperty("color", t2, "important");
			e.style.setProperty("border", "1px solid " + br, "important");
			e.style.setProperty("border-radius", "6px", "important");
			e.style.setProperty("font-size", "0.75rem", "important");
		});

		// Fix 6: RTL select arrow position
		if (document.dir === "rtl") {
			f(".page-form select").forEach(function (e) {
				e.style.setProperty("padding", "2px 8px 2px 26px", "important");
			});
		}

		var inputs = f(".page-form select,.page-form input.form-control").length;
		var pfs = f(".page-form").length;
		console.log("[CT-Filter] applied: " + pfs + " page-form(s), " + inputs + " inputs");
	}
	[0, 500, 1500, 3000, 5000, 8000].forEach(function (d) {
		setTimeout(enforce, d);
	});
	var o = new MutationObserver(function () {
		setTimeout(enforce, 50);
	});
	setTimeout(function () {
		var p = document.querySelectorAll(".page-form");
		if (p.length) {
			for (var i = 0; i < p.length; i++) o.observe(p[i], { childList: true, subtree: true });
			console.log("[CT-Filter] observer active on " + p.length + " page-form(s)");
		}
	}, 100);
})();
