(function() {
  "use strict";

  frappe.ui.form.on("*", {
    onload: function(frm) {
      if (!window.scopeContext || !window.scopeContext.enabled) return;
      if (!frm.is_new()) return;

      var dims = window.scopeContext.enabledDimensions;
      var scope = window.scopeContext.getCurrentScope();
      var meta = frm.meta;

      if (dims.company && scope.company && frappe.meta.has_field(meta, "company") && !frm.doc.company) {
        frm.set_value("company", scope.company);
      }
      if (dims.cost_center && scope.cost_center && frappe.meta.has_field(meta, "cost_center") && !frm.doc.cost_center) {
        frm.set_value("cost_center", scope.cost_center);
      }
      if (dims.project && scope.project && frappe.meta.has_field(meta, "project") && !frm.doc.project) {
        frm.set_value("project", scope.project);
      }
      if (dims.department && scope.department && frappe.meta.has_field(meta, "department") && !frm.doc.department) {
        frm.set_value("department", scope.department);
      }
    },
  });
})();
