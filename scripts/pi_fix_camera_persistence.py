#!/usr/bin/env python3
"""
Direct fix for camera persistence issues on Raspberry Pi.
Run this script on the Pi to fix the camera persistence issue.
"""

import os
import sys
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pi_fix')

# Define database path
DB_PATH = '/home/pi/AMSLPR/data/amslpr.db'

def ensure_cameras_table():
    """Ensure the cameras table exists with the correct structure."""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if cameras table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
        if not cursor.fetchone():
            logger.info("Creating cameras table...")
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
        else:
            logger.info("Cameras table already exists")
            
            # Check if we need to add any missing columns
            cursor.execute("PRAGMA table_info(cameras)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add missing columns if needed
            required_columns = [
                ('stream_uri', 'TEXT'),
                ('manufacturer', 'TEXT'),
                ('model', 'TEXT'),
                ('name', 'TEXT'),
                ('location', 'TEXT')
            ]
            
            for col_name, col_type in required_columns:
                if col_name not in columns:
                    logger.info(f"Adding missing column {col_name} to cameras table")
                    cursor.execute(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_type}")
            
            conn.commit()
            logger.info("Cameras table structure updated successfully")
        
        # Create index on IP
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cameras_ip ON cameras(ip)")
        conn.commit()
        
        # Close connection
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error ensuring cameras table: {e}")
        return False

def add_camera_loading_code():
    """Add code to camera_routes.py to ensure cameras are loaded from the database."""
    try:
        # Define paths
        camera_routes_path = '/home/pi/AMSLPR/src/web/camera_routes.py'
        
        # Check if the file exists
        if not os.path.exists(camera_routes_path):
            logger.error(f"File not found: {camera_routes_path}")
            return False
        
        # Create a backup
        backup_path = camera_routes_path + '.bak'
        os.system(f"cp {camera_routes_path} {backup_path}")
        logger.info(f"Created backup at {backup_path}")
        
        # Read the file
        with open(camera_routes_path, 'r') as f:
            content = f.readlines()
        
        # Find the init_camera_manager function
        init_camera_found = False
        reload_cameras_call_found = False
        for i, line in enumerate(content):
            if 'def init_camera_manager(' in line:
                init_camera_found = True
            if init_camera_found and 'onvif_camera_manager = ONVIFCameraManager()' in line:
                # Check if the next few lines already have the reload_cameras_from_database call
                for j in range(i+1, min(i+10, len(content))):
                    if 'reload_cameras_from_database()' in content[j]:
                        reload_cameras_call_found = True
                        break
                
                if not reload_cameras_call_found:
                    # Insert the camera loading code after the camera manager initialization
                    logger.info("Adding camera loading code...")
                    content.insert(i+1, '            # Load cameras from database\n')
                    content.insert(i+2, '            logger.info("Loading cameras from database")\n')
                    content.insert(i+3, '            try:\n')
                    content.insert(i+4, '                reload_cameras_from_database()\n')
                    content.insert(i+5, '                logger.info("Successfully loaded cameras from database")\n')
                    content.insert(i+6, '            except Exception as e:\n')
                    content.insert(i+7, '                logger.error(f"Failed to load cameras from database: {str(e)}")\n')
                    break
        
        if not init_camera_found:
            logger.error("Could not find init_camera_manager function")
            return False
        
        if reload_cameras_call_found:
            logger.info("Camera loading code already exists")
        else:
            # Write the modified content back to the file
            with open(camera_routes_path, 'w') as f:
                f.writelines(content)
            logger.info("Camera loading code added successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error adding camera loading code: {e}")
        return False

def add_camera_saving_code():
    """Add code to onvif_camera.py to ensure cameras are saved to the database."""
    try:
        # Define paths
        onvif_camera_path = '/home/pi/AMSLPR/src/recognition/onvif_camera.py'
        
        # Check if the file exists
        if not os.path.exists(onvif_camera_path):
            logger.error(f"File not found: {onvif_camera_path}")
            return False
        
        # Create a backup
        backup_path = onvif_camera_path + '.bak'
        os.system(f"cp {onvif_camera_path} {backup_path}")
        logger.info(f"Created backup at {backup_path}")
        
        # Read the file
        with open(onvif_camera_path, 'r') as f:
            content = f.readlines()
        
        # Find all instances where cameras are added to self.cameras
        camera_add_lines = []
        for i, line in enumerate(content):
            if 'self.cameras[ip] = {' in line:
                camera_add_lines.append(i)
        
        if not camera_add_lines:
            logger.error("Could not find where cameras are added to self.cameras")
            return False
        
        # Process each instance in reverse order to avoid messing up line numbers
        for line_num in sorted(camera_add_lines, reverse=True):
            # Find the end of this block (closing brace)
            end_line = None
            for i in range(line_num, len(content)):
                if '}' in content[i] and 'stream' in content[i]:
                    end_line = i
                    break
            
            if end_line is None:
                continue
            
            # Check if there's already code to save to database after this line
            save_code_exists = False
            for i in range(end_line+1, min(end_line+10, len(content))):
                if 'db_manager' in content[i] and 'add_camera' in content[i]:
                    save_code_exists = True
                    break
            
            if not save_code_exists:
                # Insert the camera saving code after the camera is added to self.cameras
                logger.info(f"Adding camera saving code at line {end_line+1}...")
                save_code = [
                    '                # Save camera to database\n',
                    '                try:\n',
                    '                    # Try to get db_manager from camera_routes\n',
                    '                    from src.web.camera_routes import db_manager\n',
                    '                    if db_manager and hasattr(db_manager, \'add_camera\'):\n',
                    '                        logger.info(f"Saving camera {ip} to database")\n',
                    '                        db_camera_info = {\n',
                    '                            \'ip\': ip,\n',
                    '                            \'port\': port,\n',
                    '                            \'username\': username,\n',
                    '                            \'password\': password,\n',
                    '                            \'stream_uri\': camera_info.get(\'stream_uri\', \'\'),\n',
                    '                            \'name\': camera_info.get(\'name\', f\'Camera {ip}\'),\n',
                    '                            \'location\': camera_info.get(\'location\', \'Unknown\'),\n',
                    '                            \'manufacturer\': camera_info.get(\'manufacturer\', \'Unknown\'),\n',
                    '                            \'model\': camera_info.get(\'model\', \'ONVIF Camera\')\n',
                    '                        }\n',
                    '                        db_manager.add_camera(db_camera_info)\n',
                    '                        logger.info(f"Camera {ip} saved to database")\n',
                    '                    else:\n',
                    '                        logger.warning(f"Database manager not available, camera {ip} not saved to database")\n',
                    '                except Exception as e:\n',
                    '                    logger.error(f"Error saving camera {ip} to database: {str(e)}")\n',
                    '                    import traceback\n',
                    '                    logger.error(f"Traceback: {traceback.format_exc()}")\n'
                ]
                
                for i, line in enumerate(save_code):
                    content.insert(end_line+1+i, line)
        
        # Write the modified content back to the file
        with open(onvif_camera_path, 'w') as f:
            f.writelines(content)
        
        logger.info("Camera saving code added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding camera saving code: {e}")
        return False

def main():
    logger.info("Starting direct camera persistence fix for Raspberry Pi")
    
    # Step 1: Ensure the cameras table exists with the correct structure
    logger.info("Step 1: Ensuring cameras table exists...")
    if ensure_cameras_table():
        logger.info("Step 1 completed successfully")
    else:
        logger.error("Step 1 failed")
    
    # Step 2: Add code to load cameras from database
    logger.info("Step 2: Adding camera loading code...")
    if add_camera_loading_code():
        logger.info("Step 2 completed successfully")
    else:
        logger.error("Step 2 failed")
    
    # Step 3: Add code to save cameras to database
    logger.info("Step 3: Adding camera saving code...")
    if add_camera_saving_code():
        logger.info("Step 3 completed successfully")
    else:
        logger.error("Step 3 failed")
    
    logger.info("Camera persistence fix complete")
    logger.info("Please restart the AMSLPR service for the changes to take effect:")
    logger.info("sudo systemctl restart amslpr")

if __name__ == "__main__":
    main()
