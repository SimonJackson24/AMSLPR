# VisiGate Production Deployment Guide

This guide provides detailed information on deploying the VisiGate system in a production environment.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [SSL/TLS Configuration](#ssltls-configuration)
4. [Nginx Configuration](#nginx-configuration)
5. [System Service](#system-service)
6. [Security Features](#security-features)
7. [System Monitoring](#system-monitoring)
8. [Backup and Restore](#backup-and-restore)
9. [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware Requirements

- Raspberry Pi 4 (4GB RAM recommended)
- 32GB or larger microSD card (Class 10 or better)
- Power supply (5V/3A recommended)
- Network connectivity (wired Ethernet recommended for production)
- Camera (Raspberry Pi Camera Module, USB camera, or ONVIF IP camera)
- Optional: GPIO-connected barrier control hardware

### Software Requirements

- Raspberry Pi OS (Buster or newer, 64-bit recommended)
- Python 3.7 or newer
- Nginx web server
- OpenSSL for SSL/TLS certificate generation
- SQLite for database storage

## Installation

The easiest way to install VisiGate in a production environment is to use the provided installation script:

```bash
sudo ./install.sh
```

The installation script performs the following actions:

1. Installs all required system dependencies
2. Creates the necessary directory structure:
   - `/opt/visigate`: Application files
   - `/etc/visigate`: Configuration files
   - `/var/log/visigate`: Log files
   - `/var/lib/visigate`: Data files
3. Sets up a Python virtual environment
4. Generates SSL/TLS certificates
5. Configures Nginx as a reverse proxy
6. Creates and enables a systemd service
7. Creates an initial database and admin user

### Manual Installation

If you prefer to install the system manually, follow these steps:

1. Install system dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv libopencv-dev python3-opencv \
                        libatlas-base-dev libjasper-dev libqtgui4 libqt4-test \
                        libhdf5-dev libhdf5-serial-dev libopenjp2-7 libtiff5 \
                        nginx openssl supervisor
```

2. Create directory structure:

```bash
sudo mkdir -p /opt/visigate
sudo mkdir -p /etc/visigate/ssl
sudo mkdir -p /var/log/visigate/errors
sudo mkdir -p /var/lib/visigate/images
sudo mkdir -p /var/lib/visigate/metrics
sudo mkdir -p /var/lib/visigate/reports
```

3. Set up Python virtual environment:

```bash
sudo python3 -m venv /opt/visigate/venv
sudo /opt/visigate/venv/bin/pip install --upgrade pip
sudo /opt/visigate/venv/bin/pip install -r requirements.txt
```

4. Copy application files:

```bash
sudo cp -r src /opt/visigate/
sudo cp -r docs /opt/visigate/
sudo cp -r tests /opt/visigate/
sudo cp run_tests.py /opt/visigate/
```

5. Create configuration file:

```bash
sudo cp config/config.json.example /etc/visigate/config.json
```

6. Generate SSL certificate:

```bash
sudo openssl req -x509 -newkey rsa:2048 -keyout /etc/visigate/ssl/key.pem \
                 -out /etc/visigate/ssl/cert.pem -days 365 -nodes -subj "/CN=visigate.local"
```

7. Create systemd service:

```bash
sudo cp config/visigate.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable visigate.service
```

8. Configure Nginx:

```bash
sudo cp config/nginx.conf /etc/nginx/sites-available/visigate
sudo ln -sf /etc/nginx/sites-available/visigate /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl enable nginx
sudo systemctl restart nginx
```

9. Start the service:

```bash
sudo systemctl start visigate.service
```

## SSL/TLS Configuration

The VisiGate system supports SSL/TLS encryption for secure communication. By default, the installation script generates a self-signed certificate for immediate use.

### Using Self-Signed Certificates

Self-signed certificates are suitable for testing and internal deployments but will generate browser warnings. The default certificate is valid for 365 days.

### Using Let's Encrypt Certificates

For public-facing deployments, it's recommended to use Let's Encrypt for free, trusted certificates:

1. Install certbot:

```bash
sudo apt-get install certbot python3-certbot-nginx
```

2. Obtain a certificate:

```bash
sudo certbot --nginx -d your-domain.com
```

3. Update the VisiGate configuration to use the new certificates:

```bash
sudo nano /etc/visigate/config.json
```

Update the SSL section:

```json
"ssl": {
    "enabled": true,
    "cert_file": "/etc/letsencrypt/live/your-domain.com/fullchain.pem",
    "key_file": "/etc/letsencrypt/live/your-domain.com/privkey.pem",
    "auto_generate": false
}
```

4. Restart the service:

```bash
sudo systemctl restart visigate.service
```

## Nginx Configuration

Nginx is used as a reverse proxy to provide additional security and performance benefits:

1. SSL/TLS termination
2. HTTP to HTTPS redirection
3. Static file serving
4. Load balancing (for multi-instance deployments)
5. Additional security headers

The default Nginx configuration is installed at `/etc/nginx/sites-available/visigate` and includes:

- HTTP to HTTPS redirection
- SSL/TLS configuration with secure ciphers
- Proxy settings for the VisiGate application

## System Service

The VisiGate system runs as a systemd service for automatic startup and management:

- Service name: `visigate.service`
- Service file: `/etc/systemd/system/visigate.service`

### Service Management

```bash
# Start the service
sudo systemctl start visigate.service

# Stop the service
sudo systemctl stop visigate.service

# Restart the service
sudo systemctl restart visigate.service

# Check service status
sudo systemctl status visigate.service

# View service logs
sudo journalctl -u visigate.service
```

## Security Features

The VisiGate system includes several security features for production deployments:

### Rate Limiting

API rate limiting is implemented to prevent abuse and DoS attacks. The default configuration allows 100 requests per minute per IP address. This can be adjusted in the configuration file:

```json
"security": {
    "rate_limiting": {
        "enabled": true,
        "max_requests": 100,
        "window_seconds": 60
    }
}
```

### Security Headers

The following security headers are automatically added to all responses:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';`

### Failed Login Protection

The system includes protection against brute force login attempts:

- Delay after failed login attempts
- Account lockout after multiple failed attempts
- Configurable lockout time

```json
"security": {
    "failed_login_delay": 3,
    "max_failed_logins": 5,
    "lockout_time": 300
}
```

## System Monitoring

The VisiGate system includes comprehensive monitoring features:

### Resource Monitoring

The system monitors and reports on:

- CPU usage
- Memory usage
- Disk usage
- CPU temperature (Raspberry Pi specific)
- Network usage

This information is available on the System Status page in the web interface.

### Error Handling

Comprehensive error handling includes:

- Detailed error logging
- Error categorization
- Error notifications via email or SMS
- Automatic recovery from common errors

Error logs are stored in `/var/log/visigate/errors/` and can be viewed in the web interface.

### Camera Health Monitoring

The system continuously monitors camera health and attempts to recover from issues:

- Detects camera disconnections
- Monitors frame rate and quality
- Automatically attempts to reconnect to failed cameras
- Sends notifications for persistent camera issues

## Backup and Restore

### Automated Backups

The system can be configured to perform automated backups:

1. Edit the crontab:

```bash
sudo crontab -e
```

2. Add a daily backup job (runs at 2 AM):

```
0 2 * * * /opt/visigate/venv/bin/python /opt/visigate/src/utils/backup.py > /dev/null 2>&1
```

### Manual Backup

To perform a manual backup:

```bash
sudo /opt/visigate/venv/bin/python /opt/visigate/src/utils/backup.py
```

Backups are stored in `/var/backups/visigate/` by default.

### Restore from Backup

To restore from a backup:

```bash
sudo /opt/visigate/venv/bin/python /opt/visigate/src/utils/restore.py /path/to/backup/file.tar.gz
```

## Troubleshooting

### Common Issues

#### Service Won't Start

1. Check the service status:

```bash
sudo systemctl status visigate.service
```

2. Check the logs:

```bash
sudo journalctl -u visigate.service
```

3. Verify the configuration file:

```bash
sudo /opt/visigate/venv/bin/python -c "import json; print(json.load(open('/etc/visigate/config.json')))"
```

#### Nginx Configuration Issues

1. Test the Nginx configuration:

```bash
sudo nginx -t
```

2. Check Nginx logs:

```bash
sudo tail -f /var/log/nginx/error.log
```

#### SSL Certificate Issues

1. Verify certificate and key:

```bash
sudo openssl verify /etc/visigate/ssl/cert.pem
sudo openssl rsa -check -in /etc/visigate/ssl/key.pem
```

2. Check certificate expiration:

```bash
sudo openssl x509 -in /etc/visigate/ssl/cert.pem -noout -enddate
```

#### Camera Issues

1. Check camera connections
2. Verify camera permissions
3. Test camera directly with OpenCV

```bash
sudo /opt/visigate/venv/bin/python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"
```

### Getting Help

If you encounter issues not covered in this guide, please:

1. Check the full documentation in the `docs/` directory
2. Submit an issue on the project's GitHub repository
3. Contact the development team for support
