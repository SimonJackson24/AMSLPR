# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
from flask import Flask, session, g, redirect, url_for, request
import os
import logging
import traceback
import sys
from datetime import datetime
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
import asyncio
import nest_asyncio
from functools import wraps
import redis

# Configure enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AMSLPR')

# Initialize event loop support
nest_asyncio.apply()

def async_route(f):
    """Decorator to make a route async-compatible."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(f(*args, **kwargs))
    return wrapper

# Import routes with fallback for missing dependencies
try:
    from src.web.camera_routes import register_camera_routes
    from src.web.ocr_routes import register_routes as register_ocr_routes
    ROUTES_AVAILABLE = True
    logger.info("Successfully imported camera and OCR routes")
except ImportError as e:
    logger.error(f"Could not import camera/OCR routes: {e}")
    logger.error(traceback.format_exc())
    logger.warning("Running in limited mode without OCR functionality")
    ROUTES_AVAILABLE = False

# Import other routes
try:
    from src.web.main_routes import register_main_routes
    from src.web.vehicle_routes import register_vehicle_routes
    from src.web.barrier_routes import register_routes as register_barrier_routes
    from src.web.api_routes import register_routes as register_api_routes
    from src.web.stats_routes import register_routes as register_stats_routes
    from src.web.system_routes import register_routes as register_system_routes
    from src.web.auth_routes import register_routes as register_auth_routes
    from src.web.user_routes import register_routes as register_user_routes
    from src.web.parking_routes import register_routes as register_parking_routes
    OTHER_ROUTES_AVAILABLE = True
    logger.info("Successfully imported all other routes")
except ImportError as e:
    logger.error(f"Could not import other routes: {e}")
    logger.error(traceback.format_exc())
    logger.warning("Running in limited mode without some functionality")
    OTHER_ROUTES_AVAILABLE = False

def create_app(config=None):
    """Create and configure the Flask application."""
    # Create Flask app
    app = Flask(__name__)
    
    # Enable debug mode for more detailed error information
    app.config['DEBUG'] = True
    
    # Log startup information
    logger.info("Starting AMSLPR web application")
    logger.info(f"Configuration: {config}")
    
    # Initialize CSRF protection
    try:
        csrf = CSRFProtect(app)
        logger.info("CSRF protection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize CSRF protection: {e}")
        logger.error(traceback.format_exc())
    
    # Initialize session handling
    try:
        app.config['SESSION_TYPE'] = 'redis'
        app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
        Session(app)
        logger.info("Redis session initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis session: {e}")
        logger.error(traceback.format_exc())
    
    # Set secret key for session management
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
    
    # Initialize database and detector
    try:
        from src.database.db_manager import DatabaseManager
        from src.recognition.detector import LicensePlateDetector
        
        db_manager = DatabaseManager(config.get('database', {})) if config else None
        detector = LicensePlateDetector(config.get('recognition', {})) if config else None
        logger.info("Database and detector initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database or detector: {e}")
        logger.error(traceback.format_exc())
        db_manager = None
        detector = None
    
    # Register routes
    if ROUTES_AVAILABLE:
        try:
            app = register_camera_routes(app, detector, db_manager)
            app = register_ocr_routes(app, detector)
            
            # Direct import and registration of OCR blueprint to fix 404 error
            try:
                from src.web.ocr_routes import ocr_bp
                app.register_blueprint(ocr_bp)
                logger.info("OCR blueprint registered directly to fix 404 error")
                
                # Add a direct route for OCR settings at the Flask app level to ensure it works
                @app.route('/ocr/settings', methods=['GET', 'POST'])
                def direct_ocr_settings():
                    """Direct handler for OCR settings page to bypass any blueprint conflicts"""
                    from flask import render_template, request, redirect, url_for, flash
                    import os
                    import json
                    
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
                    
                logger.info("Direct OCR settings route registered at application level")
            except Exception as e:
                logger.error(f"Failed to register OCR routes directly: {e}")
                
            logger.info("Camera and OCR routes registered")
        except Exception as e:
            logger.error(f"Failed to register camera/OCR routes: {e}")
            logger.error(traceback.format_exc())
    
    # Register direct fix blueprint as a final fallback for OCR settings
    try:
        from src.web.direct_fix import register_direct_fix
        app = register_direct_fix(app)
        logger.info("Direct OCR settings fix registered successfully")
    except Exception as e:
        logger.error(f"Failed to register direct OCR settings fix: {e}")
        logger.error(traceback.format_exc())
    
    if OTHER_ROUTES_AVAILABLE:
        # Initialize any additional controllers or integrations needed
        barrier_controller = None
        paxton_integration = None
        nayax_integration = None
        
        try:
            app = register_main_routes(app, db_manager, barrier_controller, paxton_integration, nayax_integration)
            logger.info("Main routes registered")
        except Exception as e:
            logger.error(f"Failed to register main routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_vehicle_routes(app, db_manager)
            logger.info("Vehicle routes registered")
        except Exception as e:
            logger.error(f"Failed to register vehicle routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_barrier_routes(app, db_manager)
            logger.info("Barrier routes registered")
        except Exception as e:
            logger.error(f"Failed to register barrier routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_api_routes(app, db_manager)
            logger.info("API routes registered")
        except Exception as e:
            logger.error(f"Failed to register API routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_stats_routes(app, db_manager)
            logger.info("Stats routes registered")
        except Exception as e:
            logger.error(f"Failed to register stats routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_system_routes(app, db_manager)
            logger.info("System routes registered")
        except Exception as e:
            logger.error(f"Failed to register system routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_auth_routes(app, db_manager)
            logger.info("Auth routes registered")
        except Exception as e:
            logger.error(f"Failed to register auth routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_user_routes(app, db_manager)
            logger.info("User routes registered")
        except Exception as e:
            logger.error(f"Failed to register user routes: {e}")
            logger.error(traceback.format_exc())
            
        try:
            app = register_parking_routes(app, db_manager)
            logger.info("Parking routes registered")
        except Exception as e:
            logger.error(f"Failed to register parking routes: {e}")
            logger.error(traceback.format_exc())
    
    # Add request logging
    @app.before_request
    def log_request():
        logger.info(f"Request: {request.method} {request.path}")
    
    # Add enhanced error handling
    @app.errorhandler(Exception)
    def log_error(e):
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        
        # In development mode, show detailed error information
        if app.config.get('DEBUG', False):
            error_details = traceback.format_exc()
            return f"""<h1>Application Error</h1>
