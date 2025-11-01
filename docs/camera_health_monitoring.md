# Camera Health Monitoring

The VisiGate system includes a comprehensive camera health monitoring system that ensures reliable operation of all connected cameras. This document describes the camera health monitoring features and how to use them.

## Overview

The camera health monitoring system continuously monitors the status of all cameras in the system and provides the following features:

- **Automatic Status Monitoring**: Continuously checks the status of all cameras to detect issues
- **Reconnection Attempts**: Automatically attempts to reconnect to offline or stalled cameras
- **Notification System**: Sends alerts when camera issues are detected
- **Health Dashboard**: Provides a web interface for monitoring camera health

## Camera Health States

Cameras can be in one of the following health states:

- **Healthy**: Camera is connected and streaming frames normally
- **Stalled**: Camera is connected but not receiving new frames
- **Offline**: Camera is disconnected or not responding

## Health Monitoring Dashboard

The camera health monitoring dashboard provides a real-time view of the status of all cameras in the system. To access the dashboard, navigate to:

```
http://[server-address]/cameras/health
```

The dashboard includes the following information:

- **Summary Statistics**: Total number of cameras, number of healthy/stalled/offline cameras, and overall health percentage
- **Camera Status Table**: Detailed information about each camera, including status, last frame time, and FPS
- **Actions**: Buttons to view camera feeds and restart problematic cameras

## Automatic Reconnection

When a camera goes offline or becomes stalled, the system will automatically attempt to reconnect to it. The reconnection process follows an exponential backoff strategy to avoid overwhelming the camera with reconnection attempts:

1. First attempt: 30 seconds after detecting the issue
2. Second attempt: 60 seconds after the first attempt
3. Third attempt: 2 minutes after the second attempt
4. Fourth attempt: 5 minutes after the third attempt
5. Fifth attempt: 10 minutes after the fourth attempt

If all reconnection attempts fail, the system will send a final notification indicating that manual intervention may be required.

## Manual Camera Restart

If automatic reconnection fails, you can manually restart a camera from the health dashboard by clicking the "Restart" button next to the camera. This will:

1. Stop the camera stream if it's running
2. Wait a moment for the camera to reset
3. Start the stream again

## Notifications

The camera health monitoring system can send notifications when camera issues are detected. Notifications are sent in the following situations:

- When a camera goes offline or becomes stalled
- When reconnection attempts fail

Notifications are sent through the system's notification channels, which can include email, SMS, and webhooks.

## Configuration

The camera health monitoring system is configured automatically when the VisiGate system starts. The following configuration options are available:

- **Check Interval**: How often to check camera health (default: 60 seconds)
- **Maximum Reconnection Attempts**: Maximum number of times to attempt reconnection (default: 5)
- **Reconnection Backoff**: Time between reconnection attempts (default: 30s, 60s, 2m, 5m, 10m)

These options can be configured in the system settings.

## Troubleshooting

If you're experiencing issues with camera health monitoring, check the following:

1. **Camera Network Connectivity**: Ensure the camera is accessible on the network
2. **Camera Credentials**: Verify that the username and password for the camera are correct
3. **Camera Resources**: Check if the camera has enough resources to handle the requested stream
4. **System Logs**: Check the VisiGate logs for error messages related to camera connections

## API Endpoints

The camera health monitoring system provides the following API endpoints:

- `GET /api/cameras/health`: Get the health status of all cameras
- `GET /api/cameras/health/{camera_id}`: Get the health status of a specific camera
- `POST /api/cameras/restart/{camera_id}`: Restart a specific camera

These endpoints can be used to integrate the camera health monitoring system with other systems.
