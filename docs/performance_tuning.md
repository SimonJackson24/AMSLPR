# VisiGate Performance Tuning Guide

This guide provides recommendations for optimizing the performance of your VisiGate system in a production environment. These optimizations can help improve recognition speed, reduce resource usage, and enhance overall system responsiveness.

## Hardware Optimization

### Raspberry Pi Optimization

1. **Use adequate cooling**
   - Install a heatsink and fan to prevent thermal throttling
   - Monitor CPU temperature using the system monitoring page
   - Consider a case with good airflow

2. **Use a high-quality microSD card**
   - Class 10 or UHS-I/II cards recommended
   - Consider using an SSD via USB 3.0 for improved performance
   - Regularly check for SD card errors

3. **Power supply**
   - Use an official Raspberry Pi power supply (5V/3A)
   - Ensure stable power to prevent undervoltage issues
   - Consider a UPS for uninterrupted operation

4. **Memory optimization**
   - Allocate appropriate GPU memory (64-128MB is usually sufficient)
   ```bash
   sudo nano /boot/config.txt
   ```
   Add or modify:
   ```
   gpu_mem=128
   ```

5. **Overclocking (optional)**
   - Moderate overclocking can improve performance
   - Requires adequate cooling
   ```bash
   sudo nano /boot/config.txt
   ```
   Add or modify:
   ```
   over_voltage=2
   arm_freq=1750
   ```
   Note: Overclocking may void warranty and can cause system instability

### Camera Optimization

1. **Camera positioning**
   - Position the camera to capture license plates at an optimal angle
   - Ensure adequate lighting for night operation
   - Minimize exposure to direct sunlight to prevent glare

