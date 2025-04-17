#!/usr/bin/env python3
"""
Direct fix for the OCR test route
"""

import logging
from flask import Blueprint, render_template
from functools import wraps

# Import user manager for authentication if needed
from src.utils.user_management import UserManager

direct_test_ocr_bp = Blueprint('direct_test_ocr', __name__)
logger = logging.getLogger('AMSLPR.direct_test_ocr_fix')

# Initialize user manager for admin_required decorator
user_manager = UserManager()

# Create admin_required decorator
def admin_required(f):
    """Decorator for routes that require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, redirect, url_for, flash
        
        # Check if user is logged in
        if 'username' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user has admin role
        username = session.get('username')
        user = user_manager.get_user(username)
        
        if not user or user.get('role') != 'admin':
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@direct_test_ocr_bp.route('/ocr/test', methods=['GET'])
@admin_required
def direct_ocr_test():
    """Direct implementation of OCR test page"""
    logger.info("OCR test page accessed via direct route")
    return render_template('ocr_test.html')

def register_direct_test_ocr_fix(app):
    """Register the direct OCR test blueprint"""
    app.register_blueprint(direct_test_ocr_bp)
    logger.info("Direct OCR test fix registered successfully")
    return app
