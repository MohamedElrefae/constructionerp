"""Refresh Arabic translations and Construction sidebar during deploy."""

import frappe

from construction.insert_translations import execute as seed_translations
from construction.install import setup_construction_workspace_page, setup_workspace_sidebar


def execute():
	seed_translations()

	if frappe.db.table_exists("Workspace Sidebar"):
		setup_workspace_sidebar()
		setup_construction_workspace_page()

	frappe.clear_cache()
