#!/usr/bin/env python3

"""
Simple script to run the AMSLPR web server for testing purposes.
"""

import os
import sys
import json
from src.web.app import create_app
from src.database.db_manager import DatabaseManager

# Default configuration for testing
default_config = {
    "web": {
        "secret_key": "development-key-for-testing",
        "debug": True,
        "host": "127.0.0.1",
        "port": 5060,
        "upload_folder": "uploads",
        "ssl": {
            "enabled": False,
            "cert_path": "",
            "key_path": ""
        }
    },
    "database": {
        "db_path": "data/amslpr.db",
        "backup_interval": 86400
    },
    "notifications": {
        "email_enabled": False,
        "email_from": "noreply@example.com",
        "email_to": "admin@example.com",
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "smtp_use_tls": True,
        "sms_enabled": False,
        "sms_provider": "twilio",
        "sms_to_number": "+1234567890",
        "webhook_enabled": False,
        "webhook_url": "https://example.com/webhook",
        "location_name": "Main Entrance"
    }
}

def main():
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Create reports directory if it doesn't exist
    os.makedirs("/home/simon/Projects/AMSLPR/reports", exist_ok=True)
    
    # Initialize database manager
    db_manager = DatabaseManager(default_config["database"])
    
    # Create a mock detector for testing
    class MockDetector:
        def __init__(self):
            pass
        
        def detect(self, image):
            return []
    
    # Create and run app
    app = create_app(default_config, db_manager, MockDetector())
    
    # Add a test route to set a mock session for testing
    @app.route('/test_login')
    def test_login():
        from flask import session, redirect, url_for
        session['username'] = 'admin'
        session['user_id'] = 1
        session['role'] = 'admin'
        return redirect(url_for('main.dashboard'))
    
    # Add Jinja2 filter for formatDateTime
    @app.template_filter('formatDateTime')
    def format_datetime(value):
        if not value:
            return '-'
        from datetime import datetime
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    app.run(
        host=default_config["web"]["host"],
        port=default_config["web"]["port"],
        debug=default_config["web"]["debug"]
    )

if __name__ == "__main__":
    main()
