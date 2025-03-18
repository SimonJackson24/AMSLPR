from flask import Flask, session, g
import os
import logging
from datetime import datetime
from flask_session import Session

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
    from src.web.auth_routes import register_routes as register_auth_routes
    from src.web.user_routes import register_routes as register_user_routes
    OTHER_ROUTES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import other routes: {e}")
    logging.warning("Running in limited mode without some functionality")
    OTHER_ROUTES_AVAILABLE = False

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
            get_remote_address,
            app=app,
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
        from src.utils.camera_health import CameraHealthMonitor
        # We'll initialize this later when we have a camera manager
        app.config['CAMERA_HEALTH_MONITOR_ENABLED'] = True
    except ImportError as e:
        logging.warning(f"Could not import camera health monitor: {e}")
        logging.warning("Running without camera health monitoring")
        app.config['CAMERA_HEALTH_MONITOR_ENABLED'] = False
    
    # Initialize authentication system if available
    try:
        from src.web.auth_routes import auth_bp, register_routes
        app.register_blueprint(auth_bp, url_prefix='/auth')
        register_routes(app, db_manager)
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
    
    # Register system routes if available
    if OTHER_ROUTES_AVAILABLE:
        register_system_routes(app)
    
    # Register blueprints if available
    try:
        from src.web.main_routes import main_bp
        # Blueprint is registered in register_main_routes
    except ImportError as e:
        logging.warning(f"Could not import main routes: {e}")
    
    try:
        from src.web.vehicle_routes import vehicle_bp
        app.register_blueprint(vehicle_bp)
    except ImportError as e:
        logging.warning(f"Could not import vehicle routes: {e}")
    
    try:
        from src.web.parking_routes import parking_bp
        app.register_blueprint(parking_bp)
    except ImportError as e:
        logging.warning(f"Could not import parking routes: {e}")
    
    # Register OCR routes if available
    try:
        from src.web.ocr_routes import ocr_bp, setup_routes
        app.register_blueprint(ocr_bp, url_prefix='/ocr')
        setup_routes(app, detector)
    except ImportError as e:
        logging.warning(f"Could not import OCR routes: {e}")
    
    # Register other routes if available
    if OTHER_ROUTES_AVAILABLE:
        # Register vehicle routes
        register_vehicle_routes(app, db_manager)
        
        # Register barrier routes
        register_barrier_routes(app, barrier_controller)
        
        # Register API routes
        register_api_routes(app, db_manager, paxton_integration=paxton_integration, nayax_integration=nayax_integration)
        
        # Register stats routes
        register_stats_routes(app, db_manager)
        
        # Register user routes
        register_user_routes(app, db_manager)
        
        # Register main routes with integrations
        register_main_routes(app, db_manager, barrier_controller, paxton_integration, nayax_integration)
    
    return app

def init_camera_health_monitor(app):
    """Initialize the camera health monitor."""
    global camera_health_monitor
    
    # Get camera manager from app config
    camera_manager = app.config.get('CAMERA_MANAGER')
    if not camera_manager:
        app.logger.error("Cannot initialize camera health monitor: Camera manager not found")
        return
    
    # Get notification manager if available
    notification_manager = app.config.get('NOTIFICATION_MANAGER')
    
    # Create and start camera health monitor
    camera_health_monitor = CameraHealthMonitor(
        camera_manager=camera_manager,
        notification_manager=notification_manager,
        check_interval=60  # Check every 60 seconds
    )
    camera_health_monitor.start()
    
    # Store in app config for access in routes
    app.config['CAMERA_HEALTH_MONITOR'] = camera_health_monitor
    
    app.logger.info("Camera health monitor initialized")

# ... rest of the code remains the same ...
