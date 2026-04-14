/**
 * Modern Theme Loader for ERPNext
 * Bridges Frappe's Light/Dark/Automatic with custom Desk Themes
 */

(function() {
    'use strict';

    const ModernThemeLoader = {
        currentTheme: null,
        currentMode: null,
        
        /**
         * Initialize the theme loader
         */
        init: function() {
            console.log('[Modern Theme] Initializing...');
            
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
        applyTheme: function() {
            const self = this;
            
            frappe.call({
                method: 'construction.api.theme_api.get_effective_desk_theme',
                callback: function(r) {
                    if (r.message) {
                        const { theme_name, mode, source } = r.message;
                        console.log(`[Modern Theme] Applying: ${theme_name} (${mode}, source: ${source})`);
                        
                        self.currentTheme = theme_name;
                        self.currentMode = mode;
                        
                        // Apply to document
                        document.documentElement.setAttribute('data-theme', mode);
                        document.documentElement.setAttribute('data-modern-theme', theme_name);
                        
                        // If using frappe_desk_theme, trigger its loader
                        if (typeof frappe.DeskTheme !== 'undefined' && theme_name !== 'Standard') {
                            frappe.DeskTheme.apply(theme_name);
                        }
                        
                        // Dispatch custom event
                        window.dispatchEvent(new CustomEvent('modern-theme-applied', {
                            detail: { theme_name, mode, source }
                        }));
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
                    // Re-apply theme when OS preference changes
                    self.applyTheme();
                });
            }
            
            // Watch for Frappe theme toggle
            // Frappe sets data-theme attribute, we can observe that
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.attributeName === 'data-theme') {
                        const newTheme = document.documentElement.getAttribute('data-theme');
                        if (newTheme !== self.currentMode) {
                            console.log('[Modern Theme] Mode changed to:', newTheme);
                            self.applyTheme();
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
         * Inject modern theme CSS variables
         */
        injectCSSVariables: function() {
            // CSS variables are already loaded via app_include_css
            // This method can be used for dynamic variable injection if needed
            
            // Add modern-theme-loaded class to body
            document.body.classList.add('modern-theme-loaded');
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
        }
    };

    // Expose to global
    window.ModernThemeLoader = ModernThemeLoader;
    
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
