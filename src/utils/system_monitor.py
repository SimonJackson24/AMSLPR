
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
System monitoring utilities for the AMSLPR system.
"""

import os
import sys
import logging
import psutil
import time
import json
import threading
from datetime import datetime

logger = logging.getLogger('AMSLPR.system_monitor')

class SystemMonitor:
    """
    System monitor for the AMSLPR system.
    """
    
    def __init__(self, data_dir='/var/lib/amslpr', check_interval=60, notification_manager=None):
        """
        Initialize system monitor.
        
        Args:
            data_dir (str): Directory for system metrics
            check_interval (int): Check interval in seconds
            notification_manager (NotificationManager): Notification manager instance
        """
        self.data_dir = data_dir
        self.check_interval = check_interval
        self.notification_manager = notification_manager
        self.running = False
        self.thread = None
        
        # Create metrics directory if it doesn't exist
        self.metrics_dir = os.path.join(data_dir, 'metrics')
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Set thresholds
        self.cpu_threshold = 90  # 90% CPU usage
        self.memory_threshold = 90  # 90% memory usage
        self.disk_threshold = 90  # 90% disk usage
        self.temperature_threshold = 80  # 80°C
    
    def start(self):
        """
        Start system monitoring.
        """
        if self.running:
            logger.warning("System monitor is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("System monitor started")
    
    def stop(self):
        """
        Stop system monitoring.
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        
        logger.info("System monitor stopped")
    
    def _monitoring_loop(self):
        """
        Main monitoring loop.
        """
        while self.running:
            try:
                # Collect system metrics
                metrics = self.collect_metrics()
                
                # Save metrics to file
                self._save_metrics(metrics)
                
                # Check for alerts
                self._check_alerts(metrics)
                
                # Sleep until next check
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {e}")
                time.sleep(10)  # Sleep for a shorter time on error
    
    def collect_metrics(self):
        """
        Collect system metrics.
        
        Returns:
            dict: System metrics
        """
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Get CPU temperature (Raspberry Pi specific)
        temperature = None
        try:
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temperature = float(f.read()) / 1000.0
        except Exception as e:
            logger.warning(f"Failed to get CPU temperature: {e}")
        
        # Get network usage
        network = psutil.net_io_counters()
        
        # Get process information
        process = psutil.Process(os.getpid())
        process_cpu = process.cpu_percent(interval=1)
        process_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Create metrics dictionary
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'temperature': temperature,
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            },
            'process': {
                'cpu_percent': process_cpu,
                'memory_mb': process_memory
            }
        }
        
        return metrics
    
    def _save_metrics(self, metrics):
        """
        Save metrics to a file.
        
        Args:
            metrics (dict): System metrics
        """
        try:
            # Generate filename with date
            date = datetime.now().strftime('%Y%m%d')
            filename = f"metrics_{date}.jsonl"
            filepath = os.path.join(self.metrics_dir, filename)
            
            # Append metrics to file
            with open(filepath, 'a') as f:
                f.write(json.dumps(metrics) + '\n')
        except Exception as e:
            logger.error(f"Failed to save metrics to file: {e}")
    
    def _check_alerts(self, metrics):
        """
        Check for alert conditions.
        
        Args:
            metrics (dict): System metrics
        """
        alerts = []
        
        # Check CPU usage
        if metrics['system']['cpu_percent'] > self.cpu_threshold:
            alerts.append(f"High CPU usage: {metrics['system']['cpu_percent']}%")
        
        # Check memory usage
        if metrics['system']['memory_percent'] > self.memory_threshold:
            alerts.append(f"High memory usage: {metrics['system']['memory_percent']}%")
        
        # Check disk usage
        if metrics['system']['disk_percent'] > self.disk_threshold:
            alerts.append(f"High disk usage: {metrics['system']['disk_percent']}%")
        
        # Check temperature
        if metrics['system']['temperature'] and metrics['system']['temperature'] > self.temperature_threshold:
            alerts.append(f"High CPU temperature: {metrics['system']['temperature']}°C")
        
        # Send alerts if any
        if alerts and self.notification_manager:
            self._send_alert_notification(alerts)
    
    def _send_alert_notification(self, alerts):
        """
        Send alert notification.
        
        Args:
            alerts (list): List of alert messages
        """
        try:
            if not self.notification_manager:
                return
            
            # Create alert message
            alert_message = "AMSLPR System Alerts:\n\n"
            alert_message += "\n".join([f"- {alert}" for alert in alerts])
            
            # Send email notification
            self.notification_manager.send_email_notification(
                subject="AMSLPR System Alert",
                message=alert_message
            )
            
            logger.info(f"Alert notification sent: {', '.join(alerts)}")
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    def get_system_status(self):
        """
        Get current system status.
        
        Returns:
            dict: System status
        """
        # Collect current metrics
        metrics = self.collect_metrics()
        
        # Get uptime
        uptime_seconds = time.time() - psutil.boot_time()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        # Get disk space
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024 * 1024 * 1024)
        disk_used_gb = disk.used / (1024 * 1024 * 1024)
        disk_free_gb = disk.free / (1024 * 1024 * 1024)
        
        # Get memory
        memory = psutil.virtual_memory()
        memory_total_mb = memory.total / (1024 * 1024)
        memory_used_mb = memory.used / (1024 * 1024)
        memory_free_mb = memory.free / (1024 * 1024)
        
        # Create status dictionary
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime': uptime,
            'cpu': {
                'percent': metrics['system']['cpu_percent'],
                'count': psutil.cpu_count()
            },
            'memory': {
                'percent': metrics['system']['memory_percent'],
                'total_mb': memory_total_mb,
                'used_mb': memory_used_mb,
                'free_mb': memory_free_mb
            },
            'disk': {
                'percent': metrics['system']['disk_percent'],
                'total_gb': disk_total_gb,
                'used_gb': disk_used_gb,
                'free_gb': disk_free_gb
            },
            'temperature': metrics['system']['temperature'],
            'network': metrics['system']['network'],
            'process': metrics['process']
        }
        
        return status

def setup_system_monitor(app):
    """
    Set up system monitor for a Flask application.
    
    Args:
        app (Flask): Flask application instance
    
    Returns:
        SystemMonitor: System monitor instance
    """
    # Get data directory from environment or config
    data_dir = os.environ.get('AMSLPR_DATA_DIR', '/var/lib/amslpr')
    
    # Get notification manager if available
    notification_manager = app.config.get('NOTIFICATION_MANAGER')
    
    # Create system monitor
    system_monitor = SystemMonitor(
        data_dir=data_dir,
        check_interval=60,  # Check every 60 seconds
        notification_manager=notification_manager
    )
    
    # Start monitoring
    system_monitor.start()
    
    # Store in app config for access in routes
    app.config['SYSTEM_MONITOR'] = system_monitor
    
    # Register cleanup on app shutdown
    @app.teardown_appcontext
    def shutdown_system_monitor(exception=None):
        if system_monitor:
            system_monitor.stop()
    
    logger.info("System monitor initialized")
    return system_monitor
