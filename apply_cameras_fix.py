#!/usr/bin/env python3

"""
Script to apply a targeted fix to the cameras function in camera_routes.py
This script will only modify the cameras function while preserving the rest of the file.
"""

import os
import re
import sys
import shutil
from datetime import datetime

# Path to the camera_routes.py file
CAMERA_ROUTES_PATH = '/opt/amslpr/src/web/camera_routes.py'

# The fixed cameras function
FIXED_CAMERAS_FUNCTION = '''
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    try:
        global onvif_camera_manager
        if onvif_camera_manager is None:
            logger.info("Camera manager not initialized, initializing now")
            init_camera_manager(current_app.config)
        
        # Get cameras with error handling
        cameras = []
        if onvif_camera_manager:
            try:
                # Try using get_all_cameras method if it exists
                if hasattr(onvif_camera_manager, 'get_all_cameras'):
                    camera_dict = onvif_camera_manager.get_all_cameras()
                    # Convert dictionary to list format expected by template
                    for camera_id, camera_info in camera_dict.items():
                        try:
                            camera = {
                                'id': camera_id,
                                'name': camera_info.get('name', 'Unknown'),
                                'location': camera_info.get('location', 'Unknown'),
                                'status': camera_info.get('status', 'unknown'),
                                'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                'model': camera_info.get('model', 'Unknown')
                            }
                            cameras.append(camera)
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
                # If cameras is still empty, try accessing the cameras attribute directly
                elif hasattr(onvif_camera_manager, 'cameras') and not cameras:
                    for camera_id, camera_data in onvif_camera_manager.cameras.items():
                        try:
                            # Extract camera info
                            if isinstance(camera_data, dict) and 'info' in camera_data:
                                camera_info = camera_data['info']
                            else:
                                camera_info = camera_data
                            
                            # Handle different data structures
                            if isinstance(camera_info, dict):
                                camera = {
                                    'id': camera_id,
                                    'name': camera_info.get('name', 'Unknown'),
                                    'location': camera_info.get('location', 'Unknown'),
                                    'status': camera_info.get('status', 'unknown'),
                                    'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                    'model': camera_info.get('model', 'Unknown')
                                }
                            else:
                                # Handle object-like camera info
                                camera = {
                                    'id': camera_id,
                                    'name': getattr(camera_info, 'name', 'Unknown'),
                                    'location': getattr(camera_info, 'location', 'Unknown'),
                                    'status': getattr(camera_info, 'status', 'unknown'),
                                    'manufacturer': getattr(camera_info, 'manufacturer', 'Unknown'),
                                    'model': getattr(camera_info, 'model', 'Unknown')
                                }
                            
                            cameras.append(camera)
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error retrieving cameras: {str(e)}")
        
        # Calculate camera stats
        stats = {
            'total': len(cameras),
            'online': sum(1 for c in cameras if c.get('status') == 'online'),
            'offline': sum(1 for c in cameras if c.get('status') == 'offline'),
            'issues': sum(1 for c in cameras if c.get('status') not in ['online', 'offline']),
            'avg_fps': '24.5'  # Default value
        }
        
        return render_template('cameras.html', cameras=cameras, stats=stats)
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Return a simple message instead of trying to render the template
        return "<h1>Camera Page Temporarily Unavailable</h1><p>We're experiencing technical difficulties with the camera management page. Please try again later.</p>", 503
'''

def main():
    # Check if the camera_routes.py file exists
    if not os.path.exists(CAMERA_ROUTES_PATH):
        print(f"Error: {CAMERA_ROUTES_PATH} does not exist")
        sys.exit(1)
    
    # Create a backup of the original file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{CAMERA_ROUTES_PATH}.backup_{timestamp}"
    shutil.copy2(CAMERA_ROUTES_PATH, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Read the original file
    with open(CAMERA_ROUTES_PATH, 'r') as f:
        content = f.read()
    
    # Find and replace the cameras function
    # Look for the function definition and everything until the next function or route
    pattern = r'@camera_bp\.route\(\'?\/cameras\'?\)[^@]*?def cameras\(\):[\s\S]*?(?=@camera_bp\.route|def \w+\(|$)'
    
    if re.search(pattern, content):
        # Replace the cameras function
        new_content = re.sub(pattern, FIXED_CAMERAS_FUNCTION, content)
        
        # Write the modified content back to the file
        with open(CAMERA_ROUTES_PATH, 'w') as f:
            f.write(new_content)
        
        print("Successfully applied the fix to the cameras function")
        print("Restart the AMSLPR service to apply the changes")
    else:
        print("Error: Could not find the cameras function in the file")
        sys.exit(1)

if __name__ == '__main__':
    main()
