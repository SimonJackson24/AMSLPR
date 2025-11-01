
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import sys
import os
import json
from datetime import datetime, timedelta
import random

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager
from src.utils.statistics import StatisticsManager

class TestStatistics(unittest.TestCase):
    """
    Test cases for the statistics functionality.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Create test database configuration
        self.config = {
            'db_path': 'tests/test_data/test_stats.db',
            'backup_interval': 86400
        }
        
        # Ensure test data directory exists
        os.makedirs(os.path.dirname(self.config['db_path']), exist_ok=True)
        
        # Remove test database if it exists
        if os.path.exists(self.config['db_path']):
            os.remove(self.config['db_path'])
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Initialize statistics manager
        self.stats_manager = StatisticsManager(self.db_manager)
        
        # Add test data
        self._add_test_data()
    
    def _add_test_data(self):
        """
        Add test data to the database.
        """
        # Add test vehicles
        vehicles = [
            {'plate': 'ABC123', 'desc': 'Test Vehicle 1', 'auth': True},
            {'plate': 'DEF456', 'desc': 'Test Vehicle 2', 'auth': True},
            {'plate': 'GHI789', 'desc': 'Test Vehicle 3', 'auth': False},
            {'plate': 'JKL012', 'desc': 'Test Vehicle 4', 'auth': True},
            {'plate': 'MNO345', 'desc': 'Test Vehicle 5', 'auth': False}
        ]
        
        for v in vehicles:
            self.db_manager.add_vehicle(v['plate'], v['desc'], v['auth'])
        
        # Add test access logs
        # Current time
        now = datetime.now()
        
        # Generate access logs for the past 10 days
        for day in range(10):
            day_date = now - timedelta(days=day)
            
            # Generate random number of entries/exits for each day
            num_entries = random.randint(5, 15)
            
            for _ in range(num_entries):
                # Random vehicle
                vehicle = random.choice(vehicles)
                
                # Random hour
                hour = random.randint(6, 22)
                minute = random.randint(0, 59)
                
                # Entry time
                entry_time = day_date.replace(hour=hour, minute=minute, second=0)
                
                # Exit time (1-5 hours later)
                duration_hours = random.randint(1, 5)
                exit_time = entry_time + timedelta(hours=duration_hours)
                
                # Log entry
                self.db_manager.log_vehicle_access(
                    plate_number=vehicle['plate'],
                    direction='entry',
                    authorized=vehicle['auth']
                )
                
                # Log exit
                self.db_manager.log_vehicle_access(
                    plate_number=vehicle['plate'],
                    direction='exit',
                    authorized=vehicle['auth']
                )
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Remove test database
        if os.path.exists(self.config['db_path']):
            os.remove(self.config['db_path'])
    
    def test_daily_traffic(self):
        """
        Test daily traffic statistics.
        """
        # Get daily traffic for the past 7 days
        daily_traffic = self.stats_manager.get_daily_traffic(days=7)
        
        # Check structure
        self.assertIn('dates', daily_traffic)
        self.assertIn('entry', daily_traffic)
        self.assertIn('exit', daily_traffic)
        self.assertIn('total', daily_traffic)
        
        # Check data types
        self.assertIsInstance(daily_traffic['dates'], list)
        self.assertIsInstance(daily_traffic['entry'], list)
        self.assertIsInstance(daily_traffic['exit'], list)
        self.assertIsInstance(daily_traffic['total'], list)
        
        # Check lengths - should be 7 days
        self.assertEqual(len(daily_traffic['dates']), 7)
        self.assertEqual(len(daily_traffic['entry']), 7)
        self.assertEqual(len(daily_traffic['exit']), 7)
        self.assertEqual(len(daily_traffic['total']), 7)
    
    def test_hourly_distribution(self):
        """
        Test hourly distribution statistics.
        """
        # Get hourly distribution
        hourly_distribution = self.stats_manager.get_hourly_distribution(days=30)
        
        # Check structure
        self.assertIn('hours', hourly_distribution)
        self.assertIn('entry', hourly_distribution)
        self.assertIn('exit', hourly_distribution)
        self.assertIn('total', hourly_distribution)
        
        # Check data types
        self.assertIsInstance(hourly_distribution['hours'], list)
        self.assertIsInstance(hourly_distribution['entry'], list)
        self.assertIsInstance(hourly_distribution['exit'], list)
        self.assertIsInstance(hourly_distribution['total'], list)
        
        # Check lengths
        self.assertEqual(len(hourly_distribution['hours']), 24)
        self.assertEqual(len(hourly_distribution['entry']), 24)
        self.assertEqual(len(hourly_distribution['exit']), 24)
        self.assertEqual(len(hourly_distribution['total']), 24)
    
    def test_vehicle_statistics(self):
        """
        Test vehicle statistics.
        """
        # Get vehicle statistics
        vehicle_stats = self.stats_manager.get_vehicle_statistics()
        
        # Check structure
        self.assertIn('total_vehicles', vehicle_stats)
        self.assertIn('authorized_vehicles', vehicle_stats)
        self.assertIn('unauthorized_vehicles', vehicle_stats)
        self.assertIn('most_frequent_vehicles', vehicle_stats)
        self.assertIn('avg_accesses_per_vehicle', vehicle_stats)
        self.assertIn('authorized_access_percentage', vehicle_stats)
        
        # Check data types
        self.assertIsInstance(vehicle_stats['total_vehicles'], int)
        self.assertIsInstance(vehicle_stats['authorized_vehicles'], int)
        self.assertIsInstance(vehicle_stats['unauthorized_vehicles'], int)
        self.assertIsInstance(vehicle_stats['most_frequent_vehicles'], dict)
        self.assertIsInstance(vehicle_stats['avg_accesses_per_vehicle'], float)
        self.assertIsInstance(vehicle_stats['authorized_access_percentage'], float)
        
        # Check values
        self.assertEqual(vehicle_stats['total_vehicles'], 5)
        self.assertEqual(vehicle_stats['authorized_vehicles'], 3)
        self.assertEqual(vehicle_stats['unauthorized_vehicles'], 2)
    
    def test_parking_duration_statistics(self):
        """
        Test parking duration statistics.
        """
        # Get parking duration statistics
        parking_stats = self.stats_manager.get_parking_duration_statistics()
        
        # Check structure
        self.assertIn('avg_duration_minutes', parking_stats)
        self.assertIn('max_duration_minutes', parking_stats)
        self.assertIn('min_duration_minutes', parking_stats)
        self.assertIn('duration_distribution', parking_stats)
        
        # Check data types
        self.assertIsInstance(parking_stats['avg_duration_minutes'], float)
        self.assertIsInstance(parking_stats['max_duration_minutes'], float)
        self.assertIsInstance(parking_stats['min_duration_minutes'], float)
        self.assertIsInstance(parking_stats['duration_distribution'], dict)

if __name__ == '__main__':
    unittest.main()
