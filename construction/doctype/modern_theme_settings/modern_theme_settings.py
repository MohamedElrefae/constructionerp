# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ModernThemeSettings(Document):
	"""Site-wide Modern Theme Settings (Single DocType)

	This is a site-wide configuration DocType that stores:
	- Default themes for light/dark modes
	- User override permissions
	- Contrast check enforcement
	- Theme switcher UI settings
	- CSS cache TTL

	Individual theme configurations are stored in the Construction Theme DocType.
	Per-user theme preferences are stored in the User Desk Theme DocType.
	"""

	def validate(self):
		"""Validate theme settings"""
		# Validate that referenced themes exist
		if self.default_light_theme:
			if not frappe.db.exists("Construction Theme", self.default_light_theme):
				frappe.throw(f"Construction Theme '{self.default_light_theme}' does not exist")

		if self.default_dark_theme:
			if not frappe.db.exists("Construction Theme", self.default_dark_theme):
				frappe.throw(f"Construction Theme '{self.default_dark_theme}' does not exist")

		# Validate theme switcher limit
		if self.theme_switcher_limit and self.theme_switcher_limit < 1:
			frappe.throw("Theme Switcher Limit must be at least 1")

		# Validate CSS cache TTL
		if self.css_cache_ttl and self.css_cache_ttl < 60:
			frappe.throw("CSS Cache TTL must be at least 60 seconds")

	def on_update(self):
		"""Clear cache when settings are updated"""
		frappe.cache().delete_key("modern_theme_settings")
		# Invalidate all theme CSS caches
		frappe.cache().delete_key("theme_css:*")

	@staticmethod
	def get_settings():
		"""Get or create Modern Theme Settings"""
		try:
			return frappe.get_doc("Modern Theme Settings")
		except frappe.DoesNotExistError:
			# Create default settings
			settings = frappe.new_doc("Modern Theme Settings")
			settings.allow_user_override = 1
			settings.enforce_contrast_check = 0
			settings.theme_switcher_limit = 12
			settings.css_cache_ttl = 3600
			settings.insert(ignore_permissions=True)
			return settings

	@staticmethod
	def get_default_light_theme():
		"""Get the default light theme"""
		settings = ModernThemeSettings.get_settings()
		return settings.default_light_theme or "Construction Light"

	@staticmethod
	def get_default_dark_theme():
		"""Get the default dark theme"""
		settings = ModernThemeSettings.get_settings()
		return settings.default_dark_theme or "Construction Dark"

	@staticmethod
	def is_user_override_allowed():
		"""Check if users can override theme"""
		settings = ModernThemeSettings.get_settings()
		return settings.allow_user_override

	@staticmethod
	def is_contrast_check_enforced():
		"""Check if contrast check is enforced"""
		settings = ModernThemeSettings.get_settings()
		return settings.enforce_contrast_check
