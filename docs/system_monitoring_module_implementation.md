# System Monitoring Module Implementation

## Overview

The System Monitoring module provides comprehensive monitoring of system resources, performance metrics, and health status. It enables administrators to track system performance, identify potential issues, and receive alerts when resource usage exceeds defined thresholds.

## Module Structure

The System Monitoring module is implemented in `src/utils/system_monitor.py` and consists of the following components:

- `SystemMonitor` class: Core monitoring functionality
- System metrics collection and analysis
- Metrics logging and storage
- Alert generation based on thresholds
- Web interface integration via system routes

## Implementation Details

### SystemMonitor Class

The `SystemMonitor` class is responsible for collecting and analyzing system metrics:

```python
class SystemMonitor:
    def __init__(self, config):
        """
        Initialize the system monitor.
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.metrics_path = config['monitoring']['metrics_path']
        self.log_interval = config['monitoring']['log_interval']
        self.alert_thresholds = config['monitoring']['alert_thresholds']
        
        # Create metrics directory if it doesn't exist
        os.makedirs(self.metrics_path, exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger('AMSLPR.system_monitor')
        
        # Start monitoring thread if enabled
        if config['monitoring']['enabled']:
            self.start_monitoring()
```

### System Metrics Collection

The module collects the following metrics:

- CPU usage (percentage)
- Memory usage (percentage and absolute)
- Disk usage (percentage and absolute)
- CPU temperature (Raspberry Pi specific)
- Network statistics (bytes sent/received)
- System uptime
- Process information

Metrics are collected using the `psutil` library:

```python
def get_system_stats(self):
    """
    Get current system statistics.
    
    Returns:
        dict: Dictionary containing system statistics
    """
    stats = {
        'timestamp': datetime.datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'memory_used': psutil.virtual_memory().used,
        'memory_total': psutil.virtual_memory().total,
        'disk_percent': psutil.disk_usage('/').percent,
        'disk_used': psutil.disk_usage('/').used,
        'disk_total': psutil.disk_usage('/').total,
        'uptime': int(time.time() - psutil.boot_time())
    }
    
    # Get network statistics
    net_io = psutil.net_io_counters()
    stats['network_sent'] = net_io.bytes_sent
    stats['network_received'] = net_io.bytes_recv
    
    # Get CPU temperature (Raspberry Pi specific)
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
            stats['cpu_temp'] = temp
    except (IOError, ValueError):
        stats['cpu_temp'] = 0.0
    
    return stats
```

### Metrics Logging

System metrics are logged to JSON files for historical analysis:

```python
def log_metrics(self):
    """
    Log current system metrics to a file.
    """
    stats = self.get_system_stats()
    
    # Create filename based on date
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = f"metrics_{date_str}.json"
    filepath = os.path.join(self.metrics_path, filename)
    
    # Append metrics to file
    with open(filepath, 'a') as f:
        f.write(json.dumps(stats) + '\n')
    
    # Check for alerts
    self.check_alerts(stats)
    
    return stats
```

### Alert Generation

The module generates alerts when resource usage exceeds defined thresholds:

```python
def check_alerts(self, stats):
    """
    Check if any metrics exceed alert thresholds.
    
    Args:
        stats (dict): Current system statistics
    """
    alerts = []
    
    # Check CPU usage
    if stats['cpu_percent'] > self.alert_thresholds['cpu_percent']:
        alerts.append(f"CPU usage is high: {stats['cpu_percent']}%")
    
    # Check memory usage
    if stats['memory_percent'] > self.alert_thresholds['memory_percent']:
        alerts.append(f"Memory usage is high: {stats['memory_percent']}%")
    
    # Check disk usage
    if stats['disk_percent'] > self.alert_thresholds['disk_percent']:
        alerts.append(f"Disk usage is high: {stats['disk_percent']}%")
    
    # Check CPU temperature
    if 'cpu_temp' in stats and stats['cpu_temp'] > self.alert_thresholds['cpu_temp']:
        alerts.append(f"CPU temperature is high: {stats['cpu_temp']}°C")
    
    # Send alerts if any
    if alerts:
        self.send_alerts(alerts)
```

### Monitoring Thread

A background thread collects metrics at regular intervals:

