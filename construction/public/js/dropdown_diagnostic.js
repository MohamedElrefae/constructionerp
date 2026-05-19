/* ════════════════════════════════════════════════════════════
   DROP-DOWN DIAGNOSTIC — Run this in browser console
   when a filter dropdown is OPEN (e.g. company selector)
   ════════════════════════════════════════════════════════════ */

(function () {
	console.clear();
	console.log("%c=== DROPDOWN DIAGNOSTIC ===", "font-size:16px;font-weight:bold;color:#2563eb");

	// 1. Check if theme CSS is loaded
	const themeCss = [...document.styleSheets].find(
		(s) => s.href && s.href.includes("modern_theme.css"),
	);
	console.log("\n%c1. THEME CSS", "font-weight:bold;color:#f59e0b");
	console.log("  Loaded:", !!themeCss);
	if (themeCss) {
		console.log("  URL:", themeCss.href);
		console.log("  Rules count:", themeCss.cssRules?.length || themeCss.rules?.length || "?");
	}

	// 2. Find all open dropdowns
	console.log("\n%c2. OPEN DROPDOWNS", "font-weight:bold;color:#f59e0b");

	// Awesomplete
	const awesompletes = document.querySelectorAll('ul.awesomplete, .awesomplete[role="listbox"]');
	console.log("  ul.awesomplete found:", awesompletes.length);
	awesompletes.forEach((el, i) => {
		const style = getComputedStyle(el);
		console.log(
			`  Awesomplete #${i}:`,
			el.tagName,
			"\n    class:",
			el.className,
			"\n    style attr:",
			el.getAttribute("style"),
			"\n    computed bg:",
			style.backgroundColor,
			"\n    computed border-left:",
			style.borderLeftColor,
			"\n    computed color:",
			style.color,
			"\n    computed display:",
			style.display,
			"\n    parent:",
			el.parentElement?.tagName,
			el.parentElement?.className?.substring(0, 50),
		);

		// List items
		const items = el.querySelectorAll('li, [role="option"]');
		console.log(`    Items:`, items.length);
		if (items[0]) {
			const itemStyle = getComputedStyle(items[0]);
			console.log(
				`    First item computed bg:`,
				itemStyle.backgroundColor,
				"color:",
				itemStyle.color,
			);
		}
	});

	// Bootstrap dropdowns
	const dropdownMenus = document.querySelectorAll(
		".dropdown-menu.show, .dropdown.open .dropdown-menu, .dropdown-menu",
	);
	console.log("\n  .dropdown-menu found:", dropdownMenus.length);
	dropdownMenus.forEach((el, i) => {
		const style = getComputedStyle(el);
		console.log(
			`  Dropdown #${i}:`,
			el.tagName,
			"\n    class:",
			el.className,
			"\n    style attr:",
			el.getAttribute("style"),
			"\n    computed bg:",
			style.backgroundColor,
			"\n    computed display:",
			style.display,
			"\n    z-index:",
			style.zIndex,
		);
	});

	// 3. Check what applies to the company link field
	console.log("\n%c3. COMPANY LINK FIELD", "font-weight:bold;color:#f59e0b");
	const linkFields = document.querySelectorAll('.link-field, [data-fieldtype="Link"]');
	console.log("  Link fields found:", linkFields.length);

	// 4. Check select elements in page form
	console.log("\n%c4. SELECT ELEMENTS", "font-weight:bold;color:#f59e0b");
	const selects = document.querySelectorAll(".page-form select, .filter-area select");
	console.log("  Selects found:", selects.length);
	selects.forEach((el, i) => {
		const style = getComputedStyle(el);
		console.log(
			`  Select #${i}:`,
			"\n    class:",
			el.className,
			"\n    computed bg:",
			style.backgroundColor,
			"\n    computed color:",
			style.color,
			"\n    computed border-left:",
			style.borderLeftWidth,
			style.borderLeftColor,
		);
	});

	// 5. Check for !important conflicts
	console.log("\n%c5. RULES APPLYING TO FIRST DROPDOWN", "font-weight:bold;color:#f59e0b");
	const firstDropdown = awesompletes[0] || dropdownMenus[0];
	if (firstDropdown) {
		try {
			const rules = [...document.styleSheets]
				.flatMap((s) => [...(s.cssRules || s.rules || [])])
				.filter((r) => r.selectorText && firstDropdown.matches(r.selectorText));
			console.log("  Matching CSS rules:", rules.length);
			rules.slice(0, 5).forEach((r) => {
				console.log(
					"   ",
					r.selectorText.substring(0, 80),
					"->",
					r.style.cssText.substring(0, 100),
				);
			});
		} catch (e) {
			console.log("  Could not read rules (cross-origin):", e.message);
		}
	}

	// 6. Get exact HTML of first awesomplete
	if (awesompletes[0]) {
		console.log("\n%c6. AWESOMPLETE HTML STRUCTURE", "font-weight:bold;color:#f59e0b");
		console.log(awesompletes[0].outerHTML.substring(0, 500));
	}

	console.log("\n%c=== END DIAGNOSTIC ===", "font-size:16px;font-weight:bold;color:#2563eb");
})();
