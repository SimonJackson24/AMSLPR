# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import sqlite3
import os
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for VisiGate."""
    
    def __init__(self, db_path=None):
        """Initialize database manager."""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'visigate.db')
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create vehicles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS vehicles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plate_number TEXT NOT NULL UNIQUE,
                        authorized BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create access_logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS access_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plate_number TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        authorized BOOLEAN,
                        confidence REAL,
                        image_path TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def get_vehicle_count(self, authorized=None):
        """Get count of vehicles."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if authorized is None:
                    cursor.execute('SELECT COUNT(*) FROM vehicles')
                else:
                    cursor.execute('SELECT COUNT(*) FROM vehicles WHERE authorized = ?', (authorized,))
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting vehicle count: {str(e)}")
            return 0
    
    def get_access_logs(self, limit=None):
        """Get access logs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if limit:
                    cursor.execute('SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
                else:
                    cursor.execute('SELECT * FROM access_logs ORDER BY timestamp DESC')
                
                columns = [description[0] for description in cursor.description]
                logs = []
                
                for row in cursor.fetchall():
                    log = dict(zip(columns, row))
                    logs.append(log)
                
                return logs
        except Exception as e:
            logger.error(f"Error getting access logs: {str(e)}")
            return []
    
    def get_access_log_count(self, today_only=False):
        """Get count of access logs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if today_only:
                    today = date.today().isoformat()
                    cursor.execute('SELECT COUNT(*) FROM access_logs WHERE date(timestamp) = ?', (today,))
                else:
                    cursor.execute('SELECT COUNT(*) FROM access_logs')
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting access log count: {str(e)}")
            return 0
