/**
 * CT List View Config — Construction-specific list view overrides
 *
 * Patches frappe.views.ListView to:
 * 1. Conditionally hide the like/heart column (disable_like)
 * 2. Collapse .level-right when like+comment are both disabled (no-activity)
 * 3. Fix dropdown z-index overlapping sticky .level-right
 *
 * Reads config from frappe.boot.ct_list_view_config or uses defaults.
 * No core frappe files modified.
 */
(function () {
	"use strict";

	// ─── Configuration ─────────────────────────────────────────────
	// Per-doctype overrides: { doctype_name: { disable_like: true/false } }
	// Merged with frappe.boot.ct_list_view_config if available.
	const DEFAULT_CONFIG = {
		"BOQ Header": { disable_like: true },
	};

	function getConfig(doctype) {
		const boot_config = frappe.boot?.ct_list_view_config || {};
		const merged = { ...DEFAULT_CONFIG, ...boot_config };
		return merged[doctype] || {};
	}

	// ─── Patch: get_header_html (hides "Liked by me" toggle) ──────
	const _orig_get_header_html = frappe.views.ListView.prototype.get_header_html;
	frappe.views.ListView.prototype.get_header_html = function () {
		const ct_config = getConfig(this.doctype);
		if (ct_config.disable_like) {
			// Store original, call without like
			const orig_disable = this.list_view_settings?.disable_like;
			if (!this.list_view_settings) this.list_view_settings = {};
			this.list_view_settings.disable_like = true;
			const result = _orig_get_header_html.apply(this, arguments);
			// Restore original
			if (orig_disable === undefined) {
				delete this.list_view_settings.disable_like;
			} else {
				this.list_view_settings.disable_like = orig_disable;
			}
			return result;
		}
		return _orig_get_header_html.apply(this, arguments);
	};

	// ─── Patch: get_meta_html (hides per-row like button) ──────────
	const _orig_get_meta_html = frappe.views.ListView.prototype.get_meta_html;
	frappe.views.ListView.prototype.get_meta_html = function (doc) {
		const ct_config = getConfig(this.doctype);
		if (ct_config.disable_like) {
			const orig_disable = this.list_view_settings?.disable_like;
			if (!this.list_view_settings) this.list_view_settings = {};
			this.list_view_settings.disable_like = true;
			const result = _orig_get_meta_html.apply(this, arguments);
			if (orig_disable === undefined) {
				delete this.list_view_settings.disable_like;
			} else {
				this.list_view_settings.disable_like = orig_disable;
			}
			return result;
		}
		return _orig_get_meta_html.apply(this, arguments);
	};

	// ─── Patch: update_listview_classes (adds no-activity class) ───
	const _orig_update_listview_classes =
		frappe.views.ListView.prototype.update_listview_classes;
	frappe.views.ListView.prototype.update_listview_classes = function () {
		const result = _orig_update_listview_classes.apply(this, arguments);

		const ct_config = getConfig(this.doctype);
		const is_comment_disabled =
			this.list_view_settings?.disable_comment_count;
		const is_like_disabled =
			ct_config.disable_like || this.list_view_settings?.disable_like;

		if (is_like_disabled && is_comment_disabled) {
			this.$result.addClass("no-activity");
		}

		return result;
	};

	// ─── Inject settings into boot for API access ──────────────────
	if (frappe.boot) {
		frappe.boot.ct_list_view_config = {
			...DEFAULT_CONFIG,
			...(frappe.boot.ct_list_view_config || {}),
		};
	}
})();
