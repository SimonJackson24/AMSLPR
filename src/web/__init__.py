# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import logging
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    if config:
        app.config.update(config)
        
    # Set secret key
    app.config['SECRET_KEY'] = 'dev-secret-key-please-change-in-production'
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database manager
    from src.database.manager import DatabaseManager
    db_manager = DatabaseManager()
    
    # Register custom Jinja2 filters
    @app.template_filter('formatDateTime')
    def format_datetime(value):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return value
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    # Import and register blueprints
    from .camera_routes import camera_bp
    from .user_routes import user_bp
    from .system_routes import system_bp
    from .main_routes import main_bp, init_main_routes
    from .auth_routes import auth_bp
    from .vehicle_routes import vehicle_bp, init_vehicle_routes
    
    # Initialize routes with database manager
    init_main_routes(db_manager)
    init_vehicle_routes(db_manager)
    
    app.register_blueprint(camera_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(vehicle_bp)
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Configure session
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)
    
    # Configure security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data:;"
        return response
    
    # Error handlers
    @app.errorhandler(500)
    def handle_500_error(e):
        """Handle 500 Internal Server Error with JSON response."""
        logger.error(f"500 error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred'
        }), 500
    
    @app.errorhandler(404)
    def handle_404_error(e):
        """Handle 404 Not Found with JSON response."""
        return jsonify({
            'success': False,
            'error': 'Resource not found'
        }), 404
    
    @app.errorhandler(400)
    def handle_400_error(e):
        """Handle 400 Bad Request with JSON response."""
        return jsonify({
            'success': False,
            'error': str(e.description)
        }), 400
    
    @app.errorhandler(401)
    def handle_401_error(e):
        """Handle 401 Unauthorized with JSON response."""
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401
    
    @app.errorhandler(403)
    def handle_403_error(e):
        """Handle 403 Forbidden with JSON response."""
        return jsonify({
            'success': False,
            'error': 'Forbidden'
        }), 403
    
    return app
