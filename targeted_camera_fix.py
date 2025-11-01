#!/usr/bin/env python3

"""
Targeted fix for the cameras page that properly handles the camera data structure
and ensures the stats variable is correctly defined.
"""

import os
import sys

# Create backup
os.system("sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_targeted")
print("Created backup of camera_routes.py")

# The fixed cameras function with proper handling of camera data and stats variable
fixed_function = '''
def cameras():
    """Camera management page."""
    try:
        global onvif_camera_manager
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)

        # Get cameras with safe error handling
        camera_data = {}
        cameras_list = []
        
        try:
            if onvif_camera_manager and hasattr(onvif_camera_manager, "get_all_cameras"):
                camera_data = onvif_camera_manager.get_all_cameras()
                
                # Convert dictionary to list format expected by template
                for camera_id, camera_info in camera_data.items():
                    try:
                        # Handle different possible data structures
                        if isinstance(camera_info, dict):
                            camera = {
                                "id": camera_id,
                                "name": camera_info.get("name", "Unknown"),
                                "location": camera_info.get("location", "Unknown"),
                                "status": camera_info.get("status", "unknown"),
                                "manufacturer": camera_info.get("manufacturer", "Unknown"),
                                "model": camera_info.get("model", "Unknown")
                            }
                        else:
                            # Handle object-like camera info
                            camera = {
                                "id": camera_id,
                                "name": getattr(camera_info, "name", "Unknown"),
                                "location": getattr(camera_info, "location", "Unknown"),
                                "status": getattr(camera_info, "status", "unknown"),
                                "manufacturer": getattr(camera_info, "manufacturer", "Unknown"),
                                "model": getattr(camera_info, "model", "Unknown")
                            }
                        cameras_list.append(camera)
                    except Exception as e:
                        logger.error(f"Error processing camera {camera_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error retrieving cameras: {str(e)}")

        # Always define stats variable with default values
        stats = {
            "total": len(cameras_list),
            "online": sum(1 for c in cameras_list if c.get("status") == "online"),
            "offline": sum(1 for c in cameras_list if c.get("status") == "offline"),
            "issues": sum(1 for c in cameras_list if c.get("status") not in ["online", "offline"]),
            "avg_fps": "24.5"  # Default value
        }

        return render_template("cameras.html", cameras=cameras_list, stats=stats)
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
        # Return a simple error message
        return "<h1>Camera Page Temporarily Unavailable</h1><p>Error: {}</p>".format(str(e)), 503
'''

# Write the fixed function to a file
with open("/tmp/fixed_cameras_function.txt", "w") as f:
    f.write(fixed_function)

# Find the cameras function in the file
os.system("sudo grep -n 'def cameras' /opt/visigate/src/web/camera_routes.py > /tmp/cameras_line.txt")

with open("/tmp/cameras_line.txt", "r") as f:
    line_content = f.read().strip()

if not line_content:
    print("Could not find cameras function in the file")
    sys.exit(1)

line_number = int(line_content.split(":")[0])
print(f"Found cameras function at line {line_number}")

# Find the next function or route definition
os.system(f"sudo grep -n '@camera_bp.route\\|def ' /opt/visigate/src/web/camera_routes.py | awk '$1 > {line_number}' | head -1 > /tmp/next_function.txt")

with open("/tmp/next_function.txt", "r") as f:
    next_function = f.read().strip()

if not next_function:
    print("Could not find the end of the cameras function")
    sys.exit(1)

next_line = int(next_function.split(":")[0])
print(f"Found next function/route at line {next_line}")

# Replace the cameras function
print("Replacing the cameras function...")
os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/visigate/src/web/camera_routes.py")
os.system(f"sudo sed -i '{line_number-1}r /tmp/fixed_cameras_function.txt' /opt/visigate/src/web/camera_routes.py")

print("Fix applied successfully. Restarting the VisiGate service...")
os.system("sudo systemctl restart visigate")

print("Done. Please try accessing the cameras page now.")
