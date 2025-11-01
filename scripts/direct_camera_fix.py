#!/usr/bin/env python3
"""
Direct fix for camera persistence issues - run this directly on the Raspberry Pi.
This script will diagnose and fix camera persistence issues.
"""

import os
import sys
import sqlite3
import logging
import json
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('direct_fix')

# Define paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, 'data', 'visigate.db')
LOG_PATH = os.path.join(ROOT_DIR, 'camera_fix.log')

# Add file handler for logging
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def check_database():
    """Check if the database exists and has the correct structure."""
    logger.info(f"Checking database at {DB_PATH}")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file does not exist: {DB_PATH}")
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        logger.info(f"Created directory: {os.path.dirname(DB_PATH)}")
        
        # Create a new database
        create_database()
        return False
    
    # Check if cameras table exists
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
        if not cursor.fetchone():
            logger.error("Cameras table does not exist")
            create_cameras_table(conn)
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(cameras)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Cameras table columns: {columns}")
        
        # Check for required columns
        required_columns = ['ip', 'port', 'username', 'password', 'stream_uri', 'name', 'location']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"Missing columns in cameras table: {missing_columns}")
            # Add missing columns
            for col in missing_columns:
                logger.info(f"Adding missing column: {col}")
                cursor.execute(f"ALTER TABLE cameras ADD COLUMN {col} TEXT")
            conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        logger.error(traceback.format_exc())
        return False

