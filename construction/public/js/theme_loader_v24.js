/**
 * Construction Theme Loader v2.9
 * CRITICAL: Runs synchronously BEFORE DOMContentLoaded
 * to win the race against Frappe's desk.js set_theme()
 * v2.9: Added BaseChart/ResizeObserver infinite-loop guard
 */

(function() {
  'use strict';

  var html = document.documentElement;
  var path = window.location.pathname;

  if (path.startsWith('/desk') || path.startsWith('/app') || path.startsWith('/login') || path.startsWith('/reset_password')) {
    if (!html.classList.contains('ct-enterprise')) {
      html.classList.add('ct-enterprise');
    }

    var savedMode = localStorage.getItem('ct-theme-mode');
    if (savedMode === 'light') {
      html.setAttribute('data-theme', 'light');
    } else if (savedMode === 'dark') {
      html.setAttribute('data-theme', 'dark');
    } else {
      html.setAttribute('data-theme', 'dark');
      localStorage.setItem('ct-theme-mode', 'dark');
    }
  }

  document.addEventListener('DOMContentLoaded', function() {
    initTheme();
  });

  function initTheme() {
    var currentMode = html.getAttribute('data-theme') || 'dark';

    var body = document.body;
    if (body) {
      if (body.classList.contains('login-content') ||
          body.classList.contains('login-page') ||
          body.classList.contains('web-form-page') ||
          document.querySelector('.page-card') ||
          document.querySelector('.login-content')) {
        if (!html.classList.contains('ct-enterprise')) {
          html.classList.add('ct-enterprise');
        }
        if (!html.getAttribute('data-theme')) {
          html.setAttribute('data-theme', localStorage.getItem('ct-theme-mode') || 'dark');
        }
      }
    }

    renderNavbarDropdown();
    colorTreeToolbarButtons();
    removeGhostButtons();
    hideFrappeBranding();
    watchRouteChanges();

    console.log('[ConstructionTheme] v2.9 initialized in ' + currentMode + ' mode');
  }

  function setMode(mode) {
    html.setAttribute('data-theme', mode);
    localStorage.setItem('ct-theme-mode', mode);
    updateNavbarLabel(mode);
  }

  function toggleMode() {
    var current = html.getAttribute('data-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';
    setMode(next);
  }

  function renderNavbarDropdown() {
    var navbar = document.querySelector('.desk-header .navbar-nav')
              || document.querySelector('.desk-header .navbar-right')
              || document.querySelector('.desk-header');
    if (!navbar) return;

    if (document.getElementById('ct-theme-toggle')) return;

    var li = document.createElement('li');
    li.className = 'nav-item dropdown';
    li.id = 'ct-theme-toggle';
    li.innerHTML =
      '<a class="nav-link dropdown-toggle" href="#" data-toggle="dropdown">' +
      '<span id="ct-theme-label">Theme</span></a>' +
      '<div class="dropdown-menu dropdown-menu-right">' +
      '<a class="dropdown-item" href="#" onclick="ctSetMode(\'dark\'); return false;">Dark</a>' +
      '<a class="dropdown-item" href="#" onclick="ctSetMode(\'light\'); return false;">Light</a>' +
      '</div>';
    navbar.appendChild(li);

    updateNavbarLabel(html.getAttribute('data-theme') || 'dark');
  }

  function updateNavbarLabel(mode) {
    var label = document.getElementById('ct-theme-label');
    if (label) {
      label.textContent = mode === 'dark' ? 'Dark' : 'Light';
    }
  }

  window.ctSetMode = setMode;

  function getThemeColors() {
    var cs = getComputedStyle(document.documentElement);
    return {
      primary: cs.getPropertyValue('--ct-primary').trim() || '#2563eb',
      primaryHover: cs.getPropertyValue('--ct-primary-hover').trim() || '#1d4ed8',
      success: cs.getPropertyValue('--ct-success').trim() || '#16a34a',
      successHover: cs.getPropertyValue('--ct-success-hover').trim() || '#15803d',
      danger: cs.getPropertyValue('--ct-danger').trim() || '#dc2626',
      dangerHover: cs.getPropertyValue('--ct-danger-hover').trim() || '#b91c1c',
      warning: cs.getPropertyValue('--ct-warning').trim() || '#d97706',
      surface: cs.getPropertyValue('--ct-surface').trim() || '#1e293b',
      textSecondary: cs.getPropertyValue('--ct-text-secondary').trim() || '#94a3b8',
      border: cs.getPropertyValue('--ct-border').trim() || 'rgba(148,163,184,0.18)',
      textDisabled: cs.getPropertyValue('--ct-text-disabled').trim() || '#475569',
      textMuted: cs.getPropertyValue('--ct-text-muted').trim() || '#64748b'
    };
  }

  function applyButtonStyle(btn, type, colors) {
    var bg, color, border, hoverBg, hoverColor, hoverBorder;

    switch(type) {
      case 'edit':
        bg = colors.primary; color = '#fff'; border = 'transparent';
        hoverBg = colors.primaryHover; hoverColor = '#fff'; hoverBorder = hoverBg;
        break;
      case 'add':
        bg = colors.success; color = '#fff'; border = 'transparent';
        hoverBg = colors.successHover; hoverColor = '#fff'; hoverBorder = hoverBg;
        break;
      case 'delete':
        bg = colors.danger; color = '#fff'; border = 'transparent';
        hoverBg = colors.dangerHover; hoverColor = '#fff'; hoverBorder = hoverBg;
        break;
      case 'toggle':
        bg = colors.warning; color = '#fff'; border = 'transparent';
        hoverBg = bg; hoverColor = '#fff'; hoverBorder = border;
        break;
      case 'view':
      default:
        bg = colors.surface; color = colors.textSecondary; border = colors.border;
        hoverBg = colors.primary; hoverColor = '#fff'; hoverBorder = hoverBg;
        break;
    }

    var s = btn.style;
    s.setProperty('background', bg, 'important');
    s.setProperty('color', color, 'important');
    s.setProperty('border', '1px solid ' + border, 'important');
    s.setProperty('border-radius', '6px', 'important');
    s.setProperty('height', '28px', 'important');
    s.setProperty('padding', '0 10px', 'important');
    s.setProperty('font-size', '11px', 'important');
    s.setProperty('font-weight', '600', 'important');
    s.setProperty('white-space', 'nowrap', 'important');
    s.setProperty('cursor', 'pointer', 'important');
    s.setProperty('transition', 'all 0.2s ease', 'important');
    s.setProperty('outline', 'none', 'important');
    s.setProperty('box-shadow', 'none', 'important');
    s.setProperty('display', 'inline-flex', 'important');
    s.setProperty('align-items', 'center', 'important');
    s.setProperty('justify-content', 'center', 'important');
    s.setProperty('gap', '4px', 'important');
    s.setProperty('line-height', '1', 'important');
    s.setProperty('text-decoration', 'none', 'important');

    btn._ctHover = { bg: hoverBg, color: hoverColor, border: hoverBorder };
    btn._ctRest = { bg: bg, color: color, border: border };

    btn.onmouseenter = function() {
      if (this._ctHover) {
        this.style.setProperty('background', this._ctHover.bg, 'important');
        this.style.setProperty('color', this._ctHover.color, 'important');
        this.style.setProperty('border-color', this._ctHover.border, 'important');
        this.style.setProperty('transform', 'translateY(-1px)', 'important');
      }
    };
    btn.onmouseleave = function() {
      if (this._ctRest) {
        this.style.setProperty('background', this._ctRest.bg, 'important');
        this.style.setProperty('color', this._ctRest.color, 'important');
        this.style.setProperty('border-color', this._ctRest.border, 'important');
        this.style.setProperty('transform', 'translateY(0)', 'important');
      }
    };
  }

  function colorTreeToolbarButtons() {
    var colors = getThemeColors();
    var toolbars = document.querySelectorAll('.tree-node-toolbar');
    toolbars.forEach(function(toolbar) {
      var buttons = toolbar.querySelectorAll('.tree-toolbar-button');
      buttons.forEach(function(btn) {
        if (btn.dataset.ctThemed) return;

        var raw = btn.textContent || btn.innerText || '';
        var text = raw.replace(/<[^>]*>/g, '').trim().toLowerCase().replace(/\s+/g, ' ');

        var type = null;
        if (!text) {
          if (btn.querySelector('.icon-book-open, [class*="book"], [class*="ledger"], svg[data-icon-type*="ledger"]')) {
            type = 'view';
          }
        } else if (text === 'edit' || text === 'details' || text === 'renommer' || text === 'modifier') {
          type = 'edit';
        } else if (text === 'add child' || text === 'add' || text === 'ajouter' || text === 'ajouter un enfant') {
          type = 'add';
        } else if (text === 'delete' || text === 'supprimer') {
          type = 'delete';
        } else if (text === 'toggle' || text === 'basculer') {
          type = 'toggle';
        } else if (
          text.indexOf('view ledger') !== -1 ||
          text.indexOf('view') !== -1 ||
          text.indexOf('ledger') !== -1 ||
          text.indexOf('voir') !== -1 ||
          text.indexOf('rapport') !== -1
        ) {
          type = 'view';
        } else if (text === 'rename' || text === 'renommer') {
          type = 'edit';
        }

        if (type) {
          btn.dataset.ctThemed = type;
          btn.classList.add('btn-colored', 'btn-' + type);
          applyButtonStyle(btn, type, colors);
        }
      });

      var treeNode = toolbar.closest('.tree-node');
      if (!treeNode) return;

      var treeLink = treeNode.querySelector(':scope > .tree-link');
      var hasExpandIcon = treeLink && treeLink.querySelector('.node-parent') !== null;

      var deleteBtn = toolbar.querySelector('.tree-toolbar-button.btn-delete');
      if (deleteBtn) {
        var existingWrap = deleteBtn.closest('.dtw');
        if (existingWrap) {
          var tip = existingWrap.querySelector('.dtip');
          if (tip) tip.remove();
          deleteBtn.classList.remove('btn-disabled');
          deleteBtn.removeAttribute('disabled');
          deleteBtn.style.setProperty('opacity', '1', 'important');
          deleteBtn.style.setProperty('cursor', 'pointer', 'important');
          deleteBtn.onmouseenter = function() {
            if (this._ctHover) {
              this.style.setProperty('background', this._ctHover.bg, 'important');
              this.style.setProperty('color', this._ctHover.color, 'important');
              this.style.setProperty('border-color', this._ctHover.border, 'important');
            }
            this.style.setProperty('transform', 'translateY(-1px)', 'important');
          };
          deleteBtn.onmouseleave = function() {
            if (this._ctRest) {
              this.style.setProperty('background', this._ctRest.bg, 'important');
              this.style.setProperty('color', this._ctRest.color, 'important');
              this.style.setProperty('border-color', this._ctRest.border, 'important');
            }
            this.style.setProperty('transform', 'translateY(0)', 'important');
          };
          existingWrap.replaceWith(deleteBtn);
        }

        if (hasExpandIcon) {
          deleteBtn.classList.add('btn-disabled');
          deleteBtn.setAttribute('disabled', 'disabled');
          deleteBtn.style.setProperty('opacity', '0.5', 'important');
          deleteBtn.style.setProperty('cursor', 'not-allowed', 'important');
          deleteBtn.style.setProperty('background', colors.textDisabled, 'important');
          deleteBtn.style.setProperty('color', colors.textMuted, 'important');
          deleteBtn.onmouseenter = null;
          deleteBtn.onmouseleave = null;
          deleteBtn._ctHover = null;
          deleteBtn._ctRest = null;
          deleteBtn.style.setProperty('transform', 'none', 'important');

          var wrap = document.createElement('span');
          wrap.className = 'dtw';
          wrap.style.position = 'relative';
          wrap.style.display = 'inline-block';
          deleteBtn.parentNode.insertBefore(wrap, deleteBtn);
          wrap.appendChild(deleteBtn);

          var tip = document.createElement('span');
          tip.className = 'dtip';
          tip.textContent = 'Has sub-accounts';
          tip.style.cssText = 'visibility:hidden;opacity:0;position:absolute;bottom:120%;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.92);color:#fff;padding:6px 12px;border-radius:6px;font-size:0.75rem;white-space:nowrap;transition:all 0.2s ease;z-index:100;pointer-events:none;';
          wrap.appendChild(tip);

          wrap.onmouseenter = function() {
            var t = this.querySelector('.dtip');
            if (t) { t.style.visibility = 'visible'; t.style.opacity = '1'; }
          };
          wrap.onmouseleave = function() {
            var t = this.querySelector('.dtip');
            if (t) { t.style.visibility = 'hidden'; t.style.opacity = '0'; }
          };
        }
      }
    });
  }

  var treeColorInterval = setInterval(colorTreeToolbarButtons, 500);

  function removeGhostButtons() {
    var ghosts = document.querySelectorAll('.btn.ghost-btn, .ghost-btn');
    ghosts.forEach(function(btn) {
      btn.style.display = 'none';
    });
  }

  function hideFrappeBranding() {
    var powered = document.querySelector('.footer-powered');
    if (powered) powered.style.display = 'none';
  }

  function watchRouteChanges() {
    if (typeof frappe === 'undefined' || !frappe.router) {
      setTimeout(watchRouteChanges, 500);
      return;
    }

    frappe.router.on("change", function() {
      setTimeout(syncSidebarActive, 100);
      setTimeout(colorTreeToolbarButtons, 300);
    });

    setTimeout(syncSidebarActive, 500);
    setTimeout(colorTreeToolbarButtons, 500);
  }

  function syncSidebarActive() {
    var currentPath = window.location.pathname.replace(/\/$/, "");
    var allItems = document.querySelectorAll(".standard-sidebar-item");

    allItems.forEach(function(item) {
      item.classList.remove("active-sidebar", "active");
    });

    allItems.forEach(function(item) {
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

  // ─── Dropdown themer removed — handled by CSS ───

  // ════════════════════════════════════════════════════════════
  //  BaseChart / ResizeObserver infinite-loop guard
  //  Prevents: "Failed to execute 'removeChild' on 'Node'"
  //  which triggers a ResizeObserver → draw → error → loop
  //
  //  Root cause: Frappe's chart_widget.js get_chart_colors()
  //  passes [[]] for Line/Bar charts without a defined color,
  //  causing BaseChart.validateColors() to receive empty string.
  //  This can cause partial chart failure → container height
  //  oscillation → ResizeObserver fires → draw() fails again.
  // ════════════════════════════════════════════════════════════

  function installChartGuard() {
    if (typeof frappe === 'undefined') return;

    if (frappe.utils && frappe.utils.make_chart) {
      var _origMC = frappe.utils.make_chart;
      frappe.utils.make_chart = function(parent, opts) {
        if (opts && opts.colors && Array.isArray(opts.colors)) {
          opts.colors = opts.colors.filter(function(c) {
            return c !== null && c !== undefined && c !== '' && !(Array.isArray(c));
          });
        }
        return _origMC.call(this, parent, opts);
      };
    }

    if (frappe.Chart && frappe.Chart.prototype) {
      var _origConf = frappe.Chart.prototype.configure;
      if (_origConf) {
        frappe.Chart.prototype.configure = function() {
          if (this.options && this.options.colors && Array.isArray(this.options.colors)) {
            this.options.colors = this.options.colors.filter(function(c) {
              return c !== null && c !== undefined && c !== '' && !(Array.isArray(c));
            });
          }
          _origConf.apply(this, arguments);
        };
      }
    }

    if (window.ResizeObserver && !window._ctROGuarded) {
      var _OrigRO = window.ResizeObserver;
      window.ResizeObserver = function(fn) {
        var safe = function(entries, obs) {
          try { fn(entries, obs); } catch (e) {
            console.warn('[CT] ResizeObserver error intercepted:', e);
          }
        };
        return new _OrigRO(safe);
      };
      window.ResizeObserver.prototype = _OrigRO.prototype;
      window._ctROGuarded = true;
    }
  }

  // Retry guard installation on page load and route changes
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(installChartGuard, 300);
    setTimeout(installChartGuard, 1000);
  });

  function patchRouteWatch() {
    if (typeof frappe !== 'undefined' && frappe.router) {
      frappe.router.on('change', function() {
        setTimeout(installChartGuard, 300);
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

})();
