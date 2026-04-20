/**
 * Modern Theme Loader for ERPNext — Construction ERP
 * Phase 2: API-Driven Theme System
 * VERSION: 6.0 — 2026-04-18
 *
 * This file is the single source of truth for:
 * - Theme switching via API (server-side persistence)
 * - Dynamic CSS injection from Construction Theme records
 * - Server-side theme resolution (replaces localStorage)
 * - Navbar theme indicator with construction-aware labels
 * - MutationObserver for data-theme normalization
 * - Accessible theme change announcements (aria-live)
 * - TimestampMismatchError-safe persistence via API
 */
(function () {
  'use strict';

  var VERSION = '6.0';
  console.log(
    '%c[Modern Theme] LOADER v' + VERSION + ' — Phase 2 API-Driven — 20260418',
    'background:#2E7D32;color:#fff;padding:4px 8px;border-radius:4px;font-weight:bold'
  );

  // ─── 1. INLINE FALLBACK CSS INJECTION ───────────────────────────────
  // Minimal fallback CSS in case API fails
  var _css = document.createElement('style');
  _css.id = 'construction-theme-css';
  _css.textContent = [
    /* ── Base modern theme classes ── */
    '.modern-theme-loaded .page-head .btn-default.ellipsis,' +
      '.modern-theme-loaded .page-head .inner-group-button .btn-default,' +
      '.modern-theme-loaded .page-head .page-actions .btn-default' +
      '{border:1px solid var(--border-color)!important;border-radius:10px!important;font-size:.8rem!important;font-weight:500!important;padding:6px 14px!important;min-height:36px!important;transition:all .25s cubic-bezier(.4,0,.2,1)!important;background:var(--surface)!important;color:var(--text-primary)!important;box-shadow:0 1px 3px rgba(0,0,0,.06)!important}',
    '.modern-theme-loaded .page-head .btn-default.ellipsis:hover,' +
      '.modern-theme-loaded .page-head .inner-group-button .btn-default:hover,' +
      '.modern-theme-loaded .page-head .page-actions .btn-default:hover' +
      '{background:var(--hover-bg)!important;border-color:var(--accent)!important;color:var(--accent)!important;transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(0,0,0,.1)!important}',
    '.modern-theme-loaded .tree-toolbar-button{border:1px solid var(--border-color)!important;border-radius:8px!important;font-size:.78rem!important;font-weight:500!important;padding:4px 12px!important;min-height:28px!important;transition:all .2s ease!important;background:var(--surface)!important;color:var(--text-primary)!important;margin:0 3px!important}',
    '.modern-theme-loaded .tree-toolbar-button:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important;color:var(--accent)!important;transform:translateY(-1px)!important}',
    '.modern-theme-loaded .tree-toolbar-button:last-child:hover{border-color:var(--error)!important;color:var(--error)!important;background:rgba(222,63,63,.06)!important}',
    '.modern-theme-loaded .page-head .primary-action{border-radius:10px!important}',
    '.modern-theme-loaded .page-head .primary-action:hover{transform:translateY(-1px)!important}',
    '.modern-theme-loaded .page-head .icon-btn{border:1px solid var(--border-color)!important;border-radius:10px!important;background:var(--surface)!important}',
    '.modern-theme-loaded .page-head .icon-btn:hover{background:var(--hover-bg)!important;border-color:var(--accent)!important}',
    '.modern-theme-loaded .btn-default:focus-visible,' +
      '.modern-theme-loaded .tree-toolbar-button:focus-visible,' +
      '.modern-theme-loaded .navbar .nav-link:focus-visible,' +
      '.modern-theme-loaded .desk-sidebar-item a:focus-visible' +
      '{outline:2px solid var(--accent);outline-offset:2px}',
    '@media(prefers-reduced-motion:reduce){.modern-theme-loaded,.modern-theme-loaded *{transition-duration:.001ms!important;animation-duration:.001ms!important}.modern-theme-loaded .btn-default:hover,.modern-theme-loaded .tree-toolbar-button:hover{transform:none!important}#theme-mode-dot{box-shadow:none!important}}'
  ].join('\n');
  document.head.appendChild(_css);

  // ─── 2. THEME LOADER OBJECT ────────────────────────────────────────

  var ModernThemeLoader = {
    currentTheme: null,
    currentMode: null,
    currentThemeDoc: null,
    isConstruction: false,
    version: VERSION,
    cssCache: {}, // Client-side cache for generated CSS

    init: function () {
      console.log('[Modern Theme v' + this.version + '] Initializing (API-driven)...');
      if (typeof frappe === 'undefined') {
        setTimeout(function () { ModernThemeLoader.init(); }, 100);
        return;
      }

      this.applyTheme();
      this.watchThemeChanges();
      this.injectCSSVariables();
    },

    // ─── 3. THEME APPLICATION (API-DRIVEN) ─────────────────────────────

    applyTheme: function (forcedMode) {
      var self = this;
      var currentDomMode = document.documentElement.getAttribute('data-theme');
      var modeToSend = forcedMode || currentDomMode || 'light';

      frappe.call({
        method: 'construction.api.theme_api.get_effective_desk_theme',
        args: { current_mode: modeToSend },
        callback: function (r) {
          if (!r.message) return;
          var data = r.message;
          
          self.currentTheme = data.theme_name;
          self.currentMode = data.mode;
          self.currentThemeDoc = data.theme_doc;
          self.isConstruction = data.is_construction;

          document.documentElement.setAttribute('data-theme', data.mode);

          if (data.is_construction && data.theme_doc) {
            document.documentElement.setAttribute('data-modern-theme', data.theme_doc);
            if (data.needs_css_injection) {
              self.fetchAndInjectCSS(data.theme_doc);
            }
            // Apply feature toggles synchronously before DOMContentLoaded
            self.applyFeatureToggles(data.feature_toggles || {});
          } else {
            document.documentElement.removeAttribute('data-modern-theme');
            // Clear feature toggles for non-construction themes
            self.applyFeatureToggles({});
          }

          self.updateNavbarIndicator(data.mode);
          window.dispatchEvent(new CustomEvent('modern-theme-applied', {
            detail: data
          }));
        },
        error: function () {
          // Fallback to default theme on API error
          if (forcedMode) {
            document.documentElement.setAttribute('data-theme', forcedMode);
            self.currentMode = forcedMode;
            self.updateNavbarIndicator(forcedMode);
          }
        }
      });
    },

    // ─── 4. DYNAMIC CSS INJECTION FROM API ────────────────────────────

    fetchAndInjectCSS: function (themeDoc) {
      var self = this;
      
      // Check client-side cache first
      if (self.cssCache[themeDoc]) {
        self.injectCSS(self.cssCache[themeDoc], themeDoc);
        return;
      }

      frappe.call({
        method: 'construction.api.theme_api.get_theme_css',
        args: { theme_name: themeDoc },
        callback: function (r) {
          if (r.message && r.message.css) {
            var css = r.message.css;
            
            // Cache in memory
            self.cssCache[themeDoc] = css;
            
            // Inject into DOM
            self.injectCSS(css, themeDoc);
          }
        },
        error: function () {
          console.warn('[Modern Theme] Failed to fetch CSS for ' + themeDoc);
          // Fallback: use inline CSS already in DOM
        }
      });
    },

    injectCSS: function (css, themeDoc) {
      var elId = 'theme-css-' + themeDoc.replace(/\s+/g, '-').toLowerCase();
      
      // Remove existing theme CSS
      var existing = document.getElementById(elId);
      if (existing) {
        existing.remove();
      }
      
      // Create new style element
      var style = document.createElement('style');
      style.id = elId;
      style.setAttribute('data-theme-source', 'api');
      style.textContent = css;
      document.head.appendChild(style);
      
      console.log('[Modern Theme] CSS injected for: ' + themeDoc);
    },

    // ─── 5. THEME CHANGE WATCHER ───────────────────────────────────────

    watchThemeChanges: function () {
      var self = this;

      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
          self.applyTheme(e.matches ? 'dark' : 'light');
        });
      }

      var observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          if (mutations[i].attributeName === 'data-theme') {
            var rawMode = document.documentElement.getAttribute('data-theme');
            var oldMode = self.currentMode;

            // Normalize construction_* → set data-modern-theme + rewrite to light/dark
            if (rawMode === 'construction_light' || rawMode === 'construction_dark') {
              var normalized = rawMode === 'construction_light' ? 'light' : 'dark';
              document.documentElement.setAttribute('data-modern-theme', rawMode);
              document.documentElement.setAttribute('data-theme', normalized);
              return; // will re-trigger observer with normalized value
            }

            if (rawMode && rawMode !== oldMode) {
              self.persistModePreference(rawMode);
              self.applyTheme(rawMode);
            }
          }
        }
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    },

    // ─── 6. SERVER-SIDE PERSISTENCE ──────────────────────────────────

    persistModePreference: function (mode) {
      frappe.call({
        method: 'construction.api.theme_api.save_user_mode',
        args: { mode: mode },
        callback: function (r) {
          if (r.message && r.message.success) {
            console.log('[Modern Theme] Persisted mode: ' + mode);
          }
        },
        error: function () { /* non-critical */ }
      });
    },

    persistThemePreference: function (themeDoc, mode) {
      frappe.call({
        method: 'construction.api.theme_api.set_user_theme',
        args: { theme: themeDoc, mode: mode },
        callback: function (r) {
          if (r.message && r.message.success) {
            console.log('[Modern Theme] Persisted theme: ' + themeDoc);
          }
        },
        error: function () { /* non-critical */ }
      });
    },

    // ─── 7. CSS VARIABLES & BODY CLASS ─────────────────────────────────

    injectCSSVariables: function () {
      document.body.classList.add('modern-theme-loaded');
      this.injectNavbarIndicator();
    },

    // ─── 7b. FEATURE TOGGLES ──────────────────────────────────────────

    applyFeatureToggles: function (toggles) {
      /**
       * Apply feature toggle body classes based on theme configuration.
       * Removes all existing ct-theme-* classes before applying new ones.
       * 
       * Mapping:
       * - hide_help_button → ct-theme-hide-help
       * - hide_search_bar → ct-theme-hide-search
       * - hide_sidebar → ct-theme-hide-sidebar
       * - hide_like_comment → ct-theme-hide-like-comment
       * - mobile_card_view → ct-theme-mobile-card
       */
      if (!toggles) toggles = {};

      // Remove all existing ct-theme-* classes
      var classes = document.body.className.split(' ');
      classes = classes.filter(function (c) { return !c.startsWith('ct-theme-'); });
      document.body.className = classes.join(' ').trim();

      // Apply new toggles
      var TOGGLE_MAP = {
        'hide_help_button': 'ct-theme-hide-help',
        'hide_search_bar': 'ct-theme-hide-search',
        'hide_sidebar': 'ct-theme-hide-sidebar',
        'hide_like_comment': 'ct-theme-hide-like-comment',
        'mobile_card_view': 'ct-theme-mobile-card'
      };

      for (var field in TOGGLE_MAP) {
        if (toggles[field]) {
          document.body.classList.add(TOGGLE_MAP[field]);
        }
      }

      console.log('[Modern Theme] Feature toggles applied:', toggles);
    },

    // ─── 8. NAVBAR INDICATOR ──────────────────────────────────────────

    injectNavbarIndicator: function () {
      var self = this;
      var check = setInterval(function () {
        var nav = document.querySelector('.navbar-nav') || document.querySelector('.nav.navbar-right');
        if (nav && !document.getElementById('modern-theme-indicator')) {
          clearInterval(check);

          var mt = document.documentElement.getAttribute('data-modern-theme');
          var isCon = mt && self.isConstruction;
          var isDark = self.currentMode === 'dark';
          var label = isCon
            ? (isDark ? '🏗️ Construction Dark' : '🏗️ Construction Light')
            : (isDark ? '🌙 Dark' : '☀️ Light');
          var dotColor = isCon ? self.getThemeAccent() : (isDark ? '#60a5fa' : '#fbbf24');

          var li = document.createElement('li');
          li.id = 'modern-theme-indicator';
          li.className = 'nav-item dropdown';
          li.innerHTML =
            '<a class="nav-link" href="#" style="display:flex;align-items:center;padding:8px 12px;border-radius:20px;background:var(--hover-bg,rgba(0,0,0,.05));margin:0 8px;" onclick="return false;">'
            + '<span id="theme-mode-dot" style="width:10px;height:10px;border-radius:50%;background:' + dotColor + ';box-shadow:0 0 8px ' + dotColor + ';margin-right:8px;transition:all .3s ease;"></span>'
            + '<span id="theme-mode-text" style="font-size:.85rem;font-weight:500;">' + label + '</span>'
            + '</a>';

          var um = nav.querySelector('.dropdown-navbar-user');
          if (um) { nav.insertBefore(li, um); } else { nav.appendChild(li); }
          console.log('[Modern Theme] Navbar indicator injected');

          // Aria-live announcer for screen readers
          if (!document.getElementById('theme-change-announcer')) {
            var ann = document.createElement('div');
            ann.id = 'theme-change-announcer';
            ann.setAttribute('aria-live', 'polite');
            ann.setAttribute('role', 'status');
            ann.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;';
            document.body.appendChild(ann);
          }
        }
      }, 500);
      setTimeout(function () { clearInterval(check); }, 10000);
    },

    getThemeAccent: function () {
      // Try to get accent from CSS variables
      var root = document.documentElement;
      var computed = getComputedStyle(root);
      var accent = computed.getPropertyValue('--accent-primary').trim();
      return accent || '#4CAF50';
    },

    updateNavbarIndicator: function (mode) {
      var dot = document.getElementById('theme-mode-dot');
      var text = document.getElementById('theme-mode-text');
      if (!dot || !text) return;

      var mt = document.documentElement.getAttribute('data-modern-theme');
      var isCon = mt && this.isConstruction;
      var isDark = mode === 'dark';

      var label, dotColor;
      if (isCon) {
        label = isDark ? '🏗️ Construction Dark' : '🏗️ Construction Light';
        dotColor = this.getThemeAccent();
      } else {
        label = isDark ? '🌙 Dark' : '☀️ Light';
        dotColor = isDark ? '#60a5fa' : '#fbbf24';
      }

      dot.style.background = dotColor;
      dot.style.boxShadow = '0 0 8px ' + dotColor;
      text.textContent = label;

      // Announce to screen readers
      var ann = document.getElementById('theme-change-announcer');
      if (ann) {
        ann.textContent = '';
        setTimeout(function () { ann.textContent = 'Theme changed to ' + label; }, 100);
      }
    },

    // ─── 9. UTILITIES ──────────────────────────────────────────────────

    getCurrentTheme: function () {
      return {
        theme: this.currentTheme,
        mode: this.currentMode,
        themeDoc: this.currentThemeDoc,
        isConstruction: this.isConstruction
      };
    },

    refresh: function () {
      // Clear client cache and reload
      this.cssCache = {};
      this.applyTheme();
    },

    clearCache: function () {
      this.cssCache = {};
      console.log('[Modern Theme] Client CSS cache cleared');
    }
  };

  window.ModernThemeLoader = ModernThemeLoader;

  // ─── 3. EARLY THEME SWITCHER OVERRIDE ─────────────────────────────
  // This must run BEFORE frappe initializes ThemeSwitcher
  
  function setupThemeSwitcherOverride() {
    // Wait for frappe to be available
    if (typeof frappe === 'undefined' || !frappe.ui) {
      setTimeout(setupThemeSwitcherOverride, 50);
      return;
    }
    
    // Check if ThemeSwitcher exists yet
    if (!frappe.ui.ThemeSwitcher) {
      // ThemeSwitcher hasn't been defined by Frappe yet
      // Set up a proxy to intercept when it's defined
      var ThemeSwitcherProxy = new Proxy(function() {}, {
        construct: function(target, args) {
          // When Frappe tries to create ThemeSwitcher, use our custom one
          return new CustomThemeSwitcher(...args);
        }
      });
      
      // Define our custom ThemeSwitcher class
      var CustomThemeSwitcher = class extends (frappe.ui.Dialog || function() {}) {
        constructor(opts) {
          super(opts || {});
          this.themes = [
            { name: 'light', label: '☀️ Light', info: 'Frappe Light Theme' },
            { name: 'dark', label: '🌙 Dark', info: 'Frappe Dark Theme' },
            { name: 'automatic', label: '⚡ Automatic', info: 'Follows system preference' }
          ];
          this.setup_themes = this.setupThemes.bind(this);
        }
        
        setupThemes() {
          var self = this;
          // Fetch construction themes from API
          frappe.call({
            method: 'construction.api.theme_api.list_available_themes',
            callback: function(r) {
              if (r.message && r.message.success && r.message.themes) {
                // Add construction themes
                var constructionThemes = r.message.themes.map(function(t) {
                  return {
                    name: t.name,
                    label: t.label || (t.emoji_icon + ' ' + t.theme_name),
                    info: t.info || t.description || t.theme_type,
                    is_construction: true,
                    theme_doc: t.theme_doc || t.name,
                    preview_colors: t.preview_colors || []
                  };
                });
                self.themes = constructionThemes.concat(self.themes);
              }
              self.render_themes();
            },
            error: function() {
              self.render_themes();
            }
          });
        }
        
        render_themes() {
          var self = this;
          this.$body.empty();
          this.themes.forEach(function(theme) {
            var $item = $(`<div class="theme-item" data-theme="${theme.name}">
              <div class="theme-label">${theme.label}</div>
              <div class="theme-info">${theme.info || ''}</div>
            </div>`);
            $item.on('click', function() {
              self.switch_theme(theme.name);
            });
            self.$body.append($item);
          });
        }
        
        switch_theme(theme_name) {
          if (!theme_name) return;
          
          var targetMode = 'light';
          var themeDoc = null;
          var isConstruction = false;
          
          if (theme_name === 'dark') {
            targetMode = 'dark';
          } else if (theme_name === 'light') {
            targetMode = 'light';
          } else if (theme_name === 'automatic') {
            targetMode = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
          } else {
            // Check if it's a construction theme
            var theme = this.themes.find(function(t) { return t.name === theme_name; });
            if (theme && theme.is_construction) {
              isConstruction = true;
              themeDoc = theme.theme_doc;
              targetMode = theme_name.toLowerCase().indexOf('dark') !== -1 ? 'dark' : 'light';
            }
          }
          
          // Apply theme
          document.documentElement.setAttribute('data-theme', targetMode);
          ModernThemeLoader.currentMode = targetMode;
          
          if (isConstruction && themeDoc) {
            document.documentElement.setAttribute('data-modern-theme', themeDoc);
            ModernThemeLoader.currentTheme = theme_name;
            ModernThemeLoader.currentThemeDoc = themeDoc;
            ModernThemeLoader.isConstruction = true;
            ModernThemeLoader.fetchAndInjectCSS(themeDoc);
            ModernThemeLoader.persistThemePreference(themeDoc, targetMode);
          } else {
            document.documentElement.removeAttribute('data-modern-theme');
            ModernThemeLoader.currentTheme = theme_name;
            ModernThemeLoader.currentThemeDoc = null;
            ModernThemeLoader.isConstruction = false;
            ModernThemeLoader.persistModePreference(targetMode);
          }
          
          ModernThemeLoader.updateNavbarIndicator(targetMode);
          this.hide();
        }
      };
      
      // Assign our custom class to frappe.ui.ThemeSwitcher
      frappe.ui.ThemeSwitcher = CustomThemeSwitcher;
      console.log('[Modern Theme] ThemeSwitcher override applied early');
    } else {
      // ThemeSwitcher already exists - patch it
      var OriginalThemeSwitcher = frappe.ui.ThemeSwitcher;
      var OriginalFetchThemes = OriginalThemeSwitcher.prototype.fetch_themes;
      var OriginalSwitchTheme = OriginalThemeSwitcher.prototype.switch_theme;
      
      // Override fetch_themes - clear existing themes first to avoid duplicates
      OriginalThemeSwitcher.prototype.fetch_themes = function() {
        var self = this;
        // Clear any existing themes to prevent duplicates
        self.themes = [];
        
        return new Promise(function(resolve) {
          frappe.call({
            method: 'construction.api.theme_api.list_available_themes',
            callback: function(r) {
              // Start fresh with empty array
              var themes = [];
              
              if (r.message && r.message.success && r.message.themes) {
                var constructionThemes = r.message.themes.map(function(t) {
                  return {
                    name: t.name,
                    label: t.label || (t.emoji_icon + ' ' + t.theme_name),
                    info: t.info || t.description || t.theme_type,
                    is_construction: true,
                    theme_doc: t.theme_doc || t.name
                  };
                });
                themes = constructionThemes;
              }
              
              // Add Frappe native themes at the end
              themes.push(
                { name: 'automatic', label: '⚡ Automatic', info: 'Follows system preference' },
                { name: 'dark', label: '🌙 Dark', info: 'Frappe Dark Theme' },
                { name: 'light', label: '☀️ Light', info: 'Frappe Light Theme' }
              );
              
              self.themes = themes;
              resolve(self.themes);
            },
            error: function() {
              // Fallback to default themes only
              self.themes = [
                { name: 'light', label: '☀️ Light', info: 'Frappe Light Theme' },
                { name: 'dark', label: '🌙 Dark', info: 'Frappe Dark Theme' },
                { name: 'automatic', label: '⚡ Automatic', info: 'Follows system preference' }
              ];
              resolve(self.themes);
            }
          });
        });
      };
      
      // Override switch_theme with error handling and construction theme support
      OriginalThemeSwitcher.prototype.switch_theme = function(theme_name) {
        if (!theme_name) {
          console.warn('[Modern Theme] No theme name provided');
          return;
        }
        
        console.log('[Modern Theme] Switching to:', theme_name);
        
        var targetMode = 'light';
        var themeDoc = null;
        var isConstruction = false;
        
        var themeNameLower = theme_name.toLowerCase ? theme_name.toLowerCase() : String(theme_name);
        
        // Check if it's a construction theme first (before standard themes)
        var theme = this.themes ? this.themes.find(function(t) { return t && t.name === theme_name; }) : null;
        
        if (theme && theme.is_construction) {
          isConstruction = true;
          themeDoc = theme.theme_doc || theme.name;
          targetMode = themeNameLower.indexOf('dark') !== -1 ? 'dark' : 'light';
          console.log('[Modern Theme] Construction theme detected:', themeDoc, 'mode:', targetMode);
        } else if (themeNameLower === 'dark') {
          targetMode = 'dark';
        } else if (themeNameLower === 'light') {
          targetMode = 'light';
        } else if (themeNameLower === 'automatic') {
          targetMode = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
        }
        
        // Apply theme
        document.documentElement.setAttribute('data-theme', targetMode);
        ModernThemeLoader.currentMode = targetMode;
        
        if (isConstruction && themeDoc) {
          document.documentElement.setAttribute('data-modern-theme', themeDoc);
          ModernThemeLoader.currentTheme = theme_name;
          ModernThemeLoader.currentThemeDoc = themeDoc;
          ModernThemeLoader.isConstruction = true;
          console.log('[Modern Theme] Injecting CSS for construction theme:', themeDoc);
          ModernThemeLoader.fetchAndInjectCSS(themeDoc);
          ModernThemeLoader.persistThemePreference(themeDoc, targetMode);
        } else {
          document.documentElement.removeAttribute('data-modern-theme');
          ModernThemeLoader.currentTheme = theme_name;
          ModernThemeLoader.currentThemeDoc = null;
          ModernThemeLoader.isConstruction = false;
          ModernThemeLoader.persistModePreference(targetMode);
          console.log('[Modern Theme] Standard theme applied:', theme_name);
        }
        
        ModernThemeLoader.updateNavbarIndicator(targetMode);
        if (this.hide) this.hide();
      };
      
      console.log('[Modern Theme] ThemeSwitcher patched');
      
      // Mark as patched so we can detect if Frappe overwrites it
      OriginalThemeSwitcher.prototype._modernThemePatched = true;
      OriginalThemeSwitcher.prototype._modernThemeVersion = VERSION;
    }
  }
  
  // Start the override setup immediately
  setupThemeSwitcherOverride();
  
  // DEFERRED PATCH: Wait for Frappe's desk bundle to load, then patch again
  // This is necessary because Frappe's theme_switcher.js loads in the desk bundle
  // and overwrites our patch. We need to patch AFTER it loads.
  function deferredPatch() {
    if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.ThemeSwitcher) {
      // Check if our patch is still active by looking for our custom property
      if (!frappe.ui.ThemeSwitcher.prototype._modernThemePatched) {
        console.log('[Modern Theme] Frappe desk bundle loaded, re-applying patch...');
        setupThemeSwitcherOverride();
      }
    }
    // Keep checking periodically
    setTimeout(deferredPatch, 1000);
  }
  
  // Start deferred patching after a short delay to let initial load complete
  setTimeout(deferredPatch, 3000);

  // ─── 10. INIT ─────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { 
      ModernThemeLoader.init();
    });
  } else {
    setTimeout(function () { 
      ModernThemeLoader.init();
    }, 0);
  }

  // ─── 11. REALTIME UPDATES ───────────────────────────────────────────
  // Listen for theme updates from server (when admin changes a theme)
  if (typeof frappe !== 'undefined' && frappe.realtime) {
    frappe.realtime.on('theme_updated', function (data) {
      console.log('[Modern Theme] Theme updated on server:', data.theme);
      ModernThemeLoader.clearCache();
      if (ModernThemeLoader.currentThemeDoc === data.theme) {
        ModernThemeLoader.fetchAndInjectCSS(data.theme);
      }
    });
  }

})();
