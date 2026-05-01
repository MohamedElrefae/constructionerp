# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

from typing import Any, Dict, List

import frappe


class BOQMigrationService:
	"""Service for migrating old BOQ Node data to new BOQ Structure/Item structure."""

	@staticmethod
	def migrate_all_headers():
		"""Migrate all BOQ Headers from old to new structure."""
		try:
			headers = frappe.get_all("BOQ Header", fields=["name"])
			results = []

			for header in headers:
				result = BOQMigrationService.migrate_header(header.name)
				results.append(
					{
						"header": header.name,
						"success": result.get("success", False),
						"migrated": result.get("migrated", 0),
						"error": result.get("error"),
					}
				)

			return {"success": True, "results": results}
		except Exception as e:
			frappe.log_error(f"Migration error: {str(e)}")
			return {"success": False, "error": str(e)}

	@staticmethod
	def migrate_header(boq_header: str) -> Dict[str, Any]:
		"""Migrate a single BOQ Header from old to new structure."""
		try:
			# Get old BOQ Node records
			old_nodes = frappe.get_all(
				"BOQ Node",
				filters={"parent": boq_header, "parenttype": "BOQ Header"},
				fields=["*"],
				order_by="idx",
			)

			if not old_nodes:
				return {"success": False, "error": f"No BOQ Node records found for {boq_header}"}

			# Create a map of old node IDs to new structure IDs
			node_map = {}
			migrated_count = 0

			# First pass: create all BOQ Structure nodes
			for old_node in old_nodes:
				# Create BOQ Structure
				structure = frappe.new_doc("BOQ Structure")
				structure.boq_header = boq_header
				structure.title = old_node.title
				structure.node_type = old_node.node_type
				structure.description = old_node.description
				structure.parent_structure = None  # Will be updated in second pass
				structure.flags.ignore_wbs_generation = True
				structure.insert()

				# Store mapping
				node_map[old_node.name] = {
					"new_id": structure.name,
					"old_parent": old_node.parent_node,
					"old_node": old_node,
				}
				migrated_count += 1

			# Second pass: update parent relationships
			for old_node in old_nodes:
				if old_node.parent_node and old_node.parent_node in node_map:
					parent_structure = node_map[old_node.parent_node]["new_id"]
					child_structure = node_map[old_node.name]["new_id"]

					frappe.db.set_value(
						"BOQ Structure", child_structure, {"parent_structure": parent_structure}
					)

			# Third pass: create BOQ Items for leaf nodes
			for old_node in old_nodes:
				if old_node.node_type == "Item":
					structure_name = node_map[old_node.name]["new_id"]

					# Create BOQ Item
					item = frappe.new_doc("BOQ Item")
					item.structure = structure_name
					item.boq_header = boq_header
					item.quantity = old_node.quantity or 0
					item.unit = old_node.unit
					item.cost_item = old_node.cost_item
					item.contract_unit_price = old_node.unit_price or 0
					item.quantity_executed = old_node.quantity_executed or 0
					item.insert()

			# Rebuild tree and regenerate WBS codes
			frappe.db.commit()

			# Rebuild tree and regenerate WBS codes
			from construction.services.wbs_generator import WBSGenerator

			WBSGenerator.regenerate_all(boq_header)

			return {
				"success": True,
				"migrated": migrated_count,
				"message": f"Successfully migrated {migrated_count} nodes",
			}

		except Exception as e:
			frappe.log_error(f"Migration failed for {boq_header}: {str(e)}")
			return {"success": False, "error": str(e)}

	@staticmethod
	def validate_migration(boq_header: str) -> Dict[str, Any]:
		"""Validate that migration was successful."""
		try:
			# Count old nodes
			old_count = frappe.db.count("BOQ Node", {"parent": boq_header})

			# Count new structures
			new_count = frappe.db.count("BOQ Structure", {"boq_header": boq_header})

			# Count new items
			item_count = frappe.db.count("BOQ Item", {"boq_header": boq_header})

			return {
				"success": True,
				"old_nodes": old_count,
				"new_structures": new_count,
				"new_items": item_count,
				"valid": new_count == old_count,
			}
		except Exception as e:
			return {"success": False, "error": str(e)}
