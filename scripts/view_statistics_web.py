#!/usr/bin/env python3
"""
Simplified web application to view statistics.

This script runs a simplified version of the web application that only shows the statistics page.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager
from src.utils.statistics import StatisticsManager

# Create Flask app
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
           static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src/web/static'))

# Create database manager
config = {
    'db_path': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/amslpr.db'),
    'backup_interval': 86400
}

# Initialize database manager
db_manager = DatabaseManager(config)

# Initialize statistics manager
stats_manager = StatisticsManager(db_manager)

@app.route('/')
def index():
    # Get statistics from the statistics manager
    daily_traffic = stats_manager.get_daily_traffic(days=7)
    hourly_distribution = stats_manager.get_hourly_distribution(days=30)
    vehicle_stats = stats_manager.get_vehicle_statistics()
    parking_stats = stats_manager.get_parking_duration_statistics()
    
    return render_template(
        'statistics.html',
        daily_traffic=daily_traffic,
        hourly_distribution=hourly_distribution,
        vehicle_stats=vehicle_stats,
        parking_stats=parking_stats
    )

@app.route('/api/statistics')
def api_statistics():
    # Get statistics from the statistics manager
    daily_traffic = stats_manager.get_daily_traffic(days=7)
    hourly_distribution = stats_manager.get_hourly_distribution(days=30)
    vehicle_stats = stats_manager.get_vehicle_statistics()
    parking_stats = stats_manager.get_parking_duration_statistics()
    
    return jsonify({
        'daily_traffic': daily_traffic,
        'hourly_distribution': hourly_distribution,
        'vehicle_stats': vehicle_stats,
        'parking_stats': parking_stats
    })

if __name__ == '__main__':
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(config['db_path']), exist_ok=True)
    
    print(f"Starting web server at http://localhost:5000")
    print(f"Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=5000, debug=True)
