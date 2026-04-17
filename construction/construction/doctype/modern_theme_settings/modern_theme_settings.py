# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ModernThemeSettings(Document):
    """Site-wide Modern Theme Settings (Single DocType)"""
    
    def validate(self):
        """Validate theme settings"""
        # Ensure valid Desk Theme references
        if self.default_light_theme:
            if not frappe.db.exists("Desk Theme", self.default_light_theme):
                frappe.throw(f"Light theme '{self.default_light_theme}' does not exist")
        
        if self.default_dark_theme:
            if not frappe.db.exists("Desk Theme", self.default_dark_theme):
                frappe.throw(f"Dark theme '{self.default_dark_theme}' does not exist")
    
    def on_update(self):
        """Clear cache when settings are updated"""
        frappe.cache().delete_key("modern_theme_settings")
    
    @staticmethod
    def get_settings():
        """Get or create Modern Theme Settings"""
        try:
            return frappe.get_doc("Modern Theme Settings")
        except frappe.DoesNotExistError:
            # Create default settings
            settings = frappe.new_doc("Modern Theme Settings")
            settings.allow_user_override = 1
            settings.force_modern_ui = 1
            settings.insert(ignore_permissions=True)
            return settings
