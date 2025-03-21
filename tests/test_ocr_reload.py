
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Test script for OCR configuration reloading.

This script tests the OCR configuration reloading functionality by:
1. Loading the current OCR configuration
2. Making a change to the configuration
3. Saving the configuration
4. Triggering a reload
5. Verifying that the change was applied
"""

import os
import sys
import json
import time
import logging
import argparse
import requests

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from recognition.detector import LicensePlateDetector
    DETECTOR_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger('test_ocr_reload')
    logger.warning(f"Could not import LicensePlateDetector: {e}")
    logger.warning("Some tests will be skipped")
    DETECTOR_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_ocr_reload')

def test_direct_reload():
    """Test reloading the OCR configuration directly."""
    if not DETECTOR_AVAILABLE:
        logger.warning("Skipping direct reload test: LicensePlateDetector not available")
        return
        
    logger.info("Testing direct OCR configuration reloading...")
    
    # Load the current OCR configuration
    config_path = os.path.join('config', 'ocr_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Create a backup of the original configuration
    backup_config = config.copy()
    
    try:
        # Create a detector with the current configuration
        detector = LicensePlateDetector({'use_camera': False}, config)
        
        # Modify the configuration
        original_threshold = config['postprocessing']['confidence_threshold']
        new_threshold = 0.8 if original_threshold != 0.8 else 0.7
        
        config['postprocessing']['confidence_threshold'] = new_threshold
        
        # Save the modified configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Changed confidence threshold from {original_threshold} to {new_threshold}")
        
        # Reload the configuration
        success = detector.reload_ocr_config()
        
        if success:
            logger.info("OCR configuration reloaded successfully")
            
            # Verify that the change was applied
            if detector.ocr_config['postprocessing']['confidence_threshold'] == new_threshold:
                logger.info(" Test passed: Configuration change was applied")
            else:
                logger.error(" Test failed: Configuration change was not applied")
        else:
            logger.error(" Test failed: Failed to reload OCR configuration")
    
    finally:
        # Restore the original configuration
        with open(config_path, 'w') as f:
            json.dump(backup_config, f, indent=4)
        logger.info("Restored original configuration")

def test_api_reload(base_url='http://localhost:5000'):
    """Test reloading the OCR configuration via the API."""
    logger.info(f"Testing OCR configuration reloading via API at {base_url}...")
    
    # Get the current OCR configuration
    try:
        # First, check if the server is running
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            if response.status_code == 404:
                # 404 is fine, it means the server is running but the root endpoint doesn't exist
                pass
        except requests.exceptions.ConnectionError:
            logger.error(f"\u274c Test failed: Could not connect to server at {base_url}")
            logger.error("Make sure the server is running and accessible")
            return
        except requests.exceptions.Timeout:
            logger.error(f"\u274c Test failed: Connection to {base_url} timed out")
            logger.error("Make sure the server is running and accessible")
            return
        
        # Now test the OCR API endpoints
        response = requests.get(f"{base_url}/ocr/api/config")
        response.raise_for_status()
        config = response.json()
        
        # Modify the configuration
        original_threshold = config['postprocessing']['confidence_threshold']
        new_threshold = 0.8 if original_threshold != 0.8 else 0.7
        
        config['postprocessing']['confidence_threshold'] = new_threshold
        
        # Update the configuration
        response = requests.post(f"{base_url}/ocr/api/config", json=config)
        response.raise_for_status()
        update_result = response.json()
        
        if update_result['success']:
            logger.info(f"Changed confidence threshold from {original_threshold} to {new_threshold}")
            logger.info("OCR configuration updated successfully")
            
            # Get the updated configuration
            response = requests.get(f"{base_url}/ocr/api/config")
            response.raise_for_status()
            updated_config = response.json()
            
            # Verify that the change was applied
            if updated_config['postprocessing']['confidence_threshold'] == new_threshold:
                logger.info(" Test passed: Configuration change was applied")
            else:
                logger.error(" Test failed: Configuration change was not applied")
        else:
            logger.error(f" Test failed: Failed to update OCR configuration: {update_result['message']}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f" Test failed: API request failed: {e}")
    
    # Test the explicit reload endpoint
    try:
        response = requests.post(f"{base_url}/ocr/api/reload")
        response.raise_for_status()
        reload_result = response.json()
        
        if reload_result['success']:
            logger.info("OCR configuration reloaded successfully via explicit reload endpoint")
        else:
            logger.error(f" Test failed: Failed to reload OCR configuration: {reload_result['message']}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f" Test failed: API request failed: {e}")

def main():
    parser = argparse.ArgumentParser(description='Test OCR configuration reloading')
    parser.add_argument('--api', action='store_true', help='Test reloading via API')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL for API tests')
    args = parser.parse_args()
    
    if args.api:
        test_api_reload(args.url)
    else:
        test_direct_reload()

if __name__ == '__main__':
    main()
