# Direct camera fix to ensure the cameras route works correctly
import logging
from flask import Blueprint, render_template, current_app
from src.utils.user_management import login_required, UserManager

logger = logging.getLogger('VisiGate.web.direct_camera_fix')

# Create blueprint
direct_camera_bp = Blueprint('direct_camera', __name__)

# Initialize user manager
user_manager = UserManager()

@direct_camera_bp.route('/cameras')
@login_required(user_manager)
def direct_cameras():
    """Direct handler for cameras page to bypass any blueprint conflicts"""
    logger.info("Direct cameras route accessed")
    
    # Import necessary modules here to avoid circular imports
    from src.web.camera_routes import cameras as original_cameras_view
    
    # Call the original cameras view function
    return original_cameras_view()

def register_direct_camera_fix(app):
    """Register direct camera fix blueprint with the Flask application."""
    try:
        # Register the blueprint
        app.register_blueprint(direct_camera_bp)
        logger.info("Direct camera fix blueprint registered successfully")
        return app
    except Exception as e:
        logger.error(f"Failed to register direct camera fix blueprint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return app
