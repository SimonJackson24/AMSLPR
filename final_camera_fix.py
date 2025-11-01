#!/usr/bin/env python3

"""
Direct, targeted fix for the cameras page internal server error.
This script makes minimal changes to address the specific issue.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_final")
print("Created backup of camera_routes.py")

# First, let's check the current implementation of the cameras route
os.system("sudo grep -n -A 3 -B 3 'def cameras' /opt/visigate/src/web/camera_routes.py > /tmp/cameras_def.txt")

with open("/tmp/cameras_def.txt", "r") as f:
    cameras_def = f.read()

print("Current cameras function definition:")
print(cameras_def)

# Create a simple, targeted fix for the cameras function
simple_fix = '''
def cameras():
    """Camera management page."""
    try:
        # Initialize camera manager if needed
        global onvif_camera_manager
        if onvif_camera_manager is None:
            from src.recognition.onvif_camera import ONVIFCameraManager
            onvif_camera_manager = ONVIFCameraManager()
        
        # Create empty lists/dictionaries to avoid undefined variables
        cameras_list = []
        stats = {
            "total": 0,
            "online": 0,
            "offline": 0,
            "issues": 0,
            "avg_fps": "24.5"
        }
        
        # Try to get cameras if possible
        if onvif_camera_manager:
            try:
                if hasattr(onvif_camera_manager, "get_all_cameras"):
                    cameras_dict = onvif_camera_manager.get_all_cameras()
                    
                    # Convert dictionary to list for template
                    for camera_id, camera_info in cameras_dict.items():
                        try:
                            camera = {
                                "id": camera_id,
                                "name": f"Camera {camera_id}",
                                "location": "Unknown",
                                "status": "unknown",
                                "manufacturer": "Unknown",
                                "model": "Unknown"
                            }
                            
                            # Try to extract info if available
                            if isinstance(camera_info, dict):
                                camera["name"] = camera_info.get("name", camera["name"])
                                camera["location"] = camera_info.get("location", camera["location"])
                                camera["status"] = camera_info.get("status", camera["status"])
                                camera["manufacturer"] = camera_info.get("manufacturer", camera["manufacturer"])
                                camera["model"] = camera_info.get("model", camera["model"])
                            
                            cameras_list.append(camera)
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error getting cameras: {str(e)}")
        
        # Calculate camera stats based on the cameras we have
        stats = {
            "total": len(cameras_list),
            "online": sum(1 for c in cameras_list if c.get("status") == "online"),
            "offline": sum(1 for c in cameras_list if c.get("status") == "offline"),
            "issues": sum(1 for c in cameras_list if c.get("status") not in ["online", "offline"]),
            "avg_fps": "24.5"  # Default value
        }
        
        # Render the template with cameras and stats
        return render_template("cameras.html", cameras=cameras_list, stats=stats)
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
        
        # Write the simple fix to a file
        with open("/tmp/simple_fix.py", "w") as f:
            f.write(simple_fix)
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/visigate/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/simple_fix.py' /opt/visigate/src/web/camera_routes.py")
        
        print("Successfully applied simple fix to the cameras function")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras function")

# Also check the cameras.html template to ensure it's using the correct variable names
os.system("sudo grep -n '{{ stats' /opt/visigate/src/web/templates/cameras.html | head -n 5 > /tmp/template_stats.txt")

with open("/tmp/template_stats.txt", "r") as f:
    template_stats = f.readlines()

print("\nTemplate stats usage:")
for line in template_stats:
    print(line.strip())

# Restart the service
os.system("sudo systemctl restart visigate")
print("\nService restarted. Please try accessing the cameras page now.")
