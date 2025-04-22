#!/usr/bin/env python3
"""
Install TensorFlow for AMSLPR in a virtual environment
"""

import os
import sys
import logging
import subprocess
import platform
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger()

# Default paths
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_PATH = PROJECT_ROOT / 'venv'

def run_command(command):
    """Run a shell command and return success status"""
    log.info(f"Running: {command}")
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    if process.returncode != 0:
        log.error(f"Error: {process.stderr}")
        return False
    return True

def install_system_packages():
    """Install required system packages using apt"""
    log.info("\nInstalling system dependencies...")
    
    # Install Python development packages and virtual environment support
    system_packages = [
        "python3-dev",
        "python3-venv", 
        "python3-pip",
        "python3-full",
        "libhdf5-dev"
    ]
    
    return run_command(f"apt-get update && apt-get install -y {' '.join(system_packages)}")

def create_virtual_environment():
    """Create a Python virtual environment for TensorFlow"""
    log.info("\nCreating Python virtual environment...")
    
    # First check if venv already exists
    if os.path.exists(VENV_PATH):
        log.info(f"Virtual environment already exists at {VENV_PATH}")
        return True
    
    # Create venv
    if not run_command(f"python3 -m venv {VENV_PATH}"):
        log.error("Failed to create virtual environment")
        return False
    
    log.info(f"Created virtual environment at {VENV_PATH}")
    return True

def install_tensorflow_in_venv():
    """Install TensorFlow in the virtual environment"""
    # Set paths to pip and python in venv
    venv_pip = VENV_PATH / 'bin' / 'pip'
    venv_python = VENV_PATH / 'bin' / 'python'
    
    # Update pip in venv
    log.info("\nUpdating pip in virtual environment...")
    if not run_command(f"{venv_pip} install --upgrade pip"):
        log.warning("Failed to update pip. Continuing anyway.")
    
    # Install dependencies in venv
    log.info("\nInstalling required dependencies in virtual environment...")
    dependencies = [
        "wheel",
        "numpy",
        "pillow",
        "scipy",
        "h5py",
        "pybind11"
    ]
    
    if not run_command(f"{venv_pip} install {' '.join(dependencies)}"):
        log.warning("Failed to install some dependencies. Continuing with TensorFlow installation.")
    
    # Install TensorFlow (ARM64 version)
    log.info("\nInstalling TensorFlow for ARM64 architecture...")
    
    # Install the tensorflow-aarch64 package specifically designed for Raspberry Pi
    if not run_command(f"{venv_pip} install tensorflow-aarch64==2.9.1"):
        log.error("Failed to install tensorflow-aarch64")
        return False
    
    log.info("TensorFlow ARM64 package installed successfully!")
    
    # Verify installation
    log.info("\nVerifying TensorFlow installation...")
    verify_cmd = f"{venv_python} -c \"import tensorflow as tf; print('TensorFlow version:', tf.__version__); print('Num GPUs Available: ', len(tf.config.experimental.list_physical_devices(\\'GPU\\')))\""
    if not run_command(verify_cmd):
        log.warning("TensorFlow verification failed. It may not be installed correctly.")
        return False
    
    return True

def configure_amslpr_for_venv():
    """Configure AMSLPR to use the virtual environment"""
    log.info("\nConfiguring AMSLPR service to use the virtual environment...")
    
    # Create or update the service file to use the venv python
    service_file = Path('/etc/systemd/system/amslpr.service')
    
    if not service_file.exists():
        log.warning(f"Service file not found at {service_file}, skipping configuration.")
        log.info("To manually configure AMSLPR, edit the service file to use venv/bin/python")
        return True
    
    # Read existing service file
    try:
        with open(service_file, 'r') as f:
            service_content = f.read()
        
        # Check if already configured for venv
        if str(VENV_PATH) in service_content:
            log.info("Service already configured to use virtual environment")
            return True
        
        # Update the ExecStart line to use the venv python
        new_content = []
        for line in service_content.splitlines():
            if line.startswith('ExecStart=') and 'python' in line:
                parts = line.split()
                python_cmd_index = next((i for i, part in enumerate(parts) if 'python' in part), -1)
                
                if python_cmd_index >= 0:
                    parts[python_cmd_index] = f"{VENV_PATH}/bin/python"
                    line = ' '.join(parts)
            
            new_content.append(line)
        
        # Write updated service file
        with open('/tmp/amslpr.service.new', 'w') as f:
            f.write('\n'.join(new_content))
        
        # Move updated file to service location
        if not run_command(f"mv /tmp/amslpr.service.new {service_file}"):
            log.error("Failed to update service file")
            return False
        
        # Reload systemd
        if not run_command("systemctl daemon-reload"):
            log.warning("Failed to reload systemd daemon")
        
        log.info("Service updated to use virtual environment")
        return True
    
    except Exception as e:
        log.error(f"Error configuring service: {e}")
        return False

def install_tensorflow():
    """Main function to install TensorFlow for AMSLPR"""
    log.info("======== Installing TensorFlow for AMSLPR ========")
    
    # Check if running on Raspberry Pi
    if not platform.machine().startswith('arm') and not platform.machine().startswith('aarch'):
        log.warning("This script is intended for Raspberry Pi. Your system is: " + platform.machine())
        log.warning("Continuing anyway, but installation may fail.")
    
    # Check Python version
    python_version = sys.version_info
    log.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 1. Install system packages
    if not install_system_packages():
        log.error("Failed to install required system packages")
        return False
    
    # 2. Create virtual environment
    if not create_virtual_environment():
        log.error("Failed to create virtual environment")
        return False
    
    # 3. Install TensorFlow in the virtual environment
    if not install_tensorflow_in_venv():
        log.error("Failed to install TensorFlow in virtual environment")
        return False
    
    # 4. Configure AMSLPR to use the virtual environment
    if not configure_amslpr_for_venv():
        log.warning("Failed to configure AMSLPR to use virtual environment automatically")
        log.warning("You may need to manually update the AMSLPR service")
    
    log.info("\n======== TensorFlow Installation Complete ========")
    log.info(f"TensorFlow has been installed in the virtual environment at: {VENV_PATH}")
    log.info("To activate the virtual environment: ")
    log.info(f"source {VENV_PATH}/bin/activate")
    
    log.info("\nTo use TensorFlow with AMSLPR, restart the service:")
    log.info("sudo systemctl restart amslpr")
    
    return True

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        log.error("This script must be run as root (with sudo)")
        log.error("Please run: sudo python scripts/install_tensorflow.py")
        sys.exit(1)
    
    success = install_tensorflow()
    sys.exit(0 if success else 1)
