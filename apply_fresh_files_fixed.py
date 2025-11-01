#!/usr/bin/env python3

"""
Script to apply fresh versions of camera_routes.py and cameras.html to fix the internal server error.
"""

import os

# Create backups of the original files
os.system("sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_fresh 2>/dev/null || true")
os.system("sudo cp /opt/visigate/src/web/templates/cameras.html /opt/visigate/src/web/templates/cameras.html.backup_fresh 2>/dev/null || true")
print("Created backups of original files")

# Copy the fresh files to the correct locations
os.system("sudo cp /home/automate/fresh_camera_routes.py /opt/visigate/src/web/camera_routes.py")
os.system("sudo cp /home/automate/fresh_cameras.html /opt/visigate/src/web/templates/cameras.html")
print("Applied fresh versions of camera_routes.py and cameras.html")

# Restart the service
os.system("sudo systemctl restart visigate")
print("Restarted VisiGate service")

print("Fix applied. The cameras page should now work without errors.")
