# Common Issues and Solutions

This guide covers the most common issues encountered with AMSLPR and provides step-by-step solutions.

## System Startup Issues

### Application Won't Start

**Symptoms:**
- Application fails to start
- Error messages in console/logs
- Port binding failures

**Solutions:**

1. **Check Python Dependencies:**
   ```bash
   pip list | grep -E "(flask|opencv|numpy|pillow)"
   pip install -r requirements.txt
   ```

2. **Verify Configuration Files:**
   ```bash
   python -c "import json; json.load(open('config/config.json'))"
   python -c "import json; json.load(open('config/ocr_config.json'))"
   ```

3. **Check Port Availability:**
   ```bash
   netstat -tlnp | grep :5001
   lsof -i :5001
   ```

4. **Verify File Permissions:**
   ```bash
   ls -la data/ logs/ config/
   chmod -R 755 data/ logs/ config/
   ```

### Database Connection Issues

**Symptoms:**
- "Database not found" errors
- SQLite database locked
- Permission denied on database file

**Solutions:**

1. **Check Database File:**
   ```bash
   ls -la data/amslpr.db
   file data/amslpr.db
   ```

2. **Repair Database:**
   ```bash
   sqlite3 data/amslpr.db ".schema" > schema.sql
   sqlite3 data/amslpr.db ".dump" > backup.sql
   rm data/amslpr.db
   sqlite3 data/amslpr.db < schema.sql
   ```

3. **Check Database Permissions:**
   ```bash
   chmod 666 data/amslpr.db
   chown www-data:www-data data/amslpr.db
   ```

## Camera Connection Issues

### Camera Not Detected

**Symptoms:**
- Camera shows as offline
- No video stream
- Connection timeout errors

**Solutions:**

1. **Test Network Connectivity:**
   ```bash
   ping <camera-ip>
   telnet <camera-ip> <camera-port>
   ```

2. **Verify Camera Credentials:**
   ```bash
   curl -u admin:password http://<camera-ip>/ISAPI/System/status
   ```

3. **Check RTSP Stream:**
   ```bash
   ffprobe rtsp://<username>:<password>@<camera-ip>:<port>/stream1
   ```

4. **Firewall Configuration:**
   ```bash
   ufw allow <camera-port>
   iptables -A INPUT -p tcp --dport <camera-port> -j ACCEPT
   ```

### Poor Video Quality

**Symptoms:**
- Blurry license plates
- Low frame rate
- Video artifacts

**Solutions:**

1. **Adjust Camera Settings:**
   - Increase resolution to 1920x1080
   - Set frame rate to 30 FPS
   - Enable H.264 encoding
   - Adjust exposure and white balance

2. **Optimize Network:**
   ```bash
   # Check network bandwidth
   iperf -c <camera-ip> -t 10

   # Adjust MTU
   ifconfig eth0 mtu 9000
   ```

3. **Camera Positioning:**
   - Ensure camera is level
   - Adjust angle for optimal plate visibility
   - Minimize backlighting
   - Clean camera lens

## OCR Recognition Issues

### Low Recognition Accuracy

**Symptoms:**
- Incorrect license plate readings
- False positives/negatives
- Low confidence scores

**Solutions:**

1. **Adjust OCR Configuration:**
   ```json
   {
     "confidence_threshold": 0.8,
     "ocr_method": "hybrid",
     "preprocessing": {
       "apply_contrast_enhancement": true,
       "apply_noise_reduction": true
     }
   }
   ```

2. **Optimize Image Quality:**
   - Improve lighting conditions
   - Reduce motion blur
   - Clean camera lens
   - Adjust camera focus

3. **Fine-tune Detection Area:**
   ```json
   {
     "detection_area": {
       "x": 100,
       "y": 200,
       "width": 800,
       "height": 300
     }
   }
   ```

### Hailo TPU Not Working

**Symptoms:**
- OCR falls back to CPU
- "Hailo device not found" messages
- Performance degradation

**Solutions:**

1. **Check Hailo Device:**
   ```bash
   ls -la /dev/hailo*
   dmesg | grep hailo
   ```

