/**
 * CT Link Control Global Auto-Enhancer — Phase 3 (Safe Unified Dropdown)
 *
 * Strategy: POST-RENDER overlay approach.
 * We hide the native .link-field element and render a unified dropdown button
 * and glassmorphic fixed menu that behaves identically to the theme switcher.
 *
 * Data layer is completely untouched — native input validation and event loops remain intact.
 */

(function () {
    "use strict";

    const CT_ATTR = "data-ct-link-enhanced";

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

    function enhanceLink(el) {
        if (!el || el.getAttribute(CT_ATTR)) return;

        const $el = $(el);
        if ($el.hasClass('hasDatepicker') || $el.attr('data-fieldtype') === 'Date' || 
            $el.attr('type') === 'date' || 
            $el.closest('.frappe-control[data-fieldtype="Date"]').length || 
            $el.closest('.frappe-control[data-fieldtype="DateRange"]').length || 
            $el.closest('.frappe-control[data-fieldtype="Datetime"]').length ||
            /date/i.test($el.attr('name') || '') || 
            /date/i.test($el.attr('data-fieldname') || '')) {
            return;
        }

        const field = getControlInstance(el);
        if (!field || field.df.fieldtype !== "Link") return;

        const df = field.df;
        if (df.hidden || df.read_only) return;
        if (!df.options || typeof df.options !== "string") return;

        // Skip internal system link types
        const skipDoctypes = ["DocType", "DocField", "Workflow State", "Module Def", "Role"];
        if (skipDoctypes.includes(df.options)) return;

        el.setAttribute(CT_ATTR, "1");

        const $input = $(el);
        const $linkFieldWrapper = $input.closest('.link-field');
        if (!$linkFieldWrapper.length) return;

        const $parent = $linkFieldWrapper.parent();
        $parent.css("position", "relative");

        const uid = "ctl-" + Math.random().toString(36).slice(2, 8);

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
            const promise = field.set_value("");
            if (promise && promise.then) {
                promise.then(() => { syncLabel(); closeDropdown(); });
            } else {
                syncLabel();
                closeDropdown();
            }
        });

        $selectAllBtn.on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $firstItem = $list.find('.dropdown-item[data-value]').first();
            if ($firstItem.length) {
                $firstItem.trigger('click');
            } else {
                closeDropdown();
            }
        });

        // Sync label from current select value
        function syncLabel() {
            const val = field.get_value() || "";
            const text = field.get_label_value() || val;
            const placeholder = field.df.label ? __(field.df.label) : __("Select…");
            $label.text(text || placeholder);
        }
        syncLabel();

        function syncGridQuery() {
            const cascadeFields = ["boq_header", "boq_structure", "boq_item", "boq_item_stage"];
            if (!cascadeFields.includes(field.df.fieldname)) return;

            const $gridRow = $input.closest(".grid-row");
            const gridRow = $gridRow.data("grid_row");
            const grid = gridRow && gridRow.grid;
            if (!grid || !grid.get_field) return;

            const gridField = grid.get_field(field.df.fieldname);
            if (gridField && gridField.get_query) {
                field.get_query = gridField.get_query;
            }
        }

        function getScope() {
            if (window.scopeContext && window.scopeContext.enabled) {
                return window.scopeContext.getCurrentScope() || {};
            }
            return (frappe.boot.scope_context && frappe.boot.scope_context.current) || {};
        }

        function withScope(filters) {
            const mode = frappe.boot.enable_boq_cascade_filtering || "Off";
            if (!["On", "Strict"].includes(mode)) return filters;

            const scope = getScope();
            ["company", "cost_center", "project"].forEach((fieldname) => {
                if (scope[fieldname] && !filters[fieldname]) {
                    filters[fieldname] = scope[fieldname];
                }
            });
            filters.enforce_scope = true;
            return filters;
        }

        function getCurrentGridRowDoc() {
            const $gridRow = $input.closest(".grid-row");
            const gridRow = $gridRow.data("grid_row");
            return (gridRow && gridRow.doc) || field.doc || null;
        }

        function getBoqCascadeSearchArgs(searchTerm) {
            const row = getCurrentGridRowDoc();
            const fieldname = field.df.fieldname;
            const cascadeFields = ["boq_header", "boq_structure", "boq_item", "boq_item_stage"];
            if (!cascadeFields.includes(fieldname)) return null;

            const args = {
                txt: searchTerm || "",
                doctype: field.df.options,
                reference_doctype: (row && row.doctype) || field.doctype || "",
                page_length: cint(frappe.boot.sysdefaults?.link_field_results_limit) || 10,
                link_fieldname: fieldname,
            };
            const filters = {};

            if (fieldname === "boq_header") {
                args.query = "construction.api.boq_link_queries.get_boq_headers";
            } else if (fieldname === "boq_structure") {
                args.query = "construction.api.boq_link_queries.get_boq_structures";
                if (row && row.boq_header) filters.boq_header = row.boq_header;
            } else if (fieldname === "boq_item") {
                args.query = "construction.api.boq_link_queries.get_boq_items";
                if (row && row.project) filters.project = row.project;
                if (row && row.boq_header) filters.boq_header = row.boq_header;
                if (row && row.boq_structure) filters.structure = row.boq_structure;
                filters.require_boq_header = true;
                filters.require_structure = true;
                filters.allowed_statuses = ["Frozen", "Locked"];
            } else if (fieldname === "boq_item_stage") {
                args.query = "construction.api.boq_link_queries.get_boq_item_stages";
                if (row && row.boq_item) filters.boq_item = row.boq_item;
                if (row && row.boq_header) filters.boq_header = row.boq_header;
                if (row && row.boq_structure) filters.structure = row.boq_structure;
                filters.require_boq_item = true;
            }

            args.filters = withScope(filters);
            return args;
        }

        // Render search options from database
        function renderOptions(searchTerm) {
            $list.html(`<div style="padding: 10px; text-align: center; color: var(--ct-text-muted);"><i class="fa fa-spinner fa-spin"></i> ${__("Loading...")}</div>`);

            syncGridQuery();
            const args = getBoqCascadeSearchArgs(searchTerm) || field.get_search_args(searchTerm || "");
            if (!args) {
                $list.html(`<div style="padding: 10px; color: var(--ct-text-muted); font-style: italic;">${__("No options available")}</div>`);
                return;
            }

            frappe.call({
                type: "GET",
                method: "frappe.desk.search.search_link",
                args: args,
                no_spinner: true,
                callback: function (r) {
                    $list.empty();
                    const items = r.message || [];

                    // 1. None / Clear option (for optional fields)
                    if (!df.reqd) {
                        const $noneItem = $(`
                            <a class="dropdown-item" href="#" style="font-style: italic; color: var(--ct-text-muted);">
                                — ${__("None")} —
                            </a>
                        `);
                        $noneItem.on("click", function (e) {
                            e.preventDefault();
                            const promise = field.set_value("");
                            if (promise && promise.then) {
                                promise.then(() => { syncLabel(); closeDropdown(); });
                            } else {
                                syncLabel();
                                closeDropdown();
                            }
                        });
                        $list.append($noneItem);
                    }

                    // 2. Options list
                    let count = 0;
                    items.forEach(item => {
                        const val = item.value;
                        const labelText = item.label || val;
                        const isSelected = val === field.get_value();

                        const $itemEl = $(`
                            <a class="dropdown-item ${isSelected ? 'active' : ''}" href="#" data-value="${val}">
                                ${frappe.utils.escape_html(labelText)}
                            </a>
                        `);

                        $itemEl.on("click", function (e) {
                            e.preventDefault();
                            const promise = field.set_value(val);
                            if (promise && promise.then) {
                                promise.then(() => { syncLabel(); closeDropdown(); });
                            } else {
                                syncLabel();
                                closeDropdown();
                            }
                        });

                        $list.append($itemEl);
                        count++;
                    });

                    // 3. Create New item (if allowed)
                    const doctype = df.options;
                    if (!df.only_select && frappe.model.can_create(doctype)) {
                        if (count > 0 && !df.reqd) {
                            $list.append('<div class="ct-dropdown-divider"></div>');
                        }
                        const $newItem = $(`
                            <a class="dropdown-item" href="#" style="font-weight: 600; color: var(--ct-primary);">
                                <i class="fa fa-plus"></i> ${__("Create a new {0}", [__(doctype)])}…
                            </a>
                        `);
                        $newItem.on("click", function (e) {
                            e.preventDefault();
                            closeDropdown();
                            field.new_doc();
                        });
                        $list.append($newItem);
                    } else if (count === 0 && df.reqd) {
                        $list.append(`<div style="padding: 10px; color: var(--ct-text-muted); font-style: italic;">${__("No results")}</div>`);
                    }
                }
            });
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
            renderOptions("");
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

        // Search filtering (debounced)
        let searchTimeout = null;
        $search.on("input", function () {
            clearTimeout(searchTimeout);
            const term = $(this).val();
            searchTimeout = setTimeout(() => {
                renderOptions(term);
            }, 300);
        });

        // Native events synchronization
        $input.on("change select-change", syncLabel);
        $input.on("focus", function () {
            openDropdown();
        });

        // Hide native input wrapper visually
        $linkFieldWrapper.css({ opacity: 0, position: "absolute", pointerEvents: "none", zIndex: -1, width: 0, height: 0, overflow: "hidden" });
    }

    function scanAndEnhance() {
        // Restrict strictly to elements inside .frappe-control[data-fieldtype='Link']
        // to avoid matching Date inputs or other non-Link input elements.
        $(".frappe-control[data-fieldtype='Link'] input.form-control")
            .each(function () {
                try { enhanceLink(this); } catch (e) { /* silent */ }
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

    // Expose enhancer functions
    frappe.provide("construction.ct_link_enhancer");
    construction.ct_link_enhancer.scan = scanAndEnhance;
    construction.ct_link_enhancer.enhanceLink = enhanceLink;

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
