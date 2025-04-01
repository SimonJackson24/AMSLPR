# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Authentication routes for AMSLPR system.

This module provides routes for user authentication and management.
"""

import logging
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app, jsonify
from flask_wtf.csrf import CSRFProtect

from src.utils.user_management import UserManager, login_required, permission_required, role_required

logger = logging.getLogger('AMSLPR.web.auth')

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize user manager
user_manager = UserManager()

def init_user_manager(app):
    """
    Initialize the user manager.
    
    Args:
        app: Flask application
    """
    # Store in app config for access in routes
    app.config['USER_MANAGER'] = user_manager
    
    # Register authentication decorators
    app.login_required = login_required(user_manager)
    app.permission_required = lambda permission: permission_required(permission, user_manager)
    app.role_required = lambda role: role_required(role, user_manager)
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    logger.info("User manager initialized")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    """
    # Check if already logged in
    if 'username' in session:
        return redirect(url_for('main.index'))
    
    # Handle login form submission
    if request.method == 'POST':
        # Verify CSRF token
        if not request.form.get('csrf_token'):
            logger.error('CSRF token missing in login request')
            flash('Security token missing. Please try again.', 'danger')
            return render_template('login.html', current_year=datetime.now().year)
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Authenticate user
        user = user_manager.authenticate(username, password)
        
        if user:
            # Set session variables
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            session['permissions'] = user['permissions']
            session.modified = True
            
            # Log successful login
            logger.info(f"User {username} logged in successfully")
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            logger.warning(f"Failed login attempt for user {username}")
    
    # Pass current year to the template for copyright notice
    from datetime import datetime
    current_year = datetime.now().year
    
    # Get the next page from the query string
    next_page = request.args.get('next', '')
    
    return render_template('login.html', current_year=current_year, next=next_page)

@auth_bp.route('/logout')
def logout():
    """
    User logout route.
    """
    # Log user logout
    if 'username' in session:
        logger.info(f"User {session['username']} logged out")
    
    # Clear session
    session.clear()
    session.modified = True
    
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required(user_manager)
def profile():
    """
    User profile route.
    """
    # Get user data
    username = session.get('username')
    user = user_manager.get_user(username)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/profile.html', user=user)

@auth_bp.route('/profile/update', methods=['POST'])
@login_required(user_manager)
def update_profile():
    """
    Update user profile route.
    """
    # Get user data
    username = session.get('username')
    
    # Get form data
    name = request.form.get('name')
    email = request.form.get('email')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Update user data
    updates = {}
    
    if name:
        updates['name'] = name
    
    if email:
        updates['email'] = email
    
    # Update password if provided
    if current_password and new_password and confirm_password:
        # Check if passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('auth.profile'))
        
        # Authenticate current password
        if not user_manager.authenticate(username, current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.profile'))
        
        # Update password
        updates['password'] = new_password
    
    # Update user
    if updates:
        success = user_manager.update_user(username, **updates)
        
        if success:
            flash('Profile updated successfully', 'success')
            
            # Update session variables
            if 'name' in updates:
                session['name'] = updates['name']
                session.modified = True
            
            logger.info(f"User {username} updated their profile")
        else:
            flash('Failed to update profile', 'danger')
            logger.error(f"Failed to update profile for user {username}")
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/users')
@login_required(user_manager)
@permission_required('admin', user_manager)
def users_list():
    """
    User management route.
    """
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
        logger.error(f"Error in users_list: {str(e)}")
        flash(f"Error loading users: {str(e)}", 'danger')
        return redirect(url_for('main.index'))

@auth_bp.route('/users/add', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def add_user():
    """
    Add user route.
    """
    # Get form data
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    name = request.form.get('name')
    email = request.form.get('email')
    
    # Validate data
    if not username or not password or not role:
        flash('Username, password, and role are required', 'danger')
        return redirect(url_for('auth.users_list'))
    
    # Add user
    success = user_manager.add_user(
        username=username,
        password=password,
        role=role,
        name=name,
        email=email
    )
    
    if success:
        flash('User added successfully', 'success')
        logger.info(f"User {username} added by {session['username']}")
    else:
        flash('Failed to add user', 'danger')
        logger.error(f"Failed to add user {username}")
    
    return redirect(url_for('auth.users_list'))

@auth_bp.route('/users/<username>/update', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def update_user(username):
    """
    Update user route.
    """
    # Get form data
    role = request.form.get('role')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Update user data
    updates = {}
    
    if role:
        updates['role'] = role
    
    if name:
        updates['name'] = name
    
    if email:
        updates['email'] = email
    
    if password:
        updates['password'] = password
    
    # Update user
    if updates:
        success = user_manager.update_user(username, **updates)
        
        if success:
            flash('User updated successfully', 'success')
            logger.info(f"User {username} updated by {session['username']}")
        else:
            flash('Failed to update user', 'danger')
            logger.error(f"Failed to update user {username}")
    
    return redirect(url_for('auth.users_list'))

@auth_bp.route('/users/<username>/delete', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def delete_user(username):
    """
    Delete user route.
    """
    # Prevent deleting own account
    if username == session['username']:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('auth.users_list'))
    
    # Delete user
    success = user_manager.delete_user(username)
    
    if success:
        flash('User deleted successfully', 'success')
        logger.info(f"User {username} deleted by {session['username']}")
    else:
        flash('Failed to delete user', 'danger')
        logger.error(f"Failed to delete user {username}")
    
    return redirect(url_for('auth.users_list'))

def register_routes(app, database_manager=None):
    """
    Register authentication routes with the Flask application.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance (not used for auth routes)
    """
    # Initialize user manager
    init_user_manager(app)
    
    logger.info("User manager initialized")
