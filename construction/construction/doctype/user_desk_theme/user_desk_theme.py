# Copyright (c) 2026, Construction and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UserDeskTheme(Document):
	"""Per-user theme preferences"""

	def validate(self):
		"""Validate user theme settings"""
		# Check if user override is allowed
		try:
			site_settings = frappe.get_doc("Modern Theme Settings")
			if not site_settings.allow_user_override and not self.inherit_from_site:
				frappe.throw("User theme overrides are not allowed by administrator")
		except frappe.DoesNotExistError:
			pass  # No site settings yet, allow override

		# Validate theme references
		if not self.inherit_from_site:
			if self.light_theme and not frappe.db.exists("Construction Theme", self.light_theme):
				frappe.throw(f"Light theme '{self.light_theme}' does not exist")

			if self.dark_theme and not frappe.db.exists("Construction Theme", self.dark_theme):
				frappe.throw(f"Dark theme '{self.dark_theme}' does not exist")

		# Ensure user is valid
		if not frappe.db.exists("User", self.user):
			frappe.throw(f"User '{self.user}' does not exist")

	def before_insert(self):
		"""Ensure unique user constraint"""
		if frappe.db.exists("User Desk Theme", {"user": self.user}):
			frappe.throw(f"Theme settings already exist for user '{self.user}'")

	def on_update(self):
		"""Clear cache when user theme is updated"""
		frappe.cache().delete_key(f"user_desk_theme:{self.user}")

	@staticmethod
	def get_user_theme(user=None):
		"""Get theme settings for a user"""
		if not user:
			user = frappe.session.user

		try:
			return frappe.get_doc("User Desk Theme", {"user": user})
		except frappe.DoesNotExistError:
			return None

	@staticmethod
	def get_or_create_user_theme(user=None):
		"""Get or create theme settings for a user"""
		if not user:
			user = frappe.session.user

		theme = UserDeskTheme.get_user_theme(user)
		if theme:
			return theme

		# Create default settings
		theme = frappe.new_doc("User Desk Theme")
		theme.user = user
		theme.inherit_from_site = 1
		theme.insert(ignore_permissions=True)
		return theme
