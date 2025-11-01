# Backup and Restore Guide

## Overview

This guide provides instructions for backing up and restoring the VisiGate system. Regular backups are essential to protect your data and ensure business continuity in case of hardware failure, data corruption, or other issues.

The VisiGate system includes a comprehensive backup and restore utility that simplifies the process of creating, managing, and restoring backups.

## Backup Components

The VisiGate backup system includes the following components:

1. **Data Files**: All database files, including vehicle records, access logs, and system configuration.
2. **Configuration Files**: System configuration files that define how the system operates.
3. **Backup Metadata**: Information about when the backup was created and what it contains.

## Backup Utility

The VisiGate system includes a backup utility script (`scripts/backup_restore.sh`) that provides the following functionality:

- Creating backups
- Restoring from backups
- Listing available backups
- Setting up scheduled backups

### Basic Usage

#### Creating a Backup

To create a backup, run the following command as root:

```bash
sudo /opt/visigate/scripts/backup_restore.sh backup
```

This will create a backup in the default backup directory (`/var/lib/visigate/backups`) with a timestamp in the filename.

#### Listing Available Backups

To list available backups, run:

```bash
sudo /opt/visigate/scripts/backup_restore.sh list
```

This will display a list of available backups with their creation date, size, and filename.

#### Restoring from a Backup

To restore from a backup, run:

```bash
sudo /opt/visigate/scripts/backup_restore.sh restore /var/lib/visigate/backups/visigate_backup_20250314_123456.tar.gz
```

This will restore the system from the specified backup file. The script will prompt for confirmation before proceeding with the restoration.

#### Setting Up Scheduled Backups

To set up scheduled backups, run:

```bash
sudo /opt/visigate/scripts/backup_restore.sh schedule
```

This will guide you through the process of setting up scheduled backups using cron. You can choose the frequency (daily, weekly, or monthly) and specify how many backups to keep.

### Advanced Usage

The backup utility script supports various command-line options to customize its behavior:

```bash
sudo /opt/visigate/scripts/backup_restore.sh [options] [command]
```

#### Commands

- `backup`: Create a backup
- `restore <file>`: Restore from a backup file
- `list`: List available backups
- `schedule`: Set up scheduled backups
- `help`: Display help information

#### Options

- `--data-dir <dir>`: Specify the data directory (default: `/var/lib/visigate`)
- `--config-dir <dir>`: Specify the config directory (default: `/etc/visigate`)
- `--backup-dir <dir>`: Specify the backup directory (default: `/var/lib/visigate/backups`)
- `--output <file>`: Specify the output file for backup (default: auto-generated)
- `--compression <type>`: Specify compression type (gzip, bzip2, none) (default: gzip)

## Backup Storage Recommendations

To ensure the safety of your backups, consider the following recommendations:

1. **Off-site Storage**: Store backups in a different physical location from the VisiGate system.
2. **Multiple Copies**: Keep multiple copies of important backups.
3. **Regular Testing**: Regularly test restoring from backups to ensure they are valid.
4. **Encryption**: Consider encrypting backups that contain sensitive information.

## Backup Retention Policy

The VisiGate backup system includes a configurable retention policy that determines how many backups to keep. By default, the system keeps the 5 most recent backups, but this can be adjusted when setting up scheduled backups.

To manually clean up old backups, you can use the `find` command. For example, to keep only the 10 most recent backups:

```bash
sudo find /var/lib/visigate/backups -name 'visigate_backup_*.tar.gz' -type f -printf '%T@ %p\n' | sort -n | head -n -10 | cut -d' ' -f2- | xargs -r rm
```

## Backup Verification

To verify that a backup is valid, you can use the `tar` command to list its contents:

```bash
sudo tar -tvf /var/lib/visigate/backups/visigate_backup_20250314_123456.tar.gz
```

This will display a list of files contained in the backup without extracting them.

## Disaster Recovery

In case of a system failure, follow these steps to recover the VisiGate system:

1. **Install the VisiGate System**: If necessary, reinstall the VisiGate system using the installation script.
2. **Restore from Backup**: Use the backup utility script to restore from the most recent backup.

```bash
sudo /opt/visigate/scripts/backup_restore.sh restore /path/to/backup/file
```

3. **Verify the Restoration**: Verify that the system is functioning correctly after the restoration.

## Troubleshooting

### Backup Creation Fails

If backup creation fails, check the following:

1. **Disk Space**: Ensure that there is sufficient disk space available.
2. **Permissions**: Ensure that the script is run as root and has permission to access the necessary directories.
3. **File System Errors**: Check for file system errors using `fsck`.

### Restoration Fails

If restoration fails, check the following:

1. **Backup File Integrity**: Verify that the backup file is not corrupted.
2. **Permissions**: Ensure that the script is run as root and has permission to access the necessary directories.
3. **Compatibility**: Ensure that the backup was created with a compatible version of the VisiGate system.

## Conclusion

Regular backups are essential for protecting your data and ensuring business continuity. The VisiGate backup and restore utility simplifies the process of creating, managing, and restoring backups, making it easy to maintain a robust backup strategy.

For additional assistance with backup and restore operations, please refer to the [Troubleshooting Guide](troubleshooting.md) or contact support.
