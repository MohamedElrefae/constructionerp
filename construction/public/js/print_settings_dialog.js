// Print Settings Dialog — Column Configuration & Preview
// Pure-logic ColumnConfigManager + UI components (added in later tasks)

/**
 * ColumnConfigManager
 *
 * Manages column configuration state for the Print Settings Dialog.
 * Pure logic — no DOM access. Suitable for both browser and Node.js.
 *
 * @param {ColumnDescriptor[]} descriptors - Default column definitions
 * @param {ColumnConfig[]|null} [saved_settings=null] - Previously saved config, or null for defaults
 */
class ColumnConfigManager {
    constructor(descriptors, saved_settings) {
        this._columns = [];
        this._init(descriptors || [], saved_settings || null);
    }

    /**
     * Initialise internal column list by merging descriptors with optional saved settings.
     */
    _init(descriptors, saved_settings) {
        if (!saved_settings) {
            // No saved settings — use descriptor defaults
            this._columns = descriptors.map(function (d) {
                return {
                    field_key: d.field_key,
                    label: d.label,
                    width: d.default_width,
                    visible: d.default_visible,
                    sort_order: d.default_sort_order
                };
            });
        } else {
            // Build a lookup from saved settings keyed by field_key
            var saved_map = {};
            saved_settings.forEach(function (s) {
                saved_map[s.field_key] = s;
            });

            this._columns = descriptors.map(function (d) {
                var saved = saved_map[d.field_key];
                if (saved) {
                    return {
                        field_key: d.field_key,
                        label: saved.label !== undefined ? saved.label : d.label,
                        width: saved.width !== undefined ? saved.width : d.default_width,
                        visible: saved.visible !== undefined ? saved.visible : d.default_visible,
                        sort_order: saved.sort_order !== undefined ? saved.sort_order : d.default_sort_order
                    };
                }
                // No saved entry for this descriptor — use defaults
                return {
                    field_key: d.field_key,
                    label: d.label,
                    width: d.default_width,
                    visible: d.default_visible,
                    sort_order: d.default_sort_order
                };
            });
        }
    }

    /**
     * Return all columns sorted by sort_order.
     * @returns {ColumnConfig[]}
     */
    get_config() {
        return this._columns.slice().sort(function (a, b) {
            return a.sort_order - b.sort_order;
        });
    }

    /**
     * Toggle a column's visibility.
     * @param {string} field_key
     * @param {boolean} visible
     */
    set_visibility(field_key, visible) {
        var col = this._find(field_key);
        if (col) {
            col.visible = !!visible;
        }
    }

    /**
     * Set a column's width. Must be in [1, 100].
     * @param {string} field_key
     * @param {number} width
     * @returns {boolean} true if accepted, false if rejected
     */
    set_width(field_key, width) {
        if (typeof width !== 'number' || width < 1 || width > 100) {
            return false;
        }
        var col = this._find(field_key);
        if (col) {
            col.width = width;
            return true;
        }
        return false;
    }

    /**
     * Move a column from one position to another and recalculate sort_order
     * as a consecutive 0-based sequence.
     * @param {number} from_index - Current position index (in sorted order)
     * @param {number} to_index   - Target position index (in sorted order)
     */
    reorder(from_index, to_index) {
        var sorted = this.get_config();
        if (from_index < 0 || from_index >= sorted.length ||
            to_index < 0 || to_index >= sorted.length) {
            return;
        }
        if (from_index === to_index) {
            return;
        }

        // Remove the item and re-insert at the target position
        var item = sorted.splice(from_index, 1)[0];
        sorted.splice(to_index, 0, item);

        // Reassign consecutive sort_order values and write back
        var key_to_order = {};
        sorted.forEach(function (col, idx) {
            key_to_order[col.field_key] = idx;
        });
        this._columns.forEach(function (col) {
            col.sort_order = key_to_order[col.field_key];
        });
    }

    /**
     * Return only visible columns, sorted by sort_order.
     * @returns {ColumnConfig[]}
     */
    get_visible_columns() {
        return this.get_config().filter(function (col) {
            return col.visible;
        });
    }

    /**
     * Sum of widths for all visible columns.
     * @returns {number}
     */
    get_width_total() {
        return this._columns.reduce(function (sum, col) {
            return col.visible ? sum + col.width : sum;
        }, 0);
    }

    /**
     * Whether at least one column is visible.
     * @returns {boolean}
     */
    has_visible_columns() {
        return this._columns.some(function (col) {
            return col.visible;
        });
    }

