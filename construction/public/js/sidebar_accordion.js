(function () {
	"use strict";

	function close_other_sections(active_section) {
		document.querySelectorAll(".body-sidebar .sidebar-item-container.section-item").forEach(function (section) {
			if (section === active_section) return;

			var icon = section.querySelector(".drop-icon use");
			var is_open = icon && icon.getAttribute("href") === "#icon-chevron-down";
			if (!is_open) return;

			icon.setAttribute("href", "#icon-chevron-right");
			var nested = section.querySelector(".nested-container");
			if (nested) {
				nested.classList.add("hidden");
			}
		});
	}

	function bind_global_accordion() {
		document.addEventListener(
			"click",
			function (event) {
				var section = event.target.closest(".body-sidebar .sidebar-item-container.section-item");
				if (!section) return;
				if (event.target.closest("a")) return;
				close_other_sections(section);
			},
			true
		);
	}

	function init() {
		if (document.body && !document.body.dataset.ctSidebarAccordionBound) {
			document.body.dataset.ctSidebarAccordionBound = "1";
			bind_global_accordion();
		}
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
