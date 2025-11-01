# VisiGate Migration Guide

## Migrating from AMSLPR to VisiGate

This guide provides step-by-step instructions for migrating existing AMSLPR installations to the new VisiGate branding.

---

## Overview

VisiGate (formerly AMSLPR) has undergone a complete rebranding. This includes:
- Product name: AMSLPR → VisiGate
- Copyright: Automate Systems → VisiGate
- Service names: `amslpr.service` → `visigate.service`
- Environment variables: `AMSLPR_*` → `VISIGATE_*`
- File paths: `/opt/amslpr` → `/opt/visigate`
- Logger names: `AMSLPR.*` → `VisiGate.*`

---

## Pre-Migration Checklist

Before starting the migration, ensure you have:

1. **Full System Backup**
   ```bash
   # Backup database
   sudo cp /var/lib/amslpr/visigate.db /var/lib/amslpr/visigate.db.backup
   
   # Backup configuration
   sudo cp -r /etc/amslpr /etc/amslpr.backup
   
   # Backup data directory
   sudo tar -czf /tmp/amslpr-data-backup.tar.gz /opt/amslpr
   ```

2. **Document Current Configuration**
   ```bash
   # Export environment variables
   env | grep AMSLPR > /tmp/amslpr-env.txt
   
   # List running services
   systemctl list-units | grep amslpr > /tmp/amslpr-services.txt
   ```

3. **Stop All Services**
   ```bash
   sudo systemctl stop amslpr
   ```

---

## Migration Steps

### Step 1: Update System Service

1. **Stop the old service:**
   ```bash
   sudo systemctl stop amslpr
   sudo systemctl disable amslpr
   ```

2. **Update service file references:**
   ```bash
   # If you have a custom service file at /etc/systemd/system/amslpr.service
   sudo sed -i 's/amslpr/visigate/g' /etc/systemd/system/amslpr.service
   sudo mv /etc/systemd/system/amslpr.service /etc/systemd/system/visigate.service
   ```

3. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

### Step 2: Update File Paths

1. **Rename installation directory (if applicable):**
   ```bash
   # If installed in /opt/amslpr
   sudo mv /opt/amslpr /opt/visigate
   
   # If installed in user home directory
   mv ~/AMSLPR ~/VisiGate
   ```

2. **Update data directories:**
   ```bash
   # Data directory
   sudo mv /var/lib/amslpr /var/lib/visigate
   
   # Log directory
   sudo mv /var/log/amslpr /var/log/visigate
   
   # Config directory
   sudo mv /etc/amslpr /etc/visigate
   ```

3. **Update symbolic links (if any):**
   ```bash
   # Update any symlinks pointing to old paths
   sudo find /usr/local/bin -type l -lname '*amslpr*' -exec bash -c 'ln -sf $(readlink "$1" | sed "s/amslpr/visigate/g") "$1"' _ {} \;
   ```

### Step 3: Update Environment Variables

1. **Update system environment:**
   ```bash
   # Edit /etc/environment or your shell profile
   sudo nano /etc/environment
   
   # Replace:
   # AMSLPR_DATA_DIR=/var/lib/amslpr
   # AMSLPR_LOG_DIR=/var/log/amslpr
   # AMSLPR_CONFIG_DIR=/etc/amslpr
   
   # With:
   # VISIGATE_DATA_DIR=/var/lib/visigate
   # VISIGATE_LOG_DIR=/var/log/visigate
   # VISIGATE_CONFIG_DIR=/etc/visigate
   ```

2. **Update service file environment variables:**
   ```bash
   sudo nano /etc/systemd/system/visigate.service
   
   # Update any Environment= lines from AMSLPR_* to VISIGATE_*
   ```

3. **Source the new environment:**
   ```bash
   source /etc/environment
   ```

### Step 4: Update Configuration Files

1. **Update config.json (if exists):**
   ```bash
   sudo nano /etc/visigate/config.json
   
   # Update any references to "amslpr" or "AMSLPR" to "visigate" or "VISIGATE"
   ```

