#!/usr/bin/env python3

"""
Diagnostic script to identify the root cause of the cameras page error
by adding detailed logging throughout the execution path.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/amslpr/src/web/camera_routes.py /opt/amslpr/src/web/camera_routes.py.backup_diagnostic")
print("Created backup of camera_routes.py")

# Add detailed logging to the cameras function
diagnostic_cameras = '''
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    print("DEBUG: Entering cameras function")
    
    # Create empty camera list and stats dictionary
    cameras_list = []
    stats = {
        "total": 0,
        "online": 0,
        "offline": 0,
        "issues": 0,
        "avg_fps": "24.5"
    }
    print(f"DEBUG: Initial stats: {stats}")
    
    # Try to get cameras if possible
    try:
        print("DEBUG: Accessing onvif_camera_manager")
        global onvif_camera_manager
        print(f"DEBUG: onvif_camera_manager exists: {onvif_camera_manager is not None}")
        
        if onvif_camera_manager is None:
            print("DEBUG: Initializing camera manager")
            init_camera_manager(current_app.config)
            print(f"DEBUG: After init, onvif_camera_manager exists: {onvif_camera_manager is not None}")
        
        if onvif_camera_manager:
            print(f"DEBUG: onvif_camera_manager type: {type(onvif_camera_manager)}")
            print(f"DEBUG: onvif_camera_manager has get_all_cameras: {hasattr(onvif_camera_manager, 'get_all_cameras')}")
            
            if hasattr(onvif_camera_manager, "get_all_cameras"):
                try:
                    print("DEBUG: Calling get_all_cameras")
                    camera_dict = onvif_camera_manager.get_all_cameras()
                    print(f"DEBUG: get_all_cameras returned type: {type(camera_dict)}")
                    print(f"DEBUG: get_all_cameras returned {len(camera_dict) if isinstance(camera_dict, dict) else 'not a dict'} items")
                    
                    for camera_id, camera_info in camera_dict.items():
                        try:
                            print(f"DEBUG: Processing camera {camera_id}, info type: {type(camera_info)}")
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
                            print(f"DEBUG: Added camera to list, now have {len(cameras_list)} cameras")
                        except Exception as e:
                            print(f"DEBUG: Error processing camera {camera_id}: {str(e)}")
                except Exception as e:
                    print(f"DEBUG: Error getting cameras: {str(e)}")
            else:
                print("DEBUG: onvif_camera_manager does not have get_all_cameras method")
        else:
            print("DEBUG: onvif_camera_manager is None after initialization attempt")
    except Exception as e:
        print(f"DEBUG: Error in cameras function: {str(e)}")
    
    # Update stats based on cameras_list
    print(f"DEBUG: Updating stats based on {len(cameras_list)} cameras")
    stats = {
        "total": len(cameras_list),
        "online": sum(1 for c in cameras_list if c.get("status") == "online"),
        "offline": sum(1 for c in cameras_list if c.get("status") == "offline"),
        "issues": sum(1 for c in cameras_list if c.get("status") not in ["online", "offline"]),
        "avg_fps": "24.5"  # Default value
    }
    print(f"DEBUG: Final stats: {stats}")
    
    # Render the template with cameras and stats
    print(f"DEBUG: Rendering template with cameras={cameras_list}, stats={stats}")
    try:
        result = render_template("cameras.html", cameras=cameras_list, stats=stats)
        print("DEBUG: Template rendered successfully")
        return result
    except Exception as e:
        print(f"DEBUG: Error rendering template: {str(e)}")
        return f"<h1>Error rendering cameras template</h1><p>{str(e)}</p>", 500
'''

# Find the cameras function in the file
os.system("sudo grep -n '@camera_bp.route.*cameras' /opt/amslpr/src/web/camera_routes.py > /tmp/camera_route.txt")

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
        
        # Write the diagnostic cameras function to a file
        with open("/tmp/diagnostic_cameras.py", "w") as f:
            f.write(diagnostic_cameras)
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/amslpr/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/diagnostic_cameras.py' /opt/amslpr/src/web/camera_routes.py")
        
        print("Successfully added diagnostic logging to the cameras function")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras route")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Service restarted. Please try accessing the cameras page and then check the logs.")