2. **Verify Hailo SDK:**
   ```bash
   python -c "import hailo_platform; print(hailo_platform.__version__)"
   ```

3. **Install/Update Drivers:**
   ```bash
   # For PCIe devices
   sudo modprobe hailo_pci

   # For USB devices
   sudo modprobe hailo_usb
   ```

4. **Check Permissions:**
   ```bash
   sudo chmod 666 /dev/hailo0
   sudo usermod -a -G hailo $USER
   ```

## Performance Issues

### High CPU Usage

**Symptoms:**
- System slowdown
- High CPU utilization
- Delayed processing

**Solutions:**

1. **Optimize OCR Settings:**
   ```json
   {
     "ocr_method": "tesseract",
     "preprocessing": {
       "apply_noise_reduction": false,
       "apply_perspective_correction": false
     }
   }
   ```

2. **Enable Caching:**
   ```json
   {
     "cache": {
       "enabled": true,
       "redis_url": "redis://localhost:6379",
       "ttl": 3600
     }
   }
   ```

3. **Adjust Processing Threads:**
   ```bash
   export OMP_NUM_THREADS=2
   export MKL_NUM_THREADS=2
   ```

### Memory Issues

**Symptoms:**
- Out of memory errors
- System crashes
- Slow performance

**Solutions:**

1. **Monitor Memory Usage:**
   ```bash
   htop
   free -h
   ps aux --sort=-%mem | head
   ```

2. **Optimize Image Processing:**
   ```json
   {
     "recognition": {
       "save_images": false,
       "image_save_path": "/tmp"
     }
   }
   ```

3. **Configure Garbage Collection:**
   ```python
   import gc
   gc.set_threshold(700, 10, 10)
   ```

### Slow Response Times

**Symptoms:**
- Delayed API responses
- Web interface lag
- Timeout errors

**Solutions:**

1. **Database Optimization:**
   ```sql
   CREATE INDEX idx_plate_number ON vehicles(plate_number);
   CREATE INDEX idx_access_time ON access_logs(access_time);
   VACUUM;
   ```

2. **Enable Compression:**
   ```python
   from flask import Flask
   app.config['COMPRESS_LEVEL'] = 6
   app.config['COMPRESS_MIN_SIZE'] = 500
   ```

3. **Implement Caching:**
   ```python
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'redis'})
   ```

## Network Issues

### Connection Timeouts

**Symptoms:**
- API request timeouts
- Camera connection failures
- Database connection drops

**Solutions:**

1. **Adjust Timeout Settings:**
   ```json
   {
     "web": {
       "timeout": 30
     },
     "camera": {
       "connection_timeout": 10,
       "read_timeout": 30
     }
   }
   ```

2. **Network Troubleshooting:**
   ```bash
   traceroute <target-ip>
   mtr <target-ip>
   nmap -p <port> <target-ip>
   ```

3. **Firewall Configuration:**
   ```bash
   # Allow necessary ports
   ufw allow 5001/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ```

### SSL/TLS Issues

**Symptoms:**
- Certificate validation errors
- HTTPS connection failures
- Mixed content warnings

**Solutions:**

1. **Certificate Validation:**
   ```bash
   openssl s_client -connect localhost:443 -servername localhost
   openssl verify -CAfile /path/to/ca.crt /path/to/cert.pem
   ```

2. **SSL Configuration:**
   ```json
   {
     "web": {
       "ssl": {
         "enabled": true,
         "certificate": "/path/to/cert.pem",
         "key": "/path/to/key.pem",
         "ca_certificates": "/path/to/ca.crt"
       }
     }
   }
   ```

## Storage Issues

### Disk Space Problems

**Symptoms:**
- "No space left on device" errors
- Image saving failures
- Database corruption

**Solutions:**

1. **Monitor Disk Usage:**
   ```bash
   df -h
   du -sh /app/data/
   du -sh /app/logs/
   ```

2. **Configure Log Rotation:**
   ```bash
   # /etc/logrotate.d/amslpr
   /app/logs/*.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }
   ```

