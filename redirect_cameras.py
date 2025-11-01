#!/usr/bin/env python3

"""
Simple redirect fix for the cameras page.
This script modifies the cameras route to redirect to the dashboard,
which will prevent the internal server error while a proper fix is developed.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_redirect")
print("Created backup of camera_routes.py")

# Create a simple redirect for the cameras route
redirect_route = """
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Temporarily redirect to dashboard to prevent internal server error."""
    return redirect(url_for('dashboard_bp.dashboard'))
"""

# Write the redirect route to a temporary file
with open("/tmp/redirect_route.txt", "w") as f:
    f.write(redirect_route)

# Apply the redirect route
os.system("sudo sed -i '/@camera_bp.route(\\'\\?\/cameras\\'\\?)/,/def cameras/!b;/@camera_bp.route(\\'\\?\/cameras\\'\\?)/,/def cameras/!d;/@camera_bp.route(\\'\\?\/cameras\\'\\?)/r /tmp/redirect_route.txt' /opt/visigate/src/web/camera_routes.py")

print("Applied redirect to the cameras route")

# Restart the service
os.system("sudo systemctl restart visigate")
print("Service restarted. The cameras page will now redirect to the dashboard.")
