
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
View statistics from the VisiGate system.

This script displays various statistics from the VisiGate system.
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager
from src.utils.statistics import StatisticsManager

def print_json(data):
    """
    Print data as formatted JSON.
    
    Args:
        data: Data to print
    """
    print(json.dumps(data, indent=2, default=str))

def view_statistics(db_path='data/visigate.db'):
    """
    View statistics from the VisiGate system.
    
    Args:
        db_path (str): Path to the database file
    """
    # Create database manager
    config = {
        'db_path': db_path,
        'backup_interval': 86400
    }
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    # Initialize statistics manager
    stats_manager = StatisticsManager(db_manager)
    
    # Get daily traffic
    print("\n=== Daily Traffic (Last 7 Days) ===")
    daily_traffic = stats_manager.get_daily_traffic(days=7)
    print_json(daily_traffic)
    
    # Get hourly distribution
    print("\n=== Hourly Distribution ===")
    hourly_distribution = stats_manager.get_hourly_distribution()
    print_json(hourly_distribution)
    
    # Get vehicle statistics
    print("\n=== Vehicle Statistics ===")
    vehicle_stats = stats_manager.get_vehicle_statistics()
    print_json(vehicle_stats)
    
    # Get parking duration statistics
    print("\n=== Parking Duration Statistics ===")
    duration_stats = stats_manager.get_parking_duration_statistics()
    print_json(duration_stats)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='View statistics from VisiGate')
    parser.add_argument('--db-path', type=str, default='data/visigate.db', help='Path to database file')
    
    args = parser.parse_args()
    
    view_statistics(db_path=args.db_path)
