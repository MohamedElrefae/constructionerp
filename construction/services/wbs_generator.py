# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

import frappe
from typing import Optional


class WBSGenerator:
	"""Hierarchical WBS code generation for BOQ Structure tree."""

	@staticmethod
	def generate_code_for_node(boq_header: str, parent_structure: str = None, node_type: str = "Section") -> str:
		"""Generate WBS code for a new node."""
		sibling_count = WBSGenerator._count_siblings(boq_header, parent_structure)
		seq = sibling_count + 1

		if not parent_structure:
			# Root level: 2-digit code
			return f"{seq:02d}"

		# Get parent WBS code
		parent_wbs = frappe.db.get_value("BOQ Structure", parent_structure, "wbs_code")

		if node_type == "Item":
			# Leaf items: 3-digit suffix
			return f"{parent_wbs}.{seq:03d}"
		else:
			# Sections: 2-digit suffix
			return f"{parent_wbs}.{seq:02d}"

	@staticmethod
	def regenerate_subtree(node_name: str, boq_header: str):
		"""Regenerate WBS codes for a node and all its descendants."""
		node = frappe.get_doc("BOQ Structure", node_name)

		# Regenerate this node's code
		parent_wbs = None
		if node.parent_structure:
			parent_wbs = frappe.db.get_value("BOQ Structure", node.parent_structure, "wbs_code")

		# Generate new code for this node
		sibling_count = WBSGenerator._count_siblings(boq_header, node.parent_structure)
		seq = sibling_count + 1

		if node.node_type == "Item":
			new_code = f"{parent_wbs}.{seq:03d}" if parent_wbs else f"{seq:03d}"
		else:
			new_code = f"{parent_wbs}.{seq:02d}" if parent_wbs else f"{seq:02d}"

		# Update the node
		frappe.db.set_value("BOQ Structure", node.name, "wbs_code", new_code)

		# Recursively update children
		children = frappe.get_all("BOQ Structure",
			filters={"parent_structure": node.name, "boq_header": boq_header},
			order_by="lft"
		)

		for child in children:
			WBSGenerator.regenerate_subtree(child.name, boq_header)

	@staticmethod
	def regenerate_all(boq_header: str):
		"""Regenerate all WBS codes for a BOQ header."""
		# Get all root nodes
		roots = frappe.get_all("BOQ Structure",
			filters={"boq_header": boq_header, "parent_structure": ["=", ""]},
			order_by="lft"
		)

		for root in roots:
			WBSGenerator.regenerate_subtree(root.name, boq_header)

	@staticmethod
	def _count_siblings(boq_header: str, parent_structure: str = None) -> int:
		"""Count siblings for a given parent."""
		filters = {"boq_header": boq_header}
		if parent_structure:
			filters["parent_structure"] = parent_structure
		else:
			filters["parent_structure"] = ["is", "not set"]

		return frappe.db.count("BOQ Structure", filters)

	@staticmethod
	def parse_wbs_code(wbs_code: str) -> list:
		"""Parse WBS code into segments."""
		return wbs_code.split(".")

	@staticmethod
	def build_wbs_code(segments: list) -> str:
		"""Rebuild WBS code from segments."""
		return ".".join(segments)

	@staticmethod
	def validate_wbs_unique(wbs_code: str, boq_header: str, exclude: str = None) -> bool:
		"""Check if WBS code is unique within BOQ header."""
		filters = {
			"boq_header": boq_header,
			"wbs_code": wbs_code
		}
		if exclude:
			filters["name"] = ["!=", exclude]

		return not frappe.db.exists("BOQ Structure", filters)

	@staticmethod
	def get_section_rollup(structure_name: str) -> float:
		"""Calculate roll-up total for a section."""
		from frappe.utils.nestedset import get_descendants

		node = frappe.get_doc("BOQ Structure", structure_name)

		# Get all leaf nodes in this section
		descendants = get_descendants("BOQ Structure", node.name)

		# Get all BOQ Items for these structures
		items = frappe.get_all("BOQ Item",
			filters={"structure": ["in", descendants]},
			fields=["line_total"]
		)

		return sum(item.line_total for item in items if item.line_total)

	@staticmethod
	def get_leaf_items_in_section(section_name: str):
		"""Get all leaf items within a section."""
		from frappe.utils.nestedset import get_descendants

		descendants = get_descendants("BOQ Structure", section_name)
		leaf_nodes = frappe.get_all("BOQ Structure",
			filters={"name": ["in", descendants], "is_group": 0},
			fields=["name"]
		)

		leaf_item_names = [node.name for node in leaf_nodes]
		items = frappe.get_all("BOQ Item",
			filters={"structure": ["in", leaf_item_names]},
			fields=["*"]
		)

		return items
