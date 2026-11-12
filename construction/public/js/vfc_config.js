(function () {
	"use strict";

	function _vfcDebugEnabled() {
		try {
			if (window.location.search.indexOf("vfc_debug=1") !== -1) return true;
			if (window.localStorage.getItem("vfc_debug") === "true") return true;
			if (window.frappe && window.frappe.boot && window.frappe.boot.vfc_debug_enabled)
				return true;
		} catch (e) {
			// Storage access can be blocked; debug logging stays disabled.
		}
		return false;
	}

	window.VFC_DEBUG = _vfcDebugEnabled();

	/**
	 * Master switch for the Form Layout Engine (Construction Settings
	 * .enable_form_config, default OFF).
	 *
	 * Evaluated lazily rather than cached at parse time: this file is loaded
	 * ahead of frappe.boot in some paths, and a stale false here would leave a
	 * site that enabled the feature looking like it had not. Every caller gates
	 * at form-attach time, long after boot is populated.
	 *
	 * When this returns false no Form Config button is injected and the layout
	 * engine does not attach — forms render exactly as Frappe would.
	 */
	window.VFCisEnabled = function () {
		try {
			if (window.frappe && window.frappe.boot && window.frappe.boot.vfc_enabled) {
				return true;
			}
		} catch (e) {
			// boot unavailable: stay closed rather than fail open
		}
		return false;
	};

	window.vfcDebugLog = function (level) {
		if (!window.VFC_DEBUG) return;
		var fn = console.log;
		if (level === "warn") fn = console.warn;
		else if (level === "error") fn = console.error;
		var args = Array.prototype.slice.call(arguments, 1);
		fn.apply(console, args);
	};
})();
