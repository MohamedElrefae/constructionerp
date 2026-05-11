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
            console.log(`%c[ConstructionTheme] v7.0 — CSS-Only Theming`, "color: #3b82f6; font-weight: bold;");

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
                } catch (e) {}

                try {
                    var stored = sessionStorage.getItem("construction_theme_mode");
                    if (!savedPreference && stored) {
                        savedPreference = stored === "dark" ? "dark" : "light";
                    }
                } catch (e) {}

                let initialMode = savedPreference || document.documentElement.getAttribute("data-theme") || "light";

                console.log("[ConstructionTheme] Initial mode resolved:", initialMode);

                if (savedPreference === "dark") {
                    document.documentElement.setAttribute("data-theme", "dark");
                    initialMode = "dark";
                    this.updateNavbarLabel('dark');
                }

                const config = (window.frappe && frappe.boot && frappe.boot.construction_theme) || {};
                this.currentMode = initialMode;

                this.injectCSSVariables(config);

                document.documentElement.setAttribute("data-theme", initialMode);

                this.setupThemeObserver();
                this.setupMutationObserver();

                this.renderNavbarDropdown(initialMode);
                this.hideFrappeBranding(config);
                this.swapLogo(config.logo_url);
                this.pierceShadowDOM();

                this.colorTreeToolbarButtons();
                setTimeout(() => this.colorTreeToolbarButtons(), 1000);
                setTimeout(() => this.colorTreeToolbarButtons(), 3000);

                this.removeGhostButtons();

                const end = performance.now();
                console.log(`[ConstructionTheme] Initialized in ${initialMode} mode. Boot time: ${(end - start).toFixed(2)}ms`);
            } catch (err) {
                console.error("[ConstructionTheme] Initialization failed", err);
            }
        },

        injectCSSVariables: function(config) {
            if (!config || !config.primary_color) return;

            const root = document.documentElement;
            const vars = {
                '--primary': config.primary_color,
                '--accent': config.accent_color,
                '--danger': config.danger_color,
                '--success': config.success_color,
            };

            Object.entries(vars).forEach(([key, value]) => {
                if (value) root.style.setProperty(key, value);
            });
        },

        setupThemeObserver: function() {
            if (this._themeObserver) return;

            this._themeObserver = new MutationObserver((mutations) => {
                if (this.isInternalChange) return;

                mutations.forEach((mutation) => {
                    if (mutation.attributeName === "data-theme") {
                        const newMode = document.documentElement.getAttribute("data-theme");
                        if (newMode && newMode !== this.currentMode) {
                            console.log("[ConstructionTheme] External sync triggered for:", newMode);
                            this.currentMode = newMode;
                            this.updateNavbarLabel(newMode);
                        }
                    }
                });
            });
            this._themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
        },

        disconnectObservers: function() {
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

        setupMutationObserver: function() {
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
                            node.querySelectorAll('*').forEach(el => {
                                if (el.shadowRoot && !this._shadowRootsInjected.has(el.shadowRoot)) {
                                    newShadowRoots.push(el.shadowRoot);
                                }
                            });
                        }

                        if (node.classList && node.classList.contains('tree-node-toolbar')) {
                            needsTreeButtonColor = true;
                        }
                        if (node.querySelectorAll) {
                            if (node.querySelector('.tree-node-toolbar')) {
                                needsTreeButtonColor = true;
                            }
                        }
                    });
                });

                if (newShadowRoots.length > 0) {
                    newShadowRoots.forEach(root => this.injectShadowTokens(root));
                }

                if (needsTreeButtonColor) {
                    this.colorTreeToolbarButtons();
                }

                this.removeGhostButtons();
            });

            this._mutationObserver.observe(document.body, { childList: true, subtree: true });
        },

        injectShadowTokens: function(root) {
            if (!root || this._shadowRootsInjected.has(root)) return;
            if (root.querySelector('#construction-shadow-tokens')) return;

            const style = document.createElement('style');
            style.id = 'construction-shadow-tokens';
            style.textContent = `
                :host {
                    --primary-color: var(--primary, #0ea5e9);
                    --danger-color: var(--danger, #dc2626);
                    --success-color: var(--success, #16a34a);
                    --warning-color: var(--accent, #f59e0b);
                    --text-color: var(--text, #f8fafc);
                    --bg-color: var(--bg, #0b1020);
                    --fg-color: var(--surface, #1e293b);
                    --border-color: var(--border, rgba(148,163,184,0.18));
                }
            `;
            root.appendChild(style);
            this._shadowRootsInjected.add(root);
        },

        removeGhostButtons: function() {
            if (typeof $ === 'undefined' || !window.jQuery) return;

            const cleanup = () => {
                $('.construction-export-menu, .construction-view-menu').each(function() {
                    const $menu = $(this);
                    const items = $menu.find('.dropdown-menu li');
                    if (items.length === 0 || items.text().trim() === "") {
                        $menu.remove();
                    }
                });

                $('.page-head .btn-group:empty, .page-header .btn-group:empty').remove();

                $('.page-head .icon-btn, .page-header .icon-btn').each(function() {
                    var $btn = $(this);
                    var svgUse = $btn.find('svg use');
                    var hasValidIcon = svgUse.length > 0 && svgUse.attr('href');
                    var hasText = $btn.text().trim().length > 0;
                    if (!hasValidIcon && !hasText) {
                        $btn.remove();
                    }
                });
            };

            cleanup();
            setTimeout(cleanup, 500);
            setTimeout(cleanup, 1500);
        },

        colorTreeToolbarButtons: function() {
            var buttons = document.querySelectorAll('.tree-node-toolbar .btn, .tree-node-toolbar .tree-toolbar-button, .tree-node-toolbar button');
            var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

            buttons.forEach(function(btn) {
                var text = (btn.textContent || '').trim().toLowerCase();
                btn.classList.remove('btn-edit', 'btn-add', 'btn-delete', 'btn-view');
                btn.classList.remove('btn-default', 'btn-xs');

                btn.style.removeProperty('background');
                btn.style.removeProperty('background-color');
                btn.style.removeProperty('border-color');
                btn.style.removeProperty('color');
                btn.style.removeProperty('box-shadow');

                if (text.includes('edit') || text.includes('modify')) {
                    btn.classList.add('btn-edit');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--primary)', 'important');
                        btn.style.setProperty('border-color', 'var(--primary)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                } else if (text.includes('add') || text.includes('child') || text.includes('new')) {
                    btn.classList.add('btn-add');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--success)', 'important');
                        btn.style.setProperty('border-color', 'var(--success)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                } else if (text.includes('delete') || text.includes('remove')) {
                    btn.classList.add('btn-delete');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--danger)', 'important');
                        btn.style.setProperty('border-color', 'var(--danger)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                } else if (text.includes('view') || text.includes('ledger') || text.includes('open')) {
                    btn.classList.add('btn-view');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--accent)', 'important');
                        btn.style.setProperty('border-color', 'var(--accent)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                }
            });
        },

        setMode: function (mode) {
            mode = mode === "dark" ? "dark" : "light";

            var now = Date.now();
            if (this._lastSetMode && (now - this._lastSetMode) < 1000) return;
            this._lastSetMode = now;

            console.log("[ConstructionTheme] Setting mode:", mode);

            this.isInternalChange = true;
            this.currentMode = mode;

            document.documentElement.setAttribute("data-theme", mode);
            try {
                sessionStorage.setItem("construction_theme_mode", mode);
            } catch (e) {}

            this.updateNavbarLabel(mode);
            this.persist(mode);
        },

        pierceShadowDOM: function() {
            document.querySelectorAll('*').forEach(el => {
                if (el.shadowRoot) this.injectShadowTokens(el.shadowRoot);
            });
        },

        hideFrappeBranding: function(config) {
            if (typeof $ === 'undefined' || !window.jQuery) {
                return;
            }

            const hideBranding = () => {
                try {
                    $('.dropdown-help [href*="frappe.io"]').closest('li').hide();
                    $('.dropdown-help [href*="github.com/frappe"]').closest('li').hide();

                    $('.web-footer-powered-by, .footer-powered').hide();

                    if (config.app_title) {
                        $('.navbar-brand-title').text(config.app_title);
                    }
                } catch (e) {
                    console.warn('[ConstructionTheme] Error hiding branding:', e);
                }
            };

            hideBranding();
            setTimeout(hideBranding, 2000);
        },

        swapLogo: function(logoUrl) {
            if (!logoUrl) return;
            const logo = document.querySelector('.navbar-brand img, .app-logo img');
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
                    }
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

            const navbar = document.querySelector(".navbar-nav") 
                || document.querySelector(".navbar .navbar-collapse .navbar-nav") 
                || document.querySelector(".navbar .container .navbar-nav");
            if (!navbar) {
                setTimeout(() => {
                    this._navbarDropdownPending = false;
                    this.renderNavbarDropdown(mode);
                }, 100);
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
                <a class="nav-link" href="#" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" style="padding-top: 12px;">
                   <span class="theme-label">${mode === "dark" ? "\uD83C\uDFD7\uFE0F Construction Dark" : "\u2600\uFE0F Construction Light"}</span>
                </a>
                <div class="dropdown-menu dropdown-menu-right">
                    <a class="dropdown-item" href="#" onclick="ConstructionTheme.setMode('light'); return false;">\u2600\uFE0F Construction Light</a>
                    <a class="dropdown-item" href="#" onclick="ConstructionTheme.setMode('dark'); return false;">\uD83C\uDFD7\uFE0F Construction Dark</a>
                </div>
            `;
            navbar.prepend(li);
            this._navbarDropdownPending = false;
            console.log("[ConstructionTheme] Navbar dropdown rendered");
        },

        updateNavbarLabel: function (mode) {
            const label = document.querySelector("#construction-theme-dropdown .theme-label");
            if (label) {
                label.textContent = mode === "dark" ? "\uD83C\uDFD7\uFE0F Construction Dark" : "\u2600\uFE0F Construction Light";
            }
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => window.ConstructionTheme.init());
    } else {
        window.ConstructionTheme.init();
    }

    window.addEventListener('beforeunload', () => {
        if (window.ConstructionTheme) {
            window.ConstructionTheme.disconnectObservers();
        }
    });
})();
