
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import os
import sys
import sqlite3
import datetime
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.db_manager import DatabaseManager
from src.config.settings import load_config

class TestDatabaseManager(unittest.TestCase):
    """
    Test cases for database manager functionality.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Load configuration
        test_config_path = os.path.join(Path(__file__).parent, 'test_config.json')
        self.config = load_config(test_config_path)
        
        # Override database path for testing
        self.test_db_path = os.path.join(Path(__file__).parent, 'test_database.db')
        self.config['database']['path'] = self.test_db_path
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Initialize database
        self.db_manager.init_db()
        
        # Add test data
        self.add_test_data()
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Close database connection
        self.db_manager.close()
        
        # Remove test database file
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def add_test_data(self):
        """
        Add test data to the database.
        """
        # Add test vehicles
        self.db_manager.add_vehicle('ABC123', 'Test Vehicle 1', True)
        self.db_manager.add_vehicle('XYZ789', 'Test Vehicle 2', False)
        
        # Add test access logs
        now = datetime.datetime.now()
        one_hour_ago = now - datetime.timedelta(hours=1)
        
        # Add entry and exit for ABC123
        self.db_manager.add_access_log('ABC123', 'entry', True, one_hour_ago)
        self.db_manager.add_access_log('ABC123', 'exit', True, now)
        
        # Add entry for XYZ789
        self.db_manager.add_access_log('XYZ789', 'entry', False, now)
    
    def test_get_vehicle(self):
        """
        Test getting a vehicle from the database.
        """
        # Get existing vehicle
        vehicle = self.db_manager.get_vehicle('ABC123')
        self.assertIsNotNone(vehicle, "Failed to get existing vehicle")
        self.assertEqual(vehicle['plate_number'], 'ABC123', "Vehicle plate number mismatch")
        self.assertEqual(vehicle['description'], 'Test Vehicle 1', "Vehicle description mismatch")
        self.assertTrue(vehicle['authorized'], "Vehicle authorization mismatch")
        
        # Get non-existent vehicle
        vehicle = self.db_manager.get_vehicle('NONEXISTENT')
        self.assertIsNone(vehicle, "Got a vehicle that shouldn't exist")
    
    def test_get_vehicles(self):
        """
        Test getting multiple vehicles from the database.
        """
        # Get all vehicles
        vehicles = self.db_manager.get_vehicles()
        self.assertEqual(len(vehicles), 2, "Wrong number of vehicles returned")
        
        # Get authorized vehicles
        vehicles = self.db_manager.get_vehicles(authorized=True)
        self.assertEqual(len(vehicles), 1, "Wrong number of authorized vehicles returned")
        self.assertEqual(vehicles[0]['plate_number'], 'ABC123', "Wrong authorized vehicle returned")
        
        # Get unauthorized vehicles
        vehicles = self.db_manager.get_vehicles(authorized=False)
        self.assertEqual(len(vehicles), 1, "Wrong number of unauthorized vehicles returned")
        self.assertEqual(vehicles[0]['plate_number'], 'XYZ789', "Wrong unauthorized vehicle returned")
    
    def test_add_vehicle(self):
        """
        Test adding a vehicle to the database.
        """
        # Add a new vehicle
        result = self.db_manager.add_vehicle('DEF456', 'Test Vehicle 3', True)
        self.assertTrue(result, "Failed to add vehicle")
        
        # Verify the vehicle was added
        vehicle = self.db_manager.get_vehicle('DEF456')
        self.assertIsNotNone(vehicle, "Added vehicle not found")
        self.assertEqual(vehicle['description'], 'Test Vehicle 3', "Vehicle description mismatch")
        
        # Try to add a duplicate vehicle
        result = self.db_manager.add_vehicle('ABC123', 'Duplicate', True)
        self.assertFalse(result, "Added duplicate vehicle")
    
    def test_update_vehicle(self):
        """
        Test updating a vehicle in the database.
        """
        # Update an existing vehicle
        result = self.db_manager.update_vehicle('ABC123', 'Updated Description', False)
        self.assertTrue(result, "Failed to update vehicle")
        
        # Verify the vehicle was updated
        vehicle = self.db_manager.get_vehicle('ABC123')
        self.assertEqual(vehicle['description'], 'Updated Description', "Vehicle description not updated")
        self.assertFalse(vehicle['authorized'], "Vehicle authorization not updated")
        
        # Try to update a non-existent vehicle
        result = self.db_manager.update_vehicle('NONEXISTENT', 'Description', True)
        self.assertFalse(result, "Updated non-existent vehicle")
    
    def test_delete_vehicle(self):
        """
        Test deleting a vehicle from the database.
        """
        # Delete an existing vehicle
        result = self.db_manager.delete_vehicle('ABC123')
        self.assertTrue(result, "Failed to delete vehicle")
        
        # Verify the vehicle was deleted
        vehicle = self.db_manager.get_vehicle('ABC123')
        self.assertIsNone(vehicle, "Deleted vehicle still exists")
        
        # Try to delete a non-existent vehicle
        result = self.db_manager.delete_vehicle('NONEXISTENT')
        self.assertFalse(result, "Deleted non-existent vehicle")
    
    def test_get_access_logs(self):
        """
        Test getting access logs from the database.
        """
        # Get all access logs
        logs = self.db_manager.get_access_logs()
        self.assertEqual(len(logs), 3, "Wrong number of access logs returned")
        
        # Get access logs for a specific vehicle
        logs = self.db_manager.get_access_logs(plate_number='ABC123')
        self.assertEqual(len(logs), 2, "Wrong number of access logs returned for vehicle")
        
        # Get access logs for a specific direction
        logs = self.db_manager.get_access_logs(direction='entry')
        self.assertEqual(len(logs), 2, "Wrong number of entry access logs returned")
        
        logs = self.db_manager.get_access_logs(direction='exit')
        self.assertEqual(len(logs), 1, "Wrong number of exit access logs returned")
    
    def test_add_access_log(self):
        """
        Test adding an access log to the database.
        """
        # Add a new access log
        now = datetime.datetime.now()
        result = self.db_manager.add_access_log('DEF456', 'entry', False, now)
        self.assertTrue(result, "Failed to add access log")
        
        # Verify the access log was added
        logs = self.db_manager.get_access_logs(plate_number='DEF456')
        self.assertEqual(len(logs), 1, "Added access log not found")
        self.assertEqual(logs[0]['direction'], 'entry', "Access log direction mismatch")
        self.assertFalse(logs[0]['authorized'], "Access log authorization mismatch")
    
    def test_get_parking_duration(self):
        """
        Test getting parking duration from the database.
        """
        # Get parking duration for a vehicle with entry and exit
        duration = self.db_manager.get_parking_duration('ABC123')
        self.assertIsNotNone(duration, "Failed to get parking duration")
        
        # Duration should be approximately 1 hour
        self.assertGreaterEqual(duration.total_seconds(), 3500, "Parking duration too short")
        self.assertLessEqual(duration.total_seconds(), 3700, "Parking duration too long")
        
        # Get parking duration for a vehicle with only entry
        duration = self.db_manager.get_parking_duration('XYZ789')
        self.assertIsNone(duration, "Got parking duration for vehicle with no exit")

if __name__ == '__main__':
    unittest.main()
