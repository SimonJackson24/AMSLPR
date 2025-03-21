
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Integration tests for the authentication system.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.web.app import create_app
from src.utils.user_management import UserManager

class TestAuthIntegration(unittest.TestCase):
    """
    Integration tests for the authentication system.
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
        
        # Create Flask test client
        app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test_key',
            'USER_CONFIG_FILE': self.temp_file.name
        })
        
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """
        Clean up the test environment.
        """
        # Remove temporary config file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
        
        # Pop app context
        self.app_context.pop()
    
    def test_login_success(self):
        """
        Test successful login.
        """
        # Login with valid credentials
        response = self.client.post('/auth/login', data={
            'username': 'test_admin',
            'password': 'admin123'
        }, follow_redirects=True)
        
        # Check if login was successful
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
    
    def test_login_failure(self):
        """
        Test failed login.
        """
        # Login with invalid credentials
        response = self.client.post('/auth/login', data={
            'username': 'test_admin',
            'password': 'wrong_password'
        }, follow_redirects=True)
        
        # Check if login failed
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)
    
    def test_logout(self):
        """
        Test logout.
        """
        # Login
        self.client.post('/auth/login', data={
            'username': 'test_admin',
            'password': 'admin123'
        })
        
        # Logout
        response = self.client.get('/auth/logout', follow_redirects=True)
        
        # Check if logout was successful
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    
    def test_protected_route_with_auth(self):
        """
        Test accessing a protected route with authentication.
        """
        # Login
        self.client.post('/auth/login', data={
            'username': 'test_admin',
            'password': 'admin123'
        })
        
        # Access protected route
        response = self.client.get('/cameras')
        
        # Check if access was granted
        self.assertEqual(response.status_code, 200)
    
    def test_protected_route_without_auth(self):
        """
        Test accessing a protected route without authentication.
        """
        # Access protected route without login
        response = self.client.get('/cameras', follow_redirects=True)
        
        # Check if access was denied and redirected to login
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    
    def test_admin_route_with_admin(self):
        """
        Test accessing an admin route with admin role.
        """
        # Login as admin
        self.client.post('/auth/login', data={
            'username': 'test_admin',
            'password': 'admin123'
        })
        
        # Access admin route
        response = self.client.get('/auth/users')
        
        # Check if access was granted
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'User Management', response.data)
    
    def test_admin_route_with_operator(self):
        """
        Test accessing an admin route with operator role.
        """
        # Login as operator
        self.client.post('/auth/login', data={
            'username': 'test_operator',
            'password': 'operator123'
        })
        
        # Access admin route
        response = self.client.get('/auth/users', follow_redirects=True)
        
        # Check if access was denied
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()
