/**
 * Modern Theme Loader for ERPNext
 * Bridges Frappe's Light/Dark/Automatic with custom Desk Themes
 * VERSION: 2.0 - CACHE BUST: 20250416
 */

(function() {
    'use strict';

    // VERSION CHECK - This should appear in console if new file is loaded
    console.log('%c[Modern Theme] LOADER v2.0 - 20250416', 'background: #2E7D32; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;');

    const ModernThemeLoader = {
        currentTheme: null,
        currentMode: null,
        version: '2.0',

        /**
         * Initialize the theme loader
         */
        init: function() {
            console.log(`[Modern Theme v${this.version}] Initializing...`);

            // Wait for Frappe to be ready
            if (typeof frappe === 'undefined') {
                setTimeout(() => this.init(), 100);
                return;
            }

            // Apply theme on load
            this.applyTheme();

            // Watch for theme changes
            this.watchThemeChanges();

            // Inject modern theme CSS variables into root
            this.injectCSSVariables();
        },

        /**
         * Apply the effective theme for current user
         */
        applyTheme: function(forcedMode) {
            const self = this;

            // Use forced mode if provided (from DOM detection), otherwise let API decide
            const currentDomMode = document.documentElement.getAttribute('data-theme');
            const modeToSend = forcedMode || currentDomMode || 'light';

            console.log(`[Modern Theme] applyTheme called with forcedMode=${forcedMode}, currentDomMode=${currentDomMode}, sending=${modeToSend}`);

            frappe.call({
                method: 'construction.api.theme_api.get_effective_desk_theme',
                args: { current_mode: modeToSend },  // Pass current mode to help API resolve
                callback: function(r) {
                    console.log(`[Modern Theme] API response received:`, r.message);
                    if (r.message) {
                        let { theme_name, mode, source } = r.message;

                        console.log(`[Modern Theme] BEFORE override - theme_name: ${theme_name}, mode: ${mode}, forcedMode: ${forcedMode}, modeToSend: ${modeToSend}`);

                        // ALWAYS override with what we know is correct from the DOM/forced parameter
                        if (forcedMode) {
                            if (mode !== forcedMode) {
                                console.log(`[Modern Theme] OVERRIDE: API returned mode "${mode}" but forcedMode is "${forcedMode}", using forcedMode`);
                                mode = forcedMode;
                                source = 'dom_override';
                            }
                        } else if (modeToSend && mode !== modeToSend) {
                            console.log(`[Modern Theme] OVERRIDE: API returned mode "${mode}" but we sent "${modeToSend}", using modeToSend`);
                            mode = modeToSend;
                            source = 'request_override';
                        }

                        console.log(`[Modern Theme] AFTER override - Final applying: ${theme_name} (${mode}, source: ${source})`);

                        self.currentTheme = theme_name;
                        self.currentMode = mode;

                        // Apply to document - THIS IS THE CRITICAL STEP
                        console.log(`[Modern Theme] Setting document data-theme to: ${mode}`);
                        document.documentElement.setAttribute('data-theme', mode);
                        document.documentElement.setAttribute('data-modern-theme', theme_name);

                        // If using frappe_desk_theme, trigger its loader
                        if (typeof frappe.DeskTheme !== 'undefined' && theme_name !== 'Standard') {
                            frappe.DeskTheme.apply(theme_name);
                        }

                        // Fetch and apply dynamic CSS for custom themes
                        if (theme_name && theme_name !== 'Standard') {
                            self.fetchAndApplyCSSVariables(theme_name);
                        }

                        // Update navbar indicator
                        self.updateNavbarIndicator(mode);

                        // Dispatch custom event
                        window.dispatchEvent(new CustomEvent('modern-theme-applied', {
                            detail: { theme_name, mode, source }
                        }));

                        // Final verification
                        const finalMode = document.documentElement.getAttribute('data-theme');
                        console.log(`[Modern Theme] VERIFICATION: Final document data-theme is: ${finalMode}`);
                    } else {
                        console.error('[Modern Theme] ERROR: API returned no message:', r);
                    }
                },
                error: function(err) {
                    console.error('[Modern Theme] API call failed:', err);
                    // Even on error, try to apply the forced mode
                    if (forcedMode) {
                        console.log(`[Modern Theme] Applying forced mode ${forcedMode} despite API error`);
                        document.documentElement.setAttribute('data-theme', forcedMode);
                        self.currentMode = forcedMode;
                        self.updateNavbarIndicator(forcedMode);
                    }
                }
            });
        },

        /**
         * Watch for theme preference changes
         */
        watchThemeChanges: function() {
            const self = this;

            // Watch for OS theme changes (if Automatic)
            if (window.matchMedia) {
                const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
                darkModeQuery.addEventListener('change', function(e) {
                    const osMode = e.matches ? 'dark' : 'light';
                    console.log('[Modern Theme] OS mode changed to:', osMode);
                    self.applyTheme(osMode);
                });
            }

            // Watch for Frappe theme toggle
            // Frappe sets data-theme attribute, we can observe that
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.attributeName === 'data-theme') {
                        const newMode = document.documentElement.getAttribute('data-theme');
                        const oldMode = self.currentMode;
                        console.log(`[Modern Theme] MutationObserver: data-theme changed from "${oldMode}" to "${newMode}"`);

                        if (newMode && newMode !== oldMode) {
                            console.log('[Modern Theme] Mode change confirmed, calling applyTheme with:', newMode);
                            // Persist this change to backend
                            self.persistModePreference(newMode);
                            // Pass the new mode directly to avoid API re-query race condition
                            self.applyTheme(newMode);
                        } else {
                            console.log('[Modern Theme] Mode unchanged or invalid, skipping applyTheme');
                        }
                    }
                });
            });

            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['data-theme']
            });
        },

        /**
         * Persist mode preference to backend when user switches themes.
         * Uses a dedicated API that bypasses User document version checks
         * to avoid TimestampMismatchError.
         */
        persistModePreference: function(mode) {
            frappe.call({
                method: 'construction.api.theme_api.save_user_mode',
                args: { mode: mode },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        console.log('[Modern Theme] Persisted mode preference:', mode);
                    } else {
                        console.warn('[Modern Theme] Mode save returned:', r.message);
                    }
                },
                error: function(err) {
                    console.log('[Modern Theme] Mode save error (non-critical):', err.message || err);
                }
            });
        },

        /**
         * Inject modern theme CSS variables
         */
        injectCSSVariables: function() {
            // CSS variables are already loaded via app_include_css
            // This method can be used for dynamic variable injection if needed

            // Add modern-theme-loaded class to body
            document.body.classList.add('modern-theme-loaded');

            // Inject navbar theme indicator
            this.injectNavbarIndicator();
        },

        /**
         * Inject theme indicator in navbar
         */
        injectNavbarIndicator: function() {
            const self = this;

            // Wait for navbar to be ready
            const checkNavbar = setInterval(function() {
                const navbar = document.querySelector('.navbar-nav') || document.querySelector('.nav.navbar-right');
                if (navbar) {
                    clearInterval(checkNavbar);

                    // Check if indicator already exists
                    if (!document.getElementById('modern-theme-indicator')) {
                        const indicator = document.createElement('li');
                        indicator.id = 'modern-theme-indicator';
                        indicator.className = 'nav-item dropdown';
                        indicator.innerHTML = `
                            <a class="nav-link" href="#"
                               style="display: flex; align-items: center; padding: 8px 12px; border-radius: 20px; background: var(--hover-bg, rgba(0,0,0,0.05)); margin: 0 8px;"
                               onclick="return false;">
                                <span id="theme-mode-dot" style="
                                    width: 10px;
                                    height: 10px;
                                    border-radius: 50%;
                                    background: ${self.currentMode === 'dark' ? '#60a5fa' : '#fbbf24'};
                                    box-shadow: 0 0 8px ${self.currentMode === 'dark' ? '#60a5fa' : '#fbbf24'};
                                    margin-right: 8px;
                                    transition: all 0.3s ease;
                                "></span>
                                <span id="theme-mode-text" style="font-size: 0.85rem; font-weight: 500;">
                                    ${self.currentMode === 'dark' ? '🌙 Dark' : '☀️ Light'}
                                </span>
                            </a>
                        `;

                        // Insert before the user menu
                        const userMenu = navbar.querySelector('.dropdown-navbar-user');
                        if (userMenu) {
                            navbar.insertBefore(indicator, userMenu);
                        } else {
                            navbar.appendChild(indicator);
                        }

                        console.log('[Modern Theme] Navbar indicator injected');
                    }
                }
            }, 500);

            // Stop checking after 10 seconds
            setTimeout(() => clearInterval(checkNavbar), 10000);
        },

        /**
         * Update navbar indicator
         */
        updateNavbarIndicator: function(mode) {
            const dot = document.getElementById('theme-mode-dot');
            const text = document.getElementById('theme-mode-text');

            if (dot && text) {
                const isDark = mode === 'dark';
                dot.style.background = isDark ? '#60a5fa' : '#fbbf24';
                dot.style.boxShadow = `0 0 8px ${isDark ? '#60a5fa' : '#fbbf24'}`;
                text.textContent = isDark ? '🌙 Dark' : '☀️ Light';
            }
        },

        /**
         * Get current theme info
         */
        getCurrentTheme: function() {
            return {
                theme: this.currentTheme,
                mode: this.currentMode
            };
        },

        /**
         * Refresh theme (call after user changes preferences)
         */
        refresh: function() {
            this.applyTheme();
        },

        /**
         * Inject dynamic CSS variables from theme
         */
        injectDynamicCSS: function(cssVars) {
            if (!cssVars) return;

            let styleId = 'modern-theme-dynamic';
            let styleEl = document.getElementById(styleId);

            if (!styleEl) {
                styleEl = document.createElement('style');
                styleEl.id = styleId;
                document.head.appendChild(styleEl);
            }

            styleEl.textContent = `:root {\n${cssVars}\n}`;
        },

        /**
         * Fetch and apply CSS variables from Modern Theme Settings
         */
        fetchAndApplyCSSVariables: function(themeName) {
            const self = this;

            frappe.call({
                method: 'construction.api.theme_api.get_theme_css_variables',
                args: { theme_name: themeName },
                callback: function(r) {
                    if (r.message && r.message.css_variables) {
                        self.injectDynamicCSS(r.message.css_variables);
                    }
                }
            });
        }
    };

    // Expose to global
    window.ModernThemeLoader = ModernThemeLoader;

    // ============================================
    // Extend Frappe's ThemeSwitcher for v16
    // ============================================

    if (frappe.ui && frappe.ui.ThemeSwitcher) {
        frappe.ui.ThemeSwitcher = class CustomThemeSwitcher extends frappe.ui.ThemeSwitcher {
            fetch_themes() {
                return new Promise((resolve) => {
                    this.themes = [
                        { name: "light", label: "☀️ Light", info: "Frappe Light Theme" },
                        { name: "dark", label: "🌙 Dark", info: "Timeless Night Theme" },
                        { name: "construction_light", label: "🏗️ Construction Light", info: "Modern light theme optimized for construction workflows" },
                        { name: "construction_dark", label: "🏗️ Construction Dark", info: "Modern dark theme optimized for construction workflows" },
                        { name: "automatic", label: "⚡ Automatic", info: "Follows system preference" }
                    ];
                    resolve(this.themes);
                });
            }

            switch_theme(theme_name) {
                console.log(`[Modern Theme] ThemeSwitcher.switch_theme called: ${theme_name}`);

                // Get the current mode from document
                const currentMode = document.documentElement.getAttribute('data-theme') || 'light';
                let targetMode = currentMode;

                // Determine target mode based on theme selection
                if (theme_name === 'dark') {
                    targetMode = 'dark';
                } else if (theme_name === 'light') {
                    targetMode = 'light';
                } else if (theme_name === 'automatic') {
                    // Check system preference
                    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                    targetMode = prefersDark ? 'dark' : 'light';
                } else if (theme_name === 'construction_dark') {
                    targetMode = 'dark';
                } else if (theme_name === 'construction_light') {
                    targetMode = 'light';
                }

                console.log(`[Modern Theme] Switching from ${currentMode} to ${targetMode}`);

                // Update Frappe's theme first
                super.switch_theme(theme_name === 'construction_light' ? 'light' :
                                   theme_name === 'construction_dark' ? 'dark' : theme_name);

                // Apply our custom theme logic
                if (theme_name.startsWith('construction_')) {
                    document.documentElement.setAttribute('data-theme', targetMode);
                    document.documentElement.setAttribute('data-modern-theme', theme_name);
                    ModernThemeLoader.fetchAndApplyCSSVariables(theme_name);

                    // Persist to backend
                    frappe.call({
                        method: 'construction.api.theme_api.set_user_theme',
                        args: { theme: theme_name, mode: targetMode }
                    });
                }

                // Update ModernThemeLoader state and persist mode
                ModernThemeLoader.currentMode = targetMode;
                ModernThemeLoader.persistModePreference(targetMode);

                // Force apply with the new mode
                setTimeout(() => {
                    ModernThemeLoader.applyTheme(targetMode);
                }, 50);
            }

            // Override render to show checkmark on selected theme
            render() {
                try {
                    super.render();
                } catch (e) {
                    console.log('[Modern Theme] Parent ThemeSwitcher render error (non-critical):', e.message);
                }

                // Defer visual indicator application to let the DOM settle
                setTimeout(() => this._applyVisualIndicators(), 150);
            }

            _applyVisualIndicators() {
                const currentTheme = ModernThemeLoader.currentTheme || 'Standard';
                const currentMode = ModernThemeLoader.currentMode || 'light';

                // Determine which theme item should be marked as selected
                let selectedTheme = currentTheme;
                if (currentTheme === 'Standard') {
                    selectedTheme = currentMode === 'dark' ? 'dark' : 'light';
                }

                // Safety check — $wrapper might still not be ready
                if (!this.$wrapper || !this.$wrapper.length) {
                    console.log('[Modern Theme] ThemeSwitcher $wrapper not ready after defer, relying on CSS indicators');
                    return;
                }

                // Set data attribute on body so CSS-only fallback works too
                document.body.setAttribute('data-selected-theme', selectedTheme);

                // Add checkmark to selected theme
                this.$wrapper.find('.theme-item').each(function() {
                    const $item = $(this);
                    const itemTheme = $item.data('theme');

                    // Remove previous indicators
                    $item.removeClass('active-theme');
                    $item.css({ 'border': '', 'background': '' });
                    $item.find('.selected-indicator').remove();

                    const isSelected = (
                        itemTheme === selectedTheme ||
                        (selectedTheme === 'construction_light' && itemTheme === 'light' && currentTheme !== 'Standard') ||
                        (selectedTheme === 'construction_dark' && itemTheme === 'dark' && currentTheme !== 'Standard')
                    );

                    if (isSelected) {
                        $item.addClass('active-theme');
                        $item.css({
                            'border': '2px solid var(--accent-primary, #2E7D32)',
                            'background': 'var(--selected-bg, rgba(46, 125, 50, 0.1))'
                        });
                        if (!$item.find('.selected-indicator').length) {
                            $item.find('.theme-label').prepend('<span class="selected-indicator">✓ </span>');
                        }
                    }
                });
            }
        };
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            ModernThemeLoader.init();
        });
    } else {
        // DOM already loaded
        setTimeout(function() {
            ModernThemeLoader.init();
        }, 0);
    }

})();
