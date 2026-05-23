(function() {
  "use strict";

  var OPT_OUT_KEY = "scope_filter_opt_out_doctypes";
  console.log("[ScopeContext Filter] loading, scopeContext=" + (!!window.scopeContext) + " enabled=" + (window.scopeContext && window.scopeContext.enabled));

  function getOptOutList() {
    try {
      return JSON.parse(localStorage.getItem(OPT_OUT_KEY) || "[]");
    } catch (e) {
      return [];
    }
  }

  function setOptOutList(list) {
    try {
      localStorage.setItem(OPT_OUT_KEY, JSON.stringify(list));
    } catch (e) {}
  }

  function getDescendantCCNames(ccName, costCenters) {
    if (!ccName) return [];
    var scopeCC = (costCenters || []).find(function(cc) { return cc.name === ccName; });
    if (!scopeCC) return [ccName];
    return (costCenters || [])
      .filter(function(cc) { return cc.lft >= scopeCC.lft && cc.rgt <= scopeCC.rgt; })
      .map(function(cc) { return cc.name; });
  }

  if (frappe.views && frappe.views.ListView) {
    var originalGetArgs = frappe.views.ListView.prototype.get_args;

    frappe.views.ListView.prototype.get_args = function() {
      var args = originalGetArgs.apply(this, arguments);

      if (!window.scopeContext || !window.scopeContext.enabled) return args;

      var optOut = getOptOutList();
      if (optOut.indexOf(this.doctype) !== -1) return args;

      var scopeFilter = window.scopeContext.getScopeFilter();
      if (!scopeFilter) return args;

      var meta = frappe.get_meta(this.doctype);
      if (!meta || !meta.fields) return args;

      var dims = window.scopeContext.enabledDimensions;
      var hasField = {};
      (meta.fields || []).forEach(function(f) { hasField[f.fieldname] = true; });

      // Company filter
      if (dims.company && scopeFilter.company && hasField.company) {
        args.filters.push([this.doctype, "company", "=", scopeFilter.company]);
      }

      // Cost Center filter with NestedSet descendant expansion
      if (dims.cost_center && scopeFilter.cost_center && hasField.cost_center) {
        var h = window.scopeContext.hierarchy;
        var descendantNames = getDescendantCCNames(scopeFilter.cost_center, h.cost_centers);
        if (descendantNames.length === 1) {
          args.filters.push([this.doctype, "cost_center", "=", descendantNames[0]]);
        } else {
          args.filters.push([this.doctype, "cost_center", "in", descendantNames]);
        }
      }

      // Project filter
      if (dims.project && scopeFilter.project && hasField.project) {
        args.filters.push([this.doctype, "project", "=", scopeFilter.project]);
      }

      // Department filter
      if (dims.department && scopeFilter.department && hasField.department) {
        args.filters.push([this.doctype, "department", "=", scopeFilter.department]);
      }

      return args;
    };
  }

  $(document).on("scope:changed", function() {
    if (window.cur_list && window.cur_list.doctype) {
      window.cur_list.refresh();
    }
  });

  frappe.listview_settings = frappe.listview_settings || {};
  var origOnLoad = frappe.listview_settings.onload;
  frappe.listview_settings.onload = function(listview) {
    if (origOnLoad) origOnLoad(listview);

    if (!window.scopeContext || !window.scopeContext.enabled) return;

    listview.page.add_menu_item(__("Toggle Scope Filter"), function() {
      var doctype = listview.doctype;
      var optOut = getOptOutList();
      var idx = optOut.indexOf(doctype);

      if (idx === -1) {
        optOut.push(doctype);
        setOptOutList(optOut);
        frappe.show_alert({
          message: __("Scope filter disabled for {0}", [doctype]),
          indicator: "orange",
        });
      } else {
        optOut.splice(idx, 1);
        setOptOutList(optOut);
        frappe.show_alert({
          message: __("Scope filter enabled for {0}", [doctype]),
          indicator: "green",
        });
      }
      listview.refresh();
    });
  };
})();
