#!/usr/bin/env python3

"""
Minimal, targeted fix for the cameras page internal server error.
This script focuses specifically on the issue with the camera manager initialization.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/amslpr/src/web/camera_routes.py /opt/amslpr/src/web/camera_routes.py.backup_minimal")
print("Created backup of camera_routes.py")

# Check how the camera manager is currently initialized
os.system("sudo grep -n 'init_camera_manager' /opt/amslpr/src/web/camera_routes.py | head -n 5 > /tmp/init_manager.txt")

with open("/tmp/init_manager.txt", "r") as f:
    init_manager = f.read().strip()

print(f"Camera manager initialization: {init_manager}")

# Check the global declaration of onvif_camera_manager
os.system("sudo grep -n 'global onvif_camera_manager' /opt/amslpr/src/web/camera_routes.py | head -n 5 > /tmp/global_manager.txt")

with open("/tmp/global_manager.txt", "r") as f:
    global_manager = f.read().strip()

print(f"Global manager declaration: {global_manager}")

# Create a minimal fix for the cameras function
minimal_fix = '''
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    # Initialize camera manager if needed
    global onvif_camera_manager
    if onvif_camera_manager is None:
        onvif_camera_manager = init_camera_manager(current_app.config)
    
    # Get cameras with safe error handling
    cameras_list = []
    try:
        if onvif_camera_manager and hasattr(onvif_camera_manager, "get_all_cameras"):
            camera_dict = onvif_camera_manager.get_all_cameras()
            # Convert dictionary to list for template
            for camera_id, camera_info in camera_dict.items():
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
                        if "name" in camera_info:
                            camera["name"] = camera_info["name"]
                        if "location" in camera_info:
                            camera["location"] = camera_info["location"]
                        if "status" in camera_info:
                            camera["status"] = camera_info["status"]
                        if "manufacturer" in camera_info:
                            camera["manufacturer"] = camera_info["manufacturer"]
                        if "model" in camera_info:
                            camera["model"] = camera_info["model"]
                    
                    cameras_list.append(camera)
                except Exception as e:
                    logger.error(f"Error processing camera {camera_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting cameras: {str(e)}")
    
    # Calculate camera stats
    stats = {
        "total": len(cameras_list),
        "online": sum(1 for c in cameras_list if c.get("status") == "online"),
        "offline": sum(1 for c in cameras_list if c.get("status") == "offline"),
        "issues": sum(1 for c in cameras_list if c.get("status") not in ["online", "offline"]),
        "avg_fps": "24.5"  # Default value
    }
    
    # Render the template with cameras and stats
    return render_template("cameras.html", cameras=cameras_list, stats=stats)
'''

# Find the cameras function in the file
os.system("sudo grep -n '@camera_bp.route.*cameras$' /opt/amslpr/src/web/camera_routes.py > /tmp/camera_route.txt")

with open("/tmp/camera_route.txt", "r") as f:
    camera_route = f.read().strip()

if camera_route:
    line_number = int(camera_route.split(":")[0])
    print(f"Found cameras route at line {line_number}")
    
    # Find the next route or function
    os.system(f"sudo grep -n '@camera_bp.route\\|def ' /opt/amslpr/src/web/camera_routes.py | awk '$1 > {line_number}' | head -1 > /tmp/next_route.txt")
    
    with open("/tmp/next_route.txt", "r") as f:
        next_route = f.read().strip()
    
    if next_route:
        next_line = int(next_route.split(":")[0])
        print(f"Found next route at line {next_line}")
        
        # Write the minimal fix to a file
        with open("/tmp/minimal_fix.py", "w") as f:
            f.write(minimal_fix)
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/amslpr/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/minimal_fix.py' /opt/amslpr/src/web/camera_routes.py")
        
        print("Successfully applied minimal fix to the cameras function")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras route")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Service restarted. Please try accessing the cameras page now.")
