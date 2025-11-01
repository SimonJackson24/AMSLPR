
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
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

logger = logging.getLogger('VisiGate.web.security')

class RateLimiter:
    """
    Rate limiter for API endpoints.
    """
    
    def __init__(self):
        """
        Initialize rate limiter.
        """
        self.max_requests = 100
        self.window_seconds = 60
        self._request_counts = {}
        self._last_cleanup = time.time()
        
    def _cleanup_old_entries(self):
        """Remove old entries from the request counts."""
        now = time.time()
        if now - self._last_cleanup > self.window_seconds:
            cutoff = now - self.window_seconds
            self._request_counts = {
                ip: (count, timestamp) 
                for ip, (count, timestamp) in self._request_counts.items() 
                if timestamp > cutoff
            }
            self._last_cleanup = now
            
    def is_rate_limited(self, ip):
        """Check if an IP is rate limited."""
        self._cleanup_old_entries()
        now = time.time()
        
        if ip not in self._request_counts:
            self._request_counts[ip] = (1, now)
            return False
            
        count, timestamp = self._request_counts[ip]
        if now - timestamp > self.window_seconds:
            self._request_counts[ip] = (1, now)
            return False
            
        if count >= self.max_requests:
            return True
            
        self._request_counts[ip] = (count + 1, timestamp)
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
