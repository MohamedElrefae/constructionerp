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
            // The root value might be the BOQ ID or "BOQ Structure"
            if (!boq || boq === "BOQ Structure") {
                // Try to get from the filter
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
                // Set value visually in the input AND internally
                field.set_value(boq_from_url).then(function() {
                    field.$input.val(boq_from_url);
                    field.$input.trigger("change");
                });
            }, 300);
        }
        if (frappe.route_options) {
            delete frappe.route_options.boq_header;
        }


        treeview.page.add_inner_button(
            __("BOQ Header"), function () {
                var boq = get_boq_header();
                if (boq) frappe.set_route("Form", "BOQ Header", boq);
            }, __("View")
        );

        treeview.page.add_inner_button(
            __("BOQ Items"), function () {
                frappe.set_route("List", "BOQ Item", { boq_header: get_boq_header() });
            }, __("View")
        );

        treeview.page.add_inner_button(
            __("Excel - Full BOQ"), function () {
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
            }, __("Export")
        );

        treeview.page.add_inner_button(
            __("PDF - Full BOQ"), function () {
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
            }, __("Export")
        );
    },
};
