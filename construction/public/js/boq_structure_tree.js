// BOQ Structure Tree View
// Follows the standard Frappe treeview pattern (like Cost Center)

frappe.treeview_settings["BOQ Structure"] = {
    breadcrumb: "Construction",
    title: __("BOQ Structure"),
    // Use our custom get_children that filters by boq_header
    get_tree_nodes: "construction.api.boq_api.get_children",
    add_tree_node: "construction.api.boq_api.add_node",
    filters: [
        {
            fieldname: "boq_header",
            fieldtype: "Link",
            options: "BOQ Header",
            label: __("BOQ Header"),
            reqd: 1,
        }
    ],
    fields: [
        {
            fieldname: "title",
            fieldtype: "Data",
            label: __("Title"),
            reqd: 1,
        },
        {
            fieldname: "is_group",
            fieldtype: "Check",
            label: __("Is Group (Section)"),
            default: "0",
        }
    ],
    // Disable editing the root node name inline
    root_label: "BOQ Structure",
    get_tree_root: false,
    // Show the standard Add Child button
    show_expand_all: true,
    get_label: function(node) {
        if (node.data && node.data.wbs_code) {
            return node.data.wbs_code + " — " + (node.data.title || node.data.value);
        }
        return node.title || node.value;
    },
    onrender: function(node) {
        // Add group badge
        if (node.data && node.data.is_group == 1) {
            $(node.parent).find(".tree-label").first()
                .append(' <span class="badge badge-info" style="font-size:10px;">Section</span>');
        }
    },
    toolbar: [
        {
            label: __("Open"),
            click: function(node) {
                frappe.set_route("Form", "BOQ Structure", node.data.value);
            },
            btnClass: "hidden-xs",
        }
    ],
    extend_toolbar: true,
};
