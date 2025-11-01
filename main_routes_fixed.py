# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

"""
Main routes for the VisiGate web interface.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from functools import wraps
import logging
import traceback

# Set up logging
logger = logging.getLogger('VisiGate.web.main')

# Import user management
try:
    from src.utils.user_management import login_required, UserManager
    user_manager = UserManager()
except ImportError:
    # Fallback if import fails
    logger.warning("Could not import UserManager from src.utils.user_management")
    from src.web.user_management import login_required, user_manager

# Create blueprint
main_bp = Blueprint('main', __name__, url_prefix='/')

# Global variables
db_manager = None
barrier_controller = None
paxton_integration = None
nayax_integration = None

def init_main_routes(database_manager):
    """
    Initialize main routes with database manager.
    
    Args:
        database_manager: Database manager instance
    """
    global db_manager
    db_manager = database_manager
    logger.info(f"Main routes initialized with database manager: {db_manager}")


@main_bp.route('/')
def index():
    """
    Main index route. Redirects to dashboard if logged in, otherwise to login page.
    """
    try:
        if 'username' in session:
            return redirect(url_for('main.dashboard'))
        
        # If auth module is not available, go directly to dashboard
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required(user_manager)
def dashboard():
    """
    Dashboard page showing system overview.
    """
    try:
        logger.info("Dashboard route accessed")
        
        if 'username' not in session:
            logger.warning("User not in session, redirecting to login")
            return redirect(url_for('auth.login'))
        
        logger.info(f"Dashboard accessed by user: {session.get('username')}")
        
        # Initialize empty stats dictionary
        stats = {
            'recent_logs': [],
            'total_vehicles': 0,
            'authorized_vehicles': 0,
            'total_logs': 0,
            'today_logs': 0,
            'system_status': {
                'camera_status': 'Unknown',
                'barrier_status': 'Unknown',
                'database_status': 'Unknown'
            }
        }
        
        # Get statistics for dashboard if db_manager is available
        if db_manager:
            try:
                # Get recent access logs
                if hasattr(db_manager, 'get_access_logs'):
                    stats['recent_logs'] = db_manager.get_access_logs(limit=10)
                
                # Get vehicle counts
                if hasattr(db_manager, 'get_vehicle_count'):
                    stats['total_vehicles'] = db_manager.get_vehicle_count()
                    stats['authorized_vehicles'] = db_manager.get_vehicle_count(authorized=True)
                
                # Get access log counts
                if hasattr(db_manager, 'get_access_log_count'):
                    stats['total_logs'] = db_manager.get_access_log_count()
                    stats['today_logs'] = db_manager.get_access_log_count(today_only=True)
                
                # Set database status
                stats['system_status']['database_status'] = 'Connected'
            except Exception as e:
                logger.error(f'Error loading dashboard data: {str(e)}')
                logger.error(traceback.format_exc())
                flash(f'Error loading dashboard data: {str(e)}', 'danger')
                stats['system_status']['database_status'] = 'Error'
        else:
            logger.warning("Database manager not available")
            stats['system_status']['database_status'] = 'Not Connected'
        
        # Get camera status
        try:
            logger.info("Checking camera status")
            try:
                from src.web.camera_routes import onvif_camera_manager
                if onvif_camera_manager and hasattr(onvif_camera_manager, 'get_all_cameras'):
                    logger.info("Camera manager found and initialized")
                    stats['system_status']['camera_status'] = 'Connected'
                else:
                    logger.warning("Camera manager not initialized")
                    stats['system_status']['camera_status'] = 'Not Connected'
            except ImportError:
                logger.warning("Could not import onvif_camera_manager")
                stats['system_status']['camera_status'] = 'Not Available'
        except Exception as e:
            logger.error(f'Error getting camera status: {str(e)}')
            logger.error(traceback.format_exc())
            stats['system_status']['camera_status'] = 'Error'
        
        # Get barrier status if available
        if barrier_controller:
            try:
                stats['system_status']['barrier_status'] = 'Connected' if barrier_controller.is_connected() else 'Not Connected'
            except Exception as e:
                logger.error(f'Error getting barrier status: {str(e)}')
                logger.error(traceback.format_exc())
                stats['system_status']['barrier_status'] = 'Error'
        else:
            stats['system_status']['barrier_status'] = 'Not Available'
        
        logger.info("Rendering dashboard template")
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Unhandled exception in dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html', 
                              error_title="Dashboard Error",
                              error_message=f"An error occurred while loading the dashboard: {str(e)}",
                              error_details=traceback.format_exc())

@main_bp.route('/about')
def about():
    """
    About page.
    """
    return render_template('about.html')

@main_bp.route('/help')
def help():
    """
    Help page.
    """
    return render_template('help.html')

@main_bp.route('/settings')
@login_required(user_manager)
def settings():
    """
    Settings page.
    """
    return render_template('settings.html')
