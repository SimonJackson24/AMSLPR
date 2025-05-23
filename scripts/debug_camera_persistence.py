#!/usr/bin/env python3

import os
import sqlite3
import logging
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('camera_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('CameraDebug')

def check_database_path():
    """Check all possible database paths in the codebase."""
    # List of potential database paths
    potential_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'amslpr.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'amslpr.db'),
        'data/amslpr.db',
        'instance/amslpr.db',
        '/home/pi/AMSLPR/data/amslpr.db',
        '/home/pi/AMSLPR/instance/amslpr.db'
    ]
    
    logger.info("===== CHECKING POTENTIAL DATABASE PATHS =====")
    
    for path in potential_paths:
        exists = os.path.exists(path)
        logger.info(f"Path: {path}")
        logger.info(f"  Exists: {exists}")
        
        if exists:
            try:
                # Check if file is readable
                readable = os.access(path, os.R_OK)
                logger.info(f"  Readable: {readable}")
                
                # Check if file is writable
                writable = os.access(path, os.W_OK)
                logger.info(f"  Writable: {writable}")
                
                # Check file size
                size = os.path.getsize(path)
                logger.info(f"  Size: {size} bytes")
                
                # Check if it's a valid SQLite database
                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    
                    # Check for cameras table
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
                    has_cameras_table = cursor.fetchone() is not None
                    logger.info(f"  Has cameras table: {has_cameras_table}")
                    
                    if has_cameras_table:
                        # Get camera count
                        cursor.execute("SELECT COUNT(*) FROM cameras")
                        camera_count = cursor.fetchone()[0]
                        logger.info(f"  Camera count: {camera_count}")
                        
                        # Get camera details
                        if camera_count > 0:
                            cursor.execute("SELECT * FROM cameras")
                            columns = [description[0] for description in cursor.description]
                            cameras = cursor.fetchall()
                            
                            logger.info(f"  Camera table columns: {columns}")
                            
                            for i, camera in enumerate(cameras):
                                camera_dict = dict(zip(columns, camera))
                                logger.info(f"  Camera {i+1}: {json.dumps(camera_dict, default=str)}")
                    
                    # Check for other tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    logger.info(f"  Tables in database: {[table[0] for table in tables]}")
                    
                    conn.close()
                    logger.info(f"  Valid SQLite database: Yes")
                except Exception as e:
                    logger.info(f"  Valid SQLite database: No - {str(e)}")
            except Exception as e:
                logger.info(f"  Error checking file: {str(e)}")
    
    logger.info("===== DATABASE PATH CHECK COMPLETE =====")

def check_camera_routes():
    """Check camera routes in the application."""
    try:
        logger.info("===== CHECKING CAMERA ROUTES =====")
        
        # Import the camera routes module
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        try:
            from src.web.camera_routes import onvif_camera_manager, db_manager
            
            # Check if camera manager is initialized
            logger.info(f"Camera manager initialized: {onvif_camera_manager is not None}")
            if onvif_camera_manager:
                logger.info(f"Camera manager type: {type(onvif_camera_manager)}")
                logger.info(f"Camera count: {len(onvif_camera_manager.cameras) if hasattr(onvif_camera_manager, 'cameras') else 'No cameras attribute'}")
                
                if hasattr(onvif_camera_manager, 'cameras'):
                    logger.info(f"Camera IDs: {list(onvif_camera_manager.cameras.keys())}")
            
            # Check if database manager is initialized
            logger.info(f"Database manager initialized: {db_manager is not None}")
            if db_manager:
                logger.info(f"Database manager type: {type(db_manager)}")
                if hasattr(db_manager, 'db_path'):
                    logger.info(f"Database path: {db_manager.db_path}")
                    logger.info(f"Database exists: {os.path.exists(db_manager.db_path)}")
        except ImportError as e:
            logger.info(f"Error importing camera_routes: {str(e)}")
        
        # Check for MJPEG streaming route
        try:
            from src.web.app import app
            
            # Get all routes
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'path': str(rule)
                })
            
            logger.info(f"Total routes: {len(routes)}")
            
            # Look for camera-related routes
            camera_routes = [route for route in routes if 'camera' in route['path'].lower()]
            logger.info(f"Camera routes: {json.dumps(camera_routes, indent=2)}")
            
            # Look specifically for MJPEG routes
            mjpeg_routes = [route for route in routes if 'mjpeg' in route['path'].lower()]
            logger.info(f"MJPEG routes: {json.dumps(mjpeg_routes, indent=2)}")
        except ImportError as e:
            logger.info(f"Error importing app: {str(e)}")
        
        logger.info("===== CAMERA ROUTES CHECK COMPLETE =====")
    except Exception as e:
        logger.info(f"Error checking camera routes: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting camera persistence debugging")
    check_database_path()
    check_camera_routes()
    logger.info("Camera persistence debugging complete")
