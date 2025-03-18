import unittest
import os
import sys
import json
import tempfile
import shutil
import subprocess
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import modules to test
from src.utils.backup import BackupManager

class TestBackupRestore(unittest.TestCase):
    """
    Test cases for backup and restore functionality.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test directories
        self.data_dir = os.path.join(self.temp_dir, 'data')
        self.config_dir = os.path.join(self.temp_dir, 'config')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Create test configuration
        self.config = {
            'backup': {
                'data_dir': self.data_dir,
                'config_dir': self.config_dir,
                'backup_dir': self.backup_dir,
                'compression': 'gzip',
                'retention_count': 5
            },
            'database': {
                'path': os.path.join(self.data_dir, 'test.db')
            },
            'logging': {
                'level': 'ERROR',
                'file_path': os.path.join(self.temp_dir, 'test.log'),
                'max_size': 1024,
                'backup_count': 1
            }
        }
        
        # Create test files
        self._create_test_files()
        
        # Create a backup manager instance for testing
        self.backup_manager = BackupManager(self.config)
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_test_files(self):
        """
        Create test files for backup and restore testing.
        """
        # Create a test database
        conn = sqlite3.connect(self.config['database']['path'])
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE vehicles (
            id INTEGER PRIMARY KEY,
            license_plate TEXT NOT NULL,
            authorized INTEGER NOT NULL,
            owner TEXT,
            notes TEXT
        )
        ''')
        
        # Insert test data
        cursor.execute('''
        INSERT INTO vehicles (license_plate, authorized, owner, notes)
        VALUES (?, ?, ?, ?)
        ''', ('ABC123', 1, 'Test Owner', 'Test Notes'))
        
        conn.commit()
        conn.close()
        
        # Create a test configuration file
        config_file = os.path.join(self.config_dir, 'config.json')
        with open(config_file, 'w') as f:
            json.dump({
                'server': {
                    'host': '127.0.0.1',
                    'port': 5000,
                    'debug': False
                },
                'database': {
                    'path': '/var/lib/amslpr/data/amslpr.db'
                }
            }, f, indent=2)
        
        # Create a test log file
        log_file = os.path.join(self.data_dir, 'test.log')
        with open(log_file, 'w') as f:
            f.write('Test log entry\n')
    
    def test_backup_manager_initialization(self):
        """
        Test that the backup manager initializes correctly.
        """
        self.assertIsNotNone(self.backup_manager)
        self.assertEqual(self.backup_manager.data_dir, self.config['backup']['data_dir'])
        self.assertEqual(self.backup_manager.config_dir, self.config['backup']['config_dir'])
        self.assertEqual(self.backup_manager.backup_dir, self.config['backup']['backup_dir'])
        self.assertEqual(self.backup_manager.compression, self.config['backup']['compression'])
        self.assertEqual(self.backup_manager.retention_count, self.config['backup']['retention_count'])
    
    def test_create_backup(self):
        """
        Test that creating a backup works correctly.
        """
        # Create a backup
        backup_file = self.backup_manager.create_backup()
        
        # Check that the backup file exists
        self.assertTrue(os.path.exists(backup_file))
        
        # Check that the backup file is not empty
        self.assertGreater(os.path.getsize(backup_file), 0)
    
    def test_list_backups(self):
        """
        Test that listing backups works correctly.
        """
        # Create multiple backups
        for _ in range(3):
            self.backup_manager.create_backup()
        
        # List backups
        backups = self.backup_manager.list_backups()
        
        # Check that we have the expected number of backups
        self.assertEqual(len(backups), 3)
        
        # Check that each backup has the expected attributes
        for backup in backups:
            self.assertIn('file_path', backup)
            self.assertIn('timestamp', backup)
            self.assertIn('size', backup)
    
    def test_restore_backup(self):
        """
        Test that restoring a backup works correctly.
        """
        # Create a backup
        backup_file = self.backup_manager.create_backup()
        
        # Modify the original files
        conn = sqlite3.connect(self.config['database']['path'])
        cursor = conn.cursor()
        cursor.execute('DELETE FROM vehicles')
        conn.commit()
        conn.close()
        
        # Verify that the data has been modified
        conn = sqlite3.connect(self.config['database']['path'])
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM vehicles')
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)
        
        # Restore the backup
        self.backup_manager.restore_backup(backup_file)
        
        # Verify that the data has been restored
        conn = sqlite3.connect(self.config['database']['path'])
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM vehicles')
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)
    
    def test_cleanup_old_backups(self):
        """
        Test that cleaning up old backups works correctly.
        """
        # Create more backups than the retention count
        for _ in range(self.config['backup']['retention_count'] + 3):
            self.backup_manager.create_backup()
        
        # List backups before cleanup
        backups_before = self.backup_manager.list_backups()
        
        # Clean up old backups
        self.backup_manager.cleanup_old_backups()
        
        # List backups after cleanup
        backups_after = self.backup_manager.list_backups()
        
        # Check that we have the expected number of backups
        self.assertEqual(len(backups_after), self.config['backup']['retention_count'])
        
        # Check that the oldest backups were removed
        self.assertLess(len(backups_after), len(backups_before))
    
    def test_backup_script(self):
        """
        Test that the backup script works correctly.
        """
        # Path to the backup script
        script_path = os.path.join(Path(__file__).parent.parent.parent, 'scripts', 'backup_restore.sh')
        
        # Check that the script exists
        self.assertTrue(os.path.exists(script_path))
        
        # Test running the script (backup command)
        result = subprocess.run(
            [script_path, '--data-dir', self.data_dir, '--config-dir', self.config_dir, '--backup-dir', self.backup_dir, 'backup'],
            capture_output=True,
            text=True
        )
        
        # Check that the script executed successfully
        self.assertEqual(result.returncode, 0)
        
        # Check that a backup file was created
        backup_files = os.listdir(self.backup_dir)
        self.assertGreater(len(backup_files), 0)

if __name__ == '__main__':
    unittest.main()
