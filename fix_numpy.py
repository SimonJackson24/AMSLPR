#!/usr/bin/env python3
"""
Fix for the NumPy module error that's preventing the AMSLPR service from starting
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('numpy-fix')

def fix_numpy_issue():
    """Fix the NumPy issue by reinstalling or patching"""
    logger.info("Attempting to fix NumPy issue...")
    
    # First approach: Reinstall NumPy
    try:
        logger.info("Reinstalling NumPy...")
        subprocess.run(
            ["pip", "uninstall", "-y", "numpy"], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        logger.info("NumPy uninstalled successfully")
        
        subprocess.run(
            ["pip", "install", "numpy==1.24.3"], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        logger.info("NumPy reinstalled successfully")
        return True
    except Exception as e:
        logger.error(f"Error reinstalling NumPy: {e}")
        logger.info("Trying alternative approach...")
    
    # Second approach: Create a patch for the multiarray.py file
    try:
        # Find the multiarray.py file
        result = subprocess.run(
            ["find", "/opt/amslpr/venv", "-name", "multiarray.py"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        multiarray_path = result.stdout.strip()
        
        if not multiarray_path:
            logger.error("Could not find multiarray.py")
            return False
        
        logger.info(f"Found multiarray.py at: {multiarray_path}")
        
        # Read the file
        with open(multiarray_path, 'r') as f:
            content = f.read()
        
        # Create a backup
        with open(multiarray_path + '.bak', 'w') as f:
            f.write(content)
        logger.info("Created backup of multiarray.py")
        
        # Patch the file to fix the __module__ issue
        # We're looking for the _override___module__ function and modifying it to check if __module__ exists
        if 'def _override___module__():' in content:
            # Find the function
            start_idx = content.find('def _override___module__():')
            # Find the end of the function (next def or end of file)
            next_def = content.find('def ', start_idx + 1)
            if next_def == -1:
                next_def = len(content)
            
            # Extract the function
            func_content = content[start_idx:next_def]
            
            # Create patched version that checks if __module__ exists
            patched_func = """
def _override___module__():
    """Override __module__ for ufuncs and umath module."""
    from types import ModuleType
    import warnings
    
    # Patch to handle missing __module__ attribute
    def safe_set_module(obj, module_name):
        try:
            if hasattr(obj, '__module__'):
                obj.__module__ = module_name
        except (AttributeError, TypeError) as e:
            # Silently ignore if __module__ can't be set
            pass
    
    m = sys.modules['numpy.core.multiarray']
    for obj in m.__dict__.values():
        if isinstance(obj, type(m.add_docstring)):
            safe_set_module(obj, 'numpy')
    
    import numpy
    m = sys.modules['numpy.core.umath']
    for obj in m.__dict__.values():
        if isinstance(obj, type(numpy.sin)):
            safe_set_module(obj, 'numpy')
"""
            
            # Replace the function in the content
            new_content = content.replace(func_content, patched_func)
            
            # Write the patched file
            with open(multiarray_path, 'w') as f:
                f.write(new_content)
            
            logger.info("Patched multiarray.py with fix for __module__ issue")
            return True
        else:
            logger.error("Could not find _override___module__ function in multiarray.py")
            return False
            
    except Exception as e:
        logger.error(f"Error patching multiarray.py: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    logger.info("===== Fixing NumPy __module__ error =====")
    
    if fix_numpy_issue():
        logger.info("\n✓ NumPy issue fixed successfully!")
        logger.info("Restarting AMSLPR service...")
        try:
            subprocess.run(
                ["sudo", "systemctl", "restart", "amslpr"],
                check=True
            )
            logger.info("\n✓ AMSLPR service restarted successfully")
            logger.info("Wait a few moments, then check the service status:")
            logger.info("sudo systemctl status amslpr")
        except Exception as e:
            logger.error(f"Error restarting service: {e}")
    else:
        logger.error("\n✗ Failed to fix NumPy issue")
        logger.info("Try manually reinstalling NumPy in the virtual environment:")
        logger.info("sudo -u www-data /opt/amslpr/venv/bin/pip uninstall -y numpy")
        logger.info("sudo -u www-data /opt/amslpr/venv/bin/pip install numpy==1.24.3")

if __name__ == "__main__":
    main()
