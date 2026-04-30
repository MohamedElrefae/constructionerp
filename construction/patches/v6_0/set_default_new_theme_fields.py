"""One-time migration: populate new fields from existing 15 fields.

For each Construction Theme record:
1. Read existing 15 fields
2. Compute defaults for 25+ new fields using mapping rules
3. Skip fields that already have values (preserve manual overrides)
4. Use update_modified=False to avoid triggering on_update
5. Use "#2076FF" as fallback accent if accent_primary is empty
"""

import frappe

FALLBACK_ACCENT = "#2076FF"

# Mapping: new_field -> (source_field, default_value_if_source_empty)
DIRECT_COPY_MAP = {
	"primary_btn_bg": ("accent_primary", FALLBACK_ACCENT),
	"primary_btn_text": (None, "#FFFFFF"),
	"primary_btn_hover_text": (None, "#FFFFFF"),
	"secondary_btn_bg": ("surface_bg", None),
	"secondary_btn_text": ("text_primary", None),
	"secondary_btn_hover_text": ("text_primary", None),
	"table_header_bg": ("sidebar_bg", None),
	"table_header_text": ("text_primary", None),
	"table_body_bg": ("body_bg", None),
	"table_body_text": ("text_primary", None),
	"input_bg": ("surface_bg", None),
	"input_border": ("border_color", None),
	"input_text": ("text_primary", None),
	"input_label_color": ("text_secondary", None),
	"navbar_text_color": ("text_primary", None),
}


def darken_hex(hex_color, factor=0.1):
	if not hex_color or not hex_color.startswith("#"):
		return hex_color
	h = hex_color.lstrip("#")
	if len(h) == 3:
		h = "".join(c * 2 for c in h)
	r = int(int(h[0:2], 16) * (1 - factor))
	g = int(int(h[2:4], 16) * (1 - factor))
	b = int(int(h[4:6], 16) * (1 - factor))
	return f"#{r:02x}{g:02x}{b:02x}"


def lighten_hex(hex_color, factor=0.1):
	if not hex_color or not hex_color.startswith("#"):
		return hex_color
	h = hex_color.lstrip("#")
	if len(h) == 3:
		h = "".join(c * 2 for c in h)
	r = int(int(h[0:2], 16) + (255 - int(h[0:2], 16)) * factor)
	g = int(int(h[2:4], 16) + (255 - int(h[2:4], 16)) * factor)
	b = int(int(h[4:6], 16) + (255 - int(h[4:6], 16)) * factor)
	return f"#{r:02x}{g:02x}{b:02x}"


def execute():
	if not frappe.db.table_exists("tabConstruction Theme"):
		return

	themes = frappe.get_all(
		"Construction Theme",
		fields=[
			"name",
			"accent_primary",
			"surface_bg",
			"text_primary",
			"text_secondary",
			"sidebar_bg",
			"body_bg",
			"border_color",
		],
	)

	for theme_data in themes:
		updates = {}
		accent = theme_data.accent_primary or FALLBACK_ACCENT
		body_bg = theme_data.body_bg or ""
		is_dark = body_bg.startswith("#1")

		for new_field, (source_field, default) in DIRECT_COPY_MAP.items():
			current = frappe.db.get_value("Construction Theme", theme_data.name, new_field)
			if current:
				continue  # preserve manual overrides
			if source_field:
				value = theme_data.get(source_field) or default
			else:
				value = default
			if value:
				updates[new_field] = value

		# Compute hover colors
		btn_bg = updates.get("primary_btn_bg") or accent
		if not frappe.db.get_value("Construction Theme", theme_data.name, "primary_btn_hover_bg"):
			updates["primary_btn_hover_bg"] = lighten_hex(btn_bg) if is_dark else darken_hex(btn_bg)

		sec_bg = updates.get("secondary_btn_bg") or theme_data.surface_bg
		if sec_bg and not frappe.db.get_value(
			"Construction Theme", theme_data.name, "secondary_btn_hover_bg"
		):
			updates["secondary_btn_hover_bg"] = lighten_hex(sec_bg) if is_dark else darken_hex(sec_bg)

		if updates:
			frappe.db.set_value("Construction Theme", theme_data.name, updates, update_modified=False)

	frappe.db.commit()
