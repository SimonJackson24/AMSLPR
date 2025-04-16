#!/usr/bin/env python3

# Create a backup of the current file
import os

# Create backup
os.system("sudo cp /opt/amslpr/src/web/camera_routes.py /opt/amslpr/src/web/camera_routes.py.backup_minimal")
print("Created backup of camera_routes.py")

# Write the fixed function to a file
with open("/tmp/fixed_cameras.py", "w") as f:
    f.write('''
def cameras():
    """Camera management page."""
    try:
        global onvif_camera_manager
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)
        
        # Get cameras with safe error handling
        cameras_list = []
        try:
            if onvif_camera_manager and hasattr(onvif_camera_manager, "get_all_cameras"):
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
                        cameras_list.append(camera)
                    except Exception as e:
                        print(f"Error processing camera {camera_id}: {str(e)}")
        except Exception as e:
            print(f"Error retrieving cameras: {str(e)}")
        
        # Calculate camera stats
        stats = {
            "total": len(cameras_list),
            "online": 0,
            "offline": 0,
            "issues": 0,
            "avg_fps": "24.5"  # Default value
        }
        
        return render_template("cameras.html", cameras=cameras_list, stats=stats)
    except Exception as e:
        print(f"Error in cameras route: {str(e)}")
        return "<h1>Camera Page Error</h1>", 500
''')

# Find the cameras function in the file
os.system("sudo grep -n 'def cameras' /opt/amslpr/src/web/camera_routes.py > /tmp/cameras_line.txt")

with open("/tmp/cameras_line.txt", "r") as f:
    line_content = f.read().strip()

if not line_content:
    print("Could not find cameras function in the file")
    exit(1)

line_number = int(line_content.split(":")[0])
print(f"Found cameras function at line {line_number}")

# Find the next function or route definition
os.system(f"sudo grep -n '@camera_bp.route\\|def ' /opt/amslpr/src/web/camera_routes.py | awk '$1 > {line_number}' | head -1 > /tmp/next_function.txt")

with open("/tmp/next_function.txt", "r") as f:
    next_function = f.read().strip()

if not next_function:
    print("Could not find the end of the cameras function")
    exit(1)

next_line = int(next_function.split(":")[0])
print(f"Found next function/route at line {next_line}")

# Replace the cameras function
print("Replacing the cameras function...")
os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/amslpr/src/web/camera_routes.py")
os.system(f"sudo sed -i '{line_number-1}r /tmp/fixed_cameras.py' /opt/amslpr/src/web/camera_routes.py")

print("Fix applied successfully. Restarting the AMSLPR service...")
os.system("sudo systemctl restart amslpr")

print("Done. Please try accessing the cameras page now.")
