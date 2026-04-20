/**
 * Modern Theme Loader for ERPNext — Construction ERP
 * Production-ready consolidated build
 * VERSION: 5.1 — 2026-04-17
 *
 * This file is the single source of truth for:
 * - Theme switching (Light / Dark / Construction Light / Construction Dark)
 * - Construction theme CSS injection (inline, bypasses Frappe asset pipeline)
 * - Navbar theme indicator with construction-aware labels
 * - MutationObserver for data-theme normalization
 * - Accessible theme change announcements (aria-live)
 * - TimestampMismatchError-safe persistence via save_user_mode API
 */
(function () {
	"use strict";

	var VERSION = "5.2";
	console.log(
		"%c[Modern Theme] LOADER v" + VERSION + " — Hybrid API+Inline — 20260418",
		"background:#2E7D32;color:#fff;padding:4px 8px;border-radius:4px;font-weight:bold"
	);

	// ─── 0. THEME NAME NORMALIZER ─────────────────────────────────────
	// API returns "Construction Dark" but CSS selectors use "construction_dark"
	function _norm(name) {
		if (!name) return "";
		return name.toLowerCase().replace(/\s+/g, "_");
	}

	// ─── 1. INLINE CSS INJECTION ───────────────────────────────────────
	// Construction theme + button + sidebar styles injected directly into
	// <head> so they work regardless of Frappe's CSS asset pipeline.

	var _css = document.createElement("style");
	_css.id = "construction-theme-css";
	_css.textContent = [
		/* ── Construction Dark ── */
		'html[data-modern-theme="construction_dark"] .navbar{background:#1a3a1e!important;border-bottom:2px solid #4CAF50!important;box-shadow:0 2px 8px rgba(0,0,0,.3)!important}',
		'html[data-modern-theme="construction_dark"] .navbar .nav-link{color:#c8e6c9!important}',
		'html[data-modern-theme="construction_dark"] .navbar .nav-link:hover{color:#4CAF50!important;background:rgba(76,175,80,.1)!important;border-radius:8px!important}',
		'html[data-modern-theme="construction_dark"] .navbar input[type="text"]{background:#1a3a1e!important;border-color:#2d5a32!important;color:#d4e8d5!important}',

		'html[data-modern-theme="construction_dark"] .layout-side-section{background:#0d1f12!important;border-right:1px solid #2d5a32!important}',
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a *,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item .sidebar-item-label,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-item-icon,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-item-icon svg,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-item-icon .icon' +
			"{color:#e8f5e9!important;fill:#e8f5e9!important;stroke:#e8f5e9!important;font-size:13.5px!important}",
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a:hover,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a:hover *,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a:hover .icon' +
			"{color:#fff!important;fill:#4CAF50!important;stroke:#4CAF50!important;background:rgba(76,175,80,.15)!important;border-radius:8px!important}",
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected a,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected a *,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected .icon' +
			"{color:#4CAF50!important;fill:#4CAF50!important;stroke:#4CAF50!important;font-weight:600!important}",
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected a{background:rgba(76,175,80,.2)!important;box-shadow:inset 3px 0 0 #4CAF50!important;border-radius:8px!important}',
		'html[data-modern-theme="construction_dark"] .sidebar-label,' +
			'html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-section-head' +
			"{color:#81C784!important;font-size:.7rem!important;text-transform:uppercase!important;letter-spacing:1px!important}",

		'html[data-modern-theme="construction_dark"] .page-head{background:#0d1f12!important;border-bottom:1px solid #2d5a32!important}',
		'html[data-modern-theme="construction_dark"] .page-head .title-text{color:#d4e8d5!important}',
		'html[data-modern-theme="construction_dark"] .layout-main-section{background:#111a13!important}',
		'html[data-modern-theme="construction_dark"] .page-container{background:#111a13!important}',

		'html[data-modern-theme="construction_dark"] .btn-primary{background:#4CAF50!important;border-color:#4CAF50!important;color:#fff!important;border-radius:10px!important}',
		'html[data-modern-theme="construction_dark"] .btn-primary:hover{background:#66BB6A!important;border-color:#66BB6A!important;transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(76,175,80,.3)!important}',
		'html[data-modern-theme="construction_dark"] .btn-default{background:#1a3a1e!important;border:1px solid #2d5a32!important;color:#a8d5ab!important;border-radius:10px!important}',
		'html[data-modern-theme="construction_dark"] .btn-default:hover{background:rgba(76,175,80,.12)!important;border-color:#4CAF50!important;color:#4CAF50!important;transform:translateY(-1px)!important}',

		'html[data-modern-theme="construction_dark"] a{color:#81C784!important}',
		'html[data-modern-theme="construction_dark"] a:hover{color:#4CAF50!important}',
		'html[data-modern-theme="construction_dark"] h1,html[data-modern-theme="construction_dark"] h2,html[data-modern-theme="construction_dark"] h3{color:#d4e8d5!important}',

		'html[data-modern-theme="construction_dark"] .form-control{background:#1a3a1e!important;border-color:#2d5a32!important;color:#d4e8d5!important}',
		'html[data-modern-theme="construction_dark"] .form-control:focus{border-color:#4CAF50!important;box-shadow:0 0 0 3px rgba(76,175,80,.15)!important}',
		'html[data-modern-theme="construction_dark"] .dropdown-menu{background:#0d1f12!important;border-color:#2d5a32!important}',
		'html[data-modern-theme="construction_dark"] .dropdown-item{color:#a8d5ab!important}',
		'html[data-modern-theme="construction_dark"] .dropdown-item:hover{background:rgba(76,175,80,.12)!important;color:#4CAF50!important}',
		'html[data-modern-theme="construction_dark"] .modal-content{background:#0d1f12!important;border-color:#2d5a32!important}',
		'html[data-modern-theme="construction_dark"] .tree-toolbar-button{background:#1a3a1e!important;border:1px solid #2d5a32!important;color:#a8d5ab!important;border-radius:8px!important}',
		'html[data-modern-theme="construction_dark"] .tree-toolbar-button:hover{background:rgba(76,175,80,.12)!important;border-color:#4CAF50!important;color:#4CAF50!important}',

		/* ── Construction Light ── */
		'html[data-modern-theme="construction_light"] .navbar{background:#f0fdf4!important;border-bottom:2px solid #2E7D32!important}',
		'html[data-modern-theme="construction_light"] .navbar .nav-link{color:#1e293b!important}',
		'html[data-modern-theme="construction_light"] .navbar .nav-link:hover{color:#2E7D32!important;background:rgba(46,125,50,.08)!important;border-radius:8px!important}',
		'html[data-modern-theme="construction_light"] .layout-side-section{background:#f0fdf4!important;border-right:2px solid #2E7D32!important}',
		'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item a,' +
			'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item .sidebar-item-label' +
			"{color:#1b5e20!important}",
		'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item a:hover,' +
			'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item a:hover *' +
			"{color:#2E7D32!important;background:rgba(46,125,50,.08)!important;border-radius:8px!important}",
		'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item.selected a{background:rgba(46,125,50,.12)!important;color:#2E7D32!important;font-weight:600!important;box-shadow:inset 3px 0 0 #2E7D32!important;border-radius:8px!important}',
		'html[data-modern-theme="construction_light"] .btn-primary{background:#2E7D32!important;border-color:#2E7D32!important;border-radius:10px!important}',
		'html[data-modern-theme="construction_light"] .btn-primary:hover{background:#388E3C!important;transform:translateY(-1px)!important}',
		'html[data-modern-theme="construction_light"] .btn-default{border:1px solid #d1e7dd!important;border-radius:10px!important}',
		'html[data-modern-theme="construction_light"] .btn-default:hover{border-color:#2E7D32!important;color:#2E7D32!important}',
		'html[data-modern-theme="construction_light"] a{color:#2E7D32!important}',
		'html[data-modern-theme="construction_light"] .page-head{background:#f0fdf4!important;border-bottom:1px solid #d1e7dd!important}',
		'html[data-modern-theme="construction_light"] .form-control:focus{border-color:#2E7D32!important;box-shadow:0 0 0 3px rgba(46,125,50,.12)!important}',

		/* ── Standard Dark theme sidebar text ── */
		'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item a,' +
			'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item a *,' +
			'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item .sidebar-item-label,' +
			'html[data-theme="dark"] .desk-sidebar .sidebar-item-icon,' +
			'html[data-theme="dark"] .desk-sidebar .sidebar-item-icon svg,' +
			'html[data-theme="dark"] .desk-sidebar .sidebar-item-icon .icon' +
			"{color:#E8E8E8!important;fill:#E8E8E8!important;stroke:#E8E8E8!important}",
		'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item a:hover,' +
			'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item a:hover *,' +
			'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item a:hover .icon' +
			"{color:#fff!important;fill:#2076FF!important;stroke:#2076FF!important;background:rgba(32,118,255,.1)!important;border-radius:8px!important}",
		'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item.selected a,' +
			'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item.selected a *,' +
			'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item.selected .icon' +
			"{color:#2076FF!important;fill:#2076FF!important;stroke:#2076FF!important;font-weight:600!important}",
		'html[data-theme="dark"] .desk-sidebar .standard-sidebar-item.selected a{background:rgba(32,118,255,.15)!important;box-shadow:inset 3px 0 0 #2076FF!important;border-radius:8px!important}',

		/* ── Standard Dark theme — full background coverage ── */
		'html[data-theme="dark"] .navbar{background:#1a1a1a!important;border-bottom:1px solid #333!important;box-shadow:0 1px 4px rgba(0,0,0,.4)!important}',
		'html[data-theme="dark"] .navbar .nav-link{color:#E8E8E8!important}',
		'html[data-theme="dark"] .navbar .nav-link:hover{color:#2076FF!important;background:rgba(32,118,255,.1)!important;border-radius:8px!important}',
		'html[data-theme="dark"] .layout-side-section{background:#1e1e1e!important;border-right:1px solid #333!important}',
		'html[data-theme="dark"] .page-head{background:#1e1e1e!important;border-bottom:1px solid #333!important}',
		'html[data-theme="dark"] .page-head .title-text{color:#E8E8E8!important}',
		'html[data-theme="dark"] .layout-main-section{background:#1a1a1a!important}',
		'html[data-theme="dark"] .page-container{background:#1a1a1a!important}',
		'html[data-theme="dark"] body{background:#1a1a1a!important}',
		'html[data-theme="dark"] .content.page-container{background:#1a1a1a!important}',
		'html[data-theme="dark"] .form-control{background:#2d2d2d!important;border-color:#444!important;color:#E8E8E8!important}',
		'html[data-theme="dark"] .form-control:focus{border-color:#2076FF!important;box-shadow:0 0 0 3px rgba(32,118,255,.15)!important}',
		'html[data-theme="dark"] .btn-primary{background:#2076FF!important;border-color:#2076FF!important;color:#fff!important;border-radius:10px!important}',
		'html[data-theme="dark"] .btn-primary:hover{background:#1a6ae0!important;border-color:#1a6ae0!important}',
		'html[data-theme="dark"] .btn-default{background:#2d2d2d!important;border:1px solid #444!important;color:#ccc!important;border-radius:10px!important}',
		'html[data-theme="dark"] .btn-default:hover{background:rgba(32,118,255,.1)!important;border-color:#2076FF!important;color:#2076FF!important}',
		'html[data-theme="dark"] a{color:#60a5fa!important}',
		'html[data-theme="dark"] a:hover{color:#2076FF!important}',
		'html[data-theme="dark"] h1,html[data-theme="dark"] h2,html[data-theme="dark"] h3{color:#E8E8E8!important}',
		'html[data-theme="dark"] .dropdown-menu{background:#2d2d2d!important;border-color:#444!important}',
		'html[data-theme="dark"] .dropdown-item{color:#ccc!important}',
		'html[data-theme="dark"] .dropdown-item:hover{background:rgba(32,118,255,.1)!important;color:#2076FF!important}',
		'html[data-theme="dark"] .modal-content{background:#2d2d2d!important;border-color:#444!important}',
		'html[data-theme="dark"] .sidebar-label,' +
			'html[data-theme="dark"] .desk-sidebar .sidebar-section-head' +
			"{color:#888!important;font-size:.7rem!important;text-transform:uppercase!important;letter-spacing:1px!important}",

		/* ── Standard Light theme sidebar text ── */
		'html[data-theme="light"] .desk-sidebar .standard-sidebar-item a,' +
			'html[data-theme="light"] .desk-sidebar .standard-sidebar-item a *,' +
			'html[data-theme="light"] .desk-sidebar .standard-sidebar-item .sidebar-item-label,' +
			'html[data-theme="light"] .desk-sidebar .sidebar-item-icon,' +
			'html[data-theme="light"] .desk-sidebar .sidebar-item-icon svg,' +
			'html[data-theme="light"] .desk-sidebar .sidebar-item-icon .icon' +
			"{color:#2C3E50!important;fill:#2C3E50!important;stroke:#2C3E50!important}",
		'html[data-theme="light"] .desk-sidebar .standard-sidebar-item a:hover,' +
			'html[data-theme="light"] .desk-sidebar .standard-sidebar-item a:hover *,' +
			'html[data-theme="light"] .desk-sidebar .standard-sidebar-item a:hover .icon' +
			"{color:#1e293b!important;fill:#2076FF!important;stroke:#2076FF!important;background:rgba(32,118,255,.08)!important;border-radius:8px!important}",
		'html[data-theme="light"] .desk-sidebar .standard-sidebar-item.selected a,' +
			'html[data-theme="light"] .desk-sidebar .standard-sidebar-item.selected a *,' +
			'html[data-theme="light"] .desk-sidebar .standard-sidebar-item.selected .icon' +
			"{color:#2076FF!important;fill:#2076FF!important;stroke:#2076FF!important;font-weight:600!important}",
		'html[data-theme="light"] .desk-sidebar .standard-sidebar-item.selected a{background:rgba(32,118,255,.1)!important;box-shadow:inset 3px 0 0 #2076FF!important;border-radius:8px!important}',

		/* ── Toolbar buttons (all themes) ── */
		".modern-theme-loaded .page-head .btn-default.ellipsis," +
			".modern-theme-loaded .page-head .inner-group-button .btn-default," +
			".modern-theme-loaded .page-head .page-actions .btn-default" +
			"{border:1px solid var(--border-color)!important;border-radius:10px!important;font-size:.8rem!important;font-weight:500!important;padding:6px 14px!important;min-height:36px!important;transition:all .25s cubic-bezier(.4,0,.2,1)!important;background:var(--surface)!important;color:var(--text-primary)!important;box-shadow:0 1px 3px rgba(0,0,0,.06)!important}",
		".modern-theme-loaded .page-head .btn-default.ellipsis:hover," +
			".modern-theme-loaded .page-head .inner-group-button .btn-default:hover," +
			".modern-theme-loaded .page-head .page-actions .btn-default:hover" +
			"{background:var(--hover-bg)!important;border-color:var(--accent)!important;color:var(--accent)!important;transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(0,0,0,.1)!important}",

		/* ── Tree action buttons (all themes) ── */
		".modern-theme-loaded .tree-toolbar-button{border:1px solid var(--border-color)!important;border-radius:8px!important;font-size:.78rem!important;font-weight:500!important;padding:4px 12px!important;min-height:28px!important;transition:all .2s ease!important;background:var(--surface)!important;color:var(--text-primary)!important;margin:0 3px!important}",
		".modern-theme-loaded .tree-toolbar-button:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important;color:var(--accent)!important;transform:translateY(-1px)!important}",
		".modern-theme-loaded .tree-toolbar-button:last-child:hover{border-color:var(--error)!important;color:var(--error)!important;background:rgba(222,63,63,.06)!important}",

		/* ── Primary action polish ── */
		".modern-theme-loaded .page-head .primary-action{border-radius:10px!important}",
		".modern-theme-loaded .page-head .primary-action:hover{transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(46,125,50,.3)!important}",
		".modern-theme-loaded .page-head .icon-btn{border:1px solid var(--border-color)!important;border-radius:10px!important;background:var(--surface)!important}",
		".modern-theme-loaded .page-head .icon-btn:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important}",

		/* ── Body / page-container backgrounds ── */
		'html[data-modern-theme="construction_dark"] body,html[data-modern-theme="construction_dark"] .page-container,html[data-modern-theme="construction_dark"] .content.page-container{background:#111a13!important}',
		'html[data-modern-theme="construction_light"] body,html[data-modern-theme="construction_light"] .page-container,html[data-modern-theme="construction_light"] .content.page-container{background:#f0fdf4!important}',

		/* ── Full-width layout fix — remove container gaps ── */
		".modern-theme-loaded .container{max-width:100%!important;padding-left:0!important;padding-right:0!important}",
		".modern-theme-loaded #page-container{max-width:100%!important}",
		".modern-theme-loaded .main-section{max-width:100%!important;padding:0!important}",
		"html .page-container{margin:0!important;padding:0!important;max-width:100%!important}",
		"html body .content.page-container{margin:0!important;padding:0!important;max-width:100%!important}",
		"html .navbar{margin:0!important;padding-left:12px!important;padding-right:12px!important}",

		/* ── Accessibility ── */
		".modern-theme-loaded .btn-default:focus-visible," +
			".modern-theme-loaded .tree-toolbar-button:focus-visible," +
			".modern-theme-loaded .navbar .nav-link:focus-visible," +
			".modern-theme-loaded .desk-sidebar-item a:focus-visible" +
			"{outline:2px solid var(--accent);outline-offset:2px}",
		"@media(prefers-reduced-motion:reduce){.modern-theme-loaded,.modern-theme-loaded *{transition-duration:.001ms!important;animation-duration:.001ms!important}.modern-theme-loaded .btn-default:hover,.modern-theme-loaded .tree-toolbar-button:hover{transform:none!important}#theme-mode-dot{box-shadow:none!important}}",
	].join("\n");
	document.head.appendChild(_css);

	// ─── 2. THEME LOADER OBJECT ────────────────────────────────────────

	var ModernThemeLoader = {
		currentTheme: null,
		currentMode: null,
		version: VERSION,

		init: function () {
			console.log("[Modern Theme v" + this.version + "] Initializing...");
			if (typeof frappe === "undefined") {
				setTimeout(function () {
					ModernThemeLoader.init();
				}, 100);
				return;
			}

			// Restore construction theme from localStorage (persists across page reloads)
			try {
				var saved = localStorage.getItem("construction_theme");
				if (saved && saved.toLowerCase().indexOf("construction") !== -1) {
					var normalized = _norm(saved);
					document.documentElement.setAttribute("data-modern-theme", normalized);
					this.currentTheme = normalized;
				}
			} catch (e) {
				/* non-critical */
			}

			this.applyTheme();
			this.watchThemeChanges();
			this.injectCSSVariables();
		},

		applyTheme: function (forcedMode) {
			var self = this;
			var currentDomMode = document.documentElement.getAttribute("data-theme");
			var modeToSend = forcedMode || currentDomMode || "light";

			frappe.call({
				method: "construction.api.theme_api.get_effective_desk_theme",
				args: { current_mode: modeToSend },
				callback: function (r) {
					if (!r.message) return;
					var theme_name = r.message.theme_name;
					var mode = r.message.mode;
					var source = r.message.source;

					if (forcedMode && mode !== forcedMode) {
						mode = forcedMode;
						source = "dom_override";
					} else if (modeToSend && mode !== modeToSend) {
						mode = modeToSend;
						source = "request_override";
					}

					self.currentTheme = theme_name;
					self.currentMode = mode;

					document.documentElement.setAttribute("data-theme", mode);

					// Preserve data-modern-theme if set by switch_theme
					var existing = document.documentElement.getAttribute("data-modern-theme");
					if (theme_name !== "Standard") {
						var normalized = _norm(theme_name);
						document.documentElement.setAttribute("data-modern-theme", normalized);
						localStorage.setItem("construction_theme", theme_name);
					} else if (!existing) {
						document.documentElement.removeAttribute("data-modern-theme");
					}

					self.updateNavbarIndicator(mode);

					// Apply feature toggles from API response
					self.applyFeatureToggles(r.message.feature_toggles || {});

					// Load dynamic CSS for non-hardcoded themes
					if (r.message.needs_css_injection) {
						self.fetchAndApplyCSSVariables(theme_name);
					}

					window.dispatchEvent(
						new CustomEvent("modern-theme-applied", {
							detail: { theme_name: theme_name, mode: mode, source: source },
						})
					);
				},
				error: function () {
					if (forcedMode) {
						document.documentElement.setAttribute("data-theme", forcedMode);
						self.currentMode = forcedMode;
						self.updateNavbarIndicator(forcedMode);
					}
				},
			});
		},

		watchThemeChanges: function () {
			var self = this;

			if (window.matchMedia) {
				window
					.matchMedia("(prefers-color-scheme: dark)")
					.addEventListener("change", function (e) {
						self.applyTheme(e.matches ? "dark" : "light");
					});
			}

			var observer = new MutationObserver(function (mutations) {
				for (var i = 0; i < mutations.length; i++) {
					if (mutations[i].attributeName === "data-theme") {
						var rawMode = document.documentElement.getAttribute("data-theme");
						var oldMode = self.currentMode;

						// Normalize construction themes → set data-modern-theme + rewrite to light/dark
						var rawNorm = _norm(rawMode);
						if (rawNorm === "construction_light" || rawNorm === "construction_dark") {
							var baseMode = rawNorm === "construction_light" ? "light" : "dark";
							document.documentElement.setAttribute("data-modern-theme", rawNorm);
							document.documentElement.setAttribute("data-theme", baseMode);
							return; // will re-trigger observer with normalized value
						}

						if (rawMode && rawMode !== oldMode) {
							self.persistModePreference(rawMode);
							self.applyTheme(rawMode);
						}
					}
				}
			});
			observer.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ["data-theme"],
			});
		},

		persistModePreference: function (mode) {
			frappe.call({
				method: "construction.api.theme_api.save_user_mode",
				args: { mode: mode },
				callback: function (r) {
					if (r.message && r.message.success) {
						console.log("[Modern Theme] Persisted mode: " + mode);
					}
				},
				error: function () {
					/* non-critical */
				},
			});
		},

		// ─── 3. FEATURE TOGGLES ───────────────────────────────────────────

		applyFeatureToggles: function (toggles) {
			// Remove all existing ct-theme-* classes
			var classes = document.body.className.split(" ");
			classes = classes.filter(function (c) {
				return !c.startsWith("ct-theme-");
			});
			document.body.className = classes.join(" ");

			// Apply new toggles
			var TOGGLE_MAP = {
				hide_help_button: "ct-theme-hide-help",
				hide_search_bar: "ct-theme-hide-search",
				hide_sidebar: "ct-theme-hide-sidebar",
				hide_like_comment: "ct-theme-hide-like-comment",
				mobile_card_view: "ct-theme-mobile-card",
			};
			for (var field in TOGGLE_MAP) {
				if (toggles[field]) {
					document.body.classList.add(TOGGLE_MAP[field]);
				}
			}
		},

		// ─── 3b. CSS VARIABLES & BODY CLASS ────────────────────────────────

		injectCSSVariables: function () {
			document.body.classList.add("modern-theme-loaded");
			this.injectNavbarIndicator();
		},

		// ─── 3b. DYNAMIC CSS LOADING (for new themes from DocType) ─────────
		// Enhancement: Load additional CSS from API for themes not in inline CSS
		fetchAndApplyCSSVariables: function (themeName) {
			if (!themeName || themeName.toLowerCase().indexOf("construction") !== -1) {
				// Skip for hardcoded construction themes - they use inline CSS
				return;
			}

			// Check if we already loaded CSS for this theme
			var cssId = "dynamic-theme-css-" + themeName;
			if (document.getElementById(cssId)) return;

			// Fetch dynamic CSS from API
			frappe.call({
				method: "construction.api.theme_api.get_theme_css",
				args: { theme_name: themeName },
				callback: function (r) {
					if (r.message && r.message.css) {
						var style = document.createElement("style");
						style.id = cssId;
						style.textContent = r.message.css;
						document.head.appendChild(style);
						console.log("[Modern Theme] Dynamic CSS loaded for:", themeName);
					}
				},
				error: function () {
					// Silently fail - inline CSS is the fallback
					console.log(
						"[Modern Theme] Dynamic CSS failed for:",
						themeName,
						"- using inline fallback"
					);
				},
			});
		},

		// ─── 4. NAVBAR INDICATOR ───────────────────────────────────────────

		injectNavbarIndicator: function () {
			var self = this;
			var check = setInterval(function () {
				var nav =
					document.querySelector(".navbar-nav") ||
					document.querySelector(".nav.navbar-right");
				if (nav && !document.getElementById("modern-theme-indicator")) {
					clearInterval(check);

					var mt = document.documentElement.getAttribute("data-modern-theme");
					var isCon = mt && mt.toLowerCase().indexOf("construction") !== -1;
					var isDark = self.currentMode === "dark";
					var label = isCon
						? isDark
							? "\uD83C\uDFD7\uFE0F Construction Dark"
							: "\uD83C\uDFD7\uFE0F Construction Light"
						: isDark
						? "\uD83C\uDF19 Dark"
						: "\u2600\uFE0F Light";
					var dotColor = isCon ? "#4CAF50" : isDark ? "#60a5fa" : "#fbbf24";

					var li = document.createElement("li");
					li.id = "modern-theme-indicator";
					li.className = "nav-item dropdown";
					li.innerHTML =
						'<a class="nav-link" href="#" style="display:flex;align-items:center;padding:8px 12px;border-radius:20px;background:var(--hover-bg,rgba(0,0,0,.05));margin:0 8px;" onclick="return false;">' +
						'<span id="theme-mode-dot" style="width:10px;height:10px;border-radius:50%;background:' +
						dotColor +
						";box-shadow:0 0 8px " +
						dotColor +
						';margin-right:8px;transition:all .3s ease;"></span>' +
						'<span id="theme-mode-text" style="font-size:.85rem;font-weight:500;">' +
						label +
						"</span>" +
						"</a>";

					var um = nav.querySelector(".dropdown-navbar-user");
					if (um) {
						nav.insertBefore(li, um);
					} else {
						nav.appendChild(li);
					}
					console.log("[Modern Theme] Navbar indicator injected");

					// Aria-live announcer for screen readers
					if (!document.getElementById("theme-change-announcer")) {
						var ann = document.createElement("div");
						ann.id = "theme-change-announcer";
						ann.setAttribute("aria-live", "polite");
						ann.setAttribute("role", "status");
						ann.style.cssText =
							"position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;";
						document.body.appendChild(ann);
					}
				}
			}, 500);
			setTimeout(function () {
				clearInterval(check);
			}, 10000);
		},

		updateNavbarIndicator: function (mode) {
			var dot = document.getElementById("theme-mode-dot");
			var text = document.getElementById("theme-mode-text");
			if (!dot || !text) return;

			var mt = document.documentElement.getAttribute("data-modern-theme");
			var isCon = mt && mt.toLowerCase().indexOf("construction") !== -1;
			var isDark = mode === "dark";

			var label, dotColor;
			if (isCon) {
				label = isDark
					? "\uD83C\uDFD7\uFE0F Construction Dark"
					: "\uD83C\uDFD7\uFE0F Construction Light";
				dotColor = "#4CAF50";
			} else {
				label = isDark ? "\uD83C\uDF19 Dark" : "\u2600\uFE0F Light";
				dotColor = isDark ? "#60a5fa" : "#fbbf24";
			}

			dot.style.background = dotColor;
			dot.style.boxShadow = "0 0 8px " + dotColor;
			text.textContent = label;

			// Announce to screen readers
			var ann = document.getElementById("theme-change-announcer");
			if (ann) {
				ann.textContent = "";
				setTimeout(function () {
					ann.textContent = "Theme changed to " + label;
				}, 100);
			}
		},

		// ─── 5. UTILITIES ──────────────────────────────────────────────────

		getCurrentTheme: function () {
			return { theme: this.currentTheme, mode: this.currentMode };
		},

		refresh: function () {
			this.applyTheme();
		},

		injectDynamicCSS: function (css) {
			if (!css) return;
			var el = document.getElementById("modern-theme-dynamic");
			if (el) el.remove();
			el = document.createElement("style");
			el.id = "modern-theme-dynamic";
			el.textContent = css;
			document.head.appendChild(el);
		},

		loadThemeCSS: function (themeName) {
			var self = this;
			frappe.call({
				method: "construction.api.theme_api.get_theme_css",
				args: { theme_name: themeName },
				callback: function (r) {
					if (r.message && r.message.css) {
						self.injectDynamicCSS(r.message.css);
						console.log(
							"[Modern Theme] Dynamic CSS loaded for:",
							themeName,
							"(" + r.message.css.length + " bytes)"
						);
					}
				},
				error: function () {
					console.log("[Modern Theme] Dynamic CSS failed for:", themeName);
				},
			});
		},

		fetchAndApplyCSSVariables: function (themeName) {
			this.loadThemeCSS(themeName);
		},
	};

	window.ModernThemeLoader = ModernThemeLoader;

	// ─── 6. THEME SWITCHER OVERRIDE ────────────────────────────────────

	// Cache for themes loaded from API
	var _cachedThemes = null;

	if (frappe.ui && frappe.ui.ThemeSwitcher) {
		frappe.ui.ThemeSwitcher = class CustomThemeSwitcher extends frappe.ui.ThemeSwitcher {
			fetch_themes() {
				// Return cached themes immediately if available
				if (_cachedThemes) {
					this.themes = _cachedThemes;
					return Promise.resolve(_cachedThemes);
				}

				return new Promise(
					function (resolve) {
						// Try to fetch from Construction Theme DocType API
						frappe.call({
							method: "construction.api.theme_api.list_available_themes",
							callback: function (r) {
								console.log("[Modern Theme] API response:", r.message);
								if (
									r.message &&
									r.message.success &&
									r.message.themes &&
									r.message.themes.length > 0
								) {
									// Filter to only construction themes from API (exclude Light/Dark duplicates)
									_cachedThemes = r.message.themes
										.filter(function (t) {
											// Only keep themes with "construction" in the name
											return (
												t.name &&
												t.name.toLowerCase().indexOf("construction") !== -1
											);
										})
										.map(function (t) {
											console.log("[Modern Theme] Processing theme:", t);
											return {
												name: t.name,
												label: t.label || t.theme_name || "Unknown",
												info:
													t.info || t.description || t.theme_type || "",
												is_construction: true,
												theme_doc: t.theme_doc || t.name,
											};
										});
									// Add standard Frappe themes (only these 3)
									_cachedThemes.push(
										{
											name: "dark",
											label: "🌙 Dark",
											info: "Frappe Dark Theme",
										},
										{
											name: "light",
											label: "☀️ Light",
											info: "Frappe Light Theme",
										},
										{
											name: "automatic",
											label: "⚡ Automatic",
											info: "Follows system preference",
										}
									);
								} else {
									// Fallback to hardcoded themes
									_cachedThemes = [
										{
											name: "light",
											label: "☀️ Light",
											info: "Frappe Light Theme",
										},
										{
											name: "dark",
											label: "🌙 Dark",
											info: "Frappe Dark Theme",
										},
										{
											name: "construction_light",
											label: "🏗️ Construction Light",
											info: "Green-accented light theme",
										},
										{
											name: "construction_dark",
											label: "🏗️ Construction Dark",
											info: "Green-accented dark theme",
										},
										{
											name: "automatic",
											label: "⚡ Automatic",
											info: "Follows system preference",
										},
									];
								}
								this.themes = _cachedThemes;
								resolve(_cachedThemes);
							}.bind(this),
							error: function () {
								// API failed — use hardcoded fallback
								_cachedThemes = [
									{
										name: "light",
										label: "☀️ Light",
										info: "Frappe Light Theme",
									},
									{ name: "dark", label: "🌙 Dark", info: "Frappe Dark Theme" },
									{
										name: "construction_light",
										label: "🏗️ Construction Light",
										info: "Green-accented light theme",
									},
									{
										name: "construction_dark",
										label: "🏗️ Construction Dark",
										info: "Green-accented dark theme",
									},
									{
										name: "automatic",
										label: "⚡ Automatic",
										info: "Follows system preference",
									},
								];
								this.themes = _cachedThemes;
								resolve(_cachedThemes);
							}.bind(this),
						});
					}.bind(this)
				);
			}

			render_themes() {
				// Clear existing themes
				this.$body.empty();

				// Render each theme using our data format
				this.themes.forEach(
					function (theme) {
						var $item = $(`
            <div class="theme-item" data-theme="${theme.name}">
              <div class="theme-preview">
                <div class="theme-header"></div>
              </div>
              <div class="theme-label">${theme.label || theme.name}</div>
              <div class="theme-info">${theme.info || ""}</div>
            </div>
          `);

						$item.on(
							"click",
							function () {
								this.switch_theme(theme.name);
							}.bind(this)
						);

						this.$body.append($item);
					}.bind(this)
				);

				// Mark current theme as checked
				this.themes.forEach(
					function (theme) {
						var current = document.documentElement.getAttribute("data-theme");
						var modern = document.documentElement.getAttribute("data-modern-theme");
						var isActive =
							theme.name === modern ||
							(theme.name === "dark" && current === "dark" && !modern) ||
							(theme.name === "light" && current === "light" && !modern);

						if (isActive) {
							this.$body.find(`[data-theme="${theme.name}"]`).addClass("active");
						}
					}.bind(this)
				);
			}

			switch_theme(theme_name) {
				var targetMode = "light";
				var themeLower = theme_name.toLowerCase();
				if (themeLower === "dark" || themeLower.indexOf("dark") !== -1)
					targetMode = "dark";
				else if (themeLower === "light" || themeLower.indexOf("light") !== -1)
					targetMode = "light";
				else if (themeLower === "automatic") {
					targetMode =
						window.matchMedia &&
						window.matchMedia("(prefers-color-scheme: dark)").matches
							? "dark"
							: "light";
				}

				// DO NOT call super.switch_theme() — it triggers frappe.client.set_value
				// which causes TimestampMismatchError.

				// Check if it's a construction theme (case-insensitive)
				var isConstructionTheme = theme_name.toLowerCase().indexOf("construction") !== -1;

				if (isConstructionTheme) {
					var normalizedTheme = _norm(theme_name);
					document.documentElement.setAttribute("data-modern-theme", normalizedTheme);
					localStorage.setItem("construction_theme", theme_name);
					ModernThemeLoader.currentTheme = normalizedTheme;
					frappe.call({
						method: "construction.api.theme_api.set_user_theme",
						args: { theme: theme_name, mode: targetMode },
						callback: function (r) {
							// Also fetch and inject the theme's CSS variables
							ModernThemeLoader.loadThemeCSS(theme_name);
						},
						error: function () {},
					});
				} else {
					document.documentElement.removeAttribute("data-modern-theme");
					localStorage.removeItem("construction_theme");
					ModernThemeLoader.currentTheme = "Standard";
					// Remove dynamic CSS
					var dynEl = document.getElementById("modern-theme-dynamic");
					if (dynEl) dynEl.remove();
				}

				document.documentElement.setAttribute("data-theme", targetMode);
				ModernThemeLoader.currentMode = targetMode;
				ModernThemeLoader.persistModePreference(targetMode);
				ModernThemeLoader.updateNavbarIndicator(targetMode);

				// Persist construction theme choice to localStorage for page reload
				try {
					localStorage.setItem(
						"construction_theme",
						isConstructionTheme ? _norm(theme_name) : ""
					);
				} catch (e) {
					/* non-critical */
				}

				this.hide();
			}

			render() {
				try {
					super.render();
				} catch (e) {
					/* non-critical */
				}
				setTimeout(
					function () {
						this._applyVisualIndicators();
					}.bind(this),
					150
				);
			}

			_applyVisualIndicators() {
				var ct = ModernThemeLoader.currentTheme || "Standard";
				var cm = ModernThemeLoader.currentMode || "light";
				var sel = ct === "Standard" ? (cm === "dark" ? "dark" : "light") : ct;
				document.body.setAttribute("data-selected-theme", sel);
				if (!this.$wrapper || !this.$wrapper.length) return;
				this.$wrapper.find(".theme-item").each(function () {
					var $i = $(this),
						t = $i.data("theme");
					$i.removeClass("active-theme")
						.css({ border: "", background: "" })
						.find(".selected-indicator")
						.remove();
					if (t === sel) {
						$i.addClass("active-theme").css({
							border: "2px solid #2E7D32",
							background: "rgba(46,125,50,.1)",
						});
						$i.find(".theme-label").prepend(
							'<span class="selected-indicator" style="color:#2E7D32;font-weight:bold;margin-right:8px;">\u2713 </span>'
						);
					}
				});
			}
		};
	}

	// ─── 7. INIT ───────────────────────────────────────────────────────

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", function () {
			ModernThemeLoader.init();
		});
	} else {
		setTimeout(function () {
			ModernThemeLoader.init();
		}, 0);
	}
})();
