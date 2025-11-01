
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import os
import json
import logging

logger = logging.getLogger('VisiGate.config')

def load_config(config_file=None):
    """Load configuration from file."""
    if config_file is None:
        config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.json')
    
    # Default configuration
    default_config = {
        'web': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': True,
            'secret_key': 'change_this_in_production',
            'upload_folder': os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'),
            'ssl': {
                'enabled': False,
                'cert': '',
                'key': ''
            }
        },
        'database': {
            'path': os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'visigate.db')
        },
        'recognition': {
            'enabled': True,
            'method': 'hybrid',
            'confidence_threshold': 0.7,
            'processing_interval': 0.5
        },
        'barrier': {
            'enabled': True,
            'open_pin': 17,
            'close_pin': 18,
            'status_pin': 27,
            'open_time': 5
        },
        'operating_mode': 'standalone'
    }
    
    # Create config directory if it doesn't exist
    config_dir = os.path.dirname(config_file)
    if config_dir:  # Only create directory if path is not empty
        os.makedirs(config_dir, exist_ok=True)
    
    # Load configuration from file if it exists
    config = default_config
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
                # Update default config with loaded config
                update_nested_dict(config, loaded_config)
            logging.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
    else:
        # Create default configuration file
        try:
            if config_dir:  # Only write file if path is not empty
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logging.warning(f"Configuration file {config_file} not found. Creating with default values.")
            else:
                logging.warning("No configuration file path specified. Using default values.")
        except Exception as e:
            logging.error(f"Error creating default configuration file: {e}")
    
    return config

def update_nested_dict(d, u):
    """Update nested dictionary."""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            update_nested_dict(d[k], v)
        else:
            d[k] = v

def save_config(config, config_path):
    """
    Save configuration to a JSON file.
    
    Args:
        config (dict): Configuration dictionary
        config_path (str): Path to the configuration file
    """
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
