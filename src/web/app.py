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
import redis

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

def create_app(config=None):
    """
    Create and configure the Flask application.
    
    Args:
        config (dict): Application configuration
        
    Returns:
        Flask: Configured Flask application
    """
    try:
        from src.web import create_app as flask_create_app
        
        # Create Flask app
        app = flask_create_app(config)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Log startup information
        logger.info("Starting AMSLPR web application")
        logger.info(f"Configuration: {config}")
        
        return app
        
    except Exception as e:
        logger.error(f"Error creating Flask app: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

# Load configuration and create app instance for uvicorn
try:
    from src.utils.config import load_config
    from src.recognition.detector import LicensePlateDetector
    from src.database.db_manager import DatabaseManager

    config = load_config()
    db_manager = DatabaseManager(config['database'])
    detector = LicensePlateDetector(config['recognition'])
    app = create_app(config)

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
