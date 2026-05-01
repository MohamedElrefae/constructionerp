/**
 * Property-Based Tests for ColumnConfigManager
 *
 * Uses fast-check with Node.js built-in test runner.
 * Each property runs a minimum of 100 iterations.
 *
 * Feature: print-settings-dialog
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fc = require("fast-check");
const { ColumnConfigManager } = require("../../public/js/print_settings_dialog.js");

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/**
 * Generates a valid ColumnDescriptor with unique field_key within an array.
 * Constrains widths to [1, 100] and sort_order to non-negative integers.
 */
function arbColumnDescriptor(index) {
	return fc.record({
		field_key: fc.constant(`col_${index}`),
		label: fc.string({ minLength: 1, maxLength: 30 }),
		default_width: fc.integer({ min: 1, max: 100 }),
		default_visible: fc.boolean(),
		default_sort_order: fc.constant(index),
	});
}

/**
 * Generates an array of 1–20 ColumnDescriptors with unique field_keys
 * and consecutive default_sort_order values.
 */
function arbDescriptorArray() {
	return fc.integer({ min: 1, max: 20 }).chain(function (len) {
		var arbs = [];
		for (var i = 0; i < len; i++) {
			arbs.push(arbColumnDescriptor(i));
		}
		return fc.tuple.apply(fc, arbs).map(function (arr) {
			return arr;
		});
	});
}

// ---------------------------------------------------------------------------
// Property 1: Default Initialization Preserves Descriptors
// ---------------------------------------------------------------------------

