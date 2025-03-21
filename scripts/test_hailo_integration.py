
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

import os
import sys
import logging
import json
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AMSLPR.test_hailo')

# Get project root
project_root = Path(__file__).parent.parent

def test_hailo_sdk_installation():
    """Test if Hailo SDK is installed"""
    try:
        import hailo_platform
        logger.info("✅ Hailo SDK is installed")
        return True
    except ImportError:
        logger.error("❌ Hailo SDK is not installed")
        logger.error("   You need to download the Hailo SDK from the Hailo Developer Zone (https://hailo.ai/developer-zone/)")
        logger.error("   and install the packages as described in the documentation")
        return False

def test_hailo_device():
    """Test if Hailo device is accessible"""
    try:
        import hailo_platform
        try:
            device = hailo_platform.HailoDevice()
            logger.info(f"✅ Hailo device is accessible. Device ID: {device.device_id}")
            logger.info(f"   Architecture: {device.architecture}")
            return True
        except Exception as e:
            logger.error(f"❌ Hailo device is not accessible: {e}")
            logger.error("   Check if the device is properly connected and the driver is installed")
            return False
    except ImportError:
        logger.error("❌ Cannot test device: Hailo SDK is not installed")
        return False

def test_hailo_models():
    """Test if Hailo models are available"""
    models_dir = project_root / 'models'
    if not models_dir.exists():
        logger.error(f"❌ Models directory not found: {models_dir}")
        return False
    
    # Check for .hef files
    hef_files = list(models_dir.glob('*.hef'))
    if not hef_files:
        logger.error("❌ No Hailo models (.hef files) found in models directory")
        logger.error("   Run: sudo ./scripts/hailo_raspberry_pi_setup.sh to download models")
        return False
    
    logger.info(f"✅ Found {len(hef_files)} Hailo model files:")
    for model_file in hef_files:
        logger.info(f"   - {model_file.name}")
    
    return True

def test_ocr_config():
    """Test if OCR configuration is properly set up for Hailo"""
    config_path = project_root / 'config' / 'ocr_config.json'
    if not config_path.exists():
        logger.error(f"❌ OCR configuration file not found: {config_path}")
        logger.error("   Run: python scripts/enable_hailo_tpu.py to create the configuration")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Check if Hailo is enabled
        if not config.get('use_hailo_tpu', False):
            logger.error("❌ Hailo TPU is not enabled in OCR configuration")
            logger.error("   Run: python scripts/enable_hailo_tpu.py to enable Hailo TPU")
            return False
        
        # Check if Hailo model paths are set
        deep_learning = config.get('deep_learning', {})
        hailo_ocr_model_path = deep_learning.get('hailo_ocr_model_path')
        if not hailo_ocr_model_path:
            logger.error("❌ Hailo OCR model path is not set in OCR configuration")
            return False
        
        # Check if model file exists
        model_path = project_root / hailo_ocr_model_path
        if not model_path.exists():
            logger.error(f"❌ Hailo OCR model file not found: {model_path}")
            return False
        
        logger.info("✅ OCR configuration is properly set up for Hailo")
        logger.info(f"   OCR model: {hailo_ocr_model_path}")
        
        # Check for detector model
        hailo_detector_model_path = deep_learning.get('hailo_detector_model_path')
        if hailo_detector_model_path:
            detector_path = project_root / hailo_detector_model_path
            if detector_path.exists():
                logger.info(f"✅ Detector model: {hailo_detector_model_path}")
            else:
                logger.warning(f"⚠️ Detector model file not found: {detector_path}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to read OCR configuration: {e}")
        return False

def test_hailo_integration():
    """Run all tests for Hailo integration"""
    logger.info("Testing Hailo integration...")
    logger.info("-" * 50)
    
    # Run tests
    sdk_installed = test_hailo_sdk_installation()
    device_accessible = test_hailo_device() if sdk_installed else False
    models_available = test_hailo_models()
    config_valid = test_ocr_config()
    
    # Print summary
    logger.info("-" * 50)
    logger.info("Test Summary:")
    logger.info(f"Hailo SDK Installation: {'✅ PASS' if sdk_installed else '❌ FAIL'}")
    logger.info(f"Hailo Device Accessibility: {'✅ PASS' if device_accessible else '❌ FAIL'}")
    logger.info(f"Hailo Models Availability: {'✅ PASS' if models_available else '❌ FAIL'}")
    logger.info(f"OCR Configuration: {'✅ PASS' if config_valid else '❌ FAIL'}")
    logger.info("-" * 50)
    
    # Overall result
    if sdk_installed and device_accessible and models_available and config_valid:
        logger.info("✅ All tests passed! Hailo integration is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Hailo integration may not work correctly.")
        return False

if __name__ == '__main__':
    test_hailo_integration()
