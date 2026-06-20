(function () {
    "use strict";

    function _vfcDebugEnabled() {
        try {
            if (window.location.search.indexOf("vfc_debug=1") !== -1) return true;
            if (window.localStorage.getItem("vfc_debug") === "true") return true;
            if (window.frappe && window.frappe.boot && window.frappe.boot.vfc_debug_enabled) return true;
        } catch (e) {}
        return false;
    }

    window.VFC_DEBUG = _vfcDebugEnabled();

    window.vfcDebugLog = function (level) {
        if (!window.VFC_DEBUG) return;
        var fn = console.log;
        if (level === "warn") fn = console.warn;
        else if (level === "error") fn = console.error;
        var args = Array.prototype.slice.call(arguments, 1);
        fn.apply(console, args);
    };
})();
