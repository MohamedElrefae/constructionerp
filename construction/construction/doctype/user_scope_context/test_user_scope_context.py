"""
DEL-001 Automated Tests
All 8 Acceptance Criteria
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime


class TestUserScopeContext(FrappeTestCase):
    """Test suite for DEL-001: User Scope Context DocType"""
    
    def setUp(self):
        """Set up test data"""
        self.test_company = "_Test Company"
        self.test_user = "_test_user@example.com"
        
        # Create test company if not exists
        if not frappe.db.exists("Company", self.test_company):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": self.test_company,
                "default_currency": "USD",
                "country": "United States"
            })
            company.insert(ignore_permissions=True)
        
        # Create test user if not exists
        if not frappe.db.exists("User", self.test_user):
            user = frappe.get_doc({
                "doctype": "User",
                "email": self.test_user,
                "first_name": "Test",
                "enabled": 1
            })
            user.insert(ignore_permissions=True)
    
    def tearDown(self):
        """Clean up test data"""
        # Delete test records
        if frappe.db.exists("User Scope Context", {"user": self.test_user}):
            frappe.db.delete("User Scope Context", {"user": self.test_user})
    
    # =================================================================
    # AC-001: DocType exists in Admin > DocType list
    # =================================================================
    def test_01_doctype_exists(self):
        """AC-001: DocType exists in Admin > DocType list"""
        doctype_exists = frappe.db.exists("DocType", "User Scope Context")
        self.assertTrue(doctype_exists, "User Scope Context DocType should exist")
        
        # Verify DocType is not single
        is_single = frappe.db.get_value("DocType", "User Scope Context", "issingle")
        self.assertFalse(is_single, "User Scope Context should not be a Single DocType")
    
    # =================================================================
    # AC-002: Creating record with valid user and company succeeds
    # =================================================================
    def test_02_create_valid_record(self):
        """AC-002: Creating record with valid user and company succeeds"""
        doc = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc.insert(ignore_permissions=True)
        
        self.assertTrue(doc.name, "Record should be created with a name")
        self.assertEqual(doc.user, self.test_user)
        self.assertEqual(doc.company, self.test_company)
    
    # =================================================================
    # AC-003: Creating duplicate record for same user fails
    # =================================================================
    def test_03_duplicate_user_fails(self):
        """AC-003: Creating duplicate record for same user fails with unique constraint"""
        # Create first record
        doc1 = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc1.insert(ignore_permissions=True)
        
        # Try to create duplicate - should fail
        with self.assertRaises(frappe.DuplicateEntryError):
            doc2 = frappe.get_doc({
                "doctype": "User Scope Context",
                "user": self.test_user,
                "company": self.test_company
            })
            doc2.insert(ignore_permissions=True)
    
    # =================================================================
    # AC-004: Saving increments scope_version
    # =================================================================
    def test_04_scope_version_increments(self):
        """AC-004: Saving increments scope_version"""
        doc = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc.insert(ignore_permissions=True)
        
        initial_version = doc.scope_version
        self.assertEqual(initial_version, 1, "Initial version should be 1")
        
        # Save again
        doc.save(ignore_permissions=True)
        
        self.assertEqual(doc.scope_version, 2, "Version should increment to 2")
        
        # Save once more
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.scope_version, 3, "Version should increment to 3")
    
    # =================================================================
    # AC-005: last_active_at auto-populates on save
    # =================================================================
    def test_05_last_active_at_populates(self):
        """AC-005: last_active_at auto-populates on save"""
        before_create = now_datetime()
        
        doc = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc.insert(ignore_permissions=True)
        
        self.assertIsNotNone(doc.last_active_at, "last_active_at should be populated")
        self.assertTrue(
            doc.last_active_at >= before_create,
            "last_active_at should be set to current time"
        )
    
    # =================================================================
    # AC-006: Track Changes creates version history
    # =================================================================
    def test_06_track_changes_enabled(self):
        """AC-006: Track Changes creates version history"""
        # Check DocType has track_changes enabled
        track_changes = frappe.db.get_value("DocType", "User Scope Context", "track_changes")
        self.assertTrue(track_changes, "Track Changes should be enabled on DocType")
        
        # Create and modify a record
        doc = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc.insert(ignore_permissions=True)
        
        # Modify and save
        doc.company = self.test_company  # Same value but should trigger track
        doc.save(ignore_permissions=True)
        
        # Check version history exists
        versions = frappe.get_all(
            "Version",
            filters={"ref_doctype": "User Scope Context", "docname": doc.name},
            fields=["name"]
        )
        self.assertTrue(len(versions) > 0, "Version history should be created")
    
    # =================================================================
    # AC-007: Non-System Manager cannot read another user's record
    # =================================================================
    def test_07_non_admin_permission_restriction(self):
        """AC-007: Non-System Manager cannot read another user's record"""
        # Create a record for test_user
        doc = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc.insert(ignore_permissions=True)
        
        # Create another test user
        other_user = "_other_test@example.com"
        if not frappe.db.exists("User", other_user):
            user = frappe.get_doc({
                "doctype": "User",
                "email": other_user,
                "first_name": "Other",
                "enabled": 1
            })
            user.insert(ignore_permissions=True)
        
        # Check permissions - other user should not have read access
        has_read = frappe.has_permission(
            "User Scope Context",
            "read",
            doc=doc,
            user=other_user
        )
        self.assertFalse(has_read, "Other user should not have read permission")
    
    # =================================================================
    # AC-008: Cross-dimension validation rejects mismatched branch/company
    # =================================================================
    def test_08_cross_dimension_validation(self):
        """AC-008: Cross-dimension validation rejects mismatched branch/company"""
        # Create another company and branch
        other_company = "_Other Test Company"
        if not frappe.db.exists("Company", other_company):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": other_company,
                "default_currency": "USD",
                "country": "United States"
            })
            company.insert(ignore_permissions=True)
        
        # Create a branch for the other company
        other_branch = "_Test Branch Other"
        if not frappe.db.exists("Branch", other_branch):
            branch = frappe.get_doc({
                "doctype": "Branch",
                "branch": other_branch,
                "company": other_company
            })
            branch.insert(ignore_permissions=True)
        
        # Try to create context with mismatched branch/company
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc({
                "doctype": "User Scope Context",
                "user": self.test_user,
                "company": self.test_company,  # Main test company
                "branch": other_branch          # Branch from other company
            })
            doc.insert(ignore_permissions=True)
    
    # =================================================================
    # Additional Tests
    # =================================================================
    def test_required_fields(self):
        """Test that user and company are required"""
        with self.assertRaises(frappe.MandatoryError):
            doc = frappe.get_doc({
                "doctype": "User Scope Context",
                "company": self.test_company
                # Missing user
            })
            doc.insert(ignore_permissions=True)
        
        with self.assertRaises(frappe.MandatoryError):
            doc = frappe.get_doc({
                "doctype": "User Scope Context",
                "user": self.test_user
                # Missing company
            })
            doc.insert(ignore_permissions=True)
    
    def test_owner_can_modify_own_record(self):
        """Test that record owner can modify their own record"""
        doc = frappe.get_doc({
            "doctype": "User Scope Context",
            "user": self.test_user,
            "company": self.test_company
        })
        doc.insert(ignore_permissions=True)
        
        # Owner should have write permission
        has_write = frappe.has_permission(
            "User Scope Context",
            "write",
            doc=doc,
            user=self.test_user
        )
        self.assertTrue(has_write, "Owner should have write permission")
