#!/usr/bin/env python3
"""
Security utilities for AMSLPR system.

This module provides functionality for secure credential storage and management.
"""

import os
import base64
import json
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Manage secure storage and retrieval of credentials.
    """
    
    def __init__(self, key_file=None, salt=None):
        """
        Initialize the credential manager.
        
        Args:
            key_file (str): Path to the key file
            salt (bytes): Salt for key derivation
        """
        self.key_file = key_file or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'crypto.key')
        self.salt = salt or b'AMSLPR_SALT_VALUE'  # Default salt, should be overridden in production
        self.fernet = None
        
        # Initialize the encryption key
        self._init_key()
    
    def _init_key(self):
        """
        Initialize the encryption key.
        """
        try:
            # Check if key file exists
            if os.path.exists(self.key_file):
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
                
                # Save key to file with restricted permissions
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                
                # Set file permissions to be readable only by owner
                os.chmod(self.key_file, 0o600)
            
            # Initialize Fernet cipher
            self.fernet = Fernet(key)
            
            logger.info("Encryption key initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing encryption key: {e}")
            raise
    
    def encrypt_credentials(self, credentials):
        """
        Encrypt credentials.
        
        Args:
            credentials (dict): Dictionary containing credentials
            
        Returns:
            str: Encrypted credentials as a base64-encoded string
        """
        if not self.fernet:
            raise ValueError("Encryption key not initialized")
        
        try:
            # Convert credentials to JSON string
            credentials_json = json.dumps(credentials)
            
            # Encrypt credentials
            encrypted_data = self.fernet.encrypt(credentials_json.encode('utf-8'))
            
            # Return base64-encoded encrypted data
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting credentials: {e}")
            raise
    
    def decrypt_credentials(self, encrypted_data):
        """
        Decrypt credentials.
        
        Args:
            encrypted_data (str): Base64-encoded encrypted credentials
            
        Returns:
            dict: Decrypted credentials as a dictionary
        """
        if not self.fernet:
            raise ValueError("Encryption key not initialized")
        
        try:
            # Decode base64-encoded encrypted data
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Decrypt data
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            
            # Parse JSON string to dictionary
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error decrypting credentials: {e}")
            raise
    
    def derive_key_from_password(self, password):
        """
        Derive a key from a password using PBKDF2.
        
        Args:
            password (str): Password to derive key from
            
        Returns:
            bytes: Derived key
        """
        try:
            # Convert password to bytes
            password_bytes = password.encode('utf-8')
            
            # Create key derivation function
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            
            # Derive key
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            
            return key
        except Exception as e:
            logger.error(f"Error deriving key from password: {e}")
            raise
    
    def set_key_from_password(self, password):
        """
        Set the encryption key from a password.
        
        Args:
            password (str): Password to derive key from
        """
        try:
            # Derive key from password
            key = self.derive_key_from_password(password)
            
            # Initialize Fernet cipher with derived key
            self.fernet = Fernet(key)
            
            logger.info("Encryption key set from password")
        except Exception as e:
            logger.error(f"Error setting key from password: {e}")
            raise
    
    def encrypt_value(self, value):
        """
        Encrypt a single value.
        
        Args:
            value (str): Value to encrypt
            
        Returns:
            str: Encrypted value as a base64-encoded string
        """
        if not self.fernet:
            raise ValueError("Encryption key not initialized")
        
        try:
            # Encrypt value
            encrypted_data = self.fernet.encrypt(value.encode('utf-8'))
            
            # Return base64-encoded encrypted data
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting value: {e}")
            raise
    
    def decrypt_value(self, encrypted_value):
        """
        Decrypt a single value.
        
        Args:
            encrypted_value (str): Base64-encoded encrypted value
            
        Returns:
            str: Decrypted value
        """
        if not self.fernet:
            raise ValueError("Encryption key not initialized")
        
        try:
            # Decode base64-encoded encrypted data
            encrypted_bytes = base64.b64decode(encrypted_value)
            
            # Decrypt data
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            
            # Return decrypted value as string
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting value: {e}")
            raise
