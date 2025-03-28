# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
from flask import Flask, session, g, redirect, url_for
import os
import logging
from datetime import datetime
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
import asyncio
import nest_asyncio
from functools import wraps

# Try to import flask_limiter, but don't fail if it's not available
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import flask_limiter: {e}")
    logging.warning("Running without rate limiting")
    LIMITER_AVAILABLE = False

# Import routes with fallback for missing dependencies
try:
    from src.web.camera_routes import register_camera_routes
    from src.web.ocr_routes import register_routes as register_ocr_routes
    ROUTES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import routes: {e}")
    logging.warning("Running in limited mode without OCR functionality")
    ROUTES_AVAILABLE = False

# Import other routes
try:
    from src.web.main_routes import register_main_routes
    from src.web.vehicle_routes import register_vehicle_routes
    from src.web.barrier_routes import register_routes as register_barrier_routes
    from src.web.api_routes import register_routes as register_api_routes
    from src.web.stats_routes import register_routes as register_stats_routes
    from src.web.system_routes import register_routes as register_system_routes
    from src.web.auth_routes import register_routes as register_auth_routes, auth_bp
    from src.web.user_routes import register_routes as register_user_routes
    from src.web.parking_routes import parking_bp
    OTHER_ROUTES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import other routes: {e}")
    logging.warning("Running in limited mode without some functionality")
    OTHER_ROUTES_AVAILABLE = False

