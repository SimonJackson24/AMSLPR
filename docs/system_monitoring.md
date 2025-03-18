# System Monitoring Guide

## Overview

This guide provides instructions for monitoring the health and performance of the AMSLPR system. Effective monitoring is essential for identifying and addressing issues before they impact system availability or performance.

The AMSLPR system includes a comprehensive monitoring module that tracks system resources, logs metrics, and provides alerts when thresholds are exceeded.

## Monitoring Components

The AMSLPR monitoring system includes the following components:

1. **Resource Monitoring**: Tracks CPU, memory, disk usage, and system uptime.
2. **Application Monitoring**: Monitors application-specific metrics such as recognition performance and database operations.
3. **Error Monitoring**: Tracks and logs errors and exceptions.
4. **Alert System**: Sends notifications when thresholds are exceeded or errors occur.

## Monitoring Dashboard

The AMSLPR system includes a web-based monitoring dashboard that provides real-time information about system health and performance. The dashboard is accessible at:

```
http://<your-server-address>/admin/monitoring
```

### Dashboard Features

- **System Overview**: Displays a summary of system health and key metrics.
- **Resource Utilization**: Shows CPU, memory, and disk usage over time.
- **Application Metrics**: Displays application-specific metrics such as recognition rate and database operations.
- **Error Log**: Shows recent errors and exceptions.
- **Alert History**: Displays recent alerts and their status.

## Monitoring API

The AMSLPR system also provides a monitoring API that allows you to access monitoring data programmatically. The API is accessible at:

```
http://<your-server-address>/api/system/status
```

This endpoint returns a JSON object containing current system metrics:

```json
{
  "cpu_percent": 25.3,
  "memory_percent": 42.7,
  "disk_percent": 68.2,
  "uptime": 86400,
  "recognition_rate": 98.5,
  "database_size": 25600000,
  "error_count": 0,
  "timestamp": "2025-03-14T21:37:44Z"
}
```

## Alert Configuration

The AMSLPR monitoring system can be configured to send alerts when thresholds are exceeded or errors occur. Alerts can be sent via email, SMS, or webhook.

### Configuring Alert Thresholds

Alert thresholds can be configured in the web interface at:

```
http://<your-server-address>/admin/monitoring/alerts
```

The following thresholds can be configured:

- **CPU Usage**: Percentage of CPU usage that triggers an alert (default: 90%).
- **Memory Usage**: Percentage of memory usage that triggers an alert (default: 90%).
- **Disk Usage**: Percentage of disk usage that triggers an alert (default: 90%).
- **Error Rate**: Number of errors per minute that triggers an alert (default: 10).

### Configuring Alert Destinations

Alert destinations can be configured in the web interface at:

```
http://<your-server-address>/admin/monitoring/alerts/destinations
```

The following alert destinations are supported:

- **Email**: Sends alerts via SMTP.
- **SMS**: Sends alerts via SMS (requires a supported SMS gateway).
- **Webhook**: Sends alerts to a specified URL.

## Log Files

The AMSLPR monitoring system logs metrics and events to log files for historical analysis. Log files are stored in the following directories:

- **Metrics Logs**: `/var/lib/amslpr/logs/metrics`
- **Error Logs**: `/var/lib/amslpr/logs/errors`
- **Application Logs**: `/var/lib/amslpr/logs/app`

### Log Rotation

Log files are automatically rotated to prevent them from consuming too much disk space. The rotation policy can be configured in the system configuration file.

## External Monitoring

In addition to the built-in monitoring system, the AMSLPR system can be monitored using external monitoring tools such as Nagios, Zabbix, or Prometheus.

### Nagios Integration

The AMSLPR system includes a Nagios plugin that can be used to monitor system health and performance. The plugin is located at:

```
/opt/amslpr/scripts/check_amslpr.py
```

To use the plugin, add the following to your Nagios configuration:

```
define command {
  command_name check_amslpr
  command_line $USER1$/check_amslpr.py -H $HOSTADDRESS$ -p $ARG1$ -w $ARG2$ -c $ARG3$
}

define service {
  host_name amslpr-server
  service_description AMSLPR CPU Usage
  check_command check_amslpr!cpu!80!90
  use generic-service
}

define service {
  host_name amslpr-server
  service_description AMSLPR Memory Usage
  check_command check_amslpr!memory!80!90
  use generic-service
}

define service {
  host_name amslpr-server
  service_description AMSLPR Disk Usage
  check_command check_amslpr!disk!80!90
  use generic-service
}
```

### Prometheus Integration

The AMSLPR system can expose metrics in Prometheus format at:

```
http://<your-server-address>/metrics
```

To configure Prometheus to scrape these metrics, add the following to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'amslpr'
    scrape_interval: 15s
    static_configs:
      - targets: ['<your-server-address>']
```

## Performance Tuning

Based on monitoring data, you may need to tune the AMSLPR system for optimal performance. For guidance on performance tuning, refer to the [Performance Tuning Guide](performance_tuning.md).

## Troubleshooting

### Monitoring System Not Working

If the monitoring system is not working correctly, check the following:

1. **Service Status**: Ensure that the AMSLPR service is running.
2. **Log Files**: Check the monitoring log files for errors.
3. **Permissions**: Ensure that the AMSLPR service has permission to write to the log directories.

### Alerts Not Being Sent

If alerts are not being sent, check the following:

1. **Alert Configuration**: Verify that alert thresholds and destinations are configured correctly.
2. **Email Configuration**: If using email alerts, verify that the SMTP configuration is correct.
3. **Network Connectivity**: Ensure that the AMSLPR server can connect to the alert destination (SMTP server, SMS gateway, or webhook URL).

## Conclusion

Effective monitoring is essential for maintaining a healthy and performant AMSLPR system. The built-in monitoring system provides comprehensive tracking of system resources, application metrics, and errors, with configurable alerts to notify you of issues before they impact system availability or performance.

For additional assistance with monitoring, please refer to the [Troubleshooting Guide](troubleshooting.md) or contact support.
