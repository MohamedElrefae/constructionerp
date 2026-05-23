(function() {
  "use strict";

  if (window.scopeContext) return;

  var SCOPE_LS_KEY = "scope_context_current";

  window.ScopeContext = class ScopeContext {
    constructor() {
      this.enabled = frappe.boot?.scope_context_enabled || false;
      this.enabledDimensions = frappe.boot?.scope_context_enabled_dimensions || {
        company: true, cost_center: true, project: true, department: true
      };
      this.current = frappe.boot?.scope_context?.current || {};
      this.hierarchy = frappe.boot?.scope_context?.hierarchy || {};
      this._version = frappe.boot?.scope_context?._version;
      this._selectors = {};
      this._listeners = [];
    }

    init() {
      if (!this.enabled) return;
      this._loadFromLocalStorage();
      this._renderSelectors();
      this._bindEvents();
      this._setupMultiTabSync();
    }

    setCompany(name) {
      if (this.current.company === name) return;
      this.current.company = name;
      this.current.cost_center = null;
      this.current.project = null;
      this.current.department = null;
      this._persistToLocalStorage();
      this._saveToServer();
      this._emitChange();
    }

    setCostCenter(name) {
      if (this.current.cost_center === name) return;
      this.current.cost_center = name;
      if (name) {
        if (this.current.project && !this._isProjectUnderCostCenter(this.current.project, name)) {
          this.current.project = null;
        }
        if (this.current.department && !this._isDepartmentUnderCostCenter(this.current.department, name)) {
          this.current.department = null;
        }
      }
      this._persistToLocalStorage();
      this._saveToServer();
      this._emitChange();
    }

    setProject(name) {
      if (this.current.project === name) return;
      this.current.project = name;
      this._persistToLocalStorage();
      this._saveToServer();
      this._emitChange();
    }

    setDepartment(name) {
      if (this.current.department === name) return;
      this.current.department = name;
      this._persistToLocalStorage();
      this._saveToServer();
      this._emitChange();
    }

    getCurrentScope() {
      return {
        company: this.current.company || null,
        cost_center: this.current.cost_center || null,
        project: this.current.project || null,
        department: this.current.department || null,
      };
    }

    getScopeFilter() {
      var f = {};
      if (this.current.company) f.company = this.current.company;
      if (this.current.cost_center) f.cost_center = this.current.cost_center;
      if (this.current.project) f.project = this.current.project;
      if (this.current.department) f.department = this.current.department;
      return f;
    }

    on(event, handler) {
      this._listeners.push({ event: event, handler: handler });
    }

    off(event, handler) {
      this._listeners = this._listeners.filter(function(l) {
        return l.event !== event || l.handler !== handler;
      });
    }

    _saveToServer() {
      var scope = this.getCurrentScope();
      frappe.call({
        method: "construction.api.scope_context_api.set_scope_context",
        args: {
          company: scope.company,
          cost_center: scope.cost_center,
          project: scope.project,
          department: scope.department,
          source: "erpnext",
        },
        callback: function(r) {
          if (r.message && r.message.scope_version) {
            this._version = r.message.scope_version;
          }
        }.bind(this),
      });
    }

    _loadFromLocalStorage() {
      try {
        var saved = localStorage.getItem(SCOPE_LS_KEY);
        if (saved) {
          var parsed = JSON.parse(saved);
          if (parsed.company) this.current.company = parsed.company;
          if (parsed.cost_center) this.current.cost_center = parsed.cost_center;
          if (parsed.project && (!parsed.cost_center || this._isProjectUnderCostCenter(parsed.project, parsed.cost_center))) {
            this.current.project = parsed.project;
          }
          if (parsed.department && (!parsed.cost_center || this._isDepartmentUnderCostCenter(parsed.department, parsed.cost_center))) {
            this.current.department = parsed.department;
          }
        }
      } catch (e) {
        console.warn("[ScopeContext] localStorage read error:", e);
      }
    }

    _persistToLocalStorage() {
      try {
        localStorage.setItem(SCOPE_LS_KEY, JSON.stringify(this.getCurrentScope()));
      } catch (e) {
        console.warn("[ScopeContext] localStorage write error:", e);
      }
    }

    _renderSelectors() {
    }

    _bindEvents() {
    }

    _setupMultiTabSync() {
      var self = this;
      $(window).on("storage.scopeContext", function(e) {
        if (e.originalEvent && e.originalEvent.key === SCOPE_LS_KEY) {
          self._loadFromLocalStorage();
          self._emitChange();
        }
      });
    }

    _emitChange() {
      var payload = this.getCurrentScope();
      $(document).trigger("scope:changed", payload);
      this._listeners.forEach(function(l) {
        if (l.event === "scope:changed") {
          try { l.handler(payload); } catch (e) {}
        }
      });
    }

    _getDescendantCostCenterNames(ccName) {
      if (!ccName) return [];
      var scopeCC = (this.hierarchy.cost_centers || []).find(function(cc) { return cc.name === ccName; });
      if (!scopeCC) return [ccName];
      return (this.hierarchy.cost_centers || [])
        .filter(function(cc) { return cc.lft >= scopeCC.lft && cc.rgt <= scopeCC.rgt; })
        .map(function(cc) { return cc.name; });
    }

    _isItemUnderCostCenter(itemName, costCenterName, collection, fieldName) {
      if (!itemName || !costCenterName) return true;
      var item = (this.hierarchy[collection] || []).find(function(x) { return x.name === itemName; });
      if (!item) return true;
      if (!item[fieldName]) return true;
      var itemCC = (this.hierarchy.cost_centers || []).find(function(cc) { return cc.name === item[fieldName]; });
      if (!itemCC) return true;
      var scopeCC = (this.hierarchy.cost_centers || []).find(function(cc) { return cc.name === costCenterName; });
      if (!scopeCC) return true;
      return itemCC.lft >= scopeCC.lft && itemCC.rgt <= scopeCC.rgt;
    }

    _isProjectUnderCostCenter(projectName, costCenterName) {
      return this._isItemUnderCostCenter(projectName, costCenterName, "projects", "cost_center");
    }

    _isDepartmentUnderCostCenter(deptName, costCenterName) {
      return this._isItemUnderCostCenter(deptName, costCenterName, "departments", "cost_center");
    }
  };

  window.scopeContext = new window.ScopeContext();
  $(document).ready(function() {
    window.scopeContext.init();
  });
})();
