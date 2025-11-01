#!/usr/bin/env python3
"""
This script checks if the Hailo TPU is properly detected by the application code.
It uses the same detection logic as the OCR settings page without modifying anything.
"""

import os
import sys
import logging
import importlib.util
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('hailo-app-detection')

def check_application_detection():
    """Run the exact same detection code used in the application"""
    logger.info("\n===== Checking how application detects Hailo TPU =====")
    
    # Initialize the detection variable
    hailo_available = False
    ocr_bp_settings = "/ocr/settings"
    
    # First check for environment variable (which we should NOT set as a workaround)
    if os.environ.get('HAILO_ENABLED') == 'true':
        logger.info("HAILO_ENABLED environment variable is set. This would enable Hailo in the app.")
        logger.info("Note: We should not use this as a workaround for actual detection issues.")
        hailo_available = True
    else:
        logger.info("HAILO_ENABLED environment variable is not set (good).")
    
    # This is the actual detection code from direct_fix.py
    try:
        # First check for hailort module
        if importlib.util.find_spec("hailort"):
            logger.info("u2713 hailort Python module is found")
            # Check if device file exists
            if os.path.exists('/dev/hailo0'):
                logger.info("u2713 Device file /dev/hailo0 exists")
                try:
                    # Try to import and initialize the device
                    logger.info("Trying to import and initialize the Hailo device...")
                    import hailort
                    device = hailort.Device()
                    device_id = device.device_id
                    logger.info(f"u2713 Successfully initialized Hailo device: {device_id}")
                    hailo_available = True
                except Exception as e:
                    logger.error(f"u2717 Hailo TPU module found but device initialization failed: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.error("u2717 Hailo device file (/dev/hailo0) not found")
        else:
            logger.error("u2717 hailort Python module not found")
    except Exception as e:
        logger.error(f"u2717 Error checking for Hailo TPU: {e}")
        logger.error(traceback.format_exc())
    
    # Check marker file (we should remove this, not create it as a workaround)
    if os.path.exists('/tmp/hailo_diag_success'):
        logger.warning("Warning: Marker file exists. This should be removed, not used as a workaround.")
        logger.info("Run the remove_fake_marker.py script to remove this.")
    
    # Final outcome
    logger.info("\n===== Application Detection Result =====")
    logger.info(f"Would the OCR settings page show Hailo as available? {'Yes' if hailo_available else 'No'}")
    
    # If it's not being detected correctly despite system confirmation
    if not hailo_available:
        logger.info("\n===== Troubleshooting Steps =====")
        logger.info("1. Check permissions of /dev/hailo0")
        logger.info("   - Run: sudo chmod 666 /dev/hailo0")
        logger.info("2. Make sure the web application has permission to access the device")
        logger.info("3. Check that the user running the web application is in the correct group")
        logger.info("   - Run: sudo usermod -a -G video www-data")
        logger.info("4. Review any specific error messages above")
        logger.info("\nNote: Focus on fixing the actual detection issue rather than using workarounds")
    
    return hailo_available

def check_permissions():
    """Check permissions of the Hailo device file"""
    if not os.path.exists('/dev/hailo0'):
        logger.error("Cannot check permissions: /dev/hailo0 does not exist")
        return False
    
    try:
        import stat
        st = os.stat('/dev/hailo0')
        perms = st.st_mode & 0o777
        owner, group = st.st_uid, st.st_gid
        
        # Convert to human-readable
        import pwd, grp
        owner_name = pwd.getpwuid(owner).pw_name
        group_name = grp.getgrgid(group).gr_name
        
        # Format permissions
        perm_str = ""
        for who in ['USR', 'GRP', 'OTH']:
            perm_str += "".join([('r' if perms & getattr(stat, 'S_IR' + who) else '-'),
                               ('w' if perms & getattr(stat, 'S_IW' + who) else '-'),
                               ('x' if perms & getattr(stat, 'S_IX' + who) else '-')])
        
        logger.info(f"Device file permissions: {oct(perms)[2:]} ({perm_str})")
        logger.info(f"Owner: {owner_name}, Group: {group_name}")
        
        # Check if world-readable
        if not (perms & stat.S_IROTH):
            logger.warning("Device file is not world-readable. This might cause detection issues.")
            logger.info("Run: sudo chmod 666 /dev/hailo0")
        else:
            logger.info("u2713 Device file is readable by all users")
        
        # Check application user/group
        try:
            import subprocess
            result = subprocess.run("ps -ef | grep python | grep visigate", shell=True, capture_output=True, text=True)
            logger.info(f"\nApplication process info:\n{result.stdout}")
        except Exception as e:
            logger.error(f"Error checking application process: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return False

def main():
    """Main function"""
    logger.info("===== Checking Hailo TPU Detection by Application =====")
    
    # Check application detection logic
    app_detects = check_application_detection()
    
    # Check permissions if there are issues
    if not app_detects:
        logger.info("\n===== Checking Device File Permissions =====")
        check_permissions()
    
    logger.info("\n===== Final Analysis =====")    
    if app_detects:
        logger.info("u2713 The application should detect the Hailo TPU correctly")
        logger.info("If it's still not showing up in the OCR settings page, check the application logs for errors")
    else:
        logger.info("u2717 The application is not detecting the Hailo TPU")
        logger.info("Please address the specific issues mentioned above rather than using workarounds")
    
    logger.info("\nTo check application logs for Hailo-related messages:")
    logger.info("journalctl -u visigate | grep -i hailo")

if __name__ == "__main__":
    main()
