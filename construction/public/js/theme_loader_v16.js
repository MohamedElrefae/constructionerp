/* ==========================================================================
   Construction Theme for Frappe v16 — JS Safety Net & Runtime Adapter
   Phase 3: MutationObserver for dynamically injected content
   Load via app_include_js in hooks.py (after theme_loader.js)
   ========================================================================== */

(function() {
  'use strict';

  const CONFIG = {
    debug: false,
    observeInterval: 500,
    sidebarRetryInterval: 200,
    sidebarRetryMax: 50,
    forceBodyTheme: true,
    forceSvgCharts: true,
    forceInjectedContent: true,
  };

  const log = (...args) => CONFIG.debug && console.log('[ConstructionTheme v16]', ...args);

  const TOKENS = {
    bg:              '#0b1020',
    surface:         '#1e293b',
    surfaceHover:    '#334155',
    surfaceActive:   '#475569',
    text:            '#f8fafc',
    text2:           '#94a3b8',
    text3:           '#64748b',
    primary:         '#0ea5e9',
    primaryLight:    '#38bdf8',
    danger:          '#ef4444',
    success:         '#22c55e',
    warning:         '#f59e0b',
    border:          'rgba(148,163,184,0.18)',
  };

  /* =======================================================================
     SECTION 1: Force Body & Document Root Theme
     ======================================================================= */

  function forceDocumentTheme() {
    if (!CONFIG.forceBodyTheme) return;
    const root = document.documentElement;
    const body = document.body;
    if (!root.hasAttribute('data-theme')) {
      root.setAttribute('data-theme', 'dark');
    }
    if (body) {
      body.style.backgroundColor = TOKENS.bg;
      body.style.color = TOKENS.text;
    }
    const bodyWrapper = document.getElementById('body');
    if (bodyWrapper) bodyWrapper.style.backgroundColor = TOKENS.bg;
    document.querySelectorAll('.page-container, .page-content, .content').forEach(el => {
      el.style.backgroundColor = TOKENS.bg;
    });
  }

  /* =======================================================================
     SECTION 2: Sidebar Force-Text Function
     ======================================================================= */

  function forceSidebarText() {
    document.querySelectorAll('.body-sidebar-container').forEach(container => {
      container.style.backgroundColor = TOKENS.bg;
      container.style.borderRight = `1px solid ${TOKENS.border}`;
    });
    document.querySelectorAll('.body-sidebar').forEach(sidebar => {
      sidebar.style.backgroundColor = TOKENS.bg;
      sidebar.style.color = TOKENS.text2;
    });
    document.querySelectorAll('.standard-sidebar-item').forEach(item => {
      const computedBg = window.getComputedStyle(item).backgroundColor;
      const isTransparent = computedBg === 'rgba(0, 0, 0, 0)' || computedBg === 'transparent';
      if (isTransparent || item.getAttribute('data-theme-fixed')) return;
      item.setAttribute('data-theme-fixed', 'true');
      item.style.color = TOKENS.text2;
      item.style.backgroundColor = 'transparent';
      item.style.borderRadius = '8px';
      item.style.margin = '2px 8px';
      item.style.padding = '8px 16px';
      item.style.transition = 'all 0.2s cubic-bezier(0.4,0,0.2,1)';
      item.addEventListener('mouseenter', () => {
        item.style.backgroundColor = TOKENS.surfaceHover;
        item.style.color = TOKENS.text;
      });
      item.addEventListener('mouseleave', () => {
        const isActive = item.classList.contains('active') ||
                         item.classList.contains('selected') ||
                         item.classList.contains('router-link-active');
        if (!isActive) {
          item.style.backgroundColor = 'transparent';
          item.style.color = TOKENS.text2;
        }
      });
      if (item.classList.contains('active') || item.classList.contains('selected') || item.classList.contains('router-link-active')) {
        item.style.backgroundColor = 'rgba(14,165,233,0.12)';
        item.style.color = TOKENS.primaryLight;
      }
    });
    document.querySelectorAll('.sidebar-header').forEach(header => {
      header.style.color = TOKENS.text3;
      header.style.fontSize = '10px';
      header.style.fontWeight = '700';
      header.style.textTransform = 'uppercase';
      header.style.letterSpacing = '0.08em';
    });
    document.querySelectorAll('.body-sidebar-bottom').forEach(bottom => {
      bottom.style.backgroundColor = TOKENS.bg;
      bottom.style.borderTop = `1px solid ${TOKENS.border}`;
    });
    log('forceSidebarText() executed');
  }

  /* =======================================================================
     SECTION 3: SVG Chart Theming
     ======================================================================= */

  function forceChartTheme() {
    if (!CONFIG.forceSvgCharts) return;
    document.querySelectorAll('.apexcharts-canvas').forEach(canvas => {
      const svg = canvas.querySelector('svg');
      if (svg) {
        svg.querySelectorAll('.apexcharts-text').forEach(text => { text.style.fill = TOKENS.text2; });
        svg.querySelectorAll('.apexcharts-title-text').forEach(text => { text.style.fill = TOKENS.text; });
        svg.querySelectorAll('.apexcharts-legend-text').forEach(text => { text.style.fill = TOKENS.text2; });
        svg.querySelectorAll('.apexcharts-gridline').forEach(line => {
          line.style.stroke = TOKENS.border;
          line.style.strokeOpacity = '0.5';
        });
      }
    });
    document.querySelectorAll('.frappe-chart svg').forEach(svg => {
      svg.querySelectorAll('text').forEach(text => { text.style.fill = TOKENS.text3; });
      svg.querySelectorAll('.line-vertical, .line-horizontal').forEach(line => {
        line.style.stroke = TOKENS.border;
        line.style.strokeOpacity = '0.3';
      });
    });
    log('forceChartTheme() executed');
  }

  /* =======================================================================
     SECTION 4: Handle Dynamically Injected Content
     ======================================================================= */

  function handleInjectedNodes(nodes) {
    nodes.forEach(node => {
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (node.matches && (
        node.matches('.body-sidebar-container') ||
        node.matches('.body-sidebar') ||
        node.matches('.standard-sidebar-item')
      )) {
        forceSidebarText();
        return;
      }
      if (node.querySelector) {
        if (node.querySelector('.standard-sidebar-item, .body-sidebar-container')) forceSidebarText();
        if (node.querySelector('.apexcharts-canvas, .frappe-chart')) forceChartTheme();
        if (node.querySelector('.widget, .widget-group')) forceWidgetTheme();
      }
    });
  }

  function forceWidgetTheme() {
    document.querySelectorAll('.widget').forEach(widget => {
      widget.style.backgroundColor = TOKENS.surface;
      widget.style.border = `1px solid ${TOKENS.border}`;
      widget.style.borderRadius = '10px';
    });
    document.querySelectorAll('.widget .widget-head').forEach(head => {
      head.style.color = TOKENS.text;
      head.style.borderBottom = `1px solid ${TOKENS.border}`;
    });
    document.querySelectorAll('.widget .widget-body').forEach(body => {
      body.style.color = TOKENS.text2;
    });
    log('forceWidgetTheme() executed');
  }

  /* =======================================================================
     SECTION 5: Debounced MutationObserver
     ======================================================================= */

  let mutationTimeout = null;

  function setupMutationObserver() {
    if (!CONFIG.forceInjectedContent) return;
    const observer = new MutationObserver((mutations) => {
      const newNodes = [];
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) newNodes.push(node);
        });
      });
      if (newNodes.length === 0) return;
      clearTimeout(mutationTimeout);
      mutationTimeout = setTimeout(() => {
        handleInjectedNodes(newNodes);
        forceChartTheme();
      }, CONFIG.observeInterval);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    log('MutationObserver started');
  }

  /* =======================================================================
     SECTION 6: Wait for Frappe App Ready
     ======================================================================= */

  function waitForSidebar(callback) {
    let retries = 0;
    const check = () => {
      const sidebar = document.querySelector('.body-sidebar-container, .body-sidebar');
      if (sidebar) { callback(); return; }
      if (++retries < CONFIG.sidebarRetryMax) {
        setTimeout(check, CONFIG.sidebarRetryInterval);
      } else {
        callback();
      }
    };
    check();
  }

  /* =======================================================================
     SECTION 7: Public API
     ======================================================================= */

  window.constructionTheme = {
    forceSidebar: forceSidebarText,
    forceCharts: forceChartTheme,
    forceWidgets: forceWidgetTheme,
    forceDocument: forceDocumentTheme,
    forceAll() {
      forceDocumentTheme();
      forceSidebarText();
      forceChartTheme();
      forceWidgetTheme();
    },
    setDebug(enabled) { CONFIG.debug = enabled; },
    getTokens() { return { ...TOKENS }; },
  };

  /* =======================================================================
     SECTION 8: Initialization
     ======================================================================= */

  function init() {
    log('Initializing Construction Theme v16 adapter');
    forceDocumentTheme();
    waitForSidebar(() => {
      forceSidebarText();
      forceChartTheme();
      forceWidgetTheme();
    });
    if (document.body) {
      setupMutationObserver();
    } else {
      const bodyObserver = new MutationObserver((mutations, obs) => {
        if (document.body) {
          obs.disconnect();
          forceDocumentTheme();
          waitForSidebar(() => {
            forceSidebarText();
            forceChartTheme();
            forceWidgetTheme();
          });
          setupMutationObserver();
        }
      });
      bodyObserver.observe(document.documentElement, { childList: true });
    }
    if (window.frappe && window.frappe.router) {
      $(document).on('page-change', () => {
        setTimeout(() => {
          forceDocumentTheme();
          forceSidebarText();
          forceChartTheme();
          forceWidgetTheme();
        }, 300);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
