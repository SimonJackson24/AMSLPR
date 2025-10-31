#!/usr/bin/env python3
"""
Test script for the fixed LicensePlateDetector.
"""

import sys
import os
sys.path.append('.')

try:
    from src.recognition.detector_fixed import LicensePlateDetector
    print("✓ LicensePlateDetector import successful")

    # Test basic instantiation
    config = {
        'camera_id': 0,
        'mock_mode': True,  # Use mock mode to avoid camera issues
        'use_onvif': False
    }

    detector = LicensePlateDetector(config)
    print("✓ LicensePlateDetector instantiation successful")
    print(f"  OCR method: {detector.ocr_method}")
    print(f"  Mock mode: {detector.mock_mode}")

    # Test basic functionality
    import numpy as np
    # Create a dummy frame
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    plates = detector.detect_license_plates(dummy_frame)
    print(f"✓ License plate detection test: found {len(plates)} plates")

    print("✓ All tests passed!")

except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()