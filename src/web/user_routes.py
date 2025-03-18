#!/usr/bin/env python3
"""
User routes for AMSLPR system.

This module provides routes for user management.
"""

import logging
from flask import Blueprint, redirect, url_for

logger = logging.getLogger('AMSLPR.web.user')

# Create blueprint
user_bp = Blueprint('user', __name__)

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
