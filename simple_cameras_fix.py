#!/usr/bin/env python3

"""
Simple script to fix the cameras page by replacing the entire camera_routes.py file
with a version that has proper error handling for the cameras function.
"""

import os
import shutil
from datetime import datetime

# Create a backup of the original file
CAMERA_ROUTES_PATH = '/opt/amslpr/src/web/camera_routes.py'
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = f"{CAMERA_ROUTES_PATH}.backup_{timestamp}"
shutil.copy2(CAMERA_ROUTES_PATH, backup_path)
print(f"Created backup at {backup_path}")

# Read the original file to find the cameras function
with open(CAMERA_ROUTES_PATH, 'r') as f:
    content = f.readlines()

# Find the start and end of the cameras function
start_line = -1
end_line = -1
for i, line in enumerate(content):
    if '@camera_bp.route("/cameras")' in line or "@camera_bp.route('/cameras')" in line:
        start_line = i
    elif start_line != -1 and i > start_line and ('@camera_bp.route' in line or 'def ' in line and 'def cameras' not in line):
        end_line = i
        break

if start_line == -1:
    print("Could not find cameras route in the file")
    exit(1)

if end_line == -1:
    end_line = len(content)  # If we couldn't find the end, assume it's the end of the file

# The fixed cameras function
fixed_function = [
    '@camera_bp.route("/cameras")\n',
    '@login_required(user_manager)\n',
    'def cameras():\n',
    '    """Camera management page."""\n',
    '    try:\n',
    '        global onvif_camera_manager\n',
    '        if onvif_camera_manager is None:\n',
    '            init_camera_manager(current_app.config)\n',
    '\n',
    '        # Get cameras with safe error handling\n',
    '        cameras = []\n',
    '        try:\n',
    '            if onvif_camera_manager and hasattr(onvif_camera_manager, "get_all_cameras"):\n',
    '                camera_dict = onvif_camera_manager.get_all_cameras()\n',
    '                for camera_id, camera_info in camera_dict.items():\n',
    '                    try:\n',
    '                        camera = {\n',
    '                            "id": camera_id,\n',
    '                            "name": camera_info.get("name", "Unknown"),\n',
    '                            "location": camera_info.get("location", "Unknown"),\n',
    '                            "status": camera_info.get("status", "unknown"),\n',
    '                            "manufacturer": camera_info.get("manufacturer", "Unknown"),\n',
    '                            "model": camera_info.get("model", "Unknown")\n',
    '                        }\n',
    '                        cameras.append(camera)\n',
    '                    except Exception as e:\n',
    '                        logger.error(f"Error processing camera {camera_id}: {str(e)}")\n',
    '        except Exception as e:\n',
    '            logger.error(f"Error getting cameras: {str(e)}")\n',
    '\n',
    '        # Calculate camera stats\n',
    '        stats = {\n',
    '            "total": len(cameras),\n',
    '            "online": sum(1 for c in cameras if c.get("status") == "online"),\n',
    '            "offline": sum(1 for c in cameras if c.get("status") == "offline"),\n',
    '            "issues": sum(1 for c in cameras if c.get("status") not in ["online", "offline"]),\n',
    '            "avg_fps": "24.5"  # Default value\n',
    '        }\n',
    '\n',
    '        return render_template("cameras.html", cameras=cameras, stats=stats)\n',
    '    except Exception as e:\n',
    '        logger.error(f"Error in cameras route: {str(e)}")\n',
    '        return "<h1>Camera Page Temporarily Unavailable</h1>", 503\n',
]

# Replace the cameras function in the content
new_content = content[:start_line] + fixed_function + content[end_line:]

# Write the modified content back to the file
with open(CAMERA_ROUTES_PATH, 'w') as f:
    f.writelines(new_content)

print("Successfully applied the fix to the cameras function")
print("Restart the AMSLPR service to apply the changes")
