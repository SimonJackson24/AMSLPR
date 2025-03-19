#!/usr/bin/env python3

"""
Simple script to run the AMSLPR web server for testing purposes.
"""

import os
import sys
import json
import argparse
from src.web.app import create_app
from src.database.db_manager import DatabaseManager
from src.utils.config import load_config
from src.recognition.detector import LicensePlateDetector

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the AMSLPR web server')
    parser.add_argument('--port', type=int, help='Port to run the server on')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Override port if specified in command line
    if args.port:
        config["port"] = args.port
    
    # Create instance directory if it doesn't exist
    os.makedirs("instance", exist_ok=True)
    
    # Create uploads directory if it doesn't exist
    os.makedirs(config["web"]["upload_folder"], exist_ok=True)
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    # Initialize license plate detector
    detector = LicensePlateDetector(config["recognition"])
    
    # Create and run app
    app = create_app(config, db_manager, detector)
    
    # Add Jinja2 filter for formatDateTime
    @app.template_filter('formatDateTime')
    def format_datetime(value):
        if not value:
            return '-'
        from datetime import datetime
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    app.run(
        host=config["host"],
        port=config["port"],
        debug=config["debug"]
    )

if __name__ == "__main__":
    main()
