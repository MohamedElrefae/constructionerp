(function () {
    "use strict";

    // ── THEME ENGINE ────────────────────────────────────────────────────────
    window.ConstructionTheme = {
        currentMode: "light",
        isInternalChange: false,
        _mutationObserver: null,
        _themeObserver: null,
        _cascadeGuard: null,
        _shadowRootsInjected: new WeakSet(),

        init: function () {
            const start = performance.now();
            console.log(`%c[ConstructionTheme] v6.0 Native Theme Loader Initializing...`, "color: #3b82f6; font-weight: bold;");
            
            try {
                // Use Frappe native data-theme attribute only
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
                var themeKey = initialMode === "dark" ? "construction_dark" : "construction_light";
                
                console.log("[ConstructionTheme] Initial mode resolved:", initialMode, "(savedPreference:", savedPreference, ")");
                
                // If user prefers dark, force it regardless of server-rendered data-theme
                if (savedPreference === "dark") {
                    document.documentElement.setAttribute("data-theme", "dark");
                    initialMode = "dark";
                    themeKey = "construction_dark";
                    console.log("[ConstructionTheme] Forcing dark mode from saved preference");
                    // Apply CSS and update label immediately
                    this.fetchAndApplyCSS('dark');
                    this.updateNavbarLabel('dark');
                }
                
                // 1. Inject critical CSS variables immediately to prevent FOUC
                this.injectCriticalCSS(initialMode);
                
                // 2. Get config from frappe.boot
                const config = (window.frappe && frappe.boot && frappe.boot.construction_theme) || {};
                this.currentMode = initialMode;
                
                // 3. Inject additional CSS variables from config (if any)
                this.injectCSSVariables(config);
                
                // 4. Set standard theme attributes (reinforce)
                document.documentElement.setAttribute("data-theme", initialMode);
                
                // 4. Setup Observers
                this.setupCascadeGuard();
                this.setupThemeObserver(); 
                this.setupMutationObserver(); 
                
                // 5. Initial UI refinements
                this.renderNavbarDropdown(initialMode);
                this.hideFrappeBranding(config);
                this.swapLogo(config.logo_url);
                this.pierceShadowDOM();
                
                // 5b. Color tree toolbar buttons (Chart of Accounts)
                this.colorTreeToolbarButtons();
                setTimeout(() => this.colorTreeToolbarButtons(), 1000);
                setTimeout(() => this.colorTreeToolbarButtons(), 3000);
                
                // 5c. Remove ghost header buttons
                this.removeGhostButtons();
                
                // 6. Fetch full theme CSS
                this.fetchAndApplyCSS(initialMode);

                const end = performance.now();
                console.log(`[ConstructionTheme] Initialized in ${initialMode} mode. Boot time: ${(end - start).toFixed(2)}ms`);
            } catch (err) {
                console.error("[ConstructionTheme] CRITICAL: Initialization failed", err);
                // Graceful degradation: ensure base CSS at least is present
                this.applyEmergencyFallback();
            }
        },

        getSidebarTextOverrideCSS: function(mode) {
            if (mode === 'dark') {
                return `
                    /* FINAL SIDEBAR VISIBILITY GUARD — text + icons */
                    html[data-theme="dark"] .layout-side-section,
                    html[data-theme="dark"] .layout-side-section a,
                    html[data-theme="dark"] .layout-side-section span,
                    html[data-theme="dark"] .layout-side-section div,
                    html[data-theme="dark"] .layout-side-section .desk-sidebar-item,
                    html[data-theme="dark"] .layout-side-section .standard-sidebar-item,
                    html[data-theme="dark"] .layout-side-section .sidebar-item-label,
                    html[data-theme="dark"] .layout-side-section .standard-sidebar-label,
                    html[data-theme="dark"] .desk-sidebar,
                    html[data-theme="dark"] .desk-sidebar a,
                    html[data-theme="dark"] .desk-sidebar span,
                    html[data-theme="dark"] .desk-sidebar .desk-sidebar-item,
                    html[data-theme="dark"] .desk-sidebar .standard-sidebar-item,
                    html[data-theme="dark"] .desk-sidebar .sidebar-item-label,
                    html[data-theme="dark"] .standard-sidebar,
                    html[data-theme="dark"] .standard-sidebar a,
                    html[data-theme="dark"] .standard-sidebar span,
                    html[data-theme="dark"] .standard-sidebar .standard-sidebar-item,
                    html[data-theme="dark"] .standard-sidebar .sidebar-item-label {
                        color: #f8fafc !important;
                        opacity: 1 !important;
                        filter: none !important;
                    }

                    /* Icons: restore natural colours by removing monochrome forcing */
                    html[data-theme="dark"] .layout-side-section .sidebar-item-icon svg,
                    html[data-theme="dark"] .desk-sidebar .sidebar-item-icon svg,
                    html[data-theme="dark"] .standard-sidebar .sidebar-item-icon svg {
                        /* color: #f8fafc !important; -- REMOVED */
                        /* stroke: #f8fafc !important; -- REMOVED */
                        opacity: 1 !important;
                        filter: none !important;
                    }

                    /* If some icons are fill-based, this class catches them without affecting all SVG globally */
                    html[data-theme="dark"] .layout-side-section .sidebar-item-icon svg *,
                    html[data-theme="dark"] .desk-sidebar .sidebar-item-icon svg *,
                    html[data-theme="dark"] .standard-sidebar .sidebar-item-icon svg * {
                        stroke: #f8fafc !important;
                        color: #f8fafc !important;
                        opacity: 1 !important;
                    }
                `;
            }

            return `
                html[data-theme="light"] body .layout-side-section .desk-sidebar-item,
                html[data-theme="light"] body .layout-side-section .standard-sidebar-item,
                html[data-theme="light"] body .layout-side-section .desk-sidebar-item > a,
                html[data-theme="light"] body .layout-side-section .standard-sidebar-item > a,
                html[data-theme="light"] body .layout-side-section a.item-anchor,
                html[data-theme="light"] body .layout-side-section .sidebar-item-label,
                html[data-theme="light"] body .desk-sidebar .desk-sidebar-item,
                html[data-theme="light"] body .desk-sidebar .standard-sidebar-item,
                html[data-theme="light"] body .desk-sidebar .standard-sidebar-item > a.item-anchor,
                html[data-theme="light"] body .desk-sidebar .sidebar-item-label,
                html[data-theme="light"] body .standard-sidebar .desk-sidebar-item,
                html[data-theme="light"] body .standard-sidebar .standard-sidebar-item,
                html[data-theme="light"] body .standard-sidebar .standard-sidebar-item > a.item-anchor,
                html[data-theme="light"] body .standard-sidebar .sidebar-item-label,
                html[data-theme="light"] body .sidebar-container a.item-anchor,
                html[data-theme="light"] body .sidebar-container .sidebar-item-label {
                    color: #0f172a !important;
                }
            `;
        },

        applyEmergencyFallback: function() {
            // Ensure native data-theme is set for CSS to apply
            const mode = document.documentElement.getAttribute("data-theme") || "light";
            document.documentElement.setAttribute("data-theme", mode);
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

        injectCriticalCSS: function(mode) {
            // Inject critical CSS immediately to prevent FOUC and override Frappe defaults
            const isDark = mode === 'dark';
            const criticalCSS = `
                /* Layout fixes - MUST be first to override Frappe */
                html { background: ${isDark ? '#0b1020' : '#f8fafc'} !important; }
                body { background: ${isDark ? '#0b1020' : '#f8fafc'} !important; color: ${isDark ? '#f8fafc' : '#1e293b'} !important; }
                .navbar { background: ${isDark ? '#0b1020' : '#ffffff'} !important; border-bottom: 1px solid ${isDark ? 'rgba(148,163,184,0.18)' : '#e5e7eb'} !important; }
                .nav-link { color: ${isDark ? '#94a3b8' : '#64748b'} !important; }
                .btn-primary { background: #0ea5e9 !important; border-color: #0ea5e9 !important; color: white !important; }
                .btn-secondary { background: ${isDark ? '#1e293b' : '#f1f5f9'} !important; border-color: ${isDark ? 'rgba(148,163,184,0.18)' : '#e5e7eb'} !important; color: ${isDark ? '#f8fafc' : '#1e293b'} !important; }
                
                /* SIDEBAR LAYOUT FIXES - Override Frappe's defaults */
                .layout-side-section { 
                    min-width: 260px !important; 
                    width: 260px !important; 
                    flex-shrink: 0 !important;
                    max-width: 260px !important;
                }
                .layout-main-section { 
                    flex: 1 !important; 
                    min-width: 0 !important; 
                    width: 100% !important;
                    max-width: none !important;
                }
                .page-content { 
                    display: flex !important; 
                    flex-direction: row !important;
                }
                .container, #page-container, .main-section {
                    max-width: 100% !important;
                    width: 100% !important;
                }
                /* Stop any transitions that cause flicker */
                .layout-side-section, .layout-main-section, .page-content {
                    transition: none !important;
                }
                /* Sidebar buttons - ensure clickable */
                .desk-sidebar .sidebar-item-control, .standard-sidebar .sidebar-item-control {
                    z-index: 100 !important;
                    pointer-events: auto !important;
                    display: flex !important;
                }
                .desk-sidebar .sidebar-item-control .btn, .desk-sidebar .btn-group .btn {
                    pointer-events: auto !important;
                    z-index: 101 !important;
                    opacity: 1 !important;
                    display: inline-flex !important;
                }

                /* NUCLEAR HEADER SLIMMER & GHOST BUTTON HIDER */
                .page-head, .page-header {
                    height: 48px !important;
                    min-height: 48px !important;
                    padding: 0 15px !important;
                    display: flex !important;
                    align-items: center !important;
                }
                .page-head .page-head-content { height: 100% !important; display: flex !important; align-items: center !important; }
                .page-head .page-title { margin: 0 !important; line-height: 1 !important; font-size: 1.1rem !important; }
                
                /* SLIM HEADER ENFORCEMENT */
                .page-head, .page-header {
                    height: 48px !important;
                    min-height: 48px !important;
                    padding: 0 15px !important;
                    display: flex !important;
                    align-items: center !important;
                }
                .page-head .page-head-content { height: 100% !important; display: flex !important; align-items: center !important; }
                .page-head .page-title { margin: 0 !important; line-height: 1 !important; font-size: 1.1rem !important; }
                
                /* Only hide truly empty system containers, never hide buttons with content */
                .page-head .btn-group:empty, 
                .page-head .standard-actions:empty, 
                .page-head .custom-actions:empty { 
                    display: none !important; 
                }
            `;
            
            let style = document.getElementById('construction-critical-css');
            if (!style) {
                style = document.createElement('style');
                style.id = 'construction-critical-css';
                // Insert as first element in head to ensure highest priority
                if (document.head.firstChild) {
                    document.head.insertBefore(style, document.head.firstChild);
                } else {
                    document.head.appendChild(style);
                }
            }
            style.textContent = criticalCSS;
            console.log('[ConstructionTheme] Critical CSS injected for', mode, 'mode');
        },

        setupThemeObserver: function() {
            if (this._themeObserver) return; // Prevent duplicate observers
            
            this._themeObserver = new MutationObserver((mutations) => {
                if (this.isInternalChange) return;
                
                mutations.forEach((mutation) => {
                    if (mutation.attributeName === "data-theme") {
                        const newMode = document.documentElement.getAttribute("data-theme");
                        if (newMode && newMode !== this.currentMode) {
                            console.log("[ConstructionTheme] External sync triggered for:", newMode);
                            this.currentMode = newMode;
                            this.updateNavbarLabel(newMode);
                            this.fetchAndApplyCSS(newMode);
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
            if (this._cascadeGuard) {
                this._cascadeGuard.disconnect();
                this._cascadeGuard = null;
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
                        
                        if (this.currentMode === 'dark') {
                            if (node.style && node.style.backgroundColor && 
                                (node.style.backgroundColor.includes('rgb(255, 255, 255)') || node.style.backgroundColor === 'white')) {
                                node.style.backgroundColor = '';
                            }
                            
                            if (node.querySelectorAll) {
                                node.querySelectorAll('[style*="background-color: rgb(255, 255, 255)"]').forEach(el => {
                                    el.style.backgroundColor = '';
                                });
                            }
                        }
                        
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

                // Periodic ghost button cleanup
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
            /**
             * Surgical cleanup of empty or non-functional Construction header buttons.
             * Addresses "ghost" squares appearing in the header across all pages.
             */
            if (typeof $ === 'undefined' || !window.jQuery) return;

            const cleanup = () => {
                // Remove buttons with specific construction classes if they have no dropdown items
                $('.construction-export-menu, .construction-view-menu').each(function() {
                    const $menu = $(this);
                    const items = $menu.find('.dropdown-menu li');
                    // If no items or only dividers, it's a ghost button
                    if (items.length === 0 || items.text().trim() === "") {
                        $menu.remove();
                    }
                });

                // Also hide any truly empty button groups in the header
                $('.page-head .btn-group:empty, .page-header .btn-group:empty').remove();

                // Remove .icon-btn buttons whose inner SVG/icon is empty (no visible content).
                // This catches add_action_icon() calls with invalid icon names (e.g. "Print")
                // which produce <button class="icon-btn"> with empty frappe.utils.icon() output.
                $('.page-head .icon-btn, .page-header .icon-btn').each(function() {
                    var $btn = $(this);
                    // Check if the button has no meaningful visible content
                    var svgUse = $btn.find('svg use');
                    var hasValidIcon = svgUse.length > 0 && svgUse.attr('href');
                    var hasText = $btn.text().trim().length > 0;
                    if (!hasValidIcon && !hasText) {
                        $btn.remove();
                    }
                });
            };

            cleanup();
            // Run again after a short delay to catch late-renders from Frappe's page loading
            setTimeout(cleanup, 500);
            setTimeout(cleanup, 1500);
        },

        colorTreeToolbarButtons: function() {
            var buttons = document.querySelectorAll('.tree-node-toolbar .btn, .tree-node-toolbar .tree-toolbar-button, .tree-node-toolbar button');
            console.log('[ConstructionTheme] Coloring tree toolbar buttons. Found:', buttons.length);
            var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            
            buttons.forEach(function(btn) {
                var text = (btn.textContent || '').trim().toLowerCase();
                btn.classList.remove('btn-edit', 'btn-add', 'btn-delete', 'btn-view');
                btn.classList.remove('btn-default', 'btn-xs');
                
                // Clear only background/border/color inline styles - keep transition/transform from CSS
                btn.style.removeProperty('background');
                btn.style.removeProperty('background-color');
                btn.style.removeProperty('border-color');
                btn.style.removeProperty('color');
                btn.style.removeProperty('box-shadow');
                
                if (text.includes('edit') || text.includes('modify')) {
                    btn.classList.add('btn-edit');
                    if (isDark) {
                        // Use setProperty with 'important' to beat Frappe's dark mode CSS
                        btn.style.setProperty('background', 'var(--primary)', 'important');
                        btn.style.setProperty('border-color', 'var(--primary)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                    console.log('[ConstructionTheme] Colored button as edit:', text);
                } else if (text.includes('add') || text.includes('child') || text.includes('new')) {
                    btn.classList.add('btn-add');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--success)', 'important');
                        btn.style.setProperty('border-color', 'var(--success)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                    console.log('[ConstructionTheme] Colored button as add:', text);
                } else if (text.includes('delete') || text.includes('remove')) {
                    btn.classList.add('btn-delete');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--danger)', 'important');
                        btn.style.setProperty('border-color', 'var(--danger)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                    console.log('[ConstructionTheme] Colored button as delete:', text);
                } else if (text.includes('view') || text.includes('ledger') || text.includes('open')) {
                    btn.classList.add('btn-view');
                    if (isDark) {
                        btn.style.setProperty('background', 'var(--accent)', 'important');
                        btn.style.setProperty('border-color', 'var(--accent)', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                    }
                    console.log('[ConstructionTheme] Colored button as view:', text);
                }
            });
        },

        setupCascadeGuard: function () {
            if (this._cascadeGuard) return; // Prevent duplicate guards
            
            this._cascadeGuard = new MutationObserver(() => {
                const el = document.getElementById("construction-theme-override");
                if (el && el !== document.head.lastElementChild) {
                    document.head.appendChild(el);
                }
            });
            this._cascadeGuard.observe(document.head, { childList: true });
        },

        setMode: function (mode) {
            mode = mode === "dark" ? "dark" : "light";
            
            var now = Date.now();
            if (this._lastSetMode && (now - this._lastSetMode) < 1000) return;
            this._lastSetMode = now;
            
            var themeKey = mode === "dark" ? "construction_dark" : "construction_light";
            console.log("[ConstructionTheme] Setting mode:", mode);
            
            this.isInternalChange = true;
            this.currentMode = mode;
            
            document.documentElement.setAttribute("data-theme", mode);
            try {
                sessionStorage.setItem("construction_theme_mode", mode);
            } catch (e) {}
            
            this.updateNavbarLabel(mode);
            this.fetchAndApplyCSS(mode);
            this.persist(mode);
        },

        fetchAndApplyCSS: function (mode) {
            const themeKey = mode === "dark" ? "construction_dark" : "construction_light";
            
            if (window.frappe && frappe.call) {
                frappe.call({
                    method: "construction.api.theme_api.get_theme_css_variables",
                    args: { theme_name: themeKey, version: "v16" },
                    callback: (r) => {
                        if (r.message && r.message.css_variables) {
                            this.injectCSS(r.message.css_variables);
                        }
                    }
                });
            }
        },

        injectCSS: function (css) {
            let el = document.getElementById("construction-theme-override");
            if (!el) {
                el = document.createElement("style");
                el.id = "construction-theme-override";
            }
            const mode = this.currentMode === "dark" ? "dark" : "light";
            el.textContent = css + "\n" + this.getSidebarTextOverrideCSS(mode);
            document.head.appendChild(el);
        },

        pierceShadowDOM: function() {
            document.querySelectorAll('*').forEach(el => {
                if (el.shadowRoot) this.injectShadowTokens(el.shadowRoot);
            });
        },

        hideFrappeBranding: function(config) {
            // Guard: jQuery must be available
            if (typeof $ === 'undefined' || !window.jQuery) {
                console.warn('[ConstructionTheme] jQuery not available, skipping branding hide');
                return;
            }
            
            const hideBranding = () => {
                try {
                    // Hide help menu items linking to Frappe
                    $('.dropdown-help [href*="frappe.io"]').closest('li').hide();
                    $('.dropdown-help [href*="github.com/frappe"]').closest('li').hide();
                    
                    // Hide powered-by footers
                    $('.web-footer-powered-by, .footer-powered').hide();
                    
                    // Replace navbar brand if title is provided
                    if (config.app_title) {
                        $('.navbar-brand-title').text(config.app_title);
                    }
                } catch (e) {
                    console.warn('[ConstructionTheme] Error hiding branding:', e);
                }
            };
            
            hideBranding();
            // Run again after a delay to catch late-rendered items
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
                    callback: function (r) {
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
            // Guard: Prevent duplicate dropdowns
            if (document.getElementById("construction-theme-dropdown")) {
                this.updateNavbarLabel(mode);
                return;
            }
            
            // Guard: Prevent multiple concurrent retry attempts
            if (this._navbarDropdownPending) return;
            this._navbarDropdownPending = true;
            
            const navbar = document.querySelector(".navbar .navbar-collapse .navbar-nav");
            if (!navbar) {
                setTimeout(() => {
                    this._navbarDropdownPending = false;
                    this.renderNavbarDropdown(mode);
                }, 100);
                return;
            }
            
            // Double-check after acquiring navbar (race condition protection)
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
                   <span class="theme-label">${mode === "dark" ? "🏗️ Construction Dark" : "☀️ Construction Light"}</span>
                </a>
                <div class="dropdown-menu dropdown-menu-right">
                    <a class="dropdown-item" href="#" onclick="ConstructionTheme.setMode('light'); return false;">☀️ Construction Light</a>
                    <a class="dropdown-item" href="#" onclick="ConstructionTheme.setMode('dark'); return false;">🏗️ Construction Dark</a>
                </div>
            `;
            navbar.prepend(li);
            this._navbarDropdownPending = false;
            console.log("[ConstructionTheme] Navbar dropdown rendered successfully");
        },

        updateNavbarLabel: function (mode) {
            const label = document.querySelector("#construction-theme-dropdown .theme-label");
            if (label) {
                label.textContent = mode === "dark" ? "🏗️ Construction Dark" : "☀️ Construction Light";
            }
        },

        verifyLabCompliance: function() {
            /** 
             * Visual Regression Helper
             * Used by QA scripts to verify token injection success.
             */
            const root = getComputedStyle(document.documentElement);
            const tokens = {
                primary: root.getPropertyValue('--primary').trim(),
                accent: root.getPropertyValue('--accent').trim(),
                bg: root.getPropertyValue('--bg').trim(),
                surface: root.getPropertyValue('--surface').trim()
            };
            
            // Check Shadow DOM penetration
            let shadowPenetrated = false;
            const webComponents = document.querySelectorAll('*');
            for (let el of webComponents) {
                if (el.shadowRoot && el.shadowRoot.querySelector('#construction-shadow-tokens')) {
                    shadowPenetrated = true;
                    break;
                }
            }

            const status = {
                tokensInjected: !!tokens.primary && !!tokens.accent,
                shadowPenetrated: shadowPenetrated,
                themeMode: document.documentElement.getAttribute('data-theme'),
                tokens: tokens
            };
            
            console.table ? console.table(status) : console.log("[ConstructionTheme] Compliance:", status);
            return status.tokensInjected && shadowPenetrated;
        },

        verifyState: function () {
            var root = getComputedStyle(document.documentElement);
            return {
                dataTheme: document.documentElement.getAttribute("data-theme"),
                mode: window.ConstructionTheme.currentMode,
                tokens: {
                    bg: root.getPropertyValue("--bg").trim(),
                    surface: root.getPropertyValue("--surface").trim(),
                    text: root.getPropertyValue("--text").trim(),
                    border: root.getPropertyValue("--border").trim()
                }
            };
        }

    };

    // Auto-init on script load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => window.ConstructionTheme.init());
    } else {
        window.ConstructionTheme.init();
    }
    
    // Cleanup on page unload (SPA navigation support)
    window.addEventListener('beforeunload', () => {
        if (window.ConstructionTheme) {
            window.ConstructionTheme.disconnectObservers();
        }
    });
})();
