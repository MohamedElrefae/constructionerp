(function () {
	"use strict";

	window.ConstructionTheme = {
		currentMode: "light",
		isInternalChange: false,
		_mutationObserver: null,
		_themeObserver: null,
		_shadowRootsInjected: new WeakSet(),

		init: function () {
			const start = performance.now();
			console.log(
				`%c[ConstructionTheme] v2.1 — Namespace Architecture`,
				"color: #3b82f6; font-weight: bold;",
			);

			// v2.1: Inject ct-enterprise namespace class for Desk routes
			if (!document.documentElement.classList.contains("ct-enterprise")) {
				var path = window.location.pathname;
				if (path.startsWith("/desk") || path.startsWith("/app")) {
					document.documentElement.classList.add("ct-enterprise");
				}
			}

			try {
				var savedPreference = null;
				try {
					if (window.frappe && frappe.boot && frappe.boot.user) {
						var deskTheme = frappe.boot.user.desk_theme || "";
						if (deskTheme === "Dark" || deskTheme === "construction_dark") {
							savedPreference = "dark";
						} else if (deskTheme === "Light" || deskTheme === "construction_light") {
							savedPreference = "light";
						}
					}
				} catch (e) { /* ignore */ }

				try {
					var stored = sessionStorage.getItem("construction_theme_mode");
					if (!savedPreference && stored) {
						savedPreference = stored === "dark" ? "dark" : "light";
					}
				} catch (e) { /* ignore */ }

				let initialMode =
					savedPreference ||
					document.documentElement.getAttribute("data-theme") ||
					"light";

				console.log("[ConstructionTheme] Initial mode resolved:", initialMode);

				if (savedPreference === "dark") {
					document.documentElement.setAttribute("data-theme", "dark");
					initialMode = "dark";
					this.updateNavbarLabel("dark");
				}

				const config =
					(window.frappe && frappe.boot && frappe.boot.construction_theme) || {};
				this.currentMode = initialMode;

				document.documentElement.setAttribute("data-theme", initialMode);

				this.setupThemeObserver();
				this.setupMutationObserver();

				this.renderNavbarDropdown(initialMode);
				this.hideFrappeBranding(config);
				this.swapLogo(config.logo_url);

				this.colorTreeToolbarButtons();
				setTimeout(() => this.colorTreeToolbarButtons(), 1000);
				setTimeout(() => this.colorTreeToolbarButtons(), 3000);

				this.removeGhostButtons();

				const end = performance.now();
				console.log(
					`[ConstructionTheme] Initialized in ${initialMode} mode. Boot time: ${(end - start).toFixed(2)}ms`,
				);
			} catch (err) {
				console.error("[ConstructionTheme] Initialization failed", err);
			}
		},

		setupThemeObserver: function () {
			if (this._themeObserver) return;

			this._themeObserver = new MutationObserver((mutations) => {
				if (this.isInternalChange) return;

				mutations.forEach((mutation) => {
					if (mutation.attributeName === "data-theme") {
						const newMode = document.documentElement.getAttribute("data-theme");
						if (newMode && newMode !== this.currentMode) {
							console.log(
								"[ConstructionTheme] External sync triggered for:",
								newMode,
							);
							this.currentMode = newMode;
							this.updateNavbarLabel(newMode);
						}
					}
				});
			});
			this._themeObserver.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ["data-theme"],
			});
		},

		disconnectObservers: function () {
			if (this._mutationObserver) {
				this._mutationObserver.disconnect();
				this._mutationObserver = null;
			}
			if (this._themeObserver) {
				this._themeObserver.disconnect();
				this._themeObserver = null;
			}
			console.log("[ConstructionTheme] All observers disconnected");
		},

		setupMutationObserver: function () {
			if (this._mutationObserver) return;

			this._mutationObserver = new MutationObserver((mutations) => {
				let newShadowRoots = [];
				let needsTreeButtonColor = false;

				mutations.forEach((mutation) => {
					mutation.addedNodes.forEach((node) => {
						if (node.nodeType !== 1) return;

						if (node.shadowRoot && !this._shadowRootsInjected.has(node.shadowRoot)) {
							newShadowRoots.push(node.shadowRoot);
						}
						if (node.querySelectorAll) {
							node.querySelectorAll("*").forEach((el) => {
								if (
									el.shadowRoot &&
									!this._shadowRootsInjected.has(el.shadowRoot)
								) {
									newShadowRoots.push(el.shadowRoot);
								}
							});
						}

						if (node.classList && node.classList.contains("tree-node-toolbar")) {
							needsTreeButtonColor = true;
						}
						if (node.querySelectorAll) {
							if (node.querySelector(".tree-node-toolbar")) {
								needsTreeButtonColor = true;
							}
						}
					});
				});

				if (newShadowRoots.length > 0) {
					needsTreeButtonColor = true;
				}

				if (needsTreeButtonColor) {
					this.colorTreeToolbarButtons();
				}

				this.removeGhostButtons();
			});

			this._mutationObserver.observe(document.body, { childList: true, subtree: true });
		},

		hideFrappeBranding: function (config) {
			if (typeof $ === "undefined" || !window.jQuery) {
				return;
			}

			const hideBranding = () => {
				try {
					// Hide Frappe branding links inside help dropdown
					$('.dropdown-help [href*="frappe.io"]').closest("li").hide();
					$('.dropdown-help [href*="github.com/frappe"]').closest("li").hide();

					// Hide powered-by footer
					$(".web-footer-powered-by, .footer-powered").hide();

					if (config.app_title) {
						$(".navbar-brand-title").text(config.app_title);
					}

					// v16: Ensure chat/help/notification widgets remain visible
					// Our CSS must not accidentally hide these
					$(
						".navbar-notifications, .navbar-help, .chat-dropdown, .dropdown-notifications, .dropdown-help",
					).show();
					$(".navbar-right .dropdown, .desktop-navbar .dropdown").show();
				} catch (e) {
					console.warn("[ConstructionTheme] Error in branding/showing widgets:", e);
				}
			};

			hideBranding();
			setTimeout(hideBranding, 2000);
			setTimeout(hideBranding, 5000);
		},

		swapLogo: function (logoUrl) {
			if (!logoUrl) return;
			const logo = document.querySelector(".navbar-brand img, .app-logo img");
			if (logo) {
				logo.src = logoUrl;
			}
		},

		persist: function (mode) {
			if (window.frappe && frappe.call) {
				var self = this;
				frappe.call({
					method: "construction.api.theme_api.save_user_mode",
					args: { mode: mode },
					callback: function () {
						self.isInternalChange = false;
					},
					error: function () {
						self.isInternalChange = false;
					},
				});
			} else {
				this.isInternalChange = false;
			}
		},

		renderNavbarDropdown: function (mode) {
			if (document.getElementById("construction-theme-dropdown")) {
				this.updateNavbarLabel(mode);
				return;
			}

			if (this._navbarDropdownPending) return;
			this._navbarDropdownPending = true;

			// v15: .navbar-nav, v16: .navbar-right, .desktop-navbar .navbar-nav
			const navbar =
				document.querySelector(".navbar-nav") ||
				document.querySelector(".navbar .navbar-collapse .navbar-nav") ||
				document.querySelector(".navbar .container .navbar-nav") ||
				document.querySelector(".desktop-navbar .navbar-right") ||
				document.querySelector(".navbar-container .navbar-right") ||
				document.querySelector(".desktop-navbar .navbar-nav") ||
				document.querySelector(".navbar-right");
			if (!navbar) {
				setTimeout(() => {
					this._navbarDropdownPending = false;
					this.renderNavbarDropdown(mode);
				}, 500);
				return;
			}

			if (document.getElementById("construction-theme-dropdown")) {
				this._navbarDropdownPending = false;
				this.updateNavbarLabel(mode);
				return;
			}

			const li = document.createElement("li");
			li.id = "construction-theme-dropdown";
			li.className = "nav-item dropdown dropdown-notifications";
			li.innerHTML = `
                <a class="nav-link" href="#" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" style="padding-top: 12px; cursor: pointer;">
                   <span class="theme-label">${mode === "dark" ? "🏗️ Construction Dark" : "☀️ Construction Light"}</span>
                </a>
                <div class="dropdown-menu dropdown-menu-right">
                    <a class="dropdown-item" href="#" onclick="ConstructionTheme.setMode('light'); return false;">☀️ Construction Light</a>
                    <a class="dropdown-item" href="#" onclick="ConstructionTheme.setMode('dark'); return false;">🏗️ Construction Dark</a>
                </div>
            `;
			navbar.prepend(li);

			// v16: Bootstrap dropdown requires data-bs-toggle
			const toggle = li.querySelector(".nav-link");
			if (toggle && window.bootstrap && window.bootstrap.Dropdown) {
				new window.bootstrap.Dropdown(toggle);
			}

			this._navbarDropdownPending = false;
			console.log("[ConstructionTheme] Navbar dropdown rendered");
		},

		updateNavbarLabel: function (mode) {
			const label = document.querySelector("#construction-theme-dropdown .theme-label");
			if (label) {
				label.textContent =
					mode === "dark"
						? "\uD83C\uDFD7\uFE0F Construction Dark"
						: "\u2600\uFE0F Construction Light";
			}
		},

		setMode: function (mode) {
			if (this.isInternalChange) return;
			this.isInternalChange = true;
			this.currentMode = mode;
			document.documentElement.setAttribute("data-theme", mode);
			try {
				sessionStorage.setItem("construction_theme_mode", mode);
			} catch (e) { /* ignore */ }
			this.updateNavbarLabel(mode);
			this.persist(mode);
		},

		colorTreeToolbarButtons: function () {
			document
				.querySelectorAll(".tree-node-actions .btn, .tree-actions .btn")
				.forEach(function (btn) {
					btn.style.color = "var(--text-2)";
					btn.style.background = "transparent";
					btn.style.border = "none";
				});
		},

		removeGhostButtons: function () {
			document
				.querySelectorAll(".modern-sidebar, .theme-sidebar, .duplicate-sidebar")
				.forEach(function (el) {
					el.style.display = "none";
				});
		},
	};

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", () => window.ConstructionTheme.init());
	} else {
		window.ConstructionTheme.init();
	}

	window.addEventListener("beforeunload", () => {
		if (window.ConstructionTheme) {
			window.ConstructionTheme.disconnectObservers();
		}
	});
})();
