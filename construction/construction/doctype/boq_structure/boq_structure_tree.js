frappe.treeview_settings["BOQ Structure"] = {
    breadcrumb: "Construction",
    get_tree_root: false,
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

        // Update page title with project name when BOQ Header changes
        var original_on_change = treeview.page.fields_dict.boq_header.df.change;
        treeview.page.fields_dict.boq_header.df.change = function() {
            if (original_on_change) original_on_change();
            var boq = get_boq_header();
            if (boq) {
                frappe.db.get_value("BOQ Header", boq, ["title", "project_name"])
                    .then(function(r) {
                        if (r && r.message) {
                            var proj = r.message.project_name || "";
                            var title = r.message.title || boq;
                            var page_title = proj ? (proj + " — " + title) : title;
                            treeview.page.set_title(page_title);
                        }
                    });
            }
        };


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