    /**
     * Reset all columns to descriptor defaults.
     * @param {ColumnDescriptor[]} descriptors
     */
    reset(descriptors) {
        this._init(descriptors || [], null);
    }

    /**
     * Serialize current config to a JSON string (sorted by sort_order).
     * @returns {string}
     */
    to_json() {
        return JSON.stringify(this.get_config());
    }

    // ---- internal helpers ----

    _find(field_key) {
        for (var i = 0; i < this._columns.length; i++) {
            if (this._columns[i].field_key === field_key) {
                return this._columns[i];
            }
        }
        return null;
    }
}

/**
 * PreviewPanel
 *
 * Renders a sample HTML table preview of the current column configuration.
 * Pure DOM manipulation — no Frappe dependencies. Suitable for Node.js testing
 * with a simple DOM mock (e.g. jsdom or a plain object with innerHTML).
 *
 * @param {HTMLElement} container_el - DOM element to render the preview into
 */
class PreviewPanel {
    constructor(container_el) {
        this._container = container_el;
    }

    /**
     * Build and render an HTML <table> reflecting the given visible columns
     * and sample data.
     *
     * @param {ColumnConfig[]} visible_columns - Columns to display (already filtered to visible, sorted by sort_order)
     * @param {Object[]} [sample_data] - Optional array of row objects; keys are field_keys
     */
    render(visible_columns, sample_data) {
        var cols = visible_columns || [];
        var rows = sample_data && sample_data.length > 0 ? sample_data.slice(0, 5) : null;

        var html = '<table class="preview-table" style="width:100%;border-collapse:collapse;">';

        // Header row
        html += '<thead><tr>';
        for (var i = 0; i < cols.length; i++) {
            html += '<th style="width:' + cols[i].width + '%">' + this._escape(cols[i].label) + '</th>';
        }
        html += '</tr></thead>';

        // Body rows
        html += '<tbody>';
        if (rows) {
            for (var r = 0; r < rows.length; r++) {
                html += '<tr>';
                for (var c = 0; c < cols.length; c++) {
                    var val = rows[r][cols[c].field_key];
                    html += '<td>' + (val !== undefined && val !== null ? this._escape(String(val)) : '') + '</td>';
                }
                html += '</tr>';
            }
        } else {
            // Placeholder row using column labels as cell content
            html += '<tr>';
            for (var p = 0; p < cols.length; p++) {
                html += '<td>' + this._escape(cols[p].label) + '</td>';
            }
            html += '</tr>';
        }
        html += '</tbody>';

        html += '</table>';

        this._container.innerHTML = html;
    }

    /**
     * Basic HTML entity escaping for safe rendering.
     * @param {string} str
     * @returns {string}
     */
    _escape(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

/**
 * PrintSettingsDialog
 *
 * Main entry point — wraps a frappe.ui.Dialog and orchestrates
 * ColumnConfigManager + PreviewPanel sub-components.
 *
 * @param {Object} opts
 * @param {string} opts.report_type        — e.g. "BOQ_Full", "BOQ_Header"
 * @param {ColumnDescriptor[]} opts.columns — default column definitions
 * @param {Object[]} [opts.sample_data]     — up to 5 rows for preview
 * @param {Function} opts.export_callback   — fn(column_config: ColumnConfig[]) => Promise
 */
class PrintSettingsDialog {
    constructor(opts) {
        this.report_type = opts.report_type;
        this.columns = opts.columns || [];
        this.sample_data = opts.sample_data || [];
        this.export_callback = opts.export_callback;
        this.config_manager = null;
        this.preview_panel = null;
        this.dialog = null;
        this._debounce_timer = null;
    }

    /**
     * Build and show the Frappe dialog with column config panel,
     * preview panel, and action buttons.
     */
    show() {
        var self = this;

        // Load saved settings, then build the dialog
        var saved_settings = this._load_settings();
        this.config_manager = new ColumnConfigManager(this.columns, saved_settings);

        // Build dialog body HTML
        var body_html = this._build_body_html();

        this.dialog = new frappe.ui.Dialog({
            title: __('Print Settings'),
            size: 'extra-large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'print_settings_body',
                    options: body_html
                }
            ],
            primary_action_label: __('Export'),
            primary_action: function () {
                self._on_export();
            },
            secondary_action_label: __('Cancel'),
            secondary_action: function () {
                self.dialog.hide();
            }
        });

        // Add custom action buttons
        this.dialog.add_custom_action(
            __('Save Settings'),
            function () { self._save_settings(); },
            'btn-secondary-dark'
        );
        this.dialog.add_custom_action(
            __('Reset to Defaults'),
            function () { self._reset_defaults(); },
            'btn-secondary-dark'
        );

        this.dialog.show();

        // After dialog is shown, wire up interactive elements
        this._wire_events();

        // Handle empty columns case
        if (!this.columns || this.columns.length === 0) {
            this._show_info_message(__('No columns available for configuration.'));
            this._set_export_enabled(false);
        }

        // Handle all columns hidden
        this._check_all_hidden();
    }

