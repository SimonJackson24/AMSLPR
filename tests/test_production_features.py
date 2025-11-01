
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import modules to test
from src.utils.error_handling import ErrorHandler
from src.utils.system_monitor import SystemMonitor
from src.config.settings import load_config

class TestProductionFeatures(unittest.TestCase):
    """
    Test cases for production-ready features.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test directories
        self.log_dir = os.path.join(self.temp_dir, 'logs')
        self.data_dir = os.path.join(self.temp_dir, 'data')
        
        # Create required directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load test configuration
        test_config_path = os.path.join(Path(__file__).parent, 'test_config.json')
        if os.path.exists(test_config_path):
            self.config = load_config(test_config_path)
        else:
            self.config = {}
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_error_handler_initialization(self):
        """
        Test that the error handler initializes correctly.
        """
        error_handler = ErrorHandler(log_dir=self.log_dir)
        self.assertIsNotNone(error_handler)
        self.assertEqual(error_handler.log_dir, self.log_dir)
        
        # Check that the error log directory was created
        error_log_dir = os.path.join(self.log_dir, 'errors')
        self.assertTrue(os.path.exists(error_log_dir))
    
    def test_error_handler_log_error(self):
        """
        Test that the error handler logs errors correctly.
        """
        error_handler = ErrorHandler(log_dir=self.log_dir)
        test_error = Exception("Test error")
        
        # Log the error
        error_handler.log_error(test_error, "test_module", "test_function")
        
        # Check that error log file was created
        error_log_dir = os.path.join(self.log_dir, 'errors')
        log_files = os.listdir(error_log_dir)
        self.assertTrue(len(log_files) > 0)
        
        # Check log file content
        log_file_path = os.path.join(error_log_dir, log_files[0])
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        
        self.assertIn("Test error", log_content)
        self.assertIn("test_module", log_content)
        self.assertIn("test_function", log_content)
    
    def test_system_monitor_initialization(self):
        """
        Test that the system monitor initializes correctly.
        """
        system_monitor = SystemMonitor(data_dir=self.data_dir, check_interval=30)
        self.assertIsNotNone(system_monitor)
        self.assertEqual(system_monitor.data_dir, self.data_dir)
        self.assertEqual(system_monitor.check_interval, 30)
        
        # Check that the metrics directory was created
        metrics_dir = os.path.join(self.data_dir, 'metrics')
        self.assertTrue(os.path.exists(metrics_dir))
    
    def test_system_monitor_get_system_stats(self):
        """
        Test that the system monitor can get system statistics.
        """
        system_monitor = SystemMonitor(data_dir=self.data_dir)
        stats = system_monitor.get_system_stats()
        
        # Check that stats contains expected keys
        self.assertIn('cpu_percent', stats)
        self.assertIn('memory_percent', stats)
        self.assertIn('disk_percent', stats)
        self.assertIn('uptime', stats)
        
        # Check that values are reasonable
        self.assertGreaterEqual(stats['cpu_percent'], 0)
        self.assertLessEqual(stats['cpu_percent'], 100)
        self.assertGreaterEqual(stats['memory_percent'], 0)
        self.assertLessEqual(stats['memory_percent'], 100)
        self.assertGreaterEqual(stats['disk_percent'], 0)
        self.assertLessEqual(stats['disk_percent'], 100)
        self.assertGreater(stats['uptime'], 0)
    
    def test_system_monitor_log_metrics(self):
        """
        Test that the system monitor logs metrics correctly.
        """
        system_monitor = SystemMonitor(data_dir=self.data_dir)
        system_monitor.log_metrics()
        
        # Check that metrics file was created
        metrics_dir = os.path.join(self.data_dir, 'metrics')
        metrics_files = os.listdir(metrics_dir)
        self.assertTrue(len(metrics_files) > 0)
        
        # Check metrics file content
        metrics_file_path = os.path.join(metrics_dir, metrics_files[0])
        with open(metrics_file_path, 'r') as f:
            metrics_content = json.load(f)
        
        self.assertIn('timestamp', metrics_content)
        self.assertIn('cpu_percent', metrics_content)
        self.assertIn('memory_percent', metrics_content)
        self.assertIn('disk_percent', metrics_content)

if __name__ == '__main__':
    unittest.main()
