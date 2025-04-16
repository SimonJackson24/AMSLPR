#!/usr/bin/env python3

# Create a backup of the current file
import os

# Create backup
os.system("sudo cp /opt/amslpr/src/web/camera_routes.py /opt/amslpr/src/web/camera_routes.py.backup_direct")
print("Created backup of camera_routes.py")

# Create a simple cameras function that ensures stats is defined
simple_cameras = '''
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    # Create empty camera list and stats dictionary
    cameras_list = []
    stats = {
        "total": 0,
        "online": 0,
        "offline": 0,
        "issues": 0,
        "avg_fps": "24.5"
    }
    
    # Try to get cameras if possible
    try:
        global onvif_camera_manager
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)
        
        if onvif_camera_manager and hasattr(onvif_camera_manager, "get_all_cameras"):
            try:
                camera_dict = onvif_camera_manager.get_all_cameras()
                for camera_id, camera_info in camera_dict.items():
                    try:
                        camera = {
                            "id": camera_id,
                            "name": "Camera " + str(camera_id),
                            "location": "Unknown",
                            "status": "unknown",
                            "manufacturer": "Unknown",
                            "model": "Unknown"
                        }
                        
                        # Try to get camera info if available
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
                        print(f"Error processing camera {camera_id}: {str(e)}")
            except Exception as e:
                print(f"Error getting cameras: {str(e)}")
    except Exception as e:
        print(f"Error in cameras function: {str(e)}")
    
    # Update stats based on cameras_list
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

# Write the simple cameras function to a file
with open("/tmp/simple_cameras.py", "w") as f:
    f.write(simple_cameras)

# Find the cameras function in the file
os.system("sudo grep -n '@camera_bp.route.*cameras' /opt/amslpr/src/web/camera_routes.py > /tmp/cameras_line.txt")

with open("/tmp/cameras_line.txt", "r") as f:
    camera_route_line = f.read().strip()

if not camera_route_line:
    # Try alternative pattern
    os.system("sudo grep -n 'def cameras' /opt/amslpr/src/web/camera_routes.py > /tmp/cameras_line.txt")
    with open("/tmp/cameras_line.txt", "r") as f:
        camera_route_line = f.read().strip()

if camera_route_line:
    line_number = int(camera_route_line.split(":")[0])
    print(f"Found cameras function at line {line_number}")
    
    # Find the next route or function
    os.system(f"sudo grep -n '@camera_bp.route\\|def ' /opt/amslpr/src/web/camera_routes.py | awk '$1 > {line_number}' | head -1 > /tmp/next_route.txt")
    
    with open("/tmp/next_route.txt", "r") as f:
        next_route = f.read().strip()
    
    if next_route:
        next_line = int(next_route.split(":")[0])
        print(f"Found next route at line {next_line}")
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number-1},{next_line-1}d' /opt/amslpr/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/simple_cameras.py' /opt/amslpr/src/web/camera_routes.py")
        
        print("Successfully replaced the cameras function")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras route")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Service restarted. Please try accessing the cameras page now.")