def async_route(f):
    """Decorator to make a route async-compatible."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.create_task(f(*args, **kwargs))
        else:
            return loop.run_until_complete(f(*args, **kwargs))
    return wrapper

def create_app(config, db_manager, detector, barrier_controller=None, paxton_integration=None, nayax_integration=None):
    """
    Create and configure the Flask application.
    
    Args:
        config (dict): Application configuration
        db_manager (DatabaseManager): Database manager instance
        detector (LicensePlateDetector): License plate detector instance
        barrier_controller (BarrierController, optional): Barrier controller instance
        paxton_integration (PaxtonIntegration, optional): Paxton integration instance
        nayax_integration (NayaxIntegration, optional): Nayax integration instance
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config['web']['secret_key']
    app.config['UPLOAD_FOLDER'] = config['web']['upload_folder']
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
    app.config['DETECTOR_AVAILABLE'] = detector is not None
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Set up event loop for async operations
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Allow nested event loops (needed for Flask development server)
    nest_asyncio.apply()
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_COOKIE_SECURE'] = config['web']['ssl']['enabled']
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'flask_session')
    
    # Make sure the session directory exists
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # Initialize Flask-Session
    Session(app)
    
    # Configure SSL if enabled
    if config['web']['ssl']['enabled']:
        app.config['SSL_ENABLED'] = True
        app.config['SSL_CERT'] = config['web']['ssl']['cert']
        app.config['SSL_KEY'] = config['web']['ssl']['key']
    else:
        app.config['SSL_ENABLED'] = False
    
    # Set up rate limiting if available
    if LIMITER_AVAILABLE:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://",
        )
    
    # Store config in app config for access in routes
    app.config.update(config)
    
    # Store dependencies in app config for access in routes
    app.config['DB_MANAGER'] = db_manager
    app.config['DETECTOR'] = detector
    if barrier_controller:
        app.config['BARRIER_CONTROLLER'] = barrier_controller
    if paxton_integration:
        app.config['PAXTON_INTEGRATION'] = paxton_integration
    if nayax_integration:
        app.config['NAYAX_INTEGRATION'] = nayax_integration
    
    # Configure app
    app.config['DEBUG'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['EXPLAIN_TEMPLATE_LOADING'] = True
    
    # Register custom template filters
    @app.template_filter('formatDateTime')
    def format_datetime(value):
        """Format a datetime object to a readable string."""
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    # Initialize security features if available
    try:
        from src.web.security import setup_security
        setup_security(app)
    except ImportError as e:
        logging.warning(f"Could not import security module: {e}")
        logging.warning("Running without security features")
    
    # Initialize camera health monitor if available
    try:
        from src.utils.camera_health import AsyncCameraHealthMonitor
        # We'll initialize this later when we have a camera manager
        app.config['CAMERA_HEALTH_MONITOR_ENABLED'] = True
    except ImportError as e:
        logging.warning(f"Could not import camera health monitor: {e}")
        logging.warning("Running without camera health monitoring")
        app.config['CAMERA_HEALTH_MONITOR_ENABLED'] = False
    
    # Initialize authentication system if available
    try:
        from src.web.auth_routes import init_user_manager, register_routes as register_auth_routes, auth_bp
        init_user_manager(app)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        register_auth_routes(app, db_manager)
        app.config['AUTH_ENABLED'] = True
        
        # Initialize mode-based permissions
        try:
            from src.utils.mode_permissions import get_visible_features
            
            @app.context_processor
            def inject_visible_features():
                """Make visible features available in templates."""
                return {'visible_features': get_visible_features()}
                
            logging.info("Mode-based permission system initialized")
        except ImportError as e:
            logging.warning(f"Could not import mode permissions module: {e}")
            logging.warning("Running without mode-based permissions")
    except ImportError as e:
        logging.warning(f"Could not import auth module: {e}")
        logging.warning("Running without authentication")
        app.config['AUTH_ENABLED'] = False
    
    # Register camera routes if available
    if ROUTES_AVAILABLE:
        register_camera_routes(app, detector, db_manager)
        register_ocr_routes(app, detector)
    
    # Register system routes if available
    if OTHER_ROUTES_AVAILABLE:
        register_system_routes(app, db_manager)
    
    # Register blueprints if available
    try:
        from src.web.main_routes import main_bp, register_main_routes
        register_main_routes(app, db_manager)
    except ImportError as e:
        logging.warning(f"Could not import main routes: {e}")
    
    try:
        from src.web.vehicle_routes import vehicle_bp
        app.register_blueprint(vehicle_bp)
    except ImportError as e:
        logging.warning(f"Could not import vehicle routes: {e}")
        
    # Register parking blueprint if available
    try:
        from src.web.parking_routes import parking_bp
        app.register_blueprint(parking_bp)
        logging.info("Parking routes registered")
    except (ImportError, NameError) as e:
        logging.warning(f"Could not register parking routes: {e}")
    
    # Register other routes if available
    if OTHER_ROUTES_AVAILABLE:
        register_vehicle_routes(app, db_manager)
        register_barrier_routes(app, db_manager)
        register_api_routes(app, db_manager)
        register_stats_routes(app, db_manager)
        register_user_routes(app, db_manager)
        # Auth routes already registered above
    
    # Register global redirects
    @app.route('/backup')
    def backup_redirect():
        return redirect(url_for('system.backup_restore'))
    
    @app.route('/users')
    def users_redirect():
        return redirect(url_for('auth.users_list'))
    
    @app.route('/ocr/settings')
    def ocr_settings_redirect():
        return redirect(url_for('ocr.ocr_settings'))
    
    # Initialize user manager
    try:
        from src.utils.user_management import UserManager
        user_manager = UserManager()
        app.config['USER_MANAGER'] = user_manager
    except ImportError as e:
        logging.warning(f"Could not import user manager: {e}")
        logging.warning("Running without user management")
    
    return app

# Load configuration and create app instance for uvicorn
try:
    from src.utils.config import load_config
    from src.recognition.detector import LicensePlateDetector
    from src.db.manager import DatabaseManager

    config = load_config()
    db_manager = DatabaseManager(config['database'])
    detector = LicensePlateDetector(config['recognition'])
    app = create_app(config, db_manager, detector)

    # Add health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    # Make Flask app compatible with ASGI
    from asgiref.wsgi import WsgiToAsgi
    asgi_app = WsgiToAsgi(app)

except Exception as e:
    logging.error(f"Failed to initialize application: {e}")
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
            logging.info("Using uvloop for improved async performance")
        except ImportError:
            logging.warning("uvloop not available, using standard asyncio event loop")
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