describe("Property 1: Default Initialization Preserves Descriptors", function () {
	/**
	 * **Validates: Requirements 1.1, 1.2**
	 *
	 * For any array of Column_Descriptors, initializing ColumnConfigManager
	 * with no saved settings produces a config with the same length as the
	 * input array, and each entry's visible, width, and sort_order match
	 * the corresponding descriptor's default_visible, default_width, and
	 * default_sort_order.
	 */
	it("config length equals descriptors length and defaults are preserved", function () {
		fc.assert(
			fc.property(arbDescriptorArray(), function (descriptors) {
				var mgr = new ColumnConfigManager(descriptors, null);
				var config = mgr.get_config();

				// Same length
				assert.equal(
					config.length,
					descriptors.length,
					"Config length must equal descriptors length"
				);

				// Build a lookup from descriptors by field_key for easy comparison
				var descMap = {};
				descriptors.forEach(function (d) {
					descMap[d.field_key] = d;
				});

				// Each config entry must match its descriptor defaults
				config.forEach(function (col) {
					var desc = descMap[col.field_key];
					assert.ok(
						desc,
						'Config entry field_key "' + col.field_key + '" must exist in descriptors'
					);
					assert.equal(
						col.visible,
						desc.default_visible,
						"visible must match default_visible for " + col.field_key
					);
					assert.equal(
						col.width,
						desc.default_width,
						"width must match default_width for " + col.field_key
					);
					assert.equal(
						col.sort_order,
						desc.default_sort_order,
						"sort_order must match default_sort_order for " + col.field_key
					);
					assert.equal(
						col.label,
						desc.label,
						"label must match descriptor label for " + col.field_key
					);
				});
			}),
			{ numRuns: 100 }
		);
	});

	it("config field_keys are exactly the descriptor field_keys (no extras, no missing)", function () {
		fc.assert(
			fc.property(arbDescriptorArray(), function (descriptors) {
				var mgr = new ColumnConfigManager(descriptors, null);
				var config = mgr.get_config();

				var configKeys = config
					.map(function (c) {
						return c.field_key;
					})
					.sort();
				var descKeys = descriptors
					.map(function (d) {
						return d.field_key;
					})
					.sort();

				assert.deepEqual(
					configKeys,
					descKeys,
					"Config field_keys must exactly match descriptor field_keys"
				);
			}),
			{ numRuns: 100 }
		);
	});

	it("config is sorted by sort_order ascending", function () {
		fc.assert(
			fc.property(arbDescriptorArray(), function (descriptors) {
				var mgr = new ColumnConfigManager(descriptors, null);
				var config = mgr.get_config();

				for (var i = 1; i < config.length; i++) {
					assert.ok(
						config[i].sort_order >= config[i - 1].sort_order,
						"Config must be sorted by sort_order"
					);
				}
			}),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 2: Saved Settings Override Defaults
// ---------------------------------------------------------------------------

describe("Property 2: Saved Settings Override Defaults", function () {
	/**
	 * **Validates: Requirements 1.3**
	 *
	 * For any array of Column_Descriptors and any valid saved User_Settings
	 * (matching field_keys), when ColumnConfigManager is initialized with both,
	 * the resulting Column_Configuration SHALL use the saved visible, width,
	 * and sort_order values for each column present in the saved settings.
	 */

	/**
	 * Given descriptors, generate saved settings for a random subset of their
	 * field_keys with valid overridden values, plus optional extra keys that
	 * should be ignored.
	 */
	function arbSavedSettingsForDescriptors(descriptors) {
		// For each descriptor, optionally generate a saved setting
		var perColumn = descriptors.map(function (d) {
			return fc.record({
				include: fc.boolean(),
				width: fc.integer({ min: 1, max: 100 }),
				visible: fc.boolean(),
				sort_order: fc.integer({ min: 0, max: 50 }),
			});
		});

		// Also generate 0–3 extra saved settings with keys not in descriptors
		var extraCount = fc.integer({ min: 0, max: 3 });

		return fc.tuple(fc.tuple.apply(fc, perColumn), extraCount).chain(function (args) {
			var overrides = args[0];
			var numExtra = args[1];

			var saved = [];
			overrides.forEach(function (ov, i) {
				if (ov.include) {
					saved.push({
						field_key: descriptors[i].field_key,
						label: descriptors[i].label,
						width: ov.width,
						visible: ov.visible,
						sort_order: ov.sort_order,
					});
				}
			});

			// Generate extra entries with keys that don't collide with descriptors
			var extras = [];
			for (var e = 0; e < numExtra; e++) {
				extras.push(
					fc.record({
						field_key: fc.constant("extra_key_" + e),
						label: fc.constant("Extra " + e),
						width: fc.integer({ min: 1, max: 100 }),
						visible: fc.boolean(),
						sort_order: fc.integer({ min: 0, max: 50 }),
					})
				);
			}

			if (extras.length === 0) {
				return fc.constant(saved);
			}
			return fc.tuple.apply(fc, extras).map(function (extraArr) {
				return saved.concat(extraArr);
			});
		});
	}

	it("matching saved settings override descriptor defaults", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbSavedSettingsForDescriptors(descriptors).map(function (saved) {
						return { descriptors: descriptors, saved: saved };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var saved = input.saved;

					var mgr = new ColumnConfigManager(descriptors, saved);
					var config = mgr.get_config();

					// Build lookups
					var savedMap = {};
					saved.forEach(function (s) {
						savedMap[s.field_key] = s;
					});

					var descMap = {};
					descriptors.forEach(function (d) {
						descMap[d.field_key] = d;
					});

					// Config length must equal descriptors length (extras ignored)
					assert.equal(
						config.length,
						descriptors.length,
						"Config length must equal descriptors length, extras in saved settings are ignored"
					);

					config.forEach(function (col) {
						var savedEntry = savedMap[col.field_key];
						var desc = descMap[col.field_key];
						assert.ok(desc, "Every config entry must correspond to a descriptor");

						if (savedEntry) {
							// Saved values must override defaults
							assert.equal(
								col.width,
								savedEntry.width,
								"width must use saved value for " + col.field_key
							);
							assert.equal(
								col.visible,
								savedEntry.visible,
								"visible must use saved value for " + col.field_key
							);
							assert.equal(
								col.sort_order,
								savedEntry.sort_order,
								"sort_order must use saved value for " + col.field_key
							);
						} else {
							// No saved entry — must fall back to descriptor defaults
							assert.equal(
								col.width,
								desc.default_width,
								"width must fall back to default for " + col.field_key
							);
							assert.equal(
								col.visible,
								desc.default_visible,
								"visible must fall back to default for " + col.field_key
							);
							assert.equal(
								col.sort_order,
								desc.default_sort_order,
								"sort_order must fall back to default for " + col.field_key
							);
						}
					});
				}
			),
			{ numRuns: 100 }
		);
	});

	it("extra keys in saved settings are ignored — config contains only descriptor field_keys", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbSavedSettingsForDescriptors(descriptors).map(function (saved) {
						return { descriptors: descriptors, saved: saved };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var saved = input.saved;

					var mgr = new ColumnConfigManager(descriptors, saved);
					var config = mgr.get_config();

					var configKeys = config
						.map(function (c) {
							return c.field_key;
						})
						.sort();
					var descKeys = descriptors
						.map(function (d) {
							return d.field_key;
						})
						.sort();

					assert.deepEqual(
						configKeys,
						descKeys,
						"Config field_keys must exactly match descriptor field_keys — no extras from saved settings"
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("descriptors without matching saved settings fall back to defaults", function () {
		fc.assert(
			fc.property(arbDescriptorArray(), function (descriptors) {
				// Provide saved settings for NONE of the descriptors — only extra keys
				var saved = [
					{
						field_key: "nonexistent_1",
						label: "X",
						width: 50,
						visible: false,
						sort_order: 99,
					},
					{
						field_key: "nonexistent_2",
						label: "Y",
						width: 25,
						visible: true,
						sort_order: 88,
					},
				];

				var mgr = new ColumnConfigManager(descriptors, saved);
				var config = mgr.get_config();

				assert.equal(
					config.length,
					descriptors.length,
					"Config length must equal descriptors length"
				);

				var descMap = {};
				descriptors.forEach(function (d) {
					descMap[d.field_key] = d;
				});

				config.forEach(function (col) {
					var desc = descMap[col.field_key];
					assert.equal(
						col.width,
						desc.default_width,
						"width must be default when no matching saved setting for " + col.field_key
					);
					assert.equal(
						col.visible,
						desc.default_visible,
						"visible must be default when no matching saved setting for " +
							col.field_key
					);
					assert.equal(
						col.sort_order,
						desc.default_sort_order,
						"sort_order must be default when no matching saved setting for " +
							col.field_key
					);
				});
			}),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 3: Visibility Toggle Correctness
// ---------------------------------------------------------------------------

describe("Property 3: Visibility Toggle Correctness", function () {
	/**
	 * **Validates: Requirements 2.2, 2.3**
	 *
	 * For any Column_Configuration and any column within it, setting visibility
	 * to false SHALL result in that column's visible field being false, and
	 * setting visibility to true SHALL result in that column's visible field
	 * being true. All other columns SHALL remain unchanged.
	 */
	it("toggling visibility changes only the targeted column", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
					var newVisible = fc.boolean();
					return fc.tuple(fc.constant(descriptors), idx, newVisible);
				}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];
					var newVisible = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);

					// Snapshot all columns BEFORE the toggle
					var configBefore = mgr.get_config();
					var beforeMap = {};
					configBefore.forEach(function (col) {
						beforeMap[col.field_key] = {
							field_key: col.field_key,
							label: col.label,
							width: col.width,
							visible: col.visible,
							sort_order: col.sort_order,
						};
					});

					// Pick the target column by sorted index
					var targetKey = configBefore[targetIdx].field_key;

					// Toggle visibility
					mgr.set_visibility(targetKey, newVisible);

					// Snapshot AFTER the toggle
					var configAfter = mgr.get_config();

					// Same number of columns
					assert.equal(
						configAfter.length,
						configBefore.length,
						"Column count must not change after visibility toggle"
					);

					configAfter.forEach(function (col) {
						var before = beforeMap[col.field_key];
						assert.ok(before, "Column " + col.field_key + " must still exist");

						if (col.field_key === targetKey) {
							// Target column: visible must match the new value
							assert.equal(
								col.visible,
								newVisible,
								"Target column visible must be " + newVisible
							);
						} else {
							// Other columns: everything must be unchanged
							assert.equal(
								col.visible,
								before.visible,
								"Non-target column " + col.field_key + " visible must be unchanged"
							);
						}

						// For ALL columns: non-visibility fields must be unchanged
						assert.equal(
							col.label,
							before.label,
							"label must be unchanged for " + col.field_key
						);
						assert.equal(
							col.width,
							before.width,
							"width must be unchanged for " + col.field_key
						);
						assert.equal(
							col.sort_order,
							before.sort_order,
							"sort_order must be unchanged for " + col.field_key
						);
					});
				}
			),
			{ numRuns: 100 }
		);
	});

	it("setting visibility to false makes the column hidden", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
					return fc.tuple(fc.constant(descriptors), idx);
				}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];

					var mgr = new ColumnConfigManager(descriptors, null);
					var targetKey = mgr.get_config()[targetIdx].field_key;

					mgr.set_visibility(targetKey, false);

					var col = mgr.get_config().find(function (c) {
						return c.field_key === targetKey;
					});
					assert.equal(
						col.visible,
						false,
						"Column must be hidden after set_visibility(key, false)"
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("setting visibility to true makes the column visible", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
					return fc.tuple(fc.constant(descriptors), idx);
				}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];

					var mgr = new ColumnConfigManager(descriptors, null);
					var targetKey = mgr.get_config()[targetIdx].field_key;

					mgr.set_visibility(targetKey, true);

					var col = mgr.get_config().find(function (c) {
						return c.field_key === targetKey;
					});
					assert.equal(
						col.visible,
						true,
						"Column must be visible after set_visibility(key, true)"
					);
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 4: Width Validation
// ---------------------------------------------------------------------------

describe("Property 4: Width Validation", function () {
	/**
	 * **Validates: Requirements 3.2, 3.3**
	 *
	 * For any Column_Configuration and any column within it, setting the width
	 * to a value in the range [1, 100] SHALL update that column's width field
	 * to the new value. Setting the width to any value outside [1, 100] SHALL
	 * be rejected and the column's width SHALL remain unchanged.
	 */
	it("set_width with value in [1, 100] updates the width and returns true", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
					var validWidth = fc.integer({ min: 1, max: 100 });
					return fc.tuple(fc.constant(descriptors), idx, validWidth);
				}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];
					var newWidth = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);
					var targetKey = mgr.get_config()[targetIdx].field_key;

					var result = mgr.set_width(targetKey, newWidth);

					assert.equal(
						result,
						true,
						"set_width must return true for valid width " + newWidth
					);

					var col = mgr.get_config().find(function (c) {
						return c.field_key === targetKey;
					});
					assert.equal(
						col.width,
						newWidth,
						"Column width must be updated to " + newWidth
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("set_width with value outside [1, 100] is rejected and width unchanged", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
					// Generate invalid widths: negative, zero, or > 100
					var invalidWidth = fc.oneof(
						fc.integer({ min: -1000, max: 0 }),
						fc.integer({ min: 101, max: 10000 })
					);
					return fc.tuple(fc.constant(descriptors), idx, invalidWidth);
				}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];
					var invalidWidth = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);
					var configBefore = mgr.get_config();
					var targetKey = configBefore[targetIdx].field_key;
					var widthBefore = configBefore[targetIdx].width;

					var result = mgr.set_width(targetKey, invalidWidth);

					assert.equal(
						result,
						false,
						"set_width must return false for invalid width " + invalidWidth
					);

					var col = mgr.get_config().find(function (c) {
						return c.field_key === targetKey;
					});
					assert.equal(
						col.width,
						widthBefore,
						"Column width must remain unchanged at " +
							widthBefore +
							" after rejected width " +
							invalidWidth
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("set_width with non-number types is rejected and width unchanged", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
					// Generate values whose typeof is not 'number'
					var nonNumber = fc.oneof(
						fc.string(),
						fc.constant(null),
						fc.constant(undefined),
						fc.constant(true),
						fc.constant(false),
						fc.constant({})
					);
					return fc.tuple(fc.constant(descriptors), idx, nonNumber);
				}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];
					var nonNumberValue = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);
					var configBefore = mgr.get_config();
					var targetKey = configBefore[targetIdx].field_key;
					var widthBefore = configBefore[targetIdx].width;

					var result = mgr.set_width(targetKey, nonNumberValue);

					assert.equal(result, false, "set_width must return false for non-number type");

					var col = mgr.get_config().find(function (c) {
						return c.field_key === targetKey;
					});
					assert.equal(
						col.width,
						widthBefore,
						"Column width must remain unchanged after rejected non-number type"
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("set_width with valid value does not affect other columns", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray()
					.filter(function (d) {
						return d.length >= 2;
					})
					.chain(function (descriptors) {
						var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
						var validWidth = fc.integer({ min: 1, max: 100 });
						return fc.tuple(fc.constant(descriptors), idx, validWidth);
					}),
				function (args) {
					var descriptors = args[0];
					var targetIdx = args[1];
					var newWidth = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);

					// Snapshot before
					var configBefore = mgr.get_config();
					var beforeMap = {};
					configBefore.forEach(function (col) {
						beforeMap[col.field_key] = {
							field_key: col.field_key,
							label: col.label,
							width: col.width,
							visible: col.visible,
							sort_order: col.sort_order,
						};
					});

					var targetKey = configBefore[targetIdx].field_key;

					mgr.set_width(targetKey, newWidth);

					var configAfter = mgr.get_config();

					assert.equal(
						configAfter.length,
						configBefore.length,
						"Column count must not change after set_width"
					);

					configAfter.forEach(function (col) {
						var before = beforeMap[col.field_key];
						if (col.field_key !== targetKey) {
							// Other columns must be completely unchanged
							assert.equal(
								col.width,
								before.width,
								"Non-target column " + col.field_key + " width must be unchanged"
							);
							assert.equal(
								col.visible,
								before.visible,
								"Non-target column " + col.field_key + " visible must be unchanged"
							);
							assert.equal(
								col.label,
								before.label,
								"Non-target column " + col.field_key + " label must be unchanged"
							);
							assert.equal(
								col.sort_order,
								before.sort_order,
								"Non-target column " +
									col.field_key +
									" sort_order must be unchanged"
							);
						}
					});
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 5: Width Total Invariant
// ---------------------------------------------------------------------------

describe("Property 5: Width Total Invariant", function () {
	/**
	 * **Validates: Requirements 3.4**
	 *
	 * For any Column_Configuration, the value returned by get_width_total()
	 * SHALL equal the arithmetic sum of the width fields of all columns
	 * where visible is true.
	 */

	/**
	 * Given descriptors, generate a list of mutations (visibility toggles
	 * and width changes) to apply after initialization.
	 */
	function arbMutations(maxColumns) {
		return fc.array(
			fc.oneof(
				fc.record({
					type: fc.constant("visibility"),
					colIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					value: fc.boolean(),
				}),
				fc.record({
					type: fc.constant("width"),
					colIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					value: fc.integer({ min: 1, max: 100 }),
				})
			),
			{ minLength: 0, maxLength: 30 }
		);
	}

	it("get_width_total() equals sum of visible column widths after random mutations", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var mutations = input.mutations;

					var mgr = new ColumnConfigManager(descriptors, null);

					// Apply random mutations
					mutations.forEach(function (mut) {
						var config = mgr.get_config();
						if (mut.colIndex >= config.length) return;
						var key = config[mut.colIndex].field_key;

						if (mut.type === "visibility") {
							mgr.set_visibility(key, mut.value);
						} else if (mut.type === "width") {
							mgr.set_width(key, mut.value);
						}
					});

					// Compute expected sum manually
					var config = mgr.get_config();
					var expectedTotal = 0;
					config.forEach(function (col) {
						if (col.visible) {
							expectedTotal += col.width;
						}
					});

					assert.equal(
						mgr.get_width_total(),
						expectedTotal,
						"get_width_total() must equal arithmetic sum of visible column widths"
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("get_width_total() equals 0 when all columns are hidden", function () {
		fc.assert(
			fc.property(arbDescriptorArray(), function (descriptors) {
				var mgr = new ColumnConfigManager(descriptors, null);

				// Hide all columns
				mgr.get_config().forEach(function (col) {
					mgr.set_visibility(col.field_key, false);
				});

				assert.equal(
					mgr.get_width_total(),
					0,
					"get_width_total() must be 0 when all columns are hidden"
				);
			}),
			{ numRuns: 100 }
		);
	});

	it("get_width_total() matches fresh initialization without mutations", function () {
		fc.assert(
			fc.property(arbDescriptorArray(), function (descriptors) {
				var mgr = new ColumnConfigManager(descriptors, null);

				var expectedTotal = 0;
				descriptors.forEach(function (d) {
					if (d.default_visible) {
						expectedTotal += d.default_width;
					}
				});

				assert.equal(
					mgr.get_width_total(),
					expectedTotal,
					"get_width_total() must equal sum of default widths for default-visible columns"
				);
			}),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 6: Reorder Preserves Columns
// ---------------------------------------------------------------------------

describe("Property 6: Reorder Preserves Columns", function () {
	/**
	 * **Validates: Requirements 4.2**
	 *
	 * For any Column_Configuration and any valid reorder operation (moving a
	 * column from index i to index j), the resulting configuration SHALL
	 * contain exactly the same set of columns (same field_keys), and the
	 * sort_order values SHALL form a consecutive sequence starting from 0
	 * with the moved column at position j.
	 */
	it("reorder preserves same set of field_keys with consecutive sort_order", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray()
					.filter(function (d) {
						return d.length >= 2;
					})
					.chain(function (descriptors) {
						var fromIdx = fc.integer({ min: 0, max: descriptors.length - 1 });
						var toIdx = fc.integer({ min: 0, max: descriptors.length - 1 });
						return fc.tuple(fc.constant(descriptors), fromIdx, toIdx);
					}),
				function (args) {
					var descriptors = args[0];
					var fromIndex = args[1];
					var toIndex = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);

					// Snapshot field_keys before reorder
					var keysBefore = mgr
						.get_config()
						.map(function (c) {
							return c.field_key;
						})
						.sort();

					// Identify the column being moved (by its field_key at from_index in sorted order)
					var movedKey = mgr.get_config()[fromIndex].field_key;

					// Perform reorder
					mgr.reorder(fromIndex, toIndex);

					var configAfter = mgr.get_config();

					// 1. Same set of field_keys
					var keysAfter = configAfter
						.map(function (c) {
							return c.field_key;
						})
						.sort();
					assert.deepEqual(
						keysAfter,
						keysBefore,
						"Reorder must preserve the same set of field_keys"
					);

					// 2. Consecutive sort_order starting from 0
					for (var i = 0; i < configAfter.length; i++) {
						assert.equal(
							configAfter[i].sort_order,
							i,
							"sort_order must be consecutive 0-based; expected " +
								i +
								" at position " +
								i +
								" but got " +
								configAfter[i].sort_order
						);
					}

					// 3. Moved column is at the target position
					assert.equal(
						configAfter[toIndex].field_key,
						movedKey,
						'Moved column "' +
							movedKey +
							'" must be at target position ' +
							toIndex +
							' but found "' +
							configAfter[toIndex].field_key +
							'"'
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("reorder to same position is a no-op", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray()
					.filter(function (d) {
						return d.length >= 2;
					})
					.chain(function (descriptors) {
						var idx = fc.integer({ min: 0, max: descriptors.length - 1 });
						return fc.tuple(fc.constant(descriptors), idx);
					}),
				function (args) {
					var descriptors = args[0];
					var idx = args[1];

					var mgr = new ColumnConfigManager(descriptors, null);

					// Snapshot before
					var configBefore = mgr.get_config();

					// Reorder to same position
					mgr.reorder(idx, idx);

					var configAfter = mgr.get_config();

					// Everything must be identical
					assert.equal(
						configAfter.length,
						configBefore.length,
						"Column count must not change on same-position reorder"
					);

					for (var i = 0; i < configAfter.length; i++) {
						assert.equal(
							configAfter[i].field_key,
							configBefore[i].field_key,
							"field_key at position " + i + " must be unchanged"
						);
						assert.equal(
							configAfter[i].sort_order,
							configBefore[i].sort_order,
							"sort_order at position " + i + " must be unchanged"
						);
						assert.equal(
							configAfter[i].width,
							configBefore[i].width,
							"width at position " + i + " must be unchanged"
						);
						assert.equal(
							configAfter[i].visible,
							configBefore[i].visible,
							"visible at position " + i + " must be unchanged"
						);
					}
				}
			),
			{ numRuns: 100 }
		);
	});

	it("reorder preserves column count and all non-order properties", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray()
					.filter(function (d) {
						return d.length >= 2;
					})
					.chain(function (descriptors) {
						var fromIdx = fc.integer({ min: 0, max: descriptors.length - 1 });
						var toIdx = fc.integer({ min: 0, max: descriptors.length - 1 });
						return fc.tuple(fc.constant(descriptors), fromIdx, toIdx);
					}),
				function (args) {
					var descriptors = args[0];
					var fromIndex = args[1];
					var toIndex = args[2];

					var mgr = new ColumnConfigManager(descriptors, null);

					// Snapshot non-order properties before reorder
					var propsBefore = {};
					mgr.get_config().forEach(function (col) {
						propsBefore[col.field_key] = {
							label: col.label,
							width: col.width,
							visible: col.visible,
						};
					});

					mgr.reorder(fromIndex, toIndex);

					var configAfter = mgr.get_config();

					// Same count
					assert.equal(
						configAfter.length,
						descriptors.length,
						"Column count must be preserved after reorder"
					);

					// Each column's label, width, visible must be unchanged
					configAfter.forEach(function (col) {
						var before = propsBefore[col.field_key];
						assert.ok(before, "Column " + col.field_key + " must still exist");
						assert.equal(
							col.label,
							before.label,
							"label must be unchanged for " + col.field_key
						);
						assert.equal(
							col.width,
							before.width,
							"width must be unchanged for " + col.field_key
						);
						assert.equal(
							col.visible,
							before.visible,
							"visible must be unchanged for " + col.field_key
						);
					});
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 7: Reset Restores Defaults (Round-Trip)
// ---------------------------------------------------------------------------

describe("Property 7: Reset Restores Defaults", function () {
	/**
	 * **Validates: Requirements 6.3**
	 *
	 * For any array of Column_Descriptors, if the ColumnConfigManager is
	 * initialized, then arbitrarily modified (visibility toggles, width
	 * changes, reorders), then reset(descriptors) is called, the resulting
	 * Column_Configuration SHALL be identical to a fresh initialization
	 * with no saved settings.
	 */

	/**
	 * Generates a list of arbitrary mutations (visibility toggles, width
	 * changes, and reorders) to apply to a ColumnConfigManager.
	 */
	function arbMutations(maxColumns) {
		return fc.array(
			fc.oneof(
				fc.record({
					type: fc.constant("visibility"),
					colIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					value: fc.boolean(),
				}),
				fc.record({
					type: fc.constant("width"),
					colIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					value: fc.integer({ min: 1, max: 100 }),
				}),
				fc.record({
					type: fc.constant("reorder"),
					fromIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					toIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
				})
			),
			{ minLength: 1, maxLength: 30 }
		);
	}

	/**
	 * Apply a list of mutations to a ColumnConfigManager instance.
	 */
	function applyMutations(mgr, mutations) {
		mutations.forEach(function (mut) {
			var config = mgr.get_config();
			if (mut.type === "visibility") {
				if (mut.colIndex < config.length) {
					mgr.set_visibility(config[mut.colIndex].field_key, mut.value);
				}
			} else if (mut.type === "width") {
				if (mut.colIndex < config.length) {
					mgr.set_width(config[mut.colIndex].field_key, mut.value);
				}
			} else if (mut.type === "reorder") {
				if (mut.fromIndex < config.length && mut.toIndex < config.length) {
					mgr.reorder(mut.fromIndex, mut.toIndex);
				}
			}
		});
	}

	it("reset(descriptors) after arbitrary modifications produces config identical to fresh init", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var mutations = input.mutations;

					// Create a manager and apply arbitrary modifications
					var mgr = new ColumnConfigManager(descriptors, null);
					applyMutations(mgr, mutations);

					// Reset to defaults
					mgr.reset(descriptors);

					// Create a fresh manager for comparison
					var freshMgr = new ColumnConfigManager(descriptors, null);

					var resetConfig = mgr.get_config();
					var freshConfig = freshMgr.get_config();

					// Same length
					assert.equal(
						resetConfig.length,
						freshConfig.length,
						"Reset config length must equal fresh config length"
					);

					// Each column must be identical
					for (var i = 0; i < resetConfig.length; i++) {
						assert.equal(
							resetConfig[i].field_key,
							freshConfig[i].field_key,
							"field_key at position " + i + " must match after reset"
						);
						assert.equal(
							resetConfig[i].label,
							freshConfig[i].label,
							"label at position " + i + " must match after reset"
						);
						assert.equal(
							resetConfig[i].width,
							freshConfig[i].width,
							"width at position " + i + " must match after reset"
						);
						assert.equal(
							resetConfig[i].visible,
							freshConfig[i].visible,
							"visible at position " + i + " must match after reset"
						);
						assert.equal(
							resetConfig[i].sort_order,
							freshConfig[i].sort_order,
							"sort_order at position " + i + " must match after reset"
						);
					}
				}
			),
			{ numRuns: 100 }
		);
	});

	it("reset(descriptors) restores get_width_total() to fresh initialization value", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var mutations = input.mutations;

					var mgr = new ColumnConfigManager(descriptors, null);
					var freshTotal = mgr.get_width_total();

					// Apply arbitrary modifications
					applyMutations(mgr, mutations);

					// Reset
					mgr.reset(descriptors);

					assert.equal(
						mgr.get_width_total(),
						freshTotal,
						"get_width_total() after reset must equal fresh initialization total"
					);
				}
			),
			{ numRuns: 100 }
		);
	});

	it("reset(descriptors) restores to_json() to fresh initialization value", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var mutations = input.mutations;

					var mgr = new ColumnConfigManager(descriptors, null);
					var freshJson = mgr.to_json();

					// Apply arbitrary modifications
					applyMutations(mgr, mutations);

					// Reset
					mgr.reset(descriptors);

					assert.equal(
						mgr.to_json(),
						freshJson,
						"to_json() after reset must equal fresh initialization JSON"
					);
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Property 9: Serialization Round-Trip
// ---------------------------------------------------------------------------

describe("Property 9: Serialization Round-Trip", function () {
	/**
	 * **Validates: Requirements 6.1, 6.2**
	 *
	 * For any valid Column_Configuration, serializing it with to_json() and
	 * then deserializing the result SHALL produce an equivalent
	 * Column_Configuration (same field_keys, visibility, widths, and
	 * sort_order).
	 */

	/**
	 * Generates a list of arbitrary mutations (visibility toggles, width
	 * changes, and reorders) to apply to a ColumnConfigManager.
	 */
	function arbMutations(maxColumns) {
		return fc.array(
			fc.oneof(
				fc.record({
					type: fc.constant("visibility"),
					colIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					value: fc.boolean(),
				}),
				fc.record({
					type: fc.constant("width"),
					colIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					value: fc.integer({ min: 1, max: 100 }),
				}),
				fc.record({
					type: fc.constant("reorder"),
					fromIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
					toIndex: fc.integer({ min: 0, max: Math.max(0, maxColumns - 1) }),
				})
			),
			{ minLength: 0, maxLength: 30 }
		);
	}

	/**
	 * Apply a list of mutations to a ColumnConfigManager instance.
	 */
	function applyMutations(mgr, mutations) {
		mutations.forEach(function (mut) {
			var config = mgr.get_config();
			if (mut.type === "visibility") {
				if (mut.colIndex < config.length) {
					mgr.set_visibility(config[mut.colIndex].field_key, mut.value);
				}
			} else if (mut.type === "width") {
				if (mut.colIndex < config.length) {
					mgr.set_width(config[mut.colIndex].field_key, mut.value);
				}
			} else if (mut.type === "reorder") {
				if (mut.fromIndex < config.length && mut.toIndex < config.length) {
					mgr.reorder(mut.fromIndex, mut.toIndex);
				}
			}
		});
	}

	it("to_json() then JSON.parse produces config equivalent to get_config()", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var mutations = input.mutations;

					// 1. Create manager and optionally apply mutations
					var mgr = new ColumnConfigManager(descriptors, null);
					applyMutations(mgr, mutations);

					// 2. Serialize
					var jsonStr = mgr.to_json();

					// 3. Parse back
					var parsed = JSON.parse(jsonStr);

					// 4. Get the live config for comparison
					var config = mgr.get_config();

					// 5. Verify equivalence
					assert.equal(
						parsed.length,
						config.length,
						"Parsed config length must equal get_config() length"
					);

					for (var i = 0; i < config.length; i++) {
						assert.equal(
							parsed[i].field_key,
							config[i].field_key,
							"field_key at position " + i + " must match"
						);
						assert.equal(
							parsed[i].visible,
							config[i].visible,
							"visible at position " + i + " must match"
						);
						assert.equal(
							parsed[i].width,
							config[i].width,
							"width at position " + i + " must match"
						);
						assert.equal(
							parsed[i].sort_order,
							config[i].sort_order,
							"sort_order at position " + i + " must match"
						);
						assert.equal(
							parsed[i].label,
							config[i].label,
							"label at position " + i + " must match"
						);
					}
				}
			),
			{ numRuns: 100 }
		);
	});

	it("to_json() output is valid JSON", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var mgr = new ColumnConfigManager(input.descriptors, null);
					applyMutations(mgr, input.mutations);

					var jsonStr = mgr.to_json();

					// Must not throw
					var parsed;
					assert.doesNotThrow(function () {
						parsed = JSON.parse(jsonStr);
					}, "to_json() must produce valid JSON");

					// Must be an array
					assert.ok(Array.isArray(parsed), "Parsed JSON must be an array");
				}
			),
			{ numRuns: 100 }
		);
	});

	it("parsed JSON can be used as saved_settings to reconstruct equivalent config", function () {
		fc.assert(
			fc.property(
				arbDescriptorArray().chain(function (descriptors) {
					return arbMutations(descriptors.length).map(function (mutations) {
						return { descriptors: descriptors, mutations: mutations };
					});
				}),
				function (input) {
					var descriptors = input.descriptors;
					var mutations = input.mutations;

					// Create manager, apply mutations
					var mgr = new ColumnConfigManager(descriptors, null);
					applyMutations(mgr, mutations);

					// Serialize and parse
					var jsonStr = mgr.to_json();
					var parsed = JSON.parse(jsonStr);

					// Use parsed as saved_settings for a new manager
					var mgr2 = new ColumnConfigManager(descriptors, parsed);

					var config1 = mgr.get_config();
					var config2 = mgr2.get_config();

					assert.equal(
						config2.length,
						config1.length,
						"Reconstructed config length must match original"
					);

					for (var i = 0; i < config1.length; i++) {
						assert.equal(
							config2[i].field_key,
							config1[i].field_key,
							"field_key at position " + i + " must match after round-trip"
						);
						assert.equal(
							config2[i].visible,
							config1[i].visible,
							"visible at position " + i + " must match after round-trip"
						);
						assert.equal(
							config2[i].width,
							config1[i].width,
							"width at position " + i + " must match after round-trip"
						);
						assert.equal(
							config2[i].sort_order,
							config1[i].sort_order,
							"sort_order at position " + i + " must match after round-trip"
						);
					}
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ---------------------------------------------------------------------------
// Unit Tests: PreviewPanel Rendering
// ---------------------------------------------------------------------------

const { PreviewPanel } = require("../../public/js/print_settings_dialog.js");

describe("PreviewPanel Rendering", function () {
	/**
	 * **Validates: Requirements 5.1, 5.3, 5.4, 8.3**
	 *
	 * Unit tests for PreviewPanel HTML table rendering, covering:
	 * - Correct column count matching visible columns
	 * - Column widths in style attributes
	 * - Max 5 sample rows in tbody
	 * - Placeholder row when no sample data
	 * - Empty cells for missing data fields
	 */

	/**
	 * Simple mock container with innerHTML property for Node.js testing.
	 */
	function mockContainer() {
		return { innerHTML: "" };
	}

	/**
	 * Count occurrences of a regex pattern in a string.
	 */
	function countMatches(str, regex) {
		var matches = str.match(regex);
		return matches ? matches.length : 0;
	}

	// --- Test: Correct number of <th> elements matching visible columns ---

	it("renders correct number of <th> elements matching visible columns", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "wbs_code", label: "WBS Code", width: 15, visible: true, sort_order: 0 },
			{ field_key: "title", label: "Title", width: 30, visible: true, sort_order: 1 },
			{ field_key: "unit", label: "Unit", width: 10, visible: true, sort_order: 2 },
		];

		panel.render(columns, [{ wbs_code: "1.0", title: "Foundation", unit: "m3" }]);

		var thCount = countMatches(container.innerHTML, /<th /g);
		assert.equal(thCount, 3, "Should render 3 <th> elements for 3 visible columns");
	});

	it("renders correct number of <th> for a single visible column", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "wbs_code", label: "WBS Code", width: 100, visible: true, sort_order: 0 },
		];

		panel.render(columns, []);

		var thCount = countMatches(container.innerHTML, /<th /g);
		assert.equal(thCount, 1, "Should render 1 <th> element for 1 visible column");
	});

	it("renders no <th> elements when visible_columns is empty", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		panel.render([], [{ wbs_code: "1.0" }]);

		var thCount = countMatches(container.innerHTML, /<th[\s>]/g);
		assert.equal(thCount, 0, "Should render 0 <th> elements for empty visible columns");
	});

	// --- Test: Column widths in style attributes ---

	it("renders column widths in <th> style attributes", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "wbs_code", label: "WBS Code", width: 15, visible: true, sort_order: 0 },
			{ field_key: "title", label: "Title", width: 40, visible: true, sort_order: 1 },
		];

		panel.render(columns, []);

		assert.ok(
			container.innerHTML.indexOf("width:15%") !== -1,
			"Should contain width:15% for first column"
		);
		assert.ok(
			container.innerHTML.indexOf("width:40%") !== -1,
			"Should contain width:40% for second column"
		);
	});

	// --- Test: Max 5 sample rows in tbody ---

	it("renders at most 5 <tr> in tbody when more than 5 sample rows provided", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "id", label: "ID", width: 50, visible: true, sort_order: 0 },
			{ field_key: "name", label: "Name", width: 50, visible: true, sort_order: 1 },
		];

		// Provide 8 sample rows
		var sampleData = [];
		for (var i = 0; i < 8; i++) {
			sampleData.push({ id: String(i + 1), name: "Item " + (i + 1) });
		}

		panel.render(columns, sampleData);

		// Extract tbody content and count <tr> inside it
		var tbodyMatch = container.innerHTML.match(/<tbody>([\s\S]*?)<\/tbody>/);
		assert.ok(tbodyMatch, "Should contain a <tbody> element");

		var tbodyTrCount = countMatches(tbodyMatch[1], /<tr>/g);
		assert.equal(tbodyTrCount, 5, "Should render at most 5 <tr> in tbody");
	});

	it("renders exactly 3 <tr> in tbody when 3 sample rows provided", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [{ field_key: "id", label: "ID", width: 100, visible: true, sort_order: 0 }];

		var sampleData = [{ id: "A" }, { id: "B" }, { id: "C" }];

		panel.render(columns, sampleData);

		var tbodyMatch = container.innerHTML.match(/<tbody>([\s\S]*?)<\/tbody>/);
		assert.ok(tbodyMatch, "Should contain a <tbody> element");

		var tbodyTrCount = countMatches(tbodyMatch[1], /<tr>/g);
		assert.equal(tbodyTrCount, 3, "Should render exactly 3 <tr> for 3 sample rows");
	});

	// --- Test: Placeholder row when no sample data ---

	it("renders placeholder row with column labels when no sample data provided", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "wbs_code", label: "WBS Code", width: 30, visible: true, sort_order: 0 },
			{ field_key: "title", label: "Title", width: 70, visible: true, sort_order: 1 },
		];

		panel.render(columns, []);

		var tbodyMatch = container.innerHTML.match(/<tbody>([\s\S]*?)<\/tbody>/);
		assert.ok(tbodyMatch, "Should contain a <tbody> element");

		// Should have exactly 1 placeholder row
		var tbodyTrCount = countMatches(tbodyMatch[1], /<tr>/g);
		assert.equal(tbodyTrCount, 1, "Should render 1 placeholder row when no sample data");

		// Placeholder cells should contain column labels
		assert.ok(
			tbodyMatch[1].indexOf("WBS Code") !== -1,
			'Placeholder row should contain "WBS Code" label'
		);
		assert.ok(
			tbodyMatch[1].indexOf("Title") !== -1,
			'Placeholder row should contain "Title" label'
		);
	});

	it("renders placeholder row when sample_data is undefined", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "qty", label: "Quantity", width: 100, visible: true, sort_order: 0 },
		];

		panel.render(columns, undefined);

		var tbodyMatch = container.innerHTML.match(/<tbody>([\s\S]*?)<\/tbody>/);
		assert.ok(tbodyMatch, "Should contain a <tbody> element");

		var tbodyTrCount = countMatches(tbodyMatch[1], /<tr>/g);
		assert.equal(
			tbodyTrCount,
			1,
			"Should render 1 placeholder row when sample_data is undefined"
		);

		assert.ok(
			tbodyMatch[1].indexOf("Quantity") !== -1,
			'Placeholder row should contain "Quantity" label'
		);
	});

	// --- Test: Empty cells for missing data fields ---

	it("renders empty <td> for columns whose field_key is not in sample data rows", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "wbs_code", label: "WBS Code", width: 30, visible: true, sort_order: 0 },
			{ field_key: "title", label: "Title", width: 40, visible: true, sort_order: 1 },
			{
				field_key: "missing_field",
				label: "Missing",
				width: 30,
				visible: true,
				sort_order: 2,
			},
		];

		var sampleData = [
			{ wbs_code: "1.0", title: "Foundation" },
			// Note: missing_field is not present in the data
		];

		panel.render(columns, sampleData);

		var tbodyMatch = container.innerHTML.match(/<tbody>([\s\S]*?)<\/tbody>/);
		assert.ok(tbodyMatch, "Should contain a <tbody> element");

		// Extract all <td> contents from the first row
		var tdMatches = tbodyMatch[1].match(/<td>(.*?)<\/td>/g);
		assert.ok(tdMatches, "Should contain <td> elements");
		assert.equal(tdMatches.length, 3, "Should have 3 <td> elements for 3 columns");

		// First two cells should have data, third should be empty
		assert.ok(tdMatches[0].indexOf("1.0") !== -1, 'First cell should contain "1.0"');
		assert.ok(
			tdMatches[1].indexOf("Foundation") !== -1,
			'Second cell should contain "Foundation"'
		);
		assert.equal(
			tdMatches[2],
			"<td></td>",
			"Third cell should be empty for missing field_key"
		);
	});

	it("renders all empty <td> when sample data row has no matching field_keys", function () {
		var container = mockContainer();
		var panel = new PreviewPanel(container);

		var columns = [
			{ field_key: "col_a", label: "A", width: 50, visible: true, sort_order: 0 },
			{ field_key: "col_b", label: "B", width: 50, visible: true, sort_order: 1 },
		];

		var sampleData = [{ unrelated_key: "value" }];

		panel.render(columns, sampleData);

		var tbodyMatch = container.innerHTML.match(/<tbody>([\s\S]*?)<\/tbody>/);
		assert.ok(tbodyMatch, "Should contain a <tbody> element");

		var tdMatches = tbodyMatch[1].match(/<td>(.*?)<\/td>/g);
		assert.equal(tdMatches.length, 2, "Should have 2 <td> elements");
		assert.equal(tdMatches[0], "<td></td>", "First cell should be empty");
		assert.equal(tdMatches[1], "<td></td>", "Second cell should be empty");
	});
});
