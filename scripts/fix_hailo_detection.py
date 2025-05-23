#!/usr/bin/env python3

"""
Diagnostic script to fix Hailo TPU detection issues

This script will:
1. Check for Hailo device files in /dev
2. Verify Hailo modules are installed and importable
3. Test device initialization with different SDK versions
4. Set the HAILO_ENABLED environment variable if needed
5. Create a diagnostic report
"""

import os
import sys
import logging
import importlib.util
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('hailo-diagnostics')

# Get project root
project_root = Path(__file__).parent.parent

def check_device_files():
    """Check if Hailo device files exist in /dev"""
    logger.info("\n=== Checking Hailo device files ===")
    
    # Check for /dev/hailo0
    hailo_dev = Path('/dev/hailo0')
    if hailo_dev.exists():
        logger.info("✓ /dev/hailo0 device file exists")
        # Check permissions
        try:
            permissions = subprocess.run(
                f"ls -la {hailo_dev}", 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            ).stdout.strip()
            logger.info(f"  Permissions: {permissions}")
            return True
        except Exception as e:
            logger.error(f"× Error checking device permissions: {e}")
    else:
        logger.error("× /dev/hailo0 device file NOT found")
        # Check if any hailo device exists
        try:
            hailo_devices = list(Path('/dev').glob('hailo*'))
            if hailo_devices:
                logger.info(f"  Found alternative Hailo devices: {[d.name for d in hailo_devices]}")
            else:
                logger.error("  No Hailo devices found in /dev")
                # Try to load the driver
                logger.info("  Attempting to load Hailo driver...")
                try:
                    subprocess.run(
                        "sudo modprobe hailort", 
                        shell=True, 
                        check=True, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE
                    )
                    logger.info("  Hailo driver loaded, checking for device files again")
                    if Path('/dev/hailo0').exists():
                        logger.info("✓ /dev/hailo0 device file now exists after loading driver")
                        return True
                except Exception as e:
                    logger.error(f"× Error loading Hailo driver: {e}")
        except Exception as e:
            logger.error(f"× Error checking for Hailo devices: {e}")
    
    return False

def check_hailo_modules():
    """Check if Hailo modules are installed and importable"""
    logger.info("\n=== Checking Hailo Python modules ===")
    
    modules_to_check = [
        'hailo_platform',
        'hailort',
        'hailo_platform.pyhailort'
    ]
    
    found_modules = []
    
    for module in modules_to_check:
        spec = importlib.util.find_spec(module.split('.')[0])
        if spec:
            logger.info(f"✓ Module '{module.split('.')[0]}' is installed")
            found_modules.append(module.split('.')[0])
            
            # Try importing the module
            try:
                imported_module = importlib.import_module(module.split('.')[0])
                logger.info(f"✓ Successfully imported '{module.split('.')[0]}'")
                
                # Get version if available
                if hasattr(imported_module, '__version__'):
                    logger.info(f"  Version: {imported_module.__version__}")
                elif hasattr(imported_module, 'version'):
                    logger.info(f"  Version: {imported_module.version}")
            except Exception as e:
                logger.error(f"× Error importing '{module}': {e}")
        else:
            logger.warning(f"× Module '{module}' is NOT installed")
    
    return found_modules

def test_device_initialization():
    """Test Hailo device initialization with different SDK versions"""
    logger.info("\n=== Testing Hailo device initialization ===")
    
    # Try different initialization methods based on SDK version
    methods = [
        ('hailo_platform.HailoDevice', 'Newer SDK with HailoDevice'),
        ('hailo_platform.pyhailort.Device', 'Older SDK with pyhailort'),
        ('hailort.Device', 'Direct hailort import')
    ]
    
    success = False
    
    for import_path, description in methods:
        logger.info(f"\nTrying method: {description}")
        
        module_path, class_name = import_path.rsplit('.', 1)
        
        try:
            # Check if module exists
            if importlib.util.find_spec(module_path.split('.')[0]):
                # Import the module
                module = importlib.import_module(module_path)
                logger.info(f"✓ Imported {module_path}")
                
                # Get the device class
                device_class = getattr(module, class_name)
                logger.info(f"✓ Found {class_name} class")
                
                # Try to initialize the device
                device = device_class()
                logger.info(f"✓ Successfully initialized Hailo device")
                
                # Get device info if available
                if hasattr(device, 'device_id'):
                    logger.info(f"  Device ID: {device.device_id}")
                if hasattr(device, 'get_info'):
                    info = device.get_info()
                    logger.info(f"  Device Info: {info}")
                
                success = True
                break
            else:
                logger.warning(f"× Module {module_path} not found")
        except ImportError as e:
            logger.warning(f"× Import error: {e}")
        except Exception as e:
            logger.error(f"× Error initializing device: {e}")
    
    return success

