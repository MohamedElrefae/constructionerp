/* eslint-disable */
(function () {
	"use strict";

	if (window.scopeContext) return;

	var SCOPE_LS_KEY = "scope_context_current";

	window.ScopeContext = class ScopeContext {
		constructor() {
			this.enabled = frappe.boot?.scope_context_enabled || false;
			this.enabledDimensions = frappe.boot?.scope_context_enabled_dimensions || {
				company: true,
				cost_center: true,
				project: true,
				department: true,
			};
			this.current = frappe.boot?.scope_context?.current || {};
			this.hierarchy = frappe.boot?.scope_context?.hierarchy || {};
			this._version = frappe.boot?.scope_context?._version;
			this._selectors = {};
			this._listeners = [];
		}

		init() {
			if (!this.enabled) return;
			this._hydrateAndValidate();
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
				if (
					this.current.project &&
					!this._isProjectUnderCostCenter(this.current.project, name)
				) {
					this.current.project = null;
				}
				if (
					this.current.department &&
					!this._isDepartmentUnderCostCenter(this.current.department, name)
				) {
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

		getValidatedCurrentScope() {
			var changed = this._sanitizeCurrentScope();
			if (changed) {
				this._persistToLocalStorage();
			}
			return {
				company: this.current.company || null,
				cost_center: this.current.cost_center || null,
				project: this.current.project || null,
				department: this.current.department || null,
			};
		}

		getScopeFilter() {
			var scope = this.getValidatedCurrentScope();
			var f = {};
			if (scope.company) f.company = scope.company;
			if (scope.cost_center) f.cost_center = scope.cost_center;
			if (scope.project) f.project = scope.project;
			if (scope.department) f.department = scope.department;
			return f;
		}

		on(event, handler) {
			this._listeners.push({ event: event, handler: handler });
		}

		off(event, handler) {
			this._listeners = this._listeners.filter(function (l) {
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
				callback: function (r) {
					if (r.message && r.message.scope_version) {
						this._version = r.message.scope_version;
						this._persistToLocalStorage();
					}
				}.bind(this),
			});
		}

		_isCompanyValid(compName) {
			if (!compName) return true;
			return (this.hierarchy.companies || []).some(function (c) {
				return c && c.name === compName;
			});
		}

		_isCostCenterValid(ccName) {
			if (!ccName) return true;
			var cc = (this.hierarchy.cost_centers || []).find(function (x) {
				return x && x.name === ccName;
			});
			if (!cc) return false;
			if (this.current.company && cc.company && cc.company !== this.current.company) {
				return false;
			}
			return true;
		}

		_isProjectValid(projName) {
			if (!projName) return true;
			var project = (this.hierarchy.projects || []).find(function (p) {
				return p && p.name === projName;
			});
			if (!project) return false;
			if (this.current.company && project.company && project.company !== this.current.company) {
				return false;
			}
			if (this.current.cost_center && project.cost_center) {
				if (!this._isProjectUnderCostCenter(projName, this.current.cost_center)) {
					return false;
				}
			}
			return true;
		}

		_isDepartmentValid(deptName) {
			if (!deptName) return true;
			var dept = (this.hierarchy.departments || []).find(function (d) {
				return d && d.name === deptName;
			});
			if (!dept) return false;
			if (this.current.company && dept.company && dept.company !== this.current.company) {
				return false;
			}
			if (this.current.cost_center && dept.cost_center) {
				if (!this._isDepartmentUnderCostCenter(deptName, this.current.cost_center)) {
					return false;
				}
			}
			return true;
		}

		_hydrateAndValidate() {
			var saved = null;
			try {
				saved = localStorage.getItem(SCOPE_LS_KEY);
			} catch (e) {
				console.warn("[ScopeContext] localStorage read error:", e);
			}

			var parsed = null;
			if (saved) {
				try {
					parsed = JSON.parse(saved);
					var isValid = true;

					if (!parsed || parsed.site !== window.location.origin) {
						isValid = false;
					}

					if (isValid && this._version && parsed.version !== this._version) {
						isValid = false;
					}

					if (isValid) {
						var tempCompany = this.current.company;
						var tempCostCenter = this.current.cost_center;
						var tempProject = this.current.project;
						var tempDept = this.current.department;

						this.current.company = parsed.company || null;
						this.current.cost_center = parsed.cost_center || null;
						this.current.project = parsed.project || null;
						this.current.department = parsed.department || null;

						if (
							!this._isCompanyValid(this.current.company) ||
							!this._isCostCenterValid(this.current.cost_center) ||
							!this._isProjectValid(this.current.project) ||
							!this._isDepartmentValid(this.current.department)
						) {
							isValid = false;
						}

						if (!isValid) {
							this.current.company = tempCompany;
							this.current.cost_center = tempCostCenter;
							this.current.project = tempProject;
							this.current.department = tempDept;
							localStorage.removeItem(SCOPE_LS_KEY);
						}
					} else {
						localStorage.removeItem(SCOPE_LS_KEY);
					}
				} catch (e) {
					console.warn("[ScopeContext] Error parsing or validating cache:", e);
					try {
						localStorage.removeItem(SCOPE_LS_KEY);
					} catch (err) {}
				}
			}

			this._sanitizeCurrentScope();
			this._persistToLocalStorage();
			this._logDiagnostics(parsed);
		}

		_logDiagnostics(parsed) {
			var isDebug = false;
			try {
				isDebug = localStorage.getItem("scope_debug") === "true" || window.location.search.indexOf("scope_debug=1") !== -1;
			} catch (e) {}

			if (isDebug) {
				console.log("[ScopeContext Diagnostics]", {
					boot_version: this._version || null,
					cached_version: (parsed && parsed.version) || null,
					site_origin: window.location.origin,
					selected_project: this.current.project || null,
				});
			}
		}

		_loadFromLocalStorage() {
			try {
				var saved = localStorage.getItem(SCOPE_LS_KEY);
				if (saved) {
					var parsed = JSON.parse(saved);
					if (parsed.site && parsed.site !== window.location.origin) {
						return;
					}
					if (parsed.company) this.current.company = parsed.company;
					if (parsed.cost_center) this.current.cost_center = parsed.cost_center;
					if (parsed.project) this.current.project = parsed.project;
					if (parsed.department) this.current.department = parsed.department;
					this._sanitizeCurrentScope();
				}
			} catch (e) {
				console.warn("[ScopeContext] localStorage read error:", e);
			}
		}

		_persistToLocalStorage() {
			try {
				localStorage.setItem(
					SCOPE_LS_KEY,
					JSON.stringify({
						site: window.location.origin,
						version: this._version || null,
						...this.getCurrentScope(),
					})
				);
			} catch (e) {
				console.warn("[ScopeContext] localStorage write error:", e);
			}
		}

		_sanitizeCurrentScope() {
			var changed = false;

			if (this.current.company && !this._isCompanyValid(this.current.company)) {
				this.current.company = null;
				changed = true;
			}
			if (this.current.cost_center && !this._isCostCenterValid(this.current.cost_center)) {
				this.current.cost_center = null;
				changed = true;
			}
			if (this.current.project && !this._isProjectValid(this.current.project)) {
				this.current.project = null;
				changed = true;
			}
			if (this.current.department && !this._isDepartmentValid(this.current.department)) {
				this.current.department = null;
				changed = true;
			}

			return changed;
		}

		_renderSelectors() {}

		_bindEvents() {}

		_setupMultiTabSync() {
			var self = this;
			$(window).on("storage.scopeContext", function (e) {
				if (e.originalEvent && e.originalEvent.key === SCOPE_LS_KEY) {
					self._loadFromLocalStorage();
					self._emitChange();
				}
			});
		}

		_emitChange() {
			var payload = this.getValidatedCurrentScope();
			$(document).trigger("scope:changed", payload);
			this._listeners.forEach(function (l) {
				if (l.event === "scope:changed") {
					try {
						l.handler(payload);
					} catch (e) {}
				}
			});
		}

		_getDescendantCostCenterNames(ccName) {
			if (!ccName) return [];
			var scopeCC = (this.hierarchy.cost_centers || []).find(function (cc) {
				return cc.name === ccName;
			});
			if (!scopeCC) return [ccName];
			return (this.hierarchy.cost_centers || [])
				.filter(function (cc) {
					return cc.lft >= scopeCC.lft && cc.rgt <= scopeCC.rgt;
				})
				.map(function (cc) {
					return cc.name;
				});
		}

		_isItemUnderCostCenter(itemName, costCenterName, collection, fieldName) {
			if (!itemName || !costCenterName) return true;
			var item = (this.hierarchy[collection] || []).find(function (x) {
				return x.name === itemName;
			});
			if (!item) return true;
			if (!item[fieldName]) return true;
			var itemCC = (this.hierarchy.cost_centers || []).find(function (cc) {
				return cc.name === item[fieldName];
			});
			if (!itemCC) return true;
			var scopeCC = (this.hierarchy.cost_centers || []).find(function (cc) {
				return cc.name === costCenterName;
			});
			if (!scopeCC) return true;
			return itemCC.lft >= scopeCC.lft && itemCC.rgt <= scopeCC.rgt;
		}

		_isProjectUnderCostCenter(projectName, costCenterName) {
			return this._isItemUnderCostCenter(
				projectName,
				costCenterName,
				"projects",
				"cost_center"
			);
		}

		_isDepartmentUnderCostCenter(deptName, costCenterName) {
			return this._isItemUnderCostCenter(
				deptName,
				costCenterName,
				"departments",
				"cost_center"
			);
		}
	};

	window.scopeContext = new window.ScopeContext();
	$(document).ready(function () {
		window.scopeContext.init();
	});
})();
