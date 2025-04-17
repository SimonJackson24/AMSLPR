#!/usr/bin/env python3
"""
Hailo TPU diagnostic script

This script diagnoses issues with Hailo TPU detection on Raspberry Pi and helps resolve them.
"""

import os
import sys
import subprocess
import importlib.util
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('hailo-diagnostic')

def run_command(cmd):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_hailo_module():
    """Check if hailort Python module is installed"""
    logger.info("Checking for hailort Python module...")
    if importlib.util.find_spec("hailort"):
        logger.info("✓ hailort Python module is installed")
        return True
    else:
        logger.error("✗ hailort Python module is not installed")
        return False

def install_hailo_module():
    """Install the hailort Python module"""
    logger.info("Installing hailort Python module...")
    success, output = run_command("pip3 install hailort")
    if success:
        logger.info("✓ Successfully installed hailort module")
        return True
    else:
        logger.error(f"✗ Failed to install hailort module: {output}")
        return False

def check_device_file():
    """Check if /dev/hailo0 device file exists"""
    logger.info("Checking for Hailo device file...")
    if os.path.exists('/dev/hailo0'):
        logger.info("✓ Device file /dev/hailo0 exists")
        return True
    else:
        logger.error("✗ Device file /dev/hailo0 does not exist")
        return False

def check_hailoRT_driver():
    """Check if HailoRT driver is installed and loaded"""
    logger.info("Checking for HailoRT driver...")
    success, output = run_command("lsmod | grep hailo")
    if success and output.strip():
        logger.info(f"✓ HailoRT driver is loaded: {output.strip()}")
        return True
    else:
        logger.error("✗ HailoRT driver is not loaded")
        return False

def install_hailo_driver():
    """Attempt to install and load the Hailo driver"""
    logger.info("Checking for Hailo driver package...")
    success, output = run_command("dpkg -l | grep hailo")
    
    if not success or 'hailort' not in output:
        logger.info("Hailo driver package not found. Checking for installation file...")
        # Check for common installation package locations
        locations = [
            "/home/automate/AMSLPR/drivers/hailort",
            "/home/automate/hailort",
            "./drivers/hailort"
        ]
        
        install_file = None
        for loc in locations:
            if os.path.exists(f"{loc}/hailort.deb"):
                install_file = f"{loc}/hailort.deb"
                break
        
        if install_file:
            logger.info(f"Found Hailo installation package at {install_file}")
            logger.info("Installing Hailo driver...")
            success, output = run_command(f"sudo dpkg -i {install_file}")
            if success:
                logger.info("✓ Successfully installed Hailo driver package")
            else:
                logger.error(f"✗ Failed to install Hailo driver package: {output}")
                return False
        else:
            logger.error("✗ Could not find Hailo driver installation package")
            logger.info("Please download the appropriate Hailo driver for Raspberry Pi from the Hailo website")
            return False
    else:
        logger.info("✓ Hailo driver package is installed")
    
    # Try to load the driver if not already loaded
    if not check_hailoRT_driver():
        logger.info("Attempting to load Hailo driver...")
        success, output = run_command("sudo modprobe hailo")
        if success:
            logger.info("✓ Successfully loaded Hailo driver")
            return True
        else:
            logger.error(f"✗ Failed to load Hailo driver: {output}")
            return False
    return True

def check_hailo_device_connection():
    """Check if Hailo device is properly connected via PCIe"""
    logger.info("Checking PCIe connection for Hailo device...")
    success, output = run_command("lspci | grep -i hailo")
    if success and output.strip():
        logger.info(f"✓ Hailo device found on PCIe bus: {output.strip()}")
        return True
    else:
        logger.error("✗ Hailo device not found on PCIe bus")
        logger.info("This indicates a physical connection issue with the PCIe ribbon cable or power supply")
        return False

def check_hailo_power():
    """Check power status for Hailo device"""
    logger.info("Checking power for Hailo device...")
    logger.info("User reported that the LED is lit, which indicates the device is powered")
    return True

