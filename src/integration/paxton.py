
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Paxton access control integration for VisiGate system.

This module provides functionality to integrate with Paxton access control systems
using the Wiegand protocol for license plate data transmission.
"""

import logging
import time
from .wiegand import WiegandTransmitter

logger = logging.getLogger('VisiGate.integration.paxton')

class PaxtonIntegration:
    """
    Integration with Paxton access control systems.
    
    This class handles the communication between the VisiGate system and Paxton
    access control systems, using the Wiegand protocol to transmit license plate
    data to the Paxton controller.
    """
    
    def __init__(self, config):
        """
        Initialize the Paxton integration.
        
        Args:
            config (dict): Configuration dictionary with Paxton integration settings
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        
        if not self.enabled:
            logger.info("Paxton integration is disabled")
            return
        
        # Initialize Wiegand transmitter
        self.wiegand = WiegandTransmitter(config.get('wiegand', {}))
        
        logger.info("Paxton integration initialized")
    
    def process_license_plate(self, license_plate):
        """
        Process a detected license plate and send it to the Paxton system.
        
        Args:
            license_plate (str): License plate text
            
        Returns:
            bool: True if successfully processed, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Paxton integration disabled, not processing license plate {license_plate}")
            return False
        
        logger.info(f"Processing license plate for Paxton: {license_plate}")
        
        # Send license plate data via Wiegand protocol
        return self.wiegand.send_license_plate(license_plate)
    
    def cleanup(self):
        """
        Clean up resources.
        """
        if self.enabled:
            self.wiegand.cleanup()
            logger.info("Paxton integration resources cleaned up")
