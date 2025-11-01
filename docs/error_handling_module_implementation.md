# Error Handling Module Implementation

## Overview

The Error Handling module provides comprehensive error tracking, logging, and notification capabilities for the VisiGate system. It ensures that errors are properly captured, logged, and that administrators are notified of critical issues, enabling quick resolution and minimizing system downtime.

## Module Structure

The Error Handling module is implemented in `src/utils/error_handling.py` and consists of the following components:

- `ErrorHandler` class: Core error handling functionality
- Error logging and storage
- Error notification system
- Error categorization and prioritization
- Web interface integration for error viewing

## Implementation Details

### ErrorHandler Class

The `ErrorHandler` class is responsible for capturing, logging, and notifying about errors:

```python
class ErrorHandler:
    def __init__(self, config):
        """
        Initialize the error handler.
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.log_path = config['error_handling']['log_path']
        self.max_log_size = config['error_handling']['max_log_size']
        self.backup_count = config['error_handling']['backup_count']
        self.email_notifications = config['error_handling']['email_notifications']
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_path, exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger('VisiGate.error_handler')
        
        # Set up file handler for error logs
        self._setup_file_handler()
        
        # Register global exception handler
        sys.excepthook = self.global_exception_handler
```

### Error Logging

Errors are logged to rotating log files with detailed information:

```python
def _setup_file_handler(self):
    """
    Set up rotating file handler for error logs.
    """
    log_file = os.path.join(self.log_path, 'error.log')
    handler = RotatingFileHandler(
        log_file,
        maxBytes=self.max_log_size,
        backupCount=self.backup_count
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    self.logger.addHandler(handler)
    self.logger.setLevel(logging.ERROR)

def log_error(self, error, module_name, function_name, additional_info=None):
    """
    Log an error with detailed information.
    
    Args:
        error (Exception): The exception object
        module_name (str): Name of the module where the error occurred
        function_name (str): Name of the function where the error occurred
        additional_info (dict, optional): Additional information about the error
    """
    # Create error details
    error_details = {
        'timestamp': datetime.datetime.now().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'module': module_name,
        'function': function_name,
        'traceback': traceback.format_exc()
    }
    
    # Add additional info if provided
    if additional_info:
        error_details['additional_info'] = additional_info
    
    # Log error to file
    self.logger.error(f"Error in {module_name}.{function_name}: {str(error)}")
    
    # Save detailed error information to JSON file
    self._save_error_details(error_details)
    
    # Send notification if enabled
    if self.email_notifications:
        self._send_error_notification(error_details)
    
    return error_details
```

### Detailed Error Storage

Detailed error information is stored in JSON files for later analysis:

```python
def _save_error_details(self, error_details):
    """
    Save detailed error information to a JSON file.
    
    Args:
        error_details (dict): Error details dictionary
    """
    # Create filename based on timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    error_type = error_details['error_type']
    filename = f"error_{timestamp}_{error_type}.json"
    filepath = os.path.join(self.log_path, filename)
    
    # Save error details to file
    with open(filepath, 'w') as f:
        json.dump(error_details, f, indent=4)
```

### Global Exception Handler

A global exception handler captures uncaught exceptions:

```python
def global_exception_handler(self, exc_type, exc_value, exc_traceback):
    """
    Global exception handler for uncaught exceptions.
    
    Args:
        exc_type: Exception type
        exc_value: Exception value
        exc_traceback: Exception traceback
    """
    # Don't log KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Get calling frame information
    frame = inspect.trace()[-1]
    module_name = frame[0].f_globals.get('__name__', 'unknown')
    function_name = frame[3]
    
    # Log the error
    self.log_error(exc_value, module_name, function_name)
```

### Error Notification

Critical errors trigger email notifications to administrators:

