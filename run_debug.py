#!/usr/bin/env python3

"""
Debug runner for VisiGate application.
This script runs the application with the Flask development server for debugging purposes.
"""

import os
import sys
import logging
from src.utils.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VisiGate.debug')

# Add src directory to path if needed
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

def main():
    """Run the application with the Flask development server."""
    try:
        # Import the app from src.web.app
        from src.web.app import create_app
        
        # Load configuration
        config = load_config()
        
        # Create the app
        app = create_app(config)
        
        # Enable debug mode
        app.config['DEBUG'] = True
        
        # Run the application
        logger.info("Starting VisiGate in debug mode")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Error starting debug server: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
