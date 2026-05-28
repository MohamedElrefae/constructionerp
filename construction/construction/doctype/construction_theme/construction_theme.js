// Copyright (c) 2026, Construction and contributors
// For license information, please see license.txt

frappe.ui.form.on("Construction Theme", {
	refresh: function (frm) {
		// Add preview button
		frm.add_custom_button(
			__("Preview Theme"),
			function () {
				frm.preview_theme();
			},
			__("Actions")
		);

		// Add contrast check indicator
		if (frm.doc.contrast_ratio) {
			var indicator = frm.doc.contrast_ratio >= 4.5 ? "green" : "orange";
			var badge = `<span class="indicator-pill ${indicator}" style="margin-left: 10px;">
                Contrast: ${frm.doc.contrast_ratio.toFixed(1)}:1
            </span>`;
			frm.page.set_title_sub(badge);
		}

		// Update preview colors display
		frm.update_preview_colors();
	},

	validate: function (frm) {
		// Client-side validation before save
		var accent = frm.doc.accent_primary;
		var surface = frm.doc.surface_bg;

		if (accent && surface) {
			var contrast = frm.calculate_contrast(accent, surface);
			if (contrast < 4.5) {
				frappe.show_alert({
					message: __("Warning: Contrast ratio is below WCAG AA (4.5:1)"),
					indicator: "orange",
				});
			}
		}
	},

	after_save: function (frm) {
		// Clear client CSS cache when theme is saved (force fresh load)
		if (window.ModernThemeLoader && window.ModernThemeLoader._cssCache) {
			window.ModernThemeLoader._cssCache = {};
		}
		// Clear localStorage cache entries
		var prefix = "construction_theme_css:";
		var keysToRemove = [];
		for (var i = 0; i < localStorage.length; i++) {
			var key = localStorage.key(i);
			if (key && key.indexOf(prefix) === 0) {
				keysToRemove.push(key);
			}
		}
		keysToRemove.forEach(function (k) {
			localStorage.removeItem(k);
		});

		// Reload page to apply new theme
		setTimeout(function () {
			location.reload();
		}, 1000);
	},

	// Auto-update preview when colors change
	accent_primary: function (frm) {
		frm.debounce_preview_update();
	},
	navbar_bg: function (frm) {
		frm.debounce_preview_update();
	},
	sidebar_bg: function (frm) {
		frm.debounce_preview_update();
	},
	surface_bg: function (frm) {
		frm.debounce_preview_update();
	},
	body_bg: function (frm) {
		frm.debounce_preview_update();
	},
	text_primary: function (frm) {
		frm.debounce_preview_update();
	},
});

