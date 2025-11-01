# Direct OCR settings route fix
# This file adds a direct route handler for /ocr/settings

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import os
import json
import logging

logger = logging.getLogger('VisiGate.direct_ocr_fix')

# Create a blueprint with an explicit URL path
direct_ocr_bp = Blueprint('direct_ocr', __name__)

@direct_ocr_bp.route('/ocr/settings', methods=['GET', 'POST'])
def direct_ocr_settings():
    """Direct handler for OCR settings to fix 404 error"""
    logger.info("Direct OCR settings route accessed")
    
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
            return redirect(url_for('direct_ocr.direct_ocr_settings'))
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
    
    if 'deep_learning' not in config:
        config['deep_learning'] = {
            'model_type': 'crnn',
            'input_width': 100,
            'input_height': 32,
            'hailo_ocr_model_path': 'models/lprnet_vehicle_license_recognition.hef',
            'hailo_detector_model_path': 'models/yolov5m_license_plates.hef'
        }
    
    if 'preprocessing' not in config:
        config['preprocessing'] = {
            'resize_factor': 2.0,
            'apply_contrast_enhancement': True,
            'apply_noise_reduction': True,
            'apply_perspective_correction': True
        }
    
    return render_template('ocr_settings.html', config=config)

def register_direct_fix(app):
    """Register the direct OCR fix blueprint with the Flask app"""
    app.register_blueprint(direct_ocr_bp)
    logger.info("Direct OCR fix registered successfully")
    return app
