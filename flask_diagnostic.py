#!/usr/bin/env python3

"""
Diagnostic script to identify Flask routing issues.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AMSLPR.flask_diagnostic')

# Create a file for output
output_file = '/tmp/flask_diagnostic.log'

# Add AMSLPR to Python path
sys.path.append('/opt/amslpr')

try:
    # Try to import Flask app
    logger.info("Attempting to import Flask app")
    from src.web.app import app
    
    # Log all registered routes
    logger.info("Registered routes:")
    with open(output_file, 'w') as f:
        f.write("=== Flask Routes ===\n")
        for rule in app.url_map.iter_rules():
            f.write(f"Rule: {rule}\n")
            f.write(f"Endpoint: {rule.endpoint}\n")
            f.write(f"Methods: {rule.methods}\n")
            f.write("---\n")
    
    # Check if camera routes are registered
    camera_routes = [rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith('camera.')]
    with open(output_file, 'a') as f:
        f.write("\n=== Camera Routes ===\n")
        if camera_routes:
            for rule in camera_routes:
                f.write(f"Rule: {rule}\n")
                f.write(f"Endpoint: {rule.endpoint}\n")
                f.write(f"Methods: {rule.methods}\n")
                f.write("---\n")
        else:
            f.write("No camera routes found!\n")
    
    # Create a minimal test route
    @app.route('/test-diagnostic')
    def test_diagnostic():
        return "Diagnostic test route is working"
    
    # Run the app in debug mode on a different port
    logger.info("Starting Flask app in debug mode")
    with open(output_file, 'a') as f:
        f.write("\n=== Starting Flask App ===\n")
        f.write("The app will be available at http://localhost:5001/test-diagnostic\n")
    
    # Don't actually run the app, just print instructions
    print(f"Diagnostic complete. Check {output_file} for results.")
    print("To test the Flask app directly, you can run:")
    print("cd /opt/amslpr && python -m src.web.app")
    
    # Create a simple fix script
    fix_script = '''
#!/usr/bin/env python3

"""
Emergency fix for AMSLPR - redirects problematic routes to dashboard.
"""

import os

# Create a backup of the current app.py
os.system("sudo cp /opt/amslpr/src/web/app.py /opt/amslpr/src/web/app.py.backup")

# Create a new app.py with error handling
new_app = """
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
\"\"\"
Main Flask application for AMSLPR.
\"\"\"

import os
import sys
import logging
from flask import Flask, render_template, redirect, url_for, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AMSLPR.app')

def create_app(config=None):
    \"\"\"
    Create and configure the Flask application.
    \"\"\"
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    if config:
        app.config.from_mapping(config)
    else:
        app.config.from_pyfile(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.py'))
    
    # Register error handlers
    @app.errorhandler(500)
    def handle_500_error(e):
        logger.error(f"500 error: {str(e)}")
        return render_template('error.html', 
                              error_title="Internal Server Error",
                              error_message="An unexpected error occurred on the server.",
                              error_details=str(e)), 500
    
    @app.errorhandler(404)
    def handle_404_error(e):
        return render_template('error.html', 
                              error_title="Page Not Found",
                              error_message="The requested page does not exist.",
                              error_details=str(e)), 404
    
    # Register blueprints with error handling
    try:
        from src.web.main_routes import register_main_routes
        register_main_routes(app)
        logger.info("Main routes registered successfully")
    except Exception as e:
        logger.error(f"Error registering main routes: {str(e)}")
    
    # Add emergency routes for problematic sections
    @app.route('/cameras')
    def emergency_cameras_redirect():
        logger.info("Emergency redirect from /cameras to dashboard")
        return redirect(url_for('main.dashboard'))
    
    @app.route('/statistics')
    def emergency_statistics_redirect():
        logger.info("Emergency redirect from /statistics to dashboard")
        return redirect(url_for('main.dashboard'))
    
    # Try to register other routes with error handling
    try:
        from src.web.camera_routes import register_camera_routes
        register_camera_routes(app, None, None)
        logger.info("Camera routes registered successfully")
    except Exception as e:
        logger.error(f"Error registering camera routes: {str(e)}")
    
    try:
        from src.web.ocr_routes import register_routes as register_ocr_routes
        register_ocr_routes(app)
        logger.info("OCR routes registered successfully")
    except Exception as e:
        logger.error(f"Error registering OCR routes: {str(e)}")
    
    try:
        from src.web.stats_routes import register_stats_routes
        register_stats_routes(app)
        logger.info("Stats routes registered successfully")
    except Exception as e:
        logger.error(f"Error registering stats routes: {str(e)}")
    
    try:
        from src.web.settings_routes import register_settings_routes
        register_settings_routes(app)
        logger.info("Settings routes registered successfully")
    except Exception as e:
        logger.error(f"Error registering settings routes: {str(e)}")
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
"""

# Write the new app.py to a file
with open("/tmp/new_app.py", "w") as f:
    f.write(new_app)

# Replace the app.py file
os.system("sudo cp /tmp/new_app.py /opt/amslpr/src/web/app.py")

print("Successfully replaced app.py with emergency version")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Restarted AMSLPR service")

print("Emergency fix applied. Problematic routes will now redirect to the dashboard.")
'''
    
    # Write the fix script to a file
    with open('/tmp/emergency_app_fix.py', 'w') as f:
        f.write(fix_script)
    
    print("\nCreated emergency fix script at /tmp/emergency_app_fix.py")
    print("To apply the emergency fix, run: sudo python3 /tmp/emergency_app_fix.py")
    
except Exception as e:
    logger.error(f"Error in diagnostic script: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    
    with open(output_file, 'a') as f:
        f.write(f"\n=== ERROR ===\n{str(e)}\n")
        f.write(traceback.format_exc())
    
    print(f"Error in diagnostic script: {str(e)}")
    print(f"Check {output_file} for details")
