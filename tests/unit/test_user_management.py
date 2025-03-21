
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Unit tests for the user management module.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.utils.user_management import UserManager

class TestUserManagement(unittest.TestCase):
    """
    Unit tests for the UserManager class.
    """
    
    def setUp(self):
        """
        Set up the test environment.
        """
        # Create a temporary config file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        
        # Create user manager
        self.user_manager = UserManager(config_file=self.temp_file.name)
        
        # Add test users
        self.user_manager.add_user(
            username='test_admin',
            password='admin123',
            role='admin',
            name='Test Admin',
            email='admin@example.com'
        )
        
        self.user_manager.add_user(
            username='test_operator',
            password='operator123',
            role='operator',
            name='Test Operator',
            email='operator@example.com'
        )
        
        self.user_manager.add_user(
            username='test_viewer',
            password='viewer123',
            role='viewer',
            name='Test Viewer',
            email='viewer@example.com'
        )
    
    def tearDown(self):
        """
        Clean up the test environment.
        """
        # Remove temporary config file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_user_creation(self):
        """
        Test user creation.
        """
        # Get all users
        users = self.user_manager.get_users()
        
        # Check if test users were created
        self.assertIn('test_admin', users)
        self.assertIn('test_operator', users)
        self.assertIn('test_viewer', users)
        
        # Check user roles
        self.assertEqual(users['test_admin']['role'], 'admin')
        self.assertEqual(users['test_operator']['role'], 'operator')
        self.assertEqual(users['test_viewer']['role'], 'viewer')
    
    def test_authentication(self):
        """
        Test user authentication.
        """
        # Test valid authentication
        user = self.user_manager.authenticate('test_admin', 'admin123')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'test_admin')
        self.assertEqual(user['role'], 'admin')
        
        # Test invalid password
        user = self.user_manager.authenticate('test_admin', 'wrong_password')
        self.assertIsNone(user)
        
        # Test nonexistent user
        user = self.user_manager.authenticate('nonexistent_user', 'password')
        self.assertIsNone(user)
    
    def test_permissions(self):
        """
        Test permission checking.
        """
        # Test admin permissions
        self.assertTrue(self.user_manager.has_permission('test_admin', 'view'))
        self.assertTrue(self.user_manager.has_permission('test_admin', 'edit'))
        self.assertTrue(self.user_manager.has_permission('test_admin', 'admin'))
        
        # Test operator permissions
        self.assertTrue(self.user_manager.has_permission('test_operator', 'view'))
        self.assertTrue(self.user_manager.has_permission('test_operator', 'edit'))
        self.assertFalse(self.user_manager.has_permission('test_operator', 'admin'))
        
        # Test viewer permissions
        self.assertTrue(self.user_manager.has_permission('test_viewer', 'view'))
        self.assertFalse(self.user_manager.has_permission('test_viewer', 'edit'))
        self.assertFalse(self.user_manager.has_permission('test_viewer', 'admin'))
        
        # Test nonexistent user
        self.assertFalse(self.user_manager.has_permission('nonexistent_user', 'view'))
    
    def test_user_update(self):
        """
        Test user update.
        """
        # Update test user
        success = self.user_manager.update_user(
            'test_operator',
            name='Updated Operator',
            email='updated_operator@example.com'
        )
        
        self.assertTrue(success)
        
        # Check if user was updated
        user = self.user_manager.get_user('test_operator')
        self.assertEqual(user['name'], 'Updated Operator')
        self.assertEqual(user['email'], 'updated_operator@example.com')
        
        # Update password
        success = self.user_manager.update_user(
            'test_operator',
            password='new_password'
        )
        
        self.assertTrue(success)
        
        # Test authentication with new password
        user = self.user_manager.authenticate('test_operator', 'new_password')
        self.assertIsNotNone(user)
    
    def test_user_deletion(self):
        """
        Test user deletion.
        """
        # Delete test user
        success = self.user_manager.delete_user('test_viewer')
        self.assertTrue(success)
        
        # Check if user was deleted
        users = self.user_manager.get_users()
        self.assertNotIn('test_viewer', users)
        
        # Test deleting nonexistent user
        success = self.user_manager.delete_user('nonexistent_user')
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