2. **Update Nginx configuration (if using):**
   ```bash
   sudo nano /etc/nginx/sites-available/visigate
   
   # Update server_name and any amslpr references
   sudo mv /etc/nginx/sites-available/amslpr /etc/nginx/sites-available/visigate
   sudo rm /etc/nginx/sites-enabled/amslpr
   sudo ln -s /etc/nginx/sites-available/visigate /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### Step 5: Update Database (if needed)

The database schema doesn't need changes, but you may want to update any stored configuration:

```bash
# Connect to SQLite database
sqlite3 /var/lib/visigate/visigate.db

# Update any system settings that reference old names
UPDATE settings SET value = REPLACE(value, 'AMSLPR', 'VisiGate') WHERE key LIKE '%name%';
UPDATE settings SET value = REPLACE(value, 'amslpr', 'visigate') WHERE key LIKE '%path%';

# Exit
.quit
```

### Step 6: Update Python Virtual Environment (if applicable)

```bash
cd /opt/visigate

# Deactivate if active
deactivate

# Update venv references
find venv -type f -name "*.py" -o -name "activate*" | xargs sed -i 's/AMSLPR/VisiGate/g'
find venv -type f -name "*.py" -o -name "activate*" | xargs sed -i 's/amslpr/visigate/g'

# Reinstall package in development mode
source venv/bin/activate
pip install -e .
```

### Step 7: Update Cron Jobs and Scripts

```bash
# List current cron jobs
crontab -l > /tmp/old-cron.txt

# Edit cron jobs
crontab -e

# Replace any references to:
# - /opt/amslpr → /opt/visigate
# - amslpr.service → visigate.service
# - AMSLPR environment variables → VISIGATE
```

### Step 8: Start the New Service

```bash
# Enable and start the new service
sudo systemctl enable visigate
sudo systemctl start visigate

# Check status
sudo systemctl status visigate

