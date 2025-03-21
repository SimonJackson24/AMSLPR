
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import os
from src.web.app import create_app
from src.config.settings import load_config
from src.db.manager import DatabaseManager
from src.utils.user_management import UserManager
from src.recognition.detector import LicensePlateDetector

class TestParkingRoutes(unittest.TestCase):
    def setUp(self):
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        config = load_config(config_path)
        
        # Create database manager
        db_path = os.path.join(os.path.dirname(__file__), 'test_database.db')
        db_manager = DatabaseManager(db_path)
        
        # Create detector
        detector = LicensePlateDetector(config.get('recognition', {}))
        
        # Create a test client
        self.app = create_app(config, db_manager, detector)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # Login
        with self.app.app_context():
            # Create a test user
            user_manager = self.app.config.get('USER_MANAGER')
            if user_manager and 'admin' not in user_manager.users:
                user_manager.add_user('admin', 'admin', 'admin')
            
        # Login
        self.client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin'
        }, follow_redirects=True)
    
    def test_parking_dashboard(self):
        # Test parking dashboard
        response = self.client.get('/parking/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        print("Parking dashboard test passed")
    
    def test_parking_sessions(self):
        # Test parking sessions
        response = self.client.get('/parking/sessions', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        print("Parking sessions test passed")
    
    def test_parking_reports(self):
        # Test parking reports
        print("Testing parking reports route...")
        response = self.client.get('/parking/reports', follow_redirects=True)
        print(f"Response status code: {response.status_code}")
        print(f"Response data length: {len(response.data)}")
        
        # Check for error messages in the response
        if b'error' in response.data.lower():
            print("Error found in response:")
            error_start = response.data.lower().find(b'error')
            error_context = response.data[error_start:error_start+200]
            print(error_context)
        
        self.assertEqual(response.status_code, 200)
        print("Parking reports test passed")
    
    def test_parking_settings(self):
        # Test parking settings
        response = self.client.get('/parking/settings', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        print("Parking settings test passed")
    
    def test_nayax_pricing(self):
        # Test nayax pricing
        response = self.client.get('/parking/nayax-pricing', follow_redirects=False)
        # Either 200 (if Nayax is enabled) or 302 (redirect if Nayax is not enabled)
        self.assertIn(response.status_code, [200, 302])
        
        # If redirected, follow the redirect and ensure we end up at a valid page
        if response.status_code == 302:
            redirect_response = self.client.get(response.location, follow_redirects=True)
            self.assertEqual(redirect_response.status_code, 200)
            
        print("Nayax pricing test passed")
    
    def test_export_data(self):
        # Test export data CSV
        response = self.client.get('/parking/export?format=csv', follow_redirects=False)
        # Either 200 (if data available) or 302 (redirect if no data)
        self.assertIn(response.status_code, [200, 302])
        
        # If redirected, follow the redirect and ensure we end up at a valid page
        if response.status_code == 302:
            redirect_response = self.client.get(response.location, follow_redirects=True)
            self.assertEqual(redirect_response.status_code, 200)
        
        # Test export data Excel
        response = self.client.get('/parking/export?format=excel', follow_redirects=False)
        # Either 200 (if data available) or 302 (redirect if no data)
        self.assertIn(response.status_code, [200, 302])
        
        # If redirected, follow the redirect and ensure we end up at a valid page
        if response.status_code == 302:
            redirect_response = self.client.get(response.location, follow_redirects=True)
            self.assertEqual(redirect_response.status_code, 200)
        
        print("Export data test passed")

if __name__ == '__main__':
    unittest.main()
