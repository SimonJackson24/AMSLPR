# VisionGate VPS Deployment

This repository contains all necessary files to deploy VisionGate (formerly VisiGate) to a VPS using Docker with CloudPanel integration.

## Quick Start

### 1. Push to Git Repository

First, push the deployment files to your git repository:

```bash
# Make the git push script executable (on Windows, use Git Bash or WSL)
chmod +x git-push.sh

# Run the git push script
./git-push.sh
```

### 2. Deploy to VPS

Once files are pushed to your repository:

```bash
# SSH into your VPS
ssh visiongate@your-vps-ip

# Navigate to application directory
cd /home/visiongate/visiongate-app

# Pull latest changes
git pull

# Make scripts executable
chmod +x deploy.sh backup.sh

# Run deployment
./deploy.sh
```

### 3. Configure CloudPanel

1. Log into CloudPanel dashboard
2. Navigate to **Websites** → **www.visiongate.co.uk** → **Reverse Proxy**
3. Add reverse proxy rule:
   - **Type**: HTTP
   - **Destination**: `http://127.0.0.1:5001`
   - **Path**: `/`
   - **Preserve Host**: Yes
   - **WebSockets**: Yes

4. Enable SSL certificate in **Websites** → **www.visiongate.co.uk** → **SSL**

## Files Overview

### Docker Configuration
- **docker-compose.vps.yml**: VPS-optimized Docker configuration
  - Disabled Hailo TPU (not available on VPS)
  - Production environment settings
  - Proper volume mounting

### Application Configuration
- **config/config.json**: Production configuration
  - Database path adjusted for VPS
  - SSL enabled for CloudPanel
  - Security settings optimized

### Deployment Scripts
- **deploy.sh**: Automated deployment script
  - Creates directories and sets permissions
  - Builds and starts Docker container
  - Verifies deployment success

- **backup.sh**: Maintenance backup script
  - Automated backups with retention
  - Excludes temporary files
  - Backup verification

- **git-push.sh**: Git automation script
  - Adds all deployment files
  - Commits with descriptive message
  - Pushes to remote repository

### Documentation
- **VPS_DEPLOYMENT_GUIDE.md**: Comprehensive deployment guide
  - Step-by-step instructions
  - CloudPanel configuration
  - Troubleshooting section
  - Maintenance commands

## Accessing the Application

After deployment, the application will be available at:
- **URL**: `https://www.visiongate.co.uk`
- **Default Username**: `admin`
- **Default Password**: Check `config/users.json` or set during first login

## Features

VisionGate provides:
- License plate recognition with OCR
- Camera management with ONVIF support
- Parking management and duration tracking
- Barrier control integration
- Web-based administration interface
- Real-time monitoring and analytics
- SSL/TLS security
- Automated backups

## Maintenance

### Regular Updates
```bash
# Update application
git pull
docker-compose -f docker-compose.vps.yml up -d --build
```

### Backups
```bash
# Create backup
./backup.sh

# View backups
ls -la ~/backups/
```

### Logs
```bash
# View application logs
docker-compose -f docker-compose.vps.yml logs -f

# Check container status
docker-compose -f docker-compose.vps.yml ps
```

## Security Considerations

1. **Firewall**: Ensure only ports 80 and 443 are open externally
2. **SSL**: Use CloudPanel's Let's Encrypt integration
3. **Updates**: Keep application and dependencies updated
4. **Backups**: Regular automated backups are essential

## Support

For issues:
1. Check application logs first
2. Verify CloudPanel reverse proxy settings
3. Ensure SSL certificate is valid
4. Check Docker and system resources

The application is production-ready and designed for reliable operation on VPS environments.