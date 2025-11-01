#!/bin/bash

# VisiGate Backup and Restore Script
# This script provides functionality to backup and restore the VisiGate system

set -e

# Text colors
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Print header
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}       VisiGate Backup and Restore Script                  ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Default configuration variables
DATA_DIR="/var/lib/visigate"
CONFIG_DIR="/etc/visigate"
BACKUP_DIR="/var/lib/visigate/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="visigate_backup_${TIMESTAMP}.tar.gz"
COMPRESSION="gzip"

# Function to display usage information
usage() {
    echo "Usage: $0 [options] [command]"
    echo
    echo "Commands:"
    echo "  backup              Create a backup of the VisiGate system"
    echo "  restore <file>      Restore the VisiGate system from a backup file"
    echo "  list                List available backup files"
    echo "  schedule            Set up a scheduled backup using cron"
    echo "  help                Display this help message"
    echo
    echo "Options:"
    echo "  --data-dir <dir>    Specify the data directory (default: $DATA_DIR)"
    echo "  --config-dir <dir>  Specify the config directory (default: $CONFIG_DIR)"
    echo "  --backup-dir <dir>  Specify the backup directory (default: $BACKUP_DIR)"
    echo "  --output <file>     Specify the output file for backup (default: auto-generated)"
    echo "  --compression <type> Specify compression type (gzip, bzip2, none) (default: gzip)"
    echo
    echo "Examples:"
    echo "  $0 backup                      # Create a backup with default settings"
    echo "  $0 --output /tmp/backup.tar.gz backup  # Create a backup with custom output file"
    echo "  $0 restore /tmp/backup.tar.gz  # Restore from a backup file"
    echo "  $0 list                        # List available backup files"
    echo "  $0 schedule                    # Set up a scheduled backup"
    exit 1
}

# Parse command line arguments
COMMAND=""
RESTORE_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        backup|restore|list|schedule|help)
            COMMAND="$1"
            shift
            if [ "$COMMAND" = "restore" ] && [ $# -gt 0 ]; then
                RESTORE_FILE="$1"
                shift
            fi
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --output)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --compression)
            COMPRESSION="$2"
            if [ "$COMPRESSION" != "gzip" ] && [ "$COMPRESSION" != "bzip2" ] && [ "$COMPRESSION" != "none" ]; then
                echo -e "${RED}Error: Invalid compression type. Must be gzip, bzip2, or none.${NC}"
                exit 1
            fi
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Check if command is provided
if [ -z "$COMMAND" ]; then
    echo -e "${RED}Error: No command specified${NC}"
    usage
fi

# Display help if requested
if [ "$COMMAND" = "help" ]; then
    usage
fi

