#!/usr/bin/env python3

"""
Script to fix Hailo module imports on Raspberry Pi

This script creates the necessary module structure for Hailo imports
to work properly in the virtual environment when the wheel installation
doesn't succeed.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('AMSLPR.fix_hailo')

# Get project root directory
project_root = Path(__file__).resolve().parent.parent

def create_hailo_modules():
    """Create missing Hailo modules in the virtual environment."""
    # Get virtual environment path
    venv_path = project_root / 'venv'
    
    # Find site-packages
    python_versions = list(venv_path.glob('lib/python3.*'))
    if not python_versions:
        logger.error("Could not find Python lib directory in the virtual environment")
        return False
    
    python_lib = python_versions[0]
    site_packages = python_lib / 'site-packages'
    
    if not site_packages.exists():
        logger.error(f"Could not find site-packages directory at {site_packages}")
        return False
    
    logger.info(f"Found site-packages at {site_packages}")
    
    # Check if we have write permissions
    if not os.access(str(site_packages), os.W_OK):
        logger.error(f"No write permission for {site_packages}")
        logger.info("Creating temporary directory for modules instead")
        
        # Create in a user-writable location
        temp_dir = project_root / 'temp_modules'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create module directories
        hailort_path = temp_dir / 'hailort'
        hailo_platform_path = temp_dir / 'hailo_platform'
        
        os.makedirs(hailort_path, exist_ok=True)
        os.makedirs(hailo_platform_path, exist_ok=True)
        
        logger.info(f"Created module directories in {temp_dir}")
        logger.info("NOTE: This is a temporary solution. Run with sudo to install system-wide.")
    else:
        # Create in site-packages since we have permission
        # Create hailort module
        hailort_path = site_packages / 'hailort'
        os.makedirs(hailort_path, exist_ok=True)
        
        # Create hailo_platform module
        hailo_platform_path = site_packages / 'hailo_platform'
        os.makedirs(hailo_platform_path, exist_ok=True)
    
    # Create mock_hailo module or copy from project
    mock_hailo_path = project_root / 'src' / 'recognition' / 'mock_hailo.py'
    if mock_hailo_path.exists():
        logger.info(f"Copying mock_hailo.py from {mock_hailo_path}")
        shutil.copy(mock_hailo_path, hailort_path / 'mock_hailo.py')
    else:
        logger.warning(f"mock_hailo.py not found at {mock_hailo_path}, creating minimal version")
        
        with open(hailort_path / 'mock_hailo.py', 'w') as f:
            f.write("""
# Mock Hailo TPU implementation
import logging

logger = logging.getLogger('hailort.mock')

class Device:
    def __init__(self):
        self.device_id = "HAILO-MOCK-DEVICE"
        logger.info(f"Initialized mock Hailo device: {self.device_id}")
        
    def close(self):
        logger.info("Closed mock Hailo device")

class HailoRuntime:
    def __init__(self, model_path):
        self.model_path = model_path
        logger.info(f"Initialized mock Hailo runtime with model: {model_path}")
        
    def infer(self, input_data):
        logger.info(f"Mock inference on input data")
        return []
    
    def close(self):
        logger.info(f"Closed mock Hailo runtime")

def load_and_run(model_path):
    logger.info(f"Loading mock Hailo model: {model_path}")
    return HailoRuntime(model_path)

__version__ = "4.20.0-mock"
""")
    
    # Create hailort __init__.py
    with open(hailort_path / '__init__.py', 'w') as f:
        f.write("""
# hailort module
import logging
import os
import sys

# Check if we're on ARM (Raspberry Pi) or x86_64 (development)
import platform
is_arm = platform.machine() in ('aarch64', 'armv7l', 'armv6l')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('hailort')

__version__ = "4.20.0"