def create_database():
    """Create a new database with the required tables."""
    try:
        logger.info(f"Creating new database at {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        create_cameras_table(conn)
        conn.close()
        logger.info("Database created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        logger.error(traceback.format_exc())
        return False

def create_cameras_table(conn):
    """Create the cameras table in the database."""
    try:
        logger.info("Creating cameras table")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT UNIQUE NOT NULL,
                port INTEGER DEFAULT 80,
                username TEXT,
                password TEXT,
                stream_uri TEXT,
                manufacturer TEXT,
                model TEXT,
                name TEXT,
                location TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logger.info("Cameras table created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating cameras table: {e}")
        logger.error(traceback.format_exc())
        return False

def check_camera_manager():
    """Check if the camera manager is properly loading cameras from the database."""
    try:
        # Import the camera manager
        sys.path.append(ROOT_DIR)
        from src.recognition.onvif_camera import ONVIFCameraManager
        from src.database.db_manager import DatabaseManager
        
        # Initialize database manager
        config = {'database': {'path': DB_PATH}}
        db_manager = DatabaseManager(config)
        
        # Get cameras from database
        cameras = db_manager.get_all_cameras()
        logger.info(f"Found {len(cameras)} cameras in database")
        
        # Log camera details
        for camera in cameras:
            logger.info(f"Camera in DB: {camera['ip']} - {camera.get('name', 'Unknown')}")
        
        # Initialize camera manager
        camera_manager = ONVIFCameraManager()
        
        # Check if camera manager has cameras attribute
        if not hasattr(camera_manager, 'cameras'):
            logger.error("Camera manager does not have cameras attribute")
            return False
        
        # Log camera manager cameras
        logger.info(f"Camera manager has {len(camera_manager.cameras)} cameras")
        for ip, camera in camera_manager.cameras.items():
            logger.info(f"Camera in manager: {ip}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking camera manager: {e}")
        logger.error(traceback.format_exc())
        return False

def add_test_camera():
    """Add a test camera to the database to verify persistence."""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Add a test camera
        test_camera = {
            'ip': '192.168.1.100',
            'port': 80,
            'username': 'admin',
            'password': 'admin',
            'stream_uri': 'rtsp://192.168.1.100:554/stream1',
            'name': 'Test Camera',
            'location': 'Test Location',
            'manufacturer': 'Test',
            'model': 'Test Model'
        }
        
        # Check if camera already exists
        cursor.execute('SELECT id FROM cameras WHERE ip = ?', (test_camera['ip'],))
        if cursor.fetchone():
            logger.info(f"Test camera already exists in database")
        else:
            # Insert camera
            cursor.execute('''
                INSERT INTO cameras (ip, port, username, password, stream_uri, name, location, manufacturer, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_camera['ip'],
                test_camera['port'],
                test_camera['username'],
                test_camera['password'],
                test_camera['stream_uri'],
                test_camera['name'],
                test_camera['location'],
                test_camera['manufacturer'],
                test_camera['model']
            ))
            conn.commit()
            logger.info(f"Added test camera to database")
        
        # Close connection
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding test camera: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_camera_routes():
    """Fix the camera_routes.py file to ensure cameras are loaded from the database."""
    try:
        camera_routes_path = os.path.join(ROOT_DIR, 'src', 'web', 'camera_routes.py')
        logger.info(f"Fixing camera routes file: {camera_routes_path}")
        
        # Check if file exists
        if not os.path.exists(camera_routes_path):
            logger.error(f"Camera routes file not found: {camera_routes_path}")
            return False
        
        # Create backup
        backup_path = camera_routes_path + '.bak'
        os.system(f"cp {camera_routes_path} {backup_path}")
        logger.info(f"Created backup at {backup_path}")
        
        # Read file
        with open(camera_routes_path, 'r') as f:
            content = f.read()
        
        # Find the reload_cameras_from_database function
        if 'def reload_cameras_from_database():' not in content:
            logger.error("reload_cameras_from_database function not found")
            return False
        
        # Add explicit return True at the end of the function
        if 'def reload_cameras_from_database():' in content and 'return True' not in content:
            # Find the end of the function
            func_start = content.find('def reload_cameras_from_database():')
            next_func = content.find('def ', func_start + 1)
            if next_func > 0:
                # Insert return True before the next function
                insert_pos = content.rfind('\n', func_start, next_func) + 1
                content = content[:insert_pos] + '        return True\n' + content[insert_pos:]
                logger.info("Added explicit return True to reload_cameras_from_database function")
                
                # Write the modified content back to the file
                with open(camera_routes_path, 'w') as f:
                    f.write(content)
        
        # Find the init_camera_manager function
        if 'def init_camera_manager(' not in content:
            logger.error("init_camera_manager function not found")
            return False
        
        # Check if reload_cameras_from_database is called in init_camera_manager
        if 'def init_camera_manager(' in content and 'reload_cameras_from_database()' not in content:
            # Find the position to insert the call
            func_start = content.find('def init_camera_manager(')
            camera_init = content.find('onvif_camera_manager = ONVIFCameraManager()', func_start)
            if camera_init > 0:
                # Find the end of this line
                line_end = content.find('\n', camera_init) + 1
                # Insert the call to reload_cameras_from_database
                insert_code = '''
            # Load cameras from database
            logger.info("Loading cameras from database")
            try:
                reload_cameras_from_database()
                logger.info("Successfully loaded cameras from database")
            except Exception as e:
                logger.error(f"Failed to load cameras from database: {str(e)}")
'''
                content = content[:line_end] + insert_code + content[line_end:]
                logger.info("Added call to reload_cameras_from_database in init_camera_manager")
                
                # Write the modified content back to the file
                with open(camera_routes_path, 'w') as f:
                    f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"Error fixing camera routes: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_onvif_camera():
    """Fix the onvif_camera.py file to ensure cameras are saved to the database."""
    try:
        onvif_camera_path = os.path.join(ROOT_DIR, 'src', 'recognition', 'onvif_camera.py')
        logger.info(f"Fixing ONVIF camera file: {onvif_camera_path}")
        
        # Check if file exists
        if not os.path.exists(onvif_camera_path):
            logger.error(f"ONVIF camera file not found: {onvif_camera_path}")
            return False
        
        # Create backup
        backup_path = onvif_camera_path + '.bak'
        os.system(f"cp {onvif_camera_path} {backup_path}")
        logger.info(f"Created backup at {backup_path}")
        
        # Read file
        with open(onvif_camera_path, 'r') as f:
            content = f.read()
        
        # Find the add_camera method
        if 'def add_camera(self, camera_info):' not in content:
            logger.error("add_camera method not found")
            return False
        
        # Find all occurrences of self.cameras[ip] = {
        camera_add_pos = []
        pos = 0
        while True:
            pos = content.find('self.cameras[ip] = {', pos)
            if pos == -1:
                break
            camera_add_pos.append(pos)
            pos += 1
        
        logger.info(f"Found {len(camera_add_pos)} occurrences of camera addition")
        
        # Process each occurrence in reverse order to avoid messing up positions
        for pos in sorted(camera_add_pos, reverse=True):
            # Find the end of this block
            block_end = content.find('}', pos)
            if block_end == -1:
                continue
            
            # Find the end of this line
            line_end = content.find('\n', block_end) + 1
            
            # Check if there's already code to save to database
            save_code_exists = False
            next_pos = content.find('self.cameras[ip] = {', line_end)
            if next_pos == -1:
                next_pos = len(content)
            
            check_section = content[line_end:min(line_end + 500, next_pos)]
            if 'db_manager' in check_section and 'add_camera' in check_section:
                save_code_exists = True
            
            if not save_code_exists:
                # Insert code to save camera to database
                save_code = '''
                # Save camera to database
                try:
                    # Try to import database manager directly
                    try:
                        from src.database.db_manager import DatabaseManager
                        config = {'database': {'path': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'visigate.db')}}
                        direct_db = DatabaseManager(config)
                        
                        # Prepare camera info
                        db_camera_info = {
                            'ip': ip,
                            'port': port if 'port' in locals() else 80,
                            'username': username if 'username' in locals() else '',
                            'password': password if 'password' in locals() else '',
                            'stream_uri': camera_info.get('stream_uri', ''),
                            'name': camera_info.get('name', f'Camera {ip}'),
                            'location': camera_info.get('location', 'Unknown'),
                            'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                            'model': camera_info.get('model', 'ONVIF Camera')
                        }
                        
                        # Save to database
                        direct_db.add_camera(db_camera_info)
                        logger.info(f"Camera {ip} saved to database directly")
                    except Exception as e:
                        logger.error(f"Error saving camera directly: {str(e)}")
                        
                        # Try to get db_manager from camera_routes as fallback
                        try:
                            from src.web.camera_routes import db_manager
                            if db_manager and hasattr(db_manager, 'add_camera'):
                                # Prepare camera info
                                db_camera_info = {
                                    'ip': ip,
                                    'port': port if 'port' in locals() else 80,
                                    'username': username if 'username' in locals() else '',
                                    'password': password if 'password' in locals() else '',
                                    'stream_uri': camera_info.get('stream_uri', ''),
                                    'name': camera_info.get('name', f'Camera {ip}'),
                                    'location': camera_info.get('location', 'Unknown'),
                                    'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                    'model': camera_info.get('model', 'ONVIF Camera')
                                }
                                
                                # Save to database
                                db_manager.add_camera(db_camera_info)
                                logger.info(f"Camera {ip} saved to database via camera_routes")
                        except Exception as e:
                            logger.error(f"Error saving camera via camera_routes: {str(e)}")
                except Exception as e:
                    logger.error(f"Error saving camera {ip} to database: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
'''
                content = content[:line_end] + save_code + content[line_end:]
                logger.info(f"Added code to save camera at position {pos}")
        
        # Write the modified content back to the file
        with open(onvif_camera_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"Error fixing ONVIF camera: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to fix camera persistence issues."""
    logger.info("Starting direct camera persistence fix")
    
    # Step 1: Check database
    logger.info("Step 1: Checking database...")
    if check_database():
        logger.info("Database check passed")
    else:
        logger.warning("Database check failed, but continuing with fixes")
    
    # Step 2: Add test camera
    logger.info("Step 2: Adding test camera...")
    if add_test_camera():
        logger.info("Test camera added successfully")
    else:
        logger.warning("Failed to add test camera, but continuing with fixes")
    
    # Step 3: Fix camera_routes.py
    logger.info("Step 3: Fixing camera_routes.py...")
    if fix_camera_routes():
        logger.info("camera_routes.py fixed successfully")
    else:
        logger.warning("Failed to fix camera_routes.py, but continuing with fixes")
    
    # Step 4: Fix onvif_camera.py
    logger.info("Step 4: Fixing onvif_camera.py...")
    if fix_onvif_camera():
        logger.info("onvif_camera.py fixed successfully")
    else:
        logger.warning("Failed to fix onvif_camera.py, but continuing with fixes")
    
    # Step 5: Check camera manager
    logger.info("Step 5: Checking camera manager...")
    if check_camera_manager():
        logger.info("Camera manager check passed")
    else:
        logger.warning("Camera manager check failed")
    
    logger.info("Camera persistence fix complete")
    logger.info("Please restart the VisiGate service for the changes to take effect:")
    logger.info("sudo systemctl restart visigate")
    logger.info(f"Check the log file at {LOG_PATH} for details")

if __name__ == "__main__":
    main()
