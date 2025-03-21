
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import logging
import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available. Running in simulation mode.")

logger = logging.getLogger('AMSLPR.barrier')

class BarrierController:
    """
    Controller for the barrier/gate system.
    Uses GPIO pins to control the barrier.
    """
    
    def __init__(self, config):
        """
        Initialize the barrier controller.
        
        Args:
            config (dict): Configuration dictionary for barrier control
        """
        self.config = config
        self.gpio_pin = config.get('gpio_pin', 18)
        self.open_time = config.get('open_time', 5)
        self.safety_check = config.get('safety_check', True)
        
        # Initialize GPIO
        self._init_gpio()
        
        logger.info("Barrier controller initialized")
    
    def _init_gpio(self):
        """
        Initialize GPIO pins.
        """
        if not GPIO_AVAILABLE:
            logger.info("Running in simulation mode (GPIO not available)")
            return
        
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            
            # Set up GPIO pin as output
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            
            # Ensure barrier is closed initially
            GPIO.output(self.gpio_pin, GPIO.LOW)
            
            logger.info(f"GPIO pin {self.gpio_pin} initialized for barrier control")
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            raise
    
    def open_barrier(self):
        """
        Open the barrier.
        """
        if not GPIO_AVAILABLE:
            logger.info("Simulation: Opening barrier")
            time.sleep(self.open_time)
            logger.info("Simulation: Closing barrier")
            return
        
        try:
            # Perform safety check if enabled
            if self.safety_check and not self._safety_check():
                logger.warning("Safety check failed. Not opening barrier.")
                return False
            
            # Open barrier
            logger.info("Opening barrier")
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            
            # Wait for specified time
            time.sleep(self.open_time)
            
            # Close barrier
            logger.info("Closing barrier")
            GPIO.output(self.gpio_pin, GPIO.LOW)
            
            return True
        except Exception as e:
            logger.error(f"Error controlling barrier: {e}")
            return False
    
    def _safety_check(self):
        """
        Perform safety check before opening barrier.
        In a real implementation, this would check sensors to ensure it's safe to open.
        
        Returns:
            bool: True if safe to open, False otherwise
        """
        # In a real implementation, this would check sensors
        # For this example, we'll always return True
        return True
    
    def cleanup(self):
        """
        Clean up GPIO resources.
        """
        if GPIO_AVAILABLE:
            GPIO.cleanup(self.gpio_pin)
            logger.info("GPIO resources cleaned up")
