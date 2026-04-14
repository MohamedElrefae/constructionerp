frappe.treeview_settings["BOQ Structure"] = {
    breadcrumb: "Construction",
    get_tree_root: false,
    filters: [
        {
            fieldname: "boq_header",
            fieldtype: "Link",
            options: "BOQ Header",
            label: __("BOQ Header"),
            description: __("Select a BOQ Header to view its structure tree"),
            reqd: true,
            get_query: function() {
                return {
                    filters: {},
                    fields: ["name", "title", "project", "status", "boq_type"]
                };
            }
        },
    ],
    root_label: "BOQ Structure",
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
    onload: function (treeview) {
        function get_boq_header() {
            return treeview.page.fields_dict.boq_header.get_value();
        }

        // Update page title with project name when BOQ Header is selected
        var boq_field = treeview.page.fields_dict.boq_header;
        if (boq_field && boq_field.$input) {
            boq_field.$input.on("change", function() {
                var boq = get_boq_header();
                if (boq) {
                    frappe.db.get_value("BOQ Header", boq, ["title", "project"]).then(function(r) {
                        if (r && r.message) {
                            var project = r.message.project || "";
                            var title = r.message.title || boq;
                            treeview.page.set_title(
                                __("BOQ Structure") + " — " + project + " / " + title
                            );
                        }
                    });
                }
            });
        }


        treeview.page.add_inner_button(
            __("BOQ Header"),
            function () {
                var boq = get_boq_header();
                if (boq) {
                    frappe.set_route("Form", "BOQ Header", boq);
                }
            },
            __("View")
        );

        treeview.page.add_inner_button(
            __("BOQ Items"),
            function () {
                frappe.set_route("List", "BOQ Item", {
                    boq_header: get_boq_header(),
                });
            },
            __("View")
        );

        treeview.page.add_inner_button(
            __("Excel - Header Only"),
            function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                frappe.call({
                    method: "construction.api.boq_api.export_boq_header_excel",
                    args: { boq_header: boq },
                    callback: function(r) {
                        if (r.message && r.message.file_url) {
                            window.open(r.message.file_url);
                            frappe.show_alert({ message: __("Header exported"), indicator: "green" });
                        }
                    }
                });
            },
            __("Export")
        );

        treeview.page.add_inner_button(
            __("Excel - Full BOQ"),
            function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                frappe.call({
                    method: "construction.api.boq_api.export_boq_excel",
                    args: { boq_header: boq },
                    callback: function(r) {
                        if (r.message && r.message.file_url) {
                            window.open(r.message.file_url);
                            frappe.show_alert({ message: __("BOQ exported"), indicator: "green" });
                        }
                    }
                });
            },
            __("Export")
        );

        treeview.page.add_inner_button(
            __("PDF - Full BOQ"),
            function () {
                var boq = get_boq_header();
                if (!boq) { frappe.msgprint(__("Please select a BOQ Header first.")); return; }
                frappe.call({
                    method: "construction.api.boq_api.export_boq_pdf",
                    args: { boq_header: boq },
                    callback: function(r) {
                        if (r.message && r.message.file_url) {
                            window.open(r.message.file_url);
                            frappe.show_alert({ message: __("BOQ PDF exported"), indicator: "green" });
                        }
                    }
                });
            },
            __("Export")
        );
    },
};
