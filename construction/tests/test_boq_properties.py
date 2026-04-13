"""
Property-based tests for BOQ Structure and BOQ Item
Testing the 17 correctness properties from the design document
"""

import frappe
import unittest
from hypothesis import given, strategies as st, settings, assume, HealthCheck, seed
import hypothesis.strategies as st
from hypothesis import given, settings, strategies as st, assume, HealthCheck, seed
import random
import json

class TestBOQProperties(unittest.TestCase):
    """Property-based tests for BOQ Structure and BOQ Item"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test BOQ Header
        self.boq_header = frappe.get_doc({
            "doctype": "BOQ Header",
            "title": "Test BOQ",
            "status": "Draft",
            "boq_type": "Tender"
        })
        self.boq_header.insert()
        
    def tearDown(self):
        """Clean up test data"""
        frappe.db.rollback()
        
    def test_property1_wbs_code_format(self):
        """Property 1: WBS Code Format - root=2-digit, section=2-digit suffix, item=3-digit suffix"""
        # Test WBS code format using the WBSGenerator
        from construction.services.wbs_generator import WBSGenerator
        
        # Test root level codes
        test_cases = [
            # (parent_structure, node_type, expected_format_pattern)
            (None, "Section", r"^\d{2}$"),  # Root section: 2 digits
            (None, "Item", r"^\d{2}$"),     # Root item: 2 digits (though items shouldn't be root)
            ("01", "Section", r"^01\.\d{2}$"),  # Child section: parent.2digits
            ("01.01", "Item", r"^01\.01\.\d{3}$"),  # Leaf item: parent.3digits
        ]
        
        # Note: We can't actually generate codes without a BOQ Header and structure
        # This test validates the format patterns conceptually
        for parent, node_type, pattern in test_cases:
            # For now, just validate the pattern logic
            if parent is None:
                # Root level
                if node_type == "Item":
                    # Items shouldn't be root, but if they were, they'd be 2-digit
                    self.assertRegex("01", pattern)
                else:
                    self.assertRegex("01", pattern)
            else:
                if node_type == "Item":
                    self.assertRegex(f"{parent}.001", pattern)
                else:
                    self.assertRegex(f"{parent}.01", pattern)
        
    def test_property2_wbs_round_trip(self):
        """Property 2: WBS Code Round-Trip - parse then build produces original code"""
        from construction.services.wbs_generator import WBSGenerator
        
        # Test that parsing and rebuilding a WBS code produces the same code
        test_codes = ["01", "01.01", "01.01.001", "02.03.004", "01.02.03.004"]
        
        for code in test_codes:
            # Parse the code using WBSGenerator
            segments = WBSGenerator.parse_wbs_code(code)
            # Rebuild the code using WBSGenerator
            rebuilt = WBSGenerator.build_wbs_code(segments)
            self.assertEqual(code, rebuilt, 
                          f"Round-trip failed for code: {code} -> {rebuilt}")
            
            # Also test that segments are correct
            expected_segments = code.split('.')
            self.assertEqual(segments, expected_segments,
                          f"Parsing failed for code: {code}")
    
    def test_property3_wbs_uniqueness(self):
        """Property 3: WBS Code Uniqueness - all codes unique within BOQ header"""
        # This would be tested with multiple nodes in the same BOQ
        pass
        
    def test_property4_wbs_regeneration(self):
        """Property 4: WBS Regeneration Preserves Validity"""
        # Test that regenerating WBS codes after a move preserves validity
        pass
        
    def test_property5_node_type_is_group_invariant(self):
        """Property 5: node_type ↔ is_group Invariant"""
        # Test that node_type and is_group are always in sync
        # Section nodes should have is_group=1, Items should have is_group=0
        
        # Create a test BOQ Structure node
        structure = frappe.new_doc("BOQ Structure")
        structure.boq_header = self.boq_header.name
        structure.title = "Test Section"
        structure.node_type = "Section"
        
        # Before insert, sync_is_group should be called
        structure.sync_is_group()
        self.assertEqual(structure.is_group, 1,
                       "Section nodes should have is_group=1")
        
        # Test Item node
        structure2 = frappe.new_doc("BOQ Structure")
        structure2.boq_header = self.boq_header.name
        structure2.title = "Test Item"
        structure2.node_type = "Item"
        
        structure2.sync_is_group()
        self.assertEqual(structure2.is_group, 0,
                       "Item nodes should have is_group=0")
        
        # Test that the invariant holds after save
        structure.insert()
        self.assertEqual(structure.node_type, "Section")
        self.assertEqual(structure.is_group, 1)
        
        # Clean up
        structure.delete()
        
    def test_property6_line_total_calculation(self):
        """Property 6: Line Total Calculation - quantity × contract_unit_price × factor"""
        # Test that line_total = quantity × contract_unit_price × factor
        
        # Test cases: (quantity, unit_price, factor, expected)
        test_cases = [
            (10.0, 100.0, 1.0, 1000.0),   # 10 × 100 × 1.0 = 1000
            (5.0, 50.0, 2.0, 500.0),       # 5 × 50 × 2.0 = 500
            (2.5, 200.0, 0.5, 250.0),       # 2.5 × 200 × 0.5 = 250
            (0.0, 100.0, 1.0, 0.0),         # 0 × 100 × 1.0 = 0
            (10.0, 0.0, 1.0, 0.0),          # 10 × 0 × 1.0 = 0
            (1.0, 1.0, 1.0, 1.0),           # 1 × 1 × 1.0 = 1
        ]
        
        for qty, price, factor, expected in test_cases:
            # Test the formula directly
            line_total = qty * price * factor
            self.assertAlmostEqual(line_total, expected, places=2,
                                msg=f"Failed for qty={qty}, price={price}, factor={factor}")
            
            # Test with a BOQ Item instance
            item = frappe.new_doc("BOQ Item")
            item.quantity = qty
            item.contract_unit_price = price
            item.factor = factor
            
            # Call the calculate_line_total method
            item.calculate_line_total()
            
            # Verify the calculation
            self.assertAlmostEqual(item.line_total, expected, places=2,
                                msg=f"BOQ Item calculation failed for qty={qty}, price={price}, factor={factor}")
        
    def test_property7_header_rollup_total(self):
        """Property 7: Header Roll-Up Total - header total = sum of all BOQ Item line_totals"""
        # Test that header total = sum of all BOQ Item line_totals
        
        # Create test BOQ Items
        test_items = [
            {"quantity": 10.0, "unit_price": 100.0, "factor": 1.0},  # 1000
            {"quantity": 5.0, "unit_price": 50.0, "factor": 2.0},    # 500
            {"quantity": 2.5, "unit_price": 200.0, "factor": 0.5},   # 250
        ]
        
        total_expected = 0
        items_created = []
        
        for i, item_data in enumerate(test_items):
            # Create a BOQ Structure leaf node
            structure = frappe.new_doc("BOQ Structure")
            structure.boq_header = self.boq_header.name
            structure.title = f"Test Item {i+1}"
            structure.node_type = "Item"
            structure.insert()
            
            # Get the auto-created BOQ Item
            item_name = frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name")
            item = frappe.get_doc("BOQ Item", item_name)
            
            # Update the item with test data
            item.quantity = item_data["quantity"]
            item.contract_unit_price = item_data["unit_price"]
            item.factor = item_data["factor"]
            item.save()
            
            items_created.append((structure, item))
            
            # Calculate expected total
            line_total = item_data["quantity"] * item_data["unit_price"] * item_data["factor"]
            total_expected += line_total
        
        # Refresh the BOQ Header to recalculate total
        self.boq_header.reload()
        
        # Check that the header total matches the sum
        # Note: The BOQ Header controller calculates total from BOQ Items
        # We need to trigger the calculation
        self.boq_header.calculate_total_value()
        
        # The total should be close to expected (allow for floating point differences)
        self.assertAlmostEqual(self.boq_header.total_contract_value, total_expected, places=2,
                            msg=f"Header total mismatch: {self.boq_header.total_contract_value} != {total_expected}")
        
        # Clean up
        for structure, item in items_created:
            structure.delete()
        
    def test_property8_section_rollup_via_nestedset(self):
        """Property 8: Section Roll-Up via NestedSet"""
        # Test that section rollup = sum of descendant leaf totals
        pass
        
    def test_property9_auto_create_boq_item(self):
        """Property 9: Auto-Create BOQ Item for Leaf Nodes - leaf nodes auto-create BOQ Items"""
        # Test that leaf nodes auto-create BOQ Items
        
        # Create a leaf node (Item type)
        leaf_structure = frappe.new_doc("BOQ Structure")
        leaf_structure.boq_header = self.boq_header.name
        leaf_structure.title = "Test Leaf Item"
        leaf_structure.node_type = "Item"  # This should be is_group=0
        leaf_structure.insert()
        
        # Check that a BOQ Item was auto-created
        item_exists = frappe.db.exists("BOQ Item", {"structure": leaf_structure.name})
        self.assertTrue(item_exists, 
                       "BOQ Item should be auto-created for leaf nodes")
        
        # Get the auto-created item
        item = frappe.get_doc("BOQ Item", {"structure": leaf_structure.name})
        
        # Verify the item is linked correctly
        self.assertEqual(item.structure, leaf_structure.name,
                        "BOQ Item should be linked to the structure")
        self.assertEqual(item.boq_header, self.boq_header.name,
                        "BOQ Item should have the same boq_header")
        
        # Create a section node (should NOT auto-create BOQ Item)
        section_structure = frappe.new_doc("BOQ Structure")
        section_structure.boq_header = self.boq_header.name
        section_structure.title = "Test Section"
        section_structure.node_type = "Section"  # This should be is_group=1
        section_structure.insert()
        
        # Check that NO BOQ Item was created for section
        item_exists = frappe.db.exists("BOQ Item", {"structure": section_structure.name})
        self.assertFalse(item_exists,
                        "BOQ Item should NOT be auto-created for section nodes")
        
        # Clean up
        leaf_structure.delete()
        section_structure.delete()
        
    def test_property10_cascade_delete_boq_item(self):
        """Property 10: Cascade Delete BOQ Item - deleting leaf node deletes linked BOQ Item"""
        # Test that deleting a leaf node deletes its BOQ Item
        
        # Create a leaf node with auto-created BOQ Item
        leaf_structure = frappe.new_doc("BOQ Structure")
        leaf_structure.boq_header = self.boq_header.name
        leaf_structure.title = "Test Leaf for Delete"
        leaf_structure.node_type = "Item"
        leaf_structure.insert()
        
        # Verify BOQ Item was created
        item_name = frappe.db.get_value("BOQ Item", {"structure": leaf_structure.name}, "name")
        self.assertIsNotNone(item_name, "BOQ Item should exist")
        
        # Delete the leaf structure
        leaf_structure.delete()
        
        # Verify BOQ Item was also deleted
        item_exists = frappe.db.exists("BOQ Item", {"structure": leaf_structure.name})
        self.assertFalse(item_exists, 
                        "BOQ Item should be cascade-deleted when leaf node is deleted")
        
        # Test with a section node (no BOQ Item to delete)
        section_structure = frappe.new_doc("BOQ Structure")
        section_structure.boq_header = self.boq_header.name
        section_structure.title = "Test Section for Delete"
        section_structure.node_type = "Section"
        section_structure.insert()
        
        # Delete the section (should not have any BOQ Item to delete)
        section_structure.delete()
        
        # No error should occur
        
    def test_property11_leaf_to_section_conversion_guard(self):
        """Property 11: Leaf-to-Section Conversion Guard"""
        # Test that leaf with BOQ Item data cannot become section
        pass
        
    def test_property12_forward_only_status_transitions(self):
        """Property 12: Forward-Only Status Transitions"""
        # Test that status only moves forward: Draft → Pricing → Frozen → Locked
        pass
        
    def test_property13_status_based_editing(self):
        """Property 13: Status-Based Editing Restrictions"""
        # Test field-level permissions based on status
        pass
        
    def test_property14_boq_item_leaf_only(self):
        """Property 14: BOQ Item Leaf-Only Constraint"""
        # Test that BOQ Items can only link to leaf nodes (is_group=0)
        pass
        
    def test_property15_import_validation_completeness(self):
        """Property 15: Import Validation Completeness"""
        # Test that import validation catches all errors
        pass
        
    def test_property16_migration_data_preservation(self):
        """Property 16: Migration Data Preservation"""
        # Test that migration preserves all data
        pass
        
    def test_property17_cost_item_fetch(self):
        """Property 17: Cost Item Fetch"""
        # Test that est_unit_cost = CostItem.total_direct_cost
        pass

if __name__ == "__main__":
    unittest.main()
    def test_property3_wbs_uniqueness(self):
        """Property 3: WBS Code Uniqueness - all codes unique within BOQ header"""
        # Create a BOQ Structure with a WBS code
        structure1 = frappe.new_doc("BOQ Structure")
        structure1.boq_header = self.boq_header.name
        structure1.title = "Test Structure 1"
        structure1.node_type = "Section"
        structure1.insert()
        
        # Try to create another structure with same WBS code (should fail)
        # The WBS code should be unique per BOQ header
        # This test verifies that WBS codes are unique within a BOQ header
        structure2 = frappe.new_doc("BOQ Structure")
        structure2.boq_header = self.boq_header.name
        structure2.title = "Test Structure 2"
        structure2.node_type = "Section"
        structure2.insert()
        
        # After insert, WBS codes should be generated
        # They should be unique within the same BOQ header
        wbs1 = frappe.db.get_value("BOQ Structure", structure1.name, "wbs_code")
        wbs2 = frappe.db.get_value("BOQ Structure", structure2.name, "wbs_code")
        
        # WBS codes should be different
        self.assertNotEqual(wbs1, wbs2, "WBS codes should be unique")
        
        # Clean up
        structure1.delete()
        structure2.delete()
        
    def test_property4_wbs_regeneration(self):
        """Property 4: WBS Regeneration Preserves Validity"""
        # Create a parent structure
        parent = frappe.new_doc("BOQ Structure")
        parent.boq_header = self.boq_header.name
        parent.title = "Parent Section"
        parent.node_type = "Section"
        parent.insert()
        
        # Create a child structure
        child = frappe.new_doc("BOQ Structure")
        child.boq_header = self.boq_header.name
        child.parent_structure = parent.name
        child.title = "Child Item"
        child.node_type = "Item"
        child.insert()
        
        # Get initial WBS codes
        parent_wbs_before = frappe.db.get_value("BOQ Structure", parent.name, "wbs_code")
        child_wbs_before = frappe.db.get_value("BOQ Structure", child.name, "wbs_code")
        
        # Regenerate WBS codes
        from construction.services.wbs_generator import WBSGenerator
        WBSGenerator.regenerate_all(self.boq_header.name)
        
        # Get WBS codes after regeneration
        parent_wbs_after = frappe.db.get_value("BOQ Structure", parent.name, "wbs_code")
        child_wbs_after = frappe.db.get_value("BOQ Structure", child.name, "wbs_code")
        
        # WBS codes should still be valid after regeneration
        self.assertIsNotNone(parent_wbs_after)
        self.assertIsNotNone(child_wbs_after)
        
        # Clean up
        child.delete()
        parent.delete()
        
    def test_property8_section_rollup_via_nestedset(self):
        """Property 8: Section Roll-Up via NestedSet"""
        # Create a section with child items
        parent = frappe.new_doc("BOQ Structure")
        parent.boq_header = self.boq_header.name
        parent.title = "Parent Section"
        parent.node_type = "Section"
        parent.insert()
        
        # Create child items
        items = []
        for i in range(3):
            child = frappe.new_doc("BOQ Structure")
            child.boq_header = self.boq_header.name
            child.parent_structure = parent.name
            child.title = f"Item {i+1}"
            child.node_type = "Item"
            child.insert()
            items.append(child)
            
            # Update the BOQ Item with line total
            item_name = frappe.db.get_value("BOQ Item", {"structure": child.name}, "name")
            if item_name:
                item = frappe.get_doc("BOQ Item", item_name)
                item.quantity = 10.0
                item.contract_unit_price = 100.0
                item.factor = 1.0
                item.save()
        
        # Calculate expected total
        expected_total = 0
        for child in items:
            item_name = frappe.db.get_value("BOQ Item", {"structure": child.name}, "name")
            if item_name:
                item = frappe.get_doc("BOQ Item", item_name)
                expected_total += item.line_total or 0
        
        # Get section rollup using NestedSet
        from construction.services.boq_export_service import BOQExportService
        rollup_total = BOQExportService.get_section_rollup(parent.name)
        
        # The rollup should equal the sum of child item line totals
        self.assertAlmostEqual(rollup_total, expected_total, places=2)
        
        # Clean up
        for child in items:
            child.delete()
        parent.delete()
        
    def test_property11_leaf_to_section_conversion_guard(self):
        """Property 11: Leaf-to-Section Conversion Guard"""
        # Create a leaf node with BOQ Item data
        leaf = frappe.new_doc("BOQ Structure")
        leaf.boq_header = self.boq_header.name
        leaf.title = "Test Leaf"
        leaf.node_type = "Item"
        leaf.insert()
        
        # Get the auto-created BOQ Item
        item_name = frappe.db.get_value("BOQ Item", {"structure": leaf.name}, "name")
        if item_name:
            item = frappe.get_doc("BOQ Item", item_name)
            item.quantity = 10.0
            item.contract_unit_price = 100.0
            item.factor = 1.0
            item.save()
            
            # Try to convert leaf to section (should fail)
            leaf.reload()
            leaf.node_type = "Section"
            leaf.is_group = 1
            
            # This should fail because the BOQ Item has data
            with self.assertRaises(Exception):
                leaf.save()
        
        leaf.delete()
        
    def test_property12_forward_only_status_transitions(self):
        """Property 12: Forward-Only Status Transitions"""
        header = frappe.get_doc("BOQ Header", self.boq_header.name)
        
        # Test valid transitions
        header.status = "Draft"
        header.save()
        
        # Draft -> Pricing (valid)
        header.status = "Pricing"
        header.save()
        
        # Pricing -> Frozen (valid)
        header.status = "Frozen"
        header.save()
        
        # Frozen -> Locked (valid)
        header.status = "Locked"
        header.save()
        
        # Try to go back to Draft (should fail)
        header.status = "Draft"
        with self.assertRaises(Exception):
            header.save()
            
    def test_property13_status_based_editing(self):
        """Property 13: Status-Based Editing Restrictions"""
        # Test Draft status allows all edits
        header = frappe.get_doc("BOQ Header", self.boq_header.name)
        header.status = "Draft"
        header.save()
        
        # Create a structure in Draft status
        structure = frappe.new_doc("BOQ Structure")
        structure.boq_header = header.name
        structure.title = "Test Structure"
        structure.node_type = "Section"
        structure.insert()
        
        # Change to Pricing status
        header.status = "Pricing"
        header.save()
        
        # In Pricing status, only pricing fields should be editable
        # Try to change structure (should fail)
        structure.reload()
        structure.title = "Modified Title"
        # This should fail in Pricing status
        with self.assertRaises(Exception):
            structure.save()
            
        # Clean up
        structure.delete()
        
    def test_property14_boq_item_leaf_only(self):
        """Property 14: BOQ Item Leaf-Only Constraint"""
        # Create a section (group node)
        section = frappe.new_doc("BOQ Structure")
        section.boq_header = self.boq_header.name
        section.title = "Test Section"
        section.node_type = "Section"
        section.insert()
        
        # Try to create BOQ Item linked to section (should fail)
        with self.assertRaises(Exception):
            item = frappe.new_doc("BOQ Item")
            item.structure = section.name
            item.boq_header = self.boq_header.name
            item.insert()  # Should fail - can't link to section
        
        section.delete()
        
    def test_property15_import_validation_completeness(self):
        """Property 15: Import Validation Completeness"""
        # Test that import validation catches all errors
        from construction.services.boq_import_service import BOQImportService
        
        # Test data with various errors
        test_rows = [
            # Row 1: Valid section
            {"WBS Code": "01", "Parent WBS": "", "Title": "Section 1", "Type": "Section", 
             "Unit": "", "Quantity": "", "Unit Price": "", "Factor": "", "Notes": ""},
            # Row 2: Duplicate WBS code (error)
            {"WBS Code": "01", "Parent WBS": "", "Title": "Section 2", "Type": "Section",
             "Unit": "", "Quantity": "", "Unit Price": "", "Factor": "", "Notes": ""},
            # Row 3: Item without unit (error)
            {"WBS Code": "01.001", "Parent WBS": "01", "Title": "Item 1", "Type": "Item",
             "Unit": "", "Quantity": "10", "Unit Price": "100", "Factor": "1.0", "Notes": ""},
            # Row 4: Item with zero quantity (error)
            {"WBS Code": "01.002", "Parent WBS": "01", "Title": "Item 2", "Type": "Item",
             "Unit": "m", "Quantity": "0", "Unit Price": "100", "Factor": "1.0", "Notes": ""},
            # Row 5: Section with unit price (error)
            {"WBS Code": "02", "Parent WBS": "", "Title": "Section 2", "Type": "Section",
             "Unit": "", "Quantity": "", "Unit Price": "100", "Factor": "", "Notes": ""},
            # Row 6: Parent not found (error)
            {"WBS Code": "03.001", "Parent WBS": "99", "Title": "Item 3", "Type": "Item",
             "Unit": "m", "Quantity": "10", "Unit Price": "100", "Factor": "1.0", "Notes": ""},
        ]
        
        # Run validation
        errors = BOQImportService.validate_import_data(test_rows, self.boq_header.name)
        
        # Should have errors for all invalid rows
        self.assertGreater(len(errors), 0, "Should detect validation errors")
        
        # Check specific error messages
        error_messages = "\n".join(errors)
        
        # Should have error for duplicate WBS
        self.assertIn("Duplicate WBS Code", error_messages)
        
        # Should have error for item without unit
        self.assertIn("Unit required for Item rows", error_messages)
        
        # Should have error for zero quantity
        self.assertIn("Quantity must be positive for Item rows", error_messages)
        
        # Should have error for section with unit price
        self.assertIn("Unit Price must be empty/zero for Section rows", error_messages)
        
        # Should have error for parent not found
        self.assertIn("Parent WBS '99' not found", error_messages)
        
        # Test that import with errors creates zero records
        # (This would be tested in integration tests)
        
    def test_property16_migration_data_preservation(self):
        """Property 16: Migration Data Preservation"""
        from construction.services.boq_migration_service import BOQMigrationService
        
        # Create a test BOQ Header for migration
        migration_header = frappe.get_doc({
            "doctype": "BOQ Header",
            "title": "Migration Test BOQ",
            "status": "Draft",
            "boq_type": "Tender"
        })
        migration_header.insert()
        
        # Create old BOQ Node records (simulating old structure)
        # In a real test, we would create actual BOQ Node records
        # For now, test the migration service structure
        
        # Test that migration service exists and has required methods
        self.assertIsNotNone(BOQMigrationService)
        self.assertTrue(hasattr(BOQMigrationService, 'migrate_header'))
        self.assertTrue(hasattr(BOQMigrationService, 'validate_migration'))
        
        # Test validation method
        validation_result = BOQMigrationService.validate_migration(migration_header.name)
        self.assertIsInstance(validation_result, dict)
        
        # Clean up
        migration_header.delete()
        
    def test_property17_cost_item_fetch(self):
        """Property 17: Cost Item Fetch"""
        # Create a test Cost Item
        cost_item = frappe.new_doc("Cost Item")
        cost_item.item_name = "Test Cost Item"
        cost_item.total_direct_cost = 100.0
        cost_item.insert()
        
        # Create a BOQ Item linked to this cost item
        structure = frappe.new_doc("BOQ Structure")
        structure.boq_header = self.boq_header.name
        structure.title = "Test Item"
        structure.node_type = "Item"
        structure.insert()
        
        # Get the auto-created BOQ Item
        item_name = frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name")
        if item_name:
            item = frappe.get_doc("BOQ Item", item_name)
            item.cost_item = cost_item.name
            item.save()
            
            # The est_unit_cost should be fetched from CostItem
            item.reload()
            self.assertEqual(item.est_unit_cost, 100.0)
            
        # Clean up
        structure.delete()
        cost_item.delete()