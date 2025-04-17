# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
User routes for AMSLPR system.

This module provides routes for user management.
"""

import logging
from flask import Blueprint, redirect, url_for, render_template, session
from src.utils.user_management import login_required, UserManager

logger = logging.getLogger('AMSLPR.web.user')

# Create blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

# Initialize user manager
user_manager = UserManager()

@user_bp.route('/profile')
@login_required(user_manager)
def profile():
    """
    User profile page.
    """
    return render_template('user/profile.html')

@user_bp.route('/users')
def users_redirect():
    """
    Redirect to the auth.users route.
    """
    return redirect(url_for('auth.users_list'))

@user_bp.route('/integration/settings')
def integration_settings_redirect():
    """
    Redirect from /integration/settings to /system/integration
    """
    return redirect(url_for('system.integration_settings'))

# This route is causing a conflict with the OCR blueprint
# Commenting out as we now have a direct route with the OCR blueprint
# @user_bp.route('/ocr/settings')
# def ocr_settings_redirect():
#     """
#     Redirect from /system/ocr/settings to /ocr/settings
#     """
#     return redirect(url_for('ocr.settings'))

@user_bp.route('/backup')
def backup_redirect():
    """
    Redirect from /system/backup to /system/backup
    """
    return redirect(url_for('system.backup_restore'))

def register_routes(app, database_manager=None):
    """
    Register user routes with the Flask application.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance (not used for user routes)
    """
    # Register blueprint
    app.register_blueprint(user_bp)
    
    logger.info("User routes registered")
    
    return app
