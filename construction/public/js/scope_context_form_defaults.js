(function() {
  "use strict";

  frappe.ui.form.on("*", {
    onload: function(frm) {
      if (!window.scopeContext || !window.scopeContext.enabled) return;
      if (!frm.is_new()) return;

      var dims = window.scopeContext.enabledDimensions;
      var scope = window.scopeContext.getCurrentScope();
      var meta = frm.meta;

      function set_default_silently(fieldname, value) {
        frm.doc[fieldname] = value;
        frm.refresh_field(fieldname);
      }

      if (dims.company && scope.company && frappe.meta.has_field(meta, "company") && !frm.doc.company) {
        set_default_silently("company", scope.company);
      }
      if (dims.cost_center && scope.cost_center && frappe.meta.has_field(meta, "cost_center") && !frm.doc.cost_center) {
        set_default_silently("cost_center", scope.cost_center);
      }
      if (dims.project && scope.project && frappe.meta.has_field(meta, "project") && !frm.doc.project) {
        set_default_silently("project", scope.project);
      }
      if (dims.department && scope.department && frappe.meta.has_field(meta, "department") && !frm.doc.department) {
        set_default_silently("department", scope.department);
      }
    },
  });
})();