```python
def start_monitoring(self):
    """
    Start the monitoring thread.
    """
    self.stop_monitoring_event = threading.Event()
    self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
    self.monitoring_thread.daemon = True
    self.monitoring_thread.start()
    self.logger.info("System monitoring started")

def _monitoring_loop(self):
    """
    Monitoring thread function.
    """
    while not self.stop_monitoring_event.is_set():
        try:
            self.log_metrics()
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {str(e)}")
        
        # Sleep until next interval
        self.stop_monitoring_event.wait(self.log_interval)

def stop_monitoring(self):
    """
    Stop the monitoring thread.
    """
    if hasattr(self, 'stop_monitoring_event'):
        self.stop_monitoring_event.set()
        self.monitoring_thread.join()
        self.logger.info("System monitoring stopped")
```

### Historical Data Analysis

The module provides functions to analyze historical data:

```python
def get_historical_data(self, days=1):
    """
    Get historical system metrics.
    
    Args:
        days (int): Number of days of historical data to retrieve
        
    Returns:
        list: List of metric dictionaries
    """
    metrics = []
    start_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Iterate through metric files
    for filename in os.listdir(self.metrics_path):
        if filename.startswith('metrics_') and filename.endswith('.json'):
            # Extract date from filename
            try:
                file_date_str = filename.replace('metrics_', '').replace('.json', '')
                file_date = datetime.datetime.strptime(file_date_str, '%Y-%m-%d')
                
                # Skip files older than start date
                if file_date < start_date:
                    continue
                    
                # Read metrics from file
                filepath = os.path.join(self.metrics_path, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            metric = json.loads(line.strip())
                            metrics.append(metric)
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in {filepath}")
            except ValueError:
                self.logger.warning(f"Invalid filename format: {filename}")
    
    # Sort metrics by timestamp
    metrics.sort(key=lambda x: x['timestamp'])
    
    return metrics
```

## Web Interface Integration

The System Monitoring module is integrated with the web interface through system routes defined in `src/web/system_routes.py`:

```python
@system_bp.route('/status')
@login_required
@admin_required
def system_status():
    """
    Display system status page.
    """
    # Get current system stats
    stats = system_monitor.get_system_stats()
    
    # Get historical data for charts
    historical_data = system_monitor.get_historical_data(days=1)
    
    # Process historical data for charts
    timestamps = []
    cpu_values = []
    memory_values = []
    disk_values = []
    
    for metric in historical_data:
        timestamps.append(datetime.datetime.fromisoformat(metric['timestamp']).strftime('%H:%M'))
        cpu_values.append(metric['cpu_percent'])
        memory_values.append(metric['memory_percent'])
        disk_values.append(metric['disk_percent'])
    
    # Get recent errors
    recent_errors = error_handler.get_recent_errors(limit=5)
    
    return render_template('system_status.html', 
                           stats=stats, 
                           timestamps=timestamps,
                           cpu_values=cpu_values,
                           memory_values=memory_values,
                           disk_values=disk_values,
                           recent_errors=recent_errors)
```

## Configuration

The System Monitoring module is configured through the `monitoring` section in the configuration file:

```json
"monitoring": {
    "enabled": true,
    "log_interval": 300,
    "metrics_path": "data/metrics",
    "alert_thresholds": {
        "cpu_percent": 80,
        "memory_percent": 80,
        "disk_percent": 90,
        "cpu_temp": 70
    }
}
```

Configuration options:

- `enabled`: Enable or disable system monitoring
- `log_interval`: Interval between metric collections (in seconds)
- `metrics_path`: Path to store metric files
- `alert_thresholds`: Thresholds for generating alerts
  - `cpu_percent`: CPU usage threshold (percentage)
  - `memory_percent`: Memory usage threshold (percentage)
  - `disk_percent`: Disk usage threshold (percentage)
  - `cpu_temp`: CPU temperature threshold (°C)

## Dependencies

The System Monitoring module depends on the following Python packages:

- `psutil`: For collecting system metrics
- `threading`: For background monitoring
- `json`: For storing and parsing metrics
- `datetime`: For timestamp handling
- `os`: For file and directory operations
- `logging`: For logging events and errors

## Integration with Other Modules

The System Monitoring module integrates with the following modules:

- **Error Handling**: Alerts are sent through the error handling module
- **Web Interface**: System status is displayed through the web interface
- **Notifications**: Alerts can trigger notifications to administrators

## Future Enhancements

Potential future enhancements for the System Monitoring module:

1. **Process-specific monitoring**: Monitor resource usage of specific processes
2. **Network monitoring**: Enhanced network traffic analysis
3. **Performance benchmarking**: Automatic performance testing
4. **Predictive analytics**: Predict resource usage trends
5. **Custom metrics**: Allow users to define custom metrics to monitor
6. **Graphical reporting**: Generate PDF reports of system performance
7. **Remote monitoring**: Monitor multiple AMSLPR instances from a central location
