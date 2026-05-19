// Paste this in browser console when on Accounts Tree with the company dropdown OPEN
console.clear();
(function () {
	console.log("=== DROPDOWN FINDER ===\n");

	// Find all visible ULs anywhere in body
	var visibleULs = [];
	document.querySelectorAll('body ul, body [role="listbox"]').forEach(function (el) {
		if (getComputedStyle(el).display !== "none") {
			visibleULs.push(el);
		}
	});

	console.log("Visible ULs / listboxes:", visibleULs.length);
	visibleULs.forEach(function (el, i) {
		var items = el.querySelectorAll('li, [role="option"], .dropdown-item');
		var firstText = items[0] ? items[0].textContent.trim().substring(0, 40) : "";
		console.log(
			i + ":",
			el.tagName,
			"class=" + (el.className || "none"),
			"role=" + (el.getAttribute("role") || "none"),
			"items=" + items.length,
			'firstItem="' + firstText + '"',
		);
	});

	// Also check for .dropdown-menu
	var menus = [];
	document.querySelectorAll(".dropdown-menu").forEach(function (el) {
		if (getComputedStyle(el).display !== "none") menus.push(el);
	});
	console.log("\nVisible .dropdown-menu:", menus.length);
	menus.forEach(function (el, i) {
		console.log(
			i + ":",
			el.className,
			"parent:",
			el.parentElement?.className?.substring(0, 40),
		);
	});

	// Check any absolutely positioned visible elements
	console.log("\nAbs-positioned visible elements with children:");
	document.querySelectorAll("body *").forEach(function (el) {
		var s = getComputedStyle(el);
		if (s.display !== "none" && s.position === "absolute" && el.children.length > 2) {
			var items = el.querySelectorAll('li, a, [role="option"]');
			if (items.length > 0) {
				console.log(
					el.tagName,
					"class=" + (el.className || "none"),
					"items=" + items.length,
					"text=" + items[0].textContent.trim().substring(0, 30),
				);
			}
		}
	});

	console.log("\n=== END ===");
})();
