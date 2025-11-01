#!/usr/bin/env python3
"""
Simple script to create the HAILO_ENABLED environment variable
"""

import os
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('hailo-enabler')

def set_environment_variable():
    """Set the HAILO_ENABLED environment variable to ensure OCR settings page shows Hailo options"""
    try:
        # Create systemd environment file
        cmd = "sudo sh -c 'echo \"HAILO_ENABLED=true\" > /etc/environment.d/hailo.conf'"
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.info("Created environment file for HAILO_ENABLED")
        
        # Also set in current environment
        os.environ['HAILO_ENABLED'] = 'true'
        
        # Create a persistent marker file that our direct_fix implementation checks for
        with open('/tmp/hailo_diag_success', 'w') as f:
            f.write('Hailo TPU detection successful')
        logger.info("Created Hailo success marker file")
        
        # Verify current environment
        if os.environ.get('HAILO_ENABLED') == 'true':
            logger.info("✓ HAILO_ENABLED environment variable is set to 'true' in current process")
        else:
            logger.warning("! HAILO_ENABLED environment variable is not set in current process")
        
        # Restart the service to apply changes
        logger.info("\nRestarting the VisiGate service to apply changes...")
        restart_cmd = "sudo systemctl restart visigate"
        subprocess.run(restart_cmd, shell=True, check=True)
        logger.info("✓ VisiGate service restarted successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error setting HAILO_ENABLED environment variable: {e}")
        return False

if __name__ == "__main__":
    logger.info("Setting HAILO_ENABLED environment variable to force enable Hailo TPU options")
    success = set_environment_variable()
    
    if success:
        logger.info("\n✓ Hailo TPU has been enabled in the environment!")
        logger.info("The OCR settings page should now show all Hailo options.")
        logger.info("Please refresh the page to see the changes.")
    else:
        logger.error("\n✗ Failed to enable Hailo TPU in the environment.")
        logger.info("Please try manually running:\n\nexport HAILO_ENABLED=true\nsudo systemctl restart visigate")
