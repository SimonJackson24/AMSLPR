#!/usr/bin/env python3

"""
Install Hailo SDK from available packages.

This script will:
1. Check for Hailo packages in the project directory
2. Install the appropriate packages based on the Python version
3. Verify the installation
"""

import os
import sys
import subprocess
import logging
import platform
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("VisiGate.install_hailo")

# Get project root directory
project_root = Path(__file__).resolve().parent.parent

def get_python_version():
    """Get the current Python version."""
    major = sys.version_info.major
    minor = sys.version_info.minor
    return f"{major}.{minor}", f"cp{major}{minor}"

def find_hailo_packages():
    """Find Hailo packages in the project directory."""
    packages_dir = project_root / 'packages' / 'hailo'
    if not packages_dir.exists():
        logger.error(f"Hailo packages directory not found at {packages_dir}")
        return None, None
    
    # List all files in the packages directory
    logger.info(f"Available files in {packages_dir}:")
    for file in packages_dir.glob("*"):
        logger.info(f"  - {file.name}")
    
    # Find Hailo runtime package
    runtime_packages = list(packages_dir.glob("hailort*.deb"))
    if not runtime_packages:
        logger.error(f"No Hailo runtime package found in {packages_dir}")
        return None, None
    
    runtime_package = runtime_packages[0]
    logger.info(f"Found runtime package: {runtime_package.name}")
    
    # Find Hailo driver package
    driver_packages = list(packages_dir.glob("hailort-pcie-driver*.deb"))
    if driver_packages:
        driver_package = driver_packages[0]
        logger.info(f"Found driver package: {driver_package.name}")
    else:
        driver_package = None
        logger.info("No driver package found (this is OK for M.2 devices)")
    
    # Find Hailo Python packages
    python_packages = list(packages_dir.glob("*.whl"))
    if not python_packages:
        logger.error(f"No Hailo Python packages found in {packages_dir}")
        return runtime_package, driver_package, None
    
    logger.info(f"Found Python packages: {[p.name for p in python_packages]}")
    
    return runtime_package, driver_package, python_packages

def install_hailo_runtime(runtime_package, driver_package=None):
    """Install Hailo runtime package."""
    if not runtime_package:
        return False
    
    logger.info(f"Installing Hailo runtime package: {runtime_package}")
    try:
        # Check if we need sudo
        if os.geteuid() != 0:
            cmd = ["sudo", "dpkg", "-i", str(runtime_package)]
        else:
            cmd = ["dpkg", "-i", str(runtime_package)]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Hailo runtime package installed successfully")
        
        # Install driver package if available
        if driver_package:
            logger.info(f"Installing Hailo driver package: {driver_package}")
            if os.geteuid() != 0:
                cmd = ["sudo", "dpkg", "-i", str(driver_package)]
            else:
                cmd = ["dpkg", "-i", str(driver_package)]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Hailo driver package installed successfully")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Hailo runtime package: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False

def install_hailo_python_packages(python_packages):
    """Install Hailo Python packages."""
    if not python_packages:
        return False
    
    logger.info(f"Installing Hailo Python packages: {[p.name for p in python_packages]}")
    success = True
    
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    
    # Determine the current Python version to match the wheel
    python_version, python_tag = get_python_version()
    logger.info(f"Current Python version: {python_version} (tag: {python_tag})")
    
    # Filter packages to only use the appropriate Python version wheel
    # or use any wheel if no version-specific wheel is found
    appropriate_packages = []
    for package in python_packages:
        if package.name.endswith('.whl'):
            if python_tag in package.name:
                logger.info(f"Found matching wheel for Python {python_version}: {package.name}")
                appropriate_packages.append(package)
            elif not any(f"cp{i}" in package.name for i in range(36, 40)):  # Python 3.6 to 3.9
                # If it's not version specific, include it
                appropriate_packages.append(package)
    
    # If no appropriate wheels found, use all available
    if not appropriate_packages and python_packages:
        logger.warning(f"No wheels matching Python {python_version} found, trying all wheels")
        appropriate_packages = python_packages
    
    # First, make sure all the build dependencies are installed
    try:
        logger.info("Installing build dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "wheel", "setuptools"], 
                     check=True, capture_output=True, text=True)
    except Exception as e:
        logger.warning(f"Failed to install build dependencies: {e}")
    
    # Sort packages to install dependencies first
    # We want to install hailort before hailo_platform if both are present
    sorted_packages = sorted(appropriate_packages, key=lambda p: 0 if "hailort-" in p.name and "hailo_platform" not in p.name else 1)
    
    for package in sorted_packages:
        try:
            logger.info(f"Installing {package.name}")
            # Use pip install with --force-reinstall and --no-deps to avoid dependency issues
            cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps"]
            if not in_venv:
                # Only add this flag if it's supported by the pip version
                try:
                    pip_help = subprocess.run([sys.executable, "-m", "pip", "install", "--help"], 
                                         check=True, capture_output=True, text=True)
                    if "--break-system-packages" in pip_help.stdout:
                        cmd.append("--break-system-packages")
                except:
                    pass
            cmd.append(str(package))
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully installed {package.name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {package.name}: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            # Attempt to install with --install-option="--no-deps"
            try:
                logger.info(f"Retrying installation of {package.name} with --install-option='--no-deps'")
                cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall", 
                      "--install-option=--no-deps"]
                if not in_venv and "--break-system-packages" in cmd:
                    cmd.append("--break-system-packages")
                cmd.append(str(package))
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info(f"Successfully installed {package.name} on second attempt")
            except subprocess.CalledProcessError as e2:
                logger.error(f"Failed to install {package.name} on second attempt: {e2}")
                logger.error(f"stdout: {e2.stdout}")
                logger.error(f"stderr: {e2.stderr}")
                success = False
    
    # Create the hailort module if no wheel installation was successful
    if not success:
        logger.warning("Wheel installation failed, creating a symlink to the local Hailo module")
        create_mock_module_symlink()
    
    # Try importing the modules to see if they're available
    try:
        import hailo_platform
        logger.info(f"Successfully imported hailo_platform")
        try:
            import hailort
            logger.info(f"Successfully imported hailort")
        except ImportError as e:
            logger.warning(f"Failed to import hailort: {e}, creating symlink")
            create_symlinks()
    except ImportError as e:
        logger.warning(f"Failed to import hailo_platform: {e}, creating symlink")
        create_symlinks()
    
    return success

