# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

"""
Simple script to run the AMSLPR web server for testing purposes.
"""

import os
import sys
import logging
import json
import argparse
from src.web.app import create_app
from src.database.db_manager import DatabaseManager
from src.recognition.detector import LicensePlateDetector
from src.utils.config import load_config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

def main():
    try:
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
        
        # Initialize detector if enabled
        detector = None
        if config.get("recognition", {}).get("enabled", False):
            detector = LicensePlateDetector(config)
        
        # Create Flask app
        app = create_app(config)
        
        # Run the app
        port = config.get("port", 5000)
        host = config.get("host", "0.0.0.0")  # Listen on all interfaces
        logger.info(f"Starting server on {host}:{port}")
        
        app.run(
            host=host,
            port=port,
            debug=True,
            use_reloader=False  # Disable reloader to prevent duplicate processes
        )
        
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
