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

logger = logging.getLogger("AMSLPR.install_hailo")

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
    
    if not in_venv:
        logger.info("Not in a virtual environment, creating one for Hailo SDK installation...")
        venv_path = project_root / "hailo_venv"
        
        try:
            # Create virtual environment if it doesn't exist
            if not venv_path.exists():
                logger.info(f"Creating virtual environment at {venv_path}")
                import venv
                venv.create(venv_path, with_pip=True)
            
            # Get the pip path in the virtual environment
            if platform.system() == "Windows":
                pip_path = venv_path / "Scripts" / "pip.exe"
                python_path = venv_path / "Scripts" / "python.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
                python_path = venv_path / "bin" / "python"
            
            # Upgrade pip in the virtual environment
            try:
                logger.info("Upgrading pip in virtual environment")
                subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], 
                              check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to upgrade pip in virtual environment: {e}")
            
            # Install packages in the virtual environment - sort them to install dependencies first
            # We want to install hailort before hailo_platform if both are present
            sorted_packages = sorted(python_packages, key=lambda p: 0 if "hailort-" in p.name and "hailo_platform" not in p.name else 1)
            
            for package in sorted_packages:
                try:
                    logger.info(f"Installing {package.name} in virtual environment")
                    result = subprocess.run([str(pip_path), "install", "--force-reinstall", str(package)], 
                                          check=True, capture_output=True, text=True)
                    logger.info(f"Successfully installed {package.name}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to install {package.name} in virtual environment: {e}")
                    logger.error(f"stdout: {e.stdout}")
                    logger.error(f"stderr: {e.stderr}")
                    success = False
            
            # Verify the installation in the virtual environment
            try:
                logger.info("Verifying Hailo SDK installation in virtual environment...")
                verification_result = subprocess.run(
                    [str(python_path), "-c", 
                     """try:\n    import hailo_platform\n    print(f'hailo_platform version: {getattr(hailo_platform, "__version__", "unknown")}')\n    try:\n        import hailort\n        print(f'hailort version: {getattr(hailort, "__version__", "unknown")}')\n    except ImportError as e:\n        print(f'hailort import error: {e}')\nexcept ImportError as e:\n    print(f'hailo_platform import error: {e}')"""],
                    check=False, capture_output=True, text=True
                )
                logger.info(f"Verification result:\n{verification_result.stdout}")
                if "import error" in verification_result.stdout:
                    logger.warning("Some Hailo modules could not be imported")
                    
                    # Try installing hailort directly if it's missing
                    if "hailort import error" in verification_result.stdout:
                        logger.info("Attempting to install hailort directly...")
                        try:
                            subprocess.run([str(pip_path), "install", "hailort"], 
                                          check=True, capture_output=True, text=True)
                            logger.info("Successfully installed hailort directly")
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Failed to install hailort directly: {e}")
            except Exception as e:
                logger.error(f"Failed to verify installation: {e}")
            
            # Create a wrapper script to run with the virtual environment
            wrapper_script = project_root / "run_with_hailo.sh"
            with open(wrapper_script, "w") as f:
                f.write(f"#!/bin/bash\n")
                f.write(f"# This script runs commands with the Hailo virtual environment\n")
                f.write(f"source {venv_path}/bin/activate\n")
                f.write(f"exec \"$@\"\n")
            
            # Make the wrapper script executable
            os.chmod(wrapper_script, 0o755)
            
            logger.info(f"Created wrapper script at {wrapper_script}")
            logger.info("To run commands with Hailo SDK, use: ./run_with_hailo.sh python3 your_script.py")
            
            return success
        except Exception as e:
            logger.error(f"Failed to set up virtual environment: {e}")
            logger.info("Falling back to system installation with --break-system-packages")
    
    # If we're already in a virtual environment or failed to create one, install directly
    # Sort packages to install dependencies first
    sorted_packages = sorted(python_packages, key=lambda p: 0 if "hailort-" in p.name and "hailo_platform" not in p.name else 1)
    
    for package in sorted_packages:
        try:
            logger.info(f"Installing {package.name}")
            # Use pip install with --force-reinstall and --break-system-packages
            cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall"]
            if not in_venv:
                cmd.append("--break-system-packages")
            cmd.append(str(package))
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully installed {package.name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {package.name}: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            success = False
    
    # Try installing hailort directly if needed
    try:
        import hailo_platform
        try:
            import hailort
            logger.info("hailort module is available")
        except ImportError:
            logger.warning("hailort module is not available, attempting to install directly...")
            cmd = [sys.executable, "-m", "pip", "install", "hailort"]
            if not in_venv:
                cmd.append("--break-system-packages")
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info("Successfully installed hailort directly")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install hailort directly: {e}")
    except ImportError:
        logger.warning("hailo_platform module is not available, cannot check for hailort")
    
    return success

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
    
    # Find Hailo packages
    runtime_package, driver_package, python_packages = find_hailo_packages()
    
    # Install Hailo runtime
    if runtime_package:
        install_hailo_runtime(runtime_package, driver_package)
    
    # Create udev rules
    create_udev_rules()
    
    # Install Hailo Python packages
    if python_packages:
        install_hailo_python_packages(python_packages)
    
    # Create symlinks for compatibility
    create_symlinks()
    
    # Verify installation
    if verify_installation():
        logger.info("Hailo SDK installation completed successfully")
    else:
        logger.error("Hailo SDK installation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
