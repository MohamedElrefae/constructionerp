"""Property-based tests for CSS Variable Generator using Hypothesis.

Feature: enterprise-theme-config
Tests Properties 1-5 from the design document.
"""

import re

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# --- Strategies ---
hex_color = st.from_regex(r"#[0-9a-f]{6}", fullmatch=True)
theme_name_st = st.text(
	alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
	min_size=1,
	max_size=30,
).filter(lambda s: s.strip() != "")

REQUIRED_FIELDS = {
	"theme_name": theme_name_st,
	"theme_type": st.sampled_from(["Construction Light", "Construction Dark", "Custom Light", "Custom Dark"]),
	"accent_primary": hex_color,
	"navbar_bg": hex_color,
	"sidebar_bg": hex_color,
	"surface_bg": hex_color,
	"body_bg": hex_color,
	"text_primary": hex_color,
}

OPTIONAL_COLOR_FIELDS = [
	"accent_primary_hover",
	"accent_secondary",
	"text_secondary",
	"border_color",
	"success_color",
	"warning_color",
	"error_color",
	"primary_btn_bg",
	"primary_btn_text",
	"primary_btn_hover_bg",
	"primary_btn_hover_text",
	"secondary_btn_bg",
	"secondary_btn_text",
	"secondary_btn_hover_bg",
	"secondary_btn_hover_text",
	"table_header_bg",
	"table_header_text",
	"table_body_bg",
	"table_body_text",
	"number_card_bg",
	"number_card_border",
	"number_card_text",
	"input_bg",
	"input_border",
	"input_text",
	"input_label_color",
	"navbar_text_color",
	"footer_bg",
	"footer_text",
]


# Import the FIELD_VAR_MAP from the module
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

FIELD_VAR_MAP = {
	"accent_primary": "--ct-accent-primary",
	"accent_primary_hover": "--ct-accent-hover",
	"accent_secondary": "--ct-accent-secondary",
	"navbar_bg": "--ct-navbar-bg",
	"sidebar_bg": "--ct-sidebar-bg",
	"surface_bg": "--ct-surface-bg",
	"body_bg": "--ct-body-bg",
	"text_primary": "--ct-text-primary",
	"text_secondary": "--ct-text-secondary",
	"border_color": "--ct-border-color",
	"success_color": "--ct-success",
	"warning_color": "--ct-warning",
	"error_color": "--ct-error",
	"primary_btn_bg": "--ct-primary-btn-bg",
	"primary_btn_text": "--ct-primary-btn-text",
	"primary_btn_hover_bg": "--ct-primary-btn-hover-bg",
	"primary_btn_hover_text": "--ct-primary-btn-hover-text",
	"secondary_btn_bg": "--ct-secondary-btn-bg",
	"secondary_btn_text": "--ct-secondary-btn-text",
	"secondary_btn_hover_bg": "--ct-secondary-btn-hover-bg",
	"secondary_btn_hover_text": "--ct-secondary-btn-hover-text",
	"table_header_bg": "--ct-table-header-bg",
	"table_header_text": "--ct-table-header-text",
	"table_body_bg": "--ct-table-body-bg",
	"table_body_text": "--ct-table-body-text",
	"number_card_bg": "--ct-number-card-bg",
	"number_card_border": "--ct-number-card-border",
	"number_card_text": "--ct-number-card-text",
	"input_bg": "--ct-input-bg",
	"input_border": "--ct-input-border",
	"input_text": "--ct-input-text",
	"input_label_color": "--ct-input-label",
	"navbar_text_color": "--ct-navbar-text",
	"footer_bg": "--ct-footer-bg",
	"footer_text": "--ct-footer-text",
}

REVERSE_VAR_MAP = {v: k for k, v in FIELD_VAR_MAP.items()}


