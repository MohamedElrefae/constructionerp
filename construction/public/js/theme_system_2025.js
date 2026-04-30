(function () {
	"use strict";
	function _norm(n) {
		return n ? n.toLowerCase().replace(/\s+/g, "_") : "";
	}
	var VERSION = "5.1";
	console.log(
		"%c[Modern Theme] LOADER v" + VERSION + " \u2014 20260417",
		"background:#2E7D32;color:#fff;padding:4px 8px;border-radius:4px;font-weight:bold"
	);

	var _css = document.createElement("style");
	_css.id = "construction-theme-css";
	_css.textContent =
		"" +
		'html[data-modern-theme="construction_dark"] .navbar{background:#1a3a1e!important;border-bottom:2px solid #4CAF50!important;box-shadow:0 2px 8px rgba(0,0,0,.3)!important}' +
		'html[data-modern-theme="construction_dark"] .navbar .nav-link{color:#c8e6c9!important}' +
		'html[data-modern-theme="construction_dark"] .navbar .nav-link:hover{color:#4CAF50!important;background:rgba(76,175,80,.1)!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_dark"] .navbar input[type="text"]{background:#1a3a1e!important;border-color:#2d5a32!important;color:#d4e8d5!important}' +
		'html[data-modern-theme="construction_dark"] .layout-side-section{background:#0d1f12!important;border-right:1px solid #2d5a32!important}' +
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a,html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a *,html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item .sidebar-item-label,html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-item-icon,html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-item-icon svg,html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-item-icon .icon{color:#e8f5e9!important;fill:#e8f5e9!important;stroke:#e8f5e9!important;font-size:13.5px!important}' +
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a:hover,html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a:hover *,html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item a:hover .icon{color:#fff!important;fill:#4CAF50!important;stroke:#4CAF50!important;background:rgba(76,175,80,.15)!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected a,html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected a *,html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected .icon{color:#4CAF50!important;fill:#4CAF50!important;stroke:#4CAF50!important;font-weight:600!important}' +
		'html[data-modern-theme="construction_dark"] .desk-sidebar .standard-sidebar-item.selected a{background:rgba(76,175,80,.2)!important;box-shadow:inset 3px 0 0 #4CAF50!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_dark"] .sidebar-label,html[data-modern-theme="construction_dark"] .desk-sidebar .sidebar-section-head{color:#81C784!important;font-size:.7rem!important;text-transform:uppercase!important;letter-spacing:1px!important}' +
		'html[data-modern-theme="construction_dark"] .page-head{background:#0d1f12!important;border-bottom:1px solid #2d5a32!important}' +
		'html[data-modern-theme="construction_dark"] .page-head .title-text{color:#d4e8d5!important}' +
		'html[data-modern-theme="construction_dark"] .layout-main-section{background:#111a13!important}' +
		'html[data-modern-theme="construction_dark"] .page-container{background:#111a13!important}' +
		'html[data-modern-theme="construction_dark"] .btn-primary{background:#4CAF50!important;border-color:#4CAF50!important;color:#fff!important;border-radius:10px!important}' +
		'html[data-modern-theme="construction_dark"] .btn-primary:hover{background:#66BB6A!important;border-color:#66BB6A!important;transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(76,175,80,.3)!important}' +
		'html[data-modern-theme="construction_dark"] .btn-default{background:#1a3a1e!important;border:1px solid #2d5a32!important;color:#a8d5ab!important;border-radius:10px!important}' +
		'html[data-modern-theme="construction_dark"] .btn-default:hover{background:rgba(76,175,80,.12)!important;border-color:#4CAF50!important;color:#4CAF50!important;transform:translateY(-1px)!important}' +
		'html[data-modern-theme="construction_dark"] a{color:#81C784!important}' +
		'html[data-modern-theme="construction_dark"] a:hover{color:#4CAF50!important}' +
		'html[data-modern-theme="construction_dark"] h1,html[data-modern-theme="construction_dark"] h2,html[data-modern-theme="construction_dark"] h3{color:#d4e8d5!important}' +
		'html[data-modern-theme="construction_dark"] .form-control{background:#1a3a1e!important;border-color:#2d5a32!important;color:#d4e8d5!important}' +
		'html[data-modern-theme="construction_dark"] .form-control:focus{border-color:#4CAF50!important;box-shadow:0 0 0 3px rgba(76,175,80,.15)!important}' +
		'html[data-modern-theme="construction_dark"] .dropdown-menu{background:#0d1f12!important;border-color:#2d5a32!important}' +
		'html[data-modern-theme="construction_dark"] .dropdown-item{color:#a8d5ab!important}' +
		'html[data-modern-theme="construction_dark"] .dropdown-item:hover{background:rgba(76,175,80,.12)!important;color:#4CAF50!important}' +
		'html[data-modern-theme="construction_dark"] .modal-content{background:#0d1f12!important;border-color:#2d5a32!important}' +
		'html[data-modern-theme="construction_dark"] .tree-toolbar-button{background:#1a3a1e!important;border:1px solid #2d5a32!important;color:#a8d5ab!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_dark"] .tree-toolbar-button:hover{background:rgba(76,175,80,.12)!important;border-color:#4CAF50!important;color:#4CAF50!important}' +
		'html[data-modern-theme="construction_light"] .navbar{background:#f0fdf4!important;border-bottom:2px solid #2E7D32!important}' +
		'html[data-modern-theme="construction_light"] .navbar .nav-link{color:#1e293b!important}' +
		'html[data-modern-theme="construction_light"] .navbar .nav-link:hover{color:#2E7D32!important;background:rgba(46,125,50,.08)!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_light"] .layout-side-section{background:#f0fdf4!important;border-right:2px solid #2E7D32!important}' +
		'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item a,html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item .sidebar-item-label{color:#1b5e20!important}' +
		'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item a:hover,html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item a:hover *{color:#2E7D32!important;background:rgba(46,125,50,.08)!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_light"] .desk-sidebar .standard-sidebar-item.selected a{background:rgba(46,125,50,.12)!important;color:#2E7D32!important;font-weight:600!important;box-shadow:inset 3px 0 0 #2E7D32!important;border-radius:8px!important}' +
		'html[data-modern-theme="construction_light"] .btn-primary{background:#2E7D32!important;border-color:#2E7D32!important;border-radius:10px!important}' +
		'html[data-modern-theme="construction_light"] .btn-primary:hover{background:#388E3C!important;transform:translateY(-1px)!important}' +
		'html[data-modern-theme="construction_light"] .btn-default{border:1px solid #d1e7dd!important;border-radius:10px!important}' +
		'html[data-modern-theme="construction_light"] .btn-default:hover{border-color:#2E7D32!important;color:#2E7D32!important}' +
		'html[data-modern-theme="construction_light"] a{color:#2E7D32!important}' +
		'html[data-modern-theme="construction_light"] .page-head{background:#f0fdf4!important;border-bottom:1px solid #d1e7dd!important}' +
		'html[data-modern-theme="construction_light"] .form-control:focus{border-color:#2E7D32!important;box-shadow:0 0 0 3px rgba(46,125,50,.12)!important}' +
		".modern-theme-loaded .page-head .btn-default.ellipsis,.modern-theme-loaded .page-head .inner-group-button .btn-default,.modern-theme-loaded .page-head .page-actions .btn-default{border:1px solid var(--border-color)!important;border-radius:10px!important;font-size:.8rem!important;font-weight:500!important;padding:6px 14px!important;min-height:36px!important;transition:all .25s cubic-bezier(.4,0,.2,1)!important;background:var(--surface)!important;color:var(--text-primary)!important;box-shadow:0 1px 3px rgba(0,0,0,.06)!important}" +
		".modern-theme-loaded .page-head .btn-default.ellipsis:hover,.modern-theme-loaded .page-head .inner-group-button .btn-default:hover,.modern-theme-loaded .page-head .page-actions .btn-default:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important;color:var(--accent)!important;transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(0,0,0,.1)!important}" +
		".modern-theme-loaded .tree-toolbar-button{border:1px solid var(--border-color)!important;border-radius:8px!important;font-size:.78rem!important;font-weight:500!important;padding:4px 12px!important;min-height:28px!important;transition:all .2s ease!important;background:var(--surface)!important;color:var(--text-primary)!important;margin:0 3px!important}" +
		".modern-theme-loaded .tree-toolbar-button:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important;color:var(--accent)!important;transform:translateY(-1px)!important}" +
		".modern-theme-loaded .tree-toolbar-button:last-child:hover{border-color:var(--error)!important;color:var(--error)!important;background:rgba(222,63,63,.06)!important}" +
		".modern-theme-loaded .page-head .primary-action{border-radius:10px!important}" +
		".modern-theme-loaded .page-head .primary-action:hover{transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(46,125,50,.3)!important}" +
		".modern-theme-loaded .page-head .icon-btn{border:1px solid var(--border-color)!important;border-radius:10px!important;background:var(--surface)!important}" +
		'.modern-theme-loaded .page-head .icon-btn:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important}html[data-modern-theme="construction_dark"] body,html[data-modern-theme="construction_dark"] .page-container,html[data-modern-theme="construction_dark"] .content.page-container{background:#111a13!important}html[data-modern-theme="construction_light"] body,html[data-modern-theme="construction_light"] .page-container{background:#f0fdf4!important}' +
		".modern-theme-loaded .btn-default:focus-visible,.modern-theme-loaded .tree-toolbar-button:focus-visible,.modern-theme-loaded .navbar .nav-link:focus-visible,.modern-theme-loaded .desk-sidebar-item a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}" +
		"@media(prefers-reduced-motion:reduce){.modern-theme-loaded,.modern-theme-loaded *{transition-duration:.001ms!important;animation-duration:.001ms!important}.modern-theme-loaded .btn-default:hover,.modern-theme-loaded .tree-toolbar-button:hover{transform:none!important}#theme-mode-dot{box-shadow:none!important}}";
	document.head.appendChild(_css);

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
			try {
				var saved = localStorage.getItem("construction_theme");
				if (saved && saved.indexOf("construction") === 0) {
					document.documentElement.setAttribute("data-modern-theme", saved);
					this.currentTheme = saved;
				}
			} catch (e) {}
			this.applyTheme();
			this.watchThemeChanges();
			this.injectCSSVariables();
		},
		applyTheme: function (forcedMode) {
			var self = this;
			var dom = document.documentElement.getAttribute("data-theme");
			var mode = forcedMode || dom || "light";
			frappe.call({
				method: "construction.api.theme_api.get_effective_desk_theme",
				args: { current_mode: mode },
				callback: function (r) {
					if (!r.message) return;
					var tn = r.message.theme_name,
						m = r.message.mode,
						s = r.message.source;
					if (forcedMode && m !== forcedMode) {
						m = forcedMode;
						s = "dom_override";
					} else if (mode && m !== mode) {
						m = mode;
						s = "request_override";
					}
					self.currentTheme = tn;
					self.currentMode = m;
					document.documentElement.setAttribute("data-theme", m);
					var ex = document.documentElement.getAttribute("data-modern-theme");
					if (tn !== "Standard")
						document.documentElement.setAttribute("data-modern-theme", tn);
					else if (!ex) document.documentElement.removeAttribute("data-modern-theme");
					self.updateNavbarIndicator(m);
					window.dispatchEvent(
						new CustomEvent("modern-theme-applied", {
							detail: { theme_name: tn, mode: m, source: s },
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
			if (window.matchMedia)
				window
					.matchMedia("(prefers-color-scheme: dark)")
					.addEventListener("change", function (e) {
						self.applyTheme(e.matches ? "dark" : "light");
					});
			var obs = new MutationObserver(function (muts) {
				for (var i = 0; i < muts.length; i++) {
					if (muts[i].attributeName === "data-theme") {
						var raw = document.documentElement.getAttribute("data-theme"),
							old = self.currentMode;
						if (raw === "construction_light" || raw === "construction_dark") {
							var n = raw === "construction_light" ? "light" : "dark";
							document.documentElement.setAttribute("data-modern-theme", raw);
							document.documentElement.setAttribute("data-theme", n);
							return;
						}
						if (raw && raw !== old) {
							self.persistModePreference(raw);
							self.applyTheme(raw);
						}
					}
				}
			});
			obs.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ["data-theme"],
			});
		},
		persistModePreference: function (mode) {
			frappe.call({
				method: "construction.api.theme_api.save_user_mode",
				args: { mode: mode },
				callback: function (r) {
					if (r.message && r.message.success)
						console.log("[Modern Theme] Persisted mode: " + mode);
				},
				error: function () {},
			});
		},
		injectCSSVariables: function () {
			document.body.classList.add("modern-theme-loaded");
			this.injectNavbarIndicator();
		},
		injectNavbarIndicator: function () {
			var self = this;
			var chk = setInterval(function () {
				var nav =
					document.querySelector(".navbar-nav") ||
					document.querySelector(".nav.navbar-right");
				if (nav && !document.getElementById("modern-theme-indicator")) {
					clearInterval(chk);
					var mt = document.documentElement.getAttribute("data-modern-theme");
					var isCon = mt && mt.indexOf("construction") === 0;
					var isDark = self.currentMode === "dark";
					var label = isCon
						? isDark
							? "\uD83C\uDFD7\uFE0F Construction Dark"
							: "\uD83C\uDFD7\uFE0F Construction Light"
						: isDark
						? "\uD83C\uDF19 Dark"
						: "\u2600\uFE0F Light";
					var dc = isCon ? "#4CAF50" : isDark ? "#60a5fa" : "#fbbf24";
					var li = document.createElement("li");
					li.id = "modern-theme-indicator";
					li.className = "nav-item dropdown";
					li.innerHTML =
						'<a class="nav-link" href="#" style="display:flex;align-items:center;padding:8px 12px;border-radius:20px;background:var(--hover-bg,rgba(0,0,0,.05));margin:0 8px;" onclick="return false;"><span id="theme-mode-dot" style="width:10px;height:10px;border-radius:50%;background:' +
						dc +
						";box-shadow:0 0 8px " +
						dc +
						';margin-right:8px;transition:all .3s ease;"></span><span id="theme-mode-text" style="font-size:.85rem;font-weight:500;">' +
						label +
						"</span></a>";
					var um = nav.querySelector(".dropdown-navbar-user");
					if (um) nav.insertBefore(li, um);
					else nav.appendChild(li);
					console.log("[Modern Theme] Navbar indicator injected");
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
				clearInterval(chk);
			}, 10000);
		},
		updateNavbarIndicator: function (mode) {
			var dot = document.getElementById("theme-mode-dot"),
				text = document.getElementById("theme-mode-text");
			if (!dot || !text) return;
			var mt = document.documentElement.getAttribute("data-modern-theme");
			var isCon = mt && mt.indexOf("construction") === 0,
				isDark = mode === "dark";
			var label, dc;
			if (isCon) {
				label = isDark
					? "\uD83C\uDFD7\uFE0F Construction Dark"
					: "\uD83C\uDFD7\uFE0F Construction Light";
				dc = "#4CAF50";
			} else {
				label = isDark ? "\uD83C\uDF19 Dark" : "\u2600\uFE0F Light";
				dc = isDark ? "#60a5fa" : "#fbbf24";
			}
			dot.style.background = dc;
			dot.style.boxShadow = "0 0 8px " + dc;
			text.textContent = label;
			var ann = document.getElementById("theme-change-announcer");
			if (ann) {
				ann.textContent = "";
				setTimeout(function () {
					ann.textContent = "Theme changed to " + label;
				}, 100);
			}
		},
		getCurrentTheme: function () {
			return { theme: this.currentTheme, mode: this.currentMode };
		},
		refresh: function () {
			this.applyTheme();
		},
		injectDynamicCSS: function (v) {
			if (!v) return;
			var e = document.getElementById("modern-theme-dynamic");
			if (e) e.remove();
			e = document.createElement("style");
			e.id = "modern-theme-dynamic";
			e.textContent = ":root{\n" + v + "\n}";
			document.head.appendChild(e);
		},
		fetchAndApplyCSSVariables: function (n) {
			var s = this;
			frappe.call({
				method: "construction.api.theme_api.get_theme_css_variables",
				args: { theme_name: n },
				callback: function (r) {
					if (r.message && r.message.css_variables)
						s.injectDynamicCSS(r.message.css_variables);
				},
			});
		},
	};
	window.ModernThemeLoader = ModernThemeLoader;

	if (frappe.ui && frappe.ui.ThemeSwitcher) {
		frappe.ui.ThemeSwitcher = class extends frappe.ui.ThemeSwitcher {
			fetch_themes() {
				return new Promise(
					function (res) {
						this.themes = [
							{ name: "light", label: "\u2600\uFE0F Light", info: "Frappe Light" },
							{ name: "dark", label: "\uD83C\uDF19 Dark", info: "Frappe Dark" },
							{
								name: "construction_light",
								label: "\uD83C\uDFD7\uFE0F Construction Light",
								info: "Green light",
							},
							{
								name: "construction_dark",
								label: "\uD83C\uDFD7\uFE0F Construction Dark",
								info: "Green dark",
							},
							{ name: "automatic", label: "\u26A1 Automatic", info: "System" },
						];
						res(this.themes);
					}.bind(this)
				);
			}
			switch_theme(t) {
				var m = "light";
				if (t === "dark" || t === "construction_dark") m = "dark";
				else if (t === "automatic")
					m =
						window.matchMedia &&
						window.matchMedia("(prefers-color-scheme: dark)").matches
							? "dark"
							: "light";
				if (t.indexOf("construction") === 0) {
					document.documentElement.setAttribute("data-modern-theme", t);
					ModernThemeLoader.currentTheme = t;
					frappe.call({
						method: "construction.api.theme_api.set_user_theme",
						args: { theme: t, mode: m },
						error: function () {},
					});
				} else {
					document.documentElement.removeAttribute("data-modern-theme");
					ModernThemeLoader.currentTheme = "Standard";
				}
				document.documentElement.setAttribute("data-theme", m);
				ModernThemeLoader.currentMode = m;
				ModernThemeLoader.persistModePreference(m);
				ModernThemeLoader.updateNavbarIndicator(m);
				try {
					localStorage.setItem(
						"construction_theme",
						t.indexOf("construction") === 0 ? t : ""
					);
				} catch (e) {}
				this.hide();
			}
			render() {
				try {
					super.render();
				} catch (e) {}
				setTimeout(
					function () {
						this._applyVisualIndicators();
					}.bind(this),
					150
				);
			}
			_applyVisualIndicators() {
				var ct = ModernThemeLoader.currentTheme || "Standard",
					cm = ModernThemeLoader.currentMode || "light";
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

	if (document.readyState === "loading")
		document.addEventListener("DOMContentLoaded", function () {
			ModernThemeLoader.init();
		});
	else
		setTimeout(function () {
			ModernThemeLoader.init();
		}, 0);
})();
