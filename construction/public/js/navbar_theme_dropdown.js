/**
 * Navbar Theme Dropdown Selector for Frappe v16 — Construction ERP
 * VERSION: 1.0 — Persistent Dropdown in Navbar
 * 
 * This creates a proper theme dropdown in the navbar that persists
 * across SPA navigation like the search bar and notifications.
 */

frappe.provide('construction.ui');

// Cookie helpers for login page theme persistence
window.setCookie = function(name, value, days) {
    var expires = '';
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = '; expires=' + date.toUTCString();
    }
    document.cookie = name + '=' + value + expires + '; path=/; SameSite=Lax';
};

// Theme dropdown component
construction.ui.ThemeDropdown = class ThemeDropdown {
    constructor() {
        console.log('[ThemeDropdown] Constructor called');
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
        console.log('[ThemeDropdown] Constructor initial currentTheme:', this.currentTheme);
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

        // 4. Check data-theme attribute (from Frappe)
        var domBase = document.documentElement.getAttribute('data-theme');
        if (domBase) {
            // Map basic theme keys to construction themes
            if (domBase === 'dark') return 'construction_dark';
            if (domBase === 'light') return 'construction_light';
            return domBase;
        }
        
        // 5. System preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'construction_dark';
        }
        
        return 'construction_light';
    }
    
    init() {
        console.log('[ThemeDropdown] Initializing...');
        
        // Bind events only once (prevents duplicate handlers on re-init)
        if (!this._eventsBound) {
            this.setupPageChangeListener();
            this._eventsBound = true;
            console.log('[ThemeDropdown] Events bound, _eventsBound:', this._eventsBound);
        }
        this.addToNavbar();
        // Load custom themes dynamically from API
        this._loadCustomThemes();
        
        // Also set up a fallback global click listener
        this.setupGlobalClickHandler();
    }
    
    setupGlobalClickHandler() {
        var self = this;
        // Global handler for theme-option clicks - use jQuery for compatibility
        $(document).on('click.construction-theme', '.theme-option', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var theme = $(this).data('theme') || $(this).attr('data-theme');
            console.log('[ThemeDropdown] Global click handler:', theme);
            if (theme) {
                self.switchTheme(theme);
            }
        });
        
        // Fix for Frappe user menu items that might be greyed out
        this.fixUserMenuItems();
    }
    
    fixUserMenuItems() {
        // Ensure user menu dropdown items are clickable
        var self = this;
        
        // Fix items when user menu dropdown is shown
        $(document).on('shown.bs.dropdown', '.dropdown-navbar-user', function() {
            console.log('[ThemeDropdown] User menu opened, ensuring items are clickable');
            self.enableUserMenuItems();
        });
        
        // Also fix items when navbar is clicked
        $(document).on('click', '.dropdown-navbar-user .dropdown-toggle', function() {
            setTimeout(function() {
                self.enableUserMenuItems();
            }, 50);
        });
        
        // Watch for any dynamic changes that might disable items
        if (window.MutationObserver) {
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        var target = $(mutation.target);
                        if (target.hasClass('disabled') || target.css('pointer-events') === 'none') {
                            console.log('[ThemeDropdown] Detected disabled item, re-enabling:', target.text().trim());
                            target.removeClass('disabled').css({
                                'pointer-events': 'auto',
                                'opacity': '1',
                                'cursor': 'pointer'
                            });
                        }
                    }
                });
            });
            
            // Start observing when toolbar-user is available
            var observeUserMenu = function() {
                var userMenu = document.getElementById('toolbar-user');
                if (userMenu) {
                    observer.observe(userMenu, {
                        attributes: true,
                        subtree: true,
                        attributeFilter: ['class', 'style']
                    });
                    console.log('[ThemeDropdown] MutationObserver started for user menu');
                } else {
                    setTimeout(observeUserMenu, 500);
                }
            };
            observeUserMenu();
        }
        
        // Fix for modal dialogs (ThemeSwitcher, Logout confirmation)
        this.fixModalDialogs();
    }
    
    fixModalDialogs() {
        // Ensure modal content is always clickable
        $(document).on('shown.bs.modal', function() {
            console.log('[ThemeDropdown] Modal shown, ensuring content is clickable');
            $('.modal-content, .modal-dialog, .modal-body').css({
                'pointer-events': 'auto',
                'z-index': '1055'
            });
            // Make backdrop non-clickable (it should just be visual)
            $('.modal-backdrop').css('pointer-events', 'none');
        });
        
        // Also watch for Frappe dialogs
        $(document).on(' frappe.ui.Dialog:shown', function() {
            console.log('[ThemeDropdown] Frappe dialog shown, ensuring content is clickable');
            $('.modal-dialog, .dialog-box').css({
                'pointer-events': 'auto',
                'z-index': '1055'
            });
        });
    }
    
    enableUserMenuItems() {
        // Remove any disabled attributes or classes from user menu items
        $('#toolbar-user .dropdown-item, #toolbar-user button, #toolbar-user a').each(function() {
            var $item = $(this);
            // Remove disabled class if present
            $item.removeClass('disabled');
            // Remove disabled attribute from buttons
            if ($item.is('button')) {
                $item.prop('disabled', false);
                $item.removeAttr('disabled');
            }
            // Force remove any inline styles that might disable
            var style = $item.attr('style') || '';
            if (style.includes('pointer-events') && style.includes('none')) {
                $item.attr('style', style.replace(/pointer-events:\s*none;?/gi, ''));
            }
            // Ensure pointer events are enabled
            $item.css({
                'pointer-events': 'auto',
                'opacity': '1',
                'cursor': 'pointer',
                'visibility': 'visible'
            });
            // Log for debugging
            var itemText = $item.text().trim() || $item.attr('onclick') || 'divider';
            console.log('[ThemeDropdown] Fixed user menu item:', itemText, '- disabled attr:', $item.prop('disabled'), 'classes:', $item.attr('class'));
        });
        
        // Also force re-enable via DOM manipulation for any stubborn items
        var allItems = document.querySelectorAll('#toolbar-user .dropdown-item, #toolbar-user button');
        allItems.forEach(function(item) {
            item.disabled = false;
            item.classList.remove('disabled');
            item.style.pointerEvents = 'auto';
            item.style.opacity = '1';
            item.style.cursor = 'pointer';
        });
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
        console.log('[ThemeDropdown] Looking for navbar. Found .navbar-nav:', $nav.length);
        if (!$nav.length) {
            // Try alternative selectors
            $nav = $('.nav.navbar-right');
            console.log('[ThemeDropdown] Trying .nav.navbar-right:', $nav.length);
        }
        if (!$nav.length) {
            console.log('[ThemeDropdown] Navbar not found, retrying in 500ms');
            setTimeout(() => this.injectDropdown(), 500);
            return;
        }
        
        // Remove existing theme dropdown if any
        $('#construction-theme-dropdown').remove();
        console.log('[ThemeDropdown] Injecting dropdown into navbar:', $nav.length > 0);
        
        // Get current theme config (fallback to construction_light if not found)
        var current = this.themes.find(t => t.key === this.currentTheme) || this.themes[0];
        
        // Build dropdown HTML - use BUTTON elements with direct onclick
        var dropdownHTML = `
            <li class="nav-item dropdown" id="construction-theme-dropdown">
                <a class="nav-link dropdown-toggle" href="javascript:void(0);" 
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
                               data-theme="${theme.key}">
                                ${theme.label}
                            </a>
                        </li>
                    `).join('')}
                </ul>
            </li>
        `;
        
        // Actually insert the dropdown HTML into the navbar
        $nav.append(dropdownHTML);
        console.log('[ThemeDropdown] Dropdown HTML appended. Element exists:', $('#construction-theme-dropdown').length > 0);
        console.log('[ThemeDropdown] Navbar children count:', $nav.children().length);
        
        // Manually trigger dropdown toggle to ensure it works
        $('#construction-theme-dropdown .dropdown-toggle').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var $menu = $('#construction-theme-dropdown .dropdown-menu');
            $menu.toggleClass('show');
            console.log('[ThemeDropdown] Toggle clicked, menu show:', $menu.hasClass('show'));
        });
        
        // Close dropdown when clicking outside
        $(document).on('click', function(e) {
            if (!$(e.target).closest('#construction-theme-dropdown').length) {
                $('#construction-theme-dropdown .dropdown-menu').removeClass('show');
            }
        });
    }
    
    switchTheme(theme) {
        console.log('[ThemeDropdown] switchTheme called with:', theme);
        
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
        var themeLabel = this.themes.find(t => t.key === normalizedTheme);
        frappe.show_alert({
            message: `Theme switched to ${(themeLabel && themeLabel.label) || normalizedTheme}`,
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
        console.log('[ThemeDropdown] applyTheme called with:', theme);
        
        var mode = theme.includes('dark') ? 'dark' : 'light';
        var isConstruction = theme.includes('construction');

        console.log('[ThemeDropdown] mode:', mode, 'isConstruction:', isConstruction);
        console.log('[ThemeDropdown] ModernThemeLoader available:', !!window.ModernThemeLoader);
        console.log('[ThemeDropdown] ModernThemeLoader.setTheme available:', !!(window.ModernThemeLoader && window.ModernThemeLoader.setTheme));


        // Apply via ModernThemeLoader.setTheme() which handles all synchronization
        if (window.ModernThemeLoader && window.ModernThemeLoader.setTheme) {
            console.log('[ThemeDropdown] Calling ModernThemeLoader.setTheme(theme)');
            window.ModernThemeLoader.setTheme(theme);
            console.log('[ThemeDropdown] ModernThemeLoader.setTheme returned');
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


        // Close dropdown before re-injecting
        $('#construction-theme-dropdown .dropdown-menu').removeClass('show');

        // Re-inject dropdown for instant visual update (this ensures checkmarks update immediately)
        this.injectDropdown();
    }
    
    saveTheme(theme) {
        var self = this;
        var mode = theme.includes('dark') ? 'dark' : 'light';

        // Save to server using Construction Theme API (not Frappe's original)
        frappe.call({
            method: 'construction.api.theme_api.set_user_theme',
            args: {
                theme: theme,
                mode: mode
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    // Set cookie for login page persistence
                    setCookie('construction_theme_mode', mode, 365);
                    localStorage.setItem('construction_active_theme', theme);
                    localStorage.setItem('construction_theme', theme);
                    
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

                // NOTE: Do NOT call setTheme here - it overrides localStorage preference.
                // Only update DOM attributes for visual sync without triggering CSS reload
                document.documentElement.setAttribute('data-modern-theme', constructionTheme);
                document.documentElement.setAttribute('data-theme', frappeTheme === 'dark' ? 'dark' : 'light');
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

// Check if we're on the login page
function isLoginPage() {
    return window.location.pathname === '/login' || 
           document.querySelector('.form-login') !== null ||
           document.querySelector('.page-card .form-signin') !== null ||
           (typeof frappe !== 'undefined' && frappe.boot && frappe.boot.user && frappe.boot.user.name === 'Guest');
}

// Initialize when Frappe is ready
$(document).ready(function() {
    // Skip initialization on login page
    if (isLoginPage()) {
        console.log('[ThemeDropdown] Login page detected, skipping initialization');
        return;
    }
    
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
