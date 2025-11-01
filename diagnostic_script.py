#!/usr/bin/env python3

"""
Diagnostic script to identify the exact cause of the 500 Internal Server Error on the cameras page.
"""

import os
import sys
import traceback
import logging
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VisiGate.diagnostics')

# Create a file handler for the log file
log_file = '/tmp/visigate_diagnostics.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def diagnose_camera_routes():
    """Diagnose issues with camera_routes.py"""
    logger.info("Starting camera_routes.py diagnostics")
    
    try:
        # Import the camera_routes module
        sys.path.append('/opt/visigate')
        from src.web.camera_routes import camera_bp, init_camera_manager, onvif_camera_manager
        
        logger.info(f"Successfully imported camera_routes module")
        logger.info(f"camera_bp: {camera_bp}")
        logger.info(f"onvif_camera_manager type: {type(onvif_camera_manager)}")
        
        # Check if onvif_camera_manager is None
        if onvif_camera_manager is None:
            logger.warning("onvif_camera_manager is None")
            
            # Try to initialize it
            try:
                from flask import Flask
                app = Flask(__name__)
                app.config.from_pyfile('/opt/visigate/config.py')
                init_camera_manager(app.config)
                logger.info(f"After initialization, onvif_camera_manager: {onvif_camera_manager}")
            except Exception as e:
                logger.error(f"Failed to initialize camera manager: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            # Check if onvif_camera_manager has the expected attributes and methods
            logger.info(f"onvif_camera_manager attributes: {dir(onvif_camera_manager)}")
            
            if hasattr(onvif_camera_manager, 'cameras'):
                logger.info(f"onvif_camera_manager.cameras type: {type(onvif_camera_manager.cameras)}")
                logger.info(f"onvif_camera_manager.cameras length: {len(onvif_camera_manager.cameras)}")
                
                # Log the first camera if available
                if onvif_camera_manager.cameras:
                    first_camera_key = next(iter(onvif_camera_manager.cameras))
                    logger.info(f"First camera key: {first_camera_key}")
                    logger.info(f"First camera type: {type(onvif_camera_manager.cameras[first_camera_key])}")
                    logger.info(f"First camera attributes: {dir(onvif_camera_manager.cameras[first_camera_key])}")
            else:
                logger.warning("onvif_camera_manager does not have 'cameras' attribute")
            
            if hasattr(onvif_camera_manager, 'get_all_cameras'):
                logger.info("onvif_camera_manager has 'get_all_cameras' method")
                try:
                    cameras = onvif_camera_manager.get_all_cameras()
                    logger.info(f"get_all_cameras returned: {cameras}")
                except Exception as e:
                    logger.error(f"Error calling get_all_cameras: {str(e)}")
                    logger.error(traceback.format_exc())
            else:
                logger.warning("onvif_camera_manager does not have 'get_all_cameras' method")
    except Exception as e:
        logger.error(f"Error in diagnose_camera_routes: {str(e)}")
        logger.error(traceback.format_exc())

def diagnose_templates():
    """Diagnose issues with templates"""
    logger.info("Starting template diagnostics")
    
    try:
        # Check if the cameras.html template exists
        template_path = '/opt/visigate/src/web/templates/cameras.html'
        if os.path.exists(template_path):
            logger.info(f"cameras.html template exists")
            
            # Check the template content for stats references
            with open(template_path, 'r') as f:
                template_content = f.read()
                
            stats_references = [line.strip() for line in template_content.split('\n') if 'stats' in line]
            logger.info(f"Stats references in template: {stats_references}")
        else:
            logger.warning(f"cameras.html template does not exist at {template_path}")
    except Exception as e:
        logger.error(f"Error in diagnose_templates: {str(e)}")
        logger.error(traceback.format_exc())

def diagnose_onvif_camera():
    """Diagnose issues with onvif_camera.py"""
    logger.info("Starting onvif_camera.py diagnostics")
    
    try:
        # Import the onvif_camera module
        sys.path.append('/opt/visigate')
        from src.recognition.onvif_camera import ONVIFCameraManager
        
        logger.info(f"Successfully imported ONVIFCameraManager")
        logger.info(f"ONVIFCameraManager attributes: {dir(ONVIFCameraManager)}")
        
        # Create a new instance for testing
        try:
            manager = ONVIFCameraManager()
            logger.info(f"Created new ONVIFCameraManager instance: {manager}")
            logger.info(f"Manager attributes: {dir(manager)}")
            
            if hasattr(manager, 'cameras'):
                logger.info(f"manager.cameras type: {type(manager.cameras)}")
                logger.info(f"manager.cameras length: {len(manager.cameras)}")
            else:
                logger.warning("manager does not have 'cameras' attribute")
            
            if hasattr(manager, 'get_all_cameras'):
                logger.info("manager has 'get_all_cameras' method")
                try:
                    cameras = manager.get_all_cameras()
                    logger.info(f"get_all_cameras returned: {cameras}")
                except Exception as e:
                    logger.error(f"Error calling get_all_cameras: {str(e)}")
                    logger.error(traceback.format_exc())
            else:
                logger.warning("manager does not have 'get_all_cameras' method")
        except Exception as e:
            logger.error(f"Error creating ONVIFCameraManager instance: {str(e)}")
            logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error in diagnose_onvif_camera: {str(e)}")
        logger.error(traceback.format_exc())

def diagnose_flask_app():
    """Diagnose issues with the Flask app"""
    logger.info("Starting Flask app diagnostics")
    
    try:
        # Import the app module
        sys.path.append('/opt/visigate')
        from src.web.app import app
        
        logger.info(f"Successfully imported app")
        logger.info(f"App routes: {app.url_map}")
        
        # Check if the cameras route is registered
        cameras_route_found = False
        for rule in app.url_map.iter_rules():
            if rule.endpoint == 'camera.cameras':
                cameras_route_found = True
                logger.info(f"Found cameras route: {rule}")
                break
        
        if not cameras_route_found:
            logger.warning("Cameras route not found in app.url_map")
    except Exception as e:
        logger.error(f"Error in diagnose_flask_app: {str(e)}")
        logger.error(traceback.format_exc())

def diagnose_error_logs():
    """Diagnose issues from error logs"""
    logger.info("Starting error log diagnostics")
    
    try:
        # Check the systemd journal for errors
        import subprocess
        cmd = "journalctl -u visigate -n 200 | grep -i error"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            logger.info(f"Found errors in journal:\n{result.stdout}")
        else:
            logger.info("No errors found in journal")
    except Exception as e:
        logger.error(f"Error in diagnose_error_logs: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    """Main diagnostic function"""
    logger.info("Starting VisiGate diagnostics")
    
    try:
        # Run all diagnostic functions
        diagnose_camera_routes()
        diagnose_templates()
        diagnose_onvif_camera()
        diagnose_flask_app()
        diagnose_error_logs()
        
        logger.info("Diagnostics completed")
        print(f"Diagnostics completed. See log file at {log_file}")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"Error in diagnostics: {str(e)}")

if __name__ == "__main__":
    main()
