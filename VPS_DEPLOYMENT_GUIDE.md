# VisionGate VPS Deployment Guide

## Overview
This guide will help you deploy the VisionGate application (formerly VisiGate) to your VPS using Docker on the visiongate user with CloudPanel.

## Prerequisites
- SSH access to your VPS as visiongate user
- Docker and Docker Compose installed on VPS
- CloudPanel access for www.visiongate.co.uk domain
- Application files cloned to VPS

## Step 4: Create Required Files

### 4.1 Make Scripts Executable
After uploading files to your VPS, run these commands:

```bash
# SSH into your VPS
ssh visiongate@your-vps-ip

# Navigate to application directory
cd /home/visiongate/visiongate-app

# Make scripts executable
chmod +x deploy.sh backup.sh
```

### 4.2 Files Created
I've created these files for you:
- `docker-compose.vps.yml` - VPS-optimized Docker configuration
- `config/config.json` - Production configuration
- `deploy.sh` - Automated deployment script
- `backup.sh` - Backup maintenance script

## Step 5: Deploy the Application

### Option A: Using the Automated Deployment Script (Recommended)

```bash
# Run the deployment script
./deploy.sh
```

This script will:
- Create all necessary directories
- Set correct permissions
- Build and start the Docker container
- Verify the deployment

### Option B: Manual Deployment

```bash
# Create directories manually
mkdir -p data logs config models uploads instance/flask_session

# Set permissions
chmod -R 755 data logs config models uploads instance
chmod -R 777 instance/flask_session

# Build and start container
docker-compose -f docker-compose.vps.yml up -d --build

# Check status
docker-compose -f docker-compose.vps.yml ps
```

## Step 6: Configure CloudPanel Reverse Proxy

1. Log into your CloudPanel dashboard
2. Navigate to **Websites** → **www.visiongate.co.uk** → **Reverse Proxy**
3. Add new reverse proxy rule:
   - **Type**: HTTP
   - **Destination**: `http://127.0.0.1:5001`
   - **Path**: `/`
   - **Preserve Host**: Yes
   - **WebSockets**: Yes
4. Save the configuration

## Step 7: Configure SSL Certificate

1. In CloudPanel, go to **Websites** → **www.visiongate.co.uk** → **SSL**
2. Choose one of the following:
   - **Let's Encrypt** (recommended for automatic certificates)
   - **Custom Certificate** (if you have your own)
3. Enable SSL and save settings

## Step 8: Test the Deployment

```bash
# Test local connection
curl http://localhost:5001/health

# Test external domain (after DNS propagation)
curl https://www.visiongate.co.uk/health
```

Expected response:
```json
{"status": "healthy"}
```

## Step 9: Access the Application

1. Open your browser and navigate to: `https://www.visiongate.co.uk`
2. Default login credentials:
   - Username: `admin`
   - Password: Check the `config/users.json` file or set during first login

## Maintenance Commands

### View Logs
```bash
# Follow real-time logs
docker-compose -f docker-compose.vps.yml logs -f

# Check specific service logs
docker-compose -f docker-compose.vps.yml logs visiongate
```

### Stop/Start Services
```bash
# Stop the application
docker-compose -f docker-compose.vps.yml down

# Start the application
docker-compose -f docker-compose.vps.yml up -d

# Restart the application
docker-compose -f docker-compose.vps.yml restart
```

### Update Application
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.vps.yml up -d --build
```

### Backup Data
```bash
# Run backup script
./backup.sh

# View backup files
ls -la ~/backups/
```

### Access Container Shell
```bash
# Access container for debugging
docker-compose -f docker-compose.vps.yml exec visiongate bash
```

## Security Configuration

### Firewall Settings
```bash
# Configure UFW firewall (if using Ubuntu/Debian)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5001/tcp  # Keep internal port closed
sudo ufw enable
```

### SSL Certificate Renewal
CloudPanel's Let's Encrypt certificates auto-renew, but you can check:

```bash
# Check certificate status
sudo certbot certificates
```

## Troubleshooting

### Container Won't Start
```bash
# Check container logs for errors
docker-compose -f docker-compose.vps.yml logs visiongate

# Check Docker service status
sudo systemctl status docker

# Check available disk space
df -h
```

### Database Issues
```bash
# Check database file permissions
ls -la data/visiongate.db

# Backup and recreate database
mv data/visiongate.db data/visiongate.db.backup
```

### Performance Issues
```bash
# Check container resource usage
docker stats visiongate

# Check system resources
free -h
top
```

### Network Issues
```bash
# Check if port 5001 is listening
netstat -tlnp | grep 5001

# Check reverse proxy configuration
sudo nginx -t
```

## Production Considerations

1. **Regular Updates**: Set up a cron job for weekly updates:
   ```bash
   crontab -e
   # Add: 0 2 * * 0 cd /home/visiongate/visiongate-app && git pull && docker-compose -f docker-compose.vps.yml up -d --build
   ```

2. **Automated Backups**: Set up daily backups:
   ```bash
   crontab -e
   # Add: 0 3 * * * /home/visiongate/visiongate-app/backup.sh
   ```

3. **Monitoring**: Monitor disk space and container health:
   ```bash
   # Add to crontab for every 5 minutes
   */5 * * * * docker-compose -f /home/visiongate/visiongate-app/docker-compose.vps.yml ps | grep -q "Up" || echo "Container down!" | mail -s "VisionGate Alert" admin@visiongate.co.uk
   ```

## Support

If you encounter issues:
1. Check the application logs first
2. Verify CloudPanel reverse proxy settings
3. Ensure SSL certificate is valid
4. Check Docker and system resources

The application should now be fully operational at https://www.visiongate.co.uk with all features including license plate recognition, camera management, and parking controls.