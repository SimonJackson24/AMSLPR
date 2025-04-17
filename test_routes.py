#!/usr/bin/env python3

"""
Test script to diagnose route registration issues.
This script will:
1. Initialize the Flask app exactly as in production
2. Register a guaranteed working route for /ocr/settings
3. Print all registered routes
4. Start a test server on port 5000
"""

import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('route-test')

# Add parent directory to path
parent_dir = str(Path(__file__).absolute().parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    # Import app creator
    from src.web.app import create_app
    
    # Create the app with standard configuration
    app = create_app()
    
    # List all registered routes before our addition
    logger.info("Current registered routes:")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule.rule}")
    for route in sorted(routes):
        logger.info(route)
    
    # Add our guaranteed OCR settings route directly
    @app.route('/ocr/settings', methods=['GET'])
    def guaranteed_ocr_settings():
        from flask import jsonify
        logger.info("Direct OCR settings route accessed!")
        return jsonify({
            "success": True,
            "message": "OCR settings route working correctly"
        })
    
    # Add another test route to confirm if ANY new routes can be added
    @app.route('/test/route', methods=['GET'])
    def test_route():
        from flask import jsonify
        logger.info("Test route accessed!")
        return jsonify({
            "success": True,
            "message": "Test route working correctly"
        })
    
    # List all routes after our addition
    logger.info("\nUpdated routes after adding our test routes:")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule.rule}")
    for route in sorted(routes):
        logger.info(route)
    
    # Check if our route was registered
    if any(r for r in routes if 'guaranteed_ocr_settings' in r):
        logger.info("\nOur guaranteed OCR settings route was successfully registered!")
    else:
        logger.error("\nOur guaranteed OCR settings route was NOT registered successfully!")
    
    logger.info("\nNow testing if the application can run...")
    logger.info("You can test the following routes:")
    logger.info("- http://192.168.1.183:5000/test/route")
    logger.info("- http://192.168.1.183:5000/ocr/settings")
    
    # Start a test server
    if __name__ == '__main__':
        logger.info("Starting test server on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    
except Exception as e:
    logger.error(f"Error in test script: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
