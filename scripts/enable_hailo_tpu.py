#!/usr/bin/env python3

import os
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AMSLPR.enable_hailo')

# Get project root
project_root = Path(__file__).parent.parent

def enable_hailo_tpu():
    """
    Enable Hailo TPU in the OCR configuration.
    """
    config_path = project_root / 'config' / 'ocr_config.json'
    
    # Create config directory if it doesn't exist
    config_dir = config_path.parent
    config_dir.mkdir(exist_ok=True)
    
    # Load existing config or create a new one
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info("Loaded existing OCR configuration")
        except Exception as e:
            logger.error(f"Failed to load OCR configuration: {e}")
            config = {}
    else:
        logger.info("Creating new OCR configuration")
        config = {}
    
    # Update configuration for Hailo TPU
    config.update({
        "ocr_method": "hybrid",  # Use both Tesseract and deep learning
        "use_hailo_tpu": True,    # Enable Hailo TPU
        "confidence_threshold": 0.7,
        "tesseract_config": {
            "psm_mode": 7,
            "oem_mode": 1,
            "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        },
        "deep_learning": {
            "model_type": "crnn",
            "input_width": 100,
            "input_height": 32,
            "tf_ocr_model_path": "models/ocr_crnn.h5",
            "hailo_ocr_model_path": "models/ocr_crnn.hef",
            "char_map_path": "models/char_map.json"
        },
        "preprocessing": {
            "resize_factor": 2.0,
            "apply_contrast_enhancement": True,
            "apply_noise_reduction": True,
            "apply_perspective_correction": True
        },
        "postprocessing": {
            "apply_regex_validation": True,
            "min_plate_length": 4,
            "max_plate_length": 10,
            "common_substitutions": {
                "0": "O",
                "1": "I",
                "5": "S",
                "8": "B"
            }
        },
        "regional_settings": {
            "country_code": "US",
            "plate_format": "[A-Z0-9]{3,8}"
        }
    })
    
    # Save configuration
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved OCR configuration with Hailo TPU enabled to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save OCR configuration: {e}")
        return False

def check_hailo_availability():
    """
    Check if Hailo TPU is available on the system.
    """
    try:
        import hailo_platform
        
        try:
            # Try to initialize Hailo device
            device = hailo_platform.HailoDevice()
            logger.info("Hailo TPU is available and working")
            return True
        except Exception as e:
            logger.error(f"Hailo TPU is installed but not working: {e}")
            return False
    except ImportError:
        logger.error("Hailo TPU SDK is not installed")
        return False

def main():
    """
    Main function.
    """
    # Check if Hailo TPU is available
    hailo_available = check_hailo_availability()
    
    if not hailo_available:
        logger.warning("Hailo TPU is not available. Configuration will be updated but may not work.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            logger.info("Aborted")
            return
    
    # Enable Hailo TPU in OCR configuration
    success = enable_hailo_tpu()
    
    if success:
        logger.info("Hailo TPU has been enabled in the OCR configuration")
        logger.info("Restart the AMSLPR service for changes to take effect")
    else:
        logger.error("Failed to enable Hailo TPU")

if __name__ == '__main__':
    main()