    /**
     * Build the dialog body HTML containing the column config panel,
     * width total display, and preview panel.
     * @returns {string}
     */
    _build_body_html() {
        var config = this.config_manager.get_config();
        var html = '<div class="print-settings-container">';

        // Column configuration panel
        html += '<div class="column-config-panel" style="margin-bottom:15px;">';
        html += '<h6 style="margin-bottom:10px;">' + __('Column Configuration') + '</h6>';
        html += '<div class="column-config-message" style="display:none;margin-bottom:10px;"></div>';
        html += '<div class="column-config-list">';

        for (var i = 0; i < config.length; i++) {
            html += this._build_column_row_html(config[i]);
        }

        html += '</div>'; // .column-config-list

        // Width total display
        html += '<div class="width-total-display" style="margin-top:10px;padding:5px 10px;background:#f5f5f5;border-radius:4px;">';
        html += '<strong>' + __('Total Width') + ':</strong> ';
        html += '<span class="width-total-value">' + this.config_manager.get_width_total() + '</span>%';
        html += '</div>';

        html += '</div>'; // .column-config-panel

        // Preview panel
        html += '<div class="preview-panel-section" style="margin-top:15px;">';
        html += '<h6 style="margin-bottom:10px;">' + __('Preview') + '</h6>';
        html += '<div class="preview-panel-container" style="overflow-x:auto;border:1px solid #d1d8dd;border-radius:4px;padding:10px;"></div>';
        html += '</div>';

        html += '</div>'; // .print-settings-container
        return html;
    }

    /**
     * Build HTML for a single column configuration row.
     * @param {ColumnConfig} col
     * @returns {string}
     */
    _build_column_row_html(col) {
        var checked = col.visible ? ' checked' : '';
        var html = '<div class="column-config-row" data-field-key="' + col.field_key + '" '
            + 'style="display:flex;align-items:center;padding:6px 8px;margin-bottom:4px;'
            + 'border:1px solid #d1d8dd;border-radius:4px;background:#fff;">';

        // Drag handle
        html += '<span class="drag-handle" style="cursor:grab;margin-right:10px;color:#8d99a6;">'
            + '<i class="fa fa-bars"></i></span>';

        // Visibility checkbox
        html += '<input type="checkbox" class="col-visible-check" data-field-key="' + col.field_key + '"'
            + checked + ' style="margin-right:10px;" />';

        // Label
        html += '<span class="col-label" style="flex:1;font-size:13px;">' + col.label + '</span>';

        // Width input
        html += '<input type="number" class="col-width-input" data-field-key="' + col.field_key + '" '
            + 'value="' + col.width + '" min="1" max="100" '
            + 'style="width:60px;text-align:center;margin-left:10px;" />';

        // Validation message area
        html += '<span class="col-validation-msg" data-field-key="' + col.field_key + '" '
            + 'style="color:red;font-size:11px;margin-left:8px;display:none;"></span>';

        html += '</div>';
        return html;
    }

    /**
     * Wire up event handlers for checkboxes, width inputs, and drag-and-drop.
     */
    _wire_events() {
        var self = this;
        var $body = this.dialog.$wrapper;

        // Initialize preview panel
        var preview_container = $body.find('.preview-panel-container')[0];
        if (preview_container) {
            this.preview_panel = new PreviewPanel(preview_container);
            this._update_preview();
        }

        // Checkbox change → set_visibility → debounced preview
        $body.on('change', '.col-visible-check', function () {
            var field_key = $(this).data('field-key');
            var visible = $(this).is(':checked');
            self.config_manager.set_visibility(field_key, visible);
            self._check_all_hidden();
            self._debounced_preview_update();
        });

        // Width input change → set_width → debounced preview
        $body.on('change input', '.col-width-input', function () {
            var field_key = $(this).data('field-key');
            var width = parseFloat($(this).val());
            var $msg = $body.find('.col-validation-msg[data-field-key="' + field_key + '"]');

            if (isNaN(width) || !self.config_manager.set_width(field_key, width)) {
                $msg.text(__('Width must be between 1 and 100')).show();
            } else {
                $msg.hide();
                self._update_width_total();
                self._debounced_preview_update();
            }
        });

        // Drag-and-drop via Sortable.js
        var list_el = $body.find('.column-config-list')[0];
        if (list_el && typeof Sortable !== 'undefined') {
            Sortable.create(list_el, {
                handle: '.drag-handle',
                animation: 150,
                onEnd: function (evt) {
                    self.config_manager.reorder(evt.oldIndex, evt.newIndex);
                    self._debounced_preview_update();
                }
            });
        }
    }

