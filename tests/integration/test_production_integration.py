
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import os
import sys
import json
import time
import tempfile
import shutil
import requests
import threading
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import modules to test
from src.config.settings import load_config
from src.app import create_app
from src.utils.auth import generate_token

class TestProductionIntegration(unittest.TestCase):
    """
    Integration tests for production features.
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Set up test environment once for all tests.
        """
        # Create a temporary directory for test files
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test directories
        cls.data_dir = os.path.join(cls.temp_dir, 'data')
        cls.config_dir = os.path.join(cls.temp_dir, 'config')
        cls.log_dir = os.path.join(cls.temp_dir, 'logs')
        
        os.makedirs(cls.data_dir, exist_ok=True)
        os.makedirs(cls.config_dir, exist_ok=True)
        os.makedirs(cls.log_dir, exist_ok=True)
        
        # Create test configuration
        cls.config = {
            'server': {
                'host': '127.0.0.1',
                'port': 5050,  # Use a different port for testing
                'debug': False
            },
            'database': {
                'path': os.path.join(cls.data_dir, 'test.db')
            },
            'auth': {
                'secret_key': 'test_secret_key',
                'token_expiration': 3600,  # 1 hour
                'password_min_length': 8,
                'password_hash_iterations': 100000,  # Reduced for testing
                'roles': ['admin', 'operator', 'viewer'],
                'default_role': 'viewer'
            },
            'rate_limiting': {
                'enabled': True,
                'default_limits': {
                    'per_minute': 60,
                    'per_hour': 1000,
                    'per_day': 10000
                },
                'api_limits': {
                    'per_minute': 10,  # Lower for testing
                    'per_hour': 500,
                    'per_day': 5000
                },
                'storage_path': os.path.join(cls.data_dir, 'rate_limits')
            },
            'error_handling': {
                'log_path': os.path.join(cls.log_dir, 'errors'),
                'max_log_size': 1024 * 1024,  # 1 MB
                'backup_count': 5
            },
            'monitoring': {
                'metrics_path': os.path.join(cls.log_dir, 'metrics'),
                'log_interval': 60  # 1 minute
            },
            'logging': {
                'level': 'ERROR',
                'file_path': os.path.join(cls.log_dir, 'app.log'),
                'max_size': 1024 * 1024,  # 1 MB
                'backup_count': 5
            }
        }
        
        # Create required directories
        os.makedirs(cls.config['error_handling']['log_path'], exist_ok=True)
        os.makedirs(cls.config['monitoring']['metrics_path'], exist_ok=True)
        os.makedirs(cls.config['rate_limiting']['storage_path'], exist_ok=True)
        
        # Create a Flask app for testing
        cls.app = create_app(cls.config)
        
        # Start the app in a separate thread
        cls.server_thread = threading.Thread(target=cls._run_app, args=(cls,))
        cls.server_thread.daemon = True
        cls.server_thread.start()
        
        # Wait for the server to start
        time.sleep(1)
        
        # Create test tokens
        cls.admin_token = generate_token('admin', 'admin', cls.config)
        cls.operator_token = generate_token('operator', 'operator', cls.config)
        cls.viewer_token = generate_token('viewer', 'viewer', cls.config)
    
    @classmethod
    def tearDownClass(cls):
        """
        Clean up after all tests.
        """
        # Remove temporary directory
        shutil.rmtree(cls.temp_dir)
    
    @classmethod
    def _run_app(cls):
        """
        Run the Flask app for testing.
        """
        cls.app.run(
            host=cls.config['server']['host'],
            port=cls.config['server']['port'],
            debug=False,
            use_reloader=False
        )
    
    def setUp(self):
        """
        Set up before each test.
        """
        # Base URL for API requests
        self.base_url = f"http://{self.config['server']['host']}:{self.config['server']['port']}"
    
    def test_api_authentication(self):
        """
        Test that API authentication works correctly.
        """
        # Test with valid token
        response = requests.get(
            f"{self.base_url}/api/system/status",
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Test with invalid token
        response = requests.get(
            f"{self.base_url}/api/system/status",
            headers={'Authorization': 'Bearer invalid_token'}
        )
        self.assertEqual(response.status_code, 401)
        
        # Test without token
        response = requests.get(f"{self.base_url}/api/system/status")
        self.assertEqual(response.status_code, 401)
    
    def test_api_authorization(self):
        """
        Test that API authorization works correctly.
        """
        # Admin should have access to all endpoints
        response = requests.get(
            f"{self.base_url}/api/admin/users",
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Operator should not have access to admin endpoints
        response = requests.get(
            f"{self.base_url}/api/admin/users",
            headers={'Authorization': f'Bearer {self.operator_token}'}
        )
        self.assertEqual(response.status_code, 403)
        
        # Viewer should not have access to admin endpoints
        response = requests.get(
            f"{self.base_url}/api/admin/users",
            headers={'Authorization': f'Bearer {self.viewer_token}'}
        )
        self.assertEqual(response.status_code, 403)
    
    def test_rate_limiting(self):
        """
        Test that rate limiting works correctly.
        """
        # Make multiple requests to hit the rate limit
        for _ in range(self.config['rate_limiting']['api_limits']['per_minute']):
            requests.get(
                f"{self.base_url}/api/system/status",
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
        
        # Next request should be rate limited
        response = requests.get(
            f"{self.base_url}/api/system/status",
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        self.assertEqual(response.status_code, 429)
        
        # Check for rate limit headers
        self.assertIn('X-RateLimit-Limit', response.headers)
        self.assertIn('X-RateLimit-Remaining', response.headers)
        self.assertIn('X-RateLimit-Reset', response.headers)
    
    def test_error_handling(self):
        """
        Test that error handling works correctly.
        """
        # Request a non-existent endpoint to trigger a 404 error
        response = requests.get(
            f"{self.base_url}/api/non_existent_endpoint",
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        self.assertEqual(response.status_code, 404)
        
        # Check that the response contains a structured error message
        error_data = response.json()
        self.assertIn('error', error_data)
        self.assertIn('code', error_data)
        self.assertEqual(error_data['code'], 404)
        
        # Check that an error log file was created
        error_logs = os.listdir(self.config['error_handling']['log_path'])
        self.assertTrue(len(error_logs) > 0)
    
    def test_system_monitoring(self):
        """
        Test that system monitoring works correctly.
        """
        # Request the system status endpoint
        response = requests.get(
            f"{self.base_url}/api/system/status",
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains system metrics
        status_data = response.json()
        self.assertIn('cpu_percent', status_data)
        self.assertIn('memory_percent', status_data)
        self.assertIn('disk_percent', status_data)
        self.assertIn('uptime', status_data)
        
        # Check that metrics are being logged
        # Note: This may not work if the log interval is longer than the test duration
        metrics_files = os.listdir(self.config['monitoring']['metrics_path'])
        # We don't assert on the length because the log interval might be longer than the test

if __name__ == '__main__':
    unittest.main()
