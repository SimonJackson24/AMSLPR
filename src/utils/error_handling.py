#!/usr/bin/env python3
"""
Error handling utilities for the AMSLPR system.
"""

import os
import sys
import logging
import traceback
import json
from datetime import datetime

logger = logging.getLogger('AMSLPR.error_handling')

class ErrorHandler:
    """
    Error handler for the AMSLPR system.
    """
    
    def __init__(self, log_dir='/var/log/amslpr', notification_manager=None):
        """
        Initialize error handler.
        
        Args:
            log_dir (str): Directory for error logs
            notification_manager (NotificationManager): Notification manager instance
        """
        self.log_dir = log_dir
        self.notification_manager = notification_manager
        
        # Create error log directory if it doesn't exist
        os.makedirs(os.path.join(log_dir, 'errors'), exist_ok=True)
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Log the exception
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Format traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Save error details to file
        self._save_error_to_file(exc_type, exc_value, tb_text)
        
        # Send notification if available
        if self.notification_manager:
            self._send_error_notification(exc_type, exc_value, tb_text)
    
    def log_error(self, error, module_name, function_name):
        """
        Log an error with context information.
        
        Args:
            error (Exception): The error to log
            module_name (str): Name of the module where the error occurred
            function_name (str): Name of the function where the error occurred
        """
        # Log the exception
        logger.error(f"Error in {module_name}.{function_name}: {error}")
        
        # Get traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_traceback is None:
            # If not called from an exception handler, create a new traceback
            tb_text = f"Error: {error}\nModule: {module_name}\nFunction: {function_name}"
        else:
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            tb_text = ''.join(tb_lines)
        
        # Save error details to file
        self._save_error_to_file(type(error), error, tb_text, module_name, function_name)
        
        # Send notification if available
        if self.notification_manager:
            self._send_error_notification(type(error), error, tb_text)
    
    def _save_error_to_file(self, exc_type, exc_value, traceback_text, module_name=None, function_name=None):
        """
        Save error details to a file.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            traceback_text (str): Formatted traceback text
            module_name (str, optional): Name of the module where the error occurred
            function_name (str, optional): Name of the function where the error occurred
        """
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"error_{timestamp}.json"
            filepath = os.path.join(self.log_dir, 'errors', filename)
            
            # Create error data
            error_data = {
                'timestamp': datetime.now().isoformat(),
                'type': exc_type.__name__,
                'message': str(exc_value),
                'traceback': traceback_text,
                'system_info': {
                    'python_version': sys.version,
                    'platform': sys.platform
                }
            }
            
            # Add module and function information if available
            if module_name:
                error_data['module'] = module_name
            if function_name:
                error_data['function'] = function_name
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(error_data, f, indent=2)
            
            logger.info(f"Error details saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save error details to file: {e}")
    
    def _send_error_notification(self, exc_type, exc_value, traceback_text):
        """
        Send error notification.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            traceback_text (str): Formatted traceback text
        """
        try:
            if not self.notification_manager:
                return
            
            # Create error message
            error_message = f"AMSLPR Error: {exc_type.__name__}: {exc_value}\n\n"
            error_message += "Traceback (most recent call last):\n"
            error_message += traceback_text
            
            # Send email notification
            self.notification_manager.send_email_notification(
                subject="AMSLPR System Error",
                message=error_message
            )
            
            logger.info("Error notification sent")
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

def setup_error_handler(notification_manager=None, log_dir='/var/log/amslpr'):
    """
    Set up global exception handler.
    
    Args:
        notification_manager (NotificationManager): Notification manager instance
        log_dir (str): Directory for error logs
    
    Returns:
        ErrorHandler: Error handler instance
    """
    # Create error handler
    error_handler = ErrorHandler(log_dir, notification_manager)
    
    # Set up global exception handler
    sys.excepthook = error_handler.handle_exception
    
    logger.info("Error handler set up")
    
    return error_handler

def get_error_logs(log_dir='/var/log/amslpr', limit=10):
    """
    Get recent error logs.
    
    Args:
        log_dir (str): Directory for error logs
        limit (int): Maximum number of logs to return
    
    Returns:
        list: List of error log dictionaries
    """
    error_logs = []
    
    try:
        error_log_dir = os.path.join(log_dir, 'errors')
        if not os.path.exists(error_log_dir):
            return error_logs
        
        # Get list of error log files
        log_files = [f for f in os.listdir(error_log_dir) if f.startswith('error_') and f.endswith('.json')]
        
        # Sort by timestamp (newest first)
        log_files.sort(reverse=True)
        
        # Limit number of logs
        log_files = log_files[:limit]
        
        # Read log files
        for log_file in log_files:
            log_file_path = os.path.join(error_log_dir, log_file)
            try:
                with open(log_file_path, 'r') as f:
                    log_data = json.load(f)
                error_logs.append(log_data)
            except Exception as e:
                logger.error(f"Failed to read error log file {log_file_path}: {e}")
    except Exception as e:
        logger.error(f"Failed to get error logs: {e}")
    
    return error_logs
