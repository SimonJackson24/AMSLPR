#!/usr/bin/env python3
"""
Mock License Plate Detector for AMSLPR

This module provides a mock implementation of the LicensePlateDetector class
for testing and development purposes when the required dependencies (like TensorFlow)
are not available.
"""

import os
import json
import logging
import random
import string
from datetime import datetime

logger = logging.getLogger('AMSLPR.recognition.mock_detector')

class MockLicensePlateDetector:
    """Mock implementation of the LicensePlateDetector class."""
    
    def __init__(self, recognition_config=None, ocr_config=None):
        """Initialize the mock detector."""
        self.recognition_config = recognition_config or {}
        self.ocr_config = ocr_config or {}
        self.reload_requested = False
        logger.info("Initialized MockLicensePlateDetector")
    
    def process_image(self, image_path):
        """Process an image and return a mock license plate."""
        logger.info(f"Processing image: {image_path}")
        
        # Generate a random license plate
        plate_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        confidence = random.uniform(0.7, 0.95)
        
        logger.info(f"Mock detected plate: {plate_text} (confidence: {confidence:.2f})")
        return plate_text, confidence
    
    def process_frame(self, frame):
        """Process a frame and return a mock license plate."""
        logger.info("Processing frame")
        
        # Generate a random license plate
        plate_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        confidence = random.uniform(0.7, 0.95)
        
        logger.info(f"Mock detected plate: {plate_text} (confidence: {confidence:.2f})")
        return plate_text, confidence
    
    def reload_ocr_config(self):
        """Reload the OCR configuration."""
        logger.info("Reloading OCR configuration")
        
        # Load OCR configuration from file
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ocr_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.ocr_config = json.load(f)
                logger.info("OCR configuration reloaded successfully")
                return True
            except Exception as e:
                logger.error(f"Error reloading OCR configuration: {e}")
                return False
        else:
            logger.error(f"OCR configuration file not found at {config_path}")
            return False
    
    def check_reload_requested(self):
        """Check if a reload has been requested."""
        if self.reload_requested:
            logger.info("Reload requested, reloading OCR configuration")
            self.reload_ocr_config()
            self.reload_requested = False
            return True
        return False
    
    def request_reload(self):
        """Request a reload of the OCR configuration."""
        logger.info("Reload requested")
        self.reload_requested = True
        return True
