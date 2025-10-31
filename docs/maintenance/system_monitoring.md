# System Monitoring and Maintenance Guide

This guide covers comprehensive monitoring setup, maintenance procedures, and alerting configuration for AMSLPR systems.

## Monitoring Architecture

### Monitoring Stack Components

1. **Application Metrics:** Performance and health metrics from AMSLPR
2. **System Metrics:** CPU, memory, disk, and network statistics
3. **Infrastructure Metrics:** Container and orchestration metrics
4. **Business Metrics:** License plate recognition success rates and throughput

### Monitoring Tools Integration

#### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'amslpr'
    static_configs:
      - targets: ['localhost:5001']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
    scrape_interval: 30s
```

#### Application Metrics Endpoint

```python
# src/web/metrics.py
from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from src.utils.metrics import get_metrics

metrics_bp = Blueprint('metrics', __name__)

@metrics_bp.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Register metrics collectors
from prometheus_client import Counter, Histogram, Gauge

# OCR metrics
ocr_processing_time = Histogram(
    'amslpr_ocr_processing_time_seconds',
    'Time spent processing OCR requests',
    ['method', 'status']
)

ocr_requests_total = Counter(
    'amslpr_ocr_requests_total',
    'Total number of OCR requests',
    ['method', 'status']
)

# Camera metrics
camera_connections_active = Gauge(
    'amslpr_camera_connections_active',
    'Number of active camera connections'
)

camera_frames_processed = Counter(
    'amslpr_camera_frames_processed_total',
    'Total number of camera frames processed'
)

# Database metrics
db_connections_active = Gauge(
    'amslpr_db_connections_active',
    'Number of active database connections'
)

