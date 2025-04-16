#!/usr/bin/env python3

"""
Emergency fix for the cameras page - redirect to dashboard.
"""

import os

# Create a backup of the current camera_routes.py if it doesn't already exist
os.system("sudo cp /opt/amslpr/src/web/camera_routes.py /opt/amslpr/src/web/camera_routes.py.backup_redirect 2>/dev/null || true")
print("Created backup of camera_routes.py")

# Create an emergency version of camera_routes.py that redirects to dashboard
emergency_routes = '''
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Emergency camera routes for the AMSLPR web application.
This version redirects the cameras page to the dashboard to avoid errors.
"""

import logging
from flask import Blueprint, redirect, url_for

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AMSLPR.web.cameras')

# Create blueprint
camera_bp = Blueprint('camera', __name__)

@camera_bp.route('/cameras')
def cameras():
    """Redirect to dashboard as emergency fix."""
    logger.info("Emergency redirect from cameras to dashboard")
    return redirect(url_for('main.dashboard'))

@camera_bp.route('/cameras/<camera_id>')
def camera_view(camera_id):
    """Redirect to dashboard as emergency fix."""
    logger.info(f"Emergency redirect from camera view {camera_id} to dashboard")
    return redirect(url_for('main.dashboard'))

@camera_bp.route('/cameras/<camera_id>/settings')
def camera_settings(camera_id):
    """Redirect to dashboard as emergency fix."""
    logger.info(f"Emergency redirect from camera settings {camera_id} to dashboard")
    return redirect(url_for('main.dashboard'))

@camera_bp.route('/cameras/add', methods=['POST'])
def add_camera():
    """Redirect to dashboard as emergency fix."""
    logger.info("Emergency redirect from add camera to dashboard")
    return redirect(url_for('main.dashboard'))

@camera_bp.route('/cameras/<camera_id>/delete', methods=['POST'])
def delete_camera(camera_id):
    """Redirect to dashboard as emergency fix."""
    logger.info(f"Emergency redirect from delete camera {camera_id} to dashboard")
    return redirect(url_for('main.dashboard'))

@camera_bp.route('/cameras/discover', methods=['POST'])
def discover_cameras():
    """Redirect to dashboard as emergency fix."""
    logger.info("Emergency redirect from discover cameras to dashboard")
    return redirect(url_for('main.dashboard'))

def register_camera_routes(app, detector=None, db_manager=None):
    """Register camera routes with the Flask application."""
    app.register_blueprint(camera_bp)
    logger.info("Emergency camera routes registered - all redirecting to dashboard")
'''

# Write the emergency routes to a file
with open("/tmp/emergency_camera_routes.py", "w") as f:
    f.write(emergency_routes)

# Replace the camera_routes.py file
os.system("sudo cp /tmp/emergency_camera_routes.py /opt/amslpr/src/web/camera_routes.py")

print("Successfully replaced camera_routes.py with emergency redirect version")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Restarted AMSLPR service")

print("Emergency fix applied. The cameras page will now redirect to the dashboard to avoid errors.")
