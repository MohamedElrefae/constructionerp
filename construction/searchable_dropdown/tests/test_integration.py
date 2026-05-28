"""
Integration tests for Searchable Dropdown
Tests end-to-end flow from API to UI

Run with:
    bench --site [site] run-tests --module construction.searchable_dropdown.tests.test_integration
"""

import unittest

import frappe

from construction.searchable_dropdown.api.search import searchable_link_search


class TestSearchableDropdownIntegration(unittest.TestCase):
    """Integration tests for the searchable dropdown feature"""

    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests"""
        # Store original user
        cls.original_user = frappe.session.user

        # Create test accounts if they don't exist
        cls.create_test_accounts()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Restore original user
        frappe.set_user(cls.original_user)

    @classmethod
    def create_test_accounts(cls):
        """Create test account records"""
        test_accounts = [
            {
                "doctype": "Account",
                "account_name": "Test Cash Account Arabic",
                "account_name_ar": "حساب النقدية للاختبار",
                "account_number": "9991",
                "account_type": "Cash",
                "is_group": 0,
            },
            {
                "doctype": "Account",
                "account_name": "Test Bank Account",
                "account_name_ar": "حساب البنك للاختبار",
                "account_number": "9992",
                "account_type": "Bank",
                "is_group": 0,
            },
            {
                "doctype": "Account",
                "account_name": "Test Group Account",
                "account_number": "9990",
                "account_type": "",
                "is_group": 1,
            },
        ]

        for acc in test_accounts:
            # Check if account exists
            existing = frappe.db.exists("Account", {"account_number": acc["account_number"]})
            if not existing:
                try:
                    # Create company first if needed
                    if not frappe.db.exists("Company", "_Test Company"):
                        frappe.get_doc(
                            {
                                "doctype": "Company",
                                "company_name": "_Test Company",
                                "abbr": "_TC",
                                "default_currency": "USD",
                            }
                        ).insert()

                    acc["company"] = "_Test Company"
                    doc = frappe.get_doc(acc)
                    doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                except Exception as e:
                    print(f"Warning: Could not create test account: {e}")

    def test_end_to_end_search_flow(self):
        """Test complete search flow"""
        # Search by Arabic name
        results = searchable_link_search(
            doctype="Account",
            txt="النقدية",
            search_fields=["account_name", "account_name_ar", "account_number"],
            display_format="{account_number} - {account_name_ar}",
            page_length=10,
        )

        self.assertIsInstance(results, list)

        # Check that results have the expected format
        for result in results:
            self.assertIn("value", result)
            self.assertIn("label", result)
            self.assertIsInstance(result["label"], str)

            # Verify format contains separator
            if " - " in result["label"]:
                parts = result["label"].split(" - ")
                self.assertEqual(len(parts), 2, "Label should have code and name parts")

    def test_search_with_company_filter(self):
        """Test search respects company filter"""
        results = searchable_link_search(
            doctype="Account",
            txt="999",  # Test account numbers start with 999
            filters={"company": "_Test Company", "is_group": 0},
            search_fields=["account_name", "account_number"],
            display_format="{account_number} - {account_name}",
            page_length=10,
        )

        self.assertIsInstance(results, list)

        # All results should be from _Test Company and not groups
        for result in results:
            # Verify account exists with these properties
            account = frappe.db.get_value("Account", result["value"], ["company", "is_group"], as_dict=True)
            if account:
                self.assertEqual(account.company, "_Test Company")
                self.assertEqual(account.is_group, 0)

    def test_search_performance(self):
        """Test search performance"""
        import time

        start = time.time()
        results = searchable_link_search(
            doctype="Account", txt="test", search_fields=["account_name", "account_name_ar"], page_length=20
        )
        end = time.time()

        duration = end - start

        # Should complete in under 500ms
        self.assertLess(duration, 0.5, f"Search took {duration}s, expected < 0.5s")

        print(f"Search performance: {duration:.3f}s")

    def test_concurrent_searches(self):
        """Test multiple rapid searches don't cause issues"""
        search_terms = ["test", "cash", "bank", "عربي", "999"]

        for term in search_terms:
            results = searchable_link_search(
                doctype="Account",
                txt=term,
                search_fields=["account_name", "account_name_ar", "account_number"],
                page_length=10,
            )

            self.assertIsInstance(results, list)

    def test_search_returns_empty_for_no_matches(self):
        """Test empty result set for non-existent search"""
        results = searchable_link_search(
            doctype="Account", txt="xyznonexistent12345", search_fields=["account_name"], page_length=10
        )

        self.assertEqual(len(results), 0, "Should return empty list for no matches")


class TestSearchableDropdownPermissions(unittest.TestCase):
    """Permission-related integration tests"""

    def test_user_without_read_permission(self):
        """Test user without read permission gets empty results"""
        # Create a test user with no Account permissions
        if not frappe.db.exists("User", "test_no_account_perm@example.com"):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_no_account_perm@example.com",
                    "first_name": "Test",
                    "enabled": 1,
                }
            )
            user.insert(ignore_permissions=True)

            # Remove all Account permissions
            for perm in frappe.get_all(
                "User Permission", filters={"user": "test_no_account_perm@example.com", "allow": "Account"}
            ):
                frappe.delete_doc("User Permission", perm.name)

            frappe.db.commit()

        # Switch to test user
        frappe.set_user("test_no_account_perm@example.com")

        try:
            results = searchable_link_search(doctype="Account", txt="cash", search_fields=["account_name"])

            # Should return empty list
            self.assertEqual(len(results), 0)

        finally:
            # Restore admin
            frappe.set_user("Administrator")


# Run tests if executed directly
if __name__ == "__main__":
    frappe.init(site="localhost")
    frappe.connect()

    try:
        unittest.main(verbosity=2)
    finally:
        frappe.destroy()
