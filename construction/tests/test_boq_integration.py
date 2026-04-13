# Integration tests for BOQ
"""
Integration tests for BOQ Tree Architecture
Tests the full integration of BOQ components
"""

import frappe
import unittest
import json

class TestBOQIntegration(unittest.TestCase):
    """Integration tests for BOQ Tree Architecture"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test BOQ Header
        self.boq_header = frappe.get_doc({
            "doctype": "BOQ Header",
            "title": "Test BOQ Integration",
            "status": "Draft",
            "boq_type": "Tender"
        })
        self.boq_header.insert()
        
    def tearDown(self):
        """Clean up test data"""
        frappe.db.rollback()
        
    def test_1_boq_structure_creation(self):
        """Test creating BOQ Structure tree"""
        # Create a root section
        root_section = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": self.boq_header.name,
            "title": "Root Section",
            "node_type": "Section",
            "parent_structure": None
        })
        root_section.insert()
        
        # Create a child item
        child_item = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": self.boq_header.name,
            "title": "Test Item",
            "node_type": "Item",
            "parent_structure": root_section.name
        })
        child_item.insert()
        
        # Verify the structure
        self.assertEqual(child_item.parent_structure, root_section.name)
        self.assertEqual(child_item.boq_header, self.boq_header.name)
        
    def test_2_boq_item_auto_creation(self):
        """Test auto-creation of BOQ Item for leaf nodes"""
        # Create a leaf node
        leaf_node = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": self.boq_header.name,
            "title": "Test Leaf",
            "node_type": "Item"
        })
        leaf_node.insert()
        
        # Check if BOQ Item was auto-created
        boq_items = frappe.get_all("BOQ Item", filters={"structure": leaf_node.name})
        self.assertEqual(len(boq_items), 1, "BOQ Item should be auto-created for leaf nodes")
        
    def test_3_status_transitions(self):
        """Test BOQ status machine"""
        header = frappe.get_doc("BOQ Header", self.boq_header.name)
        
        # Test Draft -> Pricing
        header.status = "Pricing"
        header.save()
        self.assertEqual(header.status, "Pricing")
        
        # Test Pricing -> Frozen
        header.status = "Frozen"
        header.save()
        self.assertEqual(header.status, "Frozen")
        
        # Test Frozen -> Locked
        header.status = "Locked"
        header.save()
        self.assertEqual(header.status, "Locked")
        
    def test_4_rollup_calculation(self):
        """Test rollup calculations"""
        # Create a structure with items
        root = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": self.boq_header.name,
            "title": "Root Section",
            "node_type": "Section"
        })
        root.insert()
        
        # Create leaf with BOQ Item
        leaf = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": self.boq_header.name,
            "title": "Test Item",
            "node_type": "Item",
            "parent_structure": root.name
        })
        leaf.insert()
        
        # Update BOQ Item with values
        boq_items = frappe.get_all("BOQ Item", filters={"structure": leaf.name})
        if boq_items:
            item = frappe.get_doc("BOQ Item", boq_items[0].name)
            item.quantity = 10
            item.contract_unit_price = 100
            item.factor = 1.0
            item.save()
            
            # Check header total
            header = frappe.get_doc("BOQ Header", self.boq_header.name)
            header.calculate_total_value()
            self.assertEqual(header.total_contract_value, 1000)  # 10 * 100 * 1.0
            
    def test_5_wbs_code_generation(self):
        """Test WBS code generation"""
        from construction.services.wbs_generator import WBSGenerator
        
        # Create a structure
        structure = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": self.boq_header.name,
            "title": "Test Structure",
            "node_type": "Section"
        })
        structure.insert()
        
        # Check that WBS code was generated
        self.assertIsNotNone(structure.wbs_code)
        self.assertTrue(structure.wbs_code)
        
    def test_6_import_export_workflow(self):
        """Test import and export workflow"""
        # This would test the full import/export cycle
        # For now, just verify services exist
        from construction.services.boq_import_service import BOQImportService
        from construction.services.boq_export_service import BOQExportService
        
        self.assertIsNotNone(BOQImportService)
        self.assertIsNotNone(BOQExportService)
        
    def test_7_migration_workflow(self):
        """Test migration from old structure"""
        from construction.services.boq_migration_service import BOQMigrationService
        
        # Test that migration service exists
        migration_service = BOQMigrationService()
        self.assertIsNotNone(migration_service)
        
    def test_8_performance_large_tree(self):
        """Test performance with large tree (simulated)"""
        # Create a moderately sized tree
        for i in range(10):  # Create 10 sections
            section = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": self.boq_header.name,
                "title": f"Section {i}",
                "node_type": "Section"
            })
            section.insert()
            
            # Add 5 items to each section
            for j in range(5):
                item = frappe.get_doc({
                    "doctype": "BOQ Structure",
                    "boq_header": self.boq_header.name,
                    "title": f"Item {i}-{j}",
                    "node_type": "Item",
                    "parent_structure": section.name
                })
                item.insert()
        
        # Verify all items were created
        total_items = frappe.db.count("BOQ Structure", filters={"boq_header": self.boq_header.name})
        self.assertEqual(total_items, 60)  # 10 sections + 50 items = 60 total
        
    def test_9_status_based_permissions(self):
        """Test that status changes affect permissions"""
        header = frappe.get_doc("BOQ Header", self.boq_header.name)
        
        # In Draft status, we should be able to edit
        header.status = "Draft"
        header.save()
        
        # Create a structure in Draft
        structure = frappe.get_doc({
            "doctype": "BOQ Structure",
            "boq_header": header.name,
            "title": "Test Structure",
            "node_type": "Section"
        })
        structure.insert()
        
        # Change to Pricing - should not allow structural changes
        header.status = "Pricing"
        header.save()
        
        # Try to modify structure - should fail
        with self.assertRaises(Exception):
            structure.title = "Modified"
            structure.save()
            
    def test_10_rollup_calculation_performance(self):
        """Test performance of rollup calculations"""
        import time
        
        # Create a moderately complex structure
        start_time = time.time()
        
        # Create 100 items
        for i in range(100):
            item = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": self.boq_header.name,
                "title": f"Test Item {i}",
                "node_type": "Item"
            })
            item.insert()
            
            # Update BOQ Item with values
            boq_items = frappe.get_all("BOQ Item", 
                                     filters={"structure": item.name},
                                     fields=["name"])
            if boq_items:
                boq_item = frappe.get_doc("BOQ Item", boq_items[0].name)
                boq_item.quantity = 10
                boq_item.contract_unit_price = 100
                boq_item.factor = 1.0
                boq_item.save()
        
        # Calculate total
        header = frappe.get_doc("BOQ Header", self.boq_header.name)
        header.calculate_total_value()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance check: should complete in reasonable time
        self.assertLess(execution_time, 5.0, 
                      f"Rollup calculation took {execution_time:.2f} seconds, should be < 5s")
        
        print(f"Rollup calculation for 100 items took {execution_time:.2f} seconds")
        
if __name__ == "__main__":
    unittest.main()