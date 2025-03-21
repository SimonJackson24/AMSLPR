# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Mock Hailo TPU Module for AMSLPR

This module provides a mock implementation of the Hailo TPU SDK for
development and testing without requiring actual Hailo hardware.
It can be installed as hailort to satisfy import dependencies.
"""

import os
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger('AMSLPR.recognition.mock_hailo')

class Device:
    """Mock implementation of Hailo device for development/testing"""
    
    def __init__(self):
        self.device_id = "MOCK-HAILO-DEV-001"
        logger.info(f"Initialized mock Hailo device: {self.device_id}")
        
    def close(self):
        logger.info("Closed mock Hailo device")

class HailoRuntime:
    """Mock implementation of Hailo runtime for development/testing"""
    
    def __init__(self, model_path):
        self.model_path = model_path
        logger.info(f"Initialized mock Hailo runtime with model: {model_path}")
        
    def infer(self, input_data):
        """Mock inference method that returns random data"""
        # Return random detection/recognition results
        if "lprnet" in str(self.model_path).lower():
            # For LPR model, return random characters
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            plate = ''.join(np.random.choice(list(chars)) for _ in range(7))
            return plate, 0.95
        else:
            # For detector model, return a mock detection box
            h, w = input_data.shape[:2] if hasattr(input_data, 'shape') else (720, 1280)
            x1 = np.random.randint(0, w//2)
            y1 = np.random.randint(0, h//2)
            x2 = np.random.randint(w//2, w)
            y2 = np.random.randint(h//2, h)
            return [[x1, y1, x2, y2, 0.93, 0]]  # Format: [x1, y1, x2, y2, confidence, class_id]
    
    def close(self):
        logger.info(f"Closed mock Hailo runtime for model: {self.model_path}")

def load_and_run(model_path):
    """Mock implementation of load_and_run for development/testing"""
    logger.info(f"Loading and running mock Hailo model: {model_path}")
    return HailoRuntime(model_path)

# Module version for compatibility checks
__version__ = "4.20.0-mock"