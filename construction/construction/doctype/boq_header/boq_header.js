// PrintSettingsDialog, ColumnConfigManager, PreviewPanel are registered globally via hooks.py

frappe.ui.form.on("BOQ Header", {
    refresh(frm) {
        if (!frm.is_new()) {
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
            frm.add_custom_button("View Tree", () => {
                frappe.set_route("Tree", "BOQ Structure", { boq_header: frm.doc.name });
            }, "Actions");

            frm.add_custom_button("Advance Status", () => {
                const transitions = { Draft: "Pricing", Pricing: "Frozen", Frozen: "Locked" };
                const next = transitions[frm.doc.status];
                if (!next) { frappe.msgprint("BOQ is already Locked."); return; }
                frappe.confirm(`Advance status to <b>${next}</b>?`, () => {
                    frappe.call({
                        method: "construction.api.boq_api.advance_boq_status",
                        args: { boq_header: frm.doc.name, target_status: next },
                        callback(r) {
                            if (r.message && r.message.success) {
                                frm.reload_doc();
                                frappe.show_alert({ message: `Status → ${next}`, indicator: "green" });
                            }
                        }
                    });
                });
            }, "Actions");

            frm.add_custom_button("Export Excel - Header Only", () => {
                const sample_data = [{
                    project_name: frm.doc.project_name || "",
                    boq_number: frm.doc.name || "",
                    revision: frm.doc.revision || "",
                    status: frm.doc.status || "",
                    total_value: frm.doc.total_value || 0
                }];
                const dialog = new PrintSettingsDialog({
                    report_type: "BOQ_Header_Excel",
                    columns: BOQ_HEADER_COLUMNS,
                    sample_data: sample_data,
                    export_callback: function (column_config) {
                        return new Promise(function (resolve, reject) {
                            frappe.call({
                                method: "construction.api.boq_api.export_boq_header_excel",
                                args: {
                                    boq_header: frm.doc.name,
                                    column_config: JSON.stringify(column_config)
                                },
                                callback(r) {
                                    if (r.message && r.message.file_url) {
                                        window.open(r.message.file_url);
                                        frappe.show_alert({ message: "Header exported successfully", indicator: "green" });
                                        resolve();
                                    } else if (r.message && r.message.error) {
                                        frappe.show_alert({ message: r.message.error, indicator: "red" });
                                        reject(new Error(r.message.error));
                                    } else {
                                        resolve();
                                    }
                                },
                                error: function (err) {
                                    reject(err);
                                }
                            });
                        });
                    }
                });
                dialog.show();
            }, "Actions");

            frm.add_custom_button("Export Excel - Full BOQ", () => {
                const dialog = new PrintSettingsDialog({
                    report_type: "BOQ_Full_Excel",
                    columns: BOQ_FULL_COLUMNS,
                    sample_data: [],
                    export_callback: function (column_config) {
                        return new Promise(function (resolve, reject) {
                            frappe.call({
                                method: "construction.api.boq_api.export_boq_excel",
                                args: {
                                    boq_header: frm.doc.name,
                                    column_config: JSON.stringify(column_config)
                                },
                                callback(r) {
                                    if (r.message && r.message.file_url) {
                                        window.open(r.message.file_url);
                                        frappe.show_alert({ message: "BOQ exported successfully", indicator: "green" });
                                        resolve();
                                    } else if (r.message && r.message.error) {
                                        frappe.show_alert({ message: r.message.error, indicator: "red" });
                                        reject(new Error(r.message.error));
                                    } else {
                                        resolve();
                                    }
                                },
                                error: function (err) {
                                    reject(err);
                                }
                            });
                        });
                    }
                });
                dialog.show();
            }, "Actions");

            frm.add_custom_button("Export PDF - Header Only", () => {
                const sample_data = [{
                    project_name: frm.doc.project_name || "",
                    boq_number: frm.doc.name || "",
                    revision: frm.doc.revision || "",
                    status: frm.doc.status || "",
                    total_value: frm.doc.total_value || 0
                }];
                const dialog = new PrintSettingsDialog({
                    report_type: "BOQ_Header_PDF",
                    columns: BOQ_HEADER_COLUMNS,
                    sample_data: sample_data,
                    export_callback: function (column_config) {
                        return new Promise(function (resolve, reject) {
                            frappe.call({
                                method: "construction.api.boq_api.export_boq_header_pdf",
                                args: {
                                    boq_header: frm.doc.name,
                                    column_config: JSON.stringify(column_config)
                                },
                                callback(r) {
                                    if (r.message && r.message.file_url) {
                                        window.open(r.message.file_url);
                                        frappe.show_alert({ message: "Header PDF exported successfully", indicator: "green" });
                                        resolve();
                                    } else if (r.message && r.message.error) {
                                        frappe.show_alert({ message: r.message.error, indicator: "red" });
                                        reject(new Error(r.message.error));
                                    } else {
                                        resolve();
                                    }
                                },
                                error: function (err) {
                                    reject(err);
                                }
                            });
                        });
                    }
                });
                dialog.show();
            }, "Actions");

            frm.add_custom_button("Export PDF - Full BOQ", () => {
                const dialog = new PrintSettingsDialog({
                    report_type: "BOQ_Full_PDF",
                    columns: BOQ_FULL_COLUMNS,
                    sample_data: [],
                    export_callback: function (column_config) {
                        return new Promise(function (resolve, reject) {
                            frappe.call({
                                method: "construction.api.boq_api.export_boq_pdf",
                                args: {
                                    boq_header: frm.doc.name,
                                    column_config: JSON.stringify(column_config)
                                },
                                callback(r) {
                                    if (r.message && r.message.file_url) {
                                        window.open(r.message.file_url);
                                        frappe.show_alert({ message: "BOQ PDF exported successfully", indicator: "green" });
                                        resolve();
                                    } else if (r.message && r.message.error) {
                                        frappe.show_alert({ message: r.message.error, indicator: "red" });
                                        reject(new Error(r.message.error));
                                    } else {
                                        resolve();
                                    }
                                },
                                error: function (err) {
                                    reject(err);
                                }
                            });
                        });
                    }
                });
                dialog.show();
            }, "Actions");

            frm.add_custom_button("Print - Header Only", () => {
                frappe.set_route("print", "BOQ Header", frm.doc.name);
            }, "Actions");

            frm.add_custom_button("Print - Full BOQ", () => {
                frappe.call({
                    method: "construction.api.boq_api.export_boq_pdf",
                    args: { boq_header: frm.doc.name },
                    freeze: true,
                    freeze_message: "Generating Full BOQ PDF...",
                    callback(r) {
                        if (r.message && r.message.file_url) {
                            var printWindow = window.open(r.message.file_url);
                            if (printWindow) {
                                printWindow.onload = function() { printWindow.print(); };
                            }
                            frappe.show_alert({ message: "Full BOQ PDF ready", indicator: "green" });
                        } else if (r.message && r.message.error) {
                            frappe.show_alert({ message: r.message.error, indicator: "red" });
                        }
                    }
                });
            }, "Actions");

            if (frm.doc.status === "Draft") {
                frm.add_custom_button("Import Excel", () => {
                    const d = new frappe.ui.Dialog({
                        title: "Import BOQ from Excel",
                        fields: [{ label: "Excel File", fieldname: "file_url", fieldtype: "Attach", reqd: 1 }],
                        primary_action_label: "Import",
                        primary_action(values) {
                            frappe.call({
                                method: "construction.api.boq_api.import_boq_excel",
                                args: { file_url: values.file_url, boq_header: frm.doc.name },
                                callback(r) {
                                    if (r.message && r.message.success) {
                                        d.hide();
                                        frm.reload_doc();
                                        frappe.show_alert({ message: "Import successful", indicator: "green" });
                                    }
                                }
                            });
                        }
                    });
                    d.show();
                }, "Actions");
            }
        }
    }
});
