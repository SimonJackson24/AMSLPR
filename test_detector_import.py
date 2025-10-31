#!/usr/bin/env python3
"""
Test script to verify LicensePlateDetector import and basic functionality.
"""

import sys
import os
sys.path.append('.')

# Mock tensorflow if it's not available
class MockTensorFlow:
    def __getattr__(self, name):
        raise ImportError("TensorFlow not available")

# Mock hailo_platform if not available
class MockHailoPlatform:
    def __getattr__(self, name):
        raise ImportError("Hailo platform not available")

# Patch imports
import builtins
original_import = builtins.__import__

def patched_import(name, *args, **kwargs):
    if name == 'tensorflow':
        raise ImportError('TensorFlow not available')
    elif name == 'hailo_platform':
        raise ImportError('Hailo platform not available')
    return original_import(name, *args, **kwargs)

builtins.__import__ = patched_import

try:
    from src.recognition.detector import LicensePlateDetector
    print("✓ LicensePlateDetector import successful")

    # Test basic instantiation
    config = {
        'camera_id': 0,
        'mock_mode': True,  # Use mock mode to avoid camera issues
        'use_onvif': False
    }

    detector = LicensePlateDetector(config)
    print("✓ LicensePlateDetector instantiation successful")

    print("✓ All tests passed!")

except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()

finally:
    builtins.__import__ = original_import