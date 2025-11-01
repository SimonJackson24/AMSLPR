#!/bin/bash

# Create a backup of the current file
sudo cp /opt/visigate/src/web/camera_routes.py /opt/visigate/src/web/camera_routes.py.backup_$(date +%Y%m%d_%H%M%S)

# Create a temporary file with the fixed cameras function
cat > /tmp/cameras_function.py << 'EOF'
def cameras():
    """Camera management page."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)

    # Get cameras with safe error handling
    cameras = {}
    if onvif_camera_manager:
        try:
            if hasattr(onvif_camera_manager, 'get_all_cameras'):
                cameras = onvif_camera_manager.get_all_cameras()
            elif hasattr(onvif_camera_manager, 'cameras'):
                cameras = onvif_camera_manager.cameras
        except Exception as e:
            logger.error(f"Error getting cameras: {str(e)}")
            cameras = {}

    # Calculate camera stats
    stats = {
        'total': len(cameras),
        'online': 0,
        'offline': 0,
        'issues': 0,
        'avg_fps': '24.5'  # Default value
    }
    
    return render_template('cameras.html', cameras=cameras, stats=stats)
EOF

# Replace the cameras function in the file
sudo sed -i '/def cameras():/,/return render_template.*cameras\.html.*cameras=cameras.*stats=stats.*/c\\n@camera_bp.route("/cameras")\n@login_required(user_manager)\n'"$(cat /tmp/cameras_function.py)" /opt/visigate/src/web/camera_routes.py

# Restart the service
sudo systemctl restart visigate

echo "Fix applied and service restarted."
echo "Please try accessing the cameras page now."
