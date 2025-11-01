
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

"""
Statistics routes for the VisiGate web interface.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from functools import wraps
from datetime import datetime, timedelta
import json

# Create blueprint
stats_bp = Blueprint('stats', __name__, url_prefix='/stats')

# Global variables
db_manager = None


def init_stats_routes(database_manager):
    """
    Initialize statistics routes with database manager.
    
    Args:
        database_manager: Database manager instance
    """
    global db_manager
    db_manager = database_manager


@stats_bp.route('/api/daily')
def api_daily_stats():
    """
    API endpoint for daily statistics.
    """
    if 'username' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not db_manager:
        return jsonify({'error': 'Database manager not available'}), 500
    
    try:
        # Get date range
        days = request.args.get('days', 7, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get daily stats
        daily_stats = db_manager.get_daily_stats(start_date, end_date)
        
        return jsonify(daily_stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/hourly')
def api_hourly_stats():
    """
    API endpoint for hourly statistics.
    """
    if 'username' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not db_manager:
        return jsonify({'error': 'Database manager not available'}), 500
    
    try:
        # Get date range
        hours = request.args.get('hours', 24, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        # Get hourly stats
        hourly_stats = db_manager.get_hourly_stats(start_date, end_date)
        
        return jsonify(hourly_stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/vehicle-types')
def api_vehicle_types():
    """
    API endpoint for vehicle type statistics.
    """
    if 'username' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not db_manager:
        return jsonify({'error': 'Database manager not available'}), 500
    
    try:
        # Get vehicle type stats
        vehicle_types = db_manager.get_vehicle_type_stats()
        
        return jsonify(vehicle_types)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def register_routes(app, database_manager):
    """
    Register statistics routes with the Flask app.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance
    """
    # Initialize routes with database manager
    init_stats_routes(database_manager)
    
    # Register blueprint
    app.register_blueprint(stats_bp)
    
    return app
