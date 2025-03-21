# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AMSLPR.verify_hailo')

# Get project root
project_root = Path(__file__).parent.parent

def check_hailo_sdk_installation():
    """Check if Hailo SDK is installed."""
    try:
        import hailo_platform
        logger.info("✅ Hailo SDK is installed")
        logger.info(f"   Version: {hailo_platform.__version__}")
        return True
    except ImportError:
        logger.error("❌ Hailo SDK is not installed")
        logger.error("   Please install the Hailo SDK from the Hailo Developer Zone (https://hailo.ai/developer-zone/)")
        logger.error("   Follow the instructions in docs/raspberry_pi_hailo_setup.md")
        
        # Check if Hailo packages are available in the project directory
        packages_dir = project_root / 'packages' / 'hailo'
        if packages_dir.exists():
            hailo_packages = list(packages_dir.glob("*.whl")) + list(packages_dir.glob("*.deb"))
            if hailo_packages:
                logger.info("✅ Found Hailo packages in project directory:")
                for package in hailo_packages:
                    logger.info(f"   - {package.name}")
                logger.info("   These packages will be automatically installed during the Raspberry Pi installation.")
                logger.info("   Run 'sudo ./scripts/install_on_raspberry_pi.sh' to install them.")
        return False

def check_hailo_device():
    """Check if Hailo device is accessible."""
    try:
        import hailo_platform
        try:
            # Try to initialize Hailo device - handle different SDK versions
            try:
                # Newer SDK version
                from hailo_platform import HailoDevice
                device = HailoDevice()
            except (ImportError, AttributeError):
                try:
                    # Older SDK version with pyhailort
                    from hailo_platform import pyhailort
                    device = pyhailort.Device()
                except (ImportError, AttributeError):
                    # Even older SDK version - direct import
                    import hailort
                    device = hailort.Device()
            
            logger.info(f"✅ Hailo device is accessible")
            logger.info(f"   Device ID: {device.device_id if hasattr(device, 'device_id') else 'Unknown'}")
            return True
        except Exception as e:
            logger.error(f"❌ Hailo device is not accessible: {e}")
            logger.error("   Check if the device is properly connected and the driver is installed.")
            logger.error("   Run 'sudo ls -l /dev/hailo*' to check if the device is detected.")
            return False
    except ImportError:
        logger.error("❌ Hailo SDK is not installed, cannot check device")
        return False

def check_hailo_models():
    """Check if Hailo models are available."""
    models_dir = project_root / 'models'
    if not models_dir.exists():
        logger.error(f"❌ Models directory does not exist: {models_dir}")
        return False
    
    # Check for specific Hailo models
    lprnet_models = list(models_dir.glob("*lprnet*.hef"))
    detector_models = list(models_dir.glob("*license_plate*.hef")) + list(models_dir.glob("*yolo*.hef"))
    
    if lprnet_models:
        logger.info(f"✅ Found LPRNet model(s):")
        for model in lprnet_models:
            logger.info(f"   - {model.name}")
    else:
        logger.warning(f"⚠️ No LPRNet models found in {models_dir}")
    
    if detector_models:
        logger.info(f"✅ Found detector model(s):")
        for model in detector_models:
            logger.info(f"   - {model.name}")
    else:
        logger.warning(f"⚠️ No detector models found in {models_dir}")
    
    return bool(lprnet_models or detector_models)

def check_ocr_config():
    """Check if OCR configuration is set up for Hailo TPU."""
    config_path = project_root / 'config' / 'ocr_config.json'
    if not config_path.exists():
        logger.warning(f"⚠️ OCR configuration file does not exist: {config_path}")
        logger.warning(f"   Run 'python scripts/enable_hailo_tpu.py' to create it")
        return False
    
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if config.get('use_hailo_tpu', False):
            logger.info(f"✅ OCR configuration is set up for Hailo TPU")
            
            # Check for model paths
            hailo_ocr_model_path = config.get('deep_learning', {}).get('hailo_ocr_model_path')
            hailo_detector_model_path = config.get('deep_learning', {}).get('hailo_detector_model_path')
            
            if hailo_ocr_model_path:
                logger.info(f"   OCR model: {hailo_ocr_model_path}")
            else:
                logger.warning(f"⚠️ No Hailo OCR model specified in configuration")
            
            if hailo_detector_model_path:
                logger.info(f"   Detector model: {hailo_detector_model_path}")
            else:
                logger.warning(f"⚠️ No Hailo detector model specified in configuration")
            
            return True
        else:
            logger.warning(f"⚠️ Hailo TPU is not enabled in OCR configuration")
            logger.warning(f"   Run 'python scripts/enable_hailo_tpu.py' to enable it")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to read OCR configuration: {e}")
        return False

def main():
    """Main function."""
    logger.info("=== Verifying Hailo TPU Installation ===")
    
    # Check Hailo SDK installation
    sdk_installed = check_hailo_sdk_installation()
    
    # Check Hailo device
    device_accessible = check_hailo_device()
    
    # Check Hailo models
    models_available = check_hailo_models()
    
    # Check OCR configuration
    ocr_configured = check_ocr_config()
    
    # Summary
    logger.info("\n=== Verification Summary ===")
    logger.info(f"Hailo SDK installed: {'✅ Yes' if sdk_installed else '❌ No'}")
    logger.info(f"Hailo device accessible: {'✅ Yes' if device_accessible else '❌ No'}")
    logger.info(f"Hailo models available: {'✅ Yes' if models_available else '❌ No'}")
    logger.info(f"OCR configured for Hailo: {'✅ Yes' if ocr_configured else '❌ No'}")
    
    if sdk_installed and device_accessible and models_available and ocr_configured:
        logger.info("\n✅ Hailo TPU is properly installed and configured!")
        return 0
    else:
        logger.error("\n❌ Hailo TPU installation is incomplete or not properly configured.")
        logger.error("   Please follow the instructions in docs/raspberry_pi_hailo_setup.md")
        return 1

if __name__ == '__main__':
    sys.exit(main())
