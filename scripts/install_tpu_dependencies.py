#!/usr/bin/env python3
"""
Script to install Hailo TPU dependencies
"""

import subprocess
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger('tpu-setup')

def run_command(cmd, cwd=None):
    """Run a command and return its output"""
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)}")
        log.error(f"Error: {e.stderr}")
        return None

def main():
    log.info("Installing TensorFlow and Hailo TPU dependencies...")
    
    # Determine if we're on Windows or Linux
    is_windows = os.name == 'nt'
    pip_cmd = [sys.executable, "-m", "pip"]
    
    # Step 1: Install TensorFlow
    log.info("\nStep 1: Installing TensorFlow...")
    tf_version = "2.9.0" if is_windows else "2.10.0"  # Different versions for different platforms
    tf_cmd = pip_cmd + ["install", f"tensorflow=={tf_version}", "--upgrade"]
    run_command(tf_cmd)
    
    # Step 2: Install Hailo SDK
    log.info("\nStep 2: Installing Hailo SDK packages...")
    if is_windows:
        # Windows installation from wheel files
        wheels_dir = Path("./hailo_wheels") if Path("./hailo_wheels").exists() else Path("../hailo_wheels")
        if not wheels_dir.exists():
            log.error(f"Hailo wheels directory not found at {wheels_dir}")
            log.info("Please download the Hailo SDK wheels to the 'hailo_wheels' directory")
            log.info("You can download them from the Hailo Developer Zone: https://hailo.ai/developer-zone/")
            return False
        
        for wheel in wheels_dir.glob("*.whl"):
            log.info(f"Installing {wheel.name}...")
            wheel_cmd = pip_cmd + ["install", str(wheel)]
            run_command(wheel_cmd)
    else:
        # Linux installation using apt
        log.info("For Linux, installing Hailo SDK via apt repository...")
        log.info("Run the following commands to install the Hailo SDK:")
        log.info("  sudo add-apt-repository -y 'deb https://hailo-hailort.s3.eu-west-2.amazonaws.com/hailort/latest/ubuntu focal main'")
        log.info("  sudo apt-get update")
        log.info("  sudo apt-get install -y hailort hailo-dev")
    
    # Step 3: Check installation
    log.info("\nStep 3: Verifying installation...")
    try:
        import tensorflow as tf
        log.info(f"✅ TensorFlow installed: {tf.__version__}")
    except ImportError:
        log.error("❌ TensorFlow not installed correctly")
    
    try:
        import hailo_platform
        log.info(f"✅ hailo_platform installed")
    except ImportError:
        log.error("❌ hailo_platform not installed correctly")
    
    try:
        import hailo_model_zoo
        log.info(f"✅ hailo_model_zoo installed")
    except ImportError:
        log.error("❌ hailo_model_zoo not installed correctly")
    
    try:
        import hailort
        log.info(f"✅ hailort installed")
    except ImportError:
        log.error("❌ hailort not installed correctly")
    
    log.info("\nInstallation complete! Next steps:")
    log.info("1. Run 'python scripts/download_hailo_models.py' to download the required models")
    log.info("2. Run 'python scripts/enable_hailo_tpu.py' to configure the system for TPU usage")
    log.info("3. Restart the AMSLPR application")
    
    return True

if __name__ == "__main__":
    main()
