# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

from flask import jsonify

@app.errorhandler(500)
def handle_500_error(e):
    """Handle 500 Internal Server Error with JSON response."""
    logger.error(f"500 error: {str(e)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error occurred'
    }), 500