<h2>{str(e)}</h2>
<pre>{error_details}</pre>""", 500
        # In production mode, show a user-friendly error page
        else:
            return render_template('error.html', 
                                  error_title="Application Error",
                                  error_message=str(e),
                                  error_details=traceback.format_exc()), 500
    
    # Register custom template filters
    @app.template_filter('formatDateTime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        """Format a datetime object to a string."""
        if value is None:
            return ""
        try:
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return value.strftime(format)
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            return str(value)
    
    return app

# Load configuration and create app instance for uvicorn
try:
    from src.utils.config import load_config
    config = load_config()
    app = create_app(config)

    # Add health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    # Make Flask app compatible with ASGI
    from asgiref.wsgi import WsgiToAsgi
    asgi_app = WsgiToAsgi(app)

except Exception as e:
    logger.error(f"Failed to initialize application: {e}")
    logger.error(traceback.format_exc())
    raise

if __name__ == '__main__':
    import uvicorn
    import logging
    
    # Set event loop policy for container environment
    import platform
    if platform.system() == 'Linux':
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("Using uvloop for improved async performance")
        except ImportError:
            logger.warning("uvloop not available, using standard asyncio event loop")
            # Continue with the default event loop policy
    
    # Run with uvicorn for better async support
    if config['web']['ssl']['enabled']:
        uvicorn.run(
            "src.web.app:asgi_app",
            host="0.0.0.0",
            port=5000,
            ssl_keyfile=config['web']['ssl']['key'],
            ssl_certfile=config['web']['ssl']['cert'],
            workers=2  # Use 2 workers on Raspberry Pi
        )
    else:
        uvicorn.run(
            "src.web.app:asgi_app",
            host="0.0.0.0",
            port=5000,
            workers=2  # Use 2 workers on Raspberry Pi
        )