3. **Clean Up Old Data:**
   ```bash
   find /app/data/images -type f -mtime +30 -delete
   find /app/logs -name "*.log.*" -mtime +7 -delete
   ```

### Permission Issues

**Symptoms:**
- File write errors
- Database access denied
- Configuration load failures

**Solutions:**

1. **Check File Permissions:**
   ```bash
   ls -la /app/
   namei -l /app/data/amslpr.db
   ```

2. **Fix Permissions:**
   ```bash
   chown -R www-data:www-data /app/
   chmod -R 755 /app/
   chmod 666 /app/data/*.db
   ```

3. **SELinux/AppArmor:**
   ```bash
   # Check SELinux status
   sestatus

   # Temporarily disable for testing
   setenforce 0

   # Configure SELinux policy
   semanage fcontext -a -t httpd_sys_rw_content_t "/app/data(/.*)?"
   restorecon -Rv /app/data/
   ```

## Notification Issues

### Email Delivery Problems

**Symptoms:**
- Emails not being sent
- SMTP connection errors
- Authentication failures

**Solutions:**

1. **Test SMTP Connection:**
   ```bash
   telnet smtp.gmail.com 587
   openssl s_client -connect smtp.gmail.com:465 -crlf
   ```

2. **Verify Email Configuration:**
   ```json
   {
     "notifications": {
       "email": {
         "smtp_server": "smtp.gmail.com",
         "smtp_port": 587,
         "use_tls": true,
         "username": "your-email@gmail.com",
         "password": "your-app-password"
       }
     }
   }
   ```

3. **Check Email Logs:**
   ```bash
   tail -f /var/log/mail.log
   journalctl -u postfix
   ```

### SMS Delivery Issues

**Symptoms:**
- SMS messages not sent
- Twilio API errors
- Invalid phone number format

**Solutions:**

1. **Verify Twilio Configuration:**
   ```json
   {
     "notifications": {
       "sms": {
         "account_sid": "ACxxxxxxxxxxxxxxxx",
         "auth_token": "your_auth_token",
         "from_number": "+1234567890"
       }
     }
   }
   ```

2. **Test SMS API:**
   ```bash
   curl -X POST https://api.twilio.com/2010-04-01/Accounts/ACxxx/Messages.json \
     --data-urlencode "From=+1234567890" \
     --data-urlencode "To=+1987654321" \
     --data-urlencode "Body=Test message" \
     -u ACxxx:your_auth_token
   ```

## Barrier Control Issues

### Barrier Not Responding

**Symptoms:**
- Barrier doesn't open/close
- GPIO pin errors
- Hardware communication failures

**Solutions:**

1. **Check GPIO Configuration:**
   ```bash
   gpio readall
   gpio mode 18 out
   gpio write 18 1
   ```

2. **Verify Hardware Connections:**
   - Check wiring connections
   - Test power supply voltage
   - Verify relay functionality

3. **Test Barrier Control:**
   ```python
   import RPi.GPIO as GPIO
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(18, GPIO.OUT)
   GPIO.output(18, GPIO.HIGH)
   ```

### Integration Issues

**Symptoms:**
- Paxton/Nayax integration failures
- API communication errors
- Synchronization problems

**Solutions:**

1. **Test Integration APIs:**
   ```bash
   curl -X GET "https://paxton-api.example.com/status" \
     -H "Authorization: Bearer your-token"
   ```

2. **Verify Integration Configuration:**
   ```json
   {
     "integration": {
       "paxton": {
         "enabled": true,
         "api_url": "https://paxton-api.example.com",
         "api_key": "your-api-key"
       }
     }
   }
   ```

## Log Analysis

### Reading Application Logs

```bash
# View recent logs
tail -f logs/amslpr.log

# Search for specific errors
grep "ERROR" logs/amslpr.log

# Filter by date
sed -n '/2023-10-01/,/2023-10-02/p' logs/amslpr.log

# Count error types
grep "ERROR" logs/amslpr.log | cut -d' ' -f4 | sort | uniq -c | sort -nr
```

