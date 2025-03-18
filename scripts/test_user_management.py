#!/usr/bin/env python3
"""
Test script for the user management system.

This script tests the functionality of the user management system, including
user creation, authentication, and permission checking.
"""

import os
import sys
import logging
import argparse
import json
import time
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.user_management import UserManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_user_management')

def test_user_creation(user_manager):
    """
    Test user creation functionality.
    
    Args:
        user_manager (UserManager): User manager instance
    """
    logger.info("Testing user creation...")
    
    # Create test users
    test_users = [
        {
            'username': 'test_admin',
            'password': 'admin123',
            'role': 'admin',
            'name': 'Test Admin',
            'email': 'admin@example.com'
        },
        {
            'username': 'test_operator',
            'password': 'operator123',
            'role': 'operator',
            'name': 'Test Operator',
            'email': 'operator@example.com'
        },
        {
            'username': 'test_viewer',
            'password': 'viewer123',
            'role': 'viewer',
            'name': 'Test Viewer',
            'email': 'viewer@example.com'
        }
    ]
    
    for user in test_users:
        success = user_manager.add_user(
            username=user['username'],
            password=user['password'],
            role=user['role'],
            name=user['name'],
            email=user['email']
        )
        
        if success:
            logger.info(f"Created user {user['username']} with role {user['role']}")
        else:
            logger.error(f"Failed to create user {user['username']}")
    
    # Get all users
    users = user_manager.get_users()
    logger.info(f"Total users: {len(users)}")
    
    # Check if test users were created
    for user in test_users:
        if user['username'] in users:
            logger.info(f"User {user['username']} exists in the database")
        else:
            logger.error(f"User {user['username']} does not exist in the database")

def test_authentication(user_manager):
    """
    Test user authentication functionality.
    
    Args:
        user_manager (UserManager): User manager instance
    """
    logger.info("Testing user authentication...")
    
    # Test valid authentication
    test_cases = [
        {'username': 'test_admin', 'password': 'admin123', 'expected': True},
        {'username': 'test_operator', 'password': 'operator123', 'expected': True},
        {'username': 'test_viewer', 'password': 'viewer123', 'expected': True},
        {'username': 'test_admin', 'password': 'wrong_password', 'expected': False},
        {'username': 'nonexistent_user', 'password': 'password', 'expected': False}
    ]
    
    for case in test_cases:
        user = user_manager.authenticate(case['username'], case['password'])
        
        if (user is not None) == case['expected']:
            logger.info(f"Authentication test passed for {case['username']}")
        else:
            logger.error(f"Authentication test failed for {case['username']}")
            logger.error(f"Expected: {case['expected']}, Got: {user is not None}")
        
        if user is not None:
            logger.info(f"Authenticated user: {user['username']}, Role: {user['role']}")
            logger.info(f"Permissions: {user['permissions']}")

def test_permissions(user_manager):
    """
    Test permission checking functionality.
    
    Args:
        user_manager (UserManager): User manager instance
    """
    logger.info("Testing permission checking...")
    
    # Test permission checks
    test_cases = [
        {'username': 'test_admin', 'permission': 'view', 'expected': True},
        {'username': 'test_admin', 'permission': 'edit', 'expected': True},
        {'username': 'test_admin', 'permission': 'admin', 'expected': True},
        {'username': 'test_operator', 'permission': 'view', 'expected': True},
        {'username': 'test_operator', 'permission': 'edit', 'expected': True},
        {'username': 'test_operator', 'permission': 'admin', 'expected': False},
        {'username': 'test_viewer', 'permission': 'view', 'expected': True},
        {'username': 'test_viewer', 'permission': 'edit', 'expected': False},
        {'username': 'test_viewer', 'permission': 'admin', 'expected': False},
        {'username': 'nonexistent_user', 'permission': 'view', 'expected': False}
    ]
    
    for case in test_cases:
        has_permission = user_manager.has_permission(case['username'], case['permission'])
        
        if has_permission == case['expected']:
            logger.info(f"Permission test passed for {case['username']} and permission {case['permission']}")
        else:
            logger.error(f"Permission test failed for {case['username']} and permission {case['permission']}")
            logger.error(f"Expected: {case['expected']}, Got: {has_permission}")

def test_user_update(user_manager):
    """
    Test user update functionality.
    
    Args:
        user_manager (UserManager): User manager instance
    """
    logger.info("Testing user update...")
    
    # Update test user
    success = user_manager.update_user(
        'test_operator',
        name='Updated Operator',
        email='updated_operator@example.com'
    )
    
    if success:
        logger.info("Updated user test_operator")
    else:
        logger.error("Failed to update user test_operator")
    
    # Check if user was updated
    user = user_manager.get_user('test_operator')
    
    if user and user['name'] == 'Updated Operator' and user['email'] == 'updated_operator@example.com':
        logger.info("User update test passed")
    else:
        logger.error("User update test failed")
        logger.error(f"User data: {user}")
    
    # Update password
    success = user_manager.update_user(
        'test_operator',
        password='new_password'
    )
    
    if success:
        logger.info("Updated password for test_operator")
    else:
        logger.error("Failed to update password for test_operator")
    
    # Test authentication with new password
    user = user_manager.authenticate('test_operator', 'new_password')
    
    if user is not None:
        logger.info("Password update test passed")
    else:
        logger.error("Password update test failed")

def test_user_deletion(user_manager):
    """
    Test user deletion functionality.
    
    Args:
        user_manager (UserManager): User manager instance
    """
    logger.info("Testing user deletion...")
    
    # Delete test users
    test_users = ['test_admin', 'test_operator', 'test_viewer']
    
    for username in test_users:
        success = user_manager.delete_user(username)
        
        if success:
            logger.info(f"Deleted user {username}")
        else:
            logger.error(f"Failed to delete user {username}")
    
    # Check if users were deleted
    users = user_manager.get_users()
    
    for username in test_users:
        if username not in users:
            logger.info(f"User deletion test passed for {username}")
        else:
            logger.error(f"User deletion test failed for {username}")

def main():
    """
    Main function.
    """
    parser = argparse.ArgumentParser(description='Test user management system')
    parser.add_argument('--config', type=str, help='Path to user configuration file')
    parser.add_argument('--skip-cleanup', action='store_true', help='Skip cleanup of test users')
    args = parser.parse_args()
    
    # Create temporary config file if not specified
    if args.config:
        config_file = args.config
    else:
        config_file = '/tmp/test_users.json'
        if os.path.exists(config_file):
            os.remove(config_file)
    
    logger.info(f"Using config file: {config_file}")
    
    # Create user manager
    user_manager = UserManager(config_file=config_file)
    
    try:
        # Run tests
        test_user_creation(user_manager)
        test_authentication(user_manager)
        test_permissions(user_manager)
        test_user_update(user_manager)
        
        # Clean up test users if not skipped
        if not args.skip_cleanup:
            test_user_deletion(user_manager)
        
        logger.info("All tests completed")
    except Exception as e:
        logger.error(f"Error during tests: {e}")
    finally:
        # Clean up temporary config file if not specified
        if not args.config and not args.skip_cleanup and os.path.exists(config_file):
            os.remove(config_file)
            logger.info(f"Removed temporary config file: {config_file}")

if __name__ == '__main__':
    main()
