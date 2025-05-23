# Camera persistence functions for the DatabaseManager class

def add_camera(self, camera_info):
    """
    Add a camera to the database.
    
    Args:
        camera_info (dict): Camera information including ip, port, username, password, etc.
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if camera already exists
        cursor.execute('SELECT id FROM cameras WHERE ip = ?', (camera_info['ip'],))
        if cursor.fetchone() is not None:
            # Update existing camera
            query = 'UPDATE cameras SET updated_at = CURRENT_TIMESTAMP'
            params = []
            
            # Update fields if provided
            fields = ['port', 'username', 'password', 'stream_uri', 'manufacturer', 'model', 'name', 'location']
            for field in fields:
                if field in camera_info and camera_info[field] is not None:
                    query += f', {field} = ?'
                    params.append(camera_info[field])
            
            query += ' WHERE ip = ?'
            params.append(camera_info['ip'])
            
            cursor.execute(query, params)
            logger.info(f"Updated camera with IP {camera_info['ip']}")
        else:
            # Insert new camera
            fields = ['ip', 'port', 'username', 'password', 'stream_uri', 'manufacturer', 'model', 'name', 'location']
            values = [camera_info.get(field) for field in fields]
            
            placeholders = ', '.join(['?' for _ in fields])
            fields_str = ', '.join(fields)
            
            cursor.execute(f'INSERT INTO cameras ({fields_str}) VALUES ({placeholders})', values)
            logger.info(f"Added camera with IP {camera_info['ip']}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error adding camera to database: {e}")
        return False

def get_all_cameras(self):
    """
    Get all cameras from the database.
    
    Returns:
        list: List of camera dictionaries
    """
    try:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Get all cameras
        cursor.execute('SELECT * FROM cameras')
        rows = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        # Convert rows to dictionaries
        cameras = [dict(row) for row in rows]
        logger.info(f"Retrieved {len(cameras)} cameras from database")
        
        return cameras
    except Exception as e:
        logger.error(f"Error getting cameras from database: {e}")
        return []

def delete_camera(self, camera_id):
    """
    Delete a camera from the database.
    
    Args:
        camera_id (str): Camera ID (IP address)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete camera
        cursor.execute('DELETE FROM cameras WHERE ip = ?', (camera_id,))
        
        # Check if any rows were affected
        if cursor.rowcount == 0:
            logger.warning(f"Camera with ID {camera_id} not found in database")
            conn.close()
            return False
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted camera with ID {camera_id} from database")
        return True
    except Exception as e:
        logger.error(f"Error deleting camera from database: {e}")
        return False
