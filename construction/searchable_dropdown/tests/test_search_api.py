"""
Unit tests for searchable_link_search API
Run with: bench --site [site] run-tests --module construction.searchable_dropdown.tests.test_search_api
"""

import frappe
import unittest
from construction.searchable_dropdown.api.search import searchable_link_search, _format_label


class TestSearchableLinkSearch(unittest.TestCase):
    """Test cases for searchable_link_search function"""
    
    def setUp(self):
        """Set up test data"""
        self.test_doctype = "Account"  # Use existing DocType for testing
        
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    def test_search_by_code(self):
        """Test searching by code field returns results"""
        # This test assumes you have Account doctype with account_code field
        # Modify based on your actual doctype structure
        results = searchable_link_search(
            doctype=self.test_doctype,
            txt="1",  # Search for accounts starting with 1
            search_fields=["account_name", "account_number"],
            display_format="{account_number} - {account_name}",
            page_length=10
        )
        
        # Should return list (may be empty if no data, but shouldn't error)
        self.assertIsInstance(results, list)
        
        # If results exist, check format
        if results:
            self.assertIn("value", results[0])
            self.assertIn("label", results[0])
            
    def test_search_by_name(self):
        """Test searching by name field works"""
        results = searchable_link_search(
            doctype=self.test_doctype,
            txt="Cash",  # Common account name
            search_fields=["account_name"],
            display_format="{account_name}",
            page_length=5
        )
        
        self.assertIsInstance(results, list)
        
        # Verify label format
        for result in results:
            self.assertIn("value", result)
            self.assertIn("label", result)
            self.assertIsInstance(result["label"], str)
            
    def test_respects_permissions(self):
        """Test that search respects user permissions"""
        # Create a test user without permissions (or use Guest)
        frappe.set_user("Guest")
        
        try:
            results = searchable_link_search(
                doctype=self.test_doctype,
                txt="test",
                search_fields=["account_name"]
            )
            
            # Should return empty list, not throw error
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 0)
            
        finally:
            # Restore admin user
            frappe.set_user("Administrator")
            
    def test_format_label_with_code_and_name(self):
        """Test label formatting with code and name"""
        doc = {
            "name": "ACC-001",
            "account_code": "1000",
            "account_name": "Cash Account"
        }
        
        label = _format_label(
            doc, 
            "{account_code} - {account_name}",
            ["account_code", "account_name"]
        )
        
        self.assertEqual(label, "1000 - Cash Account")
        
    def test_format_label_fallback_to_name(self):
        """Test label falls back to name if format fails"""
        doc = {
            "name": "ACC-001"
        }
        
        # Try format with non-existent field
        label = _format_label(
            doc,
            "{nonexistent} - {name}",
            ["name"]
        )
        
        # Should return formatted string or name
        self.assertIsInstance(label, str)
        self.assertTrue(len(label) > 0)
        
    def test_format_label_empty_doc(self):
        """Test label formatting with empty doc"""
        doc = {}
        
        label = _format_label(
            doc,
            "{code} - {name}",
            ["code", "name"]
        )
        
        # Should handle gracefully
        self.assertIsInstance(label, str)
        
    def test_search_with_filters(self):
        """Test that base filters are respected"""
        results = searchable_link_search(
            doctype=self.test_doctype,
            txt="",
            filters={"is_group": 0},  # Only leaf accounts
            search_fields=["account_name"],
            page_length=5
        )
        
        self.assertIsInstance(results, list)
        # Can't verify filter was applied without checking actual data,
        # but ensures no error occurs
        
    def test_search_empty_txt_returns_results(self):
        """Test empty search text returns standard results"""
        results = searchable_link_search(
            doctype=self.test_doctype,
            txt="",
            search_fields=["account_name"],
            page_length=5
        )
        
        self.assertIsInstance(results, list)
        # Should return some results if data exists
        
    def test_search_respects_page_length(self):
        """Test page_length parameter limits results"""
        results = searchable_link_search(
            doctype=self.test_doctype,
            txt="",
            search_fields=["account_name"],
            page_length=3
        )
        
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)
        
    def test_search_special_characters(self):
        """Test search handles special characters gracefully"""
        results = searchable_link_search(
            doctype=self.test_doctype,
            txt="%_test'\"",  # SQL special characters
            search_fields=["account_name"],
            page_length=5
        )
        
        # Should not throw error
        self.assertIsInstance(results, list)


class TestGetRecentItems(unittest.TestCase):
    """Test cases for get_recent_items function"""
    
    def test_get_recent_items_returns_list(self):
        """Test get_recent_items returns a list"""
        from construction.searchable_dropdown.api.search import get_recent_items
        
        results = get_recent_items("Account", limit=5)
        
        self.assertIsInstance(results, list)
        
        if results:
            self.assertIn("value", results[0])
            self.assertIn("label", results[0])
            
    def test_get_recent_items_respects_limit(self):
        """Test limit parameter works"""
        from construction.searchable_dropdown.api.search import get_recent_items
        
        results = get_recent_items("Account", limit=3)
        
        self.assertLessEqual(len(results), 3)


def run_tests():
    """Run all tests and print results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSearchableLinkSearch))
    suite.addTests(loader.loadTestsFromTestCase(TestGetRecentItems))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    frappe.init(site="localhost")
    frappe.connect()
    
    try:
        success = run_tests()
        exit(0 if success else 1)
    finally:
        frappe.destroy()
