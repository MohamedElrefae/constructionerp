frappe.treeview_settings["BOQ Structure"] = {
    breadcrumb: "Construction",
    get_tree_root: false,
    root_label: "BOQ Structure",
    filters: [
        {
            fieldname: "boq_header",
            fieldtype: "Link",
            options: "BOQ Header",
            label: __("Select BOQ Header"),
            placeholder: __("Choose a BOQ to view its structure..."),
            reqd: true,
        },
    ],
    get_tree_nodes: "construction.api.boq_api.get_children",
    add_tree_node: "construction.api.boq_api.add_node",
    fields: [
        {
            fieldtype: "Data",
            fieldname: "title",
            label: __("Title"),
            reqd: true,
        },
        {
            fieldtype: "Check",
            fieldname: "is_group",
            label: __("Is Group"),
            description: __(
                "Groups contain child nodes. Non-groups are leaf items for pricing."
            ),
        },
    ],
    ignore_fields: ["parent_structure"],
    get_label: function(node) {
        if (node.title && node.title !== node.label) {
            return node.title;
        }
        return node.title || node.label;
    },
    onrender: function(node) {
        // Replace root node label with project name + BOQ title
        if (node.is_root) {
            var boq = node.data ? node.data.value : null;
            if (!boq || boq === "BOQ Structure") {
                var page = cur_page && cur_page.page;
                if (page && page.fields_dict && page.fields_dict.boq_header) {
                    boq = page.fields_dict.boq_header.get_value();
                }
            }
            if (boq && boq !== "BOQ Structure") {
                frappe.db.get_value("BOQ Header", boq, ["title", "project_name"])
                    .then(function(r) {
                        if (r && r.message) {
                            var label = r.message.title || boq;
                            if (r.message.project_name) {
                                label = r.message.project_name + " — " + label;
                            }
                            if (node.$tree_link) {
                                node.$tree_link.find(".tree-label").text(label);
                            }
                        }
                    });
            }
        }
    },
    onload: function (treeview) {
        function get_boq_header() {
            return treeview.page.fields_dict.boq_header.get_value();
        }

        // Auto-load tree if boq_header is in the URL (coming from BOQ Header form)
        var boq_from_url = frappe.route_options && frappe.route_options.boq_header;
        if (!boq_from_url) {
            boq_from_url = get_boq_header();
        }
        if (boq_from_url && treeview.page.fields_dict.boq_header) {
            setTimeout(function() {
                var field = treeview.page.fields_dict.boq_header;
                field.set_value(boq_from_url).then(function() {
                    field.$input.val(boq_from_url);
                    field.$input.trigger("change");
                });
            }, 300);
        }
        if (frappe.route_options) {
            delete frappe.route_options.boq_header;
        }

        // ── Column definitions (same as BOQ Header for consistency) ──
        var BOQ_FULL_COLUMNS = [
            { field_key: "wbs_code", label: "WBS Code", default_width: 12, default_visible: true, default_sort_order: 0 },
            { field_key: "title", label: "Title / Description", default_width: 30, default_visible: true, default_sort_order: 1 },
            { field_key: "type", label: "Type", default_width: 6, default_visible: true, default_sort_order: 2 },
            { field_key: "unit", label: "Unit", default_width: 5, default_visible: true, default_sort_order: 3 },
            { field_key: "quantity", label: "Quantity", default_width: 8, default_visible: true, default_sort_order: 4 },
            { field_key: "contract_unit_price", label: "Unit Price", default_width: 10, default_visible: true, default_sort_order: 5 },
            { field_key: "factor", label: "Factor", default_width: 5, default_visible: true, default_sort_order: 6 },
            { field_key: "line_total", label: "Line Total", default_width: 10, default_visible: true, default_sort_order: 7 },
            { field_key: "owner_ref_no", label: "Ref", default_width: 9, default_visible: true, default_sort_order: 8 },
            { field_key: "owner_page", label: "Owner Page", default_width: 5, default_visible: false, default_sort_order: 9 },
            { field_key: "owner_file_ref", label: "File Ref", default_width: 5, default_visible: false, default_sort_order: 10 }
        ];

        var BOQ_HEADER_COLUMNS = [
            { field_key: "name", label: "BOQ ID", default_width: 15, default_visible: true, default_sort_order: 0 },
            { field_key: "title", label: "Title", default_width: 20, default_visible: true, default_sort_order: 1 },
            { field_key: "project_name", label: "Project", default_width: 20, default_visible: true, default_sort_order: 2 },
            { field_key: "boq_type", label: "BOQ Type", default_width: 10, default_visible: true, default_sort_order: 3 },
            { field_key: "status", label: "Status", default_width: 10, default_visible: true, default_sort_order: 4 },
            { field_key: "version", label: "Version", default_width: 8, default_visible: true, default_sort_order: 5 },
            { field_key: "total_contract_value", label: "Total Contract Value", default_width: 15, default_visible: true, default_sort_order: 6 },
            { field_key: "total_budgeted_cost", label: "Total Budgeted Cost", default_width: 15, default_visible: true, default_sort_order: 7 },
            { field_key: "created_on", label: "Created On", default_width: 12, default_visible: false, default_sort_order: 8 },
            { field_key: "modified_on", label: "Modified On", default_width: 12, default_visible: false, default_sort_order: 9 },
        ];

        // ── Helper: export callback builder ──
        function make_export_callback(method, success_msg) {
            return function (column_config) {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return Promise.reject(); }
                return new Promise(function (resolve, reject) {
                    frappe.call({
                        method: method,
                        args: { boq_header: boq, column_config: JSON.stringify(column_config) },
                        callback: function(r) {
                            if (r.message && r.message.file_url) {
                                window.open(r.message.file_url);
                                frappe.show_alert({ message: success_msg, indicator: "green" });
                                resolve();
                            } else if (r.message && r.message.error) {
                                frappe.show_alert({ message: r.message.error, indicator: "red" });
                                reject(new Error(r.message.error));
                            } else {
                                resolve();
                            }
                        },
                        error: function (err) { reject(err); }
                    });
                });
            };
        }

        // ── View buttons ──
        treeview.page.add_inner_button(
            __("BOQ Header"), function () {
                var boq = get_boq_header();
                if (boq) frappe.set_route("Form", "BOQ Header", boq);
            }, __("View")
        );

        treeview.page.add_inner_button(
            __("BOQ Items"), function () {
                var boq = get_boq_header();
                if (boq) frappe.set_route("List", "BOQ Item", { boq_header: boq });
            }, __("View")
        );

        treeview.page.add_inner_button(
            __("Table View"), function () {
                var boq = get_boq_header();
                if (boq) frappe.set_route("List", "BOQ Structure", { boq_header: boq });
            }, __("View")
        );

        // ── Export buttons (with PrintSettingsDialog for column config) ──
        treeview.page.add_inner_button(
            __("Excel - Header Only"), function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                new PrintSettingsDialog({
                    report_type: "BOQ_Header_Excel",
                    columns: BOQ_HEADER_COLUMNS,
                    sample_data: [],
                    export_callback: make_export_callback(
                        "construction.api.boq_api.export_boq_header_excel",
                        "Header exported successfully"
                    )
                }).show();
            }, __("Export")
        );

        treeview.page.add_inner_button(
            __("Excel - Full BOQ"), function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                new PrintSettingsDialog({
                    report_type: "BOQ_Full_Excel",
                    columns: BOQ_FULL_COLUMNS,
                    sample_data: [],
                    export_callback: make_export_callback(
                        "construction.api.boq_api.export_boq_excel",
                        "BOQ exported successfully"
                    )
                }).show();
            }, __("Export")
        );

        treeview.page.add_inner_button(
            __("PDF - Header Only"), function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                new PrintSettingsDialog({
                    report_type: "BOQ_Header_PDF",
                    columns: BOQ_HEADER_COLUMNS,
                    sample_data: [],
                    export_callback: make_export_callback(
                        "construction.api.boq_api.export_boq_header_pdf",
                        "Header PDF exported successfully"
                    )
                }).show();
            }, __("Export")
        );

        treeview.page.add_inner_button(
            __("PDF - Full BOQ"), function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                new PrintSettingsDialog({
                    report_type: "BOQ_Full_PDF",
                    columns: BOQ_FULL_COLUMNS,
                    sample_data: [],
                    export_callback: make_export_callback(
                        "construction.api.boq_api.export_boq_pdf",
                        "BOQ PDF exported successfully"
                    )
                }).show();
            }, __("Export")
        );

        treeview.page.add_inner_button(
            __("Print - Header Only"), function () {
                var boq = get_boq_header();
                if (boq) frappe.set_route("print", "BOQ Header", boq);
            }, __("Export")
        );

        treeview.page.add_inner_button(
            __("Print - Full BOQ"), function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                frappe.call({
                    method: "construction.api.boq_api.export_boq_pdf",
                    args: { boq_header: boq },
                    freeze: true,
                    freeze_message: __("Generating Full BOQ PDF..."),
                    callback: function(r) {
                        if (r.message && r.message.file_url) {
                            var printWindow = window.open(r.message.file_url);
                            if (printWindow) {
                                printWindow.onload = function () { printWindow.print(); };
                            }
                            frappe.show_alert({ message: __("Full BOQ PDF ready"), indicator: "green" });
                        } else if (r.message && r.message.error) {
                            frappe.show_alert({ message: r.message.error, indicator: "red" });
                        }
                    }
                });
            }, __("Export")
        );
    },
};

