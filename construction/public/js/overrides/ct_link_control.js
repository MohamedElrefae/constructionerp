/**
 * CT Link Control Global Auto-Enhancer — Phase 3 (Safe Unified Dropdown)
 *
 * Strategy: POST-RENDER overlay approach.
 * We hide the native .link-field element and render a unified dropdown button
 * and glassmorphic fixed menu that behaves identically to the theme switcher.
 *
 * Data layer is completely untouched — native input validation and event loops remain intact.
 * Note: Does not call searchable_link_search directly; builds dropdown over native search_link
 * with custom query overrides (e.g. BOQ cascade endpoints in boq_link_queries.py).
 */

(function () {
	"use strict";

	const CT_ATTR = "data-ct-link-enhanced";

	// The PRISTINE native methods of the Link control, per class of the control.
	//
	// They are captured before the theme patches the class and they are the
	// only native methods the themed control calls, so a call can never
	// recurse into a patched wrapper of the theme. A class that is loaded or
	// replaced later gets its own capture.
	const nativeMethods = new WeakMap();

	// Captures the native methods of a class of the control.
	//
	// The capture of a class happens once, before the theme patches it, so a
	// patched wrapper of the theme can never be captured as a native method.
	// A class without the native contract yields null methods: the search is
	// then closed (the native contract is mandatory).
	function captureNativeMethods(ControlLink) {
		if (!ControlLink) return null;
		let methods = nativeMethods.get(ControlLink);
		if (!methods) {
			const proto = ControlLink.prototype;
			methods = {
				getSearchArgs:
					typeof proto.get_search_args === "function" ? proto.get_search_args : null,
				setCustomQuery:
					typeof proto.set_custom_query === "function" ? proto.set_custom_query : null,
			};
			nativeMethods.set(ControlLink, methods);
		}
		return methods;
	}

	function isBoqStructureLink(field) {
		return field && field.df && field.df.options === "BOQ Structure";
	}

	function isHierarchicalLink(field) {
		return field && field.__ct_boq_blocked !== undefined;
	}

	// The BOQ link doctypes. A Link to one of them is a BOQ search and its
	// results are governed by the BOQ policy of the app.
	const BOQ_LINK_DOCTYPES = ["BOQ Header", "BOQ Structure", "BOQ Item", "BOQ Item Stage"];

	// The doctypes that OWN a `boq_header` field.
	//
	// The transaction child doctypes receive the field as a Custom Field from
	// construction/install.py::_get_boq_custom_fields_for_doctype (it installs
	// it for every doctype of BOQ_CASCADE_DEPENDS_ON); the app's own BOQ
	// doctypes and the Variation Order carry the field in their DocType.
	//
	// This is the EXPLICIT KNOWN CONTEXT of the app. It is consulted only when
	// the live client metadata of the row doctype is not loaded; the metadata
	// is always preferred (see schemaOwnsBoqHeaderField).
	const BOQ_HEADER_OWNING_DOCTYPES = [
		// The BOQ cascade custom fields of the transaction child tables.
		"Purchase Order Item",
		"Purchase Receipt Item",
		"Purchase Invoice Item",
		"Stock Entry Detail",
		"Journal Entry Account",
		"Material Request Item",
		"Sales Invoice Item",
		"Timesheet Detail",
		// The app's own BOQ doctypes and the Variation Order.
		"BOQ Item",
		"BOQ Structure",
		"BOQ Item Stage",
		"BOQ Quantity Revision",
		"BOQ Cost Analysis",
		"BOQ Import Batch",
		"Variation Order",
	];

	// The child doctypes that carry NO `boq_header` field. Their BOQ context
	// is the parent document: a VO Line belongs to a Variation Order and the
	// Variation Order carries the BOQ Header.
	const BOQ_HEADER_INHERITING_DOCTYPES = ["VO Line"];

	// The document that owns the value of a control.
	//
	// The pinned Frappe grid creates a CHILD row control with the CHILD row
	// document and the PARENT form:
	//
	//   frappe/public/js/frappe/form/grid_row.js::make_control
	//     doc: this.doc,          // the child row document
	//     frm: this.grid.frm,     // the parent transaction form
	//     grid_row: this,         // the GridRow of this row
	//
	// and the expanded row form builds its controls from a layout that carries
	// the row:
	//
	//   frappe/public/js/frappe/form/grid_row_form.js::render
	//     new frappe.ui.form.Layout({ frm: this.row.frm, grid_row: this.row, ... })
	//
	// `field.frm.doc` is therefore the PARENT transaction, which owns no
	// `boq_header`; the BOQ Header of a transaction row lives on the ROW
	// document. A form control (standalone BOQ Item / BOQ Structure /
	// BOQ Item Stage / BOQ Quantity Revision / BOQ Cost Analysis) owns the form
	// document, so there the row document and the form document are the same
	// object.
	function getControlRowDoc(field) {
		if (!field) return null;
		const gridRowDoc =
			(field.grid_row && field.grid_row.doc) ||
			(field.layout && field.layout.grid_row && field.layout.grid_row.doc) ||
			null;
		if (gridRowDoc) return gridRowDoc;
		return field.doc || (field.frm && field.frm.doc) || null;
	}

	// The parent document of a child row control.
	function getControlParentDoc(field) {
		return (field && field.frm && field.frm.doc) || null;
	}

	// Is the control a control of a child row of a grid?
	//
	// The pinned vendor marks a grid row control with `grid_row` (the inline
	// control) or with `layout.grid_row` (the expanded row form control).
	function isGridRowControl(field) {
		if (!field) return false;
		return Boolean(field.grid_row || (field.layout && field.layout.grid_row));
	}

	// Does the SCHEMA of the doctype own a `boq_header` field?
	//
	// The live client metadata is authoritative: the desk receives the
	// DocFields of a doctype (including its Custom Fields), so
	// `frappe.meta.get_docfield` answers the question of the SCHEMA and not of
	// the current row. A doctype whose metadata is not loaded is UNKNOWN (and
	// NOT "does not own"): the explicit known context of the app decides, and
	// only a doctype that is unknown to the app falls back to the presence of
	// the field on the row document.
	//
	// Returns true, false or null (unknown).
	function schemaOwnsBoqHeaderField(doctype) {
		if (!doctype) return null;

		const meta = typeof frappe !== "undefined" && frappe ? frappe.meta : null;
		if (
			meta &&
			typeof meta.get_docfield === "function" &&
			meta.docfield_map &&
			meta.docfield_map[doctype]
		) {
			try {
				return Boolean(meta.get_docfield(doctype, "boq_header"));
			} catch (error) {
				return null;
			}
		}

		if (BOQ_HEADER_OWNING_DOCTYPES.includes(doctype)) return true;
		if (BOQ_HEADER_INHERITING_DOCTYPES.includes(doctype)) return false;
		return null;
	}

	// Does the row document own the BOQ Header decision?
	function rowOwnsBoqHeaderField(rowDoc) {
		const schema = schemaOwnsBoqHeaderField(rowDoc && rowDoc.doctype);
		if (schema === true) return true;
		if (schema === false) return false;
		// The schema of the row is unknown to the app: the only available
		// evidence is the field on the row document itself.
		return Boolean(rowDoc && (rowDoc.boq_header !== undefined || "boq_header" in rowDoc));
	}

	// The ONE effective context of a control.
	//
	// The gate, the prerequisite and the outgoing search all read THIS
	// context, so they cannot disagree about the row, the parent document or
	// the BOQ Header the control belongs to.
	function resolveBoqControlContext(field) {
		const rowDoc = getControlRowDoc(field);
		const parentDoc = getControlParentDoc(field);
		const ownsBoqHeader = rowOwnsBoqHeaderField(rowDoc);

		let boqHeader = null;
		let boqHeaderSource = null;
		if (ownsBoqHeader) {
			// The row owns the field: its value decides, and an empty value
			// keeps the dropdown closed. The parent header is NEVER borrowed
			// for such a row (a new row without a BOQ Header must not inherit
			// the header of an unrelated parent document).
			boqHeader = (rowDoc && rowDoc.boq_header) || null;
			boqHeaderSource = "row";
		} else if (parentDoc && parentDoc.boq_header) {
			// The row carries no `boq_header` field of its own: the parent
			// document is the context (the VO Line semantic).
			boqHeader = parentDoc.boq_header;
			boqHeaderSource = "parent";
		} else if (rowDoc && rowDoc.boq_header) {
			boqHeader = rowDoc.boq_header;
			boqHeaderSource = "row";
		}

		return {
			rowDoc: rowDoc,
			parentDoc: parentDoc,
			rowDoctype: (rowDoc && rowDoc.doctype) || field.doctype || "",
			rowName: (rowDoc && rowDoc.name) || field.docname || "",
			ownsBoqHeader: ownsBoqHeader,
			boqHeader: boqHeader,
			boqHeaderSource: boqHeaderSource,
			isGridRow: isGridRowControl(field),
		};
	}

	function hasBoqHeader(field) {
		return Boolean(resolveBoqControlContext(field).boqHeader);
	}

	function syncBoqNativeCreateState(field) {
		if (!isBoqStructureLink(field)) return;
		const blocked = !hasBoqHeader(field);
		field.__ct_boq_blocked = blocked;
		field.df.only_select = blocked;
		field.df.filter_description = blocked ? __("Select BOQ Header first") : "";
	}

	function patchNativeLinkControl() {
		const ControlLink = frappe.ui && frappe.ui.form && frappe.ui.form.ControlLink;
		if (!ControlLink || ControlLink.__ct_boq_patch_applied) return;

		const originalSetCustomQuery = ControlLink.prototype.set_custom_query;
		const originalGetSearchArgs = ControlLink.prototype.get_search_args;
		// The capture happens BEFORE the theme patches the class, so the
		// pristine native methods are the ones that are captured.
		captureNativeMethods(ControlLink);
		const patchedSetCustomQuery = function (args) {
			syncBoqNativeCreateState(this);
			if (originalSetCustomQuery) {
				originalSetCustomQuery.call(this, args);
			}
			syncBoqNativeCreateState(this);
			return args;
		};
		ControlLink.prototype.set_custom_query = patchedSetCustomQuery;

		const originalOnInput = ControlLink.prototype.on_input;
		ControlLink.prototype.on_input = function (e) {
			if (
				this.df &&
				this.df.options &&
				frappe.model &&
				typeof frappe.model.can_read === "function"
			) {
				const canRead = frappe.model.can_read(this.df.options);
				const canSelect =
					typeof frappe.model.can_select === "function"
						? frappe.model.can_select(this.df.options)
						: false;
				if (!canRead && !canSelect) {
					return;
				}
			}
			syncBoqNativeCreateState(this);
			return originalOnInput.call(this, e);
		};

		const originalValidate = ControlLink.prototype.validate;
		ControlLink.prototype.validate = function (value) {
			if (
				this.df &&
				this.df.options &&
				frappe.model &&
				typeof frappe.model.can_read === "function"
			) {
				const canRead = frappe.model.can_read(this.df.options);
				const canSelect =
					typeof frappe.model.can_select === "function"
						? frappe.model.can_select(this.df.options)
						: false;
				if (!canRead && !canSelect) {
					return value;
				}
			}
			return originalValidate.call(this, value);
		};

		const originalValidateLinkAndFetch = ControlLink.prototype.validate_link_and_fetch;
		ControlLink.prototype.validate_link_and_fetch = function (value) {
			if (
				this.df &&
				this.df.options &&
				frappe.model &&
				typeof frappe.model.can_read === "function"
			) {
				const canRead = frappe.model.can_read(this.df.options);
				const canSelect =
					typeof frappe.model.can_select === "function"
						? frappe.model.can_select(this.df.options)
						: false;
				if (!canRead && !canSelect) {
					return Promise.resolve(value);
				}
			}
			return originalValidateLinkAndFetch.call(this, value);
		};

		const patchedGetSearchArgs = function (txt) {
			if (
				this.df &&
				this.df.options &&
				frappe.model &&
				typeof frappe.model.can_read === "function"
			) {
				const canRead = frappe.model.can_read(this.df.options);
				const canSelect =
					typeof frappe.model.can_select === "function"
						? frappe.model.can_select(this.df.options)
						: false;
				if (!canRead && !canSelect) {
					return null;
				}
			}
			return originalGetSearchArgs.call(this, txt);
		};
		ControlLink.prototype.get_search_args = patchedGetSearchArgs;

		ControlLink.__ct_boq_patch_applied = true;
	}

	patchNativeLinkControl();
	setTimeout(patchNativeLinkControl, 0);

	function controlOwnsElement(control, element) {
		const wrappers = [
			control && control.$wrapper,
			control && control.wrapper,
			control && control.$input,
		];
		return wrappers.some((wrapper) => {
			const node = wrapper && (wrapper[0] || (wrapper.get && wrapper.get(0)) || wrapper);
			return node === element || Boolean(node && node.contains && node.contains(element));
		});
	}

	function getControlInstance(el) {
		const $el = $(el);
		const $control_wrapper = $el.closest(".frappe-control");
		if ($control_wrapper.length) {
			// 1. Direct DOM node reference (Gold Standard)
			if ($control_wrapper[0].fieldobj) {
				return $control_wrapper[0].fieldobj;
			}

			// 2. Fallbacks for other context environments
			const fieldname = $control_wrapper.attr("data-fieldname");
			if (fieldname) {
				const $grid_row = $el.closest(".grid-row");
				if ($grid_row.length) {
					const grid_row_obj = $grid_row.data("grid_row");
					const field = grid_row_obj?.fields_dict?.[fieldname];
					if (field && controlOwnsElement(field, el)) {
						return field;
					}
				}
				const dialogField = window.cur_dialog?.fields_dict?.[fieldname];
				if (controlOwnsElement(dialogField, el)) return dialogField;
				const listField = window.cur_list?.page?.fields_dict?.[fieldname];
				if (controlOwnsElement(listField, el)) return listField;
			}
		}
		if (frappe.query_report && frappe.query_report.filters) {
			const fieldname =
				$el.attr("data-fieldname") || $control_wrapper.attr("data-fieldname");
			const filter = frappe.query_report.filters.find((f) => f.df.fieldname === fieldname);
			if (controlOwnsElement(filter, el)) return filter;
		}
		return null;
	}

	function enhanceLink(el) {
		if (!el) return;

		if (el.getAttribute(CT_ATTR)) {
			// Always ensure the native input wrapper remains hidden
			const $input = $(el);
			const $linkFieldWrapper = $input.closest(".link-field");
			if ($linkFieldWrapper.length) {
				$linkFieldWrapper.css({
					opacity: 0,
					position: "absolute",
					pointerEvents: "none",
					zIndex: -1,
					width: 0,
					height: 0,
					overflow: "hidden",
				});
			}
			return;
		}

		const $el = $(el);
		if (
			$el.hasClass("hasDatepicker") ||
			$el.attr("data-fieldtype") === "Date" ||
			$el.attr("type") === "date" ||
			$el.closest('.frappe-control[data-fieldtype="Date"]').length ||
			$el.closest('.frappe-control[data-fieldtype="DateRange"]').length ||
			$el.closest('.frappe-control[data-fieldtype="Datetime"]').length ||
			/date/i.test($el.attr("name") || "") ||
			/date/i.test($el.attr("data-fieldname") || "")
		) {
			return;
		}

		const field = getControlInstance(el);
		if (!field || field.df.fieldtype !== "Link") return;

		const df = field.df;
		if (df.hidden || df.read_only) return;
		if (!df.options || typeof df.options !== "string") return;

		// Skip internal system link types
		const skipDoctypes = ["DocType", "DocField", "Workflow State", "Module Def", "Role"];
		if (skipDoctypes.includes(df.options)) return;

		// Skip and disable field if user has no read/select permission on the options doctype to prevent 403/Forbidden errors
		if (frappe.model && typeof frappe.model.can_read === "function") {
			const canRead = frappe.model.can_read(df.options);
			const canSelect =
				typeof frappe.model.can_select === "function"
					? frappe.model.can_select(df.options)
					: false;
			if (!canRead && !canSelect) {
				field.df.read_only = 1;
				const $input = $(el);
				$input.prop("disabled", true);
				$input.attr("readonly", true);
				$input.off("focus");
				$input.off("input");
				return;
			}
		}

		el.setAttribute(CT_ATTR, "1");

		const $input = $(el);
		const $linkFieldWrapper = $input.closest(".link-field");
		if (!$linkFieldWrapper.length) return;

		const $parent = $linkFieldWrapper.parent();
		$parent.css("position", "relative");

		const uid = "ctl-" + Math.random().toString(36).slice(2, 8);

		// Unified Dropdown HTML structure
		const $dropdown = $(`
            <div class="dropdown ct-unified-dropdown" id="${uid}">
                <button class="btn-reset dropdown-toggle ct-dropdown-btn" type="button" aria-haspopup="true" aria-expanded="false">
                    <span class="ct-dropdown-label"></span>
                    <svg width="10" height="7" viewBox="0 0 10 7" fill="none" style="transition: transform 0.2s ease;">
                        <path d="M1 1l4 4.5L9 1" stroke="var(--ct-primary)" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                </button>
                <div class="dropdown-menu ct-dropdown-menu">
                    <div class="ct-dropdown-search-wrapper">
                        <input type="text" class="ct-dropdown-search" placeholder="${__(
							"Search…"
						)}" autocomplete="off">
                    </div>
                    <div class="ct-dropdown-list"></div>
                    <div class="ct-dropdown-footer d-flex justify-content-end">
                        <button class="btn btn-secondary btn-xs ct-btn-select-all text-nowrap">
                            ${__("Select All")}
                        </button>
                        <button class="btn btn-primary btn-xs ct-btn-clear-all text-nowrap">
                            ${__("Clear All")}
                        </button>
                    </div>
                </div>
            </div>
        `);

		$parent.append($dropdown);

		const $btn = $dropdown.find(".ct-dropdown-btn");
		const $label = $dropdown.find(".ct-dropdown-label");
		const $menu = $dropdown.find(".ct-dropdown-menu");
		const $search = $dropdown.find(".ct-dropdown-search");
		const $list = $dropdown.find(".ct-dropdown-list");
		const $selectAllBtn = $dropdown.find(".ct-btn-select-all");
		const $clearAllBtn = $dropdown.find(".ct-btn-clear-all");

		function updateBoqFirstStepAccent() {
			const isFirstStep = field.df.fieldname === "boq_header";
			const needsAccent = isFirstStep && !field.get_value();
			$dropdown.toggleClass("ct-boq-first-step", needsAccent);
			$btn.css({
				"border-color": needsAccent
					? "var(--ct-danger, #dc2626)"
					: "var(--ct-border, rgba(148,163,184,0.18))",
				"box-shadow": needsAccent ? "0 0 0 2px rgba(220,38,38,0.18)" : "none",
			});
			const isBlocked = isHierarchicalLink(field) && field.__ct_boq_blocked;
			if (!isBlocked) {
				$btn.attr(
					"title",
					needsAccent
						? __("Start here: select BOQ Header first")
						: __("Select {0}", [__(field.df.label || field.df.fieldname)])
				);
			}
		}

		$clearAllBtn.on("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const promise = field.set_value("");
			if (promise && promise.then) {
				promise.then(() => {
					syncLabel();
					closeDropdown();
				});
			} else {
				syncLabel();
				closeDropdown();
			}
		});

		$selectAllBtn.on("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const $firstItem = $list.find(".dropdown-item[data-value]").first();
			if ($firstItem.length) {
				$firstItem.trigger("click");
			} else {
				closeDropdown();
			}
		});

		// Sync label from current select value
		function syncLabel() {
			const val = field.get_value() || "";
			const text = field.get_label_value() || val;
			const placeholder = field.df.label ? __(field.df.label) : __("Select…");

			const $wrapper = $input.closest(".frappe-control");
			const isBlockedByFlag = isHierarchicalLink(field) && field.__ct_boq_blocked;
			const isBlockedByClass = $wrapper.hasClass("ct-boq-step-blocked");
			const isBlocked = isBlockedByFlag || isBlockedByClass;
			$dropdown.toggleClass("ct-dropdown-blocked", !!isBlocked);

			if (isBlocked && !text) {
				var hint = field.df.filter_description; // already translated by form script
				if (!hint) {
					hint =
						$wrapper.find(".ct-boq-inline-hint").text().trim() ||
						__("Select parent field first");
				}
				$label.text(hint);
				$btn.attr("title", hint);
			} else {
				$label.text(text || placeholder);
			}
			updateBoqFirstStepAccent();
		}
		syncBoqNativeCreateState(field);
		syncLabel();
		setTimeout(function () {
			syncBoqNativeCreateState(field);
			syncLabel();
		}, 200);
		setTimeout(function () {
			syncBoqNativeCreateState(field);
			syncLabel();
		}, 700);

		function syncGridQuery() {
			const cascadeFields = ["boq_header", "boq_structure", "boq_item", "boq_item_stage"];
			if (!cascadeFields.includes(field.df.fieldname)) return;

			const $gridRow = $input.closest(".grid-row");
			const gridRow = $gridRow.data("grid_row");
			const grid = gridRow && gridRow.grid;
			if (!grid || !grid.get_field) return;

			const gridField = grid.get_field(field.df.fieldname);
			if (gridField && gridField.get_query) {
				field.get_query = gridField.get_query;
			}
		}

		function getScope() {
			if (window.scopeContext && window.scopeContext.enabled) {
				return window.scopeContext.getValidatedCurrentScope();
			}
			return {};
		}

		function withScope(filters) {
			const mode = frappe.boot.enable_boq_cascade_filtering || "Off";
			if (!["On", "Strict"].includes(mode)) return filters;

			const scope = getScope();
			["company", "cost_center", "project"].forEach((fieldname) => {
				if (scope[fieldname] && !filters[fieldname]) {
					filters[fieldname] = scope[fieldname];
				}
			});
			filters.enforce_scope = true;
			return filters;
		}

		// The BOQ cascade fields of the app: the fields whose search is
		// governed by the BOQ cascade policy of the app
		// (construction/public/js/boq_filters.js) and by the native form
		// queries of the app.
		const BOQ_CASCADE_FIELDS = ["boq_header", "boq_structure", "boq_item", "boq_item_stage"];

		// A Link to a BOQ doctype is a BOQ search.
		function isBoqLinkField() {
			return Boolean(field && field.df && BOQ_LINK_DOCTYPES.includes(field.df.options));
		}

		// The narrow policy of the app for a BOQ cascade field.
		//
		// It mirrors the native BOQ queries of the app
		// (construction/public/js/boq_filters.js::buildHeaderFilters,
		// buildStructureFilters, buildItemFilters and buildStageFilters) and the
		// Variation Order form queries (variation_order.js).
		//
		// The policy is applied ON TOP of the native policy of the control and
		// may therefore only NARROW it: a value the native policy already
		// constrains is never overwritten (see mergePolicyFilters).
		//
		// It is also the only policy of a form level BOQ link that the app
		// never gave a native query (the BOQ Cost Analysis, BOQ Quantity
		// Revision, BOQ Import Batch and BOQ Structure forms).
		function getBoqCascadePolicy(context) {
			const row = context.rowDoc;
			const fieldname = field.df.fieldname;
			if (!BOQ_CASCADE_FIELDS.includes(fieldname)) return null;

			const policy = { query: null, filters: {} };
			const filters = policy.filters;

			if (fieldname === "boq_header") {
				policy.query = "construction.api.boq_link_queries.get_boq_headers";
			} else if (fieldname === "boq_structure") {
				policy.query = "construction.api.boq_link_queries.get_boq_structures";
				if (context.boqHeader) filters.boq_header = context.boqHeader;
				// Parity with the VO Line form query (variation_order.js), which already
				// excludes structures whose items are all omitted.
				if (context.rowDoctype === "VO Line") filters.exclude_zero_revised = true;
			} else if (fieldname === "boq_item") {
				// Parity with the form queries (buildItemFilters / variation_order.js),
				// which both pass exclude_zero_revised so omitted items are not offered.
				filters.exclude_zero_revised = true;
				if (context.rowDoctype === "VO Line") {
					policy.query = "construction.api.boq_link_queries.get_vo_line_boq_items";
					if (context.boqHeader) filters.boq_header = context.boqHeader;
					if (row && row.boq_structure) filters.structure = row.boq_structure;
					filters.require_boq_header = true;
				} else {
					policy.query = "construction.api.boq_link_queries.get_boq_items";
					// The project of the row, the project of the parent document or
					// the project of the scope, exactly like the native rowProject()
					// of the app, so the two policies never disagree.
					const project =
						(row && row.project) ||
						(context.parentDoc && context.parentDoc.project) ||
						null;
					if (project) filters.project = project;
					if (context.boqHeader) filters.boq_header = context.boqHeader;
					if (row && row.boq_structure) filters.structure = row.boq_structure;
					filters.require_boq_header = true;
					filters.require_structure = true;
					filters.allowed_statuses = ["Frozen", "Locked"];
				}
			} else if (fieldname === "boq_item_stage") {
				policy.query = "construction.api.boq_link_queries.get_boq_item_stages";
				if (row && row.boq_item) filters.boq_item = row.boq_item;
				if (context.boqHeader) filters.boq_header = context.boqHeader;
				if (row && row.boq_structure) filters.structure = row.boq_structure;
				filters.require_boq_item = true;
			}

			withScope(filters);
			return policy;
		}

		// -------------------------------------------------------------------
		// The BOQ request adapter of the themed dropdown.
		//
		// The themed dropdown NEVER builds a request of its own for a BOQ
		// link. It asks the REAL pinned native contract of the control
		// (frappe/public/js/frappe/form/controls/link.js: get_search_args ->
		// set_custom_query) with the IDENTITY of the edited row, on a THROWAWAY
		// facade of the control, and it may only NARROW the answer with the
		// narrow policy of the app.
		//
		// The whole native contract of the field therefore reaches the request:
		// the DocField filters, the operator filters of the link_filters and
		// the plain object / string / function get_query. None of it is
		// transcribed by the app, and there is NO fallback for a native
		// contract that failed: a request the native contract could not build
		// closes the search.
		//
		// Three facts are kept apart:
		//
		//   absent    the control carries no native query at all
		//   failed    the native query threw
		//   malformed the native answer carries no policy
		//
		// A failed or malformed policy closes the search EVERYWHERE. An absent
		// policy closes the search of a grid row (the policy of a grid row is
		// mandatory) and only an absent policy of a documented root form
		// context may use the reviewed narrow fallback of the app.
		// -------------------------------------------------------------------

		// A plain object, the way the pinned native contract decides it
		// ($.isPlainObject), but without depending on jQuery.
		function isPlainObject(value) {
			if (!value || typeof value !== "object" || Array.isArray(value)) return false;
			return Object.prototype.toString.call(value) === "[object Object]";
		}

		function deepEqual(left, right) {
			if (left === right) return true;
			if (Array.isArray(left) && Array.isArray(right)) {
				if (left.length !== right.length) return false;
				return left.every((value, index) => deepEqual(value, right[index]));
			}
			if (isPlainObject(left) && isPlainObject(right)) {
				const leftKeys = Object.keys(left);
				const rightKeys = Object.keys(right);
				if (leftKeys.length !== rightKeys.length) return false;
				return leftKeys.every(
					(key) =>
						Object.prototype.hasOwnProperty.call(right, key) &&
						deepEqual(left[key], right[key])
				);
			}
			return false;
		}

		// The comparison operators of the pinned vendor
		// (frappe/frappe/database/operator_map.py of the pinned Frappe).
		//
		// A filter value that is an array whose first entry is one of them
		// carries a COMPARISON ("=", "like", "in", ...), not a set of allowed
		// values: it is never intersected, flattened or converted.
		const FILTER_OPERATORS = [
			"=",
			"!=",
			"<",
			">",
			"<=",
			"=<",
			">=",
			"=>",
			"in",
			"not in",
			"like",
			"ilike",
			"not like",
			"regex",
			"between",
			"is",
			"timespan",
			"set",
			"not set",
		];

		function isOperatorFilterValue(value) {
			return (
				Array.isArray(value) &&
				value.length > 0 &&
				typeof value[0] === "string" &&
				FILTER_OPERATORS.includes(value[0].toLowerCase())
			);
		}

		// A filter value that is a SET of allowed values (the statuses of the
		// app, for example). Two sets are composed by their INTERSECTION.
		function isSetFilterValue(value) {
			return Array.isArray(value) && !isOperatorFilterValue(value);
		}

		// The effective native query of the control.
		function getEffectiveNativeQuery() {
			return field.get_query || field.df.get_query || null;
		}

		// The policy of the control, asked with the IDENTITY of the edited row.
		//
		//   { status: "absent" }   the control carries no native query at all
		//   { status: "failed" }   the native query threw
		//   { status: "malformed" } the native answer carries no policy
		//   { status: "ok", ... }  the native answer is usable
		//
		// An ABSENT policy and a FAILED policy are different facts and are
		// never reported as the same thing. A failed or malformed policy closes
		// the search everywhere; only an absent policy of a documented root
		// form context may use the reviewed narrow fallback of the app.
		function resolveNativePolicy(context) {
			const getQuery = getEffectiveNativeQuery();
			if (getQuery === null || getQuery === undefined) {
				return { status: "absent" };
			}
			if (typeof getQuery === "string") {
				return { status: "ok", kind: "string", answer: getQuery };
			}
			if (isPlainObject(getQuery)) {
				// The pinned native contract also accepts a plain object.
				return { status: "ok", kind: "object", answer: getQuery };
			}
			if (typeof getQuery !== "function") {
				return { status: "malformed" };
			}

			let answer = null;
			try {
				answer = getQuery(
					context.parentDoc || context.rowDoc,
					context.rowDoctype,
					context.rowName
				);
			} catch (error) {
				return { status: "failed", error: error };
			}
			if (typeof answer === "string") {
				return { status: "ok", kind: "string", answer: answer };
			}
			if (!isPlainObject(answer)) {
				// undefined, null, a number or an array: the answer carries no
				// policy at all.
				return { status: "malformed" };
			}
			if (!answer.query && !answer.filters) {
				// The function branch of the pinned contract keeps only a query
				// or a filter set; anything else carries no policy.
				return { status: "malformed" };
			}
			if (answer.filters !== undefined && !isPlainObject(answer.filters)) {
				return { status: "malformed" };
			}
			return { status: "ok", kind: "answer", answer: answer };
		}

		// The SUPPLIED restrictions of the field: the filters of the DocField
		// and the operator filters of its link_filters.
		//
		// The pinned native contract reads the link_filters with
		// `apply_link_field_filters`, which SWALLOWS a malformed link_filters
		// (it logs the error and returns {}). A swallowed restriction is a
		// WIDENED search, so the supplied restrictions are validated BEFORE the
		// native contract runs: an unreadable, malformed or unevaluable
		// restriction closes the search.
		//
		// This is a gate, not a second implementation of the contract: it never
		// builds a filter, it only refuses a restriction that the native
		// contract would drop.
		function validateSuppliedRestrictions(context) {
			const df = field.df || {};
			if (df.filters !== undefined && df.filters !== null && !isPlainObject(df.filters)) {
				return false;
			}

			const raw = df.link_filters;
			if (!raw || !raw.length) return true;

			let entries = null;
			try {
				entries = JSON.parse(raw);
			} catch (error) {
				return false;
			}
			if (!Array.isArray(entries)) return false;

			for (const entry of entries) {
				if (!Array.isArray(entry) || entry.length < 4) return false;
				const fieldname = entry[1];
				const operator = entry[2];
				const value = entry[3];
				if (typeof fieldname !== "string" || !fieldname) return false;
				if (typeof operator !== "string" || !operator) return false;
				if (!FILTER_OPERATORS.includes(operator.toLowerCase())) return false;
				if (typeof value === "string" && value.startsWith("eval:")) {
					if (evaluateLinkFilterValue(context, value) === undefined) return false;
				}
			}
			return true;
		}

		// The `eval:` values of the link_filters, evaluated with the context
		// the pinned native contract uses
		// (frappe/public/js/frappe/form/controls/link.js::parse_filters).
		function evaluateLinkFilterValue(context, value) {
			try {
				const utils = frappe && frappe.utils;
				if (!utils || typeof utils.eval !== "function") return undefined;
				const rowDoc = context.rowDoc;
				return utils.eval(value.split("eval:")[1], {
					doc: rowDoc,
					parent: rowDoc && rowDoc.parenttype ? context.parentDoc : null,
					frappe: frappe,
				});
			} catch (error) {
				return undefined;
			}
		}

		// A THROWAWAY facade of the control.
		//
		// It carries the IDENTITY of the edited row and a COPY of the DocField
		// of the control, so the native contract can neither mutate the
		// protected field definition (the native `set_nulls` deletes the empty
		// entries of `df.filters` in place) nor the real control.
		function buildNativeFacade(context, policy, methods) {
			const ControlLink = frappe.ui && frappe.ui.form && frappe.ui.form.ControlLink;
			const facade = ControlLink ? Object.create(ControlLink.prototype) : {};
			const df = field.df || {};
			facade.df = Object.assign({}, df);
			if (isPlainObject(df.filters)) facade.df.filters = Object.assign({}, df.filters);
			facade.frm = field.frm;
			facade.doc = context.rowDoc;
			facade.doctype = context.rowDoctype;
			facade.docname = context.rowName;
			facade.translate_values = field.translate_values;
			facade.get_options = function () {
				return field.df.options;
			};
			facade.set_custom_query = methods.setCustomQuery;
			if (policy.kind === "answer") {
				// The answer is already resolved with the identity of the row:
				// the native contract must not ask the native query a second
				// time.
				facade.get_query = function () {
					return policy.answer;
				};
			} else {
				facade.get_query = policy.answer;
			}
			return facade;
		}

		// The REAL pinned native contract of the class of the control.
		//
		// null means that the native contract could not produce a request: the
		// method is not available in this class, or it threw. There is NO
		// fallback: a request the native contract could not build is never
		// replaced by a request of the app.
		function runNativeSearchArgs(searchTerm, context, policy) {
			const ControlLink = frappe.ui && frappe.ui.form && frappe.ui.form.ControlLink;
			const methods = captureNativeMethods(ControlLink);
			if (!methods) return null;
			if (typeof methods.getSearchArgs !== "function") return null;
			if (typeof methods.setCustomQuery !== "function") return null;

			let facade = null;
			try {
				facade = buildNativeFacade(context, policy, methods);
				const args = methods.getSearchArgs.call(facade, searchTerm || "");
				if (!args || typeof args !== "object") return null;
				// The native contract turns the translation of the values off on
				// the control itself; the facade carries it back.
				if (facade.translate_values !== field.translate_values) {
					field.translate_values = facade.translate_values;
				}
				return args;
			} catch (error) {
				return null;
			}
		}

		// The policy of the app merged into the native policy.
		//
		// The native policy is NEVER overwritten:
		//   - a key the native policy does not constrain takes the value of the
		//     app (a narrowing);
		//   - a key both constrain with the same value keeps the native value;
		//   - a key both constrain with a SET value takes the INTERSECTION of
		//     the two sets, which is narrower than both; an empty intersection
		//     is a conflict;
		//   - a key both constrain with different values is a conflict: the two
		//     policies disagree, so the search is CLOSED instead of silently
		//     choosing one of them.
		//
		// A conflict is never resolved in favour of the app: the app may only
		// narrow the native policy, never widen it and never replace it.
		function mergePolicyFilters(nativeFilters, appFilters) {
			const result = Object.assign({}, nativeFilters || {});
			const conflict = [];
			Object.keys(appFilters || {}).forEach((key) => {
				const appValue = appFilters[key];
				if (!Object.prototype.hasOwnProperty.call(result, key)) {
					result[key] = appValue;
					return;
				}
				const nativeValue = result[key];
				if (deepEqual(nativeValue, appValue)) return;
				if (isSetFilterValue(nativeValue) && isSetFilterValue(appValue)) {
					const intersection = nativeValue.filter((value) =>
						appValue.some((candidate) => deepEqual(candidate, value))
					);
					if (!intersection.length) {
						conflict.push(key);
						return;
					}
					result[key] = intersection;
					return;
				}
				conflict.push(key);
			});
			return { filters: result, conflict: conflict };
		}

		// The request of the themed dropdown.
		//
		// It is the request of the REAL pinned native contract of the control,
		// narrowed by the policy of the app. The app may only narrow: a value
		// the native policy already constrains is kept, two SET values are
		// intersected and a conflict CLOSES the search.
		//
		// null means that the search must be CLOSED.
		function buildRequestArgs(searchTerm, context, policy) {
			const args = runNativeSearchArgs(searchTerm, context, policy);
			if (!args) return null;

			// A filter set that is not a plain object (a list of operator
			// filters) cannot be composed with the policy of the app without
			// changing its meaning, so the search is closed instead.
			if (args.filters !== undefined && !isPlainObject(args.filters)) return null;

			// The narrow policy of the app, merged into the native policy.
			const appPolicy = getBoqCascadePolicy(context);
			const appFilters = Object.assign({}, appPolicy ? appPolicy.filters : {});
			// The effective BOQ Header of the control is the context of the
			// search: it can only narrow it. The list of the BOQ Headers is
			// not filtered by the header of the row.
			if (context.boqHeader && field.df.options !== "BOQ Header") {
				appFilters.boq_header = context.boqHeader;
			}
			const merged = mergePolicyFilters(args.filters, appFilters);
			if (merged.conflict.length) return null;
			if (Object.keys(merged.filters).length) {
				args.filters = merged.filters;
			}
			if (!args.query && appPolicy && appPolicy.query) {
				args.query = appPolicy.query;
			}
			return args;
		}

		// The search arguments of the themed dropdown.
		//
		// A BOQ link searches through the AUTHORITATIVE native query of the
		// control, asked with the identity of the edited row. The native
		// answer carries the whole BOQ policy of the app: the omission
		// exclusion, the scope enforcement, the require_gate / gate_open gates
		// and the native per-account AccountingDimensionFilter of the BOQ Item
		// dimension.
		//
		// The native policy is MANDATORY for a child row of a grid: the app
		// installs the BOQ cascade policy on the grids of the transaction
		// forms and of the Variation Order. A failed, malformed or missing
		// mandatory policy CLOSES the search; the themed control never falls
		// back to an independent, broader query.
		//
		// Only a documented root form context (a form level BOQ link of a form
		// without any client query of its own) may use the reviewed narrow
		// fallback of the app when the control carries NO native query at all.
		//
		// Every other Link keeps the native behaviour of the control.
		function getSearchArgs(searchTerm, context) {
			if (!isBoqLinkField()) {
				return field.get_search_args(searchTerm || "");
			}
			if (!hasLinkPermission()) return null;

			// The supplied restrictions of the field are validated BEFORE the
			// native contract runs: the native contract swallows a malformed
			// link_filters, and a swallowed restriction is a widened search.
			if (!validateSuppliedRestrictions(context)) return null;

			const policy = resolveNativePolicy(context);

			if (policy.status === "failed" || policy.status === "malformed") {
				// A SUPPLIED native policy that failed or that carries no
				// policy closes the search, everywhere: an independent query
				// would offer rows the native policy excludes.
				return null;
			}

			if (policy.status === "absent") {
				// The control carries NO native query at all. A child row of a
				// grid must not search without the mandatory policy of the
				// grid; only a form level BOQ link may use the reviewed narrow
				// fallback of the app.
				if (context.isGridRow) return null;
				if (!getBoqCascadePolicy(context)) return null;
			}

			return buildRequestArgs(searchTerm, context, policy);
		}

		// The permission gate of the theme.
		//
		// A control whose target doctype may neither be read nor selected
		// offers no search at all; the native control of the desk behaves the
		// same way.
		function hasLinkPermission() {
			if (!field.df || !field.df.options) return true;
			if (!frappe.model || typeof frappe.model.can_read !== "function") return true;
			const canRead = frappe.model.can_read(field.df.options);
			const canSelect =
				typeof frappe.model.can_select === "function"
					? frappe.model.can_select(field.df.options)
					: false;
			return canRead || canSelect;
		}

		// The prerequisite of the themed dropdown: the BOQ Header of the
		// EFFECTIVE context of the control.
		function getBoqPreconditionMessage(context) {
			const isStructureField =
				field.df.fieldname === "boq_structure" || field.df.fieldname === "structure";
			if (isStructureField && !context.boqHeader) {
				return __("Select BOQ Header first");
			}
			return null;
		}

		// Render search options from database
		function renderOptions(searchTerm) {
			syncBoqNativeCreateState(field);
			$list.html(
				`<div style="padding: 10px; text-align: center; color: var(--ct-text-muted);"><i class="fa fa-spinner fa-spin"></i> ${__(
					"Loading..."
				)}</div>`
			);

			syncGridQuery();
			// The ONE effective context of the control: the gate, the
			// prerequisite and the outgoing search all read it.
			const context = resolveBoqControlContext(field);
			const preconditionMessage = getBoqPreconditionMessage(context);
			if (preconditionMessage) {
				$list.html(
					`<div style="padding: 10px; color: var(--ct-text-muted); font-style: italic;">${frappe.utils.escape_html(
						preconditionMessage
					)}</div>`
				);
				return;
			}
			const args = getSearchArgs(searchTerm, context);
			if (!args) {
				$list.html(
					`<div style="padding: 10px; color: var(--ct-text-muted); font-style: italic;">${__(
						"No options available"
					)}</div>`
				);
				return;
			}

			frappe.call({
				type: "GET",
				method: "frappe.desk.search.search_link",
				args: args,
				no_spinner: true,
				callback: function (r) {
					$list.empty();
					const items = r.message || [];

					// 1. None / Clear option (for optional fields)
					if (!df.reqd) {
						const $noneItem = $(`
                            <a class="dropdown-item" href="#" style="font-style: italic; color: var(--ct-text-muted);">
                                — ${__("None")} —
                            </a>
                        `);
						$noneItem.on("click", function (e) {
							e.preventDefault();
							const promise = field.set_value("");
							if (promise && promise.then) {
								promise.then(() => {
									syncLabel();
									closeDropdown();
								});
							} else {
								syncLabel();
								closeDropdown();
							}
						});
						$list.append($noneItem);
					}

					// 2. Options list
					let count = 0;
					items.forEach((item) => {
						const val = item.value;
						const labelText = item.label || val;
						const isSelected = val === field.get_value();

						const $itemEl = $(`
                            <a class="dropdown-item ${
								isSelected ? "active" : ""
							}" href="#" data-value="${val}">
                                ${frappe.utils.escape_html(labelText)}
                            </a>
                        `);

						$itemEl.on("click", function (e) {
							e.preventDefault();
							const promise = field.set_value(val);
							if (promise && promise.then) {
								promise.then(() => {
									syncLabel();
									closeDropdown();
								});
							} else {
								syncLabel();
								closeDropdown();
							}
						});

						$list.append($itemEl);
						count++;
					});

					// 3. Create New item (if allowed)
					const doctype = df.options;
					if (
						!df.only_select &&
						!field.__ct_boq_blocked &&
						frappe.model.can_create(doctype)
					) {
						if (count > 0 && !df.reqd) {
							$list.append('<div class="ct-dropdown-divider"></div>');
						}
						const $newItem = $(`
                            <a class="dropdown-item" href="#" style="font-weight: 600; color: var(--ct-primary);">
                                <i class="fa fa-plus"></i> ${__("Create a new {0}", [
									__(doctype),
								])}…
                            </a>
                        `);
						$newItem.on("click", function (e) {
							e.preventDefault();
							closeDropdown();
							field.new_doc();
						});
						$list.append($newItem);
					} else if (count === 0 && df.reqd) {
						$list.append(
							`<div style="padding: 10px; color: var(--ct-text-muted); font-style: italic;">${__(
								"No results"
							)}</div>`
						);
					}
				},
			});
		}

		// Position and open dropdown
		function openDropdown() {
			if (field && isHierarchicalLink(field) && field.__ct_boq_blocked) {
				return;
			}
			$(".ct-dropdown-menu:visible").hide();
			const rect = $btn[0].getBoundingClientRect();
			const spaceBelow = window.innerHeight - rect.bottom;
			const menuH = 280;

			$menu.css({
				display: "block",
				top: spaceBelow > menuH ? rect.bottom + 2 + "px" : rect.top - menuH - 2 + "px",
				left: rect.left + "px",
				width: Math.max(rect.width, 220) + "px",
			});
			$btn.find("svg").css("transform", "rotate(180deg)");
			$search.val("").focus();
			renderOptions("");
		}

		function closeDropdown() {
			$menu.hide();
			$btn.find("svg").css("transform", "none");
		}

		$btn.on("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			syncBoqNativeCreateState(field);
			syncLabel();
			if ($menu.is(":visible")) {
				closeDropdown();
			} else {
				openDropdown();
			}
		});

		// Close on outside click
		$(document).on("click.ct-dropdown-" + uid, function (e) {
			if (!$dropdown.is(e.target) && !$dropdown.has(e.target).length) {
				closeDropdown();
			}
		});

		// Search filtering (debounced)
		let searchTimeout = null;
		$search.on("input", function () {
			clearTimeout(searchTimeout);
			const term = $(this).val();
			searchTimeout = setTimeout(() => {
				renderOptions(term);
			}, 300);
		});

		// Native events synchronization
		$input.on("change select-change", syncLabel);
		$input.on("focus", function () {
			syncBoqNativeCreateState(field);
			syncLabel();
		});
		$input.on("blur", function () {
			syncBoqNativeCreateState(field);
			syncLabel();
		});

		// Hide native input wrapper visually
		$linkFieldWrapper.css({
			opacity: 0,
			position: "absolute",
			pointerEvents: "none",
			zIndex: -1,
			width: 0,
			height: 0,
			overflow: "hidden",
		});

		// Watch for blocker class changes applied by form scripts
		const $fw = $input.closest(".frappe-control");
		if ($fw.length && typeof MutationObserver !== "undefined") {
			const classObserver = new MutationObserver(function (mutations) {
				for (const m of mutations) {
					if (m.type === "attributes" && m.attributeName === "class") {
						syncLabel();
						break;
					}
				}
			});
			classObserver.observe($fw[0], { attributes: true, attributeFilter: ["class"] });
		}
	}

	function scanAndEnhance() {
		// Restrict strictly to elements inside .frappe-control[data-fieldtype='Link']
		// to avoid matching Date inputs or other non-Link input elements.
		$(".frappe-control[data-fieldtype='Link'] input.form-control").each(function () {
			try {
				enhanceLink(this);
			} catch (e) {
				/* silent */
			}
		});
	}

	// Bind events
	$(document).on("page-change", function () {
		setTimeout(scanAndEnhance, 400);
	});

	$(document).on("form-refresh", function () {
		setTimeout(scanAndEnhance, 300);
	});

	// Initial scan after boot
	$(document).ready(function () {
		setTimeout(scanAndEnhance, 800);

		// Patch query_report to re-scan after filters render
		const _orig =
			frappe.views && frappe.views.QueryReport && frappe.views.QueryReport.prototype;
		if (_orig && _orig.setup_filters) {
			const __sf = _orig.setup_filters;
			_orig.setup_filters = function () {
				const r = __sf.call(this);
				setTimeout(scanAndEnhance, 500);
				return r;
			};
		}
	});

	// Expose enhancer functions
	frappe.provide("construction.ct_link_enhancer");
	construction.ct_link_enhancer.scan = scanAndEnhance;
	construction.ct_link_enhancer.enhanceLink = enhanceLink;

	// Dynamic DOM mutation scanning to enhance dynamic filters/fields
	if (typeof MutationObserver !== "undefined") {
		const observer = new MutationObserver(function () {
			try {
				scanAndEnhance();
			} catch (e) {
				/* silent */
			}
		});
		$(document).ready(function () {
			observer.observe(document.body, { childList: true, subtree: true });
		});
	}
})();
