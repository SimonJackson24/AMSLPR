#!/usr/bin/env python3
"""
Operating mode-based permission system for AMSLPR.

This module provides functionality for controlling access to features
based on the system's operating mode and user permissions.
"""

import logging
from functools import wraps
from flask import session, redirect, url_for, flash, current_app, request

logger = logging.getLogger(__name__)

# Define permission sets for different operating modes
STANDALONE_MODE_PERMISSIONS = {
    # Features accessible to operators in standalone mode
    'vehicles': ['operator', 'admin'],
    'access_logs': ['operator', 'admin'],
    'dashboard': ['operator', 'admin'],
    'statistics': ['operator', 'admin'],
    
    # Features restricted to admins in standalone mode
    'cameras': ['admin'],
    'system_settings': ['admin'],
    'ocr_settings': ['admin'],
    'user_management': ['admin'],
    'integration': ['admin'],
    'parking': ['admin']
}

PARKING_MODE_PERMISSIONS = {
    # Features accessible to operators in parking mode
    'vehicles': ['operator', 'admin'],
    'access_logs': ['operator', 'admin'],
    'dashboard': ['operator', 'admin'],
    'statistics': ['operator', 'admin'],
    'parking': ['operator', 'admin'],  # Parking features available to operators
    
    # Features restricted to admins in parking mode
    'cameras': ['admin'],
    'system_settings': ['admin'],
    'ocr_settings': ['admin'],
    'user_management': ['admin'],
    'integration': ['admin'],
    'parking_settings': ['admin']  # Parking settings restricted to admins
}

PAXTON_MODE_PERMISSIONS = {
    # Features accessible to operators in Paxton mode
    'vehicles': ['operator', 'admin'],
    'access_logs': ['operator', 'admin'],
    'dashboard': ['operator', 'admin'],
    'statistics': ['operator', 'admin'],
    
    # Features restricted to admins in Paxton mode
    'cameras': ['admin'],
    'system_settings': ['admin'],
    'ocr_settings': ['admin'],
    'user_management': ['admin'],
    'integration': ['admin'],
    'parking': ['admin']
}

NAYAX_MODE_PERMISSIONS = {
    # Features accessible to operators in Nayax mode
    'vehicles': ['operator', 'admin'],
    'access_logs': ['operator', 'admin'],
    'dashboard': ['operator', 'admin'],
    'statistics': ['operator', 'admin'],
    'parking': ['operator', 'admin'],  # Parking features available to operators
    'nayax_pricing': ['operator', 'admin'],  # Nayax pricing features available to operators
    
    # Features restricted to admins in Nayax mode
    'cameras': ['admin'],
    'system_settings': ['admin'],
    'ocr_settings': ['admin'],
    'user_management': ['admin'],
    'integration': ['admin'],
    'parking_settings': ['admin']  # Parking settings restricted to admins
}

def check_mode_access(feature, user_role):
    """
    Check if a user with the given role can access a feature in the current operating mode.
    
    Args:
        feature (str): The feature to check access for
        user_role (str): The user's role
        
    Returns:
        bool: True if the user can access the feature, False otherwise
    """
    # Get current operating mode
    config = current_app.config.get('AMSLPR_CONFIG', {})
    operating_mode = config.get('operating_mode', 'standalone')
    
    # Determine permission set based on operating mode
    if operating_mode == 'parking':
        permission_set = PARKING_MODE_PERMISSIONS
    elif operating_mode == 'paxton':
        permission_set = PAXTON_MODE_PERMISSIONS
    elif operating_mode == 'nayax':
        permission_set = NAYAX_MODE_PERMISSIONS
    else:  # Default to standalone mode
        permission_set = STANDALONE_MODE_PERMISSIONS
    
    # Check if the feature exists in the permission set
    if feature not in permission_set:
        return False
    
    # Check if the user's role is allowed to access the feature
    return user_role in permission_set[feature]

def mode_access_required(feature, user_manager_func):
    """
    Decorator for routes that require access based on operating mode.
    
    Args:
        feature (str): The feature to check access for
        user_manager_func: Function that returns the user manager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'username' not in session:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Get user manager instance
            user_manager = user_manager_func() if callable(user_manager_func) else user_manager_func
            
            # Get user's role
            username = session.get('username')
            if user_manager and username in user_manager.users:
                user_role = user_manager.users[username]['role']
            else:
                user_role = session.get('role', 'viewer')
            
            # Admin users always have access
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # Get current operating mode
            config = current_app.config.get('AMSLPR_CONFIG', {})
            operating_mode = config.get('operating_mode', 'standalone')
            
            # In parking mode, check if user can access parking features
            if operating_mode == 'parking' and feature == 'parking':
                # Operators can access parking features in parking mode
                if user_role == 'operator':
                    return f(*args, **kwargs)
            # In standalone mode, restrict parking features to admins
            elif operating_mode == 'standalone' and feature == 'parking':
                # Only admins can access parking features in standalone mode
                flash('Parking features are only available to administrators in standalone mode', 'warning')
                return redirect(url_for('main.dashboard'))
            
            # If we get here, the user doesn't have access
            flash('You do not have permission to access this feature', 'warning')
            return redirect(url_for('main.dashboard'))
            
        return decorated_function
    return decorator

def get_visible_features():
    """
    Get a list of features that should be visible to the current user in the current operating mode.
    
    Returns:
        dict: Dictionary of features and whether they should be visible
    """
    # Check if user is logged in
    if 'username' not in session:
        return {}
    
    # Get user's role
    username = session.get('username')
    user_manager = current_app.config.get('USER_MANAGER')
    
    if user_manager and username in user_manager.users:
        user_role = user_manager.users[username]['role']
    else:
        user_role = session.get('role', 'viewer')
    
    # Admin users see everything
    if user_role == 'admin':
        return {feature: True for feature in set(list(STANDALONE_MODE_PERMISSIONS.keys()) + 
                                              list(PARKING_MODE_PERMISSIONS.keys()) + 
                                              list(PAXTON_MODE_PERMISSIONS.keys()) + 
                                              list(NAYAX_MODE_PERMISSIONS.keys()))}
    
    # Get current operating mode
    config = current_app.config.get('AMSLPR_CONFIG', {})
    operating_mode = config.get('operating_mode', 'standalone')
    
    # Determine permission set based on operating mode
    if operating_mode == 'parking':
        permission_set = PARKING_MODE_PERMISSIONS
    elif operating_mode == 'paxton':
        permission_set = PAXTON_MODE_PERMISSIONS
    elif operating_mode == 'nayax':
        permission_set = NAYAX_MODE_PERMISSIONS
    else:  # Default to standalone mode
        permission_set = STANDALONE_MODE_PERMISSIONS
    
    # Check each feature
    visible_features = {}
    for feature, allowed_roles in permission_set.items():
        visible_features[feature] = user_role in allowed_roles
    
    return visible_features
