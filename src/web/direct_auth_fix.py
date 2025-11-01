#!/usr/bin/env python3
"""
Direct fix for the auth/users route
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from functools import wraps

# Import user manager for authentication
from src.utils.user_management import UserManager, login_required, permission_required

direct_auth_bp = Blueprint('direct_auth', __name__)
logger = logging.getLogger('VisiGate.direct_auth_fix')

# Initialize user manager
user_manager = UserManager()

# Create decorator wrappers for route protection
def auth_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return login_required(user_manager)(f)(*args, **kwargs)
    return decorated_function

def auth_permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return permission_required(permission, user_manager)(f)(*args, **kwargs)
        return decorated_function
    return decorator

@direct_auth_bp.route('/auth/users')
@auth_login_required
@auth_permission_required('admin')
def direct_users_list():
    """Direct implementation of users management route"""
    # Debug output
    logger.info("============ DIRECT AUTH USERS ACCESSED ============")
    
    try:
        # Get all users
        users_list = user_manager.get_users()
        
        # Convert list to dictionary with username as key
        users = {}
        for user in users_list:
            username = user.get('username')
            if username:
                users[username] = user
        
        # Get all roles
        roles = user_manager.get_roles()
        
        return render_template('auth/users.html', users=users, roles=roles)
    except Exception as e:
        logger.error(f"Error in direct_users_list: {str(e)}")
        flash(f"Error loading users: {str(e)}", 'danger')
        return redirect(url_for('main.index'))

def register_direct_auth_fix(app):
    """Register the direct auth blueprint"""
    app.register_blueprint(direct_auth_bp)
    logger.info("Direct auth users fix registered successfully")
    return app
