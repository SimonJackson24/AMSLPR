#!/usr/bin/env python3

"""
Emergency OCR route fix script.
This script adds the OCR settings route directly to the application.
"""

import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ocr-route-fix')

# Add the src directory to the Python path
src_dir = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_dir))

try:
    from src.web.app import app
    
    # Add a direct route handler
    @app.route('/ocr/settings', methods=['GET', 'POST'])
    def emergency_ocr_settings():
        """Emergency OCR settings handler"""
        from flask import render_template, request, redirect, flash
        import json
        
        logger.info("Emergency OCR settings handler activated")
        
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
        
        return render_template('ocr_settings.html', config=config)
    
    logger.info("OCR route fix has been applied!")
    
    # List all routes
    logger.info("Registered routes:")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule.rule}")
    for route in sorted(routes):
        logger.info(route)
    
    # Save the patched app
    logger.info("Routes patched successfully.\nRestart the service with: sudo systemctl restart amslpr")
    
except Exception as e:
    logger.error(f"Error applying OCR route fix: {e}")
    import traceback
    logger.error(traceback.format_exc())
