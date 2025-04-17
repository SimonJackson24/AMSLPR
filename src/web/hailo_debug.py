#!/usr/bin/env python3
"""
This script adds debug logging to the OCR settings page to see why Hailo detection isn't working
"""

import os
import sys
import logging
import importlib.util

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('hailo-debug')

def add_debug_logging():
    """Add debug logging to the direct_fix.py file"""
    try:
        direct_fix_path = os.path.join(os.getcwd(), 'src', 'web', 'direct_fix.py')
        ocr_routes_path = os.path.join(os.getcwd(), 'src', 'web', 'ocr_routes.py')
        
        logger.info(f"Checking for direct_fix.py at: {direct_fix_path}")
        if not os.path.exists(direct_fix_path):
            logger.error(f"direct_fix.py not found at {direct_fix_path}")
            return False
        
        # First, backup the files
        with open(direct_fix_path, 'r') as f:
            direct_fix_content = f.read()
        with open(direct_fix_path + '.bak', 'w') as f:
            f.write(direct_fix_content)
            
        with open(ocr_routes_path, 'r') as f:
            ocr_routes_content = f.read()
        with open(ocr_routes_path + '.bak', 'w') as f:
            f.write(ocr_routes_content)
            
        logger.info("Backup files created successfully")
        
        # Add debug logging to direct_fix.py
        # Look for the line that sets hailo_available
        if 'hailo_available = False' in direct_fix_content:
            direct_fix_content = direct_fix_content.replace(
                'hailo_available = False',
                'hailo_available = False\n    logger.info("[HAILO DEBUG] Starting Hailo detection in direct_fix.py")'
            )
            
            # Add logging to the hailort check
            direct_fix_content = direct_fix_content.replace(
                'if importlib.util.find_spec("hailort"):',
                'logger.info("[HAILO DEBUG] Checking for hailort module")\n        if importlib.util.find_spec("hailort"):\n            logger.info("[HAILO DEBUG] hailort module found")'
            )
            
            # Add logging to the device file check
            direct_fix_content = direct_fix_content.replace(
                'if os.path.exists("/dev/hailo0"):',
                'logger.info(f"[HAILO DEBUG] Checking for /dev/hailo0 file")\n                if os.path.exists("/dev/hailo0"):\n                    logger.info("[HAILO DEBUG] /dev/hailo0 file exists")'
            )
            
            # Add logging to device initialization
            direct_fix_content = direct_fix_content.replace(
                'import hailort',
                'logger.info("[HAILO DEBUG] Importing hailort module")\n                    import hailort'
            )
            
            direct_fix_content = direct_fix_content.replace(
                'device = hailort.Device()',
                'logger.info("[HAILO DEBUG] Creating hailort.Device instance")\n                    device = hailort.Device()'
            )
            
            # Add final result logging
            direct_fix_content = direct_fix_content.replace(
                'return render_template("ocr_settings.html", hailo_available=hailo_available)',
                'logger.info(f"[HAILO DEBUG] Final hailo_available value: {hailo_available}")\n    return render_template("ocr_settings.html", hailo_available=hailo_available)'
            )
            
            # Write back modified file
            with open(direct_fix_path, 'w') as f:
                f.write(direct_fix_content)
            logger.info("Added debug logging to direct_fix.py")
            
        else:
            logger.error("Could not find 'hailo_available = False' in direct_fix.py")
        
        # Add similar logging to ocr_routes.py
        if 'def check_hailo_availability():' in ocr_routes_content:
            ocr_routes_content = ocr_routes_content.replace(
                'def check_hailo_availability():',
                'def check_hailo_availability():\n    logger.info("[HAILO DEBUG] Checking Hailo availability in ocr_routes.py")'
            )
            
            # Add final result logging
            ocr_routes_content = ocr_routes_content.replace(
                'return hailo_available',
                'logger.info(f"[HAILO DEBUG] OCR routes hailo_available result: {hailo_available}")\n    return hailo_available'
            )
            
            # Write back modified file
            with open(ocr_routes_path, 'w') as f:
                f.write(ocr_routes_content)
            logger.info("Added debug logging to ocr_routes.py")
        else:
            logger.error("Could not find 'def check_hailo_availability():' in ocr_routes.py")
        
        logger.info("Debug logging added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding debug logging: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_direct_fix_hailo_detection():
    """Directly check the hailo detection in the direct_fix.py file"""
    try:
        # Add current directory to path
        sys.path.append(os.getcwd())
        
        # Import the function from direct_fix.py
        from src.web.direct_fix import direct_settings
        
        # Create a mock context
        class MockApp:
            def __init__(self):
                self.config = {}
        
        # Create test context
        app = MockApp()
        
        # Call the function with mock values
        logger.info("Calling direct_settings function directly...")
        # This won't actually work because it would try to render a template,
        # but it should at least run the Hailo detection code
        try:
            direct_settings()
        except Exception as e:
            # Expected to fail but we just want to see the logs
            logger.info(f"Expected error when calling direct_settings: {e}")
        
        logger.info("Hailo detection function called directly - check logs above")
        return True
    except Exception as e:
        logger.error(f"Error running direct check: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def restore_backups():
    """Restore original files from backups"""
    try:
        direct_fix_path = os.path.join(os.getcwd(), 'src', 'web', 'direct_fix.py')
        ocr_routes_path = os.path.join(os.getcwd(), 'src', 'web', 'ocr_routes.py')
        
        # Restore direct_fix.py
        if os.path.exists(direct_fix_path + '.bak'):
            with open(direct_fix_path + '.bak', 'r') as f:
                original_content = f.read()
            with open(direct_fix_path, 'w') as f:
                f.write(original_content)
            logger.info("Restored direct_fix.py from backup")
        
        # Restore ocr_routes.py
        if os.path.exists(ocr_routes_path + '.bak'):
            with open(ocr_routes_path + '.bak', 'r') as f:
                original_content = f.read()
            with open(ocr_routes_path, 'w') as f:
                f.write(original_content)
            logger.info("Restored ocr_routes.py from backup")
        
        logger.info("Backup restoration complete")
        return True
    except Exception as e:
        logger.error(f"Error restoring backups: {e}")
        return False

def main():
    """Main function"""
    logger.info("\n===== Adding Debug Logging to Hailo TPU Detection Code =====")
    
    # Add debug logging
    if add_debug_logging():
        logger.info("\n===== Debug Logging Added Successfully =====")
        logger.info("Please restart the application to apply the changes:")
        logger.info("sudo systemctl restart amslpr")
        logger.info("\nThen check the application logs to see detailed information:")
        logger.info("journalctl -u amslpr | grep -i \"\[HAILO DEBUG\]\"")
    else:
        logger.error("\n===== Failed to Add Debug Logging =====")
    
    logger.info("\nNote: This script has created backup files (.bak extension) of the modified files.")
    logger.info("To restore the original files, run this script with the --restore flag")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        restore_backups()
    else:
        main()
