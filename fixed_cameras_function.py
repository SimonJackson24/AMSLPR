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