2. **Camera settings**
   - Adjust focus for the specific installation distance
   - Set appropriate resolution (higher isn't always better)
   - Configure frame rate based on traffic speed

3. **For ONVIF cameras**
   - Use wired network connections when possible
   - Configure cameras to use H.264 encoding for efficiency
   - Set appropriate bitrate and quality settings

## Software Optimization

### Recognition Pipeline Optimization

1. **Frame processing settings**
   ```bash
   sudo nano /etc/visigate/config.json
   ```
   Adjust these settings:
   ```json
   "recognition": {
       "frame_width": 640,
       "frame_height": 480,
       "processing_interval": 0.5,
       "confidence_threshold": 0.7
   }
   ```

   - Reduce resolution for faster processing
   - Increase processing interval for lower CPU usage
   - Adjust confidence threshold based on recognition accuracy

2. **Region of interest (ROI)**
   - Configure detection areas to focus only on relevant parts of the frame
   - This reduces processing time and improves accuracy
   - Use the web interface to set ROI for each camera

3. **Pre-processing optimization**
   - Enable image pre-processing for challenging conditions
   - Adjust contrast and brightness settings for better recognition
   - Use grayscale conversion to reduce processing overhead

### Web Interface Optimization

1. **Nginx caching**
   ```bash
   sudo nano /etc/nginx/sites-available/visigate
   ```
   Add caching configuration:
   ```
   # Cache static assets
   location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
       expires 7d;
       add_header Cache-Control "public, no-transform";
   }
   ```

2. **Compress responses**
   ```bash
   sudo nano /etc/nginx/sites-available/visigate
   ```
   Add compression settings:
   ```
   # Enable gzip compression
   gzip on;
   gzip_comp_level 5;
   gzip_min_length 256;
   gzip_proxied any;
   gzip_vary on;
   gzip_types
     application/javascript
     application/json
     application/x-javascript
     text/css
     text/javascript
     text/plain
     text/xml;
   ```

3. **Optimize image storage**
   - Configure image retention policy to prevent disk space issues
   - Set up automatic cleanup of old images
   - Use thumbnail generation for the web interface

### Database Optimization

1. **Regular maintenance**
   ```bash
   # Create a maintenance script
   sudo nano /opt/visigate/scripts/db_maintenance.sh
   ```
   
   Add these commands:
   ```bash
   #!/bin/bash
   # Path to the database
   DB_PATH="/var/lib/visigate/visigate.db"
   
   # Vacuum the database
   sqlite3 $DB_PATH "VACUUM;"
   
   # Analyze tables
   sqlite3 $DB_PATH "ANALYZE;"
   ```
   
   Make it executable and schedule it:
   ```bash
   sudo chmod +x /opt/visigate/scripts/db_maintenance.sh
   sudo crontab -e
   ```
   
   Add a weekly job:
   ```
   0 3 * * 0 /opt/visigate/scripts/db_maintenance.sh > /dev/null 2>&1
   ```

2. **Indexing**
   - Ensure proper indexes are created for frequently queried fields
   - The VisiGate database schema includes indexes for license plate numbers and timestamps

3. **Query optimization**
   - Use parameterized queries to prevent SQL injection and improve performance
   - Limit result sets for large queries
   - Use appropriate WHERE clauses to filter data early

## System-Level Optimization

### Operating System Tuning

1. **Disable unnecessary services**
   ```bash
   # List all enabled services
   systemctl list-unit-files --state=enabled
   
   # Disable unnecessary services
   sudo systemctl disable bluetooth.service
   sudo systemctl disable avahi-daemon.service
   sudo systemctl disable triggerhappy.service
   ```

2. **Optimize swap settings**
   ```bash
   sudo nano /etc/sysctl.conf
   ```
   
   Add or modify:
   ```
   # Decrease swap usage
   vm.swappiness=10
   
   # Increase cache pressure
   vm.vfs_cache_pressure=50
   ```
   
   Apply changes:
   ```bash
   sudo sysctl -p
   ```

3. **File system optimization**
   - Use noatime mount option to reduce disk writes
   ```bash
   sudo nano /etc/fstab
   ```
   
   Add noatime to the root partition:
   ```
   PARTUUID=... / ext4 defaults,noatime 0 1
   ```

### Network Optimization

1. **Use wired network when possible**
   - Ethernet provides more reliable performance than Wi-Fi
   - If Wi-Fi is necessary, use 5GHz band for less interference

2. **TCP optimization**
   ```bash
   sudo nano /etc/sysctl.conf
   ```
   
   Add or modify:
   ```
   # TCP optimizations
   net.core.somaxconn=1024
   net.core.netdev_max_backlog=5000
   net.ipv4.tcp_max_syn_backlog=8096
   net.ipv4.tcp_slow_start_after_idle=0
   net.ipv4.tcp_tw_reuse=1
   ```
   
   Apply changes:
   ```bash
   sudo sysctl -p
   ```

3. **DNS optimization**
   - Use local DNS caching
   ```bash
   sudo apt install dnsmasq
   sudo nano /etc/dnsmasq.conf
   ```
   
   Add or modify:
   ```
   cache-size=1000
   no-negcache
   ```

## Monitoring and Benchmarking

### Performance Monitoring

1. **Use the built-in system monitoring**
   - Access the System Status page in the web interface
   - Monitor CPU, memory, and disk usage
   - Check for resource bottlenecks

2. **Set up performance alerts**
   - Configure email notifications for high resource usage
   - Set appropriate thresholds in the configuration file

3. **Log analysis**
   - Regularly review logs for performance issues
   - Look for slow queries or processing delays
   - Use log rotation to manage log file size

### Benchmarking

1. **Recognition speed**
   - Measure the time from image capture to license plate recognition
   - Compare different camera settings and processing parameters
   - Optimize for your specific use case

2. **System responsiveness**
   - Measure web interface load times
   - Test barrier response time (if applicable)
   - Ensure the system remains responsive under load

3. **Database performance**
   - Measure query execution times
   - Test with different database sizes
   - Optimize queries and indexes based on results

## Advanced Optimization

### Multi-Camera Deployment

1. **Load balancing**
   - Distribute cameras across multiple Raspberry Pi devices
   - Use a central server for database and web interface
   - Configure each device to handle specific cameras

2. **Dedicated processing**
   - Use separate devices for recognition and web interface
   - Dedicate one device to database and reporting
   - Connect devices using a high-speed local network

### Custom Recognition Models

1. **Train custom models**
   - Create models optimized for your specific region's license plates
   - Use transfer learning to improve recognition accuracy
   - Balance model size and accuracy for optimal performance

2. **Model quantization**
   - Use quantized models for faster inference
   - Reduce model precision to improve performance
   - Test accuracy with quantized models before deployment

## Conclusion

Optimizing the VisiGate system is an iterative process. Start with the most impactful changes and measure their effect before moving on to more advanced optimizations. Regular monitoring and maintenance are key to maintaining optimal performance over time.

Remember that the optimal configuration depends on your specific hardware, environment, and requirements. Use the system monitoring tools to identify bottlenecks and focus your optimization efforts accordingly.