    /**
     * Debounced preview update (300ms).
     */
    _debounced_preview_update() {
        var self = this;
        if (this._debounce_timer) {
            clearTimeout(this._debounce_timer);
        }
        this._debounce_timer = setTimeout(function () {
            self._update_preview();
            self._update_width_total();
        }, 300);
    }

    /**
     * Re-render the preview panel with current config.
     */
    _update_preview() {
        if (this.preview_panel && this.config_manager) {
            this.preview_panel.render(
                this.config_manager.get_visible_columns(),
                this.sample_data
            );
        }
    }

    /**
     * Update the width total display.
     */
    _update_width_total() {
        if (this.dialog && this.config_manager) {
            this.dialog.$wrapper.find('.width-total-value')
                .text(this.config_manager.get_width_total());
        }
    }

    /**
     * Check if all columns are hidden and show warning / disable export.
     */
    _check_all_hidden() {
        if (!this.config_manager) return;

        if (this.columns && this.columns.length > 0 && !this.config_manager.has_visible_columns()) {
            this._show_warning_message(__('All columns are hidden. At least one column must be visible to export.'));
            this._set_export_enabled(false);
        } else if (this.columns && this.columns.length > 0) {
            this._clear_message();
            this._set_export_enabled(true);
        }
    }

    /**
     * Show an informational message in the config panel.
     * @param {string} msg
     */
    _show_info_message(msg) {
        if (!this.dialog) return;
        var $el = this.dialog.$wrapper.find('.column-config-message');
        $el.html('<div class="alert alert-info" style="margin:0;">' + msg + '</div>').show();
    }

    /**
     * Show a warning message in the config panel.
     * @param {string} msg
     */
    _show_warning_message(msg) {
        if (!this.dialog) return;
        var $el = this.dialog.$wrapper.find('.column-config-message');
        $el.html('<div class="alert alert-warning" style="margin:0;">' + msg + '</div>').show();
    }

    /**
     * Clear any message in the config panel.
     */
    _clear_message() {
        if (!this.dialog) return;
        this.dialog.$wrapper.find('.column-config-message').hide().html('');
    }

    /**
     * Enable or disable the primary Export button.
     * @param {boolean} enabled
     */
    _set_export_enabled(enabled) {
        if (!this.dialog) return;
        var $btn = this.dialog.$wrapper.find('.btn-primary-dark, .btn-primary');
        if (enabled) {
            $btn.prop('disabled', false).removeClass('disabled');
        } else {
            $btn.prop('disabled', true).addClass('disabled');
        }
    }

