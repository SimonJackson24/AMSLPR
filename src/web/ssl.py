
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
SSL/TLS support for the web interface.
"""

import os
import logging
import subprocess
from pathlib import Path
from OpenSSL import crypto

logger = logging.getLogger('VisiGate.web.ssl')

def generate_self_signed_cert(cert_file, key_file, days=365, key_size=2048):
    """
    Generate a self-signed SSL certificate.
    
    Args:
        cert_file (str): Path to the certificate file
        key_file (str): Path to the private key file
        days (int): Validity period in days
        key_size (int): Key size in bits
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directories if they don't exist
        cert_dir = os.path.dirname(cert_file)
        key_dir = os.path.dirname(key_file)
        
        if cert_dir and not os.path.exists(cert_dir):
            os.makedirs(cert_dir)
        
        if key_dir and not os.path.exists(key_dir):
            os.makedirs(key_dir)
        
        # Generate key pair
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, key_size)
        
        # Create a self-signed certificate
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "California"
        cert.get_subject().L = "Silicon Valley"
        cert.get_subject().O = "VisiGate"
        cert.get_subject().OU = "VisiGate System"
        cert.get_subject().CN = "localhost"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(days * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        # Write certificate and key to files
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        
        # Set permissions
        os.chmod(cert_file, 0o644)
        os.chmod(key_file, 0o600)
        
        logger.info(f"Generated self-signed certificate: {cert_file}")
        logger.info(f"Generated private key: {key_file}")
        
        return True
    except Exception as e:
        logger.error(f"Error generating self-signed certificate: {e}")
        return False

def check_cert_expiry(cert_file):
    """
    Check if a certificate is expired or about to expire.
    
    Args:
        cert_file (str): Path to the certificate file
    
    Returns:
        tuple: (is_valid, days_remaining)
    """
    try:
        # Check if certificate file exists
        if not os.path.exists(cert_file):
            return False, 0
        
        # Load certificate
        with open(cert_file, "rb") as f:
            cert_data = f.read()
        
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
        
        # Get expiry date
        expiry = cert.get_notAfter().decode('ascii')
        expiry_year = int(expiry[0:4])
        expiry_month = int(expiry[4:6])
        expiry_day = int(expiry[6:8])
        
        # Calculate days remaining
        import datetime
        expiry_date = datetime.datetime(expiry_year, expiry_month, expiry_day)
        days_remaining = (expiry_date - datetime.datetime.now()).days
        
        # Check if certificate is valid
        is_valid = days_remaining > 0
        
        return is_valid, days_remaining
    except Exception as e:
        logger.error(f"Error checking certificate expiry: {e}")
        return False, 0

def setup_ssl(config):
    """
    Set up SSL/TLS for the web interface.
    
    Args:
        config (dict): Configuration dictionary
    
    Returns:
        dict: SSL context parameters
    """
    ssl_config = config.get('ssl', {})
    
    # Check if SSL is enabled
    if not ssl_config.get('enabled', False):
        logger.info("SSL is disabled")
        return None
    
    # Get certificate and key file paths
    cert_file = ssl_config.get('cert_file')
    key_file = ssl_config.get('key_file')
    
    # Use default paths if not specified
    if not cert_file or not key_file:
        config_dir = os.environ.get('VISIGATE_CONFIG_DIR', '/etc/visigate')
        cert_file = os.path.join(config_dir, 'ssl', 'cert.pem')
        key_file = os.path.join(config_dir, 'ssl', 'key.pem')
    
    # Check if certificate and key files exist
    cert_exists = os.path.exists(cert_file)
    key_exists = os.path.exists(key_file)
    
    # Generate self-signed certificate if files don't exist or auto-generate is enabled
    if (not cert_exists or not key_exists) and ssl_config.get('auto_generate', True):
        logger.info("Generating self-signed certificate...")
        generate_self_signed_cert(
            cert_file=cert_file,
            key_file=key_file,
            days=ssl_config.get('days', 365),
            key_size=ssl_config.get('key_size', 2048)
        )
    
    # Check certificate expiry
    is_valid, days_remaining = check_cert_expiry(cert_file)
    
    if not is_valid:
        logger.warning(f"SSL certificate is expired or invalid")
        
        # Regenerate certificate if auto-generate is enabled
        if ssl_config.get('auto_generate', True):
            logger.info("Regenerating self-signed certificate...")
            generate_self_signed_cert(
                cert_file=cert_file,
                key_file=key_file,
                days=ssl_config.get('days', 365),
                key_size=ssl_config.get('key_size', 2048)
            )
    elif days_remaining < 30:
        logger.warning(f"SSL certificate will expire in {days_remaining} days")
    
    # Return SSL context parameters
    return {
        'cert_file': cert_file,
        'key_file': key_file
    }