# View logs
sudo journalctl -u visigate -f
```

---

## Verification

After migration, verify the system is working correctly:

### 1. Service Status
```bash
systemctl status visigate
# Should show "active (running)"
```

### 2. Web Interface
```bash
# Access the web interface (default: http://localhost:5000)
curl http://localhost:5000/health
```

### 3. Database Connectivity
```bash
# Check database exists and is accessible
ls -la /var/lib/visigate/visigate.db
```

### 4. Log Files
```bash
# Verify logs are being written
tail -f /var/log/visigate/*.log
```

### 5. Camera Connectivity
```bash
# Test camera connections through web interface or API
curl -X GET http://localhost:5000/api/cameras
```

---

## Troubleshooting

### Service Won't Start

**Problem:** `systemctl start visigate` fails

**Solutions:**
1. Check service file syntax:
   ```bash
   systemctl cat visigate
   ```

2. Check for path errors:
   ```bash
   sudo journalctl -u visigate -n 50
   ```

3. Verify Python path in service file:
   ```bash
   which python3
   # Update ExecStart in service file if needed
   ```

### Database Not Found

**Problem:** "Unable to open database file" error

**Solution:**
```bash
# Verify database location
ls -la /var/lib/visigate/

# Check permissions
sudo chown -R visigate:visigate /var/lib/visigate/
sudo chmod 755 /var/lib/visigate/
sudo chmod 664 /var/lib/visigate/visigate.db
```

### Import Errors

**Problem:** "ModuleNotFoundError: No module named 'amslpr'"

**Solution:**
```bash
# Reinstall package
cd /opt/visigate
source venv/bin/activate
pip uninstall -y amslpr visigate
pip install -e .
```

### Environment Variables Not Working

**Problem:** Old AMSLPR_* variables still being used

**Solution:**
```bash
# Clear old variables
sudo sed -i '/AMSLPR/d' /etc/environment

# Add new variables
echo "VISIGATE_DATA_DIR=/var/lib/visigate" | sudo tee -a /etc/environment
echo "VISIGATE_LOG_DIR=/var/log/visigate" | sudo tee -a /etc/environment
echo "VISIGATE_CONFIG_DIR=/etc/visigate" | sudo tee -a /etc/environment

# Reload
source /etc/environment

# Restart service
sudo systemctl restart visigate
```

---

## Rollback Procedure

If you need to rollback to AMSLPR:

```bash
# Stop new service
sudo systemctl stop visigate
sudo systemctl disable visigate

# Restore directories
sudo mv /var/lib/visigate /var/lib/amslpr
sudo mv /var/log/visigate /var/log/amslpr
sudo mv /etc/visigate /etc/amslpr
sudo mv /opt/visigate /opt/amslpr

# Restore service
sudo mv /etc/systemd/system/visigate.service /etc/systemd/system/amslpr.service
sudo sed -i 's/visigate/amslpr/g' /etc/systemd/system/amslpr.service
sudo systemctl daemon-reload

# Restore environment
sudo sed -i 's/VISIGATE/AMSLPR/g' /etc/environment
source /etc/environment

# Restore database from backup
sudo cp /var/lib/amslpr/visigate.db.backup /var/lib/amslpr/visigate.db

# Start old service
sudo systemctl enable amslpr
sudo systemctl start amslpr
```

---

## Post-Migration Tasks

### 1. Update Documentation
- Update any internal documentation referencing AMSLPR
- Update API documentation with new endpoints
- Update user manuals with new branding

### 2. Update Monitoring
- Update monitoring tools to check `visigate` service instead of `amslpr`
- Update alert configurations
- Update dashboard configurations

### 3. Update Backups
- Update backup scripts with new paths
- Test backup and restore procedures with new names
- Update backup retention policies

### 4. Notify Users
- Inform users of the rebranding
- Provide updated login URLs if they changed
- Update any documentation or training materials

---

## Support

If you encounter issues during migration:

1. **Check the logs:**
   ```bash
   sudo journalctl -u visigate -n 100
   tail -f /var/log/visigate/visiongate.log
   ```

2. **Verify all paths were updated:**
   ```bash
   grep -r "amslpr" /etc/systemd/system/
   grep -r "AMSLPR" /etc/environment
   ```

3. **Test in development mode:**
   ```bash
   cd /opt/visigate
   source venv/bin/activate
   python src/main.py --config config/config.json
   ```

4. **Contact Support:**
   - GitHub Issues: https://github.com/visigate/visigate/issues
   - Email: support@visigate.com

---

## Important Notes

- ⚠️ **The database file remains named `visigate.db`** - only the directory path changes
- ⚠️ **Camera credentials** are encrypted and should migrate automatically
- ⚠️ **User sessions** will be invalidated; users will need to log in again
- ⚠️ **API tokens** remain valid but API endpoint URLs may have changed
- ⚠️ **Backups created before migration** use old paths and naming

---

## Changes Summary

| Component | Old (AMSLPR) | New (VisiGate) |
|-----------|--------------|----------------|
| Product Name | AMSLPR | VisiGate |
| Copyright | Automate Systems | VisiGate |
| Service Name | amslpr.service | visigate.service |
| Package Name | amslpr | visigate |
| Install Dir | /opt/amslpr | /opt/visigate |
| Data Dir | /var/lib/amslpr | /var/lib/visigate |
| Log Dir | /var/log/amslpr | /var/log/visigate |
| Config Dir | /etc/amslpr | /etc/visigate |
| Env Prefix | AMSLPR_* | VISIGATE_* |
| Logger | AMSLPR.* | VisiGate.* |

---

## FAQ

**Q: Will my camera configurations be lost?**
A: No, all camera configurations are stored in the database and will be preserved.

**Q: Do I need to re-add authorized vehicles?**
A: No, the vehicle database is unchanged and all authorizations remain intact.

**Q: Will historical data be preserved?**
A: Yes, all historical access logs, statistics, and reports are preserved.

**Q: Can I run both AMSLPR and VisiGate simultaneously?**
A: No, they share the same database structure. Choose one or migrate completely.

**Q: What about third-party integrations?**
A: Update integration configurations to point to new service name and paths.

---

*Last Updated: 2025-11-01*
*VisiGate Version: 1.0.0*