#!/usr/bin/env python3
"""
Authentication routes for AMSLPR system.

This module provides routes for user authentication and management.
"""

import logging
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app, jsonify

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
    
    logger.info("User manager initialized")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    """
    # Check if already logged in
    if 'username' in session:
        return redirect(url_for('main_dashboard.index'))
    
    # Handle login form submission
    if request.method == 'POST':
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
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('main_dashboard.index'))
        else:
            flash('Invalid username or password', 'danger')
    
    # Pass current year to the template for copyright notice
    from datetime import datetime
    current_year = datetime.now().year
    
    # Get the next page from the query string
    next_page = request.args.get('next', '')
    
    return render_template('login_standalone.html', current_year=current_year, next=next_page)

@auth_bp.route('/logout')
def logout():
    """
    User logout route.
    """
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
        return redirect(url_for('main_dashboard.index'))
    
    return render_template('profile.html', user=user)

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
        else:
            flash('Failed to update profile', 'danger')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/users')
@login_required(user_manager)
@permission_required('admin', user_manager)
def users_list():
    """
    User management route.
    """
    # Get all users
    users = user_manager.get_users()
    
    # Get all roles
    roles = user_manager.get_roles()
    
    return render_template('users.html', users=users, roles=roles)

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
        flash(f'User {username} added successfully', 'success')
    else:
        flash(f'Failed to add user {username}', 'danger')
    
    return redirect(url_for('auth.users_list'))

@auth_bp.route('/users/update/<username>', methods=['POST'])
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
    
    # Validate data
    if not role:
        flash('Role is required', 'danger')
        return redirect(url_for('auth.users_list'))
    
    # Prepare updates
    updates = {
        'role': role,
        'name': name,
        'email': email
    }
    
    # Add password if provided
    if password:
        updates['password'] = password
    
    # Update user
    success = user_manager.update_user(username, **updates)
    
    if success:
        flash(f'User {username} updated successfully', 'success')
    else:
        flash(f'Failed to update user {username}', 'danger')
    
    return redirect(url_for('auth.users_list'))

@auth_bp.route('/users/delete/<username>', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def delete_user(username):
    """
    Delete user route.
    """
    # Check if trying to delete self
    if username == session.get('username'):
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('auth.users_list'))
    
    # Delete user
    success = user_manager.delete_user(username)
    
    if success:
        flash(f'User {username} deleted successfully', 'success')
    else:
        flash(f'Failed to delete user {username}', 'danger')
    
    return redirect(url_for('auth.users_list'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Forgot password route.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Check if user exists
        user = user_manager.get_user(username)
        
        if user and user.get('email') == email:
            # In a real application, this would send a password reset email
            # For now, just show a success message
            flash('Password reset instructions have been sent to your email', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('User not found or email does not match', 'danger')
    
    return render_template('forgot_password.html')

def register_routes(app, database_manager=None):
    """
    Register authentication routes with the Flask application.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance (not used for auth routes)
    """
    # Initialize user manager in app config
    init_user_manager(app)
    
    # Blueprint is registered in app.py, so we don't need to register it here
    
    return app
