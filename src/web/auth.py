#!/usr/bin/env python3
"""
Authentication utilities for the AMSLPR system.

This module provides authentication decorators and utilities.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app
import logging

# Global variables
user_manager = None

def init_user_manager(app):
    """
    Initialize the user manager.
    
    Args:
        app: Flask application
    """
    global user_manager
    
    # Import UserManager here to avoid circular imports
    from src.utils.user_manager import UserManager
    
    # Initialize user manager
    user_manager = UserManager(app.config['USER_DB_PATH'] if 'USER_DB_PATH' in app.config else None)
    
    # Add user manager to app config
    app.config['USER_MANAGER'] = user_manager

def login_required(f):
    """
    Decorator for routes that require login.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator for routes that require admin privileges.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not session.get('is_admin', False):
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('main_dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function
