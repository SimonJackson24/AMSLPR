# AMSLPR Security Hardening Guide

This guide provides recommendations for securing your AMSLPR deployment in a production environment. Following these best practices will help protect your system from common security threats.

## System-Level Security

### Operating System Hardening

1. **Keep the system updated**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install security updates automatically**
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

3. **Enable a firewall**
   ```bash
   sudo apt install ufw
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **Disable unnecessary services**
   ```bash
   # List all running services
   sudo systemctl list-units --type=service --state=running
   
   # Disable unnecessary services
   sudo systemctl disable <service-name>
   sudo systemctl stop <service-name>
   ```

5. **Secure SSH access**
   ```bash
   sudo nano /etc/ssh/sshd_config
   ```
   
   Make the following changes:
   ```
   PermitRootLogin no
   PasswordAuthentication no
   X11Forwarding no
   MaxAuthTries 3
   ```
   
   Restart SSH:
   ```bash
   sudo systemctl restart sshd
   ```

6. **Set up fail2ban to protect against brute force attacks**
   ```bash
   sudo apt install fail2ban
   sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
   sudo nano /etc/fail2ban/jail.local
   ```
   
   Configure the SSH jail:
   ```
   [sshd]
   enabled = true
   port = ssh
   filter = sshd
   logpath = /var/log/auth.log
   maxretry = 3
   bantime = 3600
   ```
   
   Start fail2ban:
   ```bash
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

### File System Security

1. **Set proper permissions for AMSLPR files**
   ```bash
   # Set ownership
   sudo chown -R root:root /opt/amslpr
   sudo chown -R root:root /etc/amslpr
   
   # Set permissions
   sudo chmod -R 755 /opt/amslpr
   sudo chmod -R 640 /etc/amslpr/config.json
   sudo chmod -R 750 /etc/amslpr/ssl
   sudo chmod 600 /etc/amslpr/ssl/key.pem
   ```

2. **Secure log files**
   ```bash
   sudo chmod -R 640 /var/log/amslpr
   ```

3. **Enable disk encryption** (for new installations)
   - Use LUKS encryption during Raspberry Pi OS installation
   - Alternatively, encrypt sensitive partitions

## Application Security

### Web Interface Security

1. **Use strong passwords**
   - Enforce password complexity requirements
   - Use a password manager to generate and store strong passwords

2. **Implement HTTPS**
   - Use Let's Encrypt for trusted certificates
   - Configure proper SSL/TLS settings
   - Test your SSL configuration with [SSL Labs](https://www.ssllabs.com/ssltest/)

3. **Configure security headers**
   The AMSLPR application automatically sets the following security headers:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: SAMEORIGIN
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security: max-age=31536000; includeSubDomains
   - Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';

4. **Enable rate limiting**
   Rate limiting is enabled by default in the AMSLPR configuration. Adjust the settings in `config.json`:
   ```json
   "security": {
       "rate_limiting": {
           "enabled": true,
           "max_requests": 100,
           "window_seconds": 60
       }
   }
   ```

### Database Security

1. **Secure the SQLite database**
   ```bash
   # Set proper permissions
   sudo chmod 640 /var/lib/amslpr/amslpr.db
   sudo chown root:root /var/lib/amslpr/amslpr.db
   ```

2. **Enable database encryption**
   SQLite doesn't support native encryption, but you can use SQLCipher for encrypted databases:
   ```bash
   sudo apt install sqlcipher
   ```
   
   Then modify the database connection in the application to use SQLCipher.

3. **Regular backups**
   ```bash
   # Set up a daily backup
   sudo crontab -e
   ```
   
   Add:
   ```
   0 2 * * * /opt/amslpr/venv/bin/python /opt/amslpr/src/utils/backup.py > /dev/null 2>&1
   ```

### Camera Security

1. **Secure ONVIF camera access**
   - Change default passwords on all cameras
   - Use unique, strong passwords for each camera
   - Disable unused services on cameras
   - Update camera firmware regularly

2. **Network isolation**
   - Place cameras on a separate network segment
   - Use VLANs to isolate camera traffic
   - Implement firewall rules to restrict camera access

3. **Encrypt camera credentials**
   AMSLPR encrypts camera credentials using Fernet symmetric encryption. Ensure the encryption key is properly secured.

## Network Security

1. **Use a separate network for the AMSLPR system**
   - Create a dedicated VLAN for the AMSLPR system
   - Implement proper network segmentation

2. **Implement a reverse proxy**
   Nginx is configured as a reverse proxy by default. Ensure it's properly configured:
   ```bash
   sudo nano /etc/nginx/sites-available/amslpr
   ```
   
   Check for these security settings:
   ```
   # SSL configuration
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_prefer_server_ciphers on;
   ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
   ssl_session_timeout 1d;
   ssl_session_cache shared:SSL:10m;
   ssl_session_tickets off;
   
   # HSTS
   add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
   
   # OCSP Stapling
   ssl_stapling on;
   ssl_stapling_verify on;
   ```

3. **Regular security scanning**
   - Use tools like Nmap to scan for open ports
   - Use OpenVAS or similar tools for vulnerability scanning
   - Regularly review system logs for suspicious activity

## Monitoring and Incident Response

1. **Set up monitoring**
   - Configure email alerts for system issues
   - Monitor system resources (CPU, memory, disk)
   - Set up alerts for failed login attempts

2. **Log management**
   - Centralize logs for easier analysis
   - Implement log rotation to manage disk space
   - Consider using a log analysis tool

3. **Create an incident response plan**
   - Document steps to take in case of a security breach
   - Identify key contacts and responsibilities
   - Regularly test the incident response plan

## Regular Security Maintenance

1. **Security updates**
   - Regularly update the AMSLPR software
   - Keep the operating system and dependencies updated
   - Subscribe to security mailing lists for relevant components

2. **Regular security audits**
   - Conduct periodic security reviews
   - Test system security with penetration testing
   - Review and update security policies

3. **Backup and recovery testing**
   - Regularly test backup and recovery procedures
   - Ensure backups are stored securely
   - Document the recovery process

## Conclusion

Security is an ongoing process, not a one-time setup. Regularly review and update your security measures to protect against new threats. By following these recommendations, you can significantly improve the security of your AMSLPR deployment.

For additional security resources, consult the following:
- [Raspberry Pi Security Guide](https://www.raspberrypi.org/documentation/configuration/security.md)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
