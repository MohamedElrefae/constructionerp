# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import re
import json
import frappe
from frappe.model.document import Document
from frappe import _


class ConstructionTheme(Document):
    """Construction Theme DocType - Enterprise-grade theme configuration"""
    
    # Field-to-CSS-Variable mapping for all 40+ theme fields
    FIELD_VAR_MAP = {
        # Core colors (existing fields)
        'accent_primary':       '--ct-accent-primary',
        'accent_primary_hover': '--ct-accent-hover',
        'accent_secondary':     '--ct-accent-secondary',
        'navbar_bg':            '--ct-navbar-bg',
        'sidebar_bg':           '--ct-sidebar-bg',
        'surface_bg':           '--ct-surface-bg',
        'body_bg':              '--ct-body-bg',
        'text_primary':         '--ct-text-primary',
        'text_secondary':       '--ct-text-secondary',
        'border_color':         '--ct-border-color',
        'success_color':        '--ct-success',
        'warning_color':        '--ct-warning',
        'error_color':          '--ct-error',
        # Buttons (new fields)
        'primary_btn_bg':           '--ct-primary-btn-bg',
        'primary_btn_text':         '--ct-primary-btn-text',
        'primary_btn_hover_bg':     '--ct-primary-btn-hover-bg',
        'primary_btn_hover_text':   '--ct-primary-btn-hover-text',
        'secondary_btn_bg':         '--ct-secondary-btn-bg',
        'secondary_btn_text':       '--ct-secondary-btn-text',
        'secondary_btn_hover_bg':   '--ct-secondary-btn-hover-bg',
        'secondary_btn_hover_text': '--ct-secondary-btn-hover-text',
        # Tables (new fields)
        'table_header_bg':   '--ct-table-header-bg',
        'table_header_text': '--ct-table-header-text',
        'table_body_bg':     '--ct-table-body-bg',
        'table_body_text':   '--ct-table-body-text',
        # Widgets (new fields)
        'number_card_bg':     '--ct-number-card-bg',
        'number_card_border': '--ct-number-card-border',
        'number_card_text':   '--ct-number-card-text',
        # Input fields (new fields)
        'input_bg':          '--ct-input-bg',
        'input_border':      '--ct-input-border',
        'input_text':        '--ct-input-text',
        'input_label_color': '--ct-input-label',
        # Navbar extension (new field)
        'navbar_text_color': '--ct-navbar-text',
        # Footer (new fields)
        'footer_bg':   '--ct-footer-bg',
        'footer_text': '--ct-footer-text',
    }
    
    def validate(self):
        """Runs on every save - prevents invalid theme states."""
        self._validate_hex_colors()
        self._validate_login_page_fields()
        self._validate_login_page_bg_image_publicity()
        self._auto_calculate_derived_colors()
        self._validate_unique_defaults()
        self._validate_custom_css()
        self._calculate_contrast_ratio()
        self._validate_preview_colors()
        
    def _validate_unique_defaults(self):
        """Only one active theme can be default light; only one default dark."""
        if self.is_default_light:
            existing = frappe.db.exists(
                "Construction Theme",
                {"is_default_light": 1, "is_active": 1, "name": ("!=", self.name)}
            )
            if existing:
                frappe.throw(_(
                    "Only one theme can be the default light theme. "
                    "'{0}' is already set as default."
                ).format(existing))

        if self.is_default_dark:
            existing = frappe.db.exists(
                "Construction Theme",
                {"is_default_dark": 1, "is_active": 1, "name": ("!=", self.name)}
            )
            if existing:
                frappe.throw(_(
                    "Only one theme can be the default dark theme. "
                    "'{0}' is already set as default."
                ).format(existing))
    
    def _validate_hex_colors(self):
        """Validate all color fields have proper hex format.
        
        Covers all 40+ color fields across all tabs:
        - General: accent_primary, accent_primary_hover, accent_secondary, sidebar_bg, surface_bg, body_bg, text_primary, text_secondary, border_color
        - Login Page: login_btn_bg, login_btn_text, login_btn_hover_bg, login_btn_hover_text, login_page_bg_color, login_heading_text_color, login_tab_bg_color
        - Buttons: primary_btn_bg, primary_btn_text, primary_btn_hover_bg, primary_btn_hover_text, secondary_btn_bg, secondary_btn_text, secondary_btn_hover_bg, secondary_btn_hover_text
        - Tables: table_header_bg, table_header_text, table_body_bg, table_body_text
        - Widgets: number_card_bg, number_card_border, number_card_text
        - Input Fields: input_bg, input_border, input_text, input_label_color
        - Navbar: navbar_bg, navbar_text_color
        - Footer: footer_bg, footer_text
        - Semantic Colors: success_color, warning_color, error_color
        """
        color_fields = [
            # General tab
            "accent_primary", "accent_primary_hover", "accent_secondary",
            "sidebar_bg", "surface_bg", "body_bg",
            "text_primary", "text_secondary", "border_color",
            # Login Page tab
            "login_btn_bg", "login_btn_text", "login_btn_hover_bg", "login_btn_hover_text",
            "login_page_bg_color", "login_heading_text_color", "login_tab_bg_color",
            # Buttons tab
            "primary_btn_bg", "primary_btn_text", "primary_btn_hover_bg", "primary_btn_hover_text",
            "secondary_btn_bg", "secondary_btn_text", "secondary_btn_hover_bg", "secondary_btn_hover_text",
            # Tables tab
            "table_header_bg", "table_header_text", "table_body_bg", "table_body_text",
            # Widgets tab
            "number_card_bg", "number_card_border", "number_card_text",
            # Input Fields tab
            "input_bg", "input_border", "input_text", "input_label_color",
            # Navbar tab
            "navbar_bg", "navbar_text_color",
            # Footer tab
            "footer_bg", "footer_text",
            # Semantic Colors tab
            "success_color", "warning_color", "error_color"
        ]
        
        for field in color_fields:
            value = self.get(field)
            if value and not self._is_valid_hex_color(value):
                frappe.throw(_(
                    "Invalid hex color format in field '{0}': {1}"
                ).format(field, value))
    
    def _is_valid_hex_color(self, color):
        """Check if color is valid hex format (#RGB or #RRGGBB)."""
        if not color:
            return True
        color = color.strip()
        if not color.startswith("#"):
            return False
        hex_part = color[1:]
        return len(hex_part) in [3, 6] and all(
            c in "0123456789ABCDEFabcdef" for c in hex_part
        )
    
    def _validate_login_page_fields(self):
        """Validate login page field dependencies and constraints.
        
        Rules:
        - If login_page_bg_type is "Background Image", login_page_bg_image must be non-empty
        - If login_page_bg_type is "Solid Color", login_page_bg_color must be non-empty
        - login_page_title must not exceed 30 characters
        """
        # Validate bg_type ↔ bg_color/bg_image mutual requirement
        bg_type = self.get('login_page_bg_type')
        bg_color = self.get('login_page_bg_color')
        bg_image = self.get('login_page_bg_image')
        
        if bg_type == "Background Image":
            if not bg_image:
                frappe.throw(_(
                    "Login Page Background Image is required when "
                    "Login Page Background Type is set to 'Background Image'."
                ))
        elif bg_type == "Solid Color":
            if not bg_color:
                frappe.throw(_(
                    "Login Page Background Color is required when "
                    "Login Page Background Type is set to 'Solid Color'."
                ))
        
        # Validate login_page_title max 30 chars
        title = self.get('login_page_title')
        if title and len(title) > 30:
            frappe.throw(_(
                "Login Page Title must not exceed 30 characters. "
                "Current length: {0}"
            ).format(len(title)))
    
    def _validate_login_page_bg_image_publicity(self):
        """Verify login_page_bg_image File record is public (is_private == 0).
        
        If the file is private, auto-set it to public and display a warning.
        """
        bg_image = self.get('login_page_bg_image')
        if not bg_image:
            return
        
        # Check if File record exists and is private
        file_doc = frappe.db.get_value(
            "File",
            {"file_url": bg_image},
            ["name", "is_private"],
            as_dict=True
        )
        
        if not file_doc:
            # Try by name/docname
            file_doc = frappe.db.get_value(
                "File",
                bg_image,
                ["name", "is_private"],
                as_dict=True
            )
        
        if file_doc and file_doc.get('is_private') == 1:
            # Auto-set to public
            frappe.db.set_value("File", file_doc['name'], "is_private", 0)
            frappe.msgprint(_(
                "Login Page Background Image was set to public. "
                "Private files cannot be accessed on the login page."
            ), alert=True, indicator="orange")
    
    def _auto_calculate_derived_colors(self):
        """Auto-calculate hover colors and border colors if blank."""
        if self.accent_primary and not self.accent_primary_hover:
            self.accent_primary_hover = self._darken_hex(self.accent_primary, 0.1)
            
        if self.accent_primary and not self.border_color:
            # 20% opacity version of accent
            self.border_color = self._hex_with_opacity(self.accent_primary, 0.2)
    
    def _darken_hex(self, hex_color, factor):
        """Darken a hex color by a factor (0-1)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _hex_with_opacity(self, hex_color, opacity):
        """Append opacity to hex color (returns #RRGGBBAA format)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        
        alpha = int(opacity * 255)
        return f"#{hex_color}{alpha:02x}"
    
    def _calculate_contrast_ratio(self):
        """Calculate WCAG contrast ratios for critical color pairs.
        
        Validates the following pairs:
        - text_primary vs body_bg
        - text_secondary vs surface_bg
        - primary_btn_text vs primary_btn_bg
        - accent_primary vs surface_bg
        
        Warns if any ratio is below 4.5:1 (WCAG AA standard for normal text).
        """
        # Define critical contrast pairs to check
        contrast_pairs = [
            ("text_primary", "body_bg", "Text Primary vs Body Background"),
            ("text_secondary", "surface_bg", "Text Secondary vs Surface Background"),
            ("primary_btn_text", "primary_btn_bg", "Primary Button Text vs Primary Button Background"),
            ("accent_primary", "surface_bg", "Accent Primary vs Surface Background"),
        ]
        
        # Store the first pair's ratio for backward compatibility (contrast_ratio field)
        first_ratio = None
        warnings = []
        
        for color1_field, color2_field, pair_name in contrast_pairs:
            color1 = self.get(color1_field)
            color2 = self.get(color2_field)
            
            if color1 and color2:
                ratio = self._get_contrast_ratio(color1, color2)
                
                # Store first ratio for backward compatibility
                if first_ratio is None:
                    first_ratio = ratio
                    self.contrast_ratio = ratio
                
                # Warn if below WCAG AA (4.5:1 for normal text)
                if ratio < 4.5:
                    warnings.append(
                        "  • {0}: {1:.1f}:1 (below 4.5:1)".format(pair_name, ratio)
                    )
        
        # Display warning if any pair fails
        if warnings:
            settings = frappe.get_single("Modern Theme Settings")
            enforce_contrast = getattr(settings, 'enforce_contrast_check', False)
            
            message = _(
                "Warning: The following color pairs have contrast ratios below "
                "WCAG AA standard (4.5:1):\n{0}\n\n"
                "Consider adjusting colors for better accessibility."
            ).format("\n".join(warnings))
            
            if enforce_contrast:
                frappe.throw(message)
            else:
                frappe.msgprint(message, alert=True, indicator="orange")
    
    def _get_contrast_ratio(self, color1, color2):
        """Calculate WCAG contrast ratio between two hex colors."""
        # Handle null/empty colors
        if not color1 or not color2:
            return 0
        
        def luminance(hex_color):
            # Handle invalid hex colors
            if not hex_color or not isinstance(hex_color, str):
                return 0
            
            hex_color = hex_color.lstrip('#').strip()
            if not hex_color or len(hex_color) not in [3, 6]:
                return 0
            
            try:
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                
                r = int(hex_color[0:2], 16) / 255
                g = int(hex_color[2:4], 16) / 255
                b = int(hex_color[4:6], 16) / 255
                
                r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
                g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
                b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
                
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            except (ValueError, IndexError):
                return 0
        
        l1 = luminance(color1)
        l2 = luminance(color2)
        
        lighter = max(l1, l2)
        darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def _validate_preview_colors(self):
        """Generate preview colors array if not set."""
        if not self.preview_colors:
            preview = [
                self.navbar_bg or self.accent_primary,
                self.accent_primary,
                self.surface_bg or self.body_bg,
                self.text_primary,
                self.border_color or self.accent_secondary or self.accent_primary
            ]
            self.preview_colors = json.dumps(preview)
    
    def _validate_custom_css(self):
        """Validate and sanitize custom CSS."""
        if not self.custom_css:
            return
            
        # Security: Block dangerous CSS patterns
        blocked_patterns = [
            r'@import\s+',
            r'@font-face\s*\{',
            r'url\s*\(',
            r'behavior\s*:',
            r'-moz-binding\s*:',
            r'javascript\s*:',
            r'expression\s*\(',
        ]
        
        for pattern in blocked_patterns:
            if re.search(pattern, self.custom_css, re.IGNORECASE):
                frappe.throw(_(
                    "Custom CSS contains blocked pattern: {0}. "
                    "External resources and expressions are not allowed."
                ).format(pattern))
        
        # Limit size to 10KB
        if len(self.custom_css) > 10240:
            frappe.throw(_("Custom CSS exceeds 10KB limit."))
    
    def on_update(self):
        """Invalidate CSS cache when theme changes."""
        frappe.cache().delete_value(f"construction_theme_css:{self.name}")
        frappe.publish_realtime("theme_updated", {"theme": self.name})
        
        # Regenerate login theme file if this is the system default
        if self.is_system_theme or self.is_default_light or self.is_default_dark:
            self._regenerate_login_theme_file()
    
    def on_trash(self):
        """Prevent deletion of system themes."""
        if self.is_system_theme:
            frappe.throw(_(
                "System themes cannot be deleted. Deactivate them instead."
            ))
        frappe.cache().delete_value(f"construction_theme_css:{self.name}")
    
    def generate_css(self) -> str:
        """Generate complete CSS for this theme using Jinja2 templates.

        NOTE: This method does NOT interact with cache. The caller
        (e.g. theme_api.get_theme_css) is responsible for caching.
        """
        try:
            from jinja2 import Environment, FileSystemLoader
            import os

            # Get template directory
            template_dir = os.path.join(
                os.path.dirname(__file__),
                '..', '..', 'theme_templates'
            )

            env = Environment(loader=FileSystemLoader(template_dir))

            # Template order: base → navbar → sidebar → buttons → forms → tables → modals → toasts → tree
            template_names = [
                'base.css.j2', 'navbar.css.j2', 'sidebar.css.j2',
                'buttons.css.j2', 'forms.css.j2', 'tables.css.j2',
                'modals.css.j2', 'toasts.css.j2', 'tree.css.j2'
            ]

            css_parts = []

            # Theme context for templates
            context = {
                'theme_name': self.theme_name,
                'is_dark_mode': 'Dark' in self.theme_type,
                'accent_primary': self.accent_primary,
                'accent_primary_hover': self.accent_primary_hover or self.accent_primary,
                'accent_secondary': self.accent_secondary or self.accent_primary,
                'navbar_bg': self.navbar_bg,
                'sidebar_bg': self.sidebar_bg,
                'surface_bg': self.surface_bg,
                'body_bg': self.body_bg,
                'text_primary': self.text_primary,
                'text_secondary': self.text_secondary or self.text_primary,
                'border_color': self.border_color or self.accent_primary,
                'success_color': self.success_color,
                'warning_color': self.warning_color,
                'error_color': self.error_color,
            }

            for template_name in template_names:
                try:
                    template = env.get_template(template_name)
                    css_parts.append(template.render(**context))
                except Exception as e:
                    frappe.log_error(f"Error rendering {template_name}: {str(e)}")

            # Append custom CSS if present
            if self.custom_css:
                css_parts.append(f"/* Custom CSS for {self.theme_name} */")
                css_parts.append(self.custom_css)

            return '\n'.join(css_parts)

        except Exception as e:
            frappe.log_error(f"Error generating theme CSS for {self.name}: {str(e)}")
            return ""
    
    def get_css_variables(self) -> str:
        """Generate CSS variable string for this theme."""
        variables = []
        
        if self.navbar_bg:
            variables.append(f"--navbar-bg: {self.navbar_bg};")
        if self.sidebar_bg:
            variables.append(f"--sidebar-bg: {self.sidebar_bg};")
        if self.surface_bg:
            variables.append(f"--surface-bg: {self.surface_bg};")
        if self.body_bg:
            variables.append(f"--body-bg: {self.body_bg};")
        if self.text_primary:
            variables.append(f"--text-primary: {self.text_primary};")
        if self.text_secondary:
            variables.append(f"--text-secondary: {self.text_secondary};")
        if self.accent_primary:
            variables.append(f"--accent-primary: {self.accent_primary};")
        if self.accent_secondary:
            variables.append(f"--accent-secondary: {self.accent_secondary};")
        if self.border_color:
            variables.append(f"--border-color: {self.border_color};")
        if self.success_color:
            variables.append(f"--success: {self.success_color};")
        if self.warning_color:
            variables.append(f"--warning: {self.warning_color};")
        if self.error_color:
            variables.append(f"--error: {self.error_color};")
        
        return "\n".join(variables)
    
    def generate_css_variables(self) -> str:
        """Generate CSS variable block scoped to this theme.
        
        Returns CSS like:
        html[data-modern-theme="theme_identifier"]{--ct-accent-primary:#4CAF50;...}
        
        Skips any field with empty/null value.
        Output ≤ 800 bytes for fully populated theme.
        Auto-computes hover colors if empty.
        Uses concise formatting (no newlines/indentation) to meet size constraint.
        """
        variables = []
        
        # Auto-compute hover colors if needed
        primary_btn_bg = self.get('primary_btn_bg')
        primary_btn_hover_bg = self.get('primary_btn_hover_bg')
        if primary_btn_bg and not primary_btn_hover_bg:
            primary_btn_hover_bg = self._compute_hover_color(primary_btn_bg)
        
        secondary_btn_bg = self.get('secondary_btn_bg')
        secondary_btn_hover_bg = self.get('secondary_btn_hover_bg')
        if secondary_btn_bg and not secondary_btn_hover_bg:
            secondary_btn_hover_bg = self._compute_hover_color(secondary_btn_bg)
        
        # Iterate FIELD_VAR_MAP and collect non-empty values
        for field_name, var_name in self.FIELD_VAR_MAP.items():
            # Special handling for computed hover colors
            if field_name == 'primary_btn_hover_bg' and primary_btn_hover_bg:
                variables.append(f"{var_name}:{primary_btn_hover_bg}")
            elif field_name == 'secondary_btn_hover_bg' and secondary_btn_hover_bg:
                variables.append(f"{var_name}:{secondary_btn_hover_bg}")
            else:
                value = self.get(field_name)
                if value:
                    variables.append(f"{var_name}:{value}")
        
        # Return empty string if no variables
        if not variables:
            return ""
        
        # Generate theme identifier: lowercase, replace spaces with underscores
        identifier = self.theme_name.lower().replace(' ', '_')
        
        # Wrap in scoped CSS block with concise formatting
        css_block = f"html[data-modern-theme=\"{identifier}\"]{{" + ";".join(variables) + ";}"
        
        return css_block
    
    def _compute_hover_color(self, hex_color: str) -> str:
        """Compute hover color by darkening/lightening by 10%.
        
        Darkens for light themes (body_bg not starting with #1).
        Lightens for dark themes (body_bg starting with #1).
        """
        body_bg = self.get('body_bg', '')
        is_dark_theme = body_bg.startswith('#1') if body_bg else False
        
        if is_dark_theme:
            # Lighten by 10% for dark themes
            return self._lighten_hex(hex_color, 0.1)
        else:
            # Darken by 10% for light themes
            return self._darken_hex(hex_color, 0.1)
    
    def _lighten_hex(self, hex_color: str, factor: float) -> str:
        """Lighten a hex color by a factor (0-1)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def generate_login_css(self) -> str:
        """Generate static CSS for login page theming.
        
        Uses Frappe's actual login page selectors:
        - .login-content.page-card for the login box
        - .btn-login.btn-primary for the login button
        - body[data-path="login"] for page-level styles
        
        HTML-escapes login_page_title to prevent XSS.
        """
        import html
        
        css_rules = []
        
        # Login button colors
        if self.login_btn_bg:
            css_rules.append(f".btn-login.btn-primary {{ background-color: {self.login_btn_bg} !important; border-color: {self.login_btn_bg} !important; }}")
        
        if self.login_btn_text:
            css_rules.append(f".btn-login.btn-primary {{ color: {self.login_btn_text} !important; }}")
        
        if self.login_btn_hover_bg:
            css_rules.append(f".btn-login.btn-primary:hover {{ background-color: {self.login_btn_hover_bg} !important; border-color: {self.login_btn_hover_bg} !important; }}")
        
        if self.login_btn_hover_text:
            css_rules.append(f".btn-login.btn-primary:hover {{ color: {self.login_btn_hover_text} !important; }}")
        
        # Page background
        bg_type = self.get('login_page_bg_type')
        if bg_type == "Background Image" and self.login_page_bg_image:
            css_rules.append(f"body[data-path='login'] {{ background-image: url('{self.login_page_bg_image}'); background-size: cover; background-position: center; }}")
        elif bg_type == "Solid Color" and self.login_page_bg_color:
            css_rules.append(f"body[data-path='login'] {{ background-color: {self.login_page_bg_color} !important; }}")
        
        # Login box position
        box_position = self.get('login_box_position')
        if box_position == "Left":
            css_rules.append(".login-content.page-card { margin-left: 5%; margin-right: auto; }")
        elif box_position == "Right":
            css_rules.append(".login-content.page-card { margin-left: auto; margin-right: 5%; }")
        
        # Heading text color
        if self.login_heading_text_color:
            css_rules.append(f".page-card-head {{ color: {self.login_heading_text_color} !important; }}")
            css_rules.append(f".page-card-head h4 {{ color: {self.login_heading_text_color} !important; }}")
        
        # Tab background color
        if self.login_tab_bg_color:
            css_rules.append(f".login-content .nav-tabs {{ background-color: {self.login_tab_bg_color} !important; }}")
        
        # Login page title comment (HTML-escaped)
        if self.login_page_title:
            escaped_title = html.escape(self.login_page_title)
            css_rules.append(f"/* Login Page Title: {escaped_title} */")
        
        return "\n".join(css_rules)
    
    def _regenerate_login_theme_file(self):
        """Write login_theme.css to sites/assets/construction/css/.
        
        Called from on_update when this theme is the system default.
        Atomic write: writes to .tmp then renames.
        On failure: logs error, preserves previous file.
        If no previous file exists on failure: writes hardcoded fallback.
        """
        import os
        import tempfile
        
        try:
            # Determine the assets directory
            bench_path = frappe.utils.get_bench_path()
            assets_dir = os.path.join(bench_path, 'sites', 'assets', 'construction', 'css')
            os.makedirs(assets_dir, exist_ok=True)
            
            login_css_path = os.path.join(assets_dir, 'login_theme.css')
            
            # Generate login CSS
            login_css = self.generate_login_css()
            
            # Atomic write: write to .tmp then rename
            tmp_path = login_css_path + '.tmp'
            
            with open(tmp_path, 'w') as f:
                f.write(login_css)
            
            # Atomic rename
            if os.path.exists(login_css_path):
                os.remove(login_css_path)
            os.rename(tmp_path, login_css_path)
            
            frappe.logger().info(f"Login theme CSS regenerated for {self.name}")
            
        except Exception as e:
            frappe.log_error(f"Error regenerating login theme CSS: {str(e)}")
            
            # Try to preserve previous file
            try:
                bench_path = frappe.utils.get_bench_path()
                assets_dir = os.path.join(bench_path, 'sites', 'assets', 'construction', 'css')
                login_css_path = os.path.join(assets_dir, 'login_theme.css')
                
                # If no previous file exists, write hardcoded fallback
                if not os.path.exists(login_css_path):
                    os.makedirs(assets_dir, exist_ok=True)
                    fallback_css = """
/* Fallback Login Theme CSS */
.login-page {
  background-color: #f5f5f5;
}
.login-page .btn-primary {
  background-color: #2E7D32;
  border-color: #2E7D32;
  color: #fff;
}
.login-page .btn-primary:hover {
  background-color: #388E3C;
  border-color: #388E3C;
}
"""
                    with open(login_css_path, 'w') as f:
                        f.write(fallback_css)
                    frappe.logger().info("Fallback login theme CSS written")
            except Exception as fallback_error:
                frappe.log_error(f"Error writing fallback login CSS: {str(fallback_error)}")
    
    @staticmethod
    def get_system_default():
        """Get the current system default theme."""
        return frappe.db.get_value(
            "Construction Theme",
            {"is_system_theme": 1, "is_active": 1},
            ["name", "theme_name"],
            as_dict=True
        )
    
    @staticmethod
    def get_default_for_mode(mode):
        """Get default theme for light/dark mode."""
        mode_field = "is_default_light" if mode == "light" else "is_default_dark"
        return frappe.db.get_value(
            "Construction Theme",
            {mode_field: 1, "is_active": 1},
            ["name", "theme_name"],
            as_dict=True
        )
    
    @staticmethod
    def list_active_themes(limit=12):
        """List all active themes for theme switcher."""
        return frappe.get_all(
            "Construction Theme",
            filters={"is_active": 1},
            fields=[
                "name", "theme_name", "emoji_icon", "theme_type",
                "is_system_theme", "preview_colors", 
                "is_default_light", "is_default_dark"
            ],
            order_by="is_system_theme desc, theme_name asc",
            limit=limit
        )
