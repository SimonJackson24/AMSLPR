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
from loguru import logger
from src.utils.user_management import login_required, UserManager
import traceback

# Create blueprint
main_bp = Blueprint('main', __name__, url_prefix='/')

# Global variables
db_manager = None
barrier_controller = None
paxton_integration = None
nayax_integration = None
user_manager = UserManager()

def init_main_routes(database_manager):
    """
    Initialize main routes with database manager.
    
    Args:
        database_manager: Database manager instance
    """
    global db_manager
    db_manager = database_manager


@main_bp.route('/')
def index():
    """
    Main index route. Redirects to dashboard if logged in, otherwise to login page.
    """
    if 'username' in session:
        return redirect(url_for('main.dashboard'))
    
    # If auth module is not available, go directly to dashboard
    try:
        return redirect(url_for('auth.login'))
    except:
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
                import traceback
                logger.error(traceback.format_exc())
                flash(f'Error loading dashboard data: {str(e)}', 'danger')
                stats['system_status']['database_status'] = 'Error'
        
        # Get camera status
        try:
            logger.info("Checking camera status")
            from src.web.camera_routes import onvif_camera_manager
            if onvif_camera_manager and hasattr(onvif_camera_manager, 'get_all_cameras'):
                logger.info("Camera manager found and initialized")
                stats['system_status']['camera_status'] = 'Connected'
            else:
                logger.warning("Camera manager not initialized")
                stats['system_status']['camera_status'] = 'Not Connected'
        except Exception as e:
            logger.error(f'Error getting camera status: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            stats['system_status']['camera_status'] = 'Error'
        
        # Get barrier status if available
        if barrier_controller:
            try:
                stats['system_status']['barrier_status'] = 'Connected' if barrier_controller.is_connected() else 'Not Connected'
            except Exception as e:
                logger.error(f'Error getting barrier status: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                stats['system_status']['barrier_status'] = 'Error'
        
        logger.info("Rendering dashboard template")
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Unhandled exception in dashboard route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error loading dashboard: {str(e)}", 500


@main_bp.route('/logs')
@login_required(user_manager)
def logs():
    """
    Access logs page.
    """
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    plate_number = request.args.get('plate_number', '')
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get access logs
    logs = []
    total_logs = 0
    if db_manager:
        # Get vehicle_id from plate_number if provided
        vehicle_id = None
        if plate_number:
            try:
                from src.db.models import Vehicle
                session = db_manager.get_session()
                vehicle = session.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
                if vehicle:
                    vehicle_id = vehicle.id
            except Exception as e:
                logger.error(f"Error getting vehicle ID: {str(e)}")
        
        logs = db_manager.get_access_logs(
            vehicle_id=vehicle_id,
            limit=limit
        )
        total_logs = db_manager.get_access_log_count()
    
    # Calculate pagination
    total_pages = (total_logs + limit - 1) // limit
    
    return render_template(
        'logs.html',
        logs=logs,
        page=page,
        limit=limit,
        total_pages=total_pages,
        total_logs=total_logs,
        plate_number=plate_number
    )


@main_bp.route('/statistics')
@login_required(user_manager)
def statistics():
    """
    Statistics page.
    """
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    # Get vehicle statistics
    vehicle_stats = {
        'total_vehicles': db_manager.get_vehicle_count(),
        'authorized_vehicles': db_manager.get_vehicle_count(authorized=True),
        'unauthorized_vehicles': db_manager.get_vehicle_count() - db_manager.get_vehicle_count(authorized=True)
    }
    
    # Get access logs for statistics
    access_logs = db_manager.get_access_logs(limit=100)
    
    # Get parking statistics
    parking_stats = {
        'avg_duration_minutes': 0,  # Default value when no data is available
        'max_duration_minutes': 0,
        'min_duration_minutes': 0,
        'total_sessions': 0,
        'duration_distribution': {'0-15 min': 0, '15-30 min': 0, '30-60 min': 0, '1-2 hours': 0, '2+ hours': 0}
    }
    
    # Add most frequent vehicles data
    vehicle_stats['most_frequent_vehicles'] = {
        'ABC123': 15,
        'XYZ789': 12,
        'DEF456': 8,
        'GHI789': 6,
        'JKL012': 4
    }
    
    # Add hourly distribution data
    hourly_distribution = {
        'hours': [f"{i:02d}:00" for i in range(24)],
        'entry': [0] * 24,
        'exit': [0] * 24
    }
    
    # Add daily traffic data
    from datetime import datetime, timedelta
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, 0, -1)]
    daily_traffic = {
        'dates': dates,
        'entry': [0] * 7,
        'exit': [0] * 7,
        'total': [0] * 7
    }
    
    return render_template('statistics.html', vehicle_stats=vehicle_stats, access_logs=access_logs, parking_stats=parking_stats, hourly_distribution=hourly_distribution, daily_traffic=daily_traffic)


@main_bp.route('/reports')
@login_required(user_manager)
def reports():
    """
    Reports page.
    """
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    # Get current year and month
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Generate list of years (current year and 4 previous years)
    years = list(range(current_year - 4, current_year + 1))
    
    # Generate list of months
    months = [
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June'),
        (7, 'July'),
        (8, 'August'),
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December')
    ]
    
    # Get list of previous reports (empty for now)
    previous_reports = []
    
    return render_template('reports.html', years=years, months=months, current_year=current_year, current_month=current_month, previous_reports=previous_reports)


@main_bp.route('/notification_settings')
@login_required(user_manager)
def notification_settings():
    """
    Notification settings page.
    """
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    return render_template('notification_settings.html')


@main_bp.route('/log_details/<int:log_id>')
@login_required(user_manager)
def log_details(log_id):
    """
    Display detailed information for a specific log entry.
    
    Args:
        log_id (int): ID of the log entry to display
    """
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    # Get log entry
    log = None
    related_logs = []
    if db_manager:
        log = db_manager.get_access_log(log_id)
        if log:
            # Get related logs (same plate number or same camera)
            related_logs = db_manager.get_access_logs(
                plate_number=log.get('plate_number'),
                limit=5,
                exclude_id=log_id
            )
    
    if not log:
        flash('Log entry not found', 'error')
        return redirect(url_for('main.logs'))
    
    return render_template('log_details.html', log=log, related_logs=related_logs)


def register_main_routes(app, database_manager, barrier_ctrl=None, paxton_integ=None, nayax_integ=None):
    """
    Register main routes with dependencies.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance
        barrier_ctrl: Barrier controller instance
        paxton_integ: Paxton integration instance
        nayax_integ: Nayax integration instance
        
    Returns:
        Flask: The Flask application instance
    """
    global db_manager, barrier_controller, paxton_integration, nayax_integration
    db_manager = database_manager
    barrier_controller = barrier_ctrl
    paxton_integration = paxton_integ
    nayax_integration = nayax_integ
    
    # Register the blueprint
    app.register_blueprint(main_bp)
    
    logger.info("Main routes registered")
    
    return app

# Legacy function for backward compatibility
def init_main_routes(database_manager):
    """
    Initialize main routes with database manager.
    
    Args:
        database_manager: Database manager instance
    """
    global db_manager
    db_manager = database_manager
