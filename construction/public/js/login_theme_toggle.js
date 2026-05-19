/**
 * Login Page Theme Toggle
 * Allows switching between light and dark login themes
 * Uses cookies for persistence (localStorage cleared on logout)
 */

(function() {
  'use strict';

  var COOKIE_NAME = 'construction_theme_mode';

  // Cookie helpers
  function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) {
      return parts.pop().split(';').shift();
    }
    return null;
  }

  function setCookie(name, value, days) {
    var expires = '';
    if (days) {
      var date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = '; expires=' + date.toUTCString();
    }
    document.cookie = name + '=' + value + expires + '; path=/; SameSite=Lax';
  }

  function getThemeMode() {
    // 1. Check cookie (persists after logout)
    var cookieTheme = getCookie(COOKIE_NAME);
    if (cookieTheme) {
      console.log('[Login Theme] Cookie:', cookieTheme);
      return cookieTheme;
    }

    // 2. Check localStorage
    var lsTheme = localStorage.getItem('construction_active_theme') ||
                  localStorage.getItem('construction_theme') ||
                  localStorage.getItem('theme');

    // Default toLIGHT
    return (lsTheme && lsTheme.toLowerCase().includes('dark')) ? 'dark' : 'light';
  }

  // Apply theme to page
  function applyTheme(mode) {
    var isDark = mode === 'dark';
    console.log('[Login Theme] Applying:', mode);

    document.querySelectorAll('link[rel="stylesheet"]').forEach(function(link) {
      var href = link.href || link.getAttribute('href') || '';
      if (href.includes('login_theme.css') && !href.includes('login_theme_light')) {
        link.disabled = isDark ? false : true;
      } else if (href.includes('login_theme_light')) {
        link.disabled = isDark ? true : false;
      }
    });

    if (isDark) {
      document.body.classList.add('theme-dark');
      document.body.classList.remove('theme-light');
    } else {
      document.body.classList.add('theme-light');
      document.body.classList.remove('theme-dark');
    }
  }

  function addThemeToggleButton(isDark) {
    if (document.getElementById('login-theme-toggle')) return;

    var toggle = document.createElement('button');
    toggle.id = 'login-theme-toggle';
    toggle.type = 'button';
    toggle.innerHTML = isDark
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

    toggle.setAttribute('aria-label', 'Toggle theme');
    toggle.style.cssText = [
      'position: fixed',
      'top: 16px',
      'right: 16px',
      'z-index: 9999',
      'width: 40px',
      'height: 40px',
      'border-radius: 50%',
      'border: 1px solid rgba(255,255,255,0.15)',
      'background: rgba(255,255,255,0.1)',
      'color: inherit',
      'cursor: pointer',
      'display: flex',
      'align-items: center',
      'justify-content: center',
      'box-shadow: 0 4px 12px rgba(0,0,0,0.2)',
      'transition: all 0.2s ease',
      'backdrop-filter: blur(8px)',
      '-webkit-backdrop-filter: blur(8px)'
    ].join(';');

    toggle.onclick = function() {
      var currentlyDark = document.body.classList.contains('theme-dark');
      var newMode = currentlyDark ? 'light' : 'dark';

      applyTheme(newMode);
      setCookie(COOKIE_NAME, newMode, 365);
      localStorage.setItem('construction_active_theme', 'construction_' + newMode);

      toggle.innerHTML = newMode === 'dark'
        ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
        : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    };

    toggle.onmouseover = function() { this.style.transform = 'scale(1.1)'; };
    toggle.onmouseout = function() { this.style.transform = 'scale(1)'; };

    document.body.appendChild(toggle);
  }

  // Init
  function init() {
    var mode = getThemeMode();
    applyTheme(mode);
    addThemeToggleButton(mode === 'dark');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();