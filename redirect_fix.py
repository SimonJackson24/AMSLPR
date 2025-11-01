#!/usr/bin/env python3

"""
Redirect fix for the cameras page that temporarily redirects to the dashboard
to prevent the internal server error while a proper fix is developed.
"""

import os

# Create a backup of the current file
os.system("sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_redirect")
print("Created backup of camera_routes.py")

# Create a simple redirect function that will prevent the internal server error
redirect_function = '''
@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Temporarily redirect to dashboard to prevent internal server error."""
    # Log that we're redirecting
    logger.info("Redirecting from /cameras to /dashboard (temporary fix)")
    
    # Return a redirect to the dashboard
    return redirect(url_for('dashboard_bp.dashboard'))
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
        
        # Write the redirect function to a file
        with open("/tmp/redirect_function.py", "w") as f:
            f.write(redirect_function)
        
        # Replace the cameras function
        os.system(f"sudo sed -i '{line_number},{next_line-1}d' /opt/visigate/src/web/camera_routes.py")
        os.system(f"sudo sed -i '{line_number-1}r /tmp/redirect_function.py' /opt/visigate/src/web/camera_routes.py")
        
        print("Successfully replaced the cameras function with a redirect")
    else:
        print("Could not find the end of the cameras function")
else:
    print("Could not find the cameras function")

# Restart the service
os.system("sudo systemctl restart visigate")
print("\nService restarted. The cameras page will now redirect to the dashboard to prevent the internal server error.")
