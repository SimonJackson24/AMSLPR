
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Generate sample data for testing the VisiGate system.

This script creates sample vehicles and access logs for testing and demonstration purposes.
"""

import os
import sys
import random
from datetime import datetime, timedelta
import sqlite3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager

# Sample data
SAMPLE_VEHICLES = [
    {'plate': 'ABC123', 'desc': 'John Doe - Toyota Camry', 'auth': True},
    {'plate': 'XYZ789', 'desc': 'Jane Smith - Honda Civic', 'auth': True},
    {'plate': 'DEF456', 'desc': 'Bob Johnson - Ford F-150', 'auth': True},
    {'plate': 'GHI789', 'desc': 'Alice Brown - Tesla Model 3', 'auth': True},
    {'plate': 'JKL012', 'desc': 'Charlie Davis - Nissan Altima', 'auth': True},
    {'plate': 'MNO345', 'desc': 'Eva Wilson - Chevrolet Malibu', 'auth': False},
    {'plate': 'PQR678', 'desc': 'Frank Miller - BMW X5', 'auth': False},
    {'plate': 'STU901', 'desc': 'Grace Taylor - Audi A4', 'auth': False},
    {'plate': 'VWX234', 'desc': 'Henry Clark - Hyundai Sonata', 'auth': True},
    {'plate': 'YZA567', 'desc': 'Ivy Martin - Kia Optima', 'auth': True},
]

def generate_sample_data(db_path='data/visigate.db', days=30, entries_per_day_min=10, entries_per_day_max=30):
    """
    Generate sample data for testing.
    
    Args:
        db_path (str): Path to the database file
        days (int): Number of days of data to generate
        entries_per_day_min (int): Minimum number of entries per day
        entries_per_day_max (int): Maximum number of entries per day
    """
    # Create database manager
    config = {
        'db_path': db_path,
        'backup_interval': 86400
    }
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    # Add sample vehicles
    for vehicle in SAMPLE_VEHICLES:
        # Check if vehicle already exists
        existing = db_manager.get_vehicle(vehicle['plate'])
        if not existing:
            db_manager.add_vehicle(
                plate_number=vehicle['plate'],
                description=vehicle['desc'],
                authorized=vehicle['auth']
            )
            print(f"Added vehicle: {vehicle['plate']}")
        else:
            print(f"Vehicle already exists: {vehicle['plate']}")
    
    # Generate access logs
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Direct database connection for bulk inserts
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    current_date = start_date
    while current_date <= end_date:
        # Random number of entries for this day
        num_entries = random.randint(entries_per_day_min, entries_per_day_max)
        
        for _ in range(num_entries):
            # Random vehicle
            vehicle = random.choice(SAMPLE_VEHICLES)
            
            # Random hour (weighted towards business hours)
            hour_weights = [1] * 6 + [3] * 3 + [5] * 8 + [3] * 4 + [1] * 3  # 0-5, 6-8, 9-16, 17-20, 21-23
            hour = random.choices(range(24), weights=hour_weights)[0]
            
            # Random minute
            minute = random.randint(0, 59)
            
            # Entry time
            entry_time = current_date.replace(hour=hour, minute=minute)
            
            # Exit time (1-8 hours later, with some probability of overnight)
            if random.random() < 0.8:  # 80% chance of same-day exit
                duration_hours = random.uniform(0.25, 8)  # 15 minutes to 8 hours
                exit_time = entry_time + timedelta(hours=duration_hours)
            else:  # 20% chance of overnight or longer stay
                duration_hours = random.uniform(8, 72)  # 8 hours to 3 days
                exit_time = entry_time + timedelta(hours=duration_hours)
            
            # Ensure exit time is not in the future
            if exit_time > end_date:
                exit_time = end_date
            
            # Log entry
            entry_time_str = entry_time.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                '''
                INSERT INTO access_logs (plate_number, direction, authorized, access_time)
                VALUES (?, ?, ?, ?)
                ''',
                (vehicle['plate'], 'entry', vehicle['auth'], entry_time_str)
            )
            
            # Log exit
            exit_time_str = exit_time.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                '''
                INSERT INTO access_logs (plate_number, direction, authorized, access_time)
                VALUES (?, ?, ?, ?)
                ''',
                (vehicle['plate'], 'exit', vehicle['auth'], exit_time_str)
            )
        
        # Commit after each day
        conn.commit()
        print(f"Generated {num_entries} entries for {current_date.date()}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    # Close connection
    conn.close()
    
    print(f"Sample data generation complete. Generated data for {days} days.")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sample data for VisiGate')
    parser.add_argument('--db-path', type=str, default='data/visigate.db', help='Path to database file')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data to generate')
    parser.add_argument('--min-entries', type=int, default=10, help='Minimum entries per day')
    parser.add_argument('--max-entries', type=int, default=30, help='Maximum entries per day')
    
    args = parser.parse_args()
    
    generate_sample_data(
        db_path=args.db_path,
        days=args.days,
        entries_per_day_min=args.min_entries,
        entries_per_day_max=args.max_entries
    )
