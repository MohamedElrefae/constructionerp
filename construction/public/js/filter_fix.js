(function () {
	"use strict";

	// Inject comprehensive filter CSS
	var styleId = "ct-filter-ground-up";
	if (document.getElementById(styleId)) {
		document.getElementById(styleId).remove();
	}

	var css = `
/* === CT Filter Ground-Up Fix v4.1 === */

/* 1. Reset ALL filter wrappers to invisible */
.page-form .standard-filter-section,
.page-form .filter-section,
.page-form .filter-area,
.page-form .frappe-control,
.page-form .frappe-control .control-input,
.page-form .frappe-control .control-input-wrapper,
.page-form .frappe-control .link-field,
.page-form .frappe-control .input-group,
.page-form .frappe-control .awesomplete,
.page-form .frappe-control .multiselect-list,
.page-form .filter-field,
.page-form .filter-selector,
.page-form .sort-selector,
.page-form .filter-box,
.page-form .filter-label,
.page-form .filter-value {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-left: none !important;
  border-right: none !important;
  border-top: none !important;
  border-bottom: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* 2. Unified page-form layout */
.page-form {
  gap: 0 !important;
  column-gap: 0 !important;
  row-gap: 0 !important;
  align-items: center !important;
}

.page-form .standard-filter-section {
  flex: 1 1 auto !important;
  min-width: 0 !important;
}

.page-form .filter-section {
  flex: 0 0 auto !important;
}

.page-form .filter-field,
.page-form .filter-selector,
.page-form .sort-selector {
  flex: 0 0 auto !important;
  margin: 0 4px !important;
}

/* 3. ALL inputs/selects - unified styling */
.page-form select,
.page-form select.form-control,
.page-form input.form-control,
.page-form input.input-with-feedback,
.page-form .link-field input,
.page-form .multiselect-list .form-control,
.page-form .awesomplete input,
.page-form input[data-fieldtype="Date"],
.page-form input.hasDatepicker,
.page-form input[type="text"],
.page-form input[type="search"] {
  height: 30px !important;
  background-color: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text, #f8fafc) !important;
  border-top: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-right: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-bottom: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-left: 3px solid var(--ct-primary, #2563eb) !important;
  border-radius: 6px !important;
  box-shadow: none !important;
  outline: none !important;
  font-size: 0.8125rem !important;
  max-width: 200px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

/* 4. Select specific */
.page-form select,
.page-form select.form-control {
  appearance: none !important;
  -webkit-appearance: none !important;
  -moz-appearance: none !important;
  padding: 2px 26px 2px 8px !important;
}

/* RTL select padding */
[dir="rtl"] .page-form select,
[dir="rtl"] .page-form select.form-control {
  padding: 2px 8px 2px 26px !important;
}

/* 5. Hide Frappe select icons */
.page-form .frappe-control .select-icon,
.page-form .frappe-control .select-icon svg,
.page-form .frappe-control .select-icon use,
.page-form .frappe-control .placeholder {
  display: none !important;
}

/* 6. Buttons unified */
.page-form .filter-selector .btn,
.page-form .filter-button,
.page-form [data-action="add-filter"],
.page-form .sort-selector .btn,
.page-form .btn-filter {
  height: 30px !important;
  background: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text-secondary, #94a3b8) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-radius: 6px !important;
  font-size: 0.75rem !important;
  padding: 0 8px !important;
  margin: 0 2px !important;
  box-shadow: none !important;
}

/* 7. Awesomplete dropdown container - NO border, NO bg */
.page-form .awesomplete {
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* 8. Awesomplete dropdown list - themed, NO item borders */
.page-form .awesomplete ul {
  background: var(--ct-bg-elevated, #111827) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-radius: 6px !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
  padding: 4px 0 !important;
  margin: 4px 0 0 0 !important;
  max-height: 300px !important;
  overflow-y: auto !important;
}

/* 9. Awesomplete dropdown items - NO borders, unified hover */
.page-form .awesomplete li {
  background: transparent !important;
  color: var(--ct-text, #f8fafc) !important;
  padding: 8px 12px !important;
  border: none !important;
  border-left: none !important;
  border-right: none !important;
  border-top: none !important;
  border-bottom: none !important;
  border-radius: 0 !important;
  margin: 0 !important;
  font-size: 0.8125rem !important;
  cursor: pointer !important;
  transition: background 0.15s ease !important;
}

/* 10. Awesomplete hover/selected states */
.page-form .awesomplete li:hover,
.page-form .awesomplete li[aria-selected="true"],
.page-form .awesomplete li.active {
  background: var(--ct-bg-hover, rgba(255,255,255,0.08)) !important;
  color: var(--ct-text, #f8fafc) !important;
}

/* 11. Native select dropdown options - themed */
.page-form select option {
  background: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text, #f8fafc) !important;
  padding: 8px 12px !important;
}

.page-form select option:hover,
.page-form select option:checked {
  background: var(--ct-bg-hover, rgba(255,255,255,0.08)) !important;
  color: var(--ct-text, #f8fafc) !important;
}

/* 12. Filter chips/tags */
.page-form .filter-pill,
.page-form .filter-pill .btn {
  background: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text, #f8fafc) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-radius: 6px !important;
  height: 30px !important;
  padding: 0 8px !important;
}

/* 13. Checkbox/radio in filters */
.page-form input[type="checkbox"],
.page-form input[type="radio"] {
  accent-color: var(--ct-primary, #2563eb) !important;
}

/* 14. Focus states */
.page-form select:focus,
.page-form input.form-control:focus,
.page-form .awesomplete input:focus {
  border-color: var(--ct-primary, #2563eb) !important;
  box-shadow: 0 0 0 2px rgba(37,99,235,0.2) !important;
}

/* 15. Hover states */
.page-form select:hover,
.page-form input.form-control:hover,
.page-form .awesomplete input:hover {
  border-color: var(--ct-primary, #2563eb) !important;
}

/* 16. Filter type dropdown (Add Filter) - unified styling */
.page-form .filter-selector .dropdown-menu,
.page-form .filter-section .dropdown-menu {
  background: var(--ct-bg-elevated, #111827) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-radius: 6px !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
  padding: 4px 0 !important;
}

.page-form .filter-selector .dropdown-menu li,
.page-form .filter-section .dropdown-menu li,
.page-form .filter-selector .dropdown-menu a,
.page-form .filter-section .dropdown-menu a {
  background: transparent !important;
  color: var(--ct-text, #f8fafc) !important;
  padding: 8px 12px !important;
  border: none !important;
  border-radius: 0 !important;
  margin: 0 !important;
  font-size: 0.8125rem !important;
}

.page-form .filter-selector .dropdown-menu li:hover,
.page-form .filter-section .dropdown-menu li:hover,
.page-form .filter-selector .dropdown-menu a:hover,
.page-form .filter-section .dropdown-menu a:hover {
  background: var(--ct-bg-hover, rgba(255,255,255,0.08)) !important;
  color: var(--ct-text, #f8fafc) !important;
}

/* 17. Link field dropdown - remove item borders */
.page-form .link-field .awesomplete ul li {
  border-bottom: none !important;
  border-top: none !important;
  border-left: none !important;
  border-right: none !important;
}

/* 18. Filter field container - prevent overflow */
.page-form .filter-field {
  overflow: visible !important;
  position: relative !important;
}

/* 19. Filter label styling */
.page-form .filter-label {
  color: var(--ct-text-secondary, #94a3b8) !important;
  font-size: 0.75rem !important;
}

/* 20. Dropdown menu global fixes */
.dropdown-menu {
  background: var(--ct-bg-elevated, #111827) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-radius: 6px !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}

.dropdown-menu li a,
.dropdown-menu .dropdown-item {
  color: var(--ct-text, #f8fafc) !important;
  padding: 8px 12px !important;
}

.dropdown-menu li a:hover,
.dropdown-menu .dropdown-item:hover {
  background: var(--ct-bg-hover, rgba(255,255,255,0.08)) !important;
  color: var(--ct-text, #f8fafc) !important;
}

/* 21. Custom Unified Dropdown styling (for selectors/links override) */
.ct-unified-dropdown {
  position: relative !important;
  width: 100% !important;
  display: inline-block !important;
}

.ct-dropdown-btn {
  width: 100% !important;
  height: 30px !important;
  background-color: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text, #f8fafc) !important;
  border-top: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-right: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-bottom: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-left: 3px solid var(--ct-primary, #2563eb) !important;
  border-radius: 6px !important;
  padding: 4px 10px 4px 8px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 6px !important;
  cursor: pointer !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  text-align: left !important;
  transition: all 0.2s ease !important;
  user-select: none !important;
}

.ct-dropdown-btn:hover {
  background-color: var(--ct-surface-hover, rgba(148,163,184,0.08)) !important;
  border-color: var(--ct-primary, #2563eb) !important;
  box-shadow: 0 0 0 1px var(--ct-primary-light, rgba(37,99,235,0.15)) !important;
}

.ct-dropdown-menu {
  display: none;
  position: fixed !important;
  z-index: 10000 !important;
  min-width: 220px !important;
  max-width: 380px !important;
  background: var(--ct-surface-bg, #112b15) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-left: 3px solid var(--ct-primary, #2563eb) !important;
  border-radius: 8px !important;
  padding: 6px !important;
  box-shadow: var(--ct-shadow-lg, 0 8px 32px rgba(0,0,0,0.45)) !important;
}

.ct-dropdown-search-wrapper {
  padding: 0 0 6px !important;
  border-bottom: 1px solid var(--ct-border, rgba(148,163,184,0.1)) !important;
  margin-bottom: 4px !important;
}

.ct-dropdown-search {
  width: 100% !important;
  padding: 5px 8px !important;
  background: var(--ct-bg-elevated, #0f172a) !important;
  color: var(--ct-text, #f8fafc) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.2)) !important;
  border-left: 2px solid var(--ct-primary, #2563eb) !important;
  border-radius: 5px !important;
  font-size: 0.8rem !important;
  outline: none !important;
}

.ct-dropdown-list {
  max-height: 220px !important;
  overflow-y: auto !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 2px !important;
}

.ct-dropdown-list .dropdown-item {
  display: block !important;
  width: 100% !important;
  padding: 7px 10px !important;
  border-radius: 5px !important;
  font-size: 0.8125rem !important;
  color: var(--ct-text, #f8fafc) !important;
  text-decoration: none !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  background: transparent !important;
  cursor: pointer !important;
  transition: all 0.12s ease !important;
}

.ct-dropdown-list .dropdown-item:hover {
  background: var(--ct-surface-hover, rgba(148,163,184,0.08)) !important;
  color: var(--ct-primary, #2563eb) !important;
  transform: translateY(-1px) !important;
}

.ct-dropdown-list .dropdown-item.active {
  color: var(--ct-primary, #2563eb) !important;
  background: var(--ct-primary-light, rgba(37,99,235,0.12)) !important;
  font-weight: 600 !important;
}

.ct-dropdown-list .ct-dropdown-divider {
  height: 1px;
  background: var(--ct-border, rgba(148,163,184,0.1));
  margin: 4px 0;
}

/* 22. MultiSelectList custom styling */
.multiselect-list .form-control {
  position: relative !important;
  background-color: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text, #f8fafc) !important;
  border-top: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-right: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-bottom: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-left: 3px solid var(--ct-primary, #2563eb) !important;
  border-radius: 6px !important;
  height: 30px !important;
  padding: 4px 26px 4px 8px !important;
  display: flex !important;
  align-items: center !important;
  cursor: pointer !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  text-align: left !important;
  transition: all 0.2s ease !important;
  box-shadow: none !important;
}

[dir="rtl"] .multiselect-list .form-control {
  padding: 4px 8px 4px 26px !important;
}

.multiselect-list .form-control:hover {
  background-color: var(--ct-surface-hover, rgba(148,163,184,0.08)) !important;
  border-color: var(--ct-primary, #2563eb) !important;
}

.multiselect-list .dropdown-menu {
  background: var(--ct-surface-bg, #112b15) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  border-left: 3px solid var(--ct-primary, #2563eb) !important;
  border-radius: 8px !important;
  padding: 6px !important;
  box-shadow: var(--ct-shadow-lg, 0 8px 32px rgba(0,0,0,0.45)) !important;
}

.multiselect-list .dropdown-input-wrapper {
  padding: 0 0 6px !important;
  border-bottom: 1px solid var(--ct-border, rgba(148,163,184,0.1)) !important;
  margin-bottom: 4px !important;
}

.multiselect-list .dropdown-input-wrapper input {
  width: 100% !important;
  height: 28px !important;
  padding: 5px 8px !important;
  background: var(--ct-bg-elevated, #0f172a) !important;
  color: var(--ct-text, #f8fafc) !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.2)) !important;
  border-left: 2px solid var(--ct-primary, #2563eb) !important;
  border-radius: 5px !important;
  font-size: 0.8rem !important;
  outline: none !important;
}

.multiselect-list .selectable-items {
  max-height: 220px !important;
  overflow-y: auto !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 2px !important;
  margin-bottom: 6px !important;
}

.multiselect-list .selectable-item {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  padding: 7px 10px !important;
  border-radius: 5px !important;
  font-size: 0.8125rem !important;
  color: var(--ct-text, #f8fafc) !important;
  cursor: pointer !important;
  transition: all 0.12s ease !important;
  border-bottom: none !important;
}

.multiselect-list .selectable-item:hover {
  background: var(--ct-surface-hover, rgba(148,163,184,0.08)) !important;
  color: var(--ct-primary, #2563eb) !important;
  transform: translateY(-1px) !important;
}

.multiselect-list .selectable-item.selected {
  color: var(--ct-primary, #2563eb) !important;
  background: var(--ct-primary-light, rgba(37,99,235,0.12)) !important;
  font-weight: 600 !important;
}

.multiselect-list .selectable-item .multiselect-check {
  display: flex !important;
  align-items: center !important;
  color: var(--ct-primary, #2563eb) !important;
}

.multiselect-list .dropdown-menu li.d-flex {
  padding: 4px 4px 0 4px !important;
  border-top: 1px solid var(--ct-border, rgba(148,163,184,0.1)) !important;
  gap: 6px !important;
}

.multiselect-list .dropdown-menu button.btn {
  height: 24px !important;
  font-size: 0.75rem !important;
  padding: 2px 8px !important;
  border-radius: 4px !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
}

.multiselect-list .dropdown-menu button.btn-secondary {
  background: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text-secondary, #94a3b8) !important;
}

.multiselect-list .dropdown-menu button.btn-primary {
  background: var(--ct-primary, #2563eb) !important;
  color: #fff !important;
}

/* 23. Gold Standard Dropdown Footer & Buttons */
.ct-dropdown-footer {
  display: flex !important;
  justify-content: flex-end !important;
  padding: 6px 8px !important;
  border-top: 1px solid var(--ct-border, rgba(148,163,184,0.1)) !important;
  gap: 6px !important;
  background: var(--ct-bg-elevated, #111827) !important;
  border-bottom-left-radius: 6px !important;
  border-bottom-right-radius: 6px !important;
  margin-top: 4px !important;
}

.ct-dropdown-footer .btn {
  height: 24px !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  padding: 2px 8px !important;
  border-radius: 4px !important;
  border: 1px solid var(--ct-border, rgba(148,163,184,0.18)) !important;
  transition: all 0.15s ease !important;
  cursor: pointer !important;
  box-shadow: none !important;
}

.ct-dropdown-footer .ct-btn-select-all {
  background: var(--ct-bg-elevated, #111827) !important;
  color: var(--ct-text-secondary, #94a3b8) !important;
}

.ct-dropdown-footer .ct-btn-select-all:hover {
  background: var(--ct-bg-hover, rgba(255,255,255,0.08)) !important;
  border-color: var(--ct-primary, #2563eb) !important;
  color: var(--ct-text, #f8fafc) !important;
}

.ct-dropdown-footer .ct-btn-clear-all {
  background: var(--ct-primary, #2563eb) !important;
  color: #fff !important;
  border-color: var(--ct-primary, #2563eb) !important;
}

.ct-dropdown-footer .ct-btn-clear-all:hover {
  background: var(--ct-primary-hover, #1d4ed8) !important;
  box-shadow: 0 0 8px rgba(37,99,235,0.3) !important;
}

`;

	var style = document.createElement("style");
	style.id = styleId;
	style.textContent = css;
	document.head.appendChild(style);

	// Minimal JS for SPA navigation re-application
	function reapply() {
		// Re-apply CSS variables if theme changed
		var root = document.documentElement;
		if (!getComputedStyle(root).getPropertyValue("--ct-bg-elevated")) {
			// Theme not loaded yet, retry
			setTimeout(reapply, 500);
			return;
		}
		console.log("[CT-Filter] CSS injected, variables available");
	}

	// Run on load
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", reapply);
	} else {
		reapply();
	}

	// Observe for SPA navigation
	var observer = new MutationObserver(function () {
		if (!document.getElementById(styleId)) {
			document.head.appendChild(style);
		}
	});
	observer.observe(document.head, { childList: true });
})();