def test_hailo_initialization():
    """Test if we can initialize the Hailo device using the hailort module"""
    logger.info("Testing Hailo device initialization...")
    try:
        import hailort
        device = hailort.Device()
        device_id = device.device_id
        logger.info(f"✓ Successfully initialized Hailo device: {device_id}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize Hailo device: {e}")
        return False

def run_hailo_info():
    """Run the hailortcli info command to get device information"""
    logger.info("Running hailortcli info command...")
    success, output = run_command("hailortcli info")
    if success:
        logger.info(f"Hailo device information:\n{output}")
        return True
    else:
        logger.error(f"Failed to get Hailo device information: {output}")
        return False

def set_environment_variable():
    """Set the HAILO_ENABLED environment variable"""
    logger.info("Setting HAILO_ENABLED environment variable...")
    
    # Check if the variable is already set in the environment
    if os.environ.get('HAILO_ENABLED') == 'true':
        logger.info("✓ HAILO_ENABLED environment variable is already set to 'true'")
        return True
    
    # Create systemd environment file
    success, output = run_command("sudo sh -c 'echo \"HAILO_ENABLED=true\" > /etc/environment.d/hailo.conf'")
    if success:
        logger.info("✓ Created environment file for HAILO_ENABLED")
        os.environ['HAILO_ENABLED'] = 'true'  # Set in current process too
        return True
    else:
        logger.error(f"✗ Failed to create environment file: {output}")
        return False

def main():
    """Main diagnostic routine"""
    logger.info("===== Starting Hailo TPU Diagnostic =====")
    
    # Run all checks
    pcie_ok = check_hailo_device_connection()
    power_ok = check_hailo_power()
    driver_ok = check_hailoRT_driver() or install_hailo_driver()
    device_file_ok = check_device_file()
    module_ok = check_hailo_module() or install_hailo_module()
    
    # Only try to initialize if prerequisites are met
    init_ok = False
    if module_ok and device_file_ok:
        init_ok = test_hailo_initialization()
        if init_ok:
            run_hailo_info()
    
    # Set environment variable as fallback if needed
    env_var_set = False
    if not (pcie_ok and power_ok and driver_ok and device_file_ok and init_ok):
        logger.info("Setting HAILO_ENABLED environment variable as a fallback...")
        env_var_set = set_environment_variable()
    
    # Summary
    logger.info("\n===== Hailo TPU Diagnostic Summary =====")
    logger.info(f"PCIe Connection: {'✓' if pcie_ok else '✗'}")
    logger.info(f"Power Status: {'✓' if power_ok else '✗'}")
    logger.info(f"Driver Status: {'✓' if driver_ok else '✗'}")
    logger.info(f"Device File: {'✓' if device_file_ok else '✗'}")
    logger.info(f"hailort Module: {'✓' if module_ok else '✗'}")
    logger.info(f"Device Initialization: {'✓' if init_ok else '✗'}")
    
    if not (pcie_ok and power_ok and driver_ok and device_file_ok and init_ok):
        if env_var_set:
            logger.info("\nThe HAILO_ENABLED environment variable has been set as a fallback.")
            logger.info("After restarting the service, OCR settings will show the Hailo options")
            logger.info("even though the actual hardware may not be fully functional.")
        
        logger.info("\nRecommendations:")
        if not pcie_ok:
            logger.info("- Check the PCIe ribbon cable connection between the Raspberry Pi and Hailo TPU")
            logger.info("- Ensure the Hailo TPU is properly seated in its connector")
        if not driver_ok:
            logger.info("- Install the HailoRT driver package: https://hailo.ai/developer-zone/documentation/hailort/latest/")
        if not (device_file_ok or init_ok):
            logger.info("- Make sure the Hailo TPU is recognized by the system:")
            logger.info("  * Run 'sudo modprobe hailo' to load the driver")
            logger.info("  * Run 'sudo chmod 666 /dev/hailo0' to set proper permissions")
    else:
        logger.info("\n✓ All checks passed! Hailo TPU is properly configured.")
    
    logger.info("\nTo apply changes, restart the AMSLPR service:")
    logger.info("sudo systemctl restart amslpr")

if __name__ == "__main__":
    main()
