
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
OCR Setup and Testing Script for VisiGate

This script helps administrators set up and test the OCR system, including the Hailo TPU integration.
It performs the following tasks:
1. Checks for required dependencies
2. Verifies the OCR configuration
3. Tests the OCR system with sample images
4. Provides guidance for optimizing the OCR configuration
"""

import os
import sys
import json
import time
import logging
import argparse
import shutil
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('setup_ocr')

# Add the src directory to the Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

# Define paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_DIR = os.path.join(ROOT_DIR, 'config')
MODELS_DIR = os.path.join(ROOT_DIR, 'models')
SAMPLE_IMAGES_DIR = os.path.join(ROOT_DIR, 'data', 'sample_images')
OCR_CONFIG_PATH = os.path.join(CONFIG_DIR, 'ocr_config.json')

# Required Python packages
REQUIRED_PACKAGES = [
    'numpy',
    'opencv-python',
    'pytesseract',
    'tensorflow',
    'pillow'
]

# Optional packages
OPTIONAL_PACKAGES = [
    'hailoRT'
]

def check_dependencies():
    """Check if all required dependencies are installed."""
    logger.info("Checking dependencies...")
    missing_packages = []
    optional_missing = []
    
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} is not installed")
    
    for package in OPTIONAL_PACKAGES:
        try:
            __import__(package)
            logger.info(f"✓ {package} is installed (optional)")
        except ImportError:
            optional_missing.append(package)
            logger.warning(f"! {package} is not installed (optional)")
    
    # Check for Tesseract OCR
    tesseract_path = shutil.which('tesseract')
    if tesseract_path:
        logger.info(f"✓ Tesseract OCR is installed at {tesseract_path}")
        # Get version
        try:
            version = subprocess.check_output([tesseract_path, '--version'], text=True)
            logger.info(f"  Tesseract version: {version.splitlines()[0]}")
        except subprocess.SubprocessError:
            logger.warning("  Could not determine Tesseract version")
    else:
        missing_packages.append('tesseract-ocr')
        logger.error("✗ Tesseract OCR is not installed")
    
    # Check for Hailo TPU
    hailo_available = False
    if 'hailoRT' not in optional_missing:
        try:
            import hailoRT
            device_count = hailoRT.get_device_count()
            if device_count > 0:
                logger.info(f"✓ Hailo TPU detected ({device_count} devices)")
                hailo_available = True
            else:
                logger.warning("! Hailo TPU driver installed but no devices detected")
        except Exception as e:
            logger.warning(f"! Error checking Hailo TPU: {e}")
    else:
        logger.warning("! Hailo TPU driver (hailoRT) not installed")
    
    if missing_packages:
        logger.error("The following required packages are missing:")
        for package in missing_packages:
            logger.error(f"  - {package}")
        logger.info("\nYou can install them with:")
        pip_packages = [p for p in missing_packages if p != 'tesseract-ocr']
        if pip_packages:
            logger.info(f"pip install {' '.join(pip_packages)}")
        if 'tesseract-ocr' in missing_packages:
            logger.info("sudo apt-get install tesseract-ocr")
        return False, hailo_available
    
    return True, hailo_available

def verify_ocr_config(hailo_available):
    """Verify the OCR configuration."""
    logger.info("\nVerifying OCR configuration...")
    
    # Check if config directory exists
    if not os.path.exists(CONFIG_DIR):
        logger.info(f"Creating config directory at {CONFIG_DIR}")
        os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Check if OCR config file exists
    if not os.path.exists(OCR_CONFIG_PATH):
        logger.info(f"OCR configuration file not found at {OCR_CONFIG_PATH}")
        logger.info("Creating default OCR configuration file")
        
        default_config = {
            "ocr_method": "tesseract",
            "use_hailo_tpu": hailo_available,
            "tesseract_config": {
                "psm_mode": 7,
                "oem_mode": 1,
                "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            },
            "deep_learning": {
                "model_type": "crnn",
                "input_width": 100,
                "input_height": 32
            },
            "preprocessing": {
                "resize_factor": 2.0,
                "apply_contrast_enhancement": True,
                "contrast_clip_limit": 2.0,
                "apply_noise_reduction": True,
                "noise_reduction_strength": 7,
                "apply_threshold": True,
                "threshold_method": "adaptive",
                "threshold_block_size": 11,
                "threshold_c": 2
            },
            "postprocessing": {
                "apply_regex_filter": True,
                "regex_pattern": "^[A-Z0-9]{3,8}$",
                "confidence_threshold": 0.7,
                "min_characters": 3,
                "max_characters": 8
            }
        }
        
        with open(OCR_CONFIG_PATH, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info(f"Created default OCR configuration at {OCR_CONFIG_PATH}")
    else:
        # Load and validate the configuration
        try:
            with open(OCR_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # Check for required fields
            required_fields = ['ocr_method', 'tesseract_config', 'preprocessing', 'postprocessing']
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                logger.warning(f"OCR configuration is missing required fields: {', '.join(missing_fields)}")
                logger.info("Consider recreating the configuration file")
            else:
                logger.info("OCR configuration file is valid")
                
                # Warn about Hailo TPU settings if not available
                if config.get('use_hailo_tpu', False) and not hailo_available:
                    logger.warning("OCR configuration has Hailo TPU enabled, but no Hailo TPU was detected")
                    logger.info("Consider disabling Hailo TPU in the configuration")
                
                # Warn about deep learning settings if Hailo TPU is enabled but deep learning is not used
                if config.get('use_hailo_tpu', False) and config.get('ocr_method') == 'tesseract':
                    logger.warning("OCR configuration has Hailo TPU enabled, but OCR method is set to 'tesseract'")
                    logger.info("Consider changing OCR method to 'deep_learning' or 'hybrid' to use Hailo TPU")
        
        except Exception as e:
            logger.error(f"Error validating OCR configuration: {e}")
            return False
    
    return True

def check_models():
    """Check if the required OCR models are available."""
    logger.info("\nChecking OCR models...")
    
    # Check if models directory exists
    if not os.path.exists(MODELS_DIR):
        logger.info(f"Creating models directory at {MODELS_DIR}")
        os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Check for deep learning models
    model_files = [
        'ocr_model.h5',
        'ocr_model.tflite',
        'ocr_model_hailo.hef'
    ]
    
    missing_models = []
    for model_file in model_files:
        model_path = os.path.join(MODELS_DIR, model_file)
        if os.path.exists(model_path):
            logger.info(f"✓ Found model: {model_file}")
        else:
            missing_models.append(model_file)
            logger.warning(f"! Missing model: {model_file}")
    
    if missing_models:
        logger.warning("Some OCR models are missing. This may affect deep learning OCR functionality.")
        logger.info("Run the model preparation script to download the required models:")
        logger.info("  python3 scripts/prepare_ocr_models.py")
        return False
    
    return True

def prepare_sample_images():
    """Prepare sample images for OCR testing."""
    logger.info("\nPreparing sample images for OCR testing...")
    
    # Check if sample images directory exists
    if not os.path.exists(SAMPLE_IMAGES_DIR):
        logger.info(f"Creating sample images directory at {SAMPLE_IMAGES_DIR}")
        os.makedirs(SAMPLE_IMAGES_DIR, exist_ok=True)
    
    # Check if there are any sample images
    sample_images = [f for f in os.listdir(SAMPLE_IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not sample_images:
        logger.warning("No sample images found for OCR testing")
        logger.info("Please add some license plate images to the sample images directory:")
        logger.info(f"  {SAMPLE_IMAGES_DIR}")
        return False
    
    logger.info(f"Found {len(sample_images)} sample images for OCR testing")
    return True

def test_ocr_system():
    """Test the OCR system with sample images."""
    logger.info("\nTesting OCR system with sample images...")
    
    try:
        # Import detector here to avoid import errors if dependencies are missing
        from recognition.detector import LicensePlateDetector
        
        # Load OCR configuration
        with open(OCR_CONFIG_PATH, 'r') as f:
            ocr_config = json.load(f)
        
        # Create detector
        detector_config = {
            'use_camera': False,
            'save_images': True,
            'image_save_path': os.path.join(ROOT_DIR, 'data', 'test_results')
        }
        
        detector = LicensePlateDetector(detector_config, ocr_config)
        
        # Test with sample images
        sample_images = [f for f in os.listdir(SAMPLE_IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not sample_images:
            logger.warning("No sample images found for OCR testing")
            return False
        
        results = []
        for image_file in sample_images:
            image_path = os.path.join(SAMPLE_IMAGES_DIR, image_file)
            logger.info(f"Testing with image: {image_file}")
            
            # Process the image
            start_time = time.time()
            plate_text, confidence = detector.process_image(image_path)
            processing_time = time.time() - start_time
            
            if plate_text:
                logger.info(f"  Detected plate: {plate_text} (confidence: {confidence:.2f}, time: {processing_time:.3f}s)")
                results.append({
                    'image': image_file,
                    'plate_text': plate_text,
                    'confidence': confidence,
                    'processing_time': processing_time
                })
            else:
                logger.warning(f"  No plate detected in {image_file}")
        
        # Summarize results
        if results:
            logger.info("\nOCR Testing Summary:")
            logger.info(f"Total images tested: {len(sample_images)}")
            logger.info(f"Successful detections: {len(results)}")
            logger.info(f"Detection rate: {len(results)/len(sample_images)*100:.1f}%")
            
            # Calculate average confidence and processing time
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            avg_time = sum(r['processing_time'] for r in results) / len(results)
            
            logger.info(f"Average confidence: {avg_confidence:.2f}")
            logger.info(f"Average processing time: {avg_time:.3f}s")
            
            return True
        else:
            logger.warning("No license plates were detected in any of the sample images")
            return False
    
    except ImportError as e:
        logger.error(f"Could not test OCR system: {e}")
        logger.error("Make sure all dependencies are installed")
        return False
    except Exception as e:
        logger.error(f"Error testing OCR system: {e}")
        return False

def provide_optimization_guidance(hailo_available):
    """Provide guidance for optimizing the OCR configuration."""
    logger.info("\nOCR Optimization Guidance:")
    
    logger.info("1. OCR Method Selection:")
    if hailo_available:
        logger.info("   - You have a Hailo TPU available. For best performance, use 'hybrid' OCR method.")
        logger.info("   - Enable 'use_hailo_tpu' in the configuration to utilize hardware acceleration.")
    else:
        logger.info("   - Without a Hailo TPU, 'tesseract' is the recommended OCR method.")
        logger.info("   - For better accuracy but slower processing, consider 'hybrid' method with CPU.")
    
    logger.info("\n2. Preprocessing Optimization:")
    logger.info("   - Increase 'resize_factor' for better accuracy on small plates (at the cost of speed).")
    logger.info("   - Enable 'apply_contrast_enhancement' for images with poor lighting conditions.")
    logger.info("   - Adjust 'noise_reduction_strength' based on image quality (higher for noisy images).")
    
    logger.info("\n3. Postprocessing Optimization:")
    logger.info("   - Set 'apply_regex_filter' to True to filter out invalid plate formats.")
    logger.info("   - Adjust 'regex_pattern' to match your region's license plate format.")
    logger.info("   - Lower 'confidence_threshold' to detect more plates (may increase false positives).")
    
    logger.info("\n4. Performance Considerations:")
    logger.info("   - For real-time processing, prioritize speed by using 'tesseract' method.")
    logger.info("   - For batch processing or higher accuracy, use 'hybrid' method.")
    logger.info("   - If using Hailo TPU, ensure the models are properly compiled for your device.")
    
    logger.info("\nYou can modify the OCR configuration through:")
    logger.info(f"1. Editing the configuration file directly: {OCR_CONFIG_PATH}")
    logger.info("2. Using the web interface: Navigate to OCR Settings in the admin dashboard")
    logger.info("3. Using the API: POST to /ocr/api/config endpoint")

def main():
    parser = argparse.ArgumentParser(description='OCR Setup and Testing Script for VisiGate')
    parser.add_argument('--skip-deps', action='store_true', help='Skip dependency checking')
    parser.add_argument('--skip-config', action='store_true', help='Skip configuration verification')
    parser.add_argument('--skip-models', action='store_true', help='Skip model checking')
    parser.add_argument('--skip-test', action='store_true', help='Skip OCR testing')
    args = parser.parse_args()
    
    logger.info("=== VisiGate OCR Setup and Testing Script ===")
    
    # Check dependencies
    deps_ok = True
    hailo_available = False
    if not args.skip_deps:
        deps_ok, hailo_available = check_dependencies()
    
    # Verify OCR configuration
    config_ok = True
    if not args.skip_config:
        config_ok = verify_ocr_config(hailo_available)
    
    # Check models
    models_ok = True
    if not args.skip_models:
        models_ok = check_models()
    
    # Prepare sample images
    images_ok = prepare_sample_images()
    
    # Test OCR system
    test_ok = True
    if not args.skip_test and deps_ok and config_ok and models_ok and images_ok:
        test_ok = test_ocr_system()
    elif not args.skip_test:
        logger.warning("Skipping OCR testing due to previous errors")
    
    # Provide optimization guidance
    provide_optimization_guidance(hailo_available)
    
    # Final status
    logger.info("\n=== Setup and Testing Complete ===")
    if deps_ok and config_ok and models_ok and (args.skip_test or test_ok):
        logger.info("✓ OCR system is ready to use")
    else:
        logger.warning("! OCR system setup is incomplete. Please address the issues above.")

if __name__ == '__main__':
    main()
