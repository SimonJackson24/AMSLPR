#!/usr/bin/env python3
"""
Direct fix for the OCR settings route
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
import os
import json

direct_bp = Blueprint('direct', __name__)
logger = logging.getLogger('AMSLPR.direct_fix')

@direct_bp.route('/ocr/settings', methods=['GET', 'POST'])
def direct_ocr_settings():
    """Direct implementation of OCR settings route"""
    # Debug output
    logger.info("============ DIRECT OCR SETTINGS ACCESSED ============")
    
    # Get the config file path
    config_path = os.path.join('config', 'ocr_config.json')
    
    # Handle form submission
    if request.method == 'POST':
        # Process form data
        ocr_method = request.form.get('ocr_method', 'hybrid')
        confidence_threshold = float(request.form.get('confidence_threshold', 0.7))
        use_hailo_tpu = 'use_hailo_tpu' in request.form
        
        # Create config object
        config = {
            'ocr_method': ocr_method,
            'confidence_threshold': confidence_threshold,
            'use_hailo_tpu': use_hailo_tpu,
            'tesseract_config': {
                'psm_mode': int(request.form.get('psm_mode', 7)),
                'oem_mode': int(request.form.get('oem_mode', 1)),
                'whitelist': request.form.get('whitelist', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            },
            'preprocessing': {
                'resize_factor': float(request.form.get('resize_factor', 2.0)),
                'apply_contrast_enhancement': 'apply_contrast_enhancement' in request.form,
                'apply_noise_reduction': 'apply_noise_reduction' in request.form,
                'apply_perspective_correction': 'apply_perspective_correction' in request.form
            }
        }
        
        # Save config
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            flash('OCR configuration saved successfully', 'success')
            return redirect('/ocr/settings')
        except Exception as e:
            logger.error(f"Error saving OCR settings: {e}")
            flash(f'Error saving settings: {str(e)}', 'danger')
    
    # Get current config
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading OCR config: {e}")
            flash('Error loading configuration', 'warning')
    
    # Ensure all required sections exist
    if 'tesseract_config' not in config:
        config['tesseract_config'] = {
            'psm_mode': 7,
            'oem_mode': 1,
            'whitelist': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        }
    
    if 'preprocessing' not in config:
        config['preprocessing'] = {
            'resize_factor': 2.0,
            'apply_contrast_enhancement': True,
            'apply_noise_reduction': True,
            'apply_perspective_correction': False
        }
        
    if 'ocr_method' not in config:
        config['ocr_method'] = 'hybrid'
        
    if 'confidence_threshold' not in config:
        config['confidence_threshold'] = 0.7
    
    # Check for Hailo TPU availability
    hailo_available = False
    try:
        # First check for hailort module
        import importlib.util
        if importlib.util.find_spec("hailort"):
            # Check if device file exists
            if os.path.exists('/dev/hailo0'):
                try:
                    # Try to import and initialize the device
                    import hailort
                    device = hailort.Device()
                    hailo_available = True
                    logger.info(f"Hailo TPU detected in direct fix: {device.device_id}")
                except Exception as e:
                    logger.warning(f"Hailo TPU module found but device initialization failed: {e}")
            else:
                logger.warning("Hailo device file (/dev/hailo0) not found")
        else:
            logger.warning("hailort module not found")
    except Exception as e:
        logger.error(f"Error checking for Hailo TPU: {e}")
    
    # Force enable if environment variable is set
    if os.environ.get('HAILO_ENABLED') == 'true':
        logger.info("HAILO_ENABLED environment variable is set, enabling Hailo UI options")
        hailo_available = True
    
    # Always enable Hailo options if diagnostics showed it's working
    if os.path.exists('/tmp/hailo_diag_success'):
        logger.info("Hailo diagnostic success file found, enabling Hailo UI options")
        hailo_available = True
    
    # Create a marker file for future reference
    if hailo_available:
        try:
            with open('/tmp/hailo_diag_success', 'w') as f:
                f.write('Hailo TPU detection successful')
        except Exception:
            pass
            
    return render_template('ocr_settings.html', config=config, mock=False, hailo_available=hailo_available)

def register_direct_fix(app):
    """Register the direct blueprint"""
    app.register_blueprint(direct_bp)
    logger.info("Direct OCR settings fix registered successfully")
    return app
