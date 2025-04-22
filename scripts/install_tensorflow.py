#!/usr/bin/env python3
"""
Install TensorFlow on Raspberry Pi
"""

import os
import sys
import logging
import subprocess
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger()

def run_command(command):
    """Run a shell command and return the output"""
    log.info(f"Running: {command}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        log.error(f"Error: {stderr}")
        return False
    return True

def install_tensorflow():
    """Install TensorFlow on Raspberry Pi"""
    log.info("======== Installing TensorFlow for Raspberry Pi ========")
    
    # Check if running on Raspberry Pi
    if not platform.machine().startswith('arm') and not platform.machine().startswith('aarch'):
        log.warning("This script is intended for Raspberry Pi. Your system is: " + platform.machine())
        log.warning("Continuing anyway, but installation may fail.")
    
    # Check Python version
    python_version = sys.version_info
    log.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Update pip
    log.info("\nUpdating pip...")
    if not run_command("pip install --upgrade pip"):
        log.error("Failed to update pip. Continuing anyway.")
    
    # Install dependencies
    log.info("\nInstalling required dependencies...")
    dependencies = [
        "numpy",
        "pillow",
        "scipy",
        "h5py",
        "pybind11"
    ]
    
    if not run_command(f"pip install {' '.join(dependencies)}"):
        log.error("Failed to install some dependencies. Continuing with TensorFlow installation.")
    
    # Install TensorFlow (ARM64 version)
    log.info("\nInstalling TensorFlow for ARM64 architecture...")
    
    # Install the tensorflow-aarch64 package specifically designed for Raspberry Pi
    if not run_command("pip install tensorflow-aarch64==2.9.1"):
        log.error("Failed to install tensorflow-aarch64. Check your internet connection and try again.")
        log.info("You may need to run: sudo apt-get update && sudo apt-get install -y libhdf5-dev")
        return False
    else:
        log.info("TensorFlow ARM64 package installed successfully!")
    
    # Verify installation
    log.info("\nVerifying TensorFlow installation...")
    verify_cmd = "python -c \"import tensorflow as tf; print('TensorFlow version:', tf.__version__); print('Num GPUs Available: ', len(tf.config.experimental.list_physical_devices(\'GPU\')))\"" 
    if not run_command(verify_cmd):
        log.warning("TensorFlow verification failed. It may not be installed correctly.")
        return False
    
    log.info("\n======== TensorFlow Installation Complete ========")
    log.info("You can now use TensorFlow in your AMSLPR application.")
    log.info("Restart the AMSLPR service for changes to take effect:")
    log.info("sudo systemctl restart amslpr")
    return True

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() == 0:
        log.info("Running as root. Proceeding with installation.")
    else:
        log.warning("Not running as root. Some operations may fail.")
        log.warning("Consider running with 'sudo python scripts/install_tensorflow.py'")
    
    success = install_tensorflow()
    sys.exit(0 if success else 1)
