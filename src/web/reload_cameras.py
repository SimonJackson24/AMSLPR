# Add this function to camera_routes.py after the init_camera_manager function
def reload_cameras_from_database():
    """Reload cameras from the database."""
    global onvif_camera_manager, db_manager
    
    if db_manager and onvif_camera_manager and hasattr(onvif_camera_manager, 'cameras'):
        try:
            logger.info("Loading cameras from database")
            cameras = db_manager.get_all_cameras()
            logger.info(f"Found {len(cameras)} cameras in database")
            
            # Add each camera to the manager if not already present
            for camera in cameras:
                try:
                    # Check if this is an RTSP camera (stored with rtsp- prefix)
                    if camera['ip'].startswith('rtsp-'):
                        camera_id = camera['ip']
                        # Skip if already in manager
                        if camera_id in onvif_camera_manager.cameras:
                            continue
                            
                        rtsp_url = camera['stream_uri']
                        
                        # Add directly to cameras dict
                        onvif_camera_manager.cameras[camera_id] = {
                            'camera': None,  # No ONVIF camera object
                            'info': {
                                'id': camera_id,
                                'name': camera['name'],
                                'location': camera['location'],
                                'status': 'connected',
                                'stream_uri': rtsp_url,
                                'rtsp_url': rtsp_url,
                                'manufacturer': camera['manufacturer'],
                                'model': camera['model']
                            },
                            'stream': None
                        }
                        logger.info(f"Added RTSP camera to manager: {camera_id}")
                    else:
                        # Regular ONVIF camera
                        # Skip if already in manager
                        if camera['ip'] in onvif_camera_manager.cameras:
                            continue
                            
                        camera_info = {
                            'ip': camera['ip'],
                            'port': camera['port'],
                            'username': camera['username'],
                            'password': camera['password']
                        }
                        
                        if 'stream_uri' in camera and camera['stream_uri']:
                            camera_info['rtsp_url'] = camera['stream_uri']
                        
                        logger.info(f"Adding ONVIF camera to manager: {camera_info}")
                        onvif_camera_manager.add_camera(camera_info)
                except Exception as e:
                    logger.error(f"Failed to add camera {camera['ip']}: {str(e)}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload cameras from database: {str(e)}")
    return False

# Add this code to the beginning of the cameras() function
def cameras():
    """Camera management page."""
    try:
        global onvif_camera_manager
        if onvif_camera_manager is None:
            logger.info("Camera manager not initialized, initializing now")
            init_camera_manager(current_app.config)
            
        # Reload cameras from database
        if db_manager and onvif_camera_manager:
            try:
                reload_cameras_from_database()
            except Exception as e:
                logger.error(f"Error reloading cameras: {str(e)}")
        
        # Rest of the function remains unchanged
