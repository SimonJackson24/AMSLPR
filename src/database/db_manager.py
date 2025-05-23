# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import sqlite3
import os
import logging
import time
import shutil
from datetime import datetime, timedelta
import math

logger = logging.getLogger('AMSLPR.database')

class DatabaseManager:
    """
    Database manager for the AMSLPR system.
    Handles database operations for vehicle management and access logs.
    """
    
    def __init__(self, config=None):
        """Initialize the database manager."""
        self.config = config or {}
        
        # Always use the standard database path in the data directory
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'amslpr.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        logger.info(f"DatabaseManager initialized with database path: {self.db_path}")
        self._init_database()
        
        logger.info("Database manager initialized")
    
    def _init_database(self):
        """
        Initialize the database schema.
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate_number TEXT UNIQUE NOT NULL,
                    description TEXT,
                    authorized BOOLEAN NOT NULL DEFAULT 1,
                    valid_from DATETIME,
                    valid_until DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate_number TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    direction TEXT CHECK(direction IN ('entry', 'exit')),
                    authorized BOOLEAN,
                    notes TEXT
                )
            ''')
            
            # Create parking-related tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parking_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate_number TEXT NOT NULL,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    calculated_fee REAL,
                    paid_amount REAL,
                    payment_status TEXT CHECK(payment_status IN ('pending', 'paid', 'cancelled', 'waived', 'error')),
                    payment_method TEXT,
                    transaction_id TEXT,
                    receipt_number TEXT,
                    special_rate_applied TEXT,
                    payment_location TEXT,
                    payment_required TEXT,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create cameras table to persist camera settings
            # Create cameras table with all required fields
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT UNIQUE NOT NULL,
                    name TEXT,
                    username TEXT,
                    password TEXT,
                    port INTEGER DEFAULT 80,
                    stream_uri TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    location TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parking_session_id INTEGER,
                    amount REAL NOT NULL,
                    tax_amount REAL,
                    currency TEXT,
                    transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    transaction_id TEXT,
                    terminal_id TEXT,
                    payment_method TEXT,
                    status TEXT CHECK(status IN ('initiated', 'processing', 'completed', 'failed', 'cancelled')),
                    response_code TEXT,
                    response_message TEXT,
                    receipt_number TEXT,
                    FOREIGN KEY (parking_session_id) REFERENCES parking_sessions(id)
                )
            ''')
            
            # Create events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create API keys table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    last_used DATETIME,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    permissions TEXT
                )
            ''')
            
            # Add index for cameras table
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cameras_ip ON cameras(ip)')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_plate_number ON vehicles(plate_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_logs_plate_number ON access_logs(plate_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parking_sessions_plate_number ON parking_sessions(plate_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parking_sessions_entry_time ON parking_sessions(entry_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parking_sessions_exit_time ON parking_sessions(exit_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_transactions_parking_session_id ON payment_transactions(parking_session_id)')
            
            # Commit changes
            conn.commit()
            conn.close()
            
            logger.info("Database schema initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise
    
    def add_vehicle(self, plate_number, description=None, authorized=True, valid_from=None, valid_until=None):
        """
        Add a vehicle to the database.
        
        Args:
            plate_number (str): License plate number
            description (str, optional): Vehicle description
            authorized (bool, optional): Whether the vehicle is authorized
            valid_from (datetime, optional): Start of validity period
            valid_until (datetime, optional): End of validity period
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if vehicle already exists
            cursor.execute('SELECT id FROM vehicles WHERE plate_number = ?', (plate_number,))
            if cursor.fetchone() is not None:
                logger.warning(f"Vehicle with plate number {plate_number} already exists")
                conn.close()
                return False
            
            # Add vehicle
            cursor.execute(
                'INSERT INTO vehicles (plate_number, description, authorized, valid_from, valid_until) VALUES (?, ?, ?, ?, ?)',
                (plate_number, description, authorized, valid_from, valid_until)
            )
            
            # Commit changes
            conn.commit()
            
            # Close connection
            conn.close()
            
            logger.info(f"Added vehicle with plate number {plate_number}")
            return True
        except Exception as e:
            logger.error(f"Error adding vehicle: {e}")
            return False
    
    def update_vehicle(self, plate_number, description=None, authorized=None, valid_from=None, valid_until=None):
        """
        Update a vehicle in the database.
        
        Args:
            plate_number (str): License plate number
            description (str, optional): Vehicle description
            authorized (bool, optional): Whether the vehicle is authorized
            valid_from (datetime, optional): Start of validity period
            valid_until (datetime, optional): End of validity period
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if vehicle exists
            cursor.execute('SELECT id FROM vehicles WHERE plate_number = ?', (plate_number,))
            if cursor.fetchone() is None:
                logger.warning(f"Vehicle with plate number {plate_number} not found")
                conn.close()
                return False
            
            # Build update query
            query = 'UPDATE vehicles SET updated_at = CURRENT_TIMESTAMP'
            params = []
            
            if description is not None:
                query += ', description = ?'
                params.append(description)
            
            if authorized is not None:
                query += ', authorized = ?'
                params.append(authorized)
            
            if valid_from is not None:
                query += ', valid_from = ?'
                params.append(valid_from)
            
            if valid_until is not None:
                query += ', valid_until = ?'
                params.append(valid_until)
            
            query += ' WHERE plate_number = ?'
            params.append(plate_number)
            
            # Update vehicle
            cursor.execute(query, params)
            
            # Commit changes
            conn.commit()
            
            # Close connection
            conn.close()
            
            logger.info(f"Updated vehicle with plate number {plate_number}")
            return True
        except Exception as e:
            logger.error(f"Error updating vehicle: {e}")
            return False
    
    def delete_vehicle(self, plate_number):
        """
        Delete a vehicle from the database.
        
        Args:
            plate_number (str): License plate number
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete vehicle
            cursor.execute('DELETE FROM vehicles WHERE plate_number = ?', (plate_number,))
            
            # Check if any rows were affected
            if cursor.rowcount == 0:
                logger.warning(f"Vehicle with plate number {plate_number} not found")
                conn.close()
                return False
            
            # Commit changes
            conn.commit()
            
            # Close connection
            conn.close()
            
            logger.info(f"Deleted vehicle with plate number {plate_number}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vehicle: {e}")
            return False
    
    def get_vehicle(self, plate_number):
        """
        Get a vehicle from the database.
        
        Args:
            plate_number (str): License plate number
            
        Returns:
            dict: Vehicle data, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Get vehicle
            cursor.execute('SELECT * FROM vehicles WHERE plate_number = ?', (plate_number,))
            row = cursor.fetchone()
            
            # Close connection
            conn.close()
            
            if row is None:
                return None
            
            # Convert row to dictionary
            vehicle = dict(row)
            
            return vehicle
        except Exception as e:
            logger.error(f"Error getting vehicle: {e}")
            return None
    
    def get_vehicles(self, authorized=None, limit=100, offset=0):
        """
        Get vehicles from the database.
        
        Args:
            authorized (bool, optional): Filter by authorization status
            limit (int, optional): Maximum number of results
            offset (int, optional): Offset for pagination
            
        Returns:
            list: List of vehicle dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT * FROM vehicles'
            params = []
            
            if authorized is not None:
                query += ' WHERE authorized = ?'
                params.append(1 if authorized else 0)
            
            query += ' ORDER BY plate_number LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            # Get vehicles
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Close connection
            conn.close()
            
            # Convert rows to dictionaries
            vehicles = [dict(row) for row in rows]
            
            return vehicles
        except Exception as e:
            logger.error(f"Error getting vehicles: {e}")
            return []
    
    def get_vehicle_count(self, authorized=None):
        """
        Get the count of vehicles in the database.
        
        Args:
            authorized (bool, optional): Filter by authorization status
            
        Returns:
            int: Number of vehicles
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT COUNT(*) FROM vehicles'
            params = []
            
            if authorized is not None:
                query += ' WHERE authorized = ?'
                params.append(1 if authorized else 0)
            
            # Get count
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            # Close connection
            conn.close()
            
            return count
        except Exception as e:
            logger.error(f"Error getting vehicle count: {e}")
            return 0
    
    def is_vehicle_authorized(self, plate_number):
        """
        Check if a vehicle is authorized.
        
        Args:
            plate_number (str): License plate number
            
        Returns:
            bool: True if authorized, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if vehicle is authorized
            cursor.execute(
                '''
                SELECT authorized FROM vehicles 
                WHERE plate_number = ? 
                AND (valid_from IS NULL OR valid_from <= ?) 
                AND (valid_until IS NULL OR valid_until >= ?)
                ''',
                (plate_number, now, now)
            )
            
            row = cursor.fetchone()
            
            # Close connection
            conn.close()
            
            if row is None:
                return False
            
            return bool(row[0])
        except Exception as e:
            logger.error(f"Error checking vehicle authorization: {e}")
            return False
    
    def log_vehicle_access(self, plate_number, direction='entry', authorized=None, notes=None):
        """
        Log vehicle access.
        
        Args:
            plate_number (str): License plate number
            direction (str, optional): Direction ('entry' or 'exit')
            authorized (bool, optional): Whether the vehicle is authorized
            notes (str, optional): Additional notes about the access event
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # If authorized is not provided, check if vehicle is authorized
            if authorized is None:
                authorized = self.is_vehicle_authorized(plate_number)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Log access
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO access_logs 
                (plate_number, created_at, direction, authorized, notes) 
                VALUES (?, ?, ?, ?, ?)
            ''', (plate_number, timestamp, direction, authorized, notes))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Logged {direction} access for vehicle {plate_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging vehicle access: {e}")
            return False
    
    def get_access_logs(self, plate_number=None, start_time=None, end_time=None, limit=100, offset=0, exclude_id=None):
        """
        Get access logs from the database.
        
        Args:
            plate_number (str, optional): Filter by license plate number
            start_time (datetime, optional): Filter by start time
            end_time (datetime, optional): Filter by end time
            limit (int, optional): Maximum number of results
            offset (int, optional): Offset for pagination
            exclude_id (int, optional): ID to exclude from results
            
        Returns:
            list: List of access log dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT * FROM access_logs'
            params = []
            conditions = []
            
            if plate_number:
                conditions.append('plate_number = ?')
                params.append(plate_number)
            
            if start_time:
                if isinstance(start_time, datetime):
                    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
                conditions.append('created_at >= ?')
                params.append(start_time)
            
            if end_time:
                if isinstance(end_time, datetime):
                    end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
                conditions.append('created_at <= ?')
                params.append(end_time)
            
            if exclude_id:
                conditions.append('id != ?')
                params.append(exclude_id)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            # Get logs
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Close connection
            conn.close()
            
            # Convert rows to dictionaries
            logs = [dict(row) for row in rows]
            
            return logs
        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return []
    
    def get_access_log_count(self, plate_number=None, start_time=None, end_time=None, today_only=False):
        """
        Get the count of access logs in the database.
        
        Args:
            plate_number (str, optional): Filter by license plate number
            start_time (datetime, optional): Filter by start time
            end_time (datetime, optional): Filter by end time
            today_only (bool, optional): If True, only count logs from today
            
        Returns:
            int: Number of access logs
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT COUNT(*) FROM access_logs'
            params = []
            conditions = []
            
            if plate_number:
                conditions.append('plate_number = ?')
                params.append(plate_number)
            
            if start_time:
                if isinstance(start_time, datetime):
                    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
                conditions.append('created_at >= ?')
                params.append(start_time)
            
            if end_time:
                if isinstance(end_time, datetime):
                    end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
                conditions.append('created_at <= ?')
                params.append(end_time)
            
            if today_only:
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
                conditions.append('created_at >= ?')
                params.append(today_start)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            # Get count
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            # Close connection
            conn.close()
            
            return count
        except Exception as e:
            logger.error(f"Error getting access log count: {e}")
            return 0
    
    def get_access_logs_by_date_range(self, start_date, end_date):
        """
        Get access logs within a date range.
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            list: List of access log dictionaries
        """
        try:
            # Format dates for SQLite
            start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
            
            return self.get_access_logs(start_time=start_str, end_time=end_str, limit=10000)
        except Exception as e:
            logger.error(f"Error getting access logs by date range: {e}")
            return []
    
    def get_all_parking_durations(self):
        """
        Calculate parking durations for all vehicles.
        
        Returns:
            list: List of timedelta objects representing parking durations
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Get all plate numbers that have both entry and exit records
            cursor.execute(
                '''
                SELECT DISTINCT plate_number 
                FROM access_logs 
                WHERE plate_number IN (
                    SELECT plate_number 
                    FROM access_logs 
                    WHERE direction = 'entry'
                ) AND plate_number IN (
                    SELECT plate_number 
                    FROM access_logs 
                    WHERE direction = 'exit'
                )
                '''
            )
            
            plate_numbers = [row['plate_number'] for row in cursor.fetchall()]
            
            durations = []
            
            for plate in plate_numbers:
                # Get all entry and exit times for this plate
                cursor.execute(
                    '''
                    SELECT direction, created_at 
                    FROM access_logs 
                    WHERE plate_number = ? 
                    ORDER BY created_at
                    ''',
                    (plate,)
                )
                
                logs = [dict(row) for row in cursor.fetchall()]
                
                # Calculate durations between entry and exit pairs
                entry_time = None
                for log in logs:
                    if log['direction'] == 'entry' and entry_time is None:
                        entry_time = datetime.strptime(log['created_at'], '%Y-%m-%d %H:%M:%S')
                    elif log['direction'] == 'exit' and entry_time is not None:
                        exit_time = datetime.strptime(log['created_at'], '%Y-%m-%d %H:%M:%S')
                        duration = exit_time - entry_time
                        durations.append(duration)
                        entry_time = None
            
            # Close connection
            conn.close()
            
            return durations
        except Exception as e:
            logger.error(f"Error calculating parking durations: {e}")
            return []
    
    def _check_backup(self):
        """
        Check if database backup is needed.
        """
        current_time = time.time()
        
        # Check if backup interval has passed
        if current_time - self.last_backup_time >= self.backup_interval:
            self._backup_database()
            self.last_backup_time = current_time
    
    def backup_database(self):
        """
        Create a backup of the database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f'amslpr_backup_{timestamp}.db')
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Created database backup: {backup_path}")
            self.last_backup_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return False
            
    # Camera persistence methods
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
                values = []
                for field in fields:
                    values.append(camera_info.get(field))
                
                placeholders = ', '.join(['?' for _ in fields])
                fields_str = ', '.join(fields)
                
                cursor.execute(f'INSERT INTO cameras ({fields_str}) VALUES ({placeholders})', values)
                logger.info(f"Added camera with IP {camera_info['ip']}")
            
            # Commit changes
            conn.commit()
            conn.close()
            
            # Log the database path for debugging
            logger.info(f"Camera saved to database at {self.db_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error adding camera to database: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def get_all_cameras(self):
        """
        Get all cameras from the database.
        
        Returns:
            list: List of camera dictionaries
        """
        try:
            # Log the database path for debugging
            logger.info(f"Loading cameras from database at {self.db_path}")
            
            # Check if database file exists
            if not os.path.exists(self.db_path):
                logger.error(f"Database file does not exist: {self.db_path}")
                return []
                
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Check if cameras table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
            if not cursor.fetchone():
                logger.error("Cameras table does not exist in the database")
                # Create cameras table
                logger.info("Creating cameras table")
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
                conn.close()
                return []
            
            # Get all cameras
            cursor.execute('SELECT * FROM cameras')
            rows = cursor.fetchall()
            
            # Close connection
            conn.close()
            
            # Convert rows to dictionaries
            cameras = [dict(row) for row in rows]
            logger.info(f"Retrieved {len(cameras)} cameras from database")
            
            # Log camera details for debugging
            for camera in cameras:
                logger.info(f"Camera from DB: IP={camera.get('ip')}, Name={camera.get('name')}, Stream URI={camera.get('stream_uri')}")
            
            return cameras
        except Exception as e:
            logger.error(f"Error getting cameras from database: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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

    # Parking-related methods
    def start_parking_session(self, plate_number):
        """
        Start a new parking session for a vehicle.
        
        Args:
            plate_number (str): License plate number
            
        Returns:
            int: Session ID
        """
        try:
            # Get current time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Get car park settings from config
            payment_location = self.config['parking'].get('payment_location', 'exit')
            payment_required = self.config['parking'].get('payment_required_for_exit', 'always')
            
            # Insert new session
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO parking_sessions 
                   (plate_number, entry_time, status, payment_location, payment_required) 
                   VALUES (?, ?, ?, ?, ?)""",
                (plate_number, now, 'pending', payment_location, payment_required)
            )
            conn.commit()
            
            # Get the session ID
            session_id = cursor.lastrowid
            
            # Log the event
            logger.info(f"Started parking session for {plate_number}")
            
            conn.close()
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting parking session: {e}")
            return None
    
    def end_parking_session(self, plate_number):
        """
        End a parking session for a vehicle and calculate the fee.
        
        Args:
            plate_number (str): License plate number
            
        Returns:
            dict: Session details including calculated fee
        """
        try:
            # Get active session
            session = self.get_active_parking_session(plate_number)
            if not session:
                logger.warning(f"No active parking session found for {plate_number}")
                return None
            
            # Get current time
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate duration
            entry_time = datetime.strptime(session['entry_time'], '%Y-%m-%d %H:%M:%S')
            duration = now - entry_time
            duration_minutes = int(duration.total_seconds() / 60)
            
            # Get payment required setting from session
            payment_required = session.get('payment_required', 'always')
            
            # Calculate fee based on duration and rates
            fee = self._calculate_parking_fee(duration_minutes)
            
            # Check if payment is required based on the setting
            if payment_required == 'never':
                # No payment required (free parking)
                fee = 0.0
                payment_status = 'free'
            elif payment_required == 'grace_period' and fee == 0:
                # Within grace period, no payment required
                payment_status = 'free'
            else:
                # Payment required
                payment_status = 'pending'
            
            # Update session
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE parking_sessions
                SET exit_time = ?, duration_minutes = ?, calculated_fee = ?, payment_status = ?
                WHERE id = ?
            ''', (now_str, duration_minutes, fee, payment_status, session['id']))
            
            conn.commit()
            conn.close()
            
            # Get updated session
            updated_session = self.get_parking_session(session['id'])
            
            # Log the event
            self.log_event('parking_session_end', 
                          f"Ended parking session for {plate_number}, duration: {duration_minutes} min, fee: {fee}")
            
            return updated_session
            
        except Exception as e:
            logger.error(f"Error ending parking session: {e}")
            return None
    
    def get_active_parking_session(self, plate_number):
        """
        Get the active parking session for a vehicle.
        
        Args:
            plate_number (str): License plate number
            
        Returns:
            dict: Session data if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM parking_sessions 
                WHERE plate_number = ? AND exit_time IS NULL 
                ORDER BY entry_time DESC LIMIT 1
            ''', (plate_number,))
            
            session = cursor.fetchone()
            conn.close()
            
            if session:
                return dict(session)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting active parking session: {e}")
            return None
    
    def calculate_parking_fee(self, session_id, exit_time=None):
        """
        Calculate the parking fee for a session.
        
        Args:
            session_id (int): Parking session ID
            exit_time (str, optional): Exit time string (format: '%Y-%m-%d %H:%M:%S')
            
        Returns:
            float: Calculated fee
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get session data
            cursor.execute('SELECT * FROM parking_sessions WHERE id = ?', (session_id,))
            session = cursor.fetchone()
            
            if not session:
                logger.warning(f"No parking session found with ID {session_id}")
                conn.close()
                return 0.0
            
            # Get parking configuration
            parking_config = self.config.get('parking', {})
            rates = parking_config.get('rates', {})
            grace_period_minutes = parking_config.get('grace_period_minutes', 15)
            special_rates = parking_config.get('special_rates', [])
            
            # Parse times
            entry_time = datetime.strptime(session['entry_time'], '%Y-%m-%d %H:%M:%S')
            
            if exit_time is None:
                if session['exit_time'] is None:
                    # If no exit time provided and none in session, use current time
                    exit_time_obj = datetime.now()
                else:
                    # Use exit time from session
                    exit_time_obj = datetime.strptime(session['exit_time'], '%Y-%m-%d %H:%M:%S')
            else:
                # Use provided exit time
                if isinstance(exit_time, str):
                    exit_time_obj = datetime.strptime(exit_time, '%Y-%m-%d %H:%M:%S')
                else:
                    exit_time_obj = exit_time
            
            # Calculate duration in minutes
            duration = (exit_time_obj - entry_time).total_seconds() / 60
            
            # Check for grace period
            if duration <= grace_period_minutes:
                logger.info(f"Vehicle within grace period ({duration:.1f} minutes)")
                return 0.0
            
            # Check for special rates
            for special_rate in special_rates:
                if self._check_special_rate_applies(special_rate, entry_time, exit_time_obj):
                    logger.info(f"Special rate '{special_rate['name']}' applies")
                    
                    # Update session with special rate info
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE parking_sessions SET special_rate_applied = ? WHERE id = ?',
                        (special_rate['name'], session_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    return special_rate['flat_rate']
            
            # Standard rate calculation
            # Check if it's a weekend
            is_weekend = entry_time.weekday() >= 5  # 5=Saturday, 6=Sunday
            
            # Calculate hours (rounded up)
            hours = int((duration - grace_period_minutes) / 60) + 1  # Round up to nearest hour
            
            if is_weekend:
                hourly_rate = rates.get('weekend_hourly', rates.get('hourly', 2.0))
                daily_max = rates.get('weekend_daily_max', rates.get('daily_max', 20.0))
            else:
                hourly_rate = rates.get('hourly', 2.0)
                daily_max = rates.get('daily_max', 20.0)
            
            # Calculate fee
            fee = hours * hourly_rate
            
            # Apply daily maximum if applicable
            if fee > daily_max:
                fee = daily_max
            
            logger.info(f"Calculated parking fee: {fee:.2f} for {hours} hours")
            return round(fee, 2)
        
        except Exception as e:
            logger.error(f"Error calculating parking fee: {e}")
            return 0.0
    
    def _calculate_parking_fee(self, duration_minutes):
        """
        Calculate parking fee based on duration and configured rates.
        
        Args:
            duration_minutes (int): Parking duration in minutes
            
        Returns:
            float: Calculated fee
        """
        try:
            # Get parking rates from config
            rates = self.config['parking'].get('rates', {})
            grace_period = self.config['parking'].get('grace_period_minutes', 15)
            hourly_rate = rates.get('hourly', 2.50)
            daily_max = rates.get('daily_max', 20.00)
            
            # Check if within grace period
            if duration_minutes <= grace_period:
                return 0.0
            
            # Calculate hours (rounded up)
            hours = math.ceil((duration_minutes - grace_period) / 60)
            
            # Calculate fee
            fee = hours * hourly_rate
            
            # Apply daily maximum if applicable
            if fee > daily_max:
                fee = daily_max
            
            # Round to 2 decimal places
            fee = round(fee, 2)
            
            return fee
            
        except Exception as e:
            logger.error(f"Error calculating parking fee: {e}")
            return 0.0
    
    def _check_special_rate_applies(self, special_rate, entry_time, exit_time):
        """
        Check if a special rate applies to a parking session.
        
        Args:
            special_rate (dict): Special rate configuration
            entry_time (datetime): Entry time
            exit_time (datetime): Exit time
            
        Returns:
            bool: True if special rate applies, False otherwise
        """
        try:
            # Check day of week
            entry_day = entry_time.weekday()  # 0=Monday, 6=Sunday
            if 'days' in special_rate and entry_day not in special_rate['days']:
                return False
            
            # Parse time strings
            def parse_time(time_str, base_date):
                if not time_str:
                    return None
                hour, minute = map(int, time_str.split(':'))
                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Check entry time constraints
            if 'entry_before' in special_rate:
                entry_before = parse_time(special_rate['entry_before'], entry_time)
                if entry_time > entry_before:
                    return False
            
            if 'entry_after' in special_rate:
                entry_after = parse_time(special_rate['entry_after'], entry_time)
                if entry_time < entry_after:
                    return False
            
            # Check exit time constraints
            if 'exit_before' in special_rate:
                exit_before = parse_time(special_rate['exit_before'], exit_time)
                if exit_time > exit_before:
                    return False
            
            if 'exit_after' in special_rate:
                exit_after = parse_time(special_rate['exit_after'], exit_time)
                if exit_time < exit_after:
                    return False
            
            # All constraints satisfied
            return True
        
        except Exception as e:
            logger.error(f"Error checking special rate: {e}")
            return False
    
    def record_payment(self, session_id, amount, payment_method, transaction_id=None, terminal_id=None, status='completed', response_code=None, response_message=None, receipt_number=None):
        """
        Record a payment for a parking session.
        
        Args:
            session_id (int): Parking session ID
            amount (float): Payment amount
            payment_method (str): Payment method
            transaction_id (str, optional): Transaction ID
            terminal_id (str, optional): Terminal ID
            status (str, optional): Transaction status
            response_code (str, optional): Response code
            response_message (str, optional): Response message
            receipt_number (str, optional): Receipt number
            
        Returns:
            int: Transaction ID if successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get session data
            cursor.execute('SELECT * FROM parking_sessions WHERE id = ?', (session_id,))
            session = cursor.fetchone()
            
            if not session:
                logger.warning(f"No parking session found with ID {session_id}")
                conn.close()
                return None
            
            # Get tax configuration
            tax_rate = self.config.get('parking', {}).get('tax_rate', 20.0)
            currency = self.config.get('parking', {}).get('currency', 'GBP')
            
            # Calculate tax amount (assuming amount includes tax)
            tax_amount = round(amount - (amount / (1 + (tax_rate / 100))), 2)
            
            # Record payment transaction
            cursor.execute('''
                INSERT INTO payment_transactions 
                (parking_session_id, amount, tax_amount, currency, transaction_id, terminal_id, 
                payment_method, status, response_code, response_message, receipt_number) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, amount, tax_amount, currency, transaction_id, terminal_id, 
                  payment_method, status, response_code, response_message, receipt_number))
            
            transaction_id = cursor.lastrowid
            
            # Update parking session
            cursor.execute('''
                UPDATE parking_sessions 
                SET paid_amount = ?, payment_status = ?, payment_method = ?, 
                transaction_id = ?, receipt_number = ?, updated_at = ? 
                WHERE id = ?
            ''', (amount, 'paid', payment_method, transaction_id, 
                  receipt_number, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded payment of {amount} for parking session {session_id}")
            return transaction_id
        
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            return None
    
    def get_parking_session(self, session_id):
        """
        Get details of a specific parking session.
        
        Args:
            session_id (int): Parking session ID
            
        Returns:
            dict: Session details
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, plate_number, entry_time, exit_time, duration_minutes,
                       calculated_fee, payment_status, payment_time, payment_method,
                       transaction_id, receipt_number, special_rate_applied,
                       payment_location, payment_required, notes
                FROM parking_sessions
                WHERE id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting parking session: {e}")
            return None
    
    def get_parking_sessions(self, plate_number=None, start_time=None, end_time=None, status=None, limit=100, offset=0):
        """
        Get parking sessions with optional filters.
        
        Args:
            plate_number (str, optional): Filter by license plate
            start_time (str, optional): Filter by start time
            end_time (str, optional): Filter by end time
            status (str, optional): Filter by payment status ('pending', 'paid', 'canceled')
            limit (int, optional): Maximum number of results
            offset (int, optional): Offset for pagination
            
        Returns:
            list: List of session dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM parking_sessions'
            params = []
            where_clauses = []
            
            if plate_number:
                where_clauses.append('plate_number LIKE ?')
                params.append(f'%{plate_number}%')
            
            if start_time:
                where_clauses.append('entry_time >= ?')
                params.append(start_time)
            
            if end_time:
                # Add time to make end_date inclusive
                end_time_with_time = end_time
                if len(end_time) == 10:  # If only date is provided (YYYY-MM-DD)
                    end_time_with_time = f"{end_time} 23:59:59"
                where_clauses.append('entry_time <= ?')
                params.append(end_time_with_time)
            
            if status:
                if status == 'pending':
                    where_clauses.append('(payment_status IS NULL OR payment_status = "pending")')
                elif status in ['paid', 'canceled']:
                    where_clauses.append('payment_status = ?')
                    params.append(status)
            
            if where_clauses:
                query += ' WHERE ' + ' AND '.join(where_clauses)
            
            query += ' ORDER BY entry_time DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            logger.debug(f"Executing query: {query} with params: {params}")
            cursor.execute(query, params)
            sessions = cursor.fetchall()
            conn.close()
            
            return [dict(session) for session in sessions]
        
        except Exception as e:
            logger.error(f"Error getting parking sessions: {e}")
            return []
    
    def get_parking_statistics(self, start_date=None, end_date=None):
        """
        Get parking statistics for a date range.
        
        Args:
            start_date (str, optional): Start date (format: '%Y-%m-%d')
            end_date (str, optional): End date (format: '%Y-%m-%d')
            
        Returns:
            dict: Statistics dictionary
        """
        try:
            if start_date is None:
                # Default to last 30 days
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Add time to make end_date inclusive
            end_date_inclusive = end_date + ' 23:59:59'
            
            # Total sessions
            cursor.execute('''
                SELECT COUNT(*) as total_sessions FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ?
            ''', (start_date, end_date_inclusive))
            total_sessions = cursor.fetchone()['total_sessions']
            
            # Completed sessions
            cursor.execute('''
                SELECT COUNT(*) as completed_sessions FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ? AND exit_time IS NOT NULL
            ''', (start_date, end_date_inclusive))
            completed_sessions = cursor.fetchone()['completed_sessions']
            
            # Total revenue
            cursor.execute('''
                SELECT SUM(paid_amount) as total_revenue FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ? AND payment_status = 'paid'
            ''', (start_date, end_date_inclusive))
            result = cursor.fetchone()
            total_revenue = result['total_revenue'] if result['total_revenue'] is not None else 0
            
            # Average parking duration
            cursor.execute('''
                SELECT AVG((julianday(exit_time) - julianday(entry_time)) * 24 * 60) as avg_duration 
                FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ? AND exit_time IS NOT NULL
            ''', (start_date, end_date_inclusive))
            result = cursor.fetchone()
            avg_duration = result['avg_duration'] if result['avg_duration'] is not None else 0
            
            # Payment method breakdown
            cursor.execute('''
                SELECT payment_method, COUNT(*) as count 
                FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ? AND payment_status = 'paid' AND payment_method IS NOT NULL 
                GROUP BY payment_method
            ''', (start_date, end_date_inclusive))
            payment_methods = {row['payment_method']: row['count'] for row in cursor.fetchall()}
            
            # Special rate usage
            cursor.execute('''
                SELECT special_rate_applied, COUNT(*) as count 
                FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ? AND special_rate_applied IS NOT NULL 
                GROUP BY special_rate_applied
            ''', (start_date, end_date_inclusive))
            special_rates = {row['special_rate_applied']: row['count'] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_revenue': round(total_revenue, 2),
                'avg_duration_minutes': round(avg_duration, 1),
                'payment_methods': payment_methods,
                'special_rates': special_rates,
                'start_date': start_date,
                'end_date': end_date
            }
        
        except Exception as e:
            logger.error(f"Error getting parking statistics: {e}")
            return {}
    
    def get_daily_revenue(self, start_date=None, end_date=None):
        """
        Get daily revenue data for a date range.
        
        Args:
            start_date (str, optional): Start date (format: '%Y-%m-%d')
            end_date (str, optional): End date (format: '%Y-%m-%d')
            
        Returns:
            list: List of dictionaries with date and revenue
        """
        try:
            if start_date is None:
                # Default to last 30 days
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Add time to make end_date inclusive
            end_date_inclusive = end_date + ' 23:59:59'
            
            # Get daily revenue
            cursor.execute('''
                SELECT 
                    date(entry_time) as date,
                    SUM(paid_amount) as revenue
                FROM parking_sessions 
                WHERE entry_time >= ? AND entry_time <= ? AND payment_status = 'paid'
                GROUP BY date(entry_time)
                ORDER BY date(entry_time)
            ''', (start_date, end_date_inclusive))
            
            daily_revenue = []
            for row in cursor.fetchall():
                daily_revenue.append({
                    'date': row['date'],
                    'revenue': round(row['revenue'] if row['revenue'] is not None else 0, 2)
                })
            
            conn.close()
            return daily_revenue
        
        except Exception as e:
            logger.error(f"Error getting daily revenue: {e}")
            return []
    
    def log_event(self, event_type, event_data):
        """
        Log a system event.
        
        Args:
            event_type (str): Type of event
            event_data (str): Event data or description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Insert event
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO events (event_type, event_data, timestamp) VALUES (?, ?, ?)",
                (event_type, event_data, now)
            )
            
            conn.commit()
            conn.close()
            
            # Log to console as well
            logger.info(f"Event: {event_type} - {event_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return False
    
    def get_access_log(self, log_id):
        """
        Get a single access log by ID.
        
        Args:
            log_id (int): ID of the access log to retrieve
            
        Returns:
            dict: Access log dictionary or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Get log
            cursor.execute('SELECT * FROM access_logs WHERE id = ?', (log_id,))
            row = cursor.fetchone()
            
            # Close connection
            conn.close()
            
            # Convert row to dictionary
            if row:
                return dict(row)
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting access log {log_id}: {e}")
            return None

    def validate_api_key(self, api_key):
        """
        Validate an API key.
        
        Args:
            api_key (str): API key to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Get current time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if key exists and is active
            cursor.execute(
                'SELECT id, expires_at, is_active FROM api_keys WHERE key = ?',
                (api_key,)
            )
            
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
                conn.close()
                return False
            
            key_id, expires_at, is_active = row
            
            # Check if key is active
            if not is_active:
                logger.warning(f"Inactive API key attempted: {api_key[:10]}...")
                conn.close()
                return False
            
            # Check if key has expired
            if expires_at and expires_at < now:
                logger.warning(f"Expired API key attempted: {api_key[:10]}...")
                conn.close()
                return False
            
            # Update last used timestamp
            cursor.execute(
                'UPDATE api_keys SET last_used = ? WHERE id = ?',
                (now, key_id)
            )
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False

    def generate_api_key(self, name, expires_at=None, permissions=None):
        """
        Generate and store a new API key.
        
        Args:
            name (str): Name or description for this API key
            expires_at (datetime, optional): Expiration date for the key
            permissions (str, optional): JSON string of permissions
            
        Returns:
            str: The generated API key or None if failed
        """
        try:
            import secrets
            import string
            import json
            
            # Generate a secure random API key
            alphabet = string.ascii_letters + string.digits
            key = 'amslpr_' + ''.join(secrets.choice(alphabet) for _ in range(32))
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert permissions to JSON string if it's a dict
            if permissions and isinstance(permissions, dict):
                permissions = json.dumps(permissions)
            
            cursor.execute(
                'INSERT INTO api_keys (key, name, expires_at, permissions) VALUES (?, ?, ?, ?)',
                (key, name, expires_at, permissions)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Generated new API key for {name}")
            return key
            
        except Exception as e:
            logger.error(f"Error generating API key: {e}")
            return None

    def revoke_api_key(self, api_key):
        """
        Revoke an API key.
        
        Args:
            api_key (str): API key to revoke
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Set key as inactive
            cursor.execute(
                'UPDATE api_keys SET is_active = 0 WHERE key = ?',
                (api_key,)
            )
            
            if cursor.rowcount == 0:
                logger.warning(f"API key not found for revocation: {api_key[:10]}...")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            logger.info(f"Revoked API key: {api_key[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key: {e}")
            return False
    
    def get_api_keys(self):
        """
        Get all API keys.
        
        Returns:
            list: List of API key dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, key, name, created_at, expires_at, last_used, is_active FROM api_keys')
            rows = cursor.fetchall()
            
            conn.close()
            
            # Convert rows to dictionaries
            keys = [dict(row) for row in rows]
            
            # Mask actual key values for security
            for key in keys:
                if 'key' in key and key['key']:
                    key['key'] = key['key'][:10] + '...' + key['key'][-5:]
            
            return keys
            
        except Exception as e:
            logger.error(f"Error getting API keys: {e}")
            return []

    def get_payment_transactions(self, session_id):
        """
        Get payment transactions for a specific parking session.
        
        Args:
            session_id (int): Parking session ID
            
        Returns:
            list: List of payment transaction dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, parking_session_id, amount, tax_amount, currency, transaction_id,
                       terminal_id, payment_method, status, response_code, response_message,
                       receipt_number, created_at
                FROM payment_transactions
                WHERE parking_session_id = ?
                ORDER BY created_at DESC
            ''', (session_id,))
            
            transactions = cursor.fetchall()
            conn.close()
            
            return [dict(transaction) for transaction in transactions]
        
        except Exception as e:
            logger.error(f"Error getting payment transactions: {e}")
            return []

    def delete_camera(self, camera_id):
        """
        Delete a camera from the database.
        
        Args:
            camera_id (str): ID of the camera to delete
            
        Returns:
            bool: True if camera was deleted successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if cameras table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
            if not cursor.fetchone():
                logger.warning("Cameras table does not exist")
                return False
                
            # Delete camera from database
            cursor.execute("DELETE FROM cameras WHERE ip = ?", (camera_id,))
            conn.commit()
            
            affected_rows = cursor.rowcount
            conn.close()
            
            if affected_rows > 0:
                logger.info(f"Camera {camera_id} deleted from database")
                return True
            else:
                logger.warning(f"Camera {camera_id} not found in database")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting camera from database: {str(e)}")
            return False

    def get_all_cameras(self):
        """
        Get all cameras from the database.
        
        Returns:
            list: List of camera dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if cameras table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
            if not cursor.fetchone():
                logger.warning("Cameras table does not exist")
                return []
            
            # Check if the extended camera fields exist
            cursor.execute("PRAGMA table_info(cameras)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # If the extended fields don't exist, alter the table to add them
            required_fields = ['port', 'username', 'password', 'stream_uri', 'manufacturer', 'model', 'name', 'location']
            missing_fields = [field for field in required_fields if field not in columns]
            
            # Add missing fields to the table
            for field in missing_fields:
                try:
                    cursor.execute(f"ALTER TABLE cameras ADD COLUMN {field} TEXT")
                    conn.commit()
                    logger.info(f"Added missing field '{field}' to cameras table")
                except Exception as e:
                    logger.warning(f"Error adding field '{field}' to cameras table: {str(e)}")
            
            # Get all cameras
            cursor.execute('SELECT * FROM cameras')
            cameras = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries
            return [dict(camera) for camera in cameras]
            
        except Exception as e:
            logger.error(f"Error getting cameras from database: {str(e)}")
            return []
    
    def get_all_cameras(self):
        """
        Get all cameras from the database.
        
        Returns:
            list: List of camera dictionaries
        """
        try:
            logger.error("======= CAMERA DEBUG ======= get_all_cameras method called")
            logger.error(f"======= CAMERA DEBUG ======= Database path: {self.db_path}")
            
            # Try to open the database file
            if not os.path.exists(self.db_path):
                logger.error("======= CAMERA DEBUG ======= Database file does not exist!")
                return []
                
            logger.error("======= CAMERA DEBUG ======= Database file exists")
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if cameras table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cameras'")
            if not cursor.fetchone():
                logger.error("======= CAMERA DEBUG ======= 'cameras' table does not exist in database!")
                conn.close()
                return []
                
            logger.error("======= CAMERA DEBUG ======= 'cameras' table exists in database")
            
            # Query all cameras
            cursor.execute('SELECT * FROM cameras')
            cameras = cursor.fetchall()
            camera_count = len(cameras)
            logger.error(f"======= CAMERA DEBUG ======= Found {camera_count} cameras in database")
            
            conn.close()
            
            # Convert to list of dictionaries
            camera_dicts = [dict(camera) for camera in cameras]
            if camera_dicts:
                logger.error(f"======= CAMERA DEBUG ======= First camera: {camera_dicts[0]}")
            
            return camera_dicts
            
        except Exception as e:
            logger.error(f"======= CAMERA DEBUG ======= Error getting cameras from database: {str(e)}")
            import traceback
            logger.error(f"======= CAMERA DEBUG ======= {traceback.format_exc()}")
            return []
    
    def save_camera(self, camera_info):
        """
        Save a camera to the database. If the camera already exists, it will be updated.
        
        Args:
            camera_info (dict): Camera information dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract camera info
            camera_id = camera_info.get('ip')
            if not camera_id:
                logger.error("Cannot save camera without IP address")
                return False
            
            # Check if camera exists
            cursor.execute('SELECT id FROM cameras WHERE ip = ?', (camera_id,))
            camera_exists = cursor.fetchone() is not None
            
            if camera_exists:
                # Update existing camera
                # Build the query dynamically based on available fields
                fields = []
                values = []
                for key, value in camera_info.items():
                    if key != 'ip':
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    logger.warning(f"No fields to update for camera {camera_id}")
                    conn.close()
                    return False
                
                # Add IP for WHERE clause
                values.append(camera_id)
                
                # Build and execute the query
                query = f"UPDATE cameras SET {', '.join(fields)} WHERE ip = ?";
                cursor.execute(query, values)
                
                logger.info(f"Updated camera {camera_id} in database")
            else:
                # Insert new camera
                # Build the query dynamically based on available fields
                fields = ['ip']
                placeholders = ['?']
                values = [camera_id]
                
                for key, value in camera_info.items():
                    if key != 'ip':
                        fields.append(key)
                        placeholders.append('?')
                        values.append(value)
                
                # Build and execute the query
                query = f"INSERT INTO cameras ({', '.join(fields)}) VALUES ({', '.join(placeholders)})";
                cursor.execute(query, values)
                
                logger.info(f"Added camera {camera_id} to database")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving camera to database: {str(e)}")
            return False
