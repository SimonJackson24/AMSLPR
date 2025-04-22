#!/usr/bin/env python3
"""
Direct test of Hailo TPU functionality without web UI
"""

import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger()

def test_hailo_directly():
    """
    Test the Hailo TPU directly using the detector code from the application
    """
    log.info("TESTING HAILO TPU DIRECTLY")
    log.info("="*60)
    
    # Try to import TensorFlow first
    log.info("Step 1: Importing TensorFlow...")
    try:
        import tensorflow as tf
        log.info(f"\u2705 TensorFlow is available (version {tf.__version__})")
    except ImportError as e:
        log.error(f"\u274c TensorFlow import failed: {e}")
        log.error("TensorFlow is required for deep learning functionality.")
        log.error("Please install TensorFlow with: pip install tensorflow")
        return False
    
    # Try to import Hailo modules
    log.info("\nStep 2: Importing Hailo modules...")
    try:
        import hailo_platform
        import hailo_model_zoo
        log.info("\u2705 Hailo modules imported successfully")
    except ImportError as e:
        log.error(f"\u274c Hailo module import failed: {e}")
        log.error("Hailo modules are required for TPU acceleration.")
        return False
    
    # Check for device on Linux
    log.info("\nStep 3: Checking for Hailo device...")
    if os.name == 'posix':
        if os.path.exists('/dev/hailo0'):
            log.info("\u2705 Hailo device found at /dev/hailo0")
        else:
            log.error("\u274c Hailo device not found at /dev/hailo0")
            return False
    else:
        log.info("Skipping device check on Windows")
    
    # Try to initialize Hailo device
    log.info("\nStep 4: Initializing Hailo device...")
    try:
        import hailort
        device = hailort.Device()
        device_id = device.device_id
        log.info(f"\u2705 Successfully initialized Hailo device: {device_id}")
    except Exception as e:
        log.error(f"\u274c Failed to initialize Hailo device: {e}")
        return False
    
    # Check OCR configuration
    log.info("\nStep 5: Checking OCR configuration...")
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'ocr_config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        tpu_enabled = config.get('use_hailo_tpu', False)
        log.info(f"\u2705 OCR configuration loaded: use_hailo_tpu = {tpu_enabled}")
        
        if not tpu_enabled:
            log.warning("\u26a0\ufe0f TPU is not enabled in the configuration")
            return False
        
        ocr_model_path = config.get('deep_learning', {}).get('hailo_ocr_model_path')
        detector_model_path = config.get('deep_learning', {}).get('hailo_detector_model_path')
        
        if ocr_model_path:
            full_ocr_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ocr_model_path)
            if os.path.exists(full_ocr_path):
                log.info(f"\u2705 OCR model found: {ocr_model_path}")
            else:
                log.error(f"\u274c OCR model not found: {full_ocr_path}")
                return False
        else:
            log.error("\u274c No OCR model path specified in configuration")
            return False
        
        if detector_model_path:
            full_detector_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), detector_model_path)
            if os.path.exists(full_detector_path):
                log.info(f"\u2705 Detector model found: {detector_model_path}")
            else:
                log.error(f"\u274c Detector model not found: {full_detector_path}")
                return False
    except Exception as e:
        log.error(f"\u274c Failed to load OCR configuration: {e}")
        return False
    
    # Try to load a model to verify Hailo TPU is working
    log.info("\nStep 6: Testing model loading...")
    try:
        # Get model path
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                detector_model_path)
        
        # Load model onto device
        log.info(f"Loading model: {model_path}")
        network = device.load_model(model_path)
        log.info("\u2705 Successfully loaded model onto Hailo TPU")
        
        # Get model info
        info = network.get_info()
        log.info(f"Model info: {info}")
        
        # Release resources
        del network
        del device
        
        log.info("\u2705 Model test successful - Hailo TPU is operational")
    except Exception as e:
        log.error(f"\u274c Failed to load model onto Hailo TPU: {e}")
        return False
    
    # Success!
    log.info("\n" + "="*60)
    log.info("\u2705 ALL TESTS PASSED - HAILO TPU IS FULLY OPERATIONAL")
    log.info("="*60)
    
    # Print instructions for fixing the web UI
    log.info("\nTo fix the web UI display, ensure the following:")
    log.info("1. The ocr_routes.py file is correctly setting hailo_available to True when use_hailo_tpu is True")
    log.info("2. The ocr_settings.html template is correctly checking the hailo_available variable")
    log.info("3. The web server has been restarted after making changes")
    
    return True

if __name__ == "__main__":
    success = test_hailo_directly()
    sys.exit(0 if success else 1)
