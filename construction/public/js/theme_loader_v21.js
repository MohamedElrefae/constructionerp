/**
 * Construction Theme Loader v2.1
 * CRITICAL: Runs synchronously BEFORE DOMContentLoaded
 * to win the race against Frappe's desk.js set_theme()
 */

(function () {
	"use strict";

	// ════════════════════════════════════════════════════════════
	// STEP 1: Inject namespace + data-theme IMMEDIATELY
	// This runs synchronously before any other script
	// ════════════════════════════════════════════════════════════

	var html = document.documentElement;
	var path = window.location.pathname;

	// Only apply on Desk/App routes
	if (path.startsWith("/desk") || path.startsWith("/app")) {
		// Add ct-enterprise class FIRST
		if (!html.classList.contains("ct-enterprise")) {
			html.classList.add("ct-enterprise");
		}

		// Set data-theme BEFORE Frappe's JS runs
		// Check localStorage first (user preference)
		var savedMode = localStorage.getItem("ct-theme-mode");
		if (savedMode === "light") {
			html.setAttribute("data-theme", "light");
			html.setAttribute("data-theme-mode", "light");
		} else if (savedMode === "dark") {
			html.setAttribute("data-theme", "dark");
			html.setAttribute("data-theme-mode", "dark");
		} else {
			// Default to dark for construction ERP
			html.setAttribute("data-theme", "dark");
			html.setAttribute("data-theme-mode", "dark");
			localStorage.setItem("ct-theme-mode", "dark");
		}
	}

	// ════════════════════════════════════════════════════════════
	// STEP 2: Full initialization on DOMContentLoaded
	// ════════════════════════════════════════════════════════════

	document.addEventListener("DOMContentLoaded", function () {
		initTheme();
	});

	function initTheme() {
		// Theme mode toggle
		var currentMode = html.getAttribute("data-theme") || "dark";

		// Render theme toggle dropdown in navbar
		renderNavbarDropdown();

		// Color tree toolbar buttons
		// NOTE: This only runs on initial DOMContentLoaded. Tree views are rendered
		// dynamically by Frappe after page load, so this rarely finds a toolbar.
		// The CSS rules in modern_theme.css handle tree button styling instead.
		// TODO: Replace with MutationObserver if dynamic tree coloring is needed.
		colorTreeToolbarButtons();

		// Remove ghost buttons
		// NOTE: Uses inline style (1,0,0,0 specificity) which overrides all CSS.
		// If a future update needs to show these buttons, this must be changed to
		// a CSS-only approach (e.g., .ghost-btn { display: none !important; })
		removeGhostButtons();

		// Hide Frappe branding
		hideFrappeBranding();

		// NOTE: persist() removed — setMode() already writes to localStorage on
		// every toggle. The old persist() captured stale mode values.

		console.log("[ConstructionTheme] v2.1 initialized in " + currentMode + " mode");
	}

	// ════════════════════════════════════════════════════════════
	// THEME MODE FUNCTIONS
	// ════════════════════════════════════════════════════════════

	function setMode(mode) {
		html.setAttribute("data-theme", mode);
		html.setAttribute("data-theme-mode", mode);
		localStorage.setItem("ct-theme-mode", mode);
		updateNavbarLabel(mode);
		swapLogo(mode);
	}

	function toggleMode() {
		var current = html.getAttribute("data-theme") || "dark";
		var next = current === "dark" ? "light" : "dark";
		setMode(next);
	}

	// ════════════════════════════════════════════════════════════
	// NAVBAR DROPDOWN
	// ════════════════════════════════════════════════════════════

	function renderNavbarDropdown() {
		// Find or create the theme toggle in navbar
		// Frappe v16 Desk uses .desk-header .navbar-nav for the top-right nav.
		// Fall back to .desk-header directly if the nav container isn't found.
		var navbar =
			document.querySelector(".desk-header .navbar-nav") ||
			document.querySelector(".desk-header .navbar-right") ||
			document.querySelector(".desk-header");
		if (!navbar) return;

		// Don't add if already present
		if (document.getElementById("ct-theme-toggle")) return;

		var li = document.createElement("li");
		li.className = "nav-item dropdown";
		li.id = "ct-theme-toggle";
		li.innerHTML =
			'<a class="nav-link dropdown-toggle" href="#" data-toggle="dropdown">' +
			'<span id="ct-theme-label">Theme</span></a>' +
			'<div class="dropdown-menu dropdown-menu-right">' +
			'<a class="dropdown-item" href="#" onclick="ctSetMode(\'dark\'); return false;">Dark</a>' +
			'<a class="dropdown-item" href="#" onclick="ctSetMode(\'light\'); return false;">Light</a>' +
			"</div>";
		navbar.appendChild(li);

		updateNavbarLabel(html.getAttribute("data-theme") || "dark");
	}

	function updateNavbarLabel(mode) {
		var label = document.getElementById("ct-theme-label");
		if (label) {
			label.textContent = mode === "dark" ? "Dark" : "Light";
		}
	}

	// Global function for dropdown onclick
	window.ctSetMode = setMode;

	// ════════════════════════════════════════════════════════════
	// TREE TOOLBAR COLORING
	// ════════════════════════════════════════════════════════════

	function colorTreeToolbarButtons() {
		var toolbar = document.querySelector(".tree-node-toolbar");
		if (!toolbar) return;

		var buttons = toolbar.querySelectorAll(".btn");
		buttons.forEach(function (btn) {
			if (btn.classList.contains("btn-primary")) {
				btn.style.background = "var(--ct-primary)";
			} else if (btn.classList.contains("btn-success")) {
				btn.style.background = "var(--ct-success)";
			} else if (btn.classList.contains("btn-danger")) {
				btn.style.background = "var(--ct-danger)";
			}
		});
	}

	// ════════════════════════════════════════════════════════════
	// GHOST BUTTON REMOVAL
	// ════════════════════════════════════════════════════════════

	function removeGhostButtons() {
		var ghosts = document.querySelectorAll(".btn.ghost-btn, .ghost-btn");
		ghosts.forEach(function (btn) {
			btn.style.display = "none";
		});
	}

	// ════════════════════════════════════════════════════════════
	// BRANDING
	// ════════════════════════════════════════════════════════════

	function hideFrappeBranding() {
		var powered = document.querySelector(".footer-powered");
		if (powered) powered.style.display = "none";
	}

	function swapLogo(mode) {
		var logo = document.querySelector(".app-logo") || document.querySelector(".navbar-brand");
		if (!logo) return;
		// Logo swap logic here if needed
	}

	// NOTE: persist() function removed.
	// setMode() already calls localStorage.setItem() on every toggle.
	// The old persist() captured stale mode at init time and would
	// overwrite the correct value on page exit.
})();