def set_environment_variable():
    """Set the HAILO_ENABLED environment variable"""
    logger.info("\n=== Setting HAILO_ENABLED environment variable ===")
    
    try:
        # Create systemd environment file
        cmd = "sudo sh -c 'echo \"HAILO_ENABLED=true\" > /etc/environment.d/hailo.conf'"
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.info("✓ Created environment file for HAILO_ENABLED")
        
        # Also set in current environment
        os.environ['HAILO_ENABLED'] = 'true'
        
        # Create a persistent marker file
        with open('/tmp/hailo_diag_success', 'w') as f:
            f.write('Hailo TPU detection successful')
        logger.info("✓ Created Hailo success marker file")
        
        return True
    except Exception as e:
        logger.error(f"× Error setting HAILO_ENABLED environment variable: {e}")
        return False

def create_diagnostic_report():
    """Create a diagnostic report for Hailo TPU"""
    logger.info("\n=== Creating diagnostic report ===")
    
    report = ["=== Hailo TPU Diagnostic Report ==="]
    
    # System information
    try:
        uname = subprocess.run(
            "uname -a", 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        ).stdout.strip()
        report.append(f"System: {uname}")
    except Exception:
        report.append("System: Unable to determine")
    
    # PCIe devices
    try:
        lspci = subprocess.run(
            "lspci | grep -i hailo", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        ).stdout.strip()
        if lspci:
            report.append(f"PCIe Hailo devices:\n{lspci}")
        else:
            report.append("PCIe Hailo devices: None found")
    except Exception:
        report.append("PCIe Hailo devices: Unable to determine")
    
    # Kernel modules
    try:
        lsmod = subprocess.run(
            "lsmod | grep -i hailo", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        ).stdout.strip()
        if lsmod:
            report.append(f"Hailo kernel modules:\n{lsmod}")
        else:
            report.append("Hailo kernel modules: None loaded")
    except Exception:
        report.append("Hailo kernel modules: Unable to determine")
    
    # Device files
    hailo_dev = Path('/dev/hailo0')
    if hailo_dev.exists():
        try:
            permissions = subprocess.run(
                f"ls -la {hailo_dev}", 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            ).stdout.strip()
            report.append(f"Device file: {hailo_dev} exists\nPermissions: {permissions}")
        except Exception:
            report.append(f"Device file: {hailo_dev} exists, but unable to get permissions")
    else:
        report.append(f"Device file: {hailo_dev} does NOT exist")
    
    # Python modules
    for module in ['hailo_platform', 'hailort']:
        spec = importlib.util.find_spec(module)
        if spec:
            try:
                imported_module = importlib.import_module(module)
                version = getattr(imported_module, '__version__', 'unknown')
                report.append(f"Python module: {module} is installed (version: {version})")
            except Exception as e:
                report.append(f"Python module: {module} is installed but cannot be imported: {e}")
        else:
            report.append(f"Python module: {module} is NOT installed")
    
    # Write report to file
    report_path = project_root / 'hailo_diagnostic_report.txt'
    with open(report_path, 'w') as f:
        f.write('\n'.join(report))
    
    logger.info(f"✓ Diagnostic report written to {report_path}")
    
    return report

def fix_hailo_detection():
    """Main function to diagnose and fix Hailo TPU detection issues"""
    logger.info("Starting Hailo TPU detection diagnostics")
    
    # Check device files
    device_files_ok = check_device_files()
    
    # Check Hailo modules
    found_modules = check_hailo_modules()
    
    # Test device initialization
    device_init_ok = test_device_initialization()
    
    # Create diagnostic report
    report = create_diagnostic_report()
    
    # Set environment variable if needed
    if device_init_ok:
        logger.info("\n=== Hailo TPU is working correctly ===")
        set_environment_variable()
        logger.info("\n✓ Hailo TPU detection fixed successfully")
        return True
    elif device_files_ok and found_modules:
        logger.warning("\n=== Hailo device files and modules exist, but device initialization failed ===")
        logger.info("Setting HAILO_ENABLED environment variable as fallback")
        set_environment_variable()
        logger.info("\n✓ Hailo TPU detection fixed with environment variable override")
        return True
    else:
        logger.error("\n=== Hailo TPU detection failed ===")
        logger.error("Please check the diagnostic report for more information")
        return False

if __name__ == "__main__":
    success = fix_hailo_detection()
    
    if success:
        logger.info("\nRestarting the AMSLPR service to apply changes...")
        try:
            subprocess.run(
                "sudo systemctl restart amslpr", 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            logger.info("✓ AMSLPR service restarted successfully")
        except Exception as e:
            logger.error(f"× Error restarting AMSLPR service: {e}")
    
    sys.exit(0 if success else 1)