    /**
     * Load saved settings for the current report_type from localStorage.
     * @returns {ColumnConfig[]|null}
     */
    _load_settings() {
        try {
            var storage_key = 'PrintSettings:' + this.report_type;
            var saved = localStorage.getItem(storage_key);
            if (saved) {
                var parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    return parsed;
                }
            }
        } catch (e) {
            console.warn('PrintSettingsDialog: Failed to load settings', e);
        }
        return null;
    }

    /**
     * Persist current Column_Configuration to localStorage,
     * keyed by "PrintSettings:{report_type}".
     */
    _save_settings() {
        try {
            var storage_key = 'PrintSettings:' + this.report_type;
            var config_json = this.config_manager.to_json();
            localStorage.setItem(storage_key, config_json);
            frappe.show_alert({ message: __('Settings saved.'), indicator: 'green' }, 3);
        } catch (e) {
            console.error('PrintSettingsDialog: Failed to save settings', e);
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to save print settings. Your current configuration is still active and you can proceed with the export.'),
                indicator: 'red'
            });
        }
    }

    /**
     * Reset columns to descriptor defaults.
     * Restores ColumnConfigManager state, re-renders the config panel rows,
     * updates preview and width total, deletes saved User_Settings, and
     * re-wires drag-and-drop on the new DOM elements.
     */
    _reset_defaults() {
        var self = this;

        // 1. Restore config manager to descriptor defaults
        this.config_manager.reset(this.columns);

        // 2. Re-render column config rows
        var config = this.config_manager.get_config();
        var rows_html = '';
        for (var i = 0; i < config.length; i++) {
            rows_html += this._build_column_row_html(config[i]);
        }
        this.dialog.$wrapper.find('.column-config-list').html(rows_html);

        // 3. Update width total display
        this._update_width_total();

        // 4. Update preview panel
        this._update_preview();

        // 5. Delete saved settings for this report_type
        try {
            var storage_key = 'PrintSettings:' + this.report_type;
            localStorage.removeItem(storage_key);
        } catch (e) {
            console.warn('PrintSettingsDialog: Failed to delete saved settings', e);
        }

        // 6. Re-wire drag-and-drop on the new DOM elements
        var list_el = this.dialog.$wrapper.find('.column-config-list')[0];
        if (list_el && typeof Sortable !== 'undefined') {
            Sortable.create(list_el, {
                handle: '.drag-handle',
                animation: 150,
                onEnd: function (evt) {
                    self.config_manager.reorder(evt.oldIndex, evt.newIndex);
                    self._debounced_preview_update();
                }
            });
        }

        // 7. Check all-hidden state
        this._check_all_hidden();

        frappe.show_alert({ message: __('Settings reset to defaults.'), indicator: 'blue' }, 3);
    }

    /**
     * Validate configuration and trigger the export callback.
     *
     * - Validates at least one column is visible (Req 7.1)
     * - Shows loading indicator and disables Export + Cancel buttons (Req 7.4)
     * - Calls export_callback(column_config) with the finalized ColumnConfig array (Req 7.1)
     * - On success, closes the dialog (Req 7.2)
     * - On failure, re-enables buttons, shows error alert, keeps dialog open (Error Handling)
     */
    _on_export() {
        var self = this;

        // Validate: at least one column must be visible
        if (!this.config_manager || !this.config_manager.has_visible_columns()) {
            this._show_warning_message(__('At least one column must be visible to export.'));
            return;
        }

        // Get finalized column config
        var column_config = this.config_manager.get_visible_columns();

        // Show loading state: disable Export and Cancel buttons
        this._set_export_enabled(false);
        this._set_cancel_enabled(false);
        this._show_loading(true);

        // Call the export callback, wrapping with Promise.resolve to handle
        // both sync and async callbacks gracefully
        try {
            var result = this.export_callback(column_config);
            Promise.resolve(result).then(function () {
                // Success — close dialog
                self._show_loading(false);
                self.dialog.hide();
            }).catch(function (err) {
                // Failure — re-enable buttons, show error, keep dialog open
                self._show_loading(false);
                self._set_export_enabled(true);
                self._set_cancel_enabled(true);
                frappe.msgprint({
                    title: __('Export Failed'),
                    message: err && err.message ? err.message : __('An error occurred during export. Please try again.'),
                    indicator: 'red'
                });
            });
        } catch (err) {
            // Synchronous throw from callback
            this._show_loading(false);
            this._set_export_enabled(true);
            this._set_cancel_enabled(true);
            frappe.msgprint({
                title: __('Export Failed'),
                message: err && err.message ? err.message : __('An error occurred during export. Please try again.'),
                indicator: 'red'
            });
        }
    }

    /**
     * Enable or disable the Cancel button.
     * @param {boolean} enabled
     */
    _set_cancel_enabled(enabled) {
        if (!this.dialog) return;
        var $btn = this.dialog.$wrapper.find('.btn-modal-close, .modal-header .close');
        if (enabled) {
            $btn.prop('disabled', false).removeClass('disabled');
        } else {
            $btn.prop('disabled', true).addClass('disabled');
        }
    }

    /**
     * Show or hide a loading indicator on the Export button.
     * @param {boolean} show
     */
    _show_loading(show) {
        if (!this.dialog) return;
        var $btn = this.dialog.$wrapper.find('.btn-primary-dark, .btn-primary');
        if (show) {
            $btn.attr('data-original-text', $btn.text());
            $btn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' + __('Exporting...'));
        } else {
            var original = $btn.attr('data-original-text') || __('Export');
            $btn.text(original);
        }
    }
}

// Node.js compatibility for testing
if (typeof module !== 'undefined') {
    module.exports = { ColumnConfigManager: ColumnConfigManager, PreviewPanel: PreviewPanel, PrintSettingsDialog: PrintSettingsDialog };
}
