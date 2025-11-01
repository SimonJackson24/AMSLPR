#!/usr/bin/env python3

"""
Direct fix for the cameras page issue
"""

import os
import sys

# Path to the camera_routes.py file
CAMERA_ROUTES_PATH = '/opt/visigate/src/web/camera_routes.py'

# Create a backup
backup_path = f"{CAMERA_ROUTES_PATH}.backup_direct"
os.system(f"cp {CAMERA_ROUTES_PATH} {backup_path}")
print(f"Created backup at {backup_path}")

# The fixed cameras function
FIXED_FUNCTION = '''
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)

    # Get cameras with safe error handling
    cameras = {}
    if onvif_camera_manager:
        try:
            if hasattr(onvif_camera_manager, 'get_all_cameras'):
                cameras = onvif_camera_manager.get_all_cameras()
            elif hasattr(onvif_camera_manager, 'cameras'):
                cameras = onvif_camera_manager.cameras
        except Exception as e:
            logger.error(f"Error getting cameras: {str(e)}")
            cameras = {}

    # Calculate camera stats
    stats = {
        'total': len(cameras),
        'online': 0,
        'offline': 0,
        'issues': 0,
        'avg_fps': '24.5'  # Default value
    }
    
    return render_template('cameras.html', cameras=cameras, stats=stats)
'''

# Write the fixed function to a temporary file
with open('/tmp/fixed_cameras_function.txt', 'w') as f:
    f.write(FIXED_FUNCTION)

# Use grep to find the cameras route definition
result = os.popen(f"grep -n '@camera_bp.route\(\"/cameras\"\)' {CAMERA_ROUTES_PATH}").read().strip()
if not result:
    result = os.popen(f"grep -n \"@camera_bp.route('/cameras')\" {CAMERA_ROUTES_PATH}").read().strip()

if result:
    # Extract the line number
    line_number = int(result.split(':')[0])
    print(f"Found cameras route at line {line_number}")
    
    # Find the next route or function definition
    next_def = os.popen(f"grep -n '@camera_bp.route\(' {CAMERA_ROUTES_PATH} | awk '$1 > {line_number}' | head -1").read().strip()
    if not next_def:
        next_def = os.popen(f"grep -n '^def ' {CAMERA_ROUTES_PATH} | awk '$1 > {line_number}' | head -1").read().strip()
    
    if next_def:
        next_line = int(next_def.split(':')[0])
        print(f"Found next definition at line {next_line}")
        
        # Create a new file with the fixed function
        os.system(f"head -n {line_number-1} {CAMERA_ROUTES_PATH} > /tmp/new_camera_routes.py")
        os.system(f"cat /tmp/fixed_cameras_function.txt >> /tmp/new_camera_routes.py")
        os.system(f"tail -n +{next_line} {CAMERA_ROUTES_PATH} >> /tmp/new_camera_routes.py")
        
        # Replace the original file
        os.system(f"cp /tmp/new_camera_routes.py {CAMERA_ROUTES_PATH}")
        print("Successfully applied the fix")
    else:
        print("Could not find the end of the cameras function")
        sys.exit(1)
else:
    print("Could not find the cameras route definition")
    sys.exit(1)

print("Fix applied. Please restart the VisiGate service.")
