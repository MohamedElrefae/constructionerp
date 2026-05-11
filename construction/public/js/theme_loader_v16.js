/* ==========================================================================
   Construction Theme for Frappe v16 — CSS-Only Safety Net
   Static CSS handles all styling. JS is detection-only.
   ========================================================================== */

(function() {
  'use strict';

  const CONFIG = {
    debug: false,
  };

  const log = (...args) => CONFIG.debug && console.log('[ConstructionTheme v16]', ...args);

  function init() {
    log('Static CSS handles all styling. JS safety net active (no-op).');
  }

  window.constructionTheme = {
    forceAll() { log('CSS handles all styling — no inline styles applied'); },
    setDebug(enabled) { CONFIG.debug = enabled; },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
