/**
 * Searchable Dropdown Enhancer
 * Wraps Frappe's native Link field Autocomplete for enhanced UX.
 *
 * Usage:
 * new SearchableDropdownEnhancer({
 *     field: frm.fields_dict.account,
 *     doctype: 'Account',
 *     display_format: '{account_code} - {account_name}',
 *     search_fields: ['account_code', 'account_name', 'account_name_ar'],
 *     filters: { is_group: 0 },
 *     clear_option: true
 * });
 */

class SearchableDropdownEnhancer {
	constructor(config) {
		this.field = config.field;
		this.doctype = config.doctype;
		this.display_format = config.display_format || "{name}";
		this.search_fields = config.search_fields || ["name"];
		this.filters = config.filters || {};
		this.clear_option = config.clear_option !== false;

		if (!this.field) {
			console.error("SearchableDropdownEnhancer: field is required");
			return;
		}

		this.init();
	}

	init() {
		// Set custom query to route to our backend API
		this.setCustomQuery();

		// Add CSS class for scoped styling
		this.applyStyling();

		// Bind clear option if enabled
		if (this.clear_option) {
			this.bindClearOption();
		}

		// Mark as enhanced
		this.field._searchableDropdown = this;
	}

	setCustomQuery() {
		const self = this;

		this.field.get_query = function () {
			return {
				query: "construction.searchable_dropdown.api.search.searchable_link_search",
				filters: {
					doctype: self.doctype,
					search_fields: self.search_fields,
					display_format: self.display_format,
					...self.filters,
				},
			};
		};
	}

	applyStyling() {
		// Add class for CSS scoping
		if (this.field.$input_area) {
			this.field.$input_area.addClass("searchable-dropdown");
		}

		// Add to wrapper as well for broader scope
		if (this.field.$wrapper) {
			this.field.$wrapper.addClass("searchable-dropdown-wrapper");
		}
	}

	bindClearOption() {
		// Append "— بلا —" option to dropdown on open
		const self = this;

		if (this.field.$input) {
			this.field.$input.on("awesomplete-open", function () {
				self.addClearOption();
			});
		}
	}

	addClearOption() {
		const self = this;
		const awesomplete = this.field.$input.data("awesomplete");

		if (!awesomplete || !awesomplete.ul) return;

		// Check if clear option already exists
		const existingClear = awesomplete.ul.querySelector(".clear-option");
		if (existingClear) return;

		// Create clear option element
		const clearLi = document.createElement("li");
		clearLi.className = "clear-option awesomplete-list-item";
		clearLi.setAttribute("role", "option");
		clearLi.setAttribute("aria-selected", "false");
		clearLi.innerHTML = "<span>— بلا —</span>";

		// Click handler
		clearLi.addEventListener("click", function (e) {
			e.preventDefault();
			e.stopPropagation();

			// Clear the field
			self.field.set_value("");

			// Close dropdown
			if (awesomplete) {
				awesomplete.close();
			}
		});

		// Append to list
		awesomplete.ul.appendChild(clearLi);
	}

	destroy() {
		// Remove CSS classes
		if (this.field.$input_area) {
			this.field.$input_area.removeClass("searchable-dropdown");
		}
		if (this.field.$wrapper) {
			this.field.$wrapper.removeClass("searchable-dropdown-wrapper");
		}

		// Remove event listeners
		if (this.field.$input) {
			this.field.$input.off("awesomplete-open");
		}

		// Reset get_query to default
		this.field.get_query = null;

		// Remove marker
		delete this.field._searchableDropdown;
	}
}

// Export for global use
frappe.provide("construction.searchable_dropdown");
construction.searchable_dropdown.Enhancer = SearchableDropdownEnhancer;

// Utility function for quick enhancement
construction.searchable_dropdown.enhance = function (field, config) {
	if (!field) {
		console.warn("searchable_dropdown.enhance: field not found");
		return null;
	}

	return new SearchableDropdownEnhancer({
		field: field,
		...config,
	});
};
