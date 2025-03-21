
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Security utilities for the web interface.
"""

import time
import logging
from functools import wraps
from flask import request, jsonify, abort, current_app

logger = logging.getLogger('AMSLPR.web.security')

class RateLimiter:
    """
    Rate limiter for API endpoints.
    """
    
    def __init__(self, max_requests=100, window_seconds=60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests (int): Maximum number of requests per window
            window_seconds (int): Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_rate_limited(self, key):
        """
        Check if a key is rate limited.
        
        Args:
            key (str): Key to check (usually IP address)
        
        Returns:
            bool: True if rate limited, False otherwise
        """
        current_time = time.time()
        
        # Initialize request tracking for this key if not exists
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [req_time for req_time in self.requests[key] 
                             if current_time - req_time <= self.window_seconds]
        
        # Check if rate limit is exceeded
        if len(self.requests[key]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {key}")
            return True
        
        # Add current request
        self.requests[key].append(current_time)
        return False

# Create global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(f):
    """
    Decorator to apply rate limiting to a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP address
        ip = request.remote_addr
        
        # Check if rate limiting is enabled
        security_config = current_app.config.get('security', {})
        rate_limiting_config = security_config.get('rate_limiting', {})
        
        if rate_limiting_config.get('enabled', False):
            # Configure rate limiter
            rate_limiter.max_requests = rate_limiting_config.get('max_requests', 100)
            rate_limiter.window_seconds = rate_limiting_config.get('window_seconds', 60)
            
            # Check if rate limited
            if rate_limiter.is_rate_limited(ip):
                logger.warning(f"Rate limit exceeded for IP: {ip}")
                return jsonify({
                    'error': 'Too many requests',
                    'message': 'Rate limit exceeded. Please try again later.'
                }), 429
        
        return f(*args, **kwargs)
    
    return decorated_function

def apply_security_headers(response):
    """
    Apply security headers to a response.
    
    Args:
        response (Response): Flask response object
    
    Returns:
        Response: Modified response with security headers
    """
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data:;"
    
    return response

def setup_security(app):
    """
    Set up security features for a Flask application.
    
    Args:
        app (Flask): Flask application instance
    """
    # Apply security headers to all responses
    app.after_request(apply_security_headers)
    
    # Store security configuration in app config
    security_config = app.config.get('security', {})
    
    # Configure rate limiter
    rate_limiting_config = security_config.get('rate_limiting', {})
    if rate_limiting_config.get('enabled', False):
        logger.info("Rate limiting enabled")
        logger.info(f"Max requests: {rate_limiting_config.get('max_requests', 100)}")
        logger.info(f"Window seconds: {rate_limiting_config.get('window_seconds', 60)}")
    
    logger.info("Security features initialized")