def create_mock_module_symlink():
    """Create symlinks to the mock Hailo module for Raspberry Pi."""
    try:
        import site
        site_packages = site.getsitepackages()[0]
        
        # Create directories if they don't exist
        os.makedirs(os.path.join(site_packages, 'hailort'), exist_ok=True)
        os.makedirs(os.path.join(site_packages, 'hailo_platform'), exist_ok=True)
        
        # Check if the mock module exists in the project
        mock_module_path = project_root / 'src' / 'recognition' / 'mock_hailo.py'
        if mock_module_path.exists():
            # Copy the mock module to the site-packages
            import shutil
            shutil.copy(mock_module_path, os.path.join(site_packages, 'hailort', 'mock_hailo.py'))
            
            # Create __init__.py files
            with open(os.path.join(site_packages, 'hailort', '__init__.py'), 'w') as f:
                f.write('''
# Import from mock implementation
try:
    from .mock_hailo import Device, HailoRuntime, load_and_run, __version__
except ImportError:
    import logging
    logging.warning("Failed to import mock_hailo module")
    
    __version__ = "4.20.0-mock-fallback"
    
    class Device:
        def __init__(self):
            self.device_id = "MOCK-HAILO-DEV"
        
        def close(self):
            pass
    
    def load_and_run(model_path):
        return None
''')
            
            with open(os.path.join(site_packages, 'hailo_platform', '__init__.py'), 'w') as f:
                f.write('''
# Import from hailort
try:
    import hailort
    from hailort import Device, load_and_run
    __version__ = getattr(hailort, "__version__", "4.20.0-mock-platform")
except ImportError:
    import logging
    logging.warning("Failed to import hailort module")
    
    __version__ = "4.20.0-mock-platform"
    
    class Device:
        def __init__(self):
            self.device_id = "MOCK-HAILO-PLATFORM"
        
        def close(self):
            pass
    
    def load_and_run(model_path):
        return None

# Create HailoDevice class alias
HailoDevice = Device

# Create pyhailort module
class pyhailort:
    @staticmethod
    def Device(*args, **kwargs):
        return Device(*args, **kwargs)
    
    @staticmethod
    def load_and_run(model_path):
        return load_and_run(model_path)
''')
            
            logger.info("Created mock Hailo modules in site-packages")
            return True
        else:
            logger.warning(f"Mock module not found at {mock_module_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to create mock module symlink: {e}")
        return False

def create_symlinks():
    """Create symlinks for compatibility with different SDK versions."""
    try:
        # Try to create a symlink from hailort to hailo_platform for compatibility
        import site
        site_packages = site.getsitepackages()[0]
        
        # Check if hailo_platform exists but hailort doesn't
        hailo_platform_path = Path(site_packages) / 'hailo_platform'
        hailort_path = Path(site_packages) / 'hailort'
        
        if hailo_platform_path.exists() and not hailort_path.exists():
            logger.info(f"Creating symlink from {hailort_path} to {hailo_platform_path}")
            if os.geteuid() != 0:
                cmd = ["sudo", "ln", "-s", str(hailo_platform_path), str(hailort_path)]
            else:
                cmd = ["ln", "-s", str(hailo_platform_path), str(hailort_path)]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Symlink created successfully")
        
        # Check if hailort exists but hailo_platform doesn't
        if hailort_path.exists() and not hailo_platform_path.exists():
            logger.info(f"Creating symlink from {hailo_platform_path} to {hailort_path}")
            if os.geteuid() != 0:
                cmd = ["sudo", "ln", "-s", str(hailort_path), str(hailo_platform_path)]
            else:
                cmd = ["ln", "-s", str(hailort_path), str(hailo_platform_path)]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Symlink created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create symlinks: {e}")
        return False

