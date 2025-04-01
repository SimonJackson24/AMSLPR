# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import logging
from flask import Flask, jsonify

# Configure logging
logger = logging.getLogger(__name__)

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    if config:
        app.config.update(config)
    
    @app.errorhandler(500)
    def handle_500_error(e):
        """Handle 500 Internal Server Error with JSON response."""
        logger.error(f"500 error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred'
        }), 500
    
    # Import and register blueprints
    from .camera_routes import camera_bp
    from .user_routes import user_bp
    from .system_routes import system_bp
    
    app.register_blueprint(camera_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(system_bp)
    
    return app
