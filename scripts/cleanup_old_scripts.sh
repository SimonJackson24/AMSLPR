#!/bin/bash

# AMSLPR - Cleanup Old Scripts
# This script removes obsolete or redundant scripts from the scripts directory

echo "Cleaning up old scripts..."

# List of scripts to remove (add more as needed)
SCRIPTS_TO_REMOVE=(
    "fix_hailo_installation.sh"
    "diagnose_hailo.sh"
    "download_hailo_sdk.sh"
    "download_offline_packages.sh"
    "enable_hailo_tpu.py"
    "fix_hailo_imports.py"
    "fix_hailo_tpu_config.py"
    "verify_hailo_installation.py"
    "hailo_raspberry_pi_setup.sh"
    "install_on_raspberry_pi.sh"
    "offline_install.sh"
    "run_with_hailo.sh"
    "test_installation.sh"
    "test_server.sh"
    "troubleshoot.sh"
)

# Create backup directory for scripts that will be removed
BACKUP_DIR="scripts/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Remove scripts with confirmation
REMOVED_COUNT=0
for script in "${SCRIPTS_TO_REMOVE[@]}"; do
    if [ -f "scripts/$script" ]; then
        echo "Moving $script to backup directory..."
        mv "scripts/$script" "$BACKUP_DIR/" 2>/dev/null
        ((REMOVED_COUNT++))
    fi
done

if [ $REMOVED_COUNT -gt 0 ]; then
    echo "✅ Moved $REMOVED_COUNT old scripts to $BACKUP_DIR"
    echo "These scripts can be restored if needed from the backup directory."
else
    echo "ℹ️ No old scripts found to clean up."
fi

echo "✅ Script cleanup completed!"