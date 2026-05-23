frappe.ui.form.on("Construction Settings", {
    refresh: function(frm) {
        renderHierarchyManager(frm);
    },
});

function renderHierarchyManager(frm) {
    var $wrapper = frm.fields_dict.scope_hierarchy_ui.$wrapper;
    if (!$wrapper || !$wrapper.length) return;

    $wrapper.html('<p class="text-muted">Loading hierarchy...</p>');

    frappe.call({
        method: "construction.api.scope_context_api.get_scope_hierarchy_detail",
        callback: function(r) {
            if (!r.message) {
                $wrapper.html('<p class="text-muted">No data</p>');
                return;
            }
            var html = buildHierarchyHTML(r.message);
            $wrapper.html(html);
            bindHierarchyEvents($wrapper, frm);
        },
    });
}

function statusIcon(ok) {
    return ok
        ? '<span class="text-success" style="font-size:1.1em">\u2713</span>'
        : '<span class="text-danger" style="font-size:1.1em">\u2717</span>';
}

function indentSpan(level) {
    if (level <= 0) return "";
    return '<span style="display:inline-block;width:' + (level * 20) + 'px"></span>';
}

function buildHierarchyHTML(tree) {
    var parts = ['<div style="margin-top:8px">'];

    for (var ci = 0; ci < tree.length; ci++) {
        var c = tree[ci];

        // Company header
        parts.push(
            '<div class="company-card" style="border:1px solid var(--border-color);border-radius:8px;margin-bottom:16px;overflow:hidden">',
            '<div class="company-header" style="background:var(--bg-color);padding:10px 14px;font-weight:600;font-size:1rem;border-bottom:1px solid var(--border-color)">',
            frappe.utils.icon("building", "sm"),
            " " + c.title,
            " &mdash; " + c.name,
            '</div>',
            '<div style="padding:10px 14px">',
        );

        // Cost Centers section (tree display)
        if (c.cost_centers.length) {
            parts.push('<div style="margin-bottom:10px">');
            parts.push('<div style="font-weight:500;margin-bottom:6px;color:var(--text-muted);font-size:0.85rem">COST CENTERS</div>');
            parts.push('<table class="table table-sm" style="margin:0;font-size:0.85rem">');
            parts.push('<thead><tr><th>Cost Center</th><th>Group</th><th>Company</th><th>Actions</th></tr></thead><tbody>');

            // Build parent_cost_center lookup for level calculation
            var parentMap = {};
            for (var cci = 0; cci < c.cost_centers.length; cci++) {
                var cc = c.cost_centers[cci];
                parentMap[cc.name] = cc;
            }

            function getLevel(ccName) {
                var level = 0;
                var current = parentMap[ccName];
                while (current && current.parent_cost_center) {
                    level++;
                    current = parentMap[current.parent_cost_center];
                    if (!current) break;
                }
                return level;
            }

            for (var cci = 0; cci < c.cost_centers.length; cci++) {
                var cc = c.cost_centers[cci];
                var level = getLevel(cc.name);
                var indent = indentSpan(level);
                var groupBadge = cc.is_group
                    ? '<span class="badge" style="background:var(--primary-color)">Group</span>'
                    : "";

                parts.push(
                    '<tr>',
                    '<td>' + indent + '<b>' + cc.label + '</b></td>',
                    '<td>' + groupBadge + '</td>',
                    '<td>' + statusIcon(cc.linked) + (cc.linked ? " Set" : " Not set") + '</td>',
                    '<td><button class="btn btn-xs btn-default open-record" data-doctype="Cost Center" data-name="' + cc.name + '">Open</button></td>',
                    '</tr>',
                );

                // Projects under this cost center
                if (cc.projects.length) {
                    parts.push(
                        '<tr style="background:var(--bg-color)"><td colspan="4" style="padding:0">',
                        '<table class="table table-sm" style="margin:0 0 0 24px;font-size:0.8rem;width:auto">',
                        '<thead><tr><th>Project</th><th>Company</th><th>Cost Center</th><th>Actions</th></tr></thead><tbody>',
                    );
                    for (var pi = 0; pi < cc.projects.length; pi++) {
                        var p = cc.projects[pi];
                        parts.push(
                            '<tr>',
                            '<td>' + indentSpan(1) + p.label + '</td>',
                            '<td>' + statusIcon(p.company_ok) + '</td>',
                            '<td>' + statusIcon(p.cost_center_ok) + '</td>',
                            '<td><button class="btn btn-xs btn-default open-record" data-doctype="Project" data-name="' + p.name + '">Open</button></td>',
                            '</tr>',
                        );
                    }
                    parts.push('</tbody></table></td></tr>');
                }

                // Departments under this cost center
                if (cc.departments.length) {
                    parts.push(
                        '<tr style="background:var(--bg-color)"><td colspan="4" style="padding:0">',
                        '<table class="table table-sm" style="margin:0 0 0 24px;font-size:0.8rem;width:auto">',
                        '<thead><tr><th>Department</th><th>Company</th><th>Cost Center</th><th>Actions</th></tr></thead><tbody>',
                    );
                    for (var di = 0; di < cc.departments.length; di++) {
                        var d = cc.departments[di];
                        parts.push(
                            '<tr>',
                            '<td>' + indentSpan(1) + d.label + '</td>',
                            '<td>' + statusIcon(d.company_ok) + '</td>',
                            '<td>' + statusIcon(d.cost_center_ok) + '</td>',
                            '<td><button class="btn btn-xs btn-default open-record" data-doctype="Department" data-name="' + d.name + '">Open</button></td>',
                            '</tr>',
                        );
                    }
                    parts.push('</tbody></table></td></tr>');
                }
            }
            parts.push('</tbody></table></div>');
        } else {
            parts.push(
                '<div class="text-muted" style="margin-bottom:10px;font-size:0.85rem">',
                'No cost centers linked to this company.',
                ' <button class="btn btn-xs btn-default create-record" data-doctype="Cost Center" data-company="' + c.name + '">+ Add Cost Center</button>',
                '</div>',
            );
        }

        // Orphan projects (not linked to a cost center)
        if (c.orphan_projects.length) {
            parts.push('<div style="margin-bottom:10px">');
            parts.push('<div style="font-weight:500;margin-bottom:6px;color:var(--text-muted);font-size:0.85rem">PROJECTS (not under a cost center)</div>');
            parts.push('<table class="table table-sm" style="margin:0;font-size:0.85rem">');
            parts.push('<thead><tr><th>Project</th><th>Company</th><th>Cost Center</th><th>Actions</th></tr></thead><tbody>');
            for (var pi = 0; pi < c.orphan_projects.length; pi++) {
                var p = c.orphan_projects[pi];
                parts.push(
                    '<tr>',
                    '<td>' + p.label + '</td>',
                    '<td>' + statusIcon(p.company_ok) + '</td>',
                    '<td>' + statusIcon(p.cost_center_ok) + '</td>',
                    '<td><button class="btn btn-xs btn-default open-record" data-doctype="Project" data-name="' + p.name + '">Open</button></td>',
                    '</tr>',
                );
            }
            parts.push('</tbody></table></div>');
        }

        // Orphan departments (not under a cost center)
        if (c.orphan_depts.length) {
            parts.push('<div style="margin-bottom:10px">');
            parts.push('<div style="font-weight:500;margin-bottom:6px;color:var(--text-muted);font-size:0.85rem">DEPARTMENTS (not under a cost center)</div>');
            parts.push('<table class="table table-sm" style="margin:0;font-size:0.85rem">');
            parts.push('<thead><tr><th>Department</th><th>Company</th><th>Cost Center</th><th>Actions</th></tr></thead><tbody>');
            for (var di = 0; di < c.orphan_depts.length; di++) {
                var d = c.orphan_depts[di];
                parts.push(
                    '<tr>',
                    '<td>' + d.label + '</td>',
                    '<td>' + statusIcon(d.company_ok) + '</td>',
                    '<td>' + statusIcon(d.cost_center_ok) + '</td>',
                    '<td><button class="btn btn-xs btn-default open-record" data-doctype="Department" data-name="' + d.name + '">Open</button></td>',
                    '</tr>',
                );
            }
            parts.push('</tbody></table></div>');
        }

        // Quick create buttons
        parts.push(
            '<div style="margin-top:8px">',
            '<button class="btn btn-xs btn-default create-record" data-doctype="Cost Center" data-company="' + c.name + '">+ New Cost Center</button> ',
            '<button class="btn btn-xs btn-default create-record" data-doctype="Project" data-company="' + c.name + '">+ New Project</button> ',
            '<button class="btn btn-xs btn-default create-record" data-doctype="Department" data-company="' + c.name + '">+ New Department</button>',
            '</div>',
        );

        parts.push('</div></div>');
    }

    parts.push("</div>");
    return parts.join("\n");
}

function bindHierarchyEvents($wrapper, frm) {
    // Open record
    $wrapper.find(".open-record").on("click", function() {
        var doctype = $(this).data("doctype");
        var name = $(this).data("name");
        frappe.set_route("Form", doctype, name);
    });

    // Create record
    $wrapper.find(".create-record").on("click", function() {
        var doctype = $(this).data("doctype");
        var company = $(this).data("company");

        if (doctype === "Cost Center") {
            frappe.new_doc("Cost Center", { company: company });
        } else if (doctype === "Project") {
            frappe.new_doc("Project", { company: company });
        } else if (doctype === "Department") {
            frappe.new_doc("Department", { company: company });
        }
    });
}
