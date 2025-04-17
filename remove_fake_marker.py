#!/usr/bin/env python3

"""Remove the fake marker file that was inappropriately created"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('remove-fake-marker')

# Remove the marker file if it exists
if os.path.exists('/tmp/hailo_diag_success'):
    try:
        os.remove('/tmp/hailo_diag_success')
        logger.info("Removed inappropriate marker file")
    except Exception as e:
        logger.error(f"Error removing marker file: {e}")
else:
    logger.info("Marker file not found")

logger.info("Please restart the service to restore proper error reporting:")  
logger.info("sudo systemctl restart amslpr")
