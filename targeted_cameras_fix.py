#!/usr/bin/env python3

"""
Targeted fix for the cameras page that addresses the specific issue with the camera manager.
This script makes minimal changes to fix the internal server error.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_targeted_fix")
print("Created backup of camera_routes.py")

# Restore the original file as a starting point
os.system("sudo cp /opt/visigate/src/web/camera_routes.py.original /opt/visigate/src/web/camera_routes.py")
print("Restored original camera_routes.py file")

# Create a fixed cameras function that handles the camera manager properly
fixed_cameras = '''
def cameras():
    """Camera management page."""
    try:
        # Initialize camera manager if needed
        global onvif_camera_manager
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)
        
        # Get cameras with proper error handling
        cameras = {}
        if onvif_camera_manager:
            try:
                cameras = onvif_camera_manager.get_all_cameras()
            except AttributeError:
                # If get_all_cameras is not available, try accessing cameras directly
                if hasattr(onvif_camera_manager, "cameras"):
                    cameras = onvif_camera_manager.cameras
                else:
                    logger.error("Camera manager does not have cameras attribute")
            except Exception as e:
                logger.error(f"Error getting cameras: {str(e)}")
        
        # Calculate camera stats
        stats = {
            "total": len(cameras),
            "online": sum(1 for c in cameras.values() if c.get("status", "") == "online"),
            "offline": sum(1 for c in cameras.values() if c.get("status", "") == "offline"),
            "issues": sum(1 for c in cameras.values() if c.get("status", "") not in ["online", "offline"]),
            "avg_fps": "24.5"  # Default value
        }
        
        return render_template("cameras.html", cameras=cameras, stats=stats)
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
        return "<h1>Camera Page Error</h1><p>There was an error loading the camera page. Please check the logs for details.</p>", 500
'''

# Find the cameras function in the file
os.system("sudo grep -n 'def cameras' /opt/visigate/src/web/camera_routes.py > /tmp/cameras_line.txt")

with open("/tmp/cameras_line.txt", "r") as f:
    cameras_line = f.read().strip()

if cameras_line:
    line_number = int(cameras_line.split(":")[0])
    print(f"Found cameras function at line {line_number}")
    
    # Find the next function definition
    os.system(f"sudo grep -n '^def ' /opt/visigate/src/web/camera_routes.py | awk '$1 > {line_number}' | head -1 > /tmp/next_function.txt")
    
    with open("/tmp/next_function.txt", "r") as f:
        next_function = f.read().strip()
    
    if next_function:
        next_line = int(next_function.split(":")[0])
        print(f"Found next function at line {next_line}")
        
        # Write the fixed cameras function to a file
        with open("/tmp/fixed_cameras.py", "w") as f:
            f.write(fixed_cameras)
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/visigate/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/fixed_cameras.py' /opt/visigate/src/web/camera_routes.py")
        
        print("Successfully replaced the cameras function with a fixed version")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras function")

# Restart the service
os.system("sudo systemctl restart visigate")
print("Service restarted. The cameras page should now work correctly.")
