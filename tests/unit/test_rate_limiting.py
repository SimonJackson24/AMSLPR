
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import modules to test
from src.config.settings import load_config
from src.app import create_app
from src.utils.rate_limiter import RateLimiter

class TestRateLimiting(unittest.TestCase):
    """
    Test cases for rate limiting functionality.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.config = {
            'server': {
                'host': '127.0.0.1',
                'port': 5000,
                'debug': False
            },
            'database': {
                'path': ':memory:'
            },
            'rate_limiting': {
                'enabled': True,
                'default_limits': {
                    'per_minute': 60,
                    'per_hour': 1000,
                    'per_day': 10000
                },
                'api_limits': {
                    'per_minute': 30,
                    'per_hour': 500,
                    'per_day': 5000
                },
                'storage_path': os.path.join(self.temp_dir, 'rate_limits')
            },
            'logging': {
                'level': 'ERROR',
                'file_path': os.path.join(self.temp_dir, 'test.log'),
                'max_size': 1024,
                'backup_count': 1
            }
        }
        
        # Create required directories
        os.makedirs(self.config['rate_limiting']['storage_path'], exist_ok=True)
        
        # Create a Flask app for testing
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        
        # Create a rate limiter instance for testing
        self.rate_limiter = RateLimiter(self.config)
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_rate_limiter_initialization(self):
        """
        Test that the rate limiter initializes correctly.
        """
        self.assertIsNotNone(self.rate_limiter)
        self.assertEqual(self.rate_limiter.enabled, self.config['rate_limiting']['enabled'])
        self.assertEqual(self.rate_limiter.default_limits, self.config['rate_limiting']['default_limits'])
        self.assertEqual(self.rate_limiter.api_limits, self.config['rate_limiting']['api_limits'])
        self.assertEqual(self.rate_limiter.storage_path, self.config['rate_limiting']['storage_path'])
    
    def test_rate_limiter_check_limit(self):
        """
        Test that the rate limiter checks limits correctly.
        """
        # Test with a new client (should not be limited)
        client_ip = '127.0.0.1'
        endpoint = '/api/vehicles'
        
        # First request should not be limited
        result = self.rate_limiter.check_limit(client_ip, endpoint)
        self.assertFalse(result['limited'])
        
        # Make multiple requests to hit the limit
        for _ in range(self.config['rate_limiting']['api_limits']['per_minute']):
            self.rate_limiter.check_limit(client_ip, endpoint)
        
        # Next request should be limited
        result = self.rate_limiter.check_limit(client_ip, endpoint)
        self.assertTrue(result['limited'])
        self.assertIn('reset_time', result)
    
    def test_rate_limiter_different_endpoints(self):
        """
        Test that the rate limiter handles different endpoints correctly.
        """
        client_ip = '127.0.0.1'
        api_endpoint = '/api/vehicles'
        web_endpoint = '/vehicles'
        
        # Make requests to the API endpoint
        for _ in range(self.config['rate_limiting']['api_limits']['per_minute']):
            self.rate_limiter.check_limit(client_ip, api_endpoint)
        
        # API endpoint should be limited
        result = self.rate_limiter.check_limit(client_ip, api_endpoint)
        self.assertTrue(result['limited'])
        
        # Web endpoint should not be limited yet (uses default limits)
        result = self.rate_limiter.check_limit(client_ip, web_endpoint)
        self.assertFalse(result['limited'])
    
    def test_rate_limiter_different_clients(self):
        """
        Test that the rate limiter handles different clients correctly.
        """
        client_ip_1 = '127.0.0.1'
        client_ip_2 = '192.168.1.1'
        endpoint = '/api/vehicles'
        
        # Make requests from the first client to hit the limit
        for _ in range(self.config['rate_limiting']['api_limits']['per_minute']):
            self.rate_limiter.check_limit(client_ip_1, endpoint)
        
        # First client should be limited
        result = self.rate_limiter.check_limit(client_ip_1, endpoint)
        self.assertTrue(result['limited'])
        
        # Second client should not be limited
        result = self.rate_limiter.check_limit(client_ip_2, endpoint)
        self.assertFalse(result['limited'])
    
    @patch('time.time')
    def test_rate_limiter_reset(self, mock_time):
        """
        Test that the rate limiter resets limits correctly.
        """
        client_ip = '127.0.0.1'
        endpoint = '/api/vehicles'
        
        # Set initial time
        mock_time.return_value = 1000
        
        # Make requests to hit the limit
        for _ in range(self.config['rate_limiting']['api_limits']['per_minute']):
            self.rate_limiter.check_limit(client_ip, endpoint)
        
        # Client should be limited
        result = self.rate_limiter.check_limit(client_ip, endpoint)
        self.assertTrue(result['limited'])
        
        # Advance time by 60 seconds (1 minute)
        mock_time.return_value = 1060
        
        # Client should no longer be limited
        result = self.rate_limiter.check_limit(client_ip, endpoint)
        self.assertFalse(result['limited'])
    
    def test_rate_limiter_headers(self):
        """
        Test that the rate limiter adds appropriate headers to responses.
        """
        # This test requires integration with Flask, which is complex to test in isolation
        # We'll test this in the integration tests
        pass

if __name__ == '__main__':
    unittest.main()