# Function to create a backup
create_backup() {
    echo -e "${YELLOW}Creating backup of VisiGate system...${NC}"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Create temporary directory for backup
    TEMP_DIR=$(mktemp -d)
    
    # Create directory structure in temp directory
    mkdir -p "$TEMP_DIR/data"
    mkdir -p "$TEMP_DIR/config"
    
    # Copy data files
    echo -e "${YELLOW}Copying data files...${NC}"
    cp -r "$DATA_DIR"/* "$TEMP_DIR/data/"
    
    # Copy configuration files
    echo -e "${YELLOW}Copying configuration files...${NC}"
    cp -r "$CONFIG_DIR"/* "$TEMP_DIR/config/"
    
    # Add backup metadata
    echo "Backup created on $(date)" > "$TEMP_DIR/backup_info.txt"
    echo "VisiGate version: $(cat /opt/visigate/version.txt 2>/dev/null || echo 'unknown')" >> "$TEMP_DIR/backup_info.txt"
    echo "Hostname: $(hostname)" >> "$TEMP_DIR/backup_info.txt"
    echo "Data directory: $DATA_DIR" >> "$TEMP_DIR/backup_info.txt"
    echo "Config directory: $CONFIG_DIR" >> "$TEMP_DIR/backup_info.txt"
    
    # Create archive
    echo -e "${YELLOW}Creating archive...${NC}"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"
    
    if [ "$COMPRESSION" = "gzip" ]; then
        tar -czf "$BACKUP_PATH" -C "$TEMP_DIR" .
    elif [ "$COMPRESSION" = "bzip2" ]; then
        tar -cjf "$BACKUP_PATH" -C "$TEMP_DIR" .
    else
        tar -cf "$BACKUP_PATH" -C "$TEMP_DIR" .
    fi
    
    # Clean up temporary directory
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}Backup created successfully: $BACKUP_PATH${NC}"
    echo -e "${GREEN}Backup size: $(du -h "$BACKUP_PATH" | cut -f1)${NC}"
}

# Function to restore from a backup
restore_from_backup() {
    local backup_file="$1"
    
    # Check if backup file exists
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found: $backup_file${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Restoring VisiGate system from backup: $backup_file${NC}"
    
    # Create temporary directory for extraction
    TEMP_DIR=$(mktemp -d)
    
    # Extract archive
    echo -e "${YELLOW}Extracting archive...${NC}"
    tar -xf "$backup_file" -C "$TEMP_DIR"
    
    # Check if backup is valid
    if [ ! -d "$TEMP_DIR/data" ] || [ ! -d "$TEMP_DIR/config" ]; then
        echo -e "${RED}Error: Invalid backup file format${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Display backup information
    if [ -f "$TEMP_DIR/backup_info.txt" ]; then
        echo -e "${BLUE}Backup information:${NC}"
        cat "$TEMP_DIR/backup_info.txt"
        echo
    fi
    
    # Confirm restoration
    echo -e "${RED}WARNING: This will overwrite existing data and configuration files!${NC}"
    read -p "Are you sure you want to proceed? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Restoration cancelled${NC}"
        rm -rf "$TEMP_DIR"
        exit 0
    fi
    
    # Stop VisiGate service if running
    if systemctl is-active --quiet visigate.service; then
        echo -e "${YELLOW}Stopping VisiGate service...${NC}"
        systemctl stop visigate.service
    fi
    
    # Backup current data and config (just in case)
    CURRENT_BACKUP_DIR="$BACKUP_DIR/pre_restore_${TIMESTAMP}"
    mkdir -p "$CURRENT_BACKUP_DIR/data"
    mkdir -p "$CURRENT_BACKUP_DIR/config"
    
    echo -e "${YELLOW}Backing up current data and configuration...${NC}"
    cp -r "$DATA_DIR"/* "$CURRENT_BACKUP_DIR/data/" 2>/dev/null || true
    cp -r "$CONFIG_DIR"/* "$CURRENT_BACKUP_DIR/config/" 2>/dev/null || true
    
    # Restore data files
    echo -e "${YELLOW}Restoring data files...${NC}"
    rm -rf "$DATA_DIR"/*
    cp -r "$TEMP_DIR/data"/* "$DATA_DIR/"
    
    # Restore configuration files
    echo -e "${YELLOW}Restoring configuration files...${NC}"
    rm -rf "$CONFIG_DIR"/*
    cp -r "$TEMP_DIR/config"/* "$CONFIG_DIR/"
    
    # Set proper permissions
    echo -e "${YELLOW}Setting proper permissions...${NC}"
    chown -R www-data:www-data "$DATA_DIR"
    chmod -R 755 "$DATA_DIR"
    chmod -R 640 "$CONFIG_DIR/config.json"
    
    # Clean up temporary directory
    rm -rf "$TEMP_DIR"
    
    # Start VisiGate service
    echo -e "${YELLOW}Starting VisiGate service...${NC}"
    systemctl start visigate.service
    
    echo -e "${GREEN}Restoration completed successfully${NC}"
    echo -e "${YELLOW}A backup of the previous state was created at: $CURRENT_BACKUP_DIR${NC}"
}

# Function to list available backups
list_backups() {
    echo -e "${YELLOW}Available backups in $BACKUP_DIR:${NC}"
    
    # Check if backup directory exists
    if [ ! -d "$BACKUP_DIR" ]; then
        echo -e "${RED}Backup directory not found: $BACKUP_DIR${NC}"
        exit 1
    fi
    
    # List backup files
    BACKUP_FILES=$(find "$BACKUP_DIR" -name "visigate_backup_*.tar.gz" -type f | sort -r)
    
    if [ -z "$BACKUP_FILES" ]; then
        echo -e "${YELLOW}No backup files found${NC}"
        exit 0
    fi
    
    # Display backup files with size and date
    echo -e "${BLUE}Date               Size    Filename${NC}"
    echo -e "${BLUE}------------------------------------------${NC}"
    
    while IFS= read -r file; do
        # Extract date from filename
        filename=$(basename "$file")
        date_str=$(echo "$filename" | grep -o "[0-9]\{8\}_[0-9]\{6\}")
        formatted_date=$(date -d "$(echo "$date_str" | sed 's/_/ /' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/')" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "Unknown")
        
        # Get file size
        file_size=$(du -h "$file" | cut -f1)
        
        echo -e "${formatted_date}  ${file_size}  ${filename}"
    done <<< "$BACKUP_FILES"
}

# Function to set up scheduled backups
schedule_backups() {
    echo -e "${YELLOW}Setting up scheduled backups...${NC}"
    
    # Ask for schedule
    echo "Select backup frequency:"
    echo "1) Daily"
    echo "2) Weekly"
    echo "3) Monthly"
    read -p "Enter your choice (1-3): " choice
    
    # Create cron job based on selection
    CRON_JOB=""
    case $choice in
        1)
            read -p "Enter hour (0-23): " hour
            CRON_JOB="0 $hour * * * root $0 backup > /var/log/visigate-backup.log 2>&1"
            SCHEDULE_DESC="daily at $hour:00"
            ;;
        2)
            read -p "Enter day of week (0-6, where 0 is Sunday): " dow
            read -p "Enter hour (0-23): " hour
            CRON_JOB="0 $hour * * $dow root $0 backup > /var/log/visigate-backup.log 2>&1"
            SCHEDULE_DESC="weekly on $(date -d "Sunday + $dow days" "+%A") at $hour:00"
            ;;
        3)
            read -p "Enter day of month (1-28): " dom
            read -p "Enter hour (0-23): " hour
            CRON_JOB="0 $hour $dom * * root $0 backup > /var/log/visigate-backup.log 2>&1"
            SCHEDULE_DESC="monthly on day $dom at $hour:00"
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    # Add retention policy
    read -p "Enter number of backups to keep (0 for unlimited): " retention
    if [ "$retention" -gt 0 ]; then
        CLEANUP_JOB="30 $hour * * * root find $BACKUP_DIR -name 'visigate_backup_*.tar.gz' -type f -printf '%T@ %p\n' | sort -n | head -n -$retention | cut -d' ' -f2- | xargs -r rm"
        echo -e "${YELLOW}Retention policy: Keep last $retention backups${NC}"
    else
        CLEANUP_JOB=""
        echo -e "${YELLOW}Retention policy: Keep all backups${NC}"
    fi
    
    # Create cron file
    CRON_FILE="/etc/cron.d/visigate-backup"
    echo "# VisiGate scheduled backup" > "$CRON_FILE"
    echo "$CRON_JOB" >> "$CRON_FILE"
    
    if [ -n "$CLEANUP_JOB" ]; then
        echo "$CLEANUP_JOB" >> "$CRON_FILE"
    fi
    
    # Set proper permissions
    chmod 644 "$CRON_FILE"
    
    echo -e "${GREEN}Scheduled backup configured successfully${NC}"
    echo -e "${GREEN}Backups will run $SCHEDULE_DESC${NC}"
    echo -e "${GREEN}Cron job added to: $CRON_FILE${NC}"
}

# Execute the requested command
case $COMMAND in
    backup)
        create_backup
        ;;
    restore)
        if [ -z "$RESTORE_FILE" ]; then
            echo -e "${RED}Error: No backup file specified for restoration${NC}"
            usage
        fi
        restore_from_backup "$RESTORE_FILE"
        ;;
    list)
        list_backups
        ;;
    schedule)
        schedule_backups
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        ;;
esac

exit 0