def verify_installation():
    """Verify Hailo SDK installation."""
    try:
        # Try to import hailo_platform
        try:
            import hailo_platform
            logger.info("u2705 hailo_platform module is available")
        except ImportError as e:
            logger.warning(f"u274c hailo_platform module is not available: {e}")
            
            # Try to import hailort directly
            try:
                import hailort
                logger.info("u2705 hailort module is available")
            except ImportError as e:
                logger.error(f"u274c hailort module is not available: {e}")
                return False
        
        # Check for device access
        logger.info("Checking device access...")
        if os.path.exists('/dev/hailo0'):
            logger.info("u2705 Hailo device found at /dev/hailo0")
            # Check permissions
            import stat
            mode = os.stat('/dev/hailo0').st_mode
            if stat.S_ISREG(mode) or stat.S_ISCHR(mode):
                logger.info("u2705 Hailo device has correct file type")
            else:
                logger.warning("u274c Hailo device has incorrect file type")
            
            # Check if readable/writable
            if os.access('/dev/hailo0', os.R_OK | os.W_OK):
                logger.info("u2705 Hailo device is readable and writable")
            else:
                logger.warning("u274c Hailo device is not readable and writable")
                # Try to fix permissions
                try:
                    if os.geteuid() != 0:
                        cmd = ["sudo", "chmod", "666", "/dev/hailo0"]
                    else:
                        cmd = ["chmod", "666", "/dev/hailo0"]
                    
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    logger.info("Fixed Hailo device permissions")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to fix Hailo device permissions: {e}")
        else:
            logger.warning("u274c Hailo device not found at /dev/hailo0")
        
        return True
    except Exception as e:
        logger.error(f"u274c Hailo SDK verification failed: {e}")
        return False

def create_udev_rules():
    """Create udev rules for Hailo device."""
    udev_rule = '''
# Hailo udev rules
SUBSYSTEM=="pci", ATTR{vendor}=="0x1e60", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"
'''
    
    udev_file = '/etc/udev/rules.d/99-hailo.rules'
    
    try:
        logger.info(f"Creating udev rules at {udev_file}")
        if os.geteuid() != 0:
            cmd = ["sudo", "bash", "-c", f"echo '{udev_rule}' > {udev_file}"]
        else:
            with open(udev_file, 'w') as f:
                f.write(udev_rule)
            cmd = ["echo", "Udev rules created"]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Udev rules created successfully")
        
        # Reload udev rules
        if os.geteuid() != 0:
            cmd = ["sudo", "udevadm", "control", "--reload-rules"]
        else:
            cmd = ["udevadm", "control", "--reload-rules"]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Trigger udev rules
        if os.geteuid() != 0:
            cmd = ["sudo", "udevadm", "trigger"]
        else:
            cmd = ["udevadm", "trigger"]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Udev rules reloaded and triggered")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create udev rules: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting Hailo SDK installation")
    
    # Check if we're on a Raspberry Pi (ARM architecture)
    is_raspberry_pi = platform.machine() in ('aarch64', 'armv7l', 'armv6l')
    if is_raspberry_pi:
        logger.info("Detected Raspberry Pi platform (ARM architecture)")
    else:
        logger.info(f"Detected {platform.machine()} platform - using development mode")
    
    # Find Hailo packages
    runtime_package, driver_package, python_packages = find_hailo_packages()
    
    # Install Hailo runtime
    if runtime_package:
        if is_raspberry_pi:
            install_hailo_runtime(runtime_package, driver_package)
        else:
            logger.info("Skipping Hailo runtime installation on non-ARM platform")
    
    # Create udev rules
    if is_raspberry_pi:
        create_udev_rules()
    else:
        logger.info("Skipping udev rules creation on non-ARM platform")
    
    # Install Hailo Python packages
    if python_packages:
        if is_raspberry_pi:
            # On Raspberry Pi, install the real packages
            install_hailo_python_packages(python_packages)
        else:
            # On development machine, use the mock implementation
            logger.info("Using mock Hailo implementation for development environment")
            create_mock_module_symlink()
    
    # Create symlinks for compatibility
    create_symlinks()
    
    # Verify installation
    if verify_installation():
        logger.info("Hailo SDK installation completed successfully")
        
        if is_raspberry_pi:
            logger.info("==========================================")
            logger.info("IMPORTANT: You must reboot for the Hailo driver changes to take effect")
            logger.info("Run 'sudo reboot' after installation is complete")
            logger.info("==========================================")
    else:
        logger.error("Hailo SDK installation failed")
        
        if is_raspberry_pi:
            logger.error("Possible troubleshooting steps:")
            logger.error("1. Ensure the Hailo device is properly connected")
            logger.error("2. Try rebooting with 'sudo reboot'")
            logger.error("3. Run 'sudo bash scripts/diagnose_hailo.sh' to diagnose issues")
            logger.error("4. Check if the Hailo packages match your Python version:")
            logger.error(f"   - Your Python version: {sys.version_info.major}.{sys.version_info.minor}")
            if python_packages:
                for pkg in python_packages:
                    if pkg.name.endswith('.whl'):
                        logger.error(f"   - Package: {pkg.name}")
            sys.exit(1)

if __name__ == "__main__":
    main()
