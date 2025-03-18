import unittest
import os
import sys
import json
import tempfile
import shutil
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import modules to test
from src.config.settings import load_config
from src.app import create_app
from src.utils.auth import AuthManager, generate_token, verify_token, hash_password, verify_password

class TestAuthentication(unittest.TestCase):
    """
    Test cases for authentication and authorization functionality.
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
            'auth': {
                'secret_key': 'test_secret_key',
                'token_expiration': 3600,  # 1 hour
                'password_min_length': 8,
                'password_hash_iterations': 100000,  # Reduced for testing
                'roles': ['admin', 'operator', 'viewer'],
                'default_role': 'viewer'
            },
            'logging': {
                'level': 'ERROR',
                'file_path': os.path.join(self.temp_dir, 'test.log'),
                'max_size': 1024,
                'backup_count': 1
            }
        }
        
        # Create a Flask app for testing
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        
        # Create an auth manager instance for testing
        self.auth_manager = AuthManager(self.config)
        
        # Create test users
        self.test_users = {
            'admin': {
                'username': 'admin',
                'password': 'admin_password',
                'password_hash': hash_password('admin_password', self.config),
                'role': 'admin'
            },
            'operator': {
                'username': 'operator',
                'password': 'operator_password',
                'password_hash': hash_password('operator_password', self.config),
                'role': 'operator'
            },
            'viewer': {
                'username': 'viewer',
                'password': 'viewer_password',
                'password_hash': hash_password('viewer_password', self.config),
                'role': 'viewer'
            }
        }
        
        # Mock the database
        self.mock_db = MagicMock()
        self.mock_db.get_user = MagicMock(side_effect=self._mock_get_user)
        self.auth_manager.db = self.mock_db
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _mock_get_user(self, username):
        """
        Mock function for database.get_user().
        """
        if username in self.test_users:
            return self.test_users[username]
        return None
    
    def test_auth_manager_initialization(self):
        """
        Test that the auth manager initializes correctly.
        """
        self.assertIsNotNone(self.auth_manager)
        self.assertEqual(self.auth_manager.secret_key, self.config['auth']['secret_key'])
        self.assertEqual(self.auth_manager.token_expiration, self.config['auth']['token_expiration'])
        self.assertEqual(self.auth_manager.password_min_length, self.config['auth']['password_min_length'])
        self.assertEqual(self.auth_manager.roles, self.config['auth']['roles'])
        self.assertEqual(self.auth_manager.default_role, self.config['auth']['default_role'])
    
    def test_password_hashing(self):
        """
        Test that password hashing and verification work correctly.
        """
        password = 'test_password'
        
        # Hash the password
        password_hash = hash_password(password, self.config)
        
        # Verify the password
        self.assertTrue(verify_password(password, password_hash, self.config))
        
        # Verify that an incorrect password fails
        self.assertFalse(verify_password('wrong_password', password_hash, self.config))
    
    def test_token_generation_and_verification(self):
        """
        Test that token generation and verification work correctly.
        """
        username = 'test_user'
        role = 'admin'
        
        # Generate a token
        token = generate_token(username, role, self.config)
        
        # Verify the token
        result = verify_token(token, self.config)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['username'], username)
        self.assertEqual(result['role'], role)
    
    def test_expired_token(self):
        """
        Test that expired tokens are rejected.
        """
        username = 'test_user'
        role = 'admin'
        
        # Create a configuration with a very short token expiration
        config = self.config.copy()
        config['auth']['token_expiration'] = 0  # Expire immediately
        
        # Generate a token
        token = generate_token(username, role, config)
        
        # Verify the token (should fail)
        result = verify_token(token, config)
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], 'Token has expired')
    
    def test_invalid_token(self):
        """
        Test that invalid tokens are rejected.
        """
        # Create an invalid token
        invalid_token = 'invalid.token.format'
        
        # Verify the token (should fail)
        result = verify_token(invalid_token, self.config)
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], 'Invalid token format')
    
    def test_tampered_token(self):
        """
        Test that tampered tokens are rejected.
        """
        username = 'test_user'
        role = 'admin'
        
        # Generate a token
        token = generate_token(username, role, self.config)
        
        # Tamper with the token
        parts = token.split('.')
        payload = json.loads(base64.b64decode(parts[1] + '==').decode('utf-8'))
        payload['role'] = 'super_admin'  # Change the role
        tampered_payload = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('=')
        tampered_token = parts[0] + '.' + tampered_payload + '.' + parts[2]
        
        # Verify the token (should fail)
        result = verify_token(tampered_token, self.config)
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], 'Invalid token signature')
    
    def test_authenticate_user(self):
        """
        Test that user authentication works correctly.
        """
        # Test with valid credentials
        result = self.auth_manager.authenticate_user('admin', 'admin_password')
        self.assertTrue(result['success'])
        self.assertEqual(result['user']['username'], 'admin')
        self.assertEqual(result['user']['role'], 'admin')
        self.assertIn('token', result)
        
        # Test with invalid username
        result = self.auth_manager.authenticate_user('nonexistent', 'password')
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid username or password')
        
        # Test with invalid password
        result = self.auth_manager.authenticate_user('admin', 'wrong_password')
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid username or password')
    
    def test_check_permission(self):
        """
        Test that permission checking works correctly.
        """
        # Define test permissions
        permissions = {
            'admin': ['read', 'write', 'delete'],
            'operator': ['read', 'write'],
            'viewer': ['read']
        }
        
        # Test admin permissions
        self.assertTrue(self.auth_manager.check_permission('admin', 'read', permissions))
        self.assertTrue(self.auth_manager.check_permission('admin', 'write', permissions))
        self.assertTrue(self.auth_manager.check_permission('admin', 'delete', permissions))
        
        # Test operator permissions
        self.assertTrue(self.auth_manager.check_permission('operator', 'read', permissions))
        self.assertTrue(self.auth_manager.check_permission('operator', 'write', permissions))
        self.assertFalse(self.auth_manager.check_permission('operator', 'delete', permissions))
        
        # Test viewer permissions
        self.assertTrue(self.auth_manager.check_permission('viewer', 'read', permissions))
        self.assertFalse(self.auth_manager.check_permission('viewer', 'write', permissions))
        self.assertFalse(self.auth_manager.check_permission('viewer', 'delete', permissions))
        
        # Test invalid role
        self.assertFalse(self.auth_manager.check_permission('invalid_role', 'read', permissions))

if __name__ == '__main__':
    unittest.main()
