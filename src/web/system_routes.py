
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
System routes for the AMSLPR web interface.
"""

import os
import logging
import subprocess
import shutil
from flask import Blueprint, render_template, request, jsonify, current_app, session, flash, redirect, url_for
from functools import wraps
from datetime import datetime

from src.utils.error_handling import get_error_logs
from src.web.security import rate_limit
from src.utils.user_management import UserManager, login_required, permission_required

logger = logging.getLogger('AMSLPR.web.system')

# Create blueprint
system_bp = Blueprint('system', __name__, url_prefix='/system')

# Initialize user manager
user_manager = UserManager()

@system_bp.route('/status')
@login_required(user_manager)
@permission_required('admin', user_manager)
def system_status():
    """
    System status page.
    """
    # Get system monitor from app config
    system_monitor = current_app.config.get('SYSTEM_MONITOR')
    
    # Default status structure if system monitor is not available
    default_status = {
        'uptime': 'Unknown',
        'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'cpu': {
            'percent': 0,
            'cores': 4,
            'temperature': 'N/A',
            'count': 4
        },
        'memory': {
            'percent': 0,
            'total': '0 GB',
            'used': '0 GB',
            'free': '0 GB',
            'total_mb': 0,
            'used_mb': 0,
            'free_mb': 0
        },
        'disk': {
            'percent': 0,
            'total': '0 GB',
            'used': '0 GB',
            'free': '0 GB',
            'total_gb': 0,
            'used_gb': 0,
            'free_gb': 0
        },
        'network': {
            'interfaces': [],
            'connections': 0,
            'bytes_sent': 0,
            'bytes_recv': 0,
            'packets_sent': 0,
            'packets_recv': 0
        },
        'process': {
            'cpu_percent': 0,
            'memory_mb': 0,
            'memory_percent': 0,
            'threads': 0,
            'open_files': 0
        },
        'processes': []
    }
    
    if not system_monitor:
        return render_template('system_status.html', status=default_status, errors=[])
    
    # Get system status
    try:
        status = system_monitor.get_system_status()
    except Exception as e:
        current_app.logger.error(f"Error getting system status: {str(e)}")
        status = default_status
    
    # Get recent errors
    log_dir = os.environ.get('AMSLPR_LOG_DIR', '/var/log/amslpr')
    errors = get_error_logs(log_dir=log_dir, limit=10)
    
    return render_template('system_status.html', status=status, errors=errors)

@system_bp.route('/clear-cache', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
@rate_limit
def clear_cache():
    """
    Clear application cache.
    """
    try:
        # Get cache directory
        cache_dir = os.path.join(current_app.root_path, 'cache')
        
        # Check if directory exists
        if os.path.exists(cache_dir):
            # Clear cache directory
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
            
            logger.info("Cache cleared successfully")
            return jsonify({'success': True})
        else:
            logger.warning("Cache directory does not exist")
            return jsonify({'success': True, 'message': 'Cache directory does not exist'})
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return jsonify({'success': False, 'error': str(e)})

@system_bp.route('/restart', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
@rate_limit
def restart_application():
    """
    Restart the application.
    """
    try:
        # Check if running as a service
        service_name = 'amslpr'
        service_exists = False
        
        try:
            # Check if service exists
            result = subprocess.run(['systemctl', 'is-active', service_name], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            service_exists = result.returncode == 0 or result.returncode == 3
        except Exception:
            service_exists = False
        
        if service_exists:
            # Restart service
            subprocess.Popen(['sudo', 'systemctl', 'restart', service_name])
            logger.info(f"Restarting {service_name} service")
        else:
            # Restart application (development mode)
            logger.info("Restarting application in development mode")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        return jsonify({'success': False, 'error': str(e)})

@system_bp.route('/logs')
@login_required(user_manager)
@permission_required('admin', user_manager)
def view_logs():
    """
    View system logs.
    """
    # Get log directory
    log_dir = os.environ.get('AMSLPR_LOG_DIR', '/var/log/amslpr')
    
    # Get log file
    log_file = os.path.join(log_dir, 'amslpr.log')
    
    # Check if file exists
    if not os.path.exists(log_file):
        return render_template('logs.html', logs=[], error="Log file not found")
    
    # Read log file (last 100 lines)
    try:
        result = subprocess.run(['tail', '-n', '100', log_file], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logs = result.stdout.decode('utf-8').splitlines()
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        logs = []
        error = str(e)
    
    return render_template('logs.html', logs=logs, error=None)

@system_bp.route('/integration', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def integration_settings():
    """
    Integration settings page.
    """
    # Get config or create a default one if not available
    config = current_app.config.get('AMSLPR_CONFIG', {
        'operating_mode': 'standalone',
        'paxton': {
            'enabled': False,
            'wiegand': {
                'data0_pin': 23,
                'data1_pin': 24,
                'facility_code': 1
            }
        },
        'nayax': {
            'enabled': False,
            'api_key': '',
            'terminal_id': '',
            'merchant_id': ''
        }
    })
    
    if request.method == 'POST':
        try:
            # Update operating mode
            config['operating_mode'] = request.form.get('operating_mode', 'standalone')
            
            # Update Paxton integration settings
            if config['operating_mode'] == 'paxton':
                config['paxton']['enabled'] = True
                config['paxton']['wiegand']['data0_pin'] = int(request.form.get('data0_pin', 23))
                config['paxton']['wiegand']['data1_pin'] = int(request.form.get('data1_pin', 24))
                config['paxton']['wiegand']['facility_code'] = int(request.form.get('facility_code', 1))
            else:
                config['paxton']['enabled'] = False
            
            # Update Nayax integration settings
            if config['operating_mode'] == 'nayax':
                config['nayax']['enabled'] = True
                config['nayax']['api_key'] = request.form.get('nayax_api_key', '')
                config['nayax']['terminal_id'] = request.form.get('nayax_terminal_id', '')
                config['nayax']['merchant_id'] = request.form.get('nayax_merchant_id', '')
                
                # Initialize parking settings if not already set
                if 'parking' not in config:
                    config['parking'] = {}
                
                # Initialize Nayax pricing settings if not already set
                if 'nayax' not in config['parking']:
                    config['parking']['nayax'] = {
                        'pricing_mode': 'hourly',
                        'hourly_rate': 2.00,
                        'fixed_rate': 5.00,
                        'currency_symbol': '$',
                        'free_period_minutes': 15,
                        'special_rates': {
                            'weekend': False,
                            'overnight': False
                        }
                    }
            else:
                config['nayax']['enabled'] = False
            
            # Save configuration
            from src.config.settings import save_config
            save_config(config, 'config.json')
            
            flash('Integration settings updated successfully.', 'success')
            logger.info(f"Integration settings updated. Operating mode: {config['operating_mode']}")
            
            # Restart required notification
            flash('Application restart required for changes to take effect.', 'warning')
            
        except Exception as e:
            flash(f'Error updating integration settings: {str(e)}', 'danger')
            logger.error(f"Error updating integration settings: {e}")
    
    return render_template('integration.html', 
                           config=config, 
                           operating_modes=['standalone', 'paxton', 'nayax'])

@system_bp.route('/settings', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def system_settings():
    """
    System settings page.
    """
    try:
        # Get current configuration
        config = current_app.config.get('AMSLPR_CONFIG', {})
        
        # Handle form submission
        if request.method == 'POST':
            # Update configuration
            config['system_name'] = request.form.get('system_name', 'AMSLPR')
            config['timezone'] = request.form.get('timezone', 'UTC')
            config['operating_mode'] = request.form.get('operating_mode', 'standalone')
            config['log_level'] = request.form.get('log_level', 'INFO')
            config['data_retention'] = int(request.form.get('data_retention', 90))
            config['enable_backups'] = 'enable_backups' in request.form
            config['enable_notifications'] = 'enable_notifications' in request.form
            
            # Save configuration
            from src.config.settings import save_config
            save_config(config)
            
            # Update app configuration
            current_app.config['AMSLPR_CONFIG'] = config
            
            flash('System settings updated successfully', 'success')
            return redirect(url_for('system.system_settings'))
        
        # Get disk usage information
        total, used, free = shutil.disk_usage('/')
        disk_usage = {
            'total': total // (2**30),  # GB
            'used': used // (2**30),    # GB
            'free': free // (2**30),    # GB
            'percent': (used / total) * 100
        }
        
        return render_template(
            'system/settings.html',
            config=config,
            disk_usage=disk_usage,
            operating_modes=['standalone', 'paxton', 'nayax']
        )
    except Exception as e:
        logger.error(f"Error in system settings: {str(e)}")
        flash(f"Error loading system settings: {str(e)}", 'danger')
        return redirect(url_for('main.dashboard'))

@system_bp.route('/api-keys', methods=['GET'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def api_key_management():
    """
    API key management page.
    """
    # Get database manager from app config
    db_manager = current_app.config.get('DB_MANAGER')
    
    if not db_manager:
        flash('Database manager not available', 'danger')
        return redirect(url_for('system.system_settings'))
    
    # Get all API keys
    api_keys = db_manager.get_api_keys()
    
    # Get messages from session
    messages = []
    if 'messages' in session:
        messages = session.pop('messages')
    
    # Get new API key from session if available
    new_key = None
    if 'new_api_key' in session:
        new_key = session.pop('new_api_key')
    
    return render_template('system/api_keys.html', api_keys=api_keys, messages=messages, new_key=new_key)

@system_bp.route('/api-keys/create', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
@rate_limit
def create_api_key():
    """
    Create a new API key.
    """
    # Get database manager from app config
    db_manager = current_app.config.get('DB_MANAGER')
    
    if not db_manager:
        flash('Database manager not available', 'danger')
        return redirect(url_for('system.api_key_management'))
    
    # Get form data
    key_name = request.form.get('key_name')
    expires_at = request.form.get('expires_at')
    
    if not key_name:
        flash('Key name is required', 'danger')
        return redirect(url_for('system.api_key_management'))
    
    # Convert expires_at to datetime if provided
    if expires_at:
        try:
            expires_at = datetime.strptime(expires_at, '%Y-%m-%d')
        except ValueError:
            flash('Invalid expiration date format', 'danger')
            return redirect(url_for('system.api_key_management'))
    
    # Generate API key
    new_key = db_manager.generate_api_key(key_name, expires_at)
    
    if not new_key:
        flash('Failed to generate API key', 'danger')
    else:
        flash('API key generated successfully', 'success')
        # Store the new key in session to display it once
        session['new_api_key'] = new_key
    
    return redirect(url_for('system.api_key_management'))

@system_bp.route('/api-keys/revoke', methods=['POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
@rate_limit
def revoke_api_key():
    """
    Revoke an API key.
    """
    # Get database manager from app config
    db_manager = current_app.config.get('DB_MANAGER')
    
    if not db_manager:
        flash('Database manager not available', 'danger')
        return redirect(url_for('system.api_key_management'))
    
    # Get API key from form
    api_key = request.form.get('api_key')
    
    if not api_key:
        flash('API key is required', 'danger')
        return redirect(url_for('system.api_key_management'))
    
    # Revoke API key
    success = db_manager.revoke_api_key(api_key)
    
    if not success:
        flash('Failed to revoke API key', 'danger')
    else:
        flash('API key revoked successfully', 'success')
    
    return redirect(url_for('system.api_key_management'))

@system_bp.route('/backup', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('admin', user_manager)
def backup_restore():
    """
    Backup and restore page.
    """
    # Get backup directory from app config
    backup_dir = current_app.config.get('BACKUP_DIR', '/app/backups')
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # List existing backups
    backups = []
    try:
        for filename in os.listdir(backup_dir):
            if filename.endswith('.zip') and filename.startswith('amslpr_backup_'):
                backup_path = os.path.join(backup_dir, filename)
                backup_time = datetime.fromtimestamp(os.path.getmtime(backup_path))
                backup_size = os.path.getsize(backup_path)
                backups.append({
                    'filename': filename,
                    'time': backup_time,
                    'size': backup_size,
                    'size_human': f"{backup_size / (1024*1024):.2f} MB"
                })
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        flash(f"Error listing backups: {str(e)}", 'danger')
    
    # Sort backups by time (newest first)
    backups.sort(key=lambda x: x['time'], reverse=True)
    
    # Handle backup creation
    if request.method == 'POST' and 'action' in request.form and request.form['action'] == 'create':
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"amslpr_backup_{timestamp}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Create backup using system utility
            # This is a simplified example - in a real system you would use a more robust backup method
            db_path = current_app.config.get('DB_MANAGER').db_path
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
            
            # Create a zip file with the database and config
            import zipfile
            with zipfile.ZipFile(backup_path, 'w') as backup_zip:
                # Add database file
                if os.path.exists(db_path):
                    backup_zip.write(db_path, os.path.basename(db_path))
                
                # Add config files
                if os.path.exists(config_dir):
                    for root, dirs, files in os.walk(config_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Add file to zip with relative path
                            backup_zip.write(file_path, os.path.relpath(file_path, os.path.dirname(config_dir)))
            
            flash(f"Backup created successfully: {backup_filename}", 'success')
            return redirect(url_for('system.backup_restore'))
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            flash(f"Error creating backup: {str(e)}", 'danger')
    
    # Handle backup restoration
    elif request.method == 'POST' and 'action' in request.form and request.form['action'] == 'restore' and 'backup_file' in request.form:
        try:
            backup_filename = request.form['backup_file']
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Validate backup file exists and is a valid backup
            if not os.path.exists(backup_path) or not backup_filename.startswith('amslpr_backup_') or not backup_filename.endswith('.zip'):
                flash("Invalid backup file selected", 'danger')
                return redirect(url_for('system.backup_restore'))
            
            # Extract backup
            import zipfile
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # Create a temporary directory for extraction
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    backup_zip.extractall(temp_dir)
                    
                    # Restore database
                    db_path = current_app.config.get('DB_MANAGER').db_path
                    db_backup = os.path.join(temp_dir, os.path.basename(db_path))
                    if os.path.exists(db_backup):
                        # Stop database connections
                        current_app.config.get('DB_MANAGER').close()
                        # Copy backup database to original location
                        shutil.copy2(db_backup, db_path)
                    
                    # Restore config files
                    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
                    config_backup = os.path.join(temp_dir, 'config')
                    if os.path.exists(config_backup):
                        # Copy config files
                        for root, dirs, files in os.walk(config_backup):
                            for file in files:
                                src_path = os.path.join(root, file)
                                # Get relative path and construct destination path
                                rel_path = os.path.relpath(src_path, config_backup)
                                dst_path = os.path.join(config_dir, rel_path)
                                # Create directory if it doesn't exist
                                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                                # Copy file
                                shutil.copy2(src_path, dst_path)
            
            flash("Backup restored successfully. The application will restart to apply changes.", 'success')
            
            # Schedule application restart
            from threading import Timer
            def restart_app():
                os._exit(0)  # This will cause the container to restart if configured correctly
            
            Timer(3.0, restart_app).start()
            return redirect(url_for('system.backup_restore'))
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            flash(f"Error restoring backup: {str(e)}", 'danger')
    
    # Handle backup deletion
    elif request.method == 'POST' and 'action' in request.form and request.form['action'] == 'delete' and 'backup_file' in request.form:
        try:
            backup_filename = request.form['backup_file']
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Validate backup file exists and is a valid backup
            if not os.path.exists(backup_path) or not backup_filename.startswith('amslpr_backup_') or not backup_filename.endswith('.zip'):
                flash("Invalid backup file selected", 'danger')
                return redirect(url_for('system.backup_restore'))
            
            # Delete backup file
            os.remove(backup_path)
            flash(f"Backup deleted: {backup_filename}", 'success')
            return redirect(url_for('system.backup_restore'))
        except Exception as e:
            logger.error(f"Error deleting backup: {str(e)}")
            flash(f"Error deleting backup: {str(e)}", 'danger')
    
    return render_template('system_backup.html', backups=backups)

def register_routes(app, database_manager=None):
    """
    Register system routes with a Flask application.
    
    Args:
        app (Flask): Flask application instance
        database_manager: Database manager instance (not used for system routes)
    """
    # Register blueprint
    app.register_blueprint(system_bp)
    
    # Set up backup directory in app config
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    app.config['BACKUP_DIR'] = backup_dir
    
    logger.info("System routes registered")
    
    return app