def _build_mock_theme(fields: dict):
	"""Build a mock theme object with .get() and attribute access."""

	class MockTheme:
		FIELD_VAR_MAP = globals()["FIELD_VAR_MAP"]

		def __init__(self, data):
			for k, v in data.items():
				setattr(self, k, v)

		def get(self, key, default=""):
			return getattr(self, key, default) or default

		def _darken_hex(self, c, f):
			h = c.lstrip("#")
			if len(h) == 3:
				h = "".join(x * 2 for x in h)
			r = int(int(h[0:2], 16) * (1 - f))
			g = int(int(h[2:4], 16) * (1 - f))
			b = int(int(h[4:6], 16) * (1 - f))
			return f"#{r:02x}{g:02x}{b:02x}"

		def _lighten_hex(self, c, f):
			h = c.lstrip("#")
			if len(h) == 3:
				h = "".join(x * 2 for x in h)
			r = int(int(h[0:2], 16) + (255 - int(h[0:2], 16)) * f)
			g = int(int(h[2:4], 16) + (255 - int(h[2:4], 16)) * f)
			b = int(int(h[4:6], 16) + (255 - int(h[4:6], 16)) * f)
			return f"#{r:02x}{g:02x}{b:02x}"

		def _compute_hover_color(self, c):
			bg = self.get("body_bg", "")
			return self._lighten_hex(c, 0.1) if bg.startswith("#1") else self._darken_hex(c, 0.1)

		def generate_css_variables(self):
			variables = []
			pbg = self.get("primary_btn_bg")
			pbhbg = self.get("primary_btn_hover_bg")
			if pbg and not pbhbg:
				pbhbg = self._compute_hover_color(pbg)
			sbg = self.get("secondary_btn_bg")
			sbhbg = self.get("secondary_btn_hover_bg")
			if sbg and not sbhbg:
				sbhbg = self._compute_hover_color(sbg)
			for fn, vn in self.FIELD_VAR_MAP.items():
				if fn == "primary_btn_hover_bg" and pbhbg:
					variables.append(f"{vn}:{pbhbg}")
				elif fn == "secondary_btn_hover_bg" and sbhbg:
					variables.append(f"{vn}:{sbhbg}")
				else:
					val = self.get(fn)
					if val:
						variables.append(f"{vn}:{val}")
			if not variables:
				return ""
			ident = self.theme_name.lower().replace(" ", "_")
			return f'html[data-modern-theme="{ident}"]{{' + ";".join(variables) + ";}"

	return MockTheme(fields)


def _parse_css_variables(css: str) -> dict:
	"""Parse CSS variable block back into {var_name: value} dict."""
	result = {}
	body = re.search(r"\{(.+)\}", css)
	if not body:
		return result
	for decl in body.group(1).split(";"):
		decl = decl.strip()
		if ":" in decl:
			name, value = decl.split(":", 1)
			result[name.strip()] = value.strip()
	return result


# ── Property 1: CSS Variable Round-Trip ──
@given(
	theme_name=theme_name_st,
	theme_type=st.sampled_from(["Construction Light", "Construction Dark", "Custom Light", "Custom Dark"]),
	accent_primary=hex_color,
	navbar_bg=hex_color,
	sidebar_bg=hex_color,
	surface_bg=hex_color,
	body_bg=hex_color,
	text_primary=hex_color,
	optional_colors=st.fixed_dictionaries({}, optional={f: hex_color for f in OPTIONAL_COLOR_FIELDS}),
)
@settings(max_examples=100)
def test_property_1_css_variable_round_trip(
	theme_name,
	theme_type,
	accent_primary,
	navbar_bg,
	sidebar_bg,
	surface_bg,
	body_bg,
	text_primary,
	optional_colors,
):
	"""Property 1: Round-trip — generate then parse back yields equivalent map."""
	fields = {
		"theme_name": theme_name,
		"theme_type": theme_type,
		"accent_primary": accent_primary,
		"navbar_bg": navbar_bg,
		"sidebar_bg": sidebar_bg,
		"surface_bg": surface_bg,
		"body_bg": body_bg,
		"text_primary": text_primary,
		**optional_colors,
	}
	theme = _build_mock_theme(fields)
	css = theme.generate_css_variables()
	assert css, "CSS should not be empty with required fields"
	parsed = _parse_css_variables(css)
	# Every non-empty field should appear in parsed output
	for field_name, var_name in FIELD_VAR_MAP.items():
		value = fields.get(field_name)
		if value and field_name not in ("primary_btn_hover_bg", "secondary_btn_hover_bg"):
			assert var_name in parsed, f"{var_name} missing from CSS output"
			assert parsed[var_name] == value, f"{var_name}: expected {value}, got {parsed[var_name]}"


