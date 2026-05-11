/**
 * Frappe v16 DOM Selector Verification Script
 * Run in browser console on your v16 cloud instance.
 * Paste this entire script and press Enter.
 *
 * GREEN = selector found in DOM (working)
 * RED   = selector NOT found (needs attention)
 */

(function verifyV16Selectors() {
    const selectors = {
        // LAYOUT
        'Layout: .page-container': '.page-container',
        'Layout: .page-body': '.page-body',
        'Layout: .page-head': '.page-head',
        'Layout: .page-head-content': '.page-head-content',
        'Layout: .page-content': '.page-content',
        'Layout: .page-wrapper': '.page-wrapper',
        'Layout: .main-section': '.main-section',

        // LAYOUT ROW
        'Layout Row: .layout-main': '.layout-main',
        'Layout Row: .layout-main-section': '.layout-main-section',
        'Layout Row: .layout-main-section-wrapper': '.layout-main-section-wrapper',

        // SIDEBAR
        'Sidebar: .layout-side-section': '.layout-side-section',
        'Sidebar: .desk-sidebar': '.desk-sidebar',
        'Sidebar: .list-sidebar': '.list-sidebar',
        'Sidebar: .form-sidebar': '.form-sidebar',
        'Sidebar: .overlay-sidebar': '.overlay-sidebar',

        // SIDEBAR ITEMS
        'Sidebar Item: .standard-sidebar-section': '.standard-sidebar-section',
        'Sidebar Item: .standard-sidebar-label': '.standard-sidebar-label',
        'Sidebar Item: .desk-sidebar-item': '.desk-sidebar-item',
        'Sidebar Item: .standard-sidebar-item': '.standard-sidebar-item',
        'Sidebar Item: .sidebar-item-container': '.sidebar-item-container',
        'Sidebar Item: .sidebar-item-label': '.sidebar-item-label',
        'Sidebar Item: .sidebar-item-icon': '.sidebar-item-icon',
        'Sidebar Item: .item-anchor': '.item-anchor',

        // NAVBAR
        'Navbar: .navbar.navbar-expand': '.navbar.navbar-expand',
        'Navbar: .navbar-brand': '.navbar-brand',
        'Navbar: .navbar-nav': '.navbar-nav',
        'Navbar: .nav-item.dropdown': '.nav-item.dropdown',

        // FORM
        'Form: .std-form-layout': '.std-form-layout',
        'Form: .form-layout': '.form-layout',
        'Form: .form-page': '.form-page',
        'Form: .frappe-control': '.frappe-control',
        'Form: .control-label': '.control-label',
        'Form: .control-input-wrapper': '.control-input-wrapper',
        'Form: .control-input': '.control-input',
        'Form: .form-section': '.form-section',
        'Form: .section-head': '.section-head',
        'Form: .section-body': '.section-body',

        // LIST VIEW
        'List: .frappe-list': '.frappe-list',
        'List: .result': '.result',
        'List: .list-row': '.list-row',
        'List: .list-row-head': '.list-row-head',
        'List: .list-row-container': '.list-row-container',
        'List: .no-result': '.no-result',

        // PAGE HEAD
        'Page: .title-area': '.title-area',
        'Page: .page-title': '.page-title',
        'Page: .page-actions': '.page-actions',
        'Page: .indicator-pill': '.indicator-pill',

        // CARDS
        'Card: .frappe-card': '.frappe-card',
        'Card: .widget': '.widget',

        // COMMON
        'Buttons: .btn-primary': '.btn-primary',
        'Buttons: .btn-default': '.btn-default',
        'Dropdowns: .dropdown-menu': '.dropdown-menu',
        'Dropdowns: .dropdown-item': '.dropdown-item',
        'Modals: .modal': '.modal',
        'Tables: .dt-row': '.dt-row',
        'Tables: .dt-cell': '.dt-cell',
    };

    // THEME TOKEN VERIFICATION
    const tokens = {
        '--primary': '#2563eb',
        '--primary-hover': '#1d4ed8',
        '--primary-light': 'rgba(37, 99, 235, 0.15)',
        '--bg': null,           // varies by theme
        '--surface': null,      // varies by theme
        '--text': null,         // varies by theme
        '--border': null,       // varies by theme
        '--sidebar-width': '260px',
        '--sidebar-collapsed': '60px',
        '--radius-sm': '6px',
        '--radius': '10px',
    };

    let found = 0, missing = 0, total = Object.keys(selectors).length;
    console.log('\n%c=== Frappe v16 DOM Selector Verification ===', 'color: #2563eb; font-size: 16px; font-weight: bold;');

    // Detect theme
    const theme = document.documentElement.getAttribute('data-theme') || 'none';
    console.log(`%cCurrent theme: ${theme}`, 'color: #94a3b8; font-size: 12px;');

    console.log('\n%c--- DOM Selectors ---', 'color: #f59e0b; font-size: 13px; font-weight: bold;');
    for (const [label, selector] of Object.entries(selectors)) {
        const elements = document.querySelectorAll(selector);
        if (elements.length > 0) {
            console.log(`%c✓ ${label}%c (${elements.length} found)`, 'color: #16a34a;', 'color: #64748b;', selector);
            found++;
        } else {
            console.log(`%c✗ ${label}%c — NOT IN DOM`, 'color: #dc2626;', 'color: #64748b;', selector);
            missing++;
        }
    }

    console.log(`\n%c--- CSS Token Verification ---`, 'color: #f59e0b; font-size: 13px; font-weight: bold;');
    const root = getComputedStyle(document.documentElement);
    let tokenPass = 0, tokenFail = 0;
    for (const [token, expected] of Object.entries(tokens)) {
        const value = root.getPropertyValue(token).trim();
        if (expected === null) {
            // Variable-only check (theme-dependent)
            if (value) {
                console.log(`%c✓ ${token}%c = ${value}`, 'color: #16a34a;', 'color: #64748b;');
                tokenPass++;
            } else {
                console.log(`%c✗ ${token}%c — NOT SET`, 'color: #dc2626;', 'color: #64748b;');
                tokenFail++;
            }
        } else {
            if (value && value.toLowerCase().replace(/\s/g, '') === expected.toLowerCase().replace(/\s/g, '')) {
                console.log(`%c✓ ${token}%c = ${value}`, 'color: #16a34a;', 'color: #64748b;');
                tokenPass++;
            } else {
                console.log(`%c✗ ${token}%c expected "${expected}" but got "${value}"`, 'color: #dc2626;', 'color: #64748b;');
                tokenFail++;
            }
        }
    }

    // CHECK FOR DUPLICATE SIDEBAR ELEMENTS
    console.log('\n%c--- Duplicate Sidebar Check ---', 'color: #f59e0b; font-size: 13px; font-weight: bold;');
    const dupeSelectors = ['.modern-sidebar', '.theme-sidebar', '.sidebar-modern', '#modern-sidebar', '#theme-sidebar'];
    for (const sel of dupeSelectors) {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) {
            console.log(`%c✗ DUPLICATE SIDEBAR FOUND: ${sel}%c (${els.length} elements)`, 'color: #dc2626; font-weight: bold;', 'color: #64748b;');
        } else {
            console.log(`%c✓ No duplicate sidebar: ${sel}`, 'color: #16a34a;');
        }
    }

    // CHECK NAVBAR STRUCTURE (debug)
    console.log('\n%c--- Navbar Structure Debug ---', 'color: #f59e0b; font-size: 13px; font-weight: bold;');
    const allNavbars = document.querySelectorAll('header, nav, .navbar');
    console.log(`Found ${allNavbars.length} navbar-like elements:`);
    allNavbars.forEach((el, i) => {
        console.log(`  [${i}] <${el.tagName.toLowerCase()}> class="${el.className}" id="${el.id || 'none'}"`);
    });
    const allNavUl = document.querySelectorAll('ul.navbar-nav, ul.nav');
    console.log(`Found ${allNavUl.length} navbar-nav/ul.nav elements`);
    allNavUl.forEach((el, i) => {
        console.log(`  [${i}] <${el.tagName.toLowerCase()}> class="${el.className}" id="${el.id || 'none'}"`);
    });

    // CHECK theme_patch.js LOADING
    console.log('\n%c--- JS Loading Check ---', 'color: #f59e0b; font-size: 13px; font-weight: bold;');
    const scripts = performance.getEntriesByType('resource').filter(r => r.name.includes('construction'));
    scripts.forEach(s => {
        const isOld = s.name.includes('theme_patch') || s.name.includes('modern_theme_loader') || s.name.includes('theme_system_2025');
        console.log(`%c${isOld ? '⚠' : '✓'} ${s.name.split('/').pop()}%c`, isOld ? 'color: #dc2626; font-weight: bold;' : 'color: #16a34a;', 'color: #64748b;');
    });

    // CHECK INLINE STYLE CONFLICTS
    const sidebar = document.querySelector('.layout-side-section') || document.querySelector('.body-sidebar-container');
    if (sidebar) {
        console.log('\n%c--- Sidebar Layout Check ---', 'color: #f59e0b; font-size: 13px; font-weight: bold;');
        const cs = getComputedStyle(sidebar);
        console.log(`  width: ${cs.width}`);
        console.log(`  position: ${cs.position}`);
        console.log(`  flex: ${cs.flex}`);
        console.log(`  background: ${cs.backgroundColor}`);
        const hasInlineWidth = sidebar.style.width;
        const hasInlinePosition = sidebar.style.position;
        if (hasInlineWidth || hasInlinePosition) {
            console.log('%c⚠ Sidebar has inline styles that may override CSS!', 'color: #f59e0b; font-weight: bold;');
            console.log(`  inline width: ${hasInlineWidth || 'none'}`);
            console.log(`  inline position: ${hasInlinePosition || 'none'}`);
        } else {
            console.log('%c✓ No conflicting inline styles on sidebar', 'color: #16a34a;');
        }
    }

    // SUMMARY
    console.log('\n%c════════════════════════════════════════', 'color: #94a3b8;');
    console.log(`%cDOM Selectors: ${found}/${total} found, ${missing} not in DOM (navigate to relevant page to see more)`, found === total ? 'color: #16a34a; font-weight: bold;' : 'color: #f59e0b; font-weight: bold;');
    console.log(`%cCSS Tokens: ${tokenPass} pass, ${tokenFail} fail`, tokenFail === 0 ? 'color: #16a34a; font-weight: bold;' : 'color: #dc2626; font-weight: bold;');
    console.log(`%cNote: Many selectors only appear on specific pages (forms, lists, workspaces). Navigate to each page type and re-run this script for full coverage.`, 'color: #94a3b8; font-style: italic;');
})();