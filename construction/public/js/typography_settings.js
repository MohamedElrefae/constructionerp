/* eslint-disable */
(function () {
	"use strict";
	var assetVersion = "21";

	var defaults = {
		desk_font_family: "System Default",
		desk_font_size: 14,
		desk_font_weight: "400",
		sidebar_font_family: "Inherit",
		sidebar_font_size: 13,
		sidebar_font_weight: "500",
		navbar_font_family: "Inherit",
		navbar_font_size: 14,
		navbar_font_weight: "500",
		form_font_family: "Inherit",
		form_font_size: 14,
		form_font_weight: "400",
		list_font_family: "Inherit",
		list_font_size: 13,
		list_font_weight: "400",
		menu_font_family: "Inherit",
		menu_font_size: 13,
		menu_font_weight: "400",
	};

	// Maintained alongside server-side allowed_fonts sets in:
	// - construction/api/theme_api.py (lines 2933-2955)
	// - construction/doctype/user_desk_theme/user_desk_theme.py (lines 37-59)
	var fontStacks = {
		Inherit: null,
		"System Default": "",
		Inter: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
		Arial: "Arial, Helvetica, sans-serif",
		Helvetica: '"Helvetica Neue", Helvetica, Arial, sans-serif',
		Tahoma: "Tahoma, Arial, sans-serif",
		Verdana: "Verdana, Geneva, sans-serif",
		"Trebuchet MS": '"Trebuchet MS", Arial, sans-serif',
		Georgia: 'Georgia, "Times New Roman", serif',
		"Times New Roman": '"Times New Roman", Times, serif',
		"Courier New": '"Courier New", Courier, monospace',
		Roboto: '"Roboto", Arial, sans-serif',
		"Open Sans": '"Open Sans", Arial, sans-serif',
		Lato: '"Lato", Arial, sans-serif',
		Montserrat: '"Montserrat", Arial, sans-serif',
		Poppins: '"Poppins", Arial, sans-serif',
		"Noto Sans": '"Noto Sans", Arial, sans-serif',
		"Noto Sans Arabic": '"Noto Sans Arabic", Tahoma, Arial, sans-serif',
		Cairo: '"Cairo", Tahoma, Arial, sans-serif',
		Tajawal: '"Tajawal", Tahoma, Arial, sans-serif',
		Almarai: '"Almarai", Tahoma, Arial, sans-serif',
	};

	var webFontOptions = [
		"Inter",
		"Cairo",
		"Tajawal",
		"Noto Sans Arabic",
		"Almarai",
		"Roboto",
		"Open Sans",
		"Lato",
		"Montserrat",
		"Poppins",
		"Noto Sans",
	];

	var localFontOptions = [
		"System Default",
		"Arial",
		"Helvetica",
		"Tahoma",
		"Verdana",
		"Trebuchet MS",
		"Georgia",
		"Times New Roman",
		"Courier New",
	];

	function sectionOption(label) {
		return { label: label, value: "__section_" + label, disabled: true };
	}

	function fontOption(font) {
		return { label: font, value: font };
	}

	var deskFontOptions = [sectionOption("Web Fonts (recommended)")].concat(
		webFontOptions.map(fontOption),
		[sectionOption("Local System Fonts (depends on device)")],
		localFontOptions.map(fontOption)
	);

	var componentFontOptions = [
		{ label: "Inherit", value: "Inherit" },
		sectionOption("Web Fonts (recommended)"),
	].concat(
		webFontOptions.map(fontOption),
		[sectionOption("Local System Fonts (depends on device)")],
		localFontOptions.map(fontOption)
	);

	// Must only contain fonts that also exist in fontStacks.
	// Google Fonts load asynchronously; display=swap mitigates FOUT.
	var googleFontNames = new Set(webFontOptions);

	var fontOptions = Object.keys(fontStacks);
	var componentFamilyFields = [
		"sidebar_font_family",
		"navbar_font_family",
		"form_font_family",
		"list_font_family",
		"menu_font_family",
	];
	var styleOrderObserverStarted = false;

	// ── CSS selector groups for literal style generation ──
	// Defined once to avoid GC pressure during repeated ensureStyleTag calls.

	var DESK_SELECTORS = ["html.ct-enterprise,", "html.ct-enterprise body"];

	var BODY_STAR_SELECTORS = [
		'html.ct-enterprise body *:not(svg):not(path):not(use):not(i):not(.icon):not([class^="icon-"]):not([class*=" icon-"]):not(.fa):not([class^="fa-"]):not([class*=" fa-"]):not(.octicon)',
	];

	var SIDEBAR_SELECTORS = [
		"html.ct-enterprise .body-sidebar .sidebar-item-label",
		"html.ct-enterprise .body-sidebar .item-anchor",
		"html.ct-enterprise .body-sidebar .collapse-sidebar-link",
		"html.ct-enterprise .body-sidebar .onboarding-sidebar",
		"html.ct-enterprise .desk-sidebar .standard-sidebar-item",
		"html.ct-enterprise .standard-sidebar .standard-sidebar-item",
		"html.ct-enterprise .desk-sidebar .standard-sidebar-item > a.item-anchor",
		"html.ct-enterprise .standard-sidebar .standard-sidebar-item > a.item-anchor",
		"html.ct-enterprise .desk-sidebar .sidebar-item-label",
		"html.ct-enterprise .standard-sidebar .sidebar-item-label",
		"html.ct-enterprise .sidebar-container .sidebar-item-label",
		"html.ct-enterprise .sidebar-container .sidebar-link",
		"html.ct-enterprise .sidebar-container .sidebar-item",
		"html.ct-enterprise .standard-sidebar-item",
		"html.ct-enterprise .body-sidebar .sidebar-item-container",
		"html.ct-enterprise .body-sidebar .sidebar-item-container a",
		"html.ct-enterprise .standard-sidebar-item a",
	];

	var NAVBAR_SELECTORS = [
		"html.ct-enterprise .navbar",
		"html.ct-enterprise .navbar .nav-link",
		"html.ct-enterprise .navbar .navbar-brand",
		'html.ct-enterprise .navbar *:not(svg):not(path):not(use):not(i):not(.icon):not([class^="icon-"]):not([class*=" icon-"]):not(.fa):not([class^="fa-"]):not([class*=" fa-"]):not(.octicon)',
		"html.ct-enterprise .desktop-navbar",
		'html.ct-enterprise .desktop-navbar *:not(svg):not(path):not(use):not(i):not(.icon):not([class^="icon-"]):not([class*=" icon-"]):not(.fa):not([class^="fa-"]):not([class*=" fa-"]):not(.octicon)',
		"html.ct-enterprise .ct-topbar-zone",
	];

	var FORM_SELECTORS = [
		"html.ct-enterprise .form-layout",
		"html.ct-enterprise .form-section",
		"html.ct-enterprise .frappe-control",
		"html.ct-enterprise .form-control",
		"html.ct-enterprise .control-input",
		"html.ct-enterprise .control-input-wrapper",
		"html.ct-enterprise .like-disabled-input",
		"html.ct-enterprise .page-form .frappe-control",
		"html.ct-enterprise .page-form .form-control",
		"html.ct-enterprise .page-form input",
		"html.ct-enterprise .page-form select",
		"html.ct-enterprise .page-form .btn",
		"html.ct-enterprise .control-label",
	];

	var LIST_SELECTORS = [
		"html.ct-enterprise .list-row",
		"html.ct-enterprise .list-row-head",
		"html.ct-enterprise .list-row *",
		"html.ct-enterprise .list-row-head *",
		"html.ct-enterprise .frappe-list",
		"html.ct-enterprise .frappe-list *",
		"html.ct-enterprise .list-paging-area",
		"html.ct-enterprise .list-paging-area *",
		"html.ct-enterprise .datatable",
		"html.ct-enterprise .datatable *",
		"html.ct-enterprise .dt-cell",
		"html.ct-enterprise .report-wrapper",
	];

	var MENU_SELECTORS = [
		"html.ct-enterprise .dropdown-menu",
		"html.ct-enterprise .dropdown-menu *",
		"html.ct-enterprise .dropdown-item",
		"html.ct-enterprise .awesomplete ul",
		"html.ct-enterprise .awesomplete ul *",
		"html.ct-enterprise .ct-dropdown-list",
		"html.ct-enterprise .ct-dropdown-list *",
		"html.ct-enterprise .ct-unified-dropdown",
		"html.ct-enterprise .ct-unified-dropdown *",
		"html.ct-enterprise .search-dialog",
	];

	// Static CSS rules not dependent on settings (preview UI, menu button).
	var STATIC_RULES = [
		"html.ct-enterprise .ct-typography-preview {",
		"  border: 1px solid var(--border-color, #d1d8dd);",
		"  border-radius: 8px;",
		"  padding: 12px;",
		"  background: var(--fg-color, #fff);",
		"  color: var(--text-color, #192734);",
		"}",
		"html.ct-enterprise .ct-typography-preview .sidebar-sample {",
		"  margin-top: 8px;",
		"  color: var(--text-muted, #6c7680);",
		"}",
		"html.ct-enterprise .ct-typography-user-menu {",
		"  display: flex;",
		"  align-items: center;",
		"  gap: 10px;",
		"  min-height: 34px;",
		"  margin: 2px 0 8px;",
		"  padding: 6px 8px;",
		"  border-radius: 8px;",
		"  color: var(--ink-gray-8);",
		"  text-decoration: none;",
		"  cursor: pointer;",
		"}",
		"html.ct-enterprise .ct-typography-user-menu:hover {",
		"  background: var(--sidebar-hover-color, rgba(0, 0, 0, 0.06));",
		"  text-decoration: none;",
		"}",
		"html.ct-enterprise .ct-typography-user-menu .ct-typography-icon {",
		"  display: inline-flex;",
		"  align-items: center;",
		"  justify-content: center;",
		"  width: 28px;",
		"  min-width: 28px;",
		"  height: 28px;",
		"  font-weight: 700;",
		"}",
		"html.ct-enterprise .body-sidebar-container:not(.expanded) .ct-typography-user-menu span:not(.ct-typography-icon) {",
		"  display: none;",
		"}",
		// Chromium forced repaint: brief invisible animation forces full style recalc.
		"@keyframes ct-typography-repaint {",
		"  0% { opacity: 0.9999; }",
		"  100% { opacity: 1; }",
		"}",
	].join("\n");

	// ── Helpers ──

	function normalize(settings) {
		settings = Object.assign({}, defaults, settings || {});
		[
			["desk_font_size", 14],
			["sidebar_font_size", 13],
			["navbar_font_size", 14],
			["form_font_size", 14],
			["list_font_size", 13],
			["menu_font_size", 13],
		].forEach(function (item) {
			settings[item[0]] = clamp(parseInt(settings[item[0]], 10), 11, 20, item[1]);
		});
		[
			["desk_font_weight", "400"],
			["sidebar_font_weight", "500"],
			["navbar_font_weight", "500"],
			["form_font_weight", "400"],
			["list_font_weight", "400"],
			["menu_font_weight", "400"],
		].forEach(function (item) {
			settings[item[0]] = normalizeWeight(settings[item[0]], item[1]);
		});
		["desk", "sidebar", "navbar", "form", "list", "menu"].forEach(function (component) {
			var fieldname = component + "_font_family";
			if (!Object.prototype.hasOwnProperty.call(fontStacks, settings[fieldname])) {
				settings[fieldname] = component === "desk" ? "System Default" : "Inherit";
			}
		});
		return settings;
	}

	function clamp(value, min, max, fallback) {
		if (Number.isNaN(value)) return fallback;
		return Math.max(min, Math.min(max, value));
	}

	function normalizeWeight(value, fallback) {
		value = String(value || fallback);
		return ["300", "400", "500", "600", "700"].indexOf(value) === -1 ? fallback : value;
	}

	function resolveFont(settings, fieldname) {
		var font = settings[fieldname];
		return font === "Inherit" ? settings.desk_font_family : font;
	}

	function fontStack(fontName) {
		return fontStacks[fontName] || "";
	}

	function closeOpenMenus() {
		document.querySelectorAll(".dropdown-menu.show").forEach(function (m) {
			m.classList.remove("show");
		});
	}

	// ── Google Fonts Loader ──

	function loadNeededGoogleFonts(settings) {
		var seen = {};
		var families = [];
		var fields = [
			"desk_font_family",
			"sidebar_font_family",
			"navbar_font_family",
			"form_font_family",
			"list_font_family",
			"menu_font_family",
		];
		fields.forEach(function (field) {
			var font = resolveFont(settings, field);
			if (googleFontNames.has(font) && !seen[font]) {
				seen[font] = true;
				families.push(font);
			}
		});

		var link = document.getElementById("ct-google-fonts");

		if (families.length === 0) {
			if (link) link.remove();
			return;
		}

		var params = families.map(function (name) {
			return "family=" + name.replace(/ /g, "+") + ":wght@300;400;500;600;700";
		});
		params.push("display=swap");

		var href = "https://fonts.googleapis.com/css2?" + params.join("&");

		if (link) {
			if (link.href !== href) link.href = href;
		} else {
			link = document.createElement("link");
			link.id = "ct-google-fonts";
			link.rel = "stylesheet";
			link.href = href;
			document.head.appendChild(link);
		}
	}

	// ── Literal CSS Stylesheet Generation ──

	function generateComponentCSS(selectors, family, size, weight) {
		var fml = fontStack(family) || "inherit";
		return (
			selectors.join(",\n") +
			" {\n" +
			"  font-family: " +
			fml +
			" !important;\n" +
			"  font-size: " +
			size +
			"px !important;\n" +
			"  font-weight: " +
			weight +
			" !important;\n" +
			"}"
		);
	}

	function ensureStyleTag(settings) {
		var id = "ct-typography-style";
		var style = document.getElementById(id);
		if (!style) {
			style = document.createElement("style");
			style.id = id;
			document.head.appendChild(style);
		}

		var dFam = settings.desk_font_family;
		var dSz = settings.desk_font_size;
		var dWgt = settings.desk_font_weight;

		var sFam = resolveFont(settings, "sidebar_font_family");
		var sSz = settings.sidebar_font_size;
		var sWgt = settings.sidebar_font_weight;

		var nFam = resolveFont(settings, "navbar_font_family");
		var nSz = settings.navbar_font_size;
		var nWgt = settings.navbar_font_weight;

		var fFam = resolveFont(settings, "form_font_family");
		var fSz = settings.form_font_size;
		var fWgt = settings.form_font_weight;

		var lFam = resolveFont(settings, "list_font_family");
		var lSz = settings.list_font_size;
		var lWgt = settings.list_font_weight;

		var mFam = resolveFont(settings, "menu_font_family");
		var mSz = settings.menu_font_size;
		var mWgt = settings.menu_font_weight;

		var parts = [
			generateComponentCSS(DESK_SELECTORS, dFam, dSz, dWgt),
			generateComponentCSS(BODY_STAR_SELECTORS, dFam, dSz, dWgt),
			generateComponentCSS(SIDEBAR_SELECTORS, sFam, sSz, sWgt),
			generateComponentCSS(NAVBAR_SELECTORS, nFam, nSz, nWgt),
			generateComponentCSS(FORM_SELECTORS, fFam, fSz, fWgt),
			generateComponentCSS(LIST_SELECTORS, lFam, lSz, lWgt),
			generateComponentCSS(MENU_SELECTORS, mFam, mSz, mWgt),
			STATIC_RULES,
		];

		style.textContent = parts.join("\n\n");

		if (document.head.lastElementChild !== style) {
			document.head.appendChild(style);
		}
		startStyleOrderObserver(style);
	}

	// ── Style Order Observer ──
	// Keeps #ct-typography-style as the last child of <head> so it wins
	// against late-injected Frappe styles. The lastElementChild guard
	// prevents micro-loops when ensureStyleTag re-appends.

	function startStyleOrderObserver(style) {
		if (styleOrderObserverStarted || !window.MutationObserver) return;
		styleOrderObserverStarted = true;

		var pending = false;
		var observer = new MutationObserver(function () {
			if (pending || !style.isConnected) return;
			pending = true;
			setTimeout(function () {
				pending = false;
				if (style.isConnected && document.head.lastElementChild !== style) {
					document.head.appendChild(style);
				}
			}, 0);
		});
		observer.observe(document.head, { childList: true });
	}

	// ── Repaint Invalidation (Chromium/Edge) ──
	// Chromium often skips repaint for style.textContent changes on
	// existing <style> elements, even with literal font stacks that
	// differ from the previous value. A brief invisible opacity animation
	// on <body> forces synchronous style recalculation in the compositor.

	function triggerRepaint() {
		var body = document.body;
		if (!body) return;
		body.style.animation = "ct-typography-repaint 0.01s";
		void body.offsetHeight;
		body.style.animation = "";
	}

	function shouldSkipInlineTypography(el) {
		if (!el || !el.style || !el.tagName) return true;
		var tag = el.tagName.toLowerCase();
		if (
			["svg", "path", "use", "img", "canvas", "video", "style", "script"].indexOf(tag) !== -1
		) {
			return true;
		}
		var className = typeof el.className === "string" ? el.className : "";
		return (
			/(^|\s)(icon|octicon|fa|avatar|indicator)(\s|$)/.test(className) ||
			/(^|\s)(icon-|fa-)/.test(className)
		);
	}

	function applyInlineTypographyFallback(settings) {
		if (!document.body) return;

		var rules = [
			{
				selector: "body, body *",
				family: settings.desk_font_family,
				size: settings.desk_font_size,
				weight: settings.desk_font_weight,
			},
			{
				selector: SIDEBAR_SELECTORS.join(","),
				family: resolveFont(settings, "sidebar_font_family"),
				size: settings.sidebar_font_size,
				weight: settings.sidebar_font_weight,
			},
			{
				selector: NAVBAR_SELECTORS.join(","),
				family: resolveFont(settings, "navbar_font_family"),
				size: settings.navbar_font_size,
				weight: settings.navbar_font_weight,
			},
			{
				selector: FORM_SELECTORS.join(","),
				family: resolveFont(settings, "form_font_family"),
				size: settings.form_font_size,
				weight: settings.form_font_weight,
			},
			{
				selector: LIST_SELECTORS.join(","),
				family: resolveFont(settings, "list_font_family"),
				size: settings.list_font_size,
				weight: settings.list_font_weight,
			},
			{
				selector: MENU_SELECTORS.join(","),
				family: resolveFont(settings, "menu_font_family"),
				size: settings.menu_font_size,
				weight: settings.menu_font_weight,
			},
		];

		rules.forEach(function (rule) {
			var family = fontStack(rule.family) || "";
			document.querySelectorAll(rule.selector).forEach(function (el) {
				if (shouldSkipInlineTypography(el)) return;
				el.style.setProperty("font-family", family, "important");
				el.style.setProperty("font-size", rule.size + "px", "important");
				el.style.setProperty("font-weight", rule.weight, "important");
			});
		});
		window.ctTypographyInlineFallbackAppliedAt = new Date().toISOString();
	}

	// ── Main Apply Function ──

	function applyTypography(settings) {
		settings = normalize(settings);
		loadNeededGoogleFonts(settings);
		ensureStyleTag(settings);

		// Legacy CSS variable compatibility (not consumed by known CSS files).
		var root = document.documentElement;
		setFontVariable(root, "desk", settings.desk_font_family, settings);
		["sidebar", "navbar", "form", "list", "menu"].forEach(function (component) {
			setFontVariable(root, component, settings[component + "_font_family"], settings);
		});
		root.style.setProperty("--ct-desk-font-size", settings.desk_font_size + "px");
		root.style.setProperty("--ct-desk-font-weight", settings.desk_font_weight);
		["sidebar", "navbar", "form", "list", "menu"].forEach(function (component) {
			root.style.setProperty(
				"--ct-" + component + "-font-size",
				settings[component + "_font_size"] + "px"
			);
			root.style.setProperty(
				"--ct-" + component + "-font-weight",
				settings[component + "_font_weight"]
			);
		});

		// Safety net: inline !important on <html> and <body> for FOUC prevention.
		applyRootTypographyStyles(settings);
		// v9 wrote inline !important font styles onto descendants. Update those
		// inline values too, otherwise no repaint mechanism can beat them.
		applyInlineTypographyFallback(settings);

		triggerRepaint();

		window.ctTypographySettings = settings;
		window.ctTypographyLastAppliedAt = new Date().toISOString();
		try {
			localStorage.setItem("ct-typography-settings", JSON.stringify(settings));
		} catch (e) {}
		return settings;
	}

	// ── Backward Compat: Legacy CSS Variables ──

	function setFontVariable(root, component, selectedFont, settings) {
		var value = fontStacks[selectedFont];
		var property = "--ct-" + component + "-font-family";
		if (!value && component !== "desk" && settings) {
			value = fontStacks[settings.desk_font_family];
		}
		root.style.setProperty(property, value || "");
	}

	// ── Inline Root Fallback ──

	function applyRootTypographyStyles(settings) {
		var deskFamily = fontStacks[settings.desk_font_family] || "";
		var root = document.documentElement;
		var body = document.body;

		root.style.setProperty("font-family", deskFamily || "", "important");
		root.style.setProperty("font-size", settings.desk_font_size + "px", "important");
		root.style.setProperty("font-weight", settings.desk_font_weight, "important");

		if (body) {
			body.style.setProperty("font-family", deskFamily || "", "important");
			body.style.setProperty("font-size", settings.desk_font_size + "px", "important");
			body.style.setProperty("font-weight", settings.desk_font_weight, "important");
		}
	}

	// ── Dialog Preview ──

	function updatePreview(dialog) {
		var values = dialog.get_values() || {};
		var settings = normalize(values);
		var preview = dialog.$wrapper.find(".ct-typography-preview").get(0);
		if (!preview) return;

		var family = fontStacks[settings.desk_font_family] || "";
		preview.style.fontFamily = family || "";
		preview.style.fontSize = settings.desk_font_size + "px";
		preview.style.fontWeight = settings.desk_font_weight;

		var sidebar = preview.querySelector(".sidebar-sample");
		if (sidebar) {
			sidebar.style.fontSize = settings.sidebar_font_size + "px";
			sidebar.style.fontWeight = settings.sidebar_font_weight;
			sidebar.style.fontFamily = fontStacks[settings.sidebar_font_family] || family || "";
		}
	}

	// ── Dialog ──

	function showDialog() {
		loadSettings(function (current) {
			buildDialog(current);
		});
	}

	function buildDialog(current) {
		current = normalize(current);
		var lastDeskFontFamily = current.desk_font_family;
		var dialog = new frappe.ui.Dialog({
			title: __("Typography Settings"),
			fields: [
				{
					fieldtype: "Select",
					fieldname: "desk_font_family",
					label: __("Font Family"),
					options: deskFontOptions,
					default: current.desk_font_family,
				},
				{
					fieldtype: "Int",
					fieldname: "desk_font_size",
					label: __("Desk Font Size"),
					default: current.desk_font_size,
					description: __("11 to 20 px"),
				},
				{
					fieldtype: "Select",
					fieldname: "desk_font_weight",
					label: __("Desk Font Weight"),
					options: "300\n400\n500\n600\n700",
					default: current.desk_font_weight,
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: "Select",
					fieldname: "sidebar_font_family",
					label: __("Sidebar Font Family"),
					options: componentFontOptions,
					default: current.sidebar_font_family,
				},
				{
					fieldtype: "Int",
					fieldname: "sidebar_font_size",
					label: __("Sidebar Font Size"),
					default: current.sidebar_font_size,
					description: __("11 to 20 px"),
				},
				{
					fieldtype: "Select",
					fieldname: "sidebar_font_weight",
					label: __("Sidebar Font Weight"),
					options: "300\n400\n500\n600\n700",
					default: current.sidebar_font_weight,
				},
				{ fieldtype: "Section Break", label: __("Components") },
				{
					fieldtype: "Select",
					fieldname: "navbar_font_family",
					label: __("Navbar Font Family"),
					options: componentFontOptions,
					default: current.navbar_font_family,
				},
				{
					fieldtype: "Int",
					fieldname: "navbar_font_size",
					label: __("Navbar Font Size"),
					default: current.navbar_font_size,
				},
				{
					fieldtype: "Select",
					fieldname: "navbar_font_weight",
					label: __("Navbar Font Weight"),
					options: "300\n400\n500\n600\n700",
					default: current.navbar_font_weight,
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: "Select",
					fieldname: "menu_font_family",
					label: __("Menu Font Family"),
					options: componentFontOptions,
					default: current.menu_font_family,
				},
				{
					fieldtype: "Int",
					fieldname: "menu_font_size",
					label: __("Menu Font Size"),
					default: current.menu_font_size,
				},
				{
					fieldtype: "Select",
					fieldname: "menu_font_weight",
					label: __("Menu Font Weight"),
					options: "300\n400\n500\n600\n700",
					default: current.menu_font_weight,
				},
				{ fieldtype: "Section Break" },
				{
					fieldtype: "Select",
					fieldname: "form_font_family",
					label: __("Form Font Family"),
					options: componentFontOptions,
					default: current.form_font_family,
				},
				{
					fieldtype: "Int",
					fieldname: "form_font_size",
					label: __("Form Font Size"),
					default: current.form_font_size,
				},
				{
					fieldtype: "Select",
					fieldname: "form_font_weight",
					label: __("Form Font Weight"),
					options: "300\n400\n500\n600\n700",
					default: current.form_font_weight,
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: "Select",
					fieldname: "list_font_family",
					label: __("List Font Family"),
					options: componentFontOptions,
					default: current.list_font_family,
				},
				{
					fieldtype: "Int",
					fieldname: "list_font_size",
					label: __("List Font Size"),
					default: current.list_font_size,
				},
				{
					fieldtype: "Select",
					fieldname: "list_font_weight",
					label: __("List Font Weight"),
					options: "300\n400\n500\n600\n700",
					default: current.list_font_weight,
				},
				{ fieldtype: "Section Break" },
				{
					fieldtype: "HTML",
					fieldname: "preview",
					options:
						'<div class="ct-typography-preview">' +
						"<div>Desk text preview for forms, lists, and reports</div>" +
						'<div class="sidebar-sample">Sidebar item preview</div>' +
						"</div>",
				},
			],
			primary_action_label: __("Save"),
			primary_action: function (values) {
				var settings = applyTypography(values);
				frappe.call({
					method: "construction.api.theme_api.save_user_typography_settings",
					args: settings,
					freeze: true,
					freeze_message: __("Saving typography settings..."),
					callback: function (response) {
						if (response.message) {
							frappe.boot.construction_typography = response.message;
							applyTypography(response.message);
							if (window.jQuery) {
								$(document).trigger("ct-typography-saved", [response.message]);
							}
						}
						dialog.hide();
						frappe.show_alert({
							message: __("Typography settings saved"),
							indicator: "green",
						});
					},
					error: function () {
						loadSettings(function (serverSettings) {
							applyTypography(serverSettings);
						});
					},
				});
			},
		});

		dialog.set_secondary_action_label(__("Reset"));
		dialog.set_secondary_action(function () {
			dialog.set_values(defaults);
			applyTypography(defaults);
			updatePreview(dialog);
		});

		dialog.$wrapper.on("change input", "select, input", function (event) {
			var values = dialog.get_values() || {};
			var fieldname = $(event.target).closest("[data-fieldname]").attr("data-fieldname");
			if (
				fieldname === "desk_font_family" &&
				values.desk_font_family !== lastDeskFontFamily
			) {
				componentFamilyFields.forEach(function (componentFieldname) {
					dialog.set_value(componentFieldname, "Inherit");
				});
				lastDeskFontFamily = values.desk_font_family;
				values = dialog.get_values() || values;
			}
			applyTypography(values);
			updatePreview(dialog);
		});

		dialog.show();
		updatePreview(dialog);
	}

	// ── Settings Load / Save ──

	function loadSettings(callback) {
		var fallback = normalize(
			window.ctTypographySettings || (frappe.boot && frappe.boot.construction_typography)
		);
		if (!frappe.call) {
			callback(fallback);
			return;
		}
		frappe.call({
			method: "construction.api.theme_api.get_user_typography_settings",
			callback: function (response) {
				var settings = normalize((response && response.message) || fallback);
				if (frappe.boot) frappe.boot.construction_typography = settings;
				applyTypography(settings);
				callback(settings);
			},
			error: function () {
				callback(fallback);
			},
		});
	}

	// ── UI Entry Points ──

	function patchSidebarHeaderMenu() {
		if (
			!frappe.ui ||
			!frappe.ui.SidebarHeader ||
			frappe.ui.SidebarHeader.prototype._ctTypographyPatched
		) {
			return;
		}

		var original = frappe.ui.SidebarHeader.prototype.get_display_siblings;
		if (typeof original !== "function") return;

		frappe.ui.SidebarHeader.prototype.get_display_siblings = function () {
			var items = original.apply(this, arguments) || [];
			if (
				!items.some(function (item) {
					return item.name === "typography-settings";
				})
			) {
				items.push({
					name: "typography-settings",
					label: __("Typography Settings"),
					icon: "type",
					onClick: closeOpenMenus,
				});
			}
			return items;
		};
		frappe.ui.SidebarHeader.prototype._ctTypographyPatched = true;
	}

	function injectToolbarUserItem() {
		var menu = document.querySelector("#toolbar-user .dropdown-menu");
		if (!menu || menu.querySelector("[data-ct-typography-settings]")) return;

		var item = document.createElement("a");
		item.href = "#";
		item.className = "dropdown-item";
		item.setAttribute("data-ct-typography-settings", "1");
		item.textContent = __("Typography Settings");
		item.addEventListener("click", function (event) {
			event.preventDefault();
			closeOpenMenus();
			showDialog();
		});
		menu.insertBefore(item, menu.firstChild);
	}

	function injectSidebarUserItem() {
		var userArea = document.querySelector(".body-sidebar-bottom .dropdown-navbar-user");
		if (!userArea || document.querySelector(".ct-typography-user-menu")) return;

		var item = document.createElement("a");
		item.className = "ct-typography-user-menu";
		item.href = "#";
		item.innerHTML =
			'<span class="ct-typography-icon" aria-hidden="true">Aa</span>' +
			"<span>" +
			__("Typography Settings") +
			"</span>";
		item.addEventListener("click", function (event) {
			event.preventDefault();
			event.stopPropagation();
			closeOpenMenus();
			showDialog();
		});
		userArea.insertAdjacentElement("afterend", item);
	}

	// ── Initialization ──

	function init() {
		if (typeof frappe === "undefined") return;

		var initialSettings =
			(frappe.boot && frappe.boot.construction_typography) ||
			readLocalSettings() ||
			defaults;
		applyTypography(initialSettings);
		if (frappe.call) {
			frappe.call({
				method: "construction.api.theme_api.get_user_typography_settings",
				callback: function (response) {
					if (response.message) {
						if (frappe.boot) frappe.boot.construction_typography = response.message;
						applyTypography(response.message);
					}
				},
			});
		}
		window.ctShowTypographySettings = showDialog;
		window.ctTypography = {
			assetVersion: assetVersion,
			defaults: defaults,
			fontOptions: fontOptions,
			componentFontOptions: componentFontOptions,
			deskFontOptions: deskFontOptions,
			normalize: normalize,
			apply: applyTypography,
			showDialog: showDialog,
			load: loadSettings,
		};
		patchSidebarHeaderMenu();
		injectToolbarUserItem();
		injectSidebarUserItem();

		if (window.jQuery) {
			$(document).on("toolbar_setup page-change", function () {
				patchSidebarHeaderMenu();
				injectToolbarUserItem();
				injectSidebarUserItem();
				applyTypography(
					window.ctTypographySettings || frappe.boot.construction_typography
				);
			});
		}

		[0, 250, 1000].forEach(function (delay) {
			setTimeout(function () {
				applyTypography(
					window.ctTypographySettings ||
						(frappe.boot && frappe.boot.construction_typography)
				);
			}, delay);
		});
	}

	function readLocalSettings() {
		try {
			var raw = localStorage.getItem("ct-typography-settings");
			return raw ? JSON.parse(raw) : null;
		} catch (e) {
			return null;
		}
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