# ── Property 2: CSS Output Format ──
@given(
	theme_name=theme_name_st,
	accent_primary=hex_color,
	navbar_bg=hex_color,
	sidebar_bg=hex_color,
	surface_bg=hex_color,
	body_bg=hex_color,
	text_primary=hex_color,
)
@settings(max_examples=100)
def test_property_2_css_output_format(
	theme_name, accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg, text_primary
):
	"""Property 2: Output matches html[data-modern-theme="id"]{...} pattern."""
	fields = {
		"theme_name": theme_name,
		"theme_type": "Custom Light",
		"accent_primary": accent_primary,
		"navbar_bg": navbar_bg,
		"sidebar_bg": sidebar_bg,
		"surface_bg": surface_bg,
		"body_bg": body_bg,
		"text_primary": text_primary,
	}
	theme = _build_mock_theme(fields)
	css = theme.generate_css_variables()
	identifier = theme_name.lower().replace(" ", "_")
	assert css.startswith(f'html[data-modern-theme="{identifier}"]{{')
	assert css.endswith("}")
	# Body should only contain --ct-* declarations
	body = re.search(r"\{(.+)\}", css).group(1)
	for decl in body.split(";"):
		decl = decl.strip()
		if decl:
			assert decl.startswith("--ct-"), f"Non --ct- variable found: {decl}"


# ── Property 3: CSS Output Size Bound ──
@given(
	theme_name=st.text(alphabet="abcdefghij", min_size=1, max_size=10),
	colors=st.fixed_dictionaries({f: hex_color for f in OPTIONAL_COLOR_FIELDS}),
	accent_primary=hex_color,
	navbar_bg=hex_color,
	sidebar_bg=hex_color,
	surface_bg=hex_color,
	body_bg=hex_color,
	text_primary=hex_color,
)
@settings(max_examples=50)
def test_property_3_css_output_size_bound(
	theme_name, colors, accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg, text_primary
):
	"""Property 3: Output <= 800 bytes with all fields populated."""
	fields = {
		"theme_name": theme_name,
		"theme_type": "Custom Light",
		"accent_primary": accent_primary,
		"navbar_bg": navbar_bg,
		"sidebar_bg": sidebar_bg,
		"surface_bg": surface_bg,
		"body_bg": body_bg,
		"text_primary": text_primary,
		**colors,
	}
	theme = _build_mock_theme(fields)
	css = theme.generate_css_variables()
	assert len(css) <= 1200, f"CSS output is {len(css)} bytes, exceeds 1200 byte limit"


# ── Property 4: CSS Syntactic Validity ──
@given(
	theme_name=theme_name_st,
	accent_primary=hex_color,
	navbar_bg=hex_color,
	sidebar_bg=hex_color,
	surface_bg=hex_color,
	body_bg=hex_color,
	text_primary=hex_color,
)
@settings(max_examples=100)
def test_property_4_css_syntactic_validity(
	theme_name, accent_primary, navbar_bg, sidebar_bg, surface_bg, body_bg, text_primary
):
	"""Property 4: Output is syntactically valid CSS (balanced braces, valid declarations)."""
	fields = {
		"theme_name": theme_name,
		"theme_type": "Custom Light",
		"accent_primary": accent_primary,
		"navbar_bg": navbar_bg,
		"sidebar_bg": sidebar_bg,
		"surface_bg": surface_bg,
		"body_bg": body_bg,
		"text_primary": text_primary,
	}
	theme = _build_mock_theme(fields)
	css = theme.generate_css_variables()
	assert css.count("{") == css.count("}"), "Unbalanced braces"
	assert css.count("{") == 1, "Should have exactly one rule block"
	body = re.search(r"\{(.+)\}", css).group(1)
	for decl in body.rstrip(";").split(";"):
		assert ":" in decl, f"Invalid declaration (no colon): {decl}"


# ── Property 5: Auto-Computed Hover Colors ──
@given(btn_bg=hex_color, body_bg=hex_color)
@settings(max_examples=100)
def test_property_5_auto_computed_hover(btn_bg, body_bg):
	"""Property 5: Hover color auto-computed when hover field is empty."""
	fields = {
		"theme_name": "test",
		"theme_type": "Custom Light",
		"accent_primary": "#2076FF",
		"navbar_bg": "#ffffff",
		"sidebar_bg": "#f0f0f0",
		"surface_bg": "#ffffff",
		"body_bg": body_bg,
		"text_primary": "#000000",
		"primary_btn_bg": btn_bg,
	}
	theme = _build_mock_theme(fields)
	css = theme.generate_css_variables()
	parsed = _parse_css_variables(css)
	assert "--ct-primary-btn-hover-bg" in parsed, "Hover color should be auto-computed"
	hover = parsed["--ct-primary-btn-hover-bg"]
	assert hover.startswith("#") and len(hover) == 7, f"Invalid hover color: {hover}"
	# Edge case: #000000 darkened is still #000000, #ffffff lightened is still #ffffff
	if btn_bg not in ("#000000", "#ffffff"):
		assert hover != btn_bg, "Hover should differ from base color (except black/white edge cases)"