// Extend form with helper methods
frappe.ui.form.on("Construction Theme", {
	onload: function (frm) {
		// Add preview method to form
		frm.preview_theme = function () {
			var color_fields = {
				theme_name: frm.doc.theme_name || "Preview",
				theme_type: frm.doc.theme_type || "Custom Light",
				accent_primary: frm.doc.accent_primary,
				accent_primary_hover: frm.doc.accent_primary_hover,
				accent_secondary: frm.doc.accent_secondary,
				navbar_bg: frm.doc.navbar_bg,
				sidebar_bg: frm.doc.sidebar_bg,
				surface_bg: frm.doc.surface_bg,
				body_bg: frm.doc.body_bg,
				text_primary: frm.doc.text_primary,
				text_secondary: frm.doc.text_secondary,
				border_color: frm.doc.border_color,
				success_color: frm.doc.success_color,
				warning_color: frm.doc.warning_color,
				error_color: frm.doc.error_color,
				custom_css: frm.doc.custom_css,
			};

			// Call preview API
			frappe.call({
				method: "construction.api.theme_api.preview_theme",
				args: {
					temporary: true,
					color_fields: color_fields,
				},
				callback: function (r) {
					if (r.message && r.message.css) {
						frm.show_preview_dialog(r.message.css);
					} else if (r.message && r.message.error) {
						frappe.msgprint(__("Error generating preview: ") + r.message.error);
					}
				},
				error: function () {
					frappe.msgprint(__("Failed to generate theme preview"));
				},
			});
		};

		// Show preview in dialog
		frm.show_preview_dialog = function (css) {
			var d = new frappe.ui.Dialog({
				title: __("Theme Preview"),
				size: "large",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "preview_html",
						options: `
                            <div id="theme-preview-container" style="
                                border: 1px solid var(--border-color);
                                border-radius: 8px;
                                overflow: hidden;
                                min-height: 300px;
                            ">
                                <iframe id="theme-preview-frame" style="
                                    width: 100%;
                                    height: 400px;
                                    border: none;
                                "></iframe>
                            </div>
                            <div style="margin-top: 10px; color: var(--text-muted);">
                                ${__(
									"Preview shows approximate rendering. Save and apply theme to see full effect."
								)}
                            </div>
                        `,
					},
				],
				primary_action_label: __("Close"),
				primary_action: function () {
					d.hide();
				},
			});

			d.show();

			// Inject CSS into iframe after dialog opens
			setTimeout(function () {
				var iframe = document.getElementById("theme-preview-frame");
				if (iframe) {
					var doc = iframe.contentDocument || iframe.contentWindow.document;
					doc.open();
					doc.write(`
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <style>${css}</style>
                            <style>
                                body {
                                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                    padding: 20px;
                                    background: var(--body-bg, #f5f5f5);
                                    color: var(--text-primary, #333);
                                }
                                .preview-navbar {
                                    background: var(--navbar-bg, #333);
                                    padding: 10px 20px;
                                    margin-bottom: 20px;
                                    border-radius: 8px;
                                    color: var(--text-primary, #fff);
                                }
                                .preview-sidebar {
                                    background: var(--sidebar-bg, #f0f0f0);
                                    padding: 15px;
                                    width: 200px;
                                    float: left;
                                    margin-right: 20px;
                                    border-radius: 8px;
                                    min-height: 200px;
                                }
                                .preview-content {
                                    background: var(--surface-bg, #fff);
                                    padding: 20px;
                                    border-radius: 8px;
                                    overflow: hidden;
                                    border: 1px solid var(--border-color, #ddd);
                                }
                                .preview-button {
                                    background: var(--accent-primary, #007bff);
                                    color: #fff;
                                    padding: 8px 16px;
                                    border: none;
                                    border-radius: 4px;
                                    margin: 5px;
                                    cursor: pointer;
                                }
                                .preview-button:hover {
                                    background: var(--accent-primary-hover, #0056b3);
                                }
                                .preview-button.secondary {
                                    background: transparent;
                                    color: var(--accent-primary, #007bff);
                                    border: 1px solid var(--accent-primary, #007bff);
                                }
                                .clear { clear: both; }
                            </style>
                        </head>
                        <body>
                            <div class="preview-navbar">
                                <strong>Navbar Preview</strong>
                            </div>
                            <div class="preview-sidebar">
                                <div>Sidebar Item 1</div>
                                <div style="color: var(--accent-primary);">Active Item</div>
                            </div>
                            <div class="preview-content">
                                <h3>Content Area Preview</h3>
                                <p style="color: var(--text-secondary);">Secondary text example</p>
                                <button class="preview-button">Primary Button</button>
                                <button class="preview-button secondary">Secondary</button>
                            </div>
                            <div class="clear"></div>
                        </body>
                        </html>
                    `);
					doc.close();
				}
			}, 100);
		};

		// Calculate contrast ratio
		frm.calculate_contrast = function (color1, color2) {
			function luminance(hex) {
				hex = hex.replace("#", "");
				if (hex.length === 3) {
					hex = hex
						.split("")
						.map(function (c) {
							return c + c;
						})
						.join("");
				}

				var r = parseInt(hex.substr(0, 2), 16) / 255;
				var g = parseInt(hex.substr(2, 2), 16) / 255;
				var b = parseInt(hex.substr(4, 2), 16) / 255;

				r = r <= 0.03928 ? r / 12.92 : Math.pow((r + 0.055) / 1.055, 2.4);
				g = g <= 0.03928 ? g / 12.92 : Math.pow((g + 0.055) / 1.055, 2.4);
				b = b <= 0.03928 ? b / 12.92 : Math.pow((b + 0.055) / 1.055, 2.4);

				return 0.2126 * r + 0.7152 * g + 0.0722 * b;
			}

			var l1 = luminance(color1);
			var l2 = luminance(color2);
			var lighter = Math.max(l1, l2);
			var darker = Math.min(l1, l2);

			return (lighter + 0.05) / (darker + 0.05);
		};

		// Debounced preview update
		var debounceTimer;
		frm.debounce_preview_update = function () {
			clearTimeout(debounceTimer);
			debounceTimer = setTimeout(function () {
				frm.update_preview_colors();
				frm.update_live_preview();
			}, 300); // Phase 2: 300ms debounce
		};

		// Update preview colors display
		frm.update_preview_colors = function () {
			var colors = [
				frm.doc.navbar_bg,
				frm.doc.accent_primary,
				frm.doc.surface_bg,
				frm.doc.text_primary,
				frm.doc.border_color || frm.doc.accent_secondary || frm.doc.accent_primary,
			];

			// Show color swatches in sidebar
			var swatches = colors
				.map(function (c) {
					return (
						'<span style="display:inline-block;width:20px;height:20px;background:' +
						c +
						';border-radius:4px;margin-right:4px;border:1px solid #ddd;"></span>'
					);
				})
				.join("");

			// Add to page if not exists
			var existing = frm.page.wrapper.find(".theme-preview-swatches");
			if (existing.length) {
				existing.html(swatches);
			} else {
				frm.page.wrapper
					.find(".page-head .page-title")
					.append(
						'<span class="theme-preview-swatches" style="margin-left:15px;vertical-align:middle;">' +
							swatches +
							"</span>"
					);
			}
		};

		// Live preview in sidebar - real-time components
		frm.update_live_preview = function () {
			var previewContainer = frm.page.wrapper.find(".live-preview-section");
			if (!previewContainer.length) return;

			// Generate live preview HTML with current colors
			var css = frm.generate_inline_css();
			previewContainer.html(
				'<div style="padding:15px;background:var(--surface-bg, #fff);border-radius:8px;border:1px solid var(--border-color);">' +
					"<style>" +
					css +
					"</style>" +
					// Navbar
					'<div class="live-navbar" style="background:var(--navbar-bg);color:var(--text-primary);padding:12px 16px;border-radius:8px 8px 0 0;margin:-15px -15px 15px -15px;">' +
					"<strong>Navbar</strong>" +
					"</div>" +
					// Buttons
					'<div style="margin-bottom:15px;">' +
					'<button class="btn-preview-primary" style="background:var(--accent-primary);color:#fff;padding:8px 16px;border:none;border-radius:6px;margin-right:8px;cursor:pointer;">Primary</button>' +
					'<button class="btn-preview-secondary" style="background:transparent;color:var(--accent-primary);padding:8px 16px;border:1px solid var(--accent-primary);border-radius:6px;margin-right:8px;cursor:pointer;">Secondary</button>' +
					'<button class="btn-preview-default" style="background:var(--surface-bg);color:var(--text-primary);padding:8px 16px;border:1px solid var(--border-color);border-radius:6px;cursor:pointer;">Default</button>' +
					"</div>" +
					// Inputs
					'<div style="margin-bottom:15px;">' +
					'<input type="text" placeholder="Input field..." style="display:block;width:100%;padding:8px 12px;margin-bottom:8px;background:var(--field-bg);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;">' +
					'<select style="display:block;width:100%;padding:8px 12px;background:var(--field-bg);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;"><option>Select option</option></select>' +
					"</div>" +
					// Alerts
					'<div style="margin-bottom:15px;">' +
					'<div style="background:rgba(16,185,129,0.15);color:#10B981;padding:10px;border-radius:6px;margin-bottom:8px;">✓ Success alert</div>' +
					'<div style="background:rgba(245,158,11,0.15);color:#F59E0B;padding:10px;border-radius:6px;margin-bottom:8px;">⚠ Warning alert</div>' +
					'<div style="background:rgba(239,68,68,0.15);color:#EF4444;padding:10px;border-radius:6px;">✕ Error alert</div>' +
					"</div>" +
					"</div>"
			);
		};

		// Generate inline CSS for live preview
		frm.generate_inline_css = function () {
			return [
				".live-navbar { background: " +
					(frm.doc.navbar_bg || "#fff") +
					"; color: " +
					(frm.doc.text_primary || "#333") +
					"; }",
				".btn-preview-primary { background: " +
					(frm.doc.accent_primary || "#2563EB") +
					" !important; color: #fff !important; }",
				".btn-preview-primary:hover { background: " +
					(frm.doc.accent_primary_hover || "#1D4ED8") +
					" !important; }",
				".btn-preview-secondary { color: " +
					(frm.doc.accent_primary || "#2563EB") +
					" !important; border-color: " +
					(frm.doc.accent_primary || "#2563EB") +
					" !important; }",
				".btn-preview-default { background: " +
					(frm.doc.surface_bg || "#fff") +
					" !important; color: " +
					(frm.doc.text_primary || "#333") +
					" !important; }",
				".live-preview-section input, .live-preview-section select { background: " +
					(frm.doc.input_bg || "#fff") +
					" !important; color: " +
					(frm.doc.input_text || "#333") +
					" !important; border-color: " +
					(frm.doc.input_border || "#ddd") +
					" !important; }",
			].join("\n");
		};

		// Toggle live preview section
		frm.toggle_live_preview = function (show) {
			var container = frm.page.wrapper.find(".live-preview-section");
			if (show) {
				if (!container.length) {
					container = $(
						'<div class="live-preview-section" style="margin-top:20px;padding:15px;background:var(--bg-light);border-radius:8px;"></div>'
					);
					frm.page.body.append(container);
				}
				container.show();
				frm.update_live_preview();
			} else if (container.length) {
				container.hide();
			}
		};

		// Initialize live preview toggle button
		if (!frm.page.wrapper.find(".toggle-live-preview").length) {
			frm.page.add_action_item(
				__("Live Preview"),
				function () {
					frm.live_preview_visible = !frm.live_preview_visible;
					frm.toggle_live_preview(frm.live_preview_visible);
				},
				{ icon: "eye" }
			);
		}
	},
});
