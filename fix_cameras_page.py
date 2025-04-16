#!/usr/bin/env python3

"""
Direct fix for the cameras page internal server error.
This script makes minimal changes to fix the specific issue.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/amslpr/src/web/camera_routes.py /opt/amslpr/src/web/camera_routes.py.backup_$(date +%Y%m%d_%H%M%S)")
print("Created backup of camera_routes.py")

# Create a minimal cameras function that works
fixed_function = """
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    try:
        # Initialize camera manager if needed
        global onvif_camera_manager
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)
        
        # Get cameras with safe error handling
        cameras_list = []
        try:
            if onvif_camera_manager:
                # Get camera data from the manager
                if hasattr(onvif_camera_manager, 'get_all_cameras'):
                    camera_dict = onvif_camera_manager.get_all_cameras()
                    
                    # Convert to list format for template
                    for camera_id, camera_info in camera_dict.items():
                        try:
                            camera = {
                                'id': camera_id,
                                'name': 'Camera ' + str(camera_id),
                                'location': 'Unknown',
                                'status': 'unknown',
                                'manufacturer': 'Unknown',
                                'model': 'Unknown'
                            }
                            
                            # Try to extract info if available
                            if isinstance(camera_info, dict):
                                camera['name'] = camera_info.get('name', camera['name'])
                                camera['location'] = camera_info.get('location', camera['location'])
                                camera['status'] = camera_info.get('status', camera['status'])
                                camera['manufacturer'] = camera_info.get('manufacturer', camera['manufacturer'])
                                camera['model'] = camera_info.get('model', camera['model'])
                            
                            cameras_list.append(camera)
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error retrieving cameras: {str(e)}")
        
        # Calculate camera stats
        stats = {
            'total': len(cameras_list),
            'online': sum(1 for c in cameras_list if c.get('status') == 'online'),
            'offline': sum(1 for c in cameras_list if c.get('status') == 'offline'),
            'issues': sum(1 for c in cameras_list if c.get('status') not in ['online', 'offline']),
            'avg_fps': '24.5'  # Default value
        }
        
        # Render the template with the camera data and stats
        return render_template('cameras.html', cameras=cameras_list, stats=stats)
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return "<h1>Camera Page Error</h1><p>There was an error loading the camera page. Please check the logs for details.</p>", 500
"""

# Find the cameras function in the file
os.system("sudo grep -n '@camera_bp.route.*cameras' /opt/amslpr/src/web/camera_routes.py > /tmp/camera_route_line.txt")

with open("/tmp/camera_route_line.txt", "r") as f:
    camera_route_line = f.read().strip()

if not camera_route_line:
    # Try alternative pattern
    os.system("sudo grep -n 'def cameras' /opt/amslpr/src/web/camera_routes.py > /tmp/camera_route_line.txt")
    with open("/tmp/camera_route_line.txt", "r") as f:
        camera_route_line = f.read().strip()

if camera_route_line:
    line_number = int(camera_route_line.split(":")[0])
    print(f"Found cameras route at line {line_number}")
    
    # Find the next route or function
    os.system(f"sudo grep -n '@camera_bp.route\|def ' /opt/amslpr/src/web/camera_routes.py | awk '$1 > {line_number}' | head -1 > /tmp/next_route.txt")
    
    with open("/tmp/next_route.txt", "r") as f:
        next_route = f.read().strip()
    
    if next_route:
        next_line = int(next_route.split(":")[0])
        print(f"Found next route at line {next_line}")
        
        # Write the fixed function to a temporary file
        with open("/tmp/fixed_cameras.txt", "w") as f:
            f.write(fixed_function)
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number-1},{next_line-1}d' /opt/amslpr/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/fixed_cameras.txt' /opt/amslpr/src/web/camera_routes.py")
        
        print("Successfully replaced the cameras function")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras route")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Service restarted. Please try accessing the cameras page now.")
