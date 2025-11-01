
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

"""Configuration management module for the VisiGate system."""
import os
import json
from typing import Any, Dict, Optional
import yaml
from loguru import logger

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from the specified path or default location.
    
    Args:
        config_path: Optional path to the configuration file. If not provided,
                    will use the default path.
    
    Returns:
        Dict containing the configuration data.
    
    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
    """
    config_path = config_path or DEFAULT_CONFIG_PATH
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            if config_path.endswith('.json'):
                config = json.load(f)
            elif config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path}")
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error(f"Failed to parse configuration file: {e}")
        raise
    
    # Add default values for optional settings
    config.setdefault('debug', False)
    config.setdefault('log_level', 'INFO')
    config.setdefault('ssl_enabled', False)
    config.setdefault('port', 5000)
    config.setdefault('host', '0.0.0.0')
    
    # Camera settings
    config.setdefault('camera', {})
    config['camera'].setdefault('timeout', 30)
    config['camera'].setdefault('retry_interval', 5)
    
    # OCR settings
    config.setdefault('ocr', {})
    config['ocr'].setdefault('confidence_threshold', 0.7)
    config['ocr'].setdefault('use_gpu', False)
    config['ocr'].setdefault('use_hailo_tpu', True)  # Enable Hailo TPU by default when available
    
    # Database settings
    config.setdefault('database', {})
    config['database'].setdefault('path', 'instance/visiongate.db')
    
    # Parking settings
    config.setdefault('parking', {})
    config['parking'].setdefault('mode', 'standalone')
    config['parking'].setdefault('max_duration', 24 * 60 * 60)  # 24 hours in seconds
    config['parking'].setdefault('grace_period', 15 * 60)  # 15 minutes in seconds
    
    return config

def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """Save configuration to the specified path or default location.
    
    Args:
        config: Dictionary containing the configuration data.
        config_path: Optional path to save the configuration file. If not provided,
                    will use the default path.
    
    Raises:
        IOError: If unable to write to the configuration file.
    """
    config_path = config_path or DEFAULT_CONFIG_PATH
    
    try:
        with open(config_path, 'w') as f:
            if config_path.endswith('.json'):
                json.dump(config, f, indent=4)
            elif config_path.endswith('.yaml') or config_path.endswith('.yml'):
                yaml.safe_dump(config, f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path}")
    except IOError as e:
        logger.error(f"Failed to save configuration file: {e}")
        raise
