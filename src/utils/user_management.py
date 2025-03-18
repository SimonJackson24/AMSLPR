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
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                    # Load users
                    self.users = config.get('users', {})
                    
                    # Load roles if present
                    if 'roles' in config:
                        self.roles = config['roles']
                    
                    logger.info(f"Loaded {len(self.users)} users from configuration")
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
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Set file permissions to be readable only by owner
            os.chmod(self.config_file, 0o600)
            
            logger.info("User configuration saved")
            return True
        except Exception as e:
            logger.error(f"Error saving user configuration: {e}")
            return False
    
    def _create_default_admin(self):
        """
        Create default admin user.
        """
        # Generate random password
        password = secrets.token_urlsafe(12)
        
        # Create admin user
        self.add_user(
            username='admin',
            password=password,
            role='admin',
            name='Administrator',
            email='admin@example.com'
        )
        
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
            logger.warning(f"User {username} not found")
            return False
        
        # Get user
        user = self.users[username]
        
        # Update password if provided
        if 'password' in kwargs:
            hashed_password, salt = self._hash_password(kwargs['password'])
            user['password_hash'] = hashed_password
            user['salt'] = salt
            kwargs.pop('password')
        
        # Update other attributes
        for key, value in kwargs.items():
            if key in ['role', 'name', 'email']:
                user[key] = value
        
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
            logger.warning(f"User {username} not found")
            return False
        
        # Delete user
        del self.users[username]
        
        # Save configuration
        self.save_config()
        
        logger.info(f"Deleted user {username}")
        return True
    
    def authenticate(self, username, password):
        """
        Authenticate a user.
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            dict: User data if authentication successful, None otherwise
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"Authentication failed: User {username} not found")
            return None
        
        # Get user
        user = self.users[username]
        
        # Hash provided password with user's salt
        hashed_password, _ = self._hash_password(password, user['salt'])
        
        # Check if passwords match
        if hashed_password != user['password_hash']:
            logger.warning(f"Authentication failed: Invalid password for user {username}")
            return None
        
        # Update last login time
        user['last_login'] = datetime.now().isoformat()
        self.save_config()
        
        # Return user data without sensitive information
        return {
            'username': username,
            'role': user['role'],
            'name': user['name'],
            'email': user['email'],
            'permissions': self.get_permissions(user['role'])
        }
    
    def get_permissions(self, role):
        """
        Get permissions for a role.
        
        Args:
            role (str): Role name
            
        Returns:
            list: List of permissions
        """
        if role not in self.roles:
            return []
        
        return self.roles[role].get('permissions', [])
    
    def has_permission(self, username, permission):
        """
        Check if a user has a specific permission.
        
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
        
        # Get permissions for role
        permissions = self.get_permissions(role)
        
        # Check if permission is granted
        return permission in permissions
    
    def get_users(self):
        """
        Get all users.
        
        Returns:
            dict: Dictionary of users without sensitive information
        """
        users = {}
        
        for username, user in self.users.items():
            users[username] = {
                'role': user['role'],
                'name': user['name'],
                'email': user['email'],
                'created_at': user['created_at'],
                'last_login': user['last_login']
            }
        
        return users
    
    def get_user(self, username):
        """
        Get a user.
        
        Args:
            username (str): Username
            
        Returns:
            dict: User data without sensitive information, or None if not found
        """
        if username not in self.users:
            return None
        
        user = self.users[username]
        
        return {
            'username': username,
            'role': user['role'],
            'name': user['name'],
            'email': user['email'],
            'created_at': user['created_at'],
            'last_login': user['last_login']
        }
    
    def get_user_role(self, username):
        """
        Get the role of a user.
        
        Args:
            username (str): Username to check
            
        Returns:
            str: User's role or 'viewer' if user not found
        """
        if username in self.users:
            return self.users[username].get('role', 'viewer')
        return 'viewer'
    
    def get_roles(self):
        """
        Get all roles.
        
        Returns:
            dict: Dictionary of roles
        """
        return self.roles

# Flask authentication decorators
def login_required(user_manager):
    """
    Decorator for routes that require authentication.
    
    Args:
        user_manager: User manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'username' not in session:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
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
            # Check if user is logged in
            if 'username' not in session:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Check if user has permission
            if not user_manager.has_permission(session['username'], permission):
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('index'))
            
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
            # Check if user is logged in
            if 'username' not in session:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Check if user has role
            if session.get('role') != role:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def mode_permission_required(standalone_permissions, parking_permissions, user_manager):
    """
    Decorator for routes that require different permissions based on operating mode.
    
    Args:
        standalone_permissions (list): Required permissions in standalone mode
        parking_permissions (list): Required permissions in parking mode
        user_manager: User manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app
            
            # Check if user is logged in
            if 'username' not in session:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Admin users always have access
            if 'admin' in session.get('permissions', []):
                return f(*args, **kwargs)
            
            # Get current operating mode
            config = current_app.config.get('AMSLPR_CONFIG', {})
            operating_mode = config.get('operating_mode', 'standalone')
            
            # Determine required permissions based on mode
            if operating_mode == 'parking':
                required_permissions = parking_permissions
            else:  # Default to standalone mode
                required_permissions = standalone_permissions
            
            # Check if user has any of the required permissions
            user_permissions = session.get('permissions', [])
            has_permission = False
            
            for permission in required_permissions:
                if permission in user_permissions:
                    has_permission = True
                    break
            
            if not has_permission:
                flash('You do not have permission to access this page in the current operating mode', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
