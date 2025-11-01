# VisiGate User Guide

Welcome to the Vision-Based Access Control System (VisiGate) system user guide. This document will help you understand how to use and manage the system effectively.

## Getting Started

### Accessing the Web Interface

The VisiGate system provides a web-based interface for administration and monitoring. To access it:

1. Open a web browser on any device connected to the same network as your Raspberry Pi
2. Enter the IP address of your Raspberry Pi followed by port 5000 in the address bar:
   ```
   http://<raspberry-pi-ip>:5000
   ```
3. Log in with your username and password (default: admin/admin)

### Dashboard Overview

The dashboard provides an overview of the system status:

- **Authorized Vehicles**: The number of vehicles authorized to access
- **Unauthorized Vehicles**: The number of vehicles without authorization
- **Recent Access Logs**: A list of recent entry and exit events

## Managing Vehicles

### Viewing Vehicles

1. Click on the "Vehicles" link in the navigation menu
2. The system displays a list of all registered vehicles
3. You can see each vehicle's plate number, description, and authorization status

### Adding a Vehicle

1. On the Vehicles page, click the "Add Vehicle" button
2. Enter the vehicle's license plate number (e.g., ABC123)
3. Optionally add a description (e.g., "John's Car", "Company Vehicle")
4. Check the "Authorized" checkbox if the vehicle should have access
5. Click "Add Vehicle" to save

### Editing a Vehicle

1. On the Vehicles page, find the vehicle you want to edit
2. Click the edit (pencil) icon in the Actions column
3. Update the vehicle's description or authorization status
4. Click "Update Vehicle" to save changes

### Deleting a Vehicle

1. On the Vehicles page, find the vehicle you want to delete
2. Click the delete (trash) icon in the Actions column
3. Confirm the deletion when prompted

## Viewing Access Logs

### All Access Logs

1. Click on the "Access Logs" link in the navigation menu
2. The system displays a list of all access events
3. Each entry shows the time, plate number, direction (entry/exit), and authorization status

### Filtering Access Logs

1. On the Access Logs page, use the filter box at the top
2. Enter a license plate number to filter logs for a specific vehicle
3. Click "Filter" to apply or "Clear" to remove the filter

### Vehicle History

1. On the Vehicles page, find the vehicle you want to view history for
2. Click the history (clock) icon in the Actions column
3. The system displays all access logs for that specific vehicle

## System Operation

### How the System Works

1. **Vehicle Approach**: When a vehicle approaches the barrier, the camera captures an image
2. **License Plate Recognition**: The system processes the image to extract the license plate number
3. **Authorization Check**: The system checks if the plate number is in the authorized vehicles list
4. **Barrier Control**: If authorized, the system opens the barrier; if not, the barrier remains closed
5. **Logging**: The system logs the event with plate number, time, direction, and authorization status

### Entry and Exit Process

- **Entry**: The system captures the license plate at the entry point, checks authorization, and opens the barrier if authorized
- **Exit**: The system captures the license plate at the exit point, logs the exit event, and opens the barrier

## Troubleshooting

### Recognition Issues

- **Problem**: System fails to recognize license plates
- **Solution**: Check camera positioning, lighting conditions, and ensure the camera lens is clean

### Barrier Control Issues

- **Problem**: Barrier doesn't open for authorized vehicles
- **Solution**: Check relay connections and barrier control mechanism

### System Access Issues

- **Problem**: Can't access the web interface
- **Solution**: Verify network connections, check if the VisiGate service is running

### Checking System Status

To check if the VisiGate service is running:

```bash
sudo systemctl status visigate.service
```

To restart the service if needed:

```bash
sudo systemctl restart visigate.service
```

## Best Practices

### Security

- Change the default admin password immediately after installation
- Regularly review the access logs for unauthorized access attempts
- Consider implementing a regular backup schedule for the database

### Maintenance

- Clean the camera lens regularly to ensure clear images
- Check all connections periodically
- Update the system software when updates are available

### Vehicle Management

- Use descriptive names for vehicles to easily identify them
- Regularly review the authorized vehicles list to remove outdated entries
- Consider adding time restrictions for temporary access (if supported)