```python
def _send_error_notification(self, error_details):
    """
    Send an email notification about the error.
    
    Args:
        error_details (dict): Error details dictionary
    """
    # Get email configuration
    email_config = self.config['error_handling']['email_config']
    
    # Create email subject and body
    subject = f"VisiGate Error: {error_details['error_type']} in {error_details['module']}"
    body = f"""An error occurred in the VisiGate system:

Timestamp: {error_details['timestamp']}
Error Type: {error_details['error_type']}
Error Message: {error_details['error_message']}
Module: {error_details['module']}
Function: {error_details['function']}

Traceback:
{error_details['traceback']}
"""
    
    # Send email
    try:
        server = smtplib.SMTP(email_config['server'], email_config['port'])
        server.starttls()
        server.login(email_config['username'], email_config['password'])
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = email_config['from_addr']
        msg['To'] = ', '.join(email_config['to_addrs'])
        
        server.sendmail(
            email_config['from_addr'],
            email_config['to_addrs'],
            msg.as_string()
        )
        server.quit()
        
        self.logger.info(f"Error notification sent to {', '.join(email_config['to_addrs'])}")
    except Exception as e:
        self.logger.error(f"Failed to send error notification: {str(e)}")
```

### Error Retrieval and Analysis

The module provides functions to retrieve and analyze error logs:

```python
def get_recent_errors(self, limit=10):
    """
    Get recent error details.
    
    Args:
        limit (int): Maximum number of errors to retrieve
        
    Returns:
        list: List of error detail dictionaries
    """
    errors = []
    
    # Get list of error files
    error_files = [f for f in os.listdir(self.log_path) if f.startswith('error_') and f.endswith('.json')]
    
    # Sort by timestamp (newest first)
    error_files.sort(reverse=True)
    
    # Load error details from files
    for filename in error_files[:limit]:
        filepath = os.path.join(self.log_path, filename)
        try:
            with open(filepath, 'r') as f:
                error_details = json.load(f)
                errors.append(error_details)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Failed to load error details from {filepath}: {str(e)}")
    
    return errors

def get_error_statistics(self, days=7):
    """
    Get error statistics for the specified period.
    
    Args:
        days (int): Number of days to analyze
        
    Returns:
        dict: Error statistics
    """
    # Calculate start date
    start_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Get all error files
    error_files = [f for f in os.listdir(self.log_path) if f.startswith('error_') and f.endswith('.json')]
    
    # Initialize statistics
    stats = {
        'total_errors': 0,
        'error_types': {},
        'modules': {},
        'daily_counts': {}
    }
    
    # Process each error file
    for filename in error_files:
        filepath = os.path.join(self.log_path, filename)
        try:
            with open(filepath, 'r') as f:
                error_details = json.load(f)
                
                # Check if error is within the specified period
                error_time = datetime.datetime.fromisoformat(error_details['timestamp'])
                if error_time >= start_date:
                    # Increment total count
                    stats['total_errors'] += 1
                    
                    # Count by error type
                    error_type = error_details['error_type']
                    stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1
                    
                    # Count by module
                    module = error_details['module']
                    stats['modules'][module] = stats['modules'].get(module, 0) + 1
                    
                    # Count by day
                    day = error_time.strftime('%Y-%m-%d')
                    stats['daily_counts'][day] = stats['daily_counts'].get(day, 0) + 1
        except (json.JSONDecodeError, IOError, KeyError) as e:
            self.logger.warning(f"Failed to process error file {filepath}: {str(e)}")
    
    return stats
```

### Error Recovery

The module includes functions to attempt recovery from common errors:

```python
def attempt_recovery(self, error_type, context=None):
    """
    Attempt to recover from a specific error type.
    
    Args:
        error_type (str): Type of error to recover from
        context (dict, optional): Additional context for recovery
        
    Returns:
        bool: True if recovery was successful, False otherwise
    """
    recovery_successful = False
    
    # Log recovery attempt
    self.logger.info(f"Attempting recovery from {error_type} error")
    
    # Attempt recovery based on error type
    if error_type == 'DatabaseError':
        recovery_successful = self._recover_database(context)
    elif error_type == 'CameraError':
        recovery_successful = self._recover_camera(context)
    elif error_type == 'NetworkError':
        recovery_successful = self._recover_network(context)
    
    # Log recovery result
    if recovery_successful:
        self.logger.info(f"Recovery from {error_type} error successful")
    else:
        self.logger.warning(f"Recovery from {error_type} error failed")
    
    return recovery_successful

def _recover_database(self, context):
    """
    Attempt to recover from database errors.
    
    Args:
        context (dict): Database context
        
    Returns:
        bool: True if recovery was successful, False otherwise
    """
    try:
        # Check if database file exists
        db_path = self.config['database']['path']
        if not os.path.exists(db_path):
            # Restore from backup if available
            backup_path = f"{db_path}.backup"
            if os.path.exists(backup_path):
                shutil.copy(backup_path, db_path)
                return True
            return False
        
        # Check if database is corrupt
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        
        if result != 'ok':
            # Database is corrupt, restore from backup
            backup_path = f"{db_path}.backup"
            if os.path.exists(backup_path):
                shutil.copy(backup_path, db_path)
                return True
        else:
            # Database is not corrupt
            return True
    except Exception as e:
        self.logger.error(f"Database recovery failed: {str(e)}")
        return False
```

