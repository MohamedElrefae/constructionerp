/**
 * Construction ERP — Theme Patch v5.0
 * Native Frappe data-theme Architecture (Single Source of Truth)
 *
 * PATCH A: frappe.ui.Theme.prototype.set_theme
 *   Ensures Frappe native theme changes flow through our system.
 *
 * PATCH B: frappe.ui.ThemeSwitcher
 *   Replaces native theme list with Construction Light/Dark.
 *   All selections route to window.ConstructionTheme.setMode().
 *
 * Architecture: html[data-theme="dark"|"light"] → CSS tokens → Component overrides
 */
(function () {
	"use strict";

	console.log(
		"%c[Construction Theme Patch] v5.0 Native Architecture...",
		"color: #3b82f6; font-weight: bold; font-size: 14px;"
	);

	// ── PATCH A: Neutralise frappe.ui.Theme.prototype.set_theme ──────────────
	function patchThemePrototype() {
		if (
			window.frappe &&
			window.frappe.ui &&
			window.frappe.ui.Theme &&
			window.frappe.ui.Theme.prototype
		) {
			window.frappe.ui.Theme.prototype.set_theme = function (theme) {
				const mode = theme === "dark" ? "dark" : "light";
				document.documentElement.setAttribute("data-theme", mode);
				console.log("[ThemePatch A] Intercepted set_theme →", mode);

				// If ConstructionTheme is ready, fetch CSS
				if (window.ConstructionTheme && window.ConstructionTheme.setMode) {
					// Just fetch CSS without re-persisting if it's a native call
					// fetchAndApplyCSS is private, so we use setMode if we want full sync
					// but usually set_theme is called on boot/navigation.
				}
			};
			console.log("[ThemePatch A] frappe.ui.Theme.prototype.set_theme patched.");
		} else {
			setTimeout(patchThemePrototype, 50);
		}
	}

	// ── PATCH B: Replace frappe.ui.ThemeSwitcher ──────────────────────────────
	function patchThemeSwitcher() {
		if (window.frappe && window.frappe.ui && window.frappe.ui.ThemeSwitcher) {
			// 1. Override fetch_themes to show Construction themes
			window.frappe.ui.ThemeSwitcher.prototype.fetch_themes = function () {
				console.log("[ThemePatch B] Providing Construction themes to switcher");
				return new Promise((resolve) => {
					this.themes = [
						{
							name: "construction_light",
							label: "☀️ Construction Light",
							info: "Enterprise Light Theme",
						},
						{
							name: "construction_dark",
							label: "🏗️ Construction Dark",
							info: "Enterprise Dark Theme",
						},
					];
					resolve(this.themes);
				});
			};

			// 2. Override toggle_theme to use our unified setMode
			window.frappe.ui.ThemeSwitcher.prototype.toggle_theme = function (theme) {
				// Map construction theme names to mode
				const mode = theme === "dark" || theme === "construction_dark" ? "dark" : "light";
				console.log("[ThemePatch B] Switcher selected theme:", theme, "-> mode:", mode);

				// Prevent infinite loop - mark as internal change
				if (window.ConstructionTheme) {
					window.ConstructionTheme.isInternalChange = true;
				}

				if (window.ConstructionTheme && window.ConstructionTheme.setMode) {
					window.ConstructionTheme.setMode(mode);
					if (window.frappe.show_alert)
						frappe.show_alert(
							"Theme Changed to Construction " +
								(mode === "dark" ? "Dark" : "Light"),
							2
						);
				} else {
					document.documentElement.setAttribute("data-theme", mode);
				}
			};

			// 3. Override refresh to sync with our state
			window.frappe.ui.ThemeSwitcher.prototype.refresh = function () {
				var currentMode = document.documentElement.getAttribute("data-theme") || "light";
				this.current_theme =
					currentMode === "dark" ? "construction_dark" : "construction_light";
				this.fetch_themes().then(() => {
					this.render();
				});
			};

			console.log("[ThemePatch B] frappe.ui.ThemeSwitcher patched.");
		} else {
			setTimeout(patchThemeSwitcher, 100);
		}
	}

	// ── PATCH C: Global frappe.ui.set_theme ──────────────────────────────────
	function patchGlobalSetTheme() {
		if (window.frappe && window.frappe.ui && window.frappe.ui.set_theme) {
			const original = window.frappe.ui.set_theme;
			window.frappe.ui.set_theme = function (theme) {
				// Call original first (reads data-theme, sets data-theme)
				original.apply(this, arguments);

				// ── Guard: prevent duplicate application ──
				// Read requested from DOM after original.apply() already set it correctly.
				// When called from Frappe's observer/startup with no argument,
				// the 'theme' parameter is undefined so we must NOT derive from it.
				var requested = document.documentElement.getAttribute("data-theme") || "light";
				var current = document.documentElement.getAttribute("data-theme") || "light";

				if (window.ConstructionTheme && window.ConstructionTheme.isInternalChange) {
					window.ConstructionTheme.isInternalChange = false;
					return;
				}

				if (requested === current) {
					return;
				}

				// Ensure data-theme is explicitly set
				document.documentElement.setAttribute("data-theme", requested);

				// Sync ConstructionTheme state without re-persisting
				if (window.ConstructionTheme) {
					window.ConstructionTheme.currentMode = requested;
					if (window.ConstructionTheme.fetchAndApplyCSS) {
						window.ConstructionTheme.fetchAndApplyCSS(requested);
					}
					if (window.ConstructionTheme.updateNavbarLabel) {
						window.ConstructionTheme.updateNavbarLabel(requested);
					}
				}
			};
			console.log("[ThemePatch C] frappe.ui.set_theme patched (no-loop).");
		} else {
			setTimeout(patchGlobalSetTheme, 150);
		}
	}

	// Run patches
	patchThemePrototype();
	patchThemeSwitcher();
	patchGlobalSetTheme();
})();