db_query_duration = Histogram(
    'amslpr_db_query_duration_seconds',
    'Database query duration',
    ['query_type']
)
```

## Key Metrics to Monitor

### Application Performance Metrics

| Metric | Description | Threshold | Alert Level |
|--------|-------------|-----------|-------------|
| `ocr_processing_time` | OCR processing duration | >500ms | Warning |
| `ocr_success_rate` | OCR recognition success rate | <95% | Critical |
| `api_response_time` | API endpoint response time | >200ms | Warning |
| `error_rate` | Application error rate | >5% | Critical |

### System Resource Metrics

| Metric | Description | Threshold | Alert Level |
|--------|-------------|-----------|-------------|
| `cpu_usage_percent` | CPU utilization | >85% | Warning |
| `memory_usage_percent` | Memory utilization | >90% | Critical |
| `disk_usage_percent` | Disk utilization | >85% | Warning |
| `network_errors_total` | Network error count | >10/min | Warning |

### Business Metrics

| Metric | Description | Threshold | Alert Level |
|--------|-------------|-----------|-------------|
| `plates_recognized_total` | Total plates recognized | - | Info |
| `recognition_accuracy` | Recognition accuracy rate | <90% | Warning |
| `processing_throughput` | Plates processed per minute | <10/min | Warning |

## Alerting Configuration

### Alert Rules

```yaml
# alert_rules.yml
groups:
  - name: amslpr_application
    rules:
      - alert: OCRProcessingSlow
        expr: histogram_quantile(0.95, rate(amslpr_ocr_processing_time_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "OCR processing is slow"
          description: "95th percentile OCR processing time is {{ $value }}s"

      - alert: OCRSuccessRateLow
        expr: rate(amslpr_ocr_requests_total{status="success"}[5m]) / rate(amslpr_ocr_requests_total[5m]) < 0.95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "OCR success rate is low"
          description: "OCR success rate is {{ $value | humanizePercentage }}"

      - alert: APIResponseSlow
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds{job="amslpr"}[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API response time is slow"
          description: "95th percentile API response time is {{ $value }}s"

  - name: amslpr_system
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}%"

      - alert: HighMemoryUsage
        expr: memory_usage_percent > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}%"

      - alert: LowDiskSpace
        expr: disk_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk usage is {{ $value }}%"

      - alert: CameraConnectionLost
        expr: amslpr_camera_connections_active == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Camera connection lost"
          description: "No active camera connections detected"
```

### Alert Manager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@amslpr.com'
  smtp_auth_username: 'alerts@amslpr.com'
  smtp_auth_password: 'your-password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'team'
  routes:
  - match:
      severity: critical
    receiver: 'team-critical'

receivers:
- name: 'team'
  email_configs:
  - to: 'team@company.com'
    send_resolved: true

- name: 'team-critical'
  email_configs:
  - to: 'team@company.com'
    send_resolved: true
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#alerts-critical'
    send_resolved: true
```

## Dashboard Configuration

### Grafana Dashboard Setup

```json
{
  "dashboard": {
    "title": "AMSLPR System Overview",
    "tags": ["amslpr", "monitoring"],
    "timezone": "UTC",
    "panels": [
      {
        "title": "OCR Processing Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(amslpr_ocr_processing_time_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(amslpr_ocr_processing_time_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "cpu_usage_percent",
            "legendFormat": "CPU %"
          },
          {
            "expr": "memory_usage_percent",
            "legendFormat": "Memory %"
          },
          {
            "expr": "disk_usage_percent",
            "legendFormat": "Disk %"
          }
        ]
      },
      {
        "title": "OCR Success Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(amslpr_ocr_requests_total{status=\"success\"}[1h]) / rate(amslpr_ocr_requests_total[1h]) * 100",
            "legendFormat": "Success Rate %"
          }
        ]
      }
    ]
  }
}
```

## Log Management

### Log Collection and Aggregation

#### Fluent Bit Configuration

```yaml
# fluent-bit.conf
[SERVICE]
    Flush         5
    Log_Level     info
    Daemon        off

[INPUT]
    Name              tail
    Path              /app/logs/*.log
    Parser            docker
    Tag               amslpr.*
    Refresh_Interval  5

[OUTPUT]
    Name  elasticsearch
    Match amslpr.*
    Host  elasticsearch
    Port  9200
    Index amslpr
    Logstash_Format On
    Logstash_Prefix amslpr
```

#### Logstash Configuration

```yaml
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][log_type] == "amslpr" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:logger} - %{GREEDYDATA:message}" }
    }

    date {
      match => [ "timestamp", "ISO8601" ]
      target => "@timestamp"
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "amslpr-%{+YYYY.MM.dd}"
  }
}
```

### Log Analysis

#### Common Log Patterns

```bash
# Search for errors
grep "ERROR" /app/logs/amslpr.log | tail -20

# Count error types
grep "ERROR" /app/logs/amslpr.log | sed 's/.*ERROR - //' | sort | uniq -c | sort -nr

# Find slow OCR processing
grep "OCR processing time" /app/logs/amslpr.log | awk '$NF > 1000 {print}'

# Monitor camera connections
grep "camera.*connected\|camera.*disconnected" /app/logs/amslpr.log
```

#### Log Queries in Elasticsearch

```json
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "level": "ERROR"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h",
              "lte": "now"
            }
          }
        }
      ]
    }
  },
  "size": 100,
  "sort": [
    {
      "@timestamp": {
        "order": "desc"
      }
    }
  ]
}
```

## Maintenance Procedures

### Daily Maintenance Tasks

```bash
#!/bin/bash
# Daily maintenance script

echo "Starting daily maintenance..."

# 1. Log rotation
logrotate /etc/logrotate.d/amslpr

# 2. Clear old cache entries
redis-cli KEYS "amslpr:*" | xargs redis-cli DEL

# 3. Database maintenance
sqlite3 /app/data/amslpr.db "VACUUM;"

# 4. Check disk space
DISK_USAGE=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
    # Send alert
fi

# 5. Verify service health
curl -f http://localhost:5001/health > /dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Service health check failed"
    # Send alert and attempt restart
    systemctl restart amslpr
fi

echo "Daily maintenance completed"
```

### Weekly Maintenance Tasks

```bash
#!/bin/bash
# Weekly maintenance script

echo "Starting weekly maintenance..."

# 1. Full database optimization
sqlite3 /app/data/amslpr.db "REINDEX;"
sqlite3 /app/data/amslpr.db "ANALYZE;"

# 2. Clean old images (older than 30 days)
find /app/data/images -type f -mtime +30 -delete

# 3. Update dependencies
pip install --upgrade -r requirements.txt

# 4. Security scan
# Add security scanning commands here

# 5. Backup verification
python /app/scripts/verify_backup.py

echo "Weekly maintenance completed"
```

### Monthly Maintenance Tasks

```bash
#!/bin/bash
# Monthly maintenance script

echo "Starting monthly maintenance..."

# 1. Performance benchmarking
python /app/scripts/benchmark.py

# 2. Full system backup
/app/scripts/backup.sh full

# 3. Log analysis and reporting
python /app/scripts/log_analysis.py --period monthly

# 4. Security audit
# Add security audit commands here

# 5. Capacity planning review
python /app/scripts/capacity_planning.py

echo "Monthly maintenance completed"
```

## Backup and Recovery

### Backup Strategy

#### Database Backup

```bash
#!/bin/bash
# Database backup script

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/amslpr_db_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sqlite3 /app/data/amslpr.db ".backup $BACKUP_FILE"

# Compress backup
gzip $BACKUP_FILE

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "amslpr_db_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: ${BACKUP_FILE}.gz"
```

#### Configuration Backup

```bash
#!/bin/bash
# Configuration backup script

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/amslpr_config_${TIMESTAMP}.tar.gz"

# Create backup
tar -czf $BACKUP_FILE \
    -C /app config/ \
    --exclude="*.log" \
    --exclude="*.tmp"

# Clean old backups
find $BACKUP_DIR -name "amslpr_config_*.tar.gz" -mtime +30 -delete

echo "Configuration backup completed: $BACKUP_FILE"
```

### Recovery Procedures

#### Database Recovery

```bash
#!/bin/bash
# Database recovery script

BACKUP_FILE=$1
RECOVERY_DB="/app/data/amslpr_recovered.db"

# Stop application
systemctl stop amslpr

# Extract backup
gunzip -c $BACKUP_FILE > $RECOVERY_DB

# Verify database integrity
sqlite3 $RECOVERY_DB "PRAGMA integrity_check;"

# Replace current database
mv /app/data/amslpr.db /app/data/amslpr.db.backup
mv $RECOVERY_DB /app/data/amslpr.db

# Start application
systemctl start amslpr

echo "Database recovery completed"
```

#### Full System Recovery

```bash
#!/bin/bash
# Full system recovery script

# 1. Stop services
docker-compose down

# 2. Restore database
./scripts/recover_database.sh /path/to/backup.sql.gz

# 3. Restore configuration
./scripts/recover_config.sh /path/to/config.tar.gz

# 4. Restore data
./scripts/recover_data.sh /path/to/data.tar.gz

# 5. Start services
docker-compose up -d

# 6. Verify recovery
curl -f http://localhost:5001/health
```

## Security Monitoring

### Security Event Monitoring

```yaml
# Security monitoring rules
groups:
  - name: amslpr_security
    rules:
      - alert: MultipleFailedLogins
        expr: rate(failed_login_attempts_total[5m]) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Multiple failed login attempts detected"
          description: "Rate of failed login attempts: {{ $value }}/s"

      - alert: SuspiciousAPIActivity
        expr: rate(api_requests_total{status="403"}[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Suspicious API activity detected"
          description: "High rate of 403 responses: {{ $value }}/s"

      - alert: UnusualTrafficPattern
        expr: rate(http_requests_total[5m]) > 2 * rate(http_requests_total[1h])
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Unusual traffic pattern detected"
          description: "Traffic spike detected"
```

### Security Audit Logging

```python
# Security audit logging
import logging
from datetime import datetime

security_logger = logging.getLogger('security')

def log_security_event(event_type, user, ip_address, details):
    """Log security-related events"""
    security_logger.info(
        f"SECURITY_EVENT: {event_type} | User: {user} | IP: {ip_address} | Details: {details}"
    )

# Usage examples
log_security_event("LOGIN_SUCCESS", "admin", "192.168.1.100", "Web login")
log_security_event("LOGIN_FAILED", "unknown", "10.0.0.1", "Invalid credentials")
log_security_event("API_ACCESS_DENIED", "user1", "192.168.1.200", "Insufficient permissions")
```

## Capacity Planning

### Resource Usage Analysis

```python
# Capacity planning script
from src.utils.capacity_planner import CapacityPlanner

planner = CapacityPlanner()
analysis = planner.analyze_usage(
    time_range="30d",
    metrics=["cpu", "memory", "disk", "network"]
)

print(f"Current peak CPU usage: {analysis['cpu']['peak']}%")
print(f"Recommended CPU cores: {analysis['cpu']['recommended_cores']}")
print(f"Predicted growth (6 months): {analysis['cpu']['growth_rate']}%")
```

### Scaling Recommendations

| Current Load | Recommendation | Action |
|--------------|----------------|--------|
| CPU > 80% | Scale vertically | Increase CPU cores |
| Memory > 85% | Scale vertically | Increase memory |
| Disk > 90% | Scale storage | Add more storage |
| Network > 80% | Optimize network | Implement caching/CDN |
| Response time > 500ms | Scale horizontally | Add more instances |

## Incident Response

### Incident Response Plan

1. **Detection**
   - Monitor alerts and dashboards
   - Check system logs
   - Verify service health

2. **Assessment**
   - Determine impact and scope
   - Identify root cause
   - Assess business impact

3. **Containment**
   - Isolate affected systems
   - Stop compromised services
   - Implement temporary fixes

4. **Recovery**
   - Restore from backups
   - Apply fixes and patches
   - Test system functionality

5. **Lessons Learned**
   - Document incident details
   - Update procedures
   - Implement preventive measures

### Communication Templates

#### Internal Incident Notification

```
Subject: AMSLPR Incident - [Severity] - [Brief Description]

Incident Details:
- Start Time: [Timestamp]
- Severity: [Critical/High/Medium/Low]
- Affected Systems: [List of affected components]
- Impact: [Description of impact]
- Status: [Investigating/Contained/Resolved]

Current Actions:
- [List of actions being taken]

Next Steps:
- [Planned next steps]

Contact: [Incident response team contact]
```

#### External Stakeholder Communication

```
Subject: AMSLPR Service Update - [Brief Description]

Dear [Stakeholder],

We are currently experiencing [brief description of issue] with our AMSLPR service.

Current Status:
- Service Impact: [Minimal/Moderate/Severe]
- Estimated Resolution: [Timeframe]

We apologize for any inconvenience this may cause. Our team is working diligently to resolve this issue.

For updates, please visit: [Status page URL]

Best regards,
AMSLPR Operations Team
```

## Compliance and Auditing

### Audit Logging

```python
# Comprehensive audit logging
from src.utils.audit import AuditLogger

audit = AuditLogger()

@audit.log_action
def update_vehicle_plate(old_plate, new_plate, user):
    """Update vehicle license plate with audit logging"""
    # Update logic here
    pass

@audit.log_access
def access_vehicle_data(plate_number, user, action):
    """Log access to vehicle data"""
    # Access logic here
    pass
```

### Compliance Monitoring

```yaml
# Compliance monitoring rules
groups:
  - name: compliance
    rules:
      - alert: AuditLogGap
        expr: time() - audit_log_last_entry_seconds > 3600
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Audit log gap detected"
          description: "No audit entries for over an hour"

      - alert: DataRetentionViolation
        expr: data_retention_days > 365
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Data retention policy violation"
          description: "Data older than retention period detected"
```

## Best Practices

### Monitoring Best Practices

1. **Define clear metrics and KPIs**
2. **Set appropriate alert thresholds**
3. **Implement proper log aggregation**
4. **Create comprehensive dashboards**
5. **Establish incident response procedures**
6. **Regular review and optimization**
7. **Automate routine maintenance tasks**
8. **Implement proper backup and recovery**
9. **Monitor security events**
10. **Plan for capacity and scaling**

### Maintenance Best Practices

1. **Schedule regular maintenance windows**
2. **Test maintenance procedures**
3. **Have rollback procedures ready**
4. **Document all changes**
5. **Monitor system during maintenance**
6. **Communicate maintenance schedules**
7. **Verify system health after maintenance**
8. **Review and update procedures regularly**
9. **Maintain comprehensive backups**
10. **Conduct post-maintenance reviews**