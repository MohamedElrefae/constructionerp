/**
 * CT Select & MultiSelectList Control Override — Phase 2 (Safe Unified Dropdown)
 *
 * Strategy: POST-RENDER, non-invasive overlay approach.
 * We do NOT monkey-patch make_input.
 * Instead, we wait for select and multiselect elements to appear in the DOM
 * and wrap/style them matching the Construction theme selectors.
 *
 * Data layer is UNTOUCHED — the native controls stay fully functional.
 */

(function () {
    "use strict";

    const CT_ATTR = "data-ct-sel-enhanced";
    const CT_MULTI_ATTR = "data-ct-multisel-enhanced";
    const CT_STYLE_ID = "ct-select-dropdown-sizing-fix-v1";

    if (!document.getElementById(CT_STYLE_ID)) {
        const style = document.createElement("style");
        style.id = CT_STYLE_ID;
        style.textContent = `
            .ct-unified-dropdown .ct-dropdown-menu {
                max-height: min(65vh, 420px) !important;
                overflow: hidden !important;
                z-index: 10020 !important;
            }
            .ct-unified-dropdown .ct-dropdown-search-wrapper {
                padding: 8px !important;
            }
            .ct-unified-dropdown .ct-dropdown-search {
                min-height: 34px !important;
            }
            .ct-unified-dropdown .ct-dropdown-list {
                max-height: min(52vh, 340px) !important;
                overflow-y: auto !important;
            }
            .ct-unified-dropdown .ct-dropdown-list .dropdown-item {
                min-height: 32px !important;
                line-height: 1.3 !important;
                white-space: normal !important;
            }
        `;
        document.head.appendChild(style);
    }

    function getControlInstance(el) {
        const $el = $(el);
        const $control_wrapper = $el.closest('.frappe-control');
        if ($control_wrapper.length) {
            // 1. Direct DOM node reference (Gold Standard)
            if ($control_wrapper[0].fieldobj) {
                return $control_wrapper[0].fieldobj;
            }

            // 2. Fallbacks for other context environments
            const fieldname = $control_wrapper.attr('data-fieldname');
            if (fieldname) {
                const $grid_row = $el.closest('.grid-row');
                if ($grid_row.length) {
                    const grid_row_obj = $grid_row.data('grid_row');
                    if (grid_row_obj && grid_row_obj.fields_dict && grid_row_obj.fields_dict[fieldname]) {
                        return grid_row_obj.fields_dict[fieldname];
                    }
                }
                if (window.cur_frm && cur_frm.fields_dict && cur_frm.fields_dict[fieldname]) {
                    return cur_frm.fields_dict[fieldname];
                }
                if (window.cur_dialog && cur_dialog.fields_dict && cur_dialog.fields_dict[fieldname]) {
                    return cur_dialog.fields_dict[fieldname];
                }
                if (window.cur_list && cur_list.page && cur_list.page.fields_dict && cur_list.page.fields_dict[fieldname]) {
                    return cur_list.page.fields_dict[fieldname];
                }
            }
        }
        if (frappe.query_report && frappe.query_report.filters) {
            const fieldname = $el.attr('data-fieldname') || $control_wrapper.attr('data-fieldname');
            const filter = frappe.query_report.filters.find(f => f.df.fieldname === fieldname);
            if (filter) return filter;
        }
        return null;
    }

    // Enhance standard <select> elements
    function enhanceSelect(el) {
        if (!el || el.getAttribute(CT_ATTR)) return;
        if (el.disabled || el.getAttribute("data-fieldtype") === "docstatus") return;

        const $select = $(el);
        if ($select.hasClass('hasDatepicker') || $select.attr('data-fieldtype') === 'Date' || 
            $select.attr('type') === 'date' || 
            $select.closest('.frappe-control[data-fieldtype="Date"]').length || 
            $select.closest('.frappe-control[data-fieldtype="DateRange"]').length || 
            $select.closest('.frappe-control[data-fieldtype="Datetime"]').length ||
            /date/i.test($select.attr('name') || '') || 
            /date/i.test($select.attr('data-fieldname') || '')) {
            return;
        }

        // Skip check fields and hidden selects
        if ($select.closest("[data-fieldtype='Check']").length) return;
        if (!$select.is(":visible") && !$select.closest(".page-form, .filters-form").length) return;

        el.setAttribute(CT_ATTR, "1");

        const uid = "cts-" + Math.random().toString(36).slice(2, 8);
        const $parent = $select.parent();
        $parent.css("position", "relative");

        const field = getControlInstance(el);

        // Unified Dropdown HTML structure
        const $dropdown = $(`
            <div class="dropdown ct-unified-dropdown" id="${uid}">
                <button class="btn-reset dropdown-toggle ct-dropdown-btn" type="button" aria-haspopup="true" aria-expanded="false">
                    <span class="ct-dropdown-label"></span>
                    <svg width="10" height="7" viewBox="0 0 10 7" fill="none" style="transition: transform 0.2s ease;">
                        <path d="M1 1l4 4.5L9 1" stroke="var(--ct-primary)" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                </button>
                <div class="dropdown-menu ct-dropdown-menu">
                    <div class="ct-dropdown-search-wrapper">
                        <input type="text" class="ct-dropdown-search" placeholder="${__("Search…")}" autocomplete="off">
                    </div>
                    <div class="ct-dropdown-list"></div>
                    <div class="ct-dropdown-footer d-flex justify-content-end">
                        <button class="btn btn-secondary btn-xs ct-btn-select-all text-nowrap">
                            ${__("Select All")}
                        </button>
                        <button class="btn btn-primary btn-xs ct-btn-clear-all text-nowrap">
                            ${__("Clear All")}
                        </button>
                    </div>
                </div>
            </div>
        `);

        $parent.append($dropdown);

        const $btn = $dropdown.find(".ct-dropdown-btn");
        const $label = $dropdown.find(".ct-dropdown-label");
        const $menu = $dropdown.find(".ct-dropdown-menu");
        const $search = $dropdown.find(".ct-dropdown-search");
        const $list = $dropdown.find(".ct-dropdown-list");
        const $selectAllBtn = $dropdown.find(".ct-btn-select-all");
        const $clearAllBtn = $dropdown.find(".ct-btn-clear-all");

        $clearAllBtn.on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            $select.val("").trigger("change").trigger("select-change");
            syncLabel();
            closeDropdown();
        });

        $selectAllBtn.on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $firstOption = $select.find("option").filter(function() {
                return $(this).val() !== "";
            }).first();
            if ($firstOption.length) {
                $select.val($firstOption.val()).trigger("change").trigger("select-change");
                syncLabel();
            }
            closeDropdown();
        });

        // Sync label from current select value
        function syncLabel() {
            const selected = $select.find("option:selected").text().trim();
            const placeholder = field && field.df && field.df.label ? __(field.df.label) : __("Select…");
            $label.text(selected || placeholder);
        }
        syncLabel();

        // Render list items
        function renderList(filterText) {
            $list.empty();
            let count = 0;
            $select.find("option").each(function () {
                const val = $(this).val();
                const text = $(this).text().trim();
                if (filterText && !text.toLowerCase().includes(filterText.toLowerCase())) return;

                const isSelected = val === $select.val();
                const $itemEl = $(`
                    <a class="dropdown-item ${isSelected ? 'active' : ''}" href="#" data-value="${val}">
                        ${frappe.utils.escape_html(text)}
                    </a>
                `);

                $itemEl.on("click", function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    $select.val(val).trigger("change").trigger("select-change");
                    syncLabel();
                    closeDropdown();
                });

                $list.append($itemEl);
                count++;
            });

            if (count === 0) {
                $list.append(`<div style="padding: 10px; color: var(--ct-text-muted); font-style: italic;">${__("No results")}</div>`);
            }
        }

        // Position and open dropdown
        function openDropdown() {
            $(".ct-dropdown-menu:visible").hide();
            const rect = $btn[0].getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            const menuH = 280;

            $menu.css({
                display: "block",
                top: spaceBelow > menuH ? (rect.bottom + 2) + "px" : (rect.top - menuH - 2) + "px",
                left: rect.left + "px",
                width: Math.max(rect.width, 220) + "px",
            });
            $btn.find('svg').css('transform', 'rotate(180deg)');
            $search.val("").focus();
            renderList("");
        }

        function closeDropdown() {
            $menu.hide();
            $btn.find('svg').css('transform', 'none');
        }

        $btn.on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if ($menu.is(":visible")) {
                closeDropdown();
            } else {
                openDropdown();
            }
        });

        // Close on outside click
        $(document).on("click.ct-dropdown-" + uid, function (e) {
            if (!$dropdown.is(e.target) && !$dropdown.has(e.target).length) {
                closeDropdown();
            }
        });

        // Search filtering
        $search.on("input", function () {
            renderList($(this).val());
        });

        // Native events synchronization
        $select.on("change select-change", syncLabel);
        $select.on("focus", function () {
            openDropdown();
        });

        // Hide native select visually
        $select.css({ opacity: 0, position: "absolute", pointerEvents: "none", zIndex: -1, width: 0, height: 0, overflow: "hidden" });
    }

    // Enhance MultiSelectList elements
    function enhanceMultiSelect(el) {
        if (!el || el.getAttribute(CT_MULTI_ATTR)) return;

        const field = getControlInstance(el);
        if (!field || field.df.fieldtype !== "MultiSelectList") return;

        el.setAttribute(CT_MULTI_ATTR, "1");

        const $wrapper = $(el);

        // Override placeholder getter to output field translated name
        field.get_placeholder_text = function() {
            return `<span class="text-extra-muted">${__(this.df.label || "Select…")}</span>`;
        };
        // Re-trigger update_status to force render correct placeholder
        field.update_status();

        // Inject Chevron SVG into trigger button
        const $trigger = $wrapper.find('.form-control');
        $trigger.css("position", "relative");
        if (!$trigger.find('svg').length) {
            $trigger.append(`
                <svg width="10" height="7" viewBox="0 0 10 7" fill="none" style="
                  position: absolute; right: 10px; top: 12px; pointer-events: none;
                  transition: transform 0.2s ease;">
                    <path d="M1 1l4 4.5L9 1" stroke="var(--ct-primary)" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
            `);
        }
    }

    // Reposition MultiSelectList dropdown menus fixedly when opened
    $(document).on("show.bs.dropdown", ".multiselect-list.dropdown", function () {
        const $wrapper = $(this);
        const $btn = $wrapper.find('[data-toggle="dropdown"]');
        const $menu = $wrapper.find('.dropdown-menu');

        const rect = $btn[0].getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const menuH = 280;

        $menu.css({
            position: 'fixed',
            top: spaceBelow > menuH ? (rect.bottom + 2) + 'px' : (rect.top - menuH - 2) + 'px',
            left: rect.left + 'px',
            width: Math.max(rect.width, 220) + 'px',
            right: 'auto',
            bottom: 'auto',
            transform: 'none',
            zIndex: 10000
        });

        // Rotate chevron when dropdown is open
        $btn.find('svg').css('transform', 'rotate(180deg)');
    });

    $(document).on("hide.bs.dropdown", ".multiselect-list.dropdown", function () {
        const $wrapper = $(this);
        const $btn = $wrapper.find('[data-toggle="dropdown"]');
        $btn.find('svg').css('transform', 'none');
    });

    function scanAndEnhance() {
        // Enhance <select> fields
        $(".frappe-control[data-fieldtype='Select'] select.form-control")
            .each(function () {
                try { enhanceSelect(this); } catch (e) { /* silent */ }
            });

        // Enhance MultiSelectList fields
        $(".frappe-control[data-fieldtype='MultiSelectList'] .multiselect-list")
            .each(function () {
                try { enhanceMultiSelect(this); } catch (e) { /* silent */ }
            });
    }

    // Bind events
    $(document).on("page-change", function () {
        setTimeout(scanAndEnhance, 400);
    });

    $(document).on("form-refresh", function () {
        setTimeout(scanAndEnhance, 300);
    });

    // Initial scan after boot
    $(document).ready(function () {
        setTimeout(scanAndEnhance, 800);

        // Patch query_report to re-scan after filters render
        const _orig = frappe.views && frappe.views.QueryReport && frappe.views.QueryReport.prototype;
        if (_orig && _orig.setup_filters) {
            const __sf = _orig.setup_filters;
            _orig.setup_filters = function () {
                const r = __sf.call(this);
                setTimeout(scanAndEnhance, 500);
                return r;
            };
        }
    });

    // Expose scan method
    frappe.provide("construction.ct_select_enhancer");
    construction.ct_select_enhancer.scan = scanAndEnhance;

    // Dynamic DOM mutation scanning to enhance dynamic filters/fields
    if (typeof MutationObserver !== "undefined") {
        const observer = new MutationObserver(function () {
            try { scanAndEnhance(); } catch (e) { /* silent */ }
        });
        $(document).ready(function () {
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }
})();
