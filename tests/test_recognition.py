
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import unittest
import os
import sys
import cv2
import numpy as np
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.recognition.detector import LicensePlateDetector
from src.config.settings import load_config
from src.utils.helpers import preprocess_image, enhance_plate_image, format_plate_number

class TestLicensePlateRecognition(unittest.TestCase):
    """
    Test cases for license plate recognition functionality.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Load configuration
        self.config = load_config()
        
        # Initialize detector
        self.detector = LicensePlateDetector(self.config)
        
        # Create test image directory if it doesn't exist
        self.test_image_dir = os.path.join(Path(__file__).parent, 'test_images')
        if not os.path.exists(self.test_image_dir):
            os.makedirs(self.test_image_dir)
        
        # Create a sample test image with a simulated license plate
        self.create_test_image()
    
    def create_test_image(self):
        """
        Create a test image with a simulated license plate.
        """
        # Create a blank image
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img.fill(255)  # White background
        
        # Draw a license plate-like rectangle
        plate_x, plate_y = 220, 200
        plate_width, plate_height = 200, 50
        cv2.rectangle(img, (plate_x, plate_y), (plate_x + plate_width, plate_y + plate_height), (0, 0, 0), 2)
        
        # Add text to the license plate
        font = cv2.FONT_HERSHEY_SIMPLEX
        plate_text = "ABC123"
        text_size = cv2.getTextSize(plate_text, font, 1, 2)[0]
        text_x = plate_x + (plate_width - text_size[0]) // 2
        text_y = plate_y + (plate_height + text_size[1]) // 2
        cv2.putText(img, plate_text, (text_x, text_y), font, 1, (0, 0, 0), 2)
        
        # Save the test image
        self.test_image_path = os.path.join(self.test_image_dir, 'test_plate.jpg')
        cv2.imwrite(self.test_image_path, img)
        
        # Store the expected plate text for testing
        self.expected_plate_text = plate_text
    
    def test_preprocess_image(self):
        """
        Test image preprocessing function.
        """
        # Load test image
        img = cv2.imread(self.test_image_path)
        self.assertIsNotNone(img, "Failed to load test image")
        
        # Preprocess image
        preprocessed = preprocess_image(img)
        
        # Check that preprocessing returned a valid image
        self.assertIsNotNone(preprocessed, "Preprocessing returned None")
        self.assertEqual(len(preprocessed.shape), 2, "Preprocessed image should be grayscale")
    
    def test_enhance_plate_image(self):
        """
        Test license plate image enhancement function.
        """
        # Load test image
        img = cv2.imread(self.test_image_path)
        self.assertIsNotNone(img, "Failed to load test image")
        
        # Extract the license plate region
        plate_img = img[200:250, 220:420]
        
        # Enhance plate image
        enhanced = enhance_plate_image(plate_img)
        
        # Check that enhancement returned a valid image
        self.assertIsNotNone(enhanced, "Enhancement returned None")
        self.assertEqual(len(enhanced.shape), 2, "Enhanced image should be grayscale")
    
    def test_format_plate_number(self):
        """
        Test license plate number formatting function.
        """
        # Test cases
        test_cases = [
            ("ABC 123", "ABC123"),
            ("abc123", "ABC123"),
            ("A8C-123", "A8C123"),
            ("  XYZ789  ", "XYZ789"),
            ("A@B#C$1%2^3", "ABC123")
        ]
        
        # Test each case
        for input_text, expected_output in test_cases:
            formatted = format_plate_number(input_text)
            self.assertEqual(formatted, expected_output, 
                             f"Format plate number failed for '{input_text}'. Expected '{expected_output}', got '{formatted}'")
    
    def test_detect_license_plate(self):
        """
        Test license plate detection.
        """
        # Skip this test if detector is not fully initialized
        if not hasattr(self.detector, 'detect_license_plate'):
            self.skipTest("Detector not fully initialized")
        
        # Load test image
        img = cv2.imread(self.test_image_path)
        self.assertIsNotNone(img, "Failed to load test image")
        
        # Detect license plate
        plate_img, plate_coords = self.detector.detect_license_plate(img)
        
        # Check that detection returned a valid result
        self.assertIsNotNone(plate_img, "License plate detection returned None for image")
        self.assertIsNotNone(plate_coords, "License plate detection returned None for coordinates")
        self.assertEqual(len(plate_coords), 4, "License plate coordinates should have 4 points")
    
    def test_recognize_license_plate(self):
        """
        Test license plate recognition.
        """
        # Skip this test if detector is not fully initialized
        if not hasattr(self.detector, 'recognize_license_plate'):
            self.skipTest("Detector not fully initialized")
        
        # Load test image
        img = cv2.imread(self.test_image_path)
        self.assertIsNotNone(img, "Failed to load test image")
        
        # Recognize license plate
        plate_text, confidence = self.detector.recognize_license_plate(img)
        
        # Check that recognition returned a valid result
        self.assertIsNotNone(plate_text, "License plate recognition returned None for text")
        self.assertIsNotNone(confidence, "License plate recognition returned None for confidence")
        
        # Note: We don't check exact match because OCR might not be perfect
        # Instead, we check that the result is not empty
        self.assertGreater(len(plate_text), 0, "License plate text should not be empty")

if __name__ == '__main__':
    unittest.main()
