#!/bin/bash

# VisionGate Backup Script
# Creates automated backups of data and configuration

set -e

# Configuration
BACKUP_DIR="/home/visiongate/backups"
APP_DIR="/home/visiongate/visiongate-app"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "=== VisionGate Backup Script ==="
echo "Starting backup process..."

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/visiongate_backup_$DATE.tar.gz"

echo "Creating backup: $BACKUP_FILE"

# Navigate to app directory
cd $APP_DIR

# Create backup of essential data
tar -czf $BACKUP_FILE \
    data/ \
    config/ \
    models/ \
    uploads/ \
    --exclude=data/logs/*.log \
    --exclude=data/temp/* \
    --exclude=uploads/temp/*

# Check if backup was created successfully
if [ -f "$BACKUP_FILE" ]; then
    echo "✅ Backup created successfully!"
    echo "Backup size: $(du -h $BACKUP_FILE | cut -f1)"
    
    # Remove old backups (keep last 7 days)
    echo "Removing old backups (older than $RETENTION_DAYS days)..."
    find $BACKUP_DIR -name "visiongate_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    echo "Old backups removed."
    
    # List current backups
    echo ""
    echo "Current backups:"
    ls -lh $BACKUP_DIR/visiongate_backup_*.tar.gz
else
    echo "❌ Backup failed!"
    exit 1
fi

echo ""
echo "=== Backup Complete ==="