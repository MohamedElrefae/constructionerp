/**
 * Navbar Theme Dropdown Selector for Frappe v16 — Construction ERP
 * VERSION: 1.0 — Persistent Dropdown in Navbar
 * 
 * This creates a proper theme dropdown in the navbar that persists
 * across SPA navigation like the search bar and notifications.
 */

frappe.provide('construction.ui');

// Theme dropdown component
construction.ui.ThemeDropdown = class ThemeDropdown {
    constructor() {
        this.currentTheme = this.getCurrentTheme();
        this.themes = [
            // System themes: Construction Light/Dark only
            { 
                key: 'construction_light', 
                label: '☀️ Construction Light',
                doc_name: 'Construction Light',
                category: 'system'
            },
            { 
                key: 'construction_dark', 
                label: '🏗️ Construction Dark',
                doc_name: 'Construction Dark',
                category: 'system'
            }
        ];
        this._isSyncing = false;
        this.init();
    }
    
    getCurrentTheme() {
        // Priority: 1. DOM attribute (most reliable), 2. Server boot, 3. localStorage, 4. System preference
        // CRITICAL: Must return NORMALIZED key (e.g., 'construction_light') to match data-theme attributes
        // NOT display name (e.g., 'Construction Light') to prevent mismatch in switchTheme comparison

        var domModern = document.documentElement.getAttribute('data-modern-theme');
        var domBase = document.documentElement.getAttribute('data-theme');

        // Use DOM data-modern-theme first - return AS-IS (normalized key)
        if (domModern) {
            return domModern;
        }

        // 2. Check frappe.boot for server-side theme
        if (frappe.boot && frappe.boot.construction_theme) {
            var bootTheme = frappe.boot.construction_theme.theme || frappe.boot.construction_theme;
            return bootTheme.toLowerCase().replace(/\s+/g, '_');
        }

        // 3. Check localStorage (cache layer)
        if (localStorage.getItem('construction_active_theme')) {
            var savedTheme = localStorage.getItem('construction_active_theme');
            return savedTheme.toLowerCase().replace(/\s+/g, '_');
        }

        // Fall back to basic theme from DOM or system
        if (domBase) {
            return domBase;
        }

        if (localStorage.getItem('theme')) {
            return localStorage.getItem('theme');
        }

        // Default to system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    init() {
        // Bind events only once (prevents duplicate handlers on re-init)
        if (!this._eventsBound) {
            this.bindEvents();
            this.setupPageChangeListener();
            this._eventsBound = true;
        }
        this.addToNavbar();
        // Load custom themes dynamically from API
        this._loadCustomThemes();
    }
    
    addToNavbar() {
        // Prevent duplicate initialization
        if (window._themeDropdownInstance && window._themeDropdownInstance !== this) {
            // Another instance exists, just use that one
            return;
        }

        // Wait for navbar to be ready
        frappe.after_ajax(() => {
            this.injectDropdown();
        });

        // Also try immediately in case navbar is already there
        if (document.readyState === 'complete') {
            this.injectDropdown();
        } else {
            $(document).ready(() => this.injectDropdown());
        }
    }
    
    injectDropdown() {
        // Find the navbar right-side items container
        var $nav = $('.navbar-nav').last();
        if (!$nav.length) {
            // Try alternative selectors
            $nav = $('.nav.navbar-right');
        }
        if (!$nav.length) {
            setTimeout(() => this.injectDropdown(), 500);
            return;
        }
        
        // Remove existing theme dropdown if any
        $('#construction-theme-dropdown').remove();
        
        // Get current theme config (fallback to construction_light if not found)
        var current = this.themes.find(t => t.key === this.currentTheme) || this.themes[0];
        
        // Build dropdown HTML
        var dropdownHTML = `
            <li class="nav-item dropdown" id="construction-theme-dropdown">
                <a class="nav-link dropdown-toggle" href="#" 
                   data-toggle="dropdown" role="button" 
                   aria-expanded="false" style="padding: 8px 12px; display: flex; align-items: center; gap: 6px;">
                    <span class="theme-label d-none d-md-inline">${current.label}</span>
                </a>
                <ul class="dropdown-menu dropdown-menu-right" role="menu">
                    <li class="dropdown-header">Select Theme</li>
                    <li class="dropdown-divider"></li>
                    ${this.themes.map(theme => `
                        <li>
                            <a class="dropdown-item theme-option ${theme.key === this.currentTheme ? 'active' : ''}" 
                               href="#" 
                               data-theme="${theme.key}"
                               onclick="return false;">
                                ${theme.label}
                                ${theme.key === this.currentTheme ? '<i class="fa fa-check ml-2" style="margin-left: auto;"></i>' : ''}
                            </a>
                        </li>
                    `).join('')}
                </ul>
            </li>
        `;
        
        // Insert before the user menu (last item)
        var $userMenu = $nav.find('.dropdown-navbar-user');
        if ($userMenu.length) {
            $(dropdownHTML).insertBefore($userMenu);
        } else {
            $nav.append(dropdownHTML);
        }
        
        // Note: Events are now bound once in init(), not here
        // This prevents duplicate handlers when re-injecting
    }

    bindEvents() {
        var self = this;

        // CRITICAL: Unbind first to prevent duplicate handlers
        // This handles cases where init() is called multiple times
        $(document).off('click.themeDropdown', '.theme-option');
        $(document).off('click.themeDropdown');

        // Theme option click - use namespaced event
        $(document).on('click.themeDropdown', '.theme-option', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var theme = $(this).data('theme');
            self.switchTheme(theme);
        });

        // Close dropdown when clicking outside - use namespaced event
        $(document).on('click.themeDropdown', function(e) {
            if (!$(e.target).closest('#construction-theme-dropdown').length) {
                $('#construction-theme-dropdown .dropdown-menu').removeClass('show');
            }
        });
    }
    
    switchTheme(theme) {
        // Guard: prevent sync loops
        if (this._isSyncing) return;
        this._isSyncing = true;

        // CRITICAL: Normalize theme parameter to match currentTheme format
        // This handles both normalized keys ('construction_light') and display names ('Construction Light')
        var normalizedTheme = theme.toLowerCase().replace(/\s+/g, '_');
        
        // Prevent duplicate switches
        if (this._isSwitching || this.currentTheme === normalizedTheme) {
            this._isSyncing = false;
            return;
        }
        this._isSwitching = true;
        this.currentTheme = normalizedTheme;

        // Apply theme immediately (this will trigger events that update UI)
        this.applyTheme(theme);

        // CRITICAL: Update dropdown UI instantly (re-injects dropdown with new checkmark/label)
        this.updateDropdownUI();

        // Save to server (debounced to prevent duplicate API calls)
        this._debouncedSave(theme);

        // CRITICAL: Sync to Frappe native system
        // This prevents the two systems from diverging
        var frappeThemeName = normalizedTheme.includes('dark') ? 'Dark' : 'Light';
        frappe.call({
            method: 'frappe.core.doctype.user.user.switch_theme',
            args: {
                theme: frappeThemeName
            },
            callback: function(r) {
                // Frappe theme synced
            },
            error: function(err) {
                // Silent fail for theme sync
            }
        });

        // Show feedback
        frappe.show_alert({
            message: `Theme switched to ${this.themes.find(t => t.key === normalizedTheme)?.label || normalizedTheme}`,
            indicator: 'green'
        }, 3);

        // Reset flags after a short delay
        setTimeout(() => {
            this._isSwitching = false;
            this._isSyncing = false;
        }, 500);
    }

    _debouncedSave(theme) {
        // Clear any pending save
        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
        }
        // Debounce save to prevent duplicate API calls
        this._saveTimeout = setTimeout(() => {
            this.saveTheme(theme);
        }, 300);
    }
    
    applyTheme(theme) {
        var mode = theme.includes('dark') ? 'dark' : 'light';
        var isConstruction = theme.includes('construction');

        // applyTheme: theme + " (" + mode + ")"

        // Apply via ModernThemeLoader.setTheme() which handles all synchronization
        if (window.ModernThemeLoader && window.ModernThemeLoader.setTheme) {
            window.ModernThemeLoader.setTheme(theme);
        } else {
            // Fallback if loader not available
            document.documentElement.setAttribute('data-theme', mode);

            if (isConstruction) {
                document.documentElement.setAttribute('data-modern-theme', theme);
                localStorage.setItem('construction_active_theme', theme);
            } else {
                document.documentElement.removeAttribute('data-modern-theme');
                localStorage.removeItem('construction_active_theme');
            }

            localStorage.setItem('construction_mode', mode);
        }

        // Trigger theme change event for other components
        $(document).trigger('theme-change', { theme: theme, mode: mode });
    }
    
    updateDropdownUI() {
        // Update dropdown to reflect current theme

        // Find matching theme config
        var current = this.themes.find(t => t.key === this.currentTheme);

        // If no exact match, try partial match (construction_light contains light)
        if (!current && this.currentTheme) {
            var currentLower = this.currentTheme.toLowerCase();
            current = this.themes.find(t => currentLower.includes(t.key) || t.key.includes(currentLower));
        }

        // Final fallback: detect from theme name
        if (!current) {
            var isDark = this.currentTheme && this.currentTheme.toLowerCase().includes('dark');
            var detectedKey = isDark ? 'construction_dark' : 'construction_light';
            current = this.themes.find(t => t.key === detectedKey) || this.themes[0];
        }

        // UI updated: current.key

        // Close dropdown before re-injecting
        $('#construction-theme-dropdown .dropdown-menu').removeClass('show');

        // Re-inject dropdown for instant visual update (this ensures checkmarks update immediately)
        this.injectDropdown();
    }
    
    saveTheme(theme) {
        var self = this;
        var mode = theme.includes('dark') ? 'dark' : 'light';

        // Theme change: theme + " (" + mode + ")"    source: 'navbar_dropdown_save'
        });

        // Save to server using Construction Theme API (not Frappe's original)
        frappe.call({
            method: 'construction.api.theme_api.set_user_theme',
            args: {
                theme: theme,
                mode: mode
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    // Save mode to User.desk_theme (for Frappe compatibility)
                    frappe.call({
                        method: 'frappe.core.doctype.user.user.switch_theme',
                        args: { mode: mode },
                        callback: function(r2) {
                            // Mode saved to User.desk_theme
                        }
                    });
                } else {
                    // Fallback to localStorage
                    localStorage.setItem('construction_active_theme', theme);
                    localStorage.setItem('construction_mode', mode);
                }
            },
            error: function(err) {
                // Silent fail - fallback to localStorage
                localStorage.setItem('construction_active_theme', theme);
                localStorage.setItem('construction_mode', mode);
            }
        });
    }
    
    _loadCustomThemes() {
        var self = this;
        
        frappe.call({
            method: 'construction.api.theme_api.list_available_themes',
            args: {
                include_system: 0  // Only custom themes
            },
            callback: function(r) {
                if (r.message && r.message.themes && r.message.themes.length) {
                    r.message.themes.forEach(function(theme) {
                        if (theme.name !== 'Construction Light' && 
                            theme.name !== 'Construction Dark' &&
                            theme.theme_doc !== 'Construction Light' &&
                            theme.theme_doc !== 'Construction Dark') {
                            self.themes.push({
                                key: theme.name.toLowerCase().replace(/\s+/g, '_'),
                                label: theme.label || theme.name,
                                doc_name: theme.theme_doc || theme.name,
                                category: 'custom'
                            });
                        }
                    });
                    // Re-render dropdown if already shown
                    if ($('#construction-theme-dropdown').length) {
                        self.injectDropdown();
                    }
                }
            }
        });
    }
    
    setupPageChangeListener() {
        var self = this;

        // Use a flag to prevent duplicate handling
        this._processingEvent = false;

        // Listen for theme change events from ModernThemeLoader (Phase 3)
        // Store handler reference so we can check if already bound
        if (!this._themeAppliedHandler) {
            this._themeAppliedHandler = function(e) {
                if (self._processingEvent) return;
                if (e.detail && e.detail.theme_name) {
                    var newTheme = e.detail.theme_name;
                    if (self.currentTheme !== newTheme) {
                        self._processingEvent = true;
                        self.currentTheme = newTheme;
                        self.updateDropdownUI();
                        setTimeout(function() { self._processingEvent = false; }, 100);
                    }
                }
            };
            window.addEventListener('modern-theme-applied', this._themeAppliedHandler);
        }

        // Listen for jQuery theme-change event (from other components) - namespaced
        $(document).off('theme-change.themeDropdown').on('theme-change.themeDropdown', function(e, data) {
            if (self._processingEvent) return;
            if (data && data.theme) {
                var newTheme = data.theme;
                if (self.currentTheme !== newTheme) {
                    self._processingEvent = true;
                    self.currentTheme = newTheme;
                    self.updateDropdownUI();
                    setTimeout(function() { self._processingEvent = false; }, 100);
                }
            }
        });

        // Sync with Frappe's user menu toggle theme change - namespaced
        $(document).off('theme-change-end.themeDropdown').on('theme-change-end.themeDropdown', function(e, newTheme) {
            if (self._isSyncing || self._processingEvent) return;
            self._processingEvent = true;

            // Map Frappe theme to Construction theme
            var frappeTheme = newTheme || (frappe.boot && frappe.boot.theme) || 'light';
            var constructionTheme;

            if (frappeTheme === 'dark') {
                constructionTheme = 'construction_dark';
            } else {
                constructionTheme = 'construction_light';
            }

            // Update our state (but don't trigger another Frappe call to avoid loop)
            if (self.currentTheme !== constructionTheme) {
                self.currentTheme = constructionTheme;
                self.updateDropdownUI();

                // Apply Construction CSS without calling Frappe again
                if (window.ModernThemeLoader && window.ModernThemeLoader.setTheme) {
                    window.ModernThemeLoader.setTheme(constructionTheme);
                } else {
                    document.documentElement.setAttribute('data-modern-theme', constructionTheme);
                    document.documentElement.setAttribute('data-theme', frappeTheme === 'dark' ? 'dark' : 'light');
                }
            }

            setTimeout(function() { self._processingEvent = false; }, 200);
        });

        // Also listen for DOM mutations on data-theme as a backup sync mechanism
        var themeObserver = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                    if (self._isSyncing) return;
                    var newFrappeTheme = document.documentElement.getAttribute('data-theme');
                    var expectedConstruction = newFrappeTheme === 'dark' ? 'construction_dark' : 'construction_light';

                    if (self.currentTheme !== expectedConstruction) {
                        self.currentTheme = expectedConstruction;
                        self.updateDropdownUI();

                        // Also set data-modern-theme to match
                        document.documentElement.setAttribute('data-modern-theme', expectedConstruction);
                    }
                }
            });
        });

        themeObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme']
        });

        // Re-inject on every page change (SPA navigation) - namespaced
        $(document).off('page-change.themeDropdown').on('page-change.themeDropdown', function() {
            setTimeout(function() {
                self.injectDropdown();
                // Refresh current theme after injection (in case it changed)
                var detectedTheme = self.getCurrentTheme();
                if (self.currentTheme !== detectedTheme) {
                    self.currentTheme = detectedTheme;
                    self.updateDropdownUI();
                }
            }, 100);
        });

        // Also re-inject when toolbar is refreshed - namespaced
        $(document).off('toolbar-render.themeDropdown').on('toolbar-render.themeDropdown', function() {
            setTimeout(function() {
                self.injectDropdown();
            }, 100);
        });
    }
};

// Global instance reference to prevent duplicates
window._themeDropdownInstance = null;

// Initialize when Frappe is ready
$(document).ready(function() {
    // Wait for frappe to be fully loaded
    if (frappe && frappe.boot) {
        if (!window._themeDropdownInstance) {
            window._themeDropdownInstance = new construction.ui.ThemeDropdown();
        }
    } else {
        // Retry after a short delay
        setTimeout(function() {
            if (frappe && frappe.boot && !window._themeDropdownInstance) {
                window._themeDropdownInstance = new construction.ui.ThemeDropdown();
            }
        }, 1000);
    }
});

// Re-initialize on ajax complete (for dynamic page loads) - inject only, don't recreate
$(document).ajaxComplete(function() {
    if (window._themeDropdownInstance && !$('#construction-theme-dropdown').length && frappe && frappe.boot) {
        // Just re-inject the dropdown HTML, don't create new instance
        window._themeDropdownInstance.injectDropdown();
    }
});
