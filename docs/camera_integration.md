# Camera Integration Guide

## Overview

The VisiGate system supports two types of cameras for license plate recognition:

1. **Local Cameras**: Connected directly to the Raspberry Pi via USB or the built-in camera interface
2. **ONVIF IP Cameras**: Network cameras that support the ONVIF protocol

This guide explains how to set up and configure both types of cameras for use with the VisiGate system.

## Local Camera Setup

### Raspberry Pi Camera Module

1. Connect the camera module to the Raspberry Pi's camera port using the ribbon cable
2. Enable the camera interface in Raspberry Pi configuration:
   ```
   sudo raspi-config
   ```
   Navigate to "Interfacing Options" > "Camera" and select "Yes"
3. Reboot the Raspberry Pi:
   ```
   sudo reboot
   ```
4. Update the VisiGate configuration to use the local camera (camera_id: 0)

### USB Camera

1. Connect the USB camera to one of the Raspberry Pi's USB ports
2. Verify that the camera is detected:
   ```
   ls -l /dev/video*
   ```
3. Update the VisiGate configuration to use the USB camera (camera_id: typically 0 or 1)

## ONVIF IP Camera Setup

### Requirements

- ONVIF-compatible IP camera
- Network connectivity between the Raspberry Pi and the IP camera
- Camera credentials (username and password)

### Configuration

1. **Web Interface Setup**:
   - Navigate to the VisiGate web interface
   - Go to the "Cameras" section
   - Click "Add Camera" or "Discover Cameras"

2. **Manual Camera Addition**:
   - Provide the following information:
     - Camera ID: A unique identifier for the camera (e.g., "entrance", "exit")
     - Camera Name: A descriptive name (e.g., "Main Entrance")
     - Location: Physical location description (e.g., "Front Gate")
     - IP Address: The IP address of the camera
     - Port: The HTTP port of the camera (typically 80)
     - Username: ONVIF account username (typically "admin")
     - Password: ONVIF account password
   - Click "Add Camera"

3. **Camera Discovery**:
   - Click "Discover Cameras" to automatically find ONVIF cameras on the network
   - Select the cameras you want to add from the discovered list
   - Provide credentials if needed
   - Click "Add Selected Cameras"

### Camera Management

Once cameras are added, you can:

- **View Live Feed**: Click "View" to see the camera's live video feed
- **Start/Stop Stream**: Control when the camera is actively streaming
- **Start/Stop Recognition**: Enable or disable license plate recognition for the camera
- **Capture Snapshot**: Take a still image from the camera
- **Remove Camera**: Remove the camera from the system

## Configuration File

Cameras can also be pre-configured in the configuration file located at `config/config.json`:

```json
{
    "camera": {
        "discovery_enabled": true,
        "discovery_interval": 60,
        "default_username": "admin",
        "default_password": "admin",
        "cameras": [
            {
                "id": "entrance",
                "name": "Main Entrance",
                "location": "Front Gate",
                "ip": "192.168.1.100",
                "port": 80,
                "username": "admin",
                "password": "admin"
            },
            {
                "id": "exit",
                "name": "Exit Gate",
                "location": "Back Gate",
                "ip": "192.168.1.101",
                "port": 80,
                "username": "admin",
                "password": "admin"
            }
        ]
    }
}
```

## Troubleshooting

### Camera Connection Issues

1. **Verify Network Connectivity**:
   ```
   ping [camera-ip-address]
   ```

2. **Check ONVIF Credentials**:
   Ensure the username and password are correct

3. **Verify ONVIF Compatibility**:
   Not all IP cameras support ONVIF. Check the camera's documentation.

4. **Check Firewall Settings**:
   Ensure that the required ports are open (typically 80, 554, and 8000-8999)

### Video Stream Issues

1. **Check Camera Resolution**:
   Some high-resolution streams may be too demanding for the Raspberry Pi

2. **Verify RTSP URL**:
   The system attempts to automatically determine the RTSP URL, but some cameras use non-standard formats

3. **Network Bandwidth**:
   Ensure sufficient network bandwidth is available for video streaming

## Performance Optimization

1. **Resolution**: Lower the camera resolution for better performance
2. **Frame Rate**: Reduce the frame rate for license plate recognition (5-10 FPS is typically sufficient)
3. **Camera Positioning**: Position cameras to capture license plates head-on for best recognition results
4. **Lighting**: Ensure adequate lighting for clear license plate visibility

## Advanced Configuration

Advanced users can modify the ONVIF camera settings by editing the `src/recognition/onvif_camera.py` file. This allows customization of:

- Discovery methods
- Stream profiles
- Connection timeouts
- Error handling behavior

## Support

For additional help with camera setup and configuration, please refer to:

- The camera manufacturer's documentation
- ONVIF protocol documentation (www.onvif.org)
- VisiGate project support channels