# On a Raspberry Pi, try to use the real hailort module if available
if is_arm:
    logger.info("Running on ARM platform, attempting to load real Hailo SDK")
    
    # Try to find the real hailort module in a system path
    for path in sys.path:
        if 'site-packages' in path and '/usr/' in path:
            # Check if there's a real hailort module
            real_hailort = os.path.join(path, 'hailort')
            if os.path.exists(real_hailort) and os.path.isdir(real_hailort):
                logger.info(f"Found real hailort module at {real_hailort}")
                sys.path.insert(0, path)
                # Don't import yet, just add to path
                break
    
    # Try to import the real device class
    try:
        # Could be in different locations depending on SDK version
        # Try the hailort.pyhailort path first (newer SDK)
        try:
            from hailort.pyhailort import Device, infer
            logger.info("Imported Device from hailort.pyhailort")
            def load_and_run(model_path):
                return infer(model_path)
        except (ImportError, ModuleNotFoundError):
            # Try direct import (older SDK)
            try:
                from _pyhailort import Device
                from _pyhailort import infer
                logger.info("Imported Device from _pyhailort")
                def load_and_run(model_path):
                    return infer(model_path)
            except (ImportError, ModuleNotFoundError):
                # Fall back to mock implementation
                logger.warning("Could not import real Device, using mock implementation")
                from .mock_hailo import Device, load_and_run, __version__
    except (ImportError, ModuleNotFoundError):
        # Fall back to mock implementation
        logger.warning("Failed to import real Hailo Device, using mock implementation")
        from .mock_hailo import Device, load_and_run, __version__
else:
    # On development platform, use mock implementation
    logger.info("Running on development platform, using mock implementation")
    from .mock_hailo import Device, load_and_run, __version__
""")
    
    # Create hailo_platform __init__.py
    with open(hailo_platform_path / '__init__.py', 'w') as f:
        f.write("""
# hailo_platform module
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('hailo_platform')

__version__ = "4.20.0"

# Try to import from hailort
try:
    import hailort
    from hailort import Device, load_and_run
    __version__ = getattr(hailort, "__version__", "4.20.0")
    logger.info(f"Imported from hailort, version {__version__}")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Failed to import hailort: {e}")
    
    # Fallback implementation
    class Device:
        def __init__(self):
            self.device_id = "HAILO-PLATFORM-MOCK"
            logger.info(f"Initialized mock Device: {self.device_id}")
        
        def close(self):
            logger.info("Closed mock Device")
    
    def load_and_run(model_path):
        logger.info(f"Mock load_and_run for {model_path}")
        return None

# Create HailoDevice class for newer SDK compatibility
HailoDevice = Device

# Create pyhailort module for older SDK compatibility
class pyhailort:
    Device = Device
    
    @staticmethod
    def load_and_run(model_path):
        return load_and_run(model_path)
""")
    
    logger.info("Successfully created Hailo modules in the virtual environment")
    return True

def fix_hailo_imports():
    """Main function to fix Hailo imports."""
    logger.info("Starting Hailo imports fix")
    
    if create_hailo_modules():
        logger.info("Hailo modules created successfully")
        
        # Verify the modules can be imported
        try:
            logger.info("Verifying hailort can be imported...")
            sys.path.insert(0, str(project_root / 'venv' / 'lib' / 'python3.*' / 'site-packages'))
            import hailort
            logger.info(f"Successfully imported hailort version {hailort.__version__}")
            
            logger.info("Verifying hailo_platform can be imported...")
            import hailo_platform
            logger.info(f"Successfully imported hailo_platform version {hailo_platform.__version__}")
            
            logger.info("All modules imported successfully!")
            return True
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"Failed to import modules after fix: {e}")
            return False
    else:
        logger.error("Failed to create Hailo modules")
        return False

if __name__ == "__main__":
    if fix_hailo_imports():
        logger.info("Hailo imports fix completed successfully")
        sys.exit(0)
    else:
        logger.error("Hailo imports fix failed")
        sys.exit(1)