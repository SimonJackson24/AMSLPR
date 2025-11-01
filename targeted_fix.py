#!/usr/bin/env python3

"""
Targeted fix for the cameras page internal server error.
This script makes minimal changes to fix the specific issue with ONVIF camera handling.
"""

import os
import shutil
import sys

# Path to the camera_routes.py file
CAMERA_ROUTES_PATH = '/opt/visigate/src/web/camera_routes.py'

# Create a backup
backup_path = f"{CAMERA_ROUTES_PATH}.backup_fix"
shutil.copy2(CAMERA_ROUTES_PATH, backup_path)
print(f"Created backup at {backup_path}")

# Read the file
with open(CAMERA_ROUTES_PATH, 'r') as f:
    content = f.read()

# Find the cameras function
if 'def cameras():' in content:
    # The specific line that's likely causing the issue
    if 'cameras = onvif_camera_manager.get_all_cameras() if onvif_camera_manager else {}' in content:
        # Replace with safer code that handles errors
        fixed_content = content.replace(
            'cameras = onvif_camera_manager.get_all_cameras() if onvif_camera_manager else {}',
            '''
    # Get cameras with safe error handling
    cameras = {}
    if onvif_camera_manager:
        try:
            cameras = onvif_camera_manager.get_all_cameras()
        except Exception as e:
            logger.error(f"Error getting cameras: {str(e)}")
            cameras = {}
'''
        )
        
        # Write the fixed content
        with open(CAMERA_ROUTES_PATH, 'w') as f:
            f.write(fixed_content)
        
        print("Successfully applied the targeted fix")
    else:
        print("Could not find the specific line causing the issue")
        sys.exit(1)
else:
    print("Could not find the cameras function")
    sys.exit(1)

print("Fix applied. Please restart the VisiGate service.")
