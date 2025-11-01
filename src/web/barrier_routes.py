
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

"""
Barrier control routes for the VisiGate web interface.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from functools import wraps

# Create blueprint
barrier_bp = Blueprint('barrier', __name__, url_prefix='/barrier')

# Global variables
db_manager = None
barrier_controller = None


def init_barrier_routes(database_manager, barrier_ctrl=None):
    """
    Initialize barrier routes with database manager and barrier controller.
    
    Args:
        database_manager: Database manager instance
        barrier_ctrl: Barrier controller instance
    """
    global db_manager, barrier_controller
    db_manager = database_manager
    barrier_controller = barrier_ctrl


@barrier_bp.route('/')
def barrier_control():
    """
    Barrier control page.
    """
    if 'username' not in session:
        try:
            return redirect(url_for('auth.login'))
        except:
            flash('Authentication required', 'warning')
            return redirect(url_for('main.index'))
    
    return render_template('barrier_control.html')


@barrier_bp.route('/open', methods=['POST'])
def open_barrier():
    """
    Open the barrier.
    """
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'})
    
    if not barrier_controller:
        return jsonify({'success': False, 'message': 'Barrier controller not available'})
    
    try:
        barrier_controller.open_barrier()
        return jsonify({'success': True, 'message': 'Barrier opened successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error opening barrier: {e}'})


@barrier_bp.route('/close', methods=['POST'])
def close_barrier():
    """
    Close the barrier.
    """
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'})
    
    if not barrier_controller:
        return jsonify({'success': False, 'message': 'Barrier controller not available'})
    
    try:
        barrier_controller.close_barrier()
        return jsonify({'success': True, 'message': 'Barrier closed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error closing barrier: {e}'})


def register_routes(app, database_manager, barrier_controller=None):
    """
    Register barrier routes with the Flask app.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance
        barrier_controller: Barrier controller instance
    """
    # Initialize routes with database manager and barrier controller
    init_barrier_routes(database_manager, barrier_controller)
    
    # Register blueprint
    app.register_blueprint(barrier_bp)
    
    return app
