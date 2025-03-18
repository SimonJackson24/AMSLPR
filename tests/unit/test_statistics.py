#!/usr/bin/env python3
"""
Unit tests for the statistics module.
"""

import os
import sys
import unittest
import tempfile
import json
import datetime
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.utils.statistics import StatisticsManager

class TestStatistics(unittest.TestCase):
    """
    Unit tests for the StatisticsManager class.
    """
    
    def setUp(self):
        """
        Set up the test environment.
        """
        # Create a temporary log file with test data
        self.temp_log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        
        # Create test log data
        self.test_logs = [
            {
                "timestamp": "2025-03-14T08:00:00",
                "plate": "ABC123",
                "confidence": 0.95,
                "camera_id": "camera1",
                "event_type": "entry",
                "authorized": True
            },
            {
                "timestamp": "2025-03-14T08:30:00",
                "plate": "DEF456",
                "confidence": 0.92,
                "camera_id": "camera1",
                "event_type": "entry",
                "authorized": True
            },
            {
                "timestamp": "2025-03-14T09:00:00",
                "plate": "GHI789",
                "confidence": 0.88,
                "camera_id": "camera2",
                "event_type": "entry",
                "authorized": False
            },
            {
                "timestamp": "2025-03-14T12:00:00",
                "plate": "ABC123",
                "confidence": 0.94,
                "camera_id": "camera2",
                "event_type": "exit",
                "authorized": True
            },
            {
                "timestamp": "2025-03-14T14:00:00",
                "plate": "DEF456",
                "confidence": 0.91,
                "camera_id": "camera2",
                "event_type": "exit",
                "authorized": True
            }
        ]
        
        # Write test logs to file
        with open(self.temp_log_file.name, 'w') as f:
            for log in self.test_logs:
                f.write(json.dumps(log) + '\n')
        
        # Create statistics manager
        self.stats_manager = StatisticsManager(log_file=self.temp_log_file.name)
    
    def tearDown(self):
        """
        Clean up the test environment.
        """
        # Remove temporary log file
        if os.path.exists(self.temp_log_file.name):
            os.unlink(self.temp_log_file.name)
    
    def test_daily_traffic(self):
        """
        Test daily traffic statistics.
        """
        # Get daily traffic statistics
        daily_traffic = self.stats_manager.get_daily_traffic()
        
        # Check if statistics are correct
        self.assertEqual(daily_traffic['entries'], 3)
        self.assertEqual(daily_traffic['exits'], 2)
        self.assertEqual(daily_traffic['total'], 5)
    
    def test_hourly_distribution(self):
        """
        Test hourly distribution statistics.
        """
        # Get hourly distribution statistics
        hourly_distribution = self.stats_manager.get_hourly_distribution()
        
        # Check if statistics are correct
        self.assertEqual(hourly_distribution[8]['entries'], 2)
        self.assertEqual(hourly_distribution[9]['entries'], 1)
        self.assertEqual(hourly_distribution[12]['exits'], 1)
        self.assertEqual(hourly_distribution[14]['exits'], 1)
    
    def test_vehicle_statistics(self):
        """
        Test vehicle statistics.
        """
        # Get vehicle statistics
        vehicle_stats = self.stats_manager.get_vehicle_statistics()
        
        # Check if statistics are correct
        self.assertEqual(vehicle_stats['authorized'], 4)
        self.assertEqual(vehicle_stats['unauthorized'], 1)
        self.assertEqual(vehicle_stats['total'], 5)
        self.assertEqual(vehicle_stats['unique_vehicles'], 3)
    
    def test_parking_duration(self):
        """
        Test parking duration statistics.
        """
        # Get parking duration statistics
        duration_stats = self.stats_manager.get_parking_duration_statistics()
        
        # Check if statistics are correct
        self.assertEqual(duration_stats['average_duration'], 3.75)  # 4 hours for ABC123, 5.5 hours for DEF456, average = 4.75
        self.assertEqual(duration_stats['max_duration'], 5.5)
        self.assertEqual(duration_stats['min_duration'], 4.0)
        self.assertEqual(duration_stats['total_vehicles_with_duration'], 2)
    
    def test_empty_statistics(self):
        """
        Test statistics with empty log file.
        """
        # Create a new empty log file
        empty_log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        empty_log_file.close()
        
        # Create statistics manager with empty log file
        empty_stats_manager = StatisticsManager(log_file=empty_log_file.name)
        
        try:
            # Get statistics
            daily_traffic = empty_stats_manager.get_daily_traffic()
            hourly_distribution = empty_stats_manager.get_hourly_distribution()
            vehicle_stats = empty_stats_manager.get_vehicle_statistics()
            duration_stats = empty_stats_manager.get_parking_duration_statistics()
            
            # Check if statistics are empty but structured
            self.assertEqual(daily_traffic['entries'], 0)
            self.assertEqual(daily_traffic['exits'], 0)
            self.assertEqual(daily_traffic['total'], 0)
            
            self.assertEqual(vehicle_stats['authorized'], 0)
            self.assertEqual(vehicle_stats['unauthorized'], 0)
            self.assertEqual(vehicle_stats['total'], 0)
            self.assertEqual(vehicle_stats['unique_vehicles'], 0)
            
            self.assertEqual(duration_stats['average_duration'], 0.0)
            self.assertEqual(duration_stats['max_duration'], 0.0)
            self.assertEqual(duration_stats['min_duration'], 0.0)
            self.assertEqual(duration_stats['total_vehicles_with_duration'], 0)
        finally:
            # Remove empty log file
            if os.path.exists(empty_log_file.name):
                os.unlink(empty_log_file.name)

if __name__ == '__main__':
    unittest.main()
