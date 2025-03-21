# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

import os
import json
import logging
import sys
import argparse
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
    
    # Check for available Hailo models
    models_dir = project_root / 'models'
    models_dir.mkdir(exist_ok=True)
    
    # Look for specific Hailo models
    lpr_model_path = None
    detector_model_path = None
    
    # Check for LPRNet model
    lprnet_candidates = list(models_dir.glob("*lprnet*.hef"))
    if lprnet_candidates:
        lpr_model_path = f"models/{lprnet_candidates[0].name}"
        logger.info(f"Found LPRNet model: {lpr_model_path}")
    else:
        logger.warning("No LPRNet model found. OCR may not work correctly.")
        lpr_model_path = "models/lprnet_vehicle_license_recognition.hef"  # Default path
    
    # Check for license plate detector models
    yolo_candidates = list(models_dir.glob("*yolov5m*.hef"))
    tiny_yolo_candidates = list(models_dir.glob("*tiny_yolov4*.hef"))
    
    # Prioritize YOLOv5m over Tiny YOLOv4 if both are available
    if yolo_candidates:
        detector_model_path = f"models/{yolo_candidates[0].name}"
        logger.info(f"Found YOLOv5m detector model: {detector_model_path}")
    elif tiny_yolo_candidates:
        detector_model_path = f"models/{tiny_yolo_candidates[0].name}"
        logger.info(f"Found Tiny YOLOv4 detector model: {detector_model_path}")
    else:
        logger.warning("No detector model found. License plate detection may not work correctly.")
    
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
            "hailo_ocr_model_path": lpr_model_path,
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
    
    # Add detector model if found
    if detector_model_path:
        config["deep_learning"]["hailo_detector_model_path"] = detector_model_path
        config["deep_learning"]["use_hailo_detector"] = True
        logger.info(f"Enabled Hailo detector with model: {detector_model_path}")
    
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
                
            logger.info(f"Hailo TPU is available and working. Device ID: {device.device_id if hasattr(device, 'device_id') else 'Unknown'}")
            return True
        except Exception as e:
            logger.error(f"Hailo TPU is installed but not working: {e}")
            logger.error("Check if the device is properly connected and the driver is installed.")
            logger.error("You may need to run 'sudo ls -l /dev/hailo*' to check if the device is detected.")
            return False
    except ImportError:
        logger.error("Hailo TPU SDK is not installed")
        logger.error("Please install the Hailo SDK from the Hailo Developer Zone (https://hailo.ai/developer-zone/)")
        logger.error("Follow the instructions in docs/raspberry_pi_hailo_setup.md")
        return False

def main():
    """
    Main function.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Enable Hailo TPU in the OCR configuration")
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve configuration without prompting")
    args = parser.parse_args()
    
    # Check if Hailo TPU is available
    hailo_available = check_hailo_availability()
    
    if not hailo_available:
        logger.warning("Hailo TPU is not available. Configuration will be updated but may not work.")
        if not args.auto_approve:
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                logger.info("Aborted")
                return
        else:
            logger.info("Auto-approve enabled, continuing with configuration...")
    
    # Enable Hailo TPU in OCR configuration
    success = enable_hailo_tpu()
    
    if success:
        logger.info("Hailo TPU has been enabled in the OCR configuration")
        logger.info("Restart the AMSLPR service for changes to take effect")
        logger.info("Run 'sudo systemctl restart amslpr' to restart the service")
    else:
        logger.error("Failed to enable Hailo TPU")

if __name__ == '__main__':
    main()
