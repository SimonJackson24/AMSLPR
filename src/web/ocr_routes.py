# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
import os
import json
import logging
from functools import wraps
from werkzeug.utils import secure_filename

# Try to import auth module, but don't fail if it's not available
try:
    from src.web.auth import admin_required
    AUTH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import auth module: {e}")
    logging.warning("Running without authentication")
    AUTH_AVAILABLE = False
    
    # Define fallback decorators
    def login_required(f):
        """Decorator for routes that require login"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    
    def admin_required(f):
        """Decorator for routes that require admin privileges"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function

# Import detector with fallback for missing dependencies
try:
    from src.recognition.detector import LicensePlateDetector
    DETECTOR_AVAILABLE = True
    MOCK_DETECTOR = False
except ImportError as e:
    logging.warning(f"Could not import LicensePlateDetector in ocr_routes: {e}")
    logging.warning("Using MockLicensePlateDetector instead")
    from src.recognition.mock_detector import MockLicensePlateDetector as LicensePlateDetector
    DETECTOR_AVAILABLE = True
    MOCK_DETECTOR = True

logger = logging.getLogger('AMSLPR.web.ocr')

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

def admin_required(f):
    """Decorator for routes that require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        
        db_manager = current_app.config['DB_MANAGER']
        user = db_manager.get_user(session['user_id'])
        
        if not user or user['role'] != 'admin':
            flash('Admin privileges required', 'danger')
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def get_ocr_config():
    """Get the OCR configuration"""
    config_path = os.path.join('config', 'ocr_config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading OCR configuration: {e}")
    
    # Return default configuration if file doesn't exist or there's an error
    return {
        "ocr_method": "tesseract",
        "use_hailo_tpu": False,
        "confidence_threshold": 0.7,
        "tesseract_config": {
            "psm_mode": 7,
            "oem_mode": 1,
            "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        },
        "deep_learning": {
            "model_type": "crnn",
            "input_width": 100,
            "input_height": 32
        },
        "preprocessing": {
            "resize_factor": 2.0,
            "apply_contrast_enhancement": True,
            "apply_noise_reduction": True,
            "apply_perspective_correction": False
        },
        "postprocessing": {
            "apply_regex_validation": True,
            "min_plate_length": 4,
            "max_plate_length": 10
        },
        "regional_settings": {
            "country_code": "US",
            "plate_format": "[A-Z0-9]{3,8}"
        }
    }

def save_ocr_config(config):
    """Save the OCR configuration"""
    config_path = os.path.join('config', 'ocr_config.json')
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving OCR configuration: {e}")
        return False

def reload_ocr_config():
    """Reload the OCR configuration for all active detectors"""
    try:
        # Set the flag to reload configuration
        current_app.recognition_reload_config = True
        logger.info("Set flag to reload OCR configuration for all detectors")
        return True
    except Exception as e:
        logger.error(f"Error setting reload flag for OCR configuration: {e}")
        return False

_detector = None
_app = None

def register_routes(app, detector):
    """Register OCR routes with the Flask application."""
    global _detector, _app
    _detector = detector
    _app = app
    
    # Register the blueprint with the app
    app.register_blueprint(ocr_bp)
    
    # Check if detector is available
    if _detector is None:
        app.logger.warning("OCR routes initialized without a detector. Some functionality will be limited.")
        
    logger.info("OCR routes registered successfully")
    
    return app  # Return the app instance for chaining

# Keep setup_routes for backward compatibility
def setup_routes(app, detector):
    """Set up OCR routes with the detector (alias for register_routes)."""
    return register_routes(app, detector)

@ocr_bp.route('/settings', methods=['GET', 'POST'])
def ocr_settings():
    """OCR settings page"""
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
            # Add default values for other config sections if they're missing
            'tesseract_config': {
                'psm_mode': 7,
                'oem_mode': 1,
                'whitelist': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            },
            'deep_learning': {
                'model_type': 'crnn',
                'input_width': 100,
                'input_height': 32,
                'tf_ocr_model_path': 'models/ocr_crnn.h5',
                'hailo_ocr_model_path': 'models/lprnet_vehicle_license_recognition.hef',
                'hailo_detector_model_path': 'models/yolov5m_license_plates.hef',
                'char_map_path': 'models/char_map.json'
            },
            'preprocessing': {
                'resize_factor': 2.0,
                'apply_contrast_enhancement': True,
                'apply_noise_reduction': True,
                'apply_perspective_correction': True
            },
            'postprocessing': {
                'apply_regex_validation': True,
                'min_plate_length': 4,
                'max_plate_length': 10,
                'common_substitutions': {
                    '0': 'O',
                    '1': 'I',
                    '5': 'S',
                    '8': 'B'
                }
            },
            'regional_settings': {
                'country_code': 'US',
                'plate_format': '[A-Z0-9]{3,8}'
            }
        }
        
        # Save config
        if save_ocr_config(config):
            flash('OCR configuration saved successfully', 'success')
            
            # Reload OCR configuration
            reload_success = reload_ocr_config()
            if reload_success:
                flash('OCR configuration reloaded successfully', 'success')
            else:
                flash('OCR configuration saved but reload failed', 'warning')
        else:
            flash('Error saving OCR configuration', 'danger')
        
        return redirect(url_for('ocr.ocr_settings'))
    
    # Get current config
    config = get_ocr_config()
    
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
    
    if 'postprocessing' not in config:
        config['postprocessing'] = {
            'apply_regex_validation': True,
            'min_plate_length': 4,
            'max_plate_length': 10,
            'common_substitutions': {
                '0': 'O',
                '1': 'I',
                '5': 'S',
                '8': 'B'
            }
        }
    
    if 'regional_settings' not in config:
        config['regional_settings'] = {
            'country_code': 'US',
            'plate_format': '[A-Z0-9]{3,8}'
        }
    
    # Check for actual Hailo TPU availability by testing all required components
    hailo_available = False
    
    # Step 1: Check for TensorFlow
    tensorflow_available = False
    try:
        import tensorflow
        tensorflow_available = True
        logger.info(f"✓ TensorFlow is available (version {tensorflow.__version__})")
    except ImportError as e:
        logger.warning(f"✗ TensorFlow is not available: {e}")
    
    # Step 2: Check for Hailo modules
    hailo_modules_available = False
    if tensorflow_available:
        try:
            import hailo_platform
            import hailo_model_zoo
            hailo_modules_available = True
            logger.info("✓ Hailo SDK modules are available")
        except ImportError as e:
            logger.warning(f"✗ Some Hailo modules are not available: {e}")
    
    # Step 3: Check for Hailo device on Linux systems
    device_check_passed = False
    if hailo_modules_available:
        if os.name == 'posix':
            # On Linux, check for physical device
            if os.path.exists('/dev/hailo0'):
                device_check_passed = True
                logger.info("✓ Hailo device found at /dev/hailo0")
            else:
                logger.warning("✗ Hailo device not found at /dev/hailo0")
        else:
            # On Windows, we can't easily check for the device, so just check SDK
            device_check_passed = True
            logger.info("✓ Running on Windows, skipping physical device check")
    
    # Step 4: Check for model files
    models_available = False
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'models')
    if os.path.exists(models_dir):
        hef_models = [f for f in os.listdir(models_dir) if f.endswith('.hef')]
        if hef_models:
            models_available = True
            logger.info(f"✓ Found {len(hef_models)} Hailo model files: {', '.join(hef_models)}")
        else:
            logger.warning("✗ No Hailo model files found in models directory")
    else:
        logger.warning("✗ Models directory not found")
    
    # Make final decision on Hailo availability
    hailo_available = tensorflow_available and hailo_modules_available and device_check_passed and models_available
    
    # Print summary
    if hailo_available:
        logger.info("=== Hailo TPU is AVAILABLE and will be used for hardware acceleration ===")
    else:
        logger.warning("=== Hailo TPU is NOT AVAILABLE, deep learning options will be disabled ===")
        logger.warning("    Run python scripts/install_tpu_dependencies.py to fix missing dependencies")
    
    return render_template('ocr_settings.html', config=config, mock=MOCK_DETECTOR, hailo_available=hailo_available)

@ocr_bp.route('/test', methods=['GET'])
@admin_required
def ocr_test():
    """OCR test page"""
    return render_template('ocr_test.html')

@ocr_bp.route('/api/config', methods=['GET'])
def api_get_config():
    """API endpoint to get OCR configuration"""
    return jsonify(get_ocr_config())

@ocr_bp.route('/api/config', methods=['POST'])
def api_update_config():
    """API endpoint to update OCR configuration"""
    try:
        config = request.json
        if save_ocr_config(config):
            # Reload configuration in all active detectors
            reload_success = reload_ocr_config()
            if reload_success:
                return jsonify({"success": True, "message": "Configuration updated and reloaded successfully"})
            else:
                return jsonify({"success": True, "message": "Configuration updated but reload failed"})
        else:
            return jsonify({"success": False, "message": "Error saving configuration"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@ocr_bp.route('/api/reload', methods=['POST'])
def api_reload_config():
    """API endpoint to reload OCR configuration without changing it"""
    try:
        reload_success = reload_ocr_config()
        if reload_success:
            return jsonify({"success": True, "message": "OCR configuration reloaded successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to reload OCR configuration"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@ocr_bp.route('/api/test', methods=['POST'])
def api_test_ocr():
    """API endpoint to test OCR with an image"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "No image provided"}), 400
            
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"success": False, "message": "No image selected"}), 400
            
        # Save the image temporarily
        temp_path = os.path.join('data', 'temp', 'ocr_test.jpg')
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        image_file.save(temp_path)
        
        # Process the image with OCR
        import cv2
        from src.recognition.detector import LicensePlateDetector
        
        # Load the image
        image = cv2.imread(temp_path)
        if image is None:
            return jsonify({"success": False, "message": "Error loading image"}), 400
            
        # Get OCR configuration
        config = get_ocr_config()
        
        # Create detector with test configuration
        detector = LicensePlateDetector({
            "save_images": False,
            "ocr_config_path": os.path.join('config', 'ocr_config.json')
        }, config)
        
        # Detect license plate
        plates = detector.detect_license_plates(image)
        
        if not plates:
            return jsonify({"success": False, "message": "No license plate detected in the image"}), 400
            
        # Recognize text on the first plate
        plate_text = detector._recognize_text(image, plates[0])
        
        if not plate_text:
            return jsonify({"success": False, "message": "Could not recognize text on the license plate"}), 400
            
        # Clean up
        os.remove(temp_path)
        
        return jsonify({
            "success": True,
            "plate_text": plate_text,
            "confidence": plates[0]['confidence'],
            "method": config["ocr_method"]
        })
    except Exception as e:
        logger.error(f"Error testing OCR: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@ocr_bp.route('/api/status', methods=['GET'])
def api_status():
    """API endpoint to get OCR status"""
    status = {
        "available": _detector is not None,
        "mock": MOCK_DETECTOR,
        "version": "1.0.0",
        "config_loaded": True if _detector is not None else False
    }
    return jsonify(status)

def register_routes(app, detector):
    """Register OCR routes with the Flask app"""
    global _detector, _app
    _detector = detector
    _app = app
    
    # Register blueprint
    app.register_blueprint(ocr_bp, url_prefix='/ocr')
    
    logger.info("OCR routes registered")
    
    return app
