#!/usr/bin/env python3
"""
Wiegand protocol integration for AMSLPR system.

This module provides functionality to send license plate data to Paxton access control systems
using the Wiegand 26-bit protocol via GPIO pins on the Raspberry Pi.
"""

import logging
import time
import threading

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available. Running in simulation mode.")

logger = logging.getLogger('AMSLPR.integration.wiegand')

class WiegandTransmitter:
    """
    Implements Wiegand 26-bit protocol transmission for Paxton integration.
    
    The Wiegand 26-bit format consists of:
    - 1 even parity bit (calculated from the first 12 bits of the card number)
    - 8 bits for the facility code (0-255)
    - 16 bits for the card number (0-65535)
    - 1 odd parity bit (calculated from the last 12 bits of the card number)
    """
    
    def __init__(self, config):
        """
        Initialize the Wiegand transmitter.
        
        Args:
            config (dict): Configuration dictionary with Wiegand settings
        """
        self.config = config
        self.data0_pin = config.get('data0_pin', 23)  # Default GPIO pin for DATA0
        self.data1_pin = config.get('data1_pin', 24)  # Default GPIO pin for DATA1
        self.pulse_width = config.get('pulse_width', 0.0001)  # 100 microseconds
        self.pulse_interval = config.get('pulse_interval', 0.002)  # 2 milliseconds
        self.facility_code = config.get('facility_code', 1)  # Default facility code
        
        # Initialize GPIO pins
        self._init_gpio()
        
        logger.info("Wiegand transmitter initialized")
    
    def _init_gpio(self):
        """
        Initialize GPIO pins for Wiegand transmission.
        """
        if not GPIO_AVAILABLE:
            logger.info("Running in simulation mode (GPIO not available)")
            return
        
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            
            # Set up GPIO pins as outputs
            GPIO.setup(self.data0_pin, GPIO.OUT)
            GPIO.setup(self.data1_pin, GPIO.OUT)
            
            # Set both lines high (idle state)
            GPIO.output(self.data0_pin, GPIO.HIGH)
            GPIO.output(self.data1_pin, GPIO.HIGH)
            
            logger.info(f"GPIO pins initialized: DATA0={self.data0_pin}, DATA1={self.data1_pin}")
        except Exception as e:
            logger.error(f"Error initializing GPIO for Wiegand: {e}")
            raise
    
    def _calculate_parity(self, data, bits, even=True):
        """
        Calculate parity bit for the given data.
        
        Args:
            data (int): Data to calculate parity for
            bits (int): Number of bits to consider
            even (bool): True for even parity, False for odd parity
            
        Returns:
            int: Parity bit (0 or 1)
        """
        ones_count = 0
        for i in range(bits):
            if (data >> i) & 1:
                ones_count += 1
        
        if even:  # Even parity
            return 0 if (ones_count % 2 == 0) else 1
        else:  # Odd parity
            return 1 if (ones_count % 2 == 0) else 0
    
    def _send_bit(self, bit):
        """
        Send a single bit using the Wiegand protocol.
        
        Args:
            bit (int): Bit to send (0 or 1)
        """
        if not GPIO_AVAILABLE:
            logger.debug(f"Simulation: Sending bit {bit}")
            time.sleep(self.pulse_width + self.pulse_interval)
            return
        
        try:
            if bit == 0:
                # Send 0: Pulse DATA0 line
                GPIO.output(self.data0_pin, GPIO.LOW)
                time.sleep(self.pulse_width)
                GPIO.output(self.data0_pin, GPIO.HIGH)
            else:
                # Send 1: Pulse DATA1 line
                GPIO.output(self.data1_pin, GPIO.LOW)
                time.sleep(self.pulse_width)
                GPIO.output(self.data1_pin, GPIO.HIGH)
            
            # Wait between bits
            time.sleep(self.pulse_interval)
        except Exception as e:
            logger.error(f"Error sending Wiegand bit: {e}")
    
    def _license_to_card_number(self, license_plate):
        """
        Convert license plate string to a numeric card number.
        This is a simple hash function that produces a 16-bit number.
        
        Args:
            license_plate (str): License plate text
            
        Returns:
            int: Card number (0-65535)
        """
        # Simple hash function for demonstration
        # In a real implementation, you might want a more sophisticated mapping
        hash_value = 0
        for char in license_plate:
            hash_value = (hash_value * 31 + ord(char)) & 0xFFFF
        
        return hash_value
    
    def send_license_plate(self, license_plate):
        """
        Send a license plate as a Wiegand 26-bit code.
        
        Args:
            license_plate (str): License plate text
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert license plate to card number
            card_number = self._license_to_card_number(license_plate)
            
            # Ensure facility code and card number are within valid ranges
            facility_code = self.facility_code & 0xFF  # 8 bits (0-255)
            card_number = card_number & 0xFFFF  # 16 bits (0-65535)
            
            # Calculate parity bits
            # Even parity for first 12 bits (facility code + 4 MSB of card number)
            first_12_bits = (facility_code << 4) | ((card_number >> 12) & 0xF)
            even_parity = self._calculate_parity(first_12_bits, 12, even=True)
            
            # Odd parity for last 12 bits (12 LSB of card number)
            last_12_bits = card_number & 0xFFF
            odd_parity = self._calculate_parity(last_12_bits, 12, even=False)
            
            logger.info(f"Sending license plate {license_plate} as Wiegand 26-bit code: "
                       f"FC={facility_code}, CN={card_number}, EP={even_parity}, OP={odd_parity}")
            
            # Send the 26-bit Wiegand code
            # First bit: even parity
            self._send_bit(even_parity)
            
            # Next 8 bits: facility code (MSB first)
            for i in range(7, -1, -1):
                self._send_bit((facility_code >> i) & 1)
            
            # Next 16 bits: card number (MSB first)
            for i in range(15, -1, -1):
                self._send_bit((card_number >> i) & 1)
            
            # Last bit: odd parity
            self._send_bit(odd_parity)
            
            logger.info(f"Successfully sent license plate {license_plate} via Wiegand protocol")
            return True
            
        except Exception as e:
            logger.error(f"Error sending license plate via Wiegand: {e}")
            return False
    
    def cleanup(self):
        """
        Clean up GPIO resources.
        """
        if GPIO_AVAILABLE:
            GPIO.cleanup([self.data0_pin, self.data1_pin])
            logger.info("Wiegand GPIO resources cleaned up")