## Web Interface Integration

The Error Handling module is integrated with the web interface through system routes defined in `src/web/system_routes.py`:

```python
@system_bp.route('/errors')
@login_required
@admin_required
def system_errors():
    """
    Display system errors page.
    """
    # Get recent errors
    recent_errors = error_handler.get_recent_errors(limit=50)
    
    # Get error statistics
    error_stats = error_handler.get_error_statistics(days=7)
    
    return render_template('system_errors.html', 
                           errors=recent_errors,
                           stats=error_stats)

@system_bp.route('/errors/<filename>')
@login_required
@admin_required
def view_error_details(filename):
    """
    View detailed information for a specific error.
    
    Args:
        filename (str): Error filename
    """
    # Validate filename to prevent directory traversal
    if not re.match(r'^error_\d{8}_\d{6}_[\w]+\.json$', filename):
        flash('Invalid error filename', 'danger')
        return redirect(url_for('system.system_errors'))
    
    # Load error details
    filepath = os.path.join(error_handler.log_path, filename)
    try:
        with open(filepath, 'r') as f:
            error_details = json.load(f)
    except (json.JSONDecodeError, IOError):
        flash('Error details not found', 'danger')
        return redirect(url_for('system.system_errors'))
    
    return render_template('error_details.html', error=error_details)
```

## Configuration

The Error Handling module is configured through the `error_handling` section in the configuration file:

```json
"error_handling": {
    "log_path": "logs/errors",
    "max_log_size": 10485760,
    "backup_count": 5,
    "email_notifications": false,
    "email_config": {
        "server": "smtp.example.com",
        "port": 587,
        "username": "user@example.com",
        "password": "password",
        "from_addr": "visigate@example.com",
        "to_addrs": ["admin@example.com"]
    }
}
```

Configuration options:

- `log_path`: Path to store error log files
- `max_log_size`: Maximum size of log files before rotation (in bytes)
- `backup_count`: Number of backup log files to keep
- `email_notifications`: Enable or disable email notifications
- `email_config`: Email server configuration
  - `server`: SMTP server address
  - `port`: SMTP server port
  - `username`: SMTP username
  - `password`: SMTP password
  - `from_addr`: Sender email address
  - `to_addrs`: List of recipient email addresses

## Dependencies

The Error Handling module depends on the following Python packages:

- `logging`: For logging errors
- `logging.handlers`: For rotating file handlers
- `smtplib`: For sending email notifications
- `email.mime.text`: For creating email messages
- `json`: For storing and parsing error details
- `datetime`: For timestamp handling
- `os`: For file and directory operations
- `sys`: For global exception handling
- `traceback`: For capturing stack traces
- `inspect`: For getting calling frame information
- `re`: For filename validation
- `shutil`: For file operations during recovery
- `sqlite3`: For database integrity checks

## Integration with Other Modules

The Error Handling module integrates with the following modules:

- **System Monitoring**: Errors are displayed on the system status page
- **Web Interface**: Error logs are accessible through the web interface
- **Notifications**: Critical errors trigger notifications to administrators

## Best Practices

1. **Error categorization**: Categorize errors by type and severity
2. **Detailed logging**: Include as much context as possible in error logs
3. **Proactive monitoring**: Regularly review error logs for patterns
4. **Recovery procedures**: Implement automatic recovery for common errors
5. **Notification thresholds**: Only notify administrators about critical errors

## Future Enhancements

Potential future enhancements for the Error Handling module:

1. **Error aggregation**: Group similar errors to reduce notification noise
2. **Error trend analysis**: Identify patterns and trends in error occurrences
3. **Machine learning**: Use ML to predict and prevent errors
4. **Custom recovery procedures**: Allow administrators to define custom recovery procedures
5. **Error severity levels**: Implement different handling based on error severity
6. **Integration with external monitoring**: Send errors to external monitoring systems
7. **Extended notification channels**: Add support for SMS, push notifications, etc.
