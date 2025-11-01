#!/usr/bin/env python3
"""
Fix camera persistence by ensuring there is only one database path used throughout the code.
This script directly modifies the necessary files to ensure cameras are saved and loaded correctly.
"""

import os
import sys
import sqlite3
import logging
import re
import traceback
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_fix')

# Define paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(ROOT_DIR, 'data')
DB_PATH = os.path.join(DB_DIR, 'visigate.db')
LOG_PATH = os.path.join(ROOT_DIR, 'db_fix.log')

# Add file handler for logging
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Define the standard database path to use everywhere
STANDARD_DB_PATH = "os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'visigate.db')"

def check_and_create_database():
    """Check if the database exists and create it if it doesn't."""
    logger.info(f"Checking database at {DB_PATH}")
    
    # Create the data directory if it doesn't exist
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
        logger.info(f"Created data directory at {DB_DIR}")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        logger.info(f"Database file does not exist, creating it at {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create cameras table
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
        
        # Create index on IP
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cameras_ip ON cameras(ip)")
        
        conn.commit()
        conn.close()
        logger.info("Database created successfully")
    else:
        logger.info(f"Database file exists at {DB_PATH}")
        
        # Check if cameras table exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
        if not cursor.fetchone():
            logger.info("Cameras table does not exist, creating it")
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
            
            # Create index on IP
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cameras_ip ON cameras(ip)")
            
            conn.commit()
            logger.info("Cameras table created successfully")
        else:
            logger.info("Cameras table exists")
            
            # Check if all required columns exist
            cursor.execute("PRAGMA table_info(cameras)")
            columns = [row[1] for row in cursor.fetchall()]
            logger.info(f"Existing columns: {columns}")
            
            # Required columns
            required_columns = [
                ('ip', 'TEXT UNIQUE NOT NULL'),
                ('port', 'INTEGER DEFAULT 80'),
                ('username', 'TEXT'),
                ('password', 'TEXT'),
                ('stream_uri', 'TEXT'),
                ('manufacturer', 'TEXT'),
                ('model', 'TEXT'),
                ('name', 'TEXT'),
                ('location', 'TEXT')
            ]
            
            # Add missing columns
            for col_name, col_type in required_columns:
                if col_name not in columns:
                    logger.info(f"Adding missing column {col_name}")
                    cursor.execute(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_type}")
            
            conn.commit()
        
        conn.close()
    
    return True

def fix_db_manager():
    """Fix the database manager to use a single database path."""
    db_manager_path = os.path.join(ROOT_DIR, 'src', 'database', 'db_manager.py')
    logger.info(f"Fixing database manager at {db_manager_path}")
    
    # Check if file exists
    if not os.path.exists(db_manager_path):
        logger.error(f"Database manager file not found at {db_manager_path}")
        return False
    
    # Create backup
    backup_path = db_manager_path + '.bak'
    shutil.copy2(db_manager_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    
    # Read file
    with open(db_manager_path, 'r') as f:
        content = f.read()
    
    # Find the DatabaseManager class
    class_pos = content.find('class DatabaseManager')
    if class_pos == -1:
        logger.error("DatabaseManager class not found")
        return False
    
    # Find the __init__ method
    init_pos = content.find('def __init__', class_pos)
    if init_pos == -1:
        logger.error("__init__ method not found")
        return False
    
    # Find where the database path is set
    db_path_pos = content.find('self.db_path =', init_pos)
    if db_path_pos == -1:
        logger.error("Database path assignment not found")
        return False
    
    # Find the end of the line
    line_end = content.find('\n', db_path_pos)
    if line_end == -1:
        logger.error("Could not find end of line")
        return False
    
    # Extract the current line
    current_line = content[db_path_pos:line_end]
    logger.info(f"Current database path assignment: {current_line}")
    
    # Create the new line with the standard database path
    new_line = f"        self.db_path = {STANDARD_DB_PATH}"
    logger.info(f"New database path assignment: {new_line}")
    
    # Replace the line
    content = content[:db_path_pos] + new_line + content[line_end:]
    
    # Write the modified content back to the file
    with open(db_manager_path, 'w') as f:
        f.write(content)
    
    logger.info("Database manager fixed successfully")
    return True

def fix_camera_routes():
    """Fix the camera routes to ensure cameras are loaded from the database."""
    camera_routes_path = os.path.join(ROOT_DIR, 'src', 'web', 'camera_routes.py')
    logger.info(f"Fixing camera routes at {camera_routes_path}")
    
    # Check if file exists
    if not os.path.exists(camera_routes_path):
        logger.error(f"Camera routes file not found at {camera_routes_path}")
        return False
    
    # Create backup
    backup_path = camera_routes_path + '.bak'
    shutil.copy2(camera_routes_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    
    # Read file
    with open(camera_routes_path, 'r') as f:
        content = f.read()
    
    # Find where the database manager is initialized
    db_init_pos = content.find('db_manager = DatabaseManager')
    if db_init_pos != -1:
        # Find the end of the line
        line_end = content.find('\n', db_init_pos)
        if line_end != -1:
            # Extract the current line
            current_line = content[db_init_pos:line_end]
            logger.info(f"Current database manager initialization: {current_line}")
            
            # Create the new line with the standard database path
            new_line = f"db_manager = DatabaseManager({{'database': {{'path': {STANDARD_DB_PATH}}}})"
            logger.info(f"New database manager initialization: {new_line}")
            
            # Replace the line
            content = content[:db_init_pos] + new_line + content[line_end:]
    
    # Find the reload_cameras_from_database function
    reload_pos = content.find('def reload_cameras_from_database()')
    if reload_pos == -1:
        logger.error("reload_cameras_from_database function not found")
        return False
    
    # Find the end of the function
    next_def_pos = content.find('def ', reload_pos + 1)
    if next_def_pos == -1:
        logger.error("Could not find end of reload_cameras_from_database function")
        return False
    
    # Extract the function
    function_content = content[reload_pos:next_def_pos]
    logger.info(f"Found reload_cameras_from_database function")
    
    # Check if the function has a return True statement
    if 'return True' not in function_content:
        # Find the last line of the function
        last_line_pos = function_content.rfind('\n')
        if last_line_pos != -1:
            # Insert return True
            function_content = function_content[:last_line_pos] + '\n        return True' + function_content[last_line_pos:]
            logger.info("Added return True to reload_cameras_from_database function")
            
            # Update the content
            content = content[:reload_pos] + function_content + content[next_def_pos:]
    
    # Find the init_camera_manager function
    init_pos = content.find('def init_camera_manager(')
    if init_pos == -1:
        logger.error("init_camera_manager function not found")
        return False
    
    # Find where the camera manager is initialized
    camera_init_pos = content.find('onvif_camera_manager = ONVIFCameraManager()', init_pos)
    if camera_init_pos == -1:
        logger.error("Camera manager initialization not found")
        return False
    
    # Find the end of the line
    line_end = content.find('\n', camera_init_pos)
    if line_end == -1:
        logger.error("Could not find end of camera manager initialization line")
        return False
    
    # Check if there's code to load cameras from database after camera initialization
    next_section = content[line_end:line_end + 500]  # Look at the next 500 characters
    if 'reload_cameras_from_database()' not in next_section:
        # Add code to load cameras from database
        load_code = '''
            # Load cameras from database
            logger.info("Loading cameras from database")
            try:
                reload_cameras_from_database()
                logger.info("Successfully loaded cameras from database")
            except Exception as e:
                logger.error(f"Failed to load cameras from database: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
'''
        content = content[:line_end + 1] + load_code + content[line_end + 1:]
        logger.info("Added code to load cameras from database after camera manager initialization")
    
    # Write the modified content back to the file
    with open(camera_routes_path, 'w') as f:
        f.write(content)
    
    logger.info("Camera routes fixed successfully")
    return True

def fix_onvif_camera():
    """Fix the ONVIF camera manager to save cameras to the database."""
    onvif_camera_path = os.path.join(ROOT_DIR, 'src', 'recognition', 'onvif_camera.py')
    logger.info(f"Fixing ONVIF camera manager at {onvif_camera_path}")
    
    # Check if file exists
    if not os.path.exists(onvif_camera_path):
        logger.error(f"ONVIF camera manager file not found at {onvif_camera_path}")
        return False
    
    # Create backup
    backup_path = onvif_camera_path + '.bak'
    shutil.copy2(onvif_camera_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    
    # Read file
    with open(onvif_camera_path, 'r') as f:
        content = f.read()
    
    # Find the add_camera method
    add_camera_pos = content.find('def add_camera(self, camera_info):')
    if add_camera_pos == -1:
        logger.error("add_camera method not found")
        return False
    
    # Find all instances where cameras are added to self.cameras
    camera_add_positions = []
    pos = 0
    while True:
        pos = content.find('self.cameras[ip] = {', pos)
        if pos == -1:
            break
        camera_add_positions.append(pos)
        pos += 1
    
    logger.info(f"Found {len(camera_add_positions)} instances of camera addition")
    
    # Process each instance in reverse order to avoid messing up positions
    for pos in sorted(camera_add_positions, reverse=True):
        # Find the end of this statement
        closing_brace_pos = content.find('}', pos)
        if closing_brace_pos == -1:
            continue
        
        # Find the end of the line
        line_end = content.find('\n', closing_brace_pos)
        if line_end == -1:
            continue
        
        # Check if there's already code to save to database
        next_section = content[line_end:line_end + 500]  # Look at the next 500 characters
        if 'db_manager' in next_section and 'add_camera' in next_section:
            logger.info(f"Code to save camera to database already exists at position {pos}")
            continue
        
        # Add code to save camera to database
        save_code = '''
                # Save camera to database
                try:
                    # Import database manager
                    from src.database.db_manager import DatabaseManager
                    
                    # Create database manager with standard path
                    db_config = {'database': {'path': ''' + STANDARD_DB_PATH + '''}}}
                    db_manager = DatabaseManager(db_config)
                    
                    # Prepare camera info for database
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
                    logger.info(f"Camera {ip} saved to database")
                except Exception as e:
                    logger.error(f"Error saving camera to database: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
'''
        content = content[:line_end + 1] + save_code + content[line_end + 1:]
        logger.info(f"Added code to save camera to database at position {pos}")
    
    # Write the modified content back to the file
    with open(onvif_camera_path, 'w') as f:
        f.write(content)
    
    logger.info("ONVIF camera manager fixed successfully")
    return True

def add_test_camera():
    """Add a test camera to the database to verify persistence."""
    logger.info(f"Adding test camera to database at {DB_PATH}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if test camera already exists
        cursor.execute("SELECT id FROM cameras WHERE ip = ?", ('192.168.1.200',))
        if cursor.fetchone():
            logger.info("Test camera already exists in database")
        else:
            # Add test camera
            cursor.execute('''
                INSERT INTO cameras (ip, port, username, password, stream_uri, name, location, manufacturer, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                '192.168.1.200',  # IP
                80,               # Port
                'admin',          # Username
                'admin',          # Password
                'rtsp://192.168.1.200:554/stream1',  # Stream URI
                'Test Camera',    # Name
                'Test Location',  # Location
                'Test',           # Manufacturer
                'Test Model'      # Model
            ))
            conn.commit()
            logger.info("Test camera added to database")
        
        # List all cameras in the database
        cursor.execute("SELECT id, ip, name FROM cameras")
        cameras = cursor.fetchall()
        logger.info(f"Cameras in database: {cameras}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding test camera: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to fix database and camera persistence issues."""
    logger.info("Starting database and camera persistence fix")
    
    # Step 1: Check and create database
    logger.info("Step 1: Checking and creating database...")
    if check_and_create_database():
        logger.info("Database check passed")
    else:
        logger.error("Database check failed")
        return False
    
    # Step 2: Fix database manager
    logger.info("Step 2: Fixing database manager...")
    if fix_db_manager():
        logger.info("Database manager fixed successfully")
    else:
        logger.error("Failed to fix database manager")
        return False
    
    # Step 3: Fix camera routes
    logger.info("Step 3: Fixing camera routes...")
    if fix_camera_routes():
        logger.info("Camera routes fixed successfully")
    else:
        logger.error("Failed to fix camera routes")
        return False
    
    # Step 4: Fix ONVIF camera manager
    logger.info("Step 4: Fixing ONVIF camera manager...")
    if fix_onvif_camera():
        logger.info("ONVIF camera manager fixed successfully")
    else:
        logger.error("Failed to fix ONVIF camera manager")
        return False
    
    # Step 5: Add test camera
    logger.info("Step 5: Adding test camera...")
    if add_test_camera():
        logger.info("Test camera added successfully")
    else:
        logger.error("Failed to add test camera")
        return False
    
    logger.info("Database and camera persistence fix complete")
    logger.info("Please restart the VisiGate service for the changes to take effect:")
    logger.info("sudo systemctl restart visigate")
    logger.info(f"Check the log file at {LOG_PATH} for details")
    return True

if __name__ == "__main__":
    main()
