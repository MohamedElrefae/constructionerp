# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import json
from typing import Dict, List, Optional

import frappe


class BOQImportService:
	"""Excel import service for BOQ Structure and BOQ Item."""

	TEMPLATE_COLUMNS = [
		"WBS Code",
		"Parent WBS",
		"Title",
		"Type",
		"Unit",
		"Quantity",
		"Unit Price",
		"Factor",
		"Notes",
		"Owner Page",
		"Owner Ref No",
		"Owner File Ref",
	]

	@staticmethod
	def import_from_excel(file_url: str, boq_header: str) -> dict:
		"""Import BOQ from Excel file."""
		try:
			# For now, return a placeholder implementation
			# In a real implementation, this would:
			# 1. Parse the Excel file using openpyxl
			# 2. Validate all rows
			# 3. Create BOQ Structure nodes
			# 4. Create BOQ Item records for leaf nodes
			# 5. Rebuild tree and regenerate WBS codes

			return {
				"success": True,
				"message": "Excel import service ready",
				"note": "Full Excel import to be implemented with openpyxl",
				"template_columns": BOQImportService.TEMPLATE_COLUMNS,
			}

		except Exception as e:
			frappe.log_error(f"BOQ import error: {e!s}")
			return {"success": False, "error": str(e)}

	@staticmethod
	def validate_import_data(rows: list[dict], boq_header: str) -> list[str]:
		"""Validate import data before creation."""
		errors = []
		seen_wbs = set()

		for i, row in enumerate(rows, start=2):  # Excel rows start at 2
			wbs = row.get("WBS Code", "").strip()

			# Check WBS code uniqueness
			if wbs in seen_wbs:
				errors.append(f"Row {i}: Duplicate WBS Code '{wbs}'")
			seen_wbs.add(wbs)

			# Check parent reference
			parent_wbs = row.get("Parent WBS", "").strip()
			if parent_wbs and parent_wbs not in seen_wbs:
				# Check if parent exists in database
				if not frappe.db.exists("BOQ Structure", {"boq_header": boq_header, "wbs_code": parent_wbs}):
					errors.append(f"Row {i}: Parent WBS '{parent_wbs}' not found")

			# Validate item rows
			if row.get("Type") == "Item":
				if not row.get("Unit"):
					errors.append(f"Row {i}: Unit required for Item rows")
				qty = row.get("Quantity")
				if not qty or float(qty) <= 0:
					errors.append(f"Row {i}: Quantity must be positive for Item rows")

			# Validate section rows
			if row.get("Type") == "Section":
				price = row.get("Unit Price")
				if price and float(price) != 0:
					errors.append(f"Row {i}: Unit Price must be empty/zero for Section rows")

		return errors

	@staticmethod
	def create_import_template() -> str:
		"""Create a downloadable Excel template."""
		# This would create an Excel file with the template columns
		# For now, return a placeholder
		return "Excel template creation to be implemented"

	@staticmethod
	def get_import_status(import_id: str) -> dict:
		"""Get status of an import job."""
		return {"status": "completed", "import_id": import_id, "message": "Import status endpoint"}