### Common Log Patterns

1. **Database Errors:**
   ```
   ERROR - Database connection failed: (sqlite3.OperationalError) database is locked
   ```

2. **Camera Errors:**
   ```
   ERROR - Camera connection timeout: 192.168.1.100:80
   ```

3. **OCR Errors:**
   ```
   ERROR - OCR confidence too low: 0.45 < 0.7
   ```

4. **Network Errors:**
   ```
   ERROR - HTTP request failed: Connection refused
   ```

## Diagnostic Tools

### System Diagnostics

```bash
# System information
uname -a
lsb_release -a
python --version

# Hardware information
lscpu
free -h
df -h

# Network information
ip addr show
netstat -tlnp
ss -tlnp
```

### AMSLPR Diagnostics

```bash
# Test database connection
python -c "from src.database.db_manager import DatabaseManager; db = DatabaseManager(); print('DB OK')"

# Test camera connection
python -c "import cv2; cap = cv2.VideoCapture('rtsp://...'); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"

# Test OCR functionality
python -c "from src.recognition.detector import LicensePlateDetector; detector = LicensePlateDetector(); print('OCR OK')"
```

### Performance Monitoring

```bash
# CPU usage
top -p $(pgrep -f amslpr)

# Memory usage
ps aux --sort=-%mem | grep amslpr

# Network connections
netstat -anp | grep :5001

# Disk I/O
iotop -p $(pgrep -f amslpr)
```

## Emergency Procedures

### System Recovery

1. **Stop the Application:**
   ```bash
   systemctl stop amslpr
   docker-compose down
   ```

2. **Backup Current State:**
   ```bash
   cp -r data/ data.backup/
   cp -r config/ config.backup/
   ```

3. **Reset Configuration:**
   ```bash
   cp config.json.example config.json
   cp ocr_config.json.example ocr_config.json
   ```

4. **Restart Services:**
   ```bash
   systemctl start amslpr
   docker-compose up -d
   ```

### Data Recovery

1. **Database Recovery:**
   ```bash
   sqlite3 data/amslpr.db ".recover" > recovered.sql
   sqlite3 data/amslpr_new.db < recovered.sql
   mv data/amslpr_new.db data/amslpr.db
   ```

2. **Configuration Recovery:**
   ```bash
   git checkout HEAD~1 config/
   ```

## Support Information

### Gathering Diagnostic Information

```bash
# Create diagnostic bundle
mkdir diagnostics
cp logs/amslpr.log diagnostics/
cp config/*.json diagnostics/
ps aux | grep amslpr > diagnostics/processes.txt
netstat -tlnp > diagnostics/network.txt
df -h > diagnostics/disk.txt
free -h > diagnostics/memory.txt

# Archive diagnostics
tar czf diagnostics.tar.gz diagnostics/
```

### Contacting Support

When contacting support, please provide:

1. **System Information:**
   - OS version and architecture
   - Python version
   - AMSLPR version
   - Hardware specifications

2. **Configuration Files:**
   - `config/config.json`
   - `config/ocr_config.json`
   - `config/camera_config.json`

3. **Log Files:**
   - Recent application logs
   - System logs (`/var/log/syslog`)

4. **Error Messages:**
   - Exact error messages
   - Steps to reproduce the issue
   - Expected vs. actual behavior

5. **Diagnostic Information:**
   - Output of diagnostic commands
   - Network connectivity tests
   - Hardware status information

## Prevention Best Practices

1. **Regular Backups:**
   - Daily database backups
   - Weekly configuration backups
   - Monthly full system backups

2. **Monitoring:**
   - Set up system monitoring alerts
   - Monitor disk space usage
   - Track performance metrics

3. **Maintenance:**
   - Regular software updates
   - Clean up old log files
   - Optimize database performance

4. **Security:**
   - Regular security audits
   - Update passwords regularly
   - Monitor access logs

5. **Documentation:**
   - Keep configuration changes documented
   - Maintain change logs
   - Document custom modifications