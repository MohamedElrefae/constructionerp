/* eslint-disable */
/**
 * Construction Theme v5.15 — Isolated Zone Placement
 * Desk: <ul.ct-topbar-zone.ct-zone--desk> appended to .desktop-navbar
 * Standard: <div.ct-topbar-zone.ct-topbar-zone--standard> absolute in .page-head
 * No injection into Frappe containers, no evacuation, no retries.
 */

(function () {
	"use strict";

	var html = document.documentElement;
	var path = window.location.pathname;

	if (
		path.startsWith("/desk") ||
		path.startsWith("/app") ||
		path.startsWith("/login") ||
		path.startsWith("/reset_password")
	) {
		if (!html.classList.contains("ct-enterprise")) {
			html.classList.add("ct-enterprise");
		}

		var savedMode = localStorage.getItem("ct-theme-mode");
		if (savedMode === "light") {
			html.setAttribute("data-theme", "light");
		} else if (savedMode === "dark") {
			html.setAttribute("data-theme", "dark");
		} else {
			html.setAttribute("data-theme", "dark");
			localStorage.setItem("ct-theme-mode", "dark");
		}
	}

	function setMode(mode) {
		html.setAttribute("data-theme", mode);
		localStorage.setItem("ct-theme-mode", mode);
		window.dispatchEvent(new CustomEvent("ct-theme-change", { detail: { theme: mode } }));
	}
	window.ctSetMode = setMode;

	function themeLabel(mode) {
		return mode === "dark"
			? "\uD83C\uDFD7\uFE0F Construction Dark"
			: "\u2600\uFE0F Construction Light";
	}

	// ============================================================
	// TopbarManager v5.15 — Isolated Zones (no Frappe container injection)
	// Zone elements persist across navigations:
	//   Desk: <ul.ct-topbar-zone.ct-zone--desk> in .desktop-navbar
	//   Standard: <div.ct-topbar-zone.ct-topbar-zone--standard> in .page-head
	// ============================================================
	function initManager() {
		class ConstructionTopbarManager {
			constructor() {
				this.registry = [];
				this._injected = new Map();
				this._renderTimeout = null;
				this._enabled = true;
				this._needsRender = false;
				this._isRendering = false;
				this._initialized = false;
				this._isDesk = false;

				this._detectContext();
				this._init();
			}

			enable() {
				if (this._enabled) return;
				this._enabled = true;
				this._scheduleRender();
			}

			disable() {
				if (!this._enabled) return;
				this._enabled = false;
				clearTimeout(this._renderTimeout);
			}

			destroy() {
				this.disable();
				try {
					$(document).off(".ct");
				} catch (e) {}
				this._injected.forEach(
					function (data, id) {
						if (data.element && data.element.isConnected) {
							var item = this.registry.find(function (r) {
								return r.id === id;
							});
							if (item && item.teardown && data.element) item.teardown(data.element);
							data.element.remove();
						}
					}.bind(this)
				);
				this._injected.clear();
				this.registry = [];
				if (window.ctTopbar === this) window.ctTopbar = null;
			}

			register(config) {
				var existing = this.registry.find(function (r) {
					return r.id === config.id;
				});
				if (existing) {
					var needsRebuild = existing.render !== config.render;
					if (needsRebuild && existing.teardown) {
						var injected = this._injected.get(config.id);
						if (injected && injected.element) existing.teardown(injected.element);
					}
					for (var k in config) {
						if (config.hasOwnProperty(k)) existing[k] = config[k];
					}
					if (needsRebuild) {
						var injected = this._injected.get(config.id);
						if (injected && injected.element) {
							injected.element.remove();
							this._injected.delete(config.id);
						}
					}
				} else {
					this.registry.push(config);
					this.registry.sort(function (a, b) {
						return (a.order || 0) - (b.order || 0);
					});
				}
				this._scheduleRender();
			}

			unregister(id) {
				var item = this.registry.find(function (r) {
					return r.id === id;
				});
				var injected = this._injected.get(id);
				if (item && item.teardown && injected && injected.element) {
					item.teardown(injected.element);
				}
				this.registry = this.registry.filter(function (r) {
					return r.id !== id;
				});
				if (injected && injected.element && injected.element.isConnected)
					injected.element.remove();
				this._injected.delete(id);
				this._scheduleRender();
			}

			_detectContext() {
				this._isDesk = false;
				try {
					var route = frappe.get_route
						? frappe.get_route()
						: frappe.router
						? frappe.router.current_route
						: null;
					if (route && route.length > 0) {
						this._isDesk =
							route[0] === "Workspaces" || route[0] === "" || route[0] === "desk";
						return;
					}
					var deskNav = document.querySelector(".desktop-navbar");
					if (deskNav && deskNav.offsetParent !== null) {
						this._isDesk = true;
					}
				} catch (e) {}
			}

			_init() {
				if (this._initialized) return;
				this._initialized = true;

				try {
					$(document).on(
						"toolbar_setup.ct",
						function () {
							this._scheduleRender();
						}.bind(this)
					);

					$(document).on(
						"desktop_screen.ct",
						function () {
							this._detectContext();
							this._scheduleRender();
						}.bind(this)
					);

					$(document).on(
						"page-change.ct",
						function () {
							setTimeout(
								function () {
									this._scheduleRender();
								}.bind(this),
								0
							);
						}.bind(this)
					);
				} catch (e) {}

				this._scheduleRender();
			}

			_scheduleRender() {
				if (!this._enabled) return;
				this._needsRender = true;
				clearTimeout(this._renderTimeout);
				this._renderTimeout = setTimeout(
					function () {
						if (this._needsRender && !this._isRendering) {
							this._needsRender = false;
							this.render();
						}
					}.bind(this),
					50
				);
			}

			render() {
				if (!this._enabled) return;
				try {
					if (!frappe.session || !frappe.session.user) return;
				} catch (e) {
					return;
				}
				if (document.body.classList.contains("login-content")) return;

				this._isRendering = true;
				try {
					var target = this._getTarget();
					if (!target) return;

					var isNavZone = target.tagName === "UL";
					var tagName = isNavZone ? "li" : "div";

					this.registry.forEach(
						function (item) {
							try {
								var injected = this._injected.get(item.id);

								if (injected && injected.element && injected.element.isConnected) {
									if (!target.contains(injected.element)) {
										target.appendChild(injected.element);
									}
									return;
								}

								var el = document.createElement(tagName);
								el.className = "ct-topbar-item";
								el.setAttribute("data-ct-topbar", item.id);
								el.innerHTML = item.render();
								target.appendChild(el);

								if (item.setup) item.setup(el);
								this._injected.set(item.id, { element: el });
							} catch (e) {
								console.warn("[CT] render item error:", e);
							}
						}.bind(this)
					);
				} finally {
					this._isRendering = false;
				}
			}

			_getTarget() {
				this._detectContext();

				if (this._isDesk) {
					var deskNav = document.querySelector(".desktop-navbar");
					if (deskNav) {
						var existing = deskNav.querySelector(".ct-topbar-zone");
						if (existing) return existing;

						var zone = document.createElement("ul");
						zone.className = "ct-topbar-zone ct-zone--desk";
						zone.style.cssText =
							"display:flex;align-items:center;list-style:none;height:100%;flex-shrink:0;margin-left:auto;padding:0 4px 0 12px;";
						deskNav.appendChild(zone);
						return zone;
					}
				}

				this._isDesk = false;

				var pageHead = this._findVisible(".page-head");
				if (pageHead) {
					var existing = pageHead.querySelector(".ct-topbar-zone--standard");
					if (existing) return existing;

					var zone = document.createElement("div");
					zone.className = "ct-topbar-zone ct-topbar-zone--standard";
					zone.style.cssText =
						"display:flex;align-items:center;margin-left:auto;flex-shrink:0;gap:4px;padding:0 4px;";

					pageHead.appendChild(zone);
					return zone;
				}

				var pageActions = this._findVisible(".page-actions");
				if (pageActions) {
					var existing = pageActions.querySelector(".ct-topbar-zone--actions");
					if (existing) return existing;

					var zone = document.createElement("div");
					zone.className = "ct-topbar-zone ct-topbar-zone--actions";
					zone.style.cssText =
						"display:inline-flex;align-items:center;margin-right:8px;gap:4px;";
					pageActions.insertBefore(zone, pageActions.firstChild);
					return zone;
				}

				return this._getHeader();
			}

			_findVisible(selector) {
				var all = document.querySelectorAll(selector);
				for (var i = 0; i < all.length; i++) {
					if (all[i].offsetParent !== null) {
						return all[i];
					}
				}
				return null;
			}

			_getHeader() {
				var header = document.querySelector("header");
				if (!header) {
					header = document.createElement("header");
					document.body.insertBefore(header, document.body.firstChild);
				}
				return header;
			}
		}

		window.ctTopbar = new ConstructionTopbarManager();

		window.ctTopbar.register({
			id: "theme-switcher",
			order: 10,
			render: function () {
				var mode = html.getAttribute("data-theme") || "dark";
				return (
					'<div class="dropdown ct-theme-wrapper" id="ct-theme-toggle">' +
					'<button class="btn-reset nav-link text-muted dropdown-toggle ct-theme-btn" ' +
					'type="button" aria-haspopup="true" aria-expanded="false">' +
					'<span id="ct-theme-label">' +
					themeLabel(mode) +
					"</span></button>" +
					'<div class="dropdown-menu dropdown-menu-right">' +
					'<a class="dropdown-item" href="#" data-ct-mode="dark">\uD83C\uDFD7\uFE0F Construction Dark</a>' +
					'<a class="dropdown-item" href="#" data-ct-mode="light">\u2600\uFE0F Construction Light</a>' +
					"</div></div>"
				);
			},
			setup: function (element) {
				var btn = element.querySelector(".ct-theme-btn");
				var menu = element.querySelector(".dropdown-menu");
				if (!btn || !menu) return;

				btn.addEventListener("click", function (e) {
					e.preventDefault();
					e.stopPropagation();

					var isOpen = menu.classList.contains("show");
					document.querySelectorAll(".dropdown-menu.show").forEach(function (m) {
						m.classList.remove("show");
						var b = m.closest(".dropdown")
							? m.closest(".dropdown").querySelector("[aria-expanded]")
							: null;
						if (b) b.setAttribute("aria-expanded", "false");
					});
					if (!isOpen) {
						menu.classList.add("show");
						btn.setAttribute("aria-expanded", "true");
						var rect = btn.getBoundingClientRect();
						menu.style.position = "fixed";
						menu.style.top = rect.bottom + 4 + "px";
						menu.style.right = window.innerWidth - rect.right + "px";
						menu.style.left = "auto";
						menu.style.bottom = "auto";
						menu.style.transform = "none";
					}
				});

				menu.querySelectorAll(".dropdown-item").forEach(function (item) {
					item.addEventListener("click", function (e) {
						e.preventDefault();
						e.stopPropagation();
						var mode = item.getAttribute("data-ct-mode");
						if (mode) ctSetMode(mode);
						menu.classList.remove("show");
						btn.setAttribute("aria-expanded", "false");
					});
				});

				var outsideClick = function (e) {
					if (!element.contains(e.target)) {
						menu.classList.remove("show");
						btn.setAttribute("aria-expanded", "false");
					}
				};
				element._ctOutsideClick = outsideClick;
				document.addEventListener("click", outsideClick);

				var handler = function (e) {
					var label = element.querySelector("#ct-theme-label");
					if (label) {
						label.textContent = themeLabel(
							e.detail ? e.detail.theme : html.getAttribute("data-theme") || "dark"
						);
					}
				};
				element._ctThemeHandler = handler;
				window.addEventListener("ct-theme-change", handler);
			},
			teardown: function (element) {
				if (element._ctThemeHandler) {
					window.removeEventListener("ct-theme-change", element._ctThemeHandler);
					element._ctThemeHandler = null;
				}
				if (element._ctOutsideClick) {
					document.removeEventListener("click", element._ctOutsideClick);
					element._ctOutsideClick = null;
				}
			},
		});
	}

	if (typeof frappe !== "undefined" && typeof jQuery !== "undefined") {
		initManager();
	} else {
		var readyStateCheck = setInterval(function () {
			if (typeof frappe !== "undefined" && typeof jQuery !== "undefined") {
				clearInterval(readyStateCheck);
				initManager();
			}
		}, 200);
		setTimeout(function () {
			clearInterval(readyStateCheck);
		}, 10000);
	}

	// ============================================================
	// Legacy Features
	// ============================================================

	function removeGhostButtons() {
		var ghosts = document.querySelectorAll(".btn.ghost-btn, .ghost-btn");
		ghosts.forEach(function (btn) {
			btn.style.display = "none";
		});
	}

	function hideFrappeBranding() {
		var powered = document.querySelector(".footer-powered");
		if (powered) powered.style.display = "none";
	}

	function getThemeColors() {
		var cs = getComputedStyle(document.documentElement);
		return {
			primary: cs.getPropertyValue("--ct-primary").trim() || "#2563eb",
			primaryHover: cs.getPropertyValue("--ct-primary-hover").trim() || "#1d4ed8",
			success: cs.getPropertyValue("--ct-success").trim() || "#16a34a",
			successHover: cs.getPropertyValue("--ct-success-hover").trim() || "#15803d",
			danger: cs.getPropertyValue("--ct-danger").trim() || "#dc2626",
			dangerHover: cs.getPropertyValue("--ct-danger-hover").trim() || "#b91c1c",
			warning: cs.getPropertyValue("--ct-warning").trim() || "#d97706",
			surface: cs.getPropertyValue("--ct-surface").trim() || "#1e293b",
			textSecondary: cs.getPropertyValue("--ct-text-secondary").trim() || "#94a3b8",
			border: cs.getPropertyValue("--ct-border").trim() || "rgba(148,163,184,0.18)",
			textDisabled: cs.getPropertyValue("--ct-text-disabled").trim() || "#475569",
			textMuted: cs.getPropertyValue("--ct-text-muted").trim() || "#64748b",
		};
	}

	function applyButtonStyle(btn, type, colors) {
		var bg, color, border, hoverBg, hoverColor, hoverBorder;
		switch (type) {
			case "edit":
				bg = colors.primary;
				color = "#fff";
				border = "transparent";
				hoverBg = colors.primaryHover;
				hoverColor = "#fff";
				hoverBorder = hoverBg;
				break;
			case "add":
				bg = colors.success;
				color = "#fff";
				border = "transparent";
				hoverBg = colors.successHover;
				hoverColor = "#fff";
				hoverBorder = hoverBg;
				break;
			case "delete":
				bg = colors.danger;
				color = "#fff";
				border = "transparent";
				hoverBg = colors.dangerHover;
				hoverColor = "#fff";
				hoverBorder = hoverBg;
				break;
			case "toggle":
				bg = colors.warning;
				color = "#fff";
				border = "transparent";
				hoverBg = bg;
				hoverColor = "#fff";
				hoverBorder = border;
				break;
			case "view":
			default:
				bg = colors.surface;
				color = colors.textSecondary;
				border = colors.border;
				hoverBg = colors.primary;
				hoverColor = "#fff";
				hoverBorder = hoverBg;
				break;
		}

		var s = btn.style;
		s.setProperty("background", bg, "important");
		s.setProperty("color", color, "important");
		s.setProperty("border", "1px solid " + border, "important");
		s.setProperty("border-radius", "6px", "important");
		s.setProperty("height", "28px", "important");
		s.setProperty("padding", "0 10px", "important");
		s.setProperty("font-size", "11px", "important");
		s.setProperty("font-weight", "600", "important");
		s.setProperty("white-space", "nowrap", "important");
		s.setProperty("cursor", "pointer", "important");
		s.setProperty("transition", "all 0.2s ease", "important");
		s.setProperty("outline", "none", "important");
		s.setProperty("box-shadow", "none", "important");
		s.setProperty("display", "inline-flex", "important");
		s.setProperty("align-items", "center", "important");
		s.setProperty("justify-content", "center", "important");
		s.setProperty("gap", "4px", "important");
		s.setProperty("line-height", "1", "important");
		s.setProperty("text-decoration", "none", "important");

		btn._ctHover = { bg: hoverBg, color: hoverColor, border: hoverBorder };
		btn._ctRest = { bg: bg, color: color, border: border };

		btn.onmouseenter = function () {
			if (this._ctHover) {
				this.style.setProperty("background", this._ctHover.bg, "important");
				this.style.setProperty("color", this._ctHover.color, "important");
				this.style.setProperty("border-color", this._ctHover.border, "important");
				this.style.setProperty("transform", "translateY(-1px)", "important");
			}
		};
		btn.onmouseleave = function () {
			if (this._ctRest) {
				this.style.setProperty("background", this._ctRest.bg, "important");
				this.style.setProperty("color", this._ctRest.color, "important");
				this.style.setProperty("border-color", this._ctRest.border, "important");
				this.style.setProperty("transform", "translateY(0)", "important");
			}
		};
	}

	function colorTreeToolbarButtons() {
		var colors = getThemeColors();
		var toolbars = document.querySelectorAll(".tree-node-toolbar");
		toolbars.forEach(function (toolbar) {
			var buttons = toolbar.querySelectorAll(".tree-toolbar-button");
			buttons.forEach(function (btn) {
				if (btn.dataset.ctThemed) return;

				var raw = btn.textContent || btn.innerText || "";
				var text = raw
					.replace(/<[^>]*>/g, "")
					.trim()
					.toLowerCase()
					.replace(/\s+/g, " ");

				var type = null;
				if (!text) {
					if (
						btn.querySelector(
							'.icon-book-open, [class*="book"], [class*="ledger"], svg[data-icon-type*="ledger"]'
						)
					) {
						type = "view";
					}
				} else if (
					text === "edit" ||
					text === "details" ||
					text === "renommer" ||
					text === "modifier"
				) {
					type = "edit";
				} else if (
					text === "add child" ||
					text === "add" ||
					text === "ajouter" ||
					text === "ajouter un enfant"
				) {
					type = "add";
				} else if (text === "delete" || text === "supprimer") {
					type = "delete";
				} else if (text === "toggle" || text === "basculer") {
					type = "toggle";
				} else if (
					text.indexOf("view ledger") !== -1 ||
					text.indexOf("view") !== -1 ||
					text.indexOf("ledger") !== -1 ||
					text.indexOf("voir") !== -1 ||
					text.indexOf("rapport") !== -1
				) {
					type = "view";
				} else if (text === "rename" || text === "renommer") {
					type = "edit";
				}

				if (type) {
					btn.dataset.ctThemed = type;
					btn.classList.add("btn-colored", "btn-" + type);
					applyButtonStyle(btn, type, colors);
				}
			});

			var treeNode = toolbar.closest(".tree-node");
			if (!treeNode) return;

			var treeLink = treeNode.querySelector(":scope > .tree-link");
			var hasExpandIcon = treeLink && treeLink.querySelector(".node-parent") !== null;

			var deleteBtn = toolbar.querySelector(".tree-toolbar-button.btn-delete");
			if (deleteBtn) {
				var existingWrap = deleteBtn.closest(".dtw");
				if (existingWrap) {
					var tip = existingWrap.querySelector(".dtip");
					if (tip) tip.remove();
					deleteBtn.classList.remove("btn-disabled");
					deleteBtn.removeAttribute("disabled");
					deleteBtn.style.setProperty("opacity", "1", "important");
					deleteBtn.style.setProperty("cursor", "pointer", "important");
					deleteBtn.onmouseenter = function () {
						if (this._ctHover) {
							this.style.setProperty("background", this._ctHover.bg, "important");
							this.style.setProperty("color", this._ctHover.color, "important");
							this.style.setProperty(
								"border-color",
								this._ctHover.border,
								"important"
							);
						}
						this.style.setProperty("transform", "translateY(-1px)", "important");
					};
					deleteBtn.onmouseleave = function () {
						if (this._ctRest) {
							this.style.setProperty("background", this._ctRest.bg, "important");
							this.style.setProperty("color", this._ctRest.color, "important");
							this.style.setProperty(
								"border-color",
								this._ctRest.border,
								"important"
							);
						}
						this.style.setProperty("transform", "translateY(0)", "important");
					};
					existingWrap.replaceWith(deleteBtn);
				}

				if (hasExpandIcon) {
					deleteBtn.classList.add("btn-disabled");
					deleteBtn.setAttribute("disabled", "disabled");
					deleteBtn.style.setProperty("opacity", "0.5", "important");
					deleteBtn.style.setProperty("cursor", "not-allowed", "important");
					deleteBtn.style.setProperty("background", colors.textDisabled, "important");
					deleteBtn.style.setProperty("color", colors.textMuted, "important");
					deleteBtn.onmouseenter = null;
					deleteBtn.onmouseleave = null;
					deleteBtn._ctHover = null;
					deleteBtn._ctRest = null;
					deleteBtn.style.setProperty("transform", "none", "important");

					var wrap = document.createElement("span");
					wrap.className = "dtw";
					wrap.style.position = "relative";
					wrap.style.display = "inline-block";
					deleteBtn.parentNode.insertBefore(wrap, deleteBtn);
					wrap.appendChild(deleteBtn);

					var tip = document.createElement("span");
					tip.className = "dtip";
					tip.textContent = "Has sub-accounts";
					tip.style.cssText =
						"visibility:hidden;opacity:0;position:absolute;bottom:120%;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.92);color:#fff;padding:6px 12px;border-radius:6px;font-size:0.75rem;white-space:nowrap;transition:all 0.2s ease;z-index:100;pointer-events:none;";
					wrap.appendChild(tip);

					wrap.onmouseenter = function () {
						var t = this.querySelector(".dtip");
						if (t) {
							t.style.visibility = "visible";
							t.style.opacity = "1";
						}
					};
					wrap.onmouseleave = function () {
						var t = this.querySelector(".dtip");
						if (t) {
							t.style.visibility = "hidden";
							t.style.opacity = "0";
						}
					};
				}
			}
		});
	}

	setInterval(colorTreeToolbarButtons, 500);

	function syncSidebarActive() {
		var currentPath = window.location.pathname.replace(/\/$/, "");
		var allItems = document.querySelectorAll(".standard-sidebar-item");
		allItems.forEach(function (item) {
			item.classList.remove("active-sidebar", "active");
		});
		allItems.forEach(function (item) {
			var anchor = item.querySelector(".item-anchor[href]");
			if (!anchor) return;
			var href = anchor.getAttribute("href");
			if (!href) return;
			href = href.split("?")[0].split("#")[0].replace(/\/$/, "");
			if (currentPath === href || currentPath.startsWith(href + "/")) {
				item.classList.add("active-sidebar");
			}
		});
	}

	function installChartGuard() {
		if (typeof frappe === "undefined") return;

		if (frappe.utils && frappe.utils.make_chart) {
			var _origMC = frappe.utils.make_chart;
			frappe.utils.make_chart = function (parent, opts) {
				if (opts && opts.colors && Array.isArray(opts.colors)) {
					opts.colors = opts.colors.filter(function (c) {
						return c !== null && c !== undefined && c !== "" && !Array.isArray(c);
					});
				}
				return _origMC.call(this, parent, opts);
			};
		}

		if (frappe.Chart && frappe.Chart.prototype) {
			var _origConf = frappe.Chart.prototype.configure;
			if (_origConf) {
				frappe.Chart.prototype.configure = function () {
					if (
						this.options &&
						this.options.colors &&
						Array.isArray(this.options.colors)
					) {
						this.options.colors = this.options.colors.filter(function (c) {
							return c !== null && c !== undefined && c !== "" && !Array.isArray(c);
						});
					}
					_origConf.apply(this, arguments);
				};
			}
		}

		if (window.ResizeObserver && !window._ctROGuarded) {
			var _OrigRO = window.ResizeObserver;
			window.ResizeObserver = function (fn) {
				var safe = function (entries, obs) {
					try {
						fn(entries, obs);
					} catch (e) {
						console.warn("[CT] ResizeObserver error intercepted:", e);
					}
				};
				return new _OrigRO(safe);
			};
			window.ResizeObserver.prototype = _OrigRO.prototype;
			window._ctROGuarded = true;
		}
	}

	document.addEventListener("DOMContentLoaded", function () {
		removeGhostButtons();
		hideFrappeBranding();
		colorTreeToolbarButtons();
		syncSidebarActive();

		setTimeout(installChartGuard, 300);
		setTimeout(installChartGuard, 1000);

		console.log(
			"[ConstructionTheme] v5.15 initialized — mode: " +
				(html.getAttribute("data-theme") || "dark")
		);
	});

	function patchRouteWatch() {
		if (typeof frappe !== "undefined" && frappe.router) {
			frappe.router.on("change", function () {
				setTimeout(installChartGuard, 300);
				setTimeout(syncSidebarActive, 200);
			});
			return true;
		}
		return false;
	}

	if (!patchRouteWatch()) {
		setTimeout(function check() {
			if (!patchRouteWatch()) setTimeout(check, 1000);
		}, 1000);
	}

	window.ctToggleMode = function () {
		var current = html.getAttribute("data-theme") || "dark";
		setMode(current === "dark" ? "light" : "dark");
	};

	if (typeof jQuery !== "undefined") {
		try {
			$(document).on("page-change", function () {
				setTimeout(syncSidebarActive, 200);
			});
		} catch (e) {}
	}

	// ════════════════════════════════════════════════════════════
	// FILTER FIX — Inline style enforcement for filter controls
	// Injected here (not in a separate file) because the separate
	// filter_fix.js was not being loaded by the server.
	//
	// Frappe v16 applies desk.bundle.css AFTER app_include_css.
	// CSS !important cannot beat inline styles from Frappe's JS.
	// Solution: JS-level style.setProperty(..., 'important')
	// ════════════════════════════════════════════════════════════

	(function fixFilters() {
		var FIX_ID = "ct-filter-fix-" + Math.random().toString(36).slice(2, 8);
		var ran = false;

		function inject() {
			if (ran) return;
			ran = true;

			// Read computed CSS variables from theme
			var cs = getComputedStyle(html);
			var bg = cs.getPropertyValue("--ct-bg-elevated").trim() || "#111827";
			var txt = cs.getPropertyValue("--ct-text").trim() || "#f8fafc";
			var txt2 = cs.getPropertyValue("--ct-text-secondary").trim() || "#94a3b8";
			var brd = cs.getPropertyValue("--ct-border").trim() || "rgba(148,163,184,0.18)";
			var pri = cs.getPropertyValue("--ct-primary").trim() || "#2563eb";

			// Wrappers → transparent
			document
				.querySelectorAll(
					".page-form .frappe-control, .page-form .control-input, .page-form .link-field, .page-form .filter-field"
				)
				.forEach(function (el) {
					el.style.setProperty("background", "transparent", "important");
					el.style.setProperty("background-color", "transparent", "important");
					el.style.setProperty("border", "none", "important");
				});

			// Inputs → unified style with left accent
			document
				.querySelectorAll(
					".page-form select, .page-form input.form-control, .page-form .link-field input"
				)
				.forEach(function (el) {
					el.style.setProperty("height", "28px", "important");
					el.style.setProperty("background-color", bg, "important");
					el.style.setProperty("color", txt, "important");
					el.style.setProperty("border", "1px solid " + brd, "important");
					el.style.setProperty("border-left", "3px solid " + pri, "important");
					el.style.setProperty("border-radius", "6px", "important");
					el.style.setProperty("font-size", "0.8125rem", "important");
					el.style.setProperty("box-shadow", "none", "important");
					el.style.setProperty("outline", "none", "important");
					if (el.tagName === "SELECT") {
						el.style.setProperty("appearance", "none", "important");
						el.style.setProperty("padding", "2px 26px 2px 8px", "important");
					}
				});

			// Hide Frappe select icons
			document
				.querySelectorAll(
					".page-form .select-icon, .page-form .select-icon svg, .page-form .select-icon use, .page-form .placeholder"
				)
				.forEach(function (el) {
					el.style.setProperty("display", "none", "important");
				});

			console.log(
				"[FilterFix] Inline styles enforced on " +
					document.querySelectorAll(".page-form select, .page-form input.form-control")
						.length +
					" filter inputs"
			);
		}

		// Initial run — try multiple times to catch Frappe's async render
		var delays = [0, 500, 1500, 3000];
		delays.forEach(function (ms) {
			setTimeout(inject, ms);
		});

		// Re-run on SPA page change
		if (typeof jQuery !== "undefined") {
			try {
				$(document).on("page-change", function () {
					setTimeout(inject, 200);
				});
			} catch (e) {}
		}
	})();
})();
