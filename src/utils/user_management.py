
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
User management module for AMSLPR system.

This module provides functionality for user authentication and authorization.
"""

import os
import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, redirect, url_for, flash

logger = logging.getLogger(__name__)

class UserManager:
    """
    Manage users, authentication, and authorization.
    """
    
    def __init__(self, config_file=None):
        """
        Initialize the user manager.
        
        Args:
            config_file (str): Path to the user configuration file
        """
        self.config_file = config_file or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'users.json')
        self.users = {}
        self.roles = {
            'admin': {
                'description': 'Administrator with full access',
                'permissions': ['view', 'edit', 'admin']
            },
            'operator': {
                'description': 'Operator with limited access',
                'permissions': ['view', 'edit']
            },
            'viewer': {
                'description': 'Viewer with read-only access',
                'permissions': ['view']
            }
        }
        
        # Load user configuration
        self.load_config()
    
    def load_config(self):
        """
        Load user configuration from file.
        """
        try:
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                        
                        # Load users
                        self.users = config.get('users', {})
                        
                        # Load roles if present
                        if 'roles' in config:
                            self.roles = config['roles']
                        
                        logger.info(f"Loaded {len(self.users)} users from configuration")
                except (PermissionError, IOError) as e:
                    logger.error(f"Permission error loading user configuration: {e}")
                    # Create default admin user if permission error
                    self._create_default_admin()
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in user configuration: {e}")
                    # Create default admin user if invalid JSON
                    self._create_default_admin()
            else:
                # Create default admin user if no config file exists
                self._create_default_admin()
                
                # Save configuration
                self.save_config()
                
                logger.info("Created default admin user")
        except Exception as e:
            logger.error(f"Error loading user configuration: {e}")
            # Create default admin user if error loading config
            self._create_default_admin()
    
    def save_config(self):
        """
        Save user configuration to file.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Create configuration dictionary
            config = {
                'users': self.users,
                'roles': self.roles
            }
            
            # Save configuration to file
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                
                # Try to set file permissions, but don't fail if we can't
                try:
                    # Set file permissions to be readable only by owner
                    os.chmod(self.config_file, 0o666)
                except (PermissionError, IOError) as e:
                    logger.warning(f"Could not set permissions on config file: {e}")
            except (PermissionError, IOError) as e:
                logger.error(f"Permission error saving user configuration: {e}")
                # Continue without failing as we have the users in memory
        except Exception as e:
            logger.error(f"Error saving user configuration: {e}")
    
    def _create_default_admin(self):
        """
        Create default admin user.
        """
        # Generate random password
        password = 'admin'  # For testing purposes, use a simple password
        
        # Create admin user
        self.add_user(
            username='admin',
            password=password,
            role='admin',
            name='Administrator',
            email='admin@example.com'
        )
        
        print(f"\n\n===================================================")
        print(f"Created default admin user with password: {password}")
        print(f"Please change this password immediately!")
        print(f"===================================================\n\n")
        logger.info(f"Created default admin user with password: {password}")
        logger.info("Please change this password immediately!")
    
    def _hash_password(self, password, salt=None):
        """
        Hash a password with a salt.
        
        Args:
            password (str): Password to hash
            salt (str): Salt to use, or None to generate a new salt
            
        Returns:
            tuple: (hashed_password, salt)
        """
        # Generate salt if not provided
        if not salt:
            salt = secrets.token_hex(16)
        
        # Hash password with salt
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        
        return hashed, salt
    
    def authenticate(self, username, password):
        """
        Authenticate a user.
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            dict: User data if authenticated, None otherwise
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"Authentication failed for non-existent user: {username}")
            return None
        
        # Get user data
        user = self.users[username]
        
        # Hash password with stored salt
        hashed_password, _ = self._hash_password(password, user['salt'])
        
        # Check password
        if hashed_password != user['password_hash']:
            logger.warning(f"Authentication failed for user: {username}")
            return None
        
        # Update last login
        user['last_login'] = datetime.now().isoformat()
        self.save_config()
        
        # Return user data with permissions
        return {
            'username': username,
            'role': user['role'],
            'name': user['name'],
            'email': user['email'],
            'permissions': self.roles[user['role']]['permissions']
        }
    
    def add_user(self, username, password, role, name=None, email=None):
        """
        Add a new user.
        
        Args:
            username (str): Username
            password (str): Password
            role (str): User role
            name (str): User's full name
            email (str): User's email address
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if username already exists
        if username in self.users:
            logger.warning(f"User {username} already exists")
            return False
        
        # Check if role is valid
        if role not in self.roles:
            logger.warning(f"Invalid role: {role}")
            return False
        
        # Hash password
        hashed_password, salt = self._hash_password(password)
        
        # Create user
        self.users[username] = {
            'password_hash': hashed_password,
            'salt': salt,
            'role': role,
            'name': name or username,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        # Save configuration
        self.save_config()
        
        logger.info(f"Added user {username} with role {role}")
        return True
    
    def update_user(self, username, **kwargs):
        """
        Update a user.
        
        Args:
            username (str): Username
            **kwargs: User attributes to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"User {username} does not exist")
            return False
        
        # Get user data
        user = self.users[username]
        
        # Update password if provided
        if 'password' in kwargs:
            hashed_password, salt = self._hash_password(kwargs['password'])
            user['password_hash'] = hashed_password
            user['salt'] = salt
            del kwargs['password']
        
        # Update other attributes
        user.update(kwargs)
        
        # Save configuration
        self.save_config()
        
        logger.info(f"Updated user {username}")
        return True
    
    def delete_user(self, username):
        """
        Delete a user.
        
        Args:
            username (str): Username
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"User {username} does not exist")
            return False
        
        # Delete user
        del self.users[username]
        
        # Save configuration
        self.save_config()
        
        logger.info(f"Deleted user {username}")
        return True
    
    def get_user(self, username):
        """
        Get user data.
        
        Args:
            username (str): Username
            
        Returns:
            dict: User data without password hash
        """
        # Check if user exists
        if username not in self.users:
            return None
        
        # Get user data
        user = self.users[username].copy()
        
        # Remove sensitive data
        del user['password_hash']
        del user['salt']
        
        # Add username and permissions
        user['username'] = username
        user['permissions'] = self.roles[user['role']]['permissions']
        
        return user
    
    def get_users(self):
        """
        Get all users.
        
        Returns:
            list: List of user data without password hashes
        """
        users = []
        
        for username, user_data in self.users.items():
            # Copy user data
            user = user_data.copy()
            
            # Remove sensitive data
            del user['password_hash']
            del user['salt']
            
            # Add username and permissions
            user['username'] = username
            user['permissions'] = self.roles[user['role']]['permissions']
            
            users.append(user)
        
        return users
    
    def get_roles(self):
        """
        Get all roles.
        
        Returns:
            dict: Role definitions
        """
        return self.roles
    
    def has_permission(self, username, permission):
        """
        Check if a user has a permission.
        
        Args:
            username (str): Username
            permission (str): Permission to check
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            return False
        
        # Get user role
        role = self.users[username]['role']
        
        # Check if role exists
        if role not in self.roles:
            return False
        
        # Check if permission exists in role
        return permission in self.roles[role]['permissions']
    
    def has_role(self, username, role):
        """
        Check if a user has a role.
        
        Args:
            username (str): Username
            role (str): Role to check
            
        Returns:
            bool: True if user has role, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            return False
        
        # Check if user has role
        return self.users[username]['role'] == role

def login_required(user_manager):
    """
    Decorator for routes that require authentication.
    
    Args:
        user_manager: User manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                # Store current URL in session for redirect after login
                session['next'] = request.url
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission, user_manager):
    """
    Decorator for routes that require a specific permission.
    
    Args:
        permission (str): Required permission
        user_manager: User manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                session['next'] = request.url
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login'))
            
            username = session['username']
            if not user_manager.has_permission(username, permission):
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role, user_manager):
    """
    Decorator for routes that require a specific role.
    
    Args:
        role (str): Required role
        user_manager: User manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                session['next'] = request.url
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login'))
            
            username = session['username']
            if not user_manager.has_role(username, role):
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
