# VisiGate API Documentation

This document describes the API endpoints provided by the VisiGate system for integration with other systems.

## Base URL

All API endpoints are relative to the base URL of your VisiGate installation:

```
https://<raspberry-pi-ip>/api
```

Replace `<raspberry-pi-ip>` with the IP address or hostname of your Raspberry Pi.

## Authentication

The API uses token-based authentication. To access protected endpoints, you must include an `Authorization` header with a valid token:

```
Authorization: Bearer <your-token>
```

To obtain a token, use the authentication endpoint described below.

## Rate Limiting

The API implements rate limiting to prevent abuse. By default, clients are limited to 100 requests per minute. If you exceed this limit, you will receive a 429 Too Many Requests response.

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1583850767
```

## Endpoints

### Authentication

#### POST /api/auth/token

Obtain an authentication token.

**Request:**

```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires": "2023-03-15T12:00:00Z"
}
```

### System Status

#### GET /api/system/status

Get current system status information.

**Response:**

```json
{
  "status": "ok",
  "version": "1.2.0",
  "uptime": 86400,
  "resources": {
    "cpu_percent": 12.5,
    "memory_percent": 45.2,
    "disk_percent": 32.1,
    "cpu_temp": 42.3
  },
  "camera_status": "active",
  "barrier_status": "ready"
}
```

### Vehicles

#### Get All Vehicles

```
GET /api/vehicles
```

**Query Parameters:**

- `authorized` (optional): Filter vehicles by authorization status (`true` or `false`)

**Response:**

```json
[
  {
    "plate_number": "ABC123",
    "description": "John's Car",
    "authorized": true,
    "valid_from": "2025-01-01T00:00:00",
    "valid_until": null,
    "created_at": "2025-03-01T12:34:56",
    "updated_at": "2025-03-01T12:34:56"
  },
  {
    "plate_number": "XYZ789",
    "description": "Visitor",
    "authorized": false,
    "valid_from": null,
    "valid_until": null,
    "created_at": "2025-03-02T09:12:34",
    "updated_at": "2025-03-02T09:12:34"
  }
]
```

#### Get Vehicle by Plate Number

```
GET /api/vehicles/<plate_number>
```

**Response:**

```json
{
  "plate_number": "ABC123",
  "description": "John's Car",
  "authorized": true,
  "valid_from": "2025-01-01T00:00:00",
  "valid_until": null,
  "created_at": "2025-03-01T12:34:56",
  "updated_at": "2025-03-01T12:34:56"
}
```

**Error Response (404):**

```json
{
  "error": "Vehicle not found"
}
```

### Access Logs

#### Get Access Logs

```
GET /api/logs
```

**Query Parameters:**

- `plate_number` (optional): Filter logs by plate number

**Response:**

```json
[
  {
    "id": 1,
    "plate_number": "ABC123",
    "direction": "entry",
    "authorized": true,
    "access_time": "2025-03-01T08:15:30",
    "image_path": "/data/images/2025-03-01/081530_ABC123_entry.jpg"
  },
  {
    "id": 2,
    "plate_number": "ABC123",
    "direction": "exit",
    "authorized": true,
    "access_time": "2025-03-01T17:45:12",
    "image_path": "/data/images/2025-03-01/174512_ABC123_exit.jpg"
  }
]
```

### Statistics

#### Get All Statistics

```
GET /api/statistics
```

**Response:**

```json
{
  "daily_traffic": {
    "dates": ["2025-03-08", "2025-03-09", "2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13", "2025-03-14"],
    "entry": [37, 37, 37, 25, 35, 19, 5],
    "exit": [35, 33, 39, 24, 36, 19, 8],
    "total": [72, 70, 76, 49, 71, 38, 13]
  },
  "hourly_distribution": {
    "hours": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    "entry": [5, 7, 7, 6, 7, 5, 17, 27, 19, 27, 33, 37, 34, 32, 31, 32, 28, 16, 22, 15, 14, 8, 10, 3],
    "exit": [22, 15, 11, 13, 11, 8, 9, 13, 8, 19, 8, 17, 18, 24, 24, 24, 31, 27, 25, 38, 14, 24, 25, 15],
    "total": [27, 22, 18, 19, 18, 13, 26, 40, 27, 46, 41, 54, 52, 56, 55, 56, 59, 43, 47, 53, 28, 32, 35, 18]
  },
  "vehicle_stats": {
    "total_vehicles": 10,
    "authorized_vehicles": 7,
    "unauthorized_vehicles": 3,
    "most_frequent_vehicles": {
      "DEF456": 17,
      "YZA567": 15,
      "VWX234": 11,
      "MNO345": 10,
      "XYZ789": 10
    },
    "avg_accesses_per_vehicle": 10.0,
    "authorized_access_percentage": 77.0
  },
  "parking_stats": {
    "avg_duration_minutes": 278.08,
    "max_duration_minutes": 1835.12,
    "min_duration_minutes": 0.93,
    "duration_distribution": {
      "<15m": 3,
      "15-30m": 14,
      "30-60m": 20,
      "1-2h": 37,
      "2-4h": 77,
      "4-8h": 94,
      "8-24h": 21,
      ">24h": 4
    }
  }
}
```

#### Get Daily Traffic Statistics

```
GET /api/statistics/daily_traffic
```

**Query Parameters:**

- `days` (optional): Number of days to include in the statistics (default: 7)

**Response:**

```json
{
  "dates": ["2025-03-08", "2025-03-09", "2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13", "2025-03-14"],
  "entry": [37, 37, 37, 25, 35, 19, 5],
  "exit": [35, 33, 39, 24, 36, 19, 8],
  "total": [72, 70, 76, 49, 71, 38, 13]
}
```

#### Get Hourly Distribution Statistics

```
GET /api/statistics/hourly_distribution
```

**Query Parameters:**

- `days` (optional): Number of days to include in the statistics (default: 30)

**Response:**

```json
{
  "hours": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
  "entry": [5, 7, 7, 6, 7, 5, 17, 27, 19, 27, 33, 37, 34, 32, 31, 32, 28, 16, 22, 15, 14, 8, 10, 3],
  "exit": [22, 15, 11, 13, 11, 8, 9, 13, 8, 19, 8, 17, 18, 24, 24, 24, 31, 27, 25, 38, 14, 24, 25, 15],
  "total": [27, 22, 18, 19, 18, 13, 26, 40, 27, 46, 41, 54, 52, 56, 55, 56, 59, 43, 47, 53, 28, 32, 35, 18]
}
```

#### Get Vehicle Statistics

```
GET /api/statistics/vehicle_stats
```

**Response:**

```json
{
  "total_vehicles": 10,
  "authorized_vehicles": 7,
  "unauthorized_vehicles": 3,
  "most_frequent_vehicles": {
    "DEF456": 17,
    "YZA567": 15,
    "VWX234": 11,
    "MNO345": 10,
    "XYZ789": 10
  },
  "avg_accesses_per_vehicle": 10.0,
  "authorized_access_percentage": 77.0
}
```

#### Get Parking Duration Statistics

```
GET /api/statistics/parking_stats
```

**Response:**

```json
{
  "avg_duration_minutes": 278.08,
  "max_duration_minutes": 1835.12,
  "min_duration_minutes": 0.93,
  "duration_distribution": {
    "<15m": 3,
    "15-30m": 14,
    "30-60m": 20,
    "1-2h": 37,
    "2-4h": 77,
    "4-8h": 94,
    "8-24h": 21,
    ">24h": 4
  }
}
```

### OCR API

### OCR Configuration

#### Get OCR Configuration

```
GET /ocr/api/config
```

**Response:**

```json
{
  "ocr_method": "tesseract",
  "use_hailo_tpu": false,
  "tesseract_config": {
    "psm_mode": 7,
    "oem_mode": 1,
    "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
  },
  "deep_learning": {
    "model_type": "crnn",
    "input_width": 100,
    "input_height": 32
  },
  "preprocessing": {
    "resize_factor": 2.0,
    "apply_contrast_enhancement": true,
    "contrast_clip_limit": 2.0,
    "apply_noise_reduction": true,
    "noise_reduction_strength": 7,
    "apply_threshold": true,
    "threshold_method": "adaptive",
    "threshold_block_size": 11,
    "threshold_c": 2
  },
  "postprocessing": {
    "apply_regex_filter": true,
    "regex_pattern": "^[A-Z0-9]{3,8}$",
    "confidence_threshold": 0.7,
    "min_characters": 3,
    "max_characters": 8
  }
}
```

#### Update OCR Configuration

```
POST /ocr/api/config
```

**Request Body:**

Same format as the response from GET /ocr/api/config

**Response:**

```json
{
  "success": true,
  "message": "OCR configuration updated successfully"
}
```

**Error Response:**

```json
{
  "success": false,
  "message": "Error updating OCR configuration: Invalid configuration format"
}
```

#### Reload OCR Configuration

```
POST /ocr/api/reload
```

**Response:**

```json
{
  "success": true,
  "message": "OCR configuration reloaded successfully"
}
```

**Error Response:**

```json
{
  "success": false,
  "message": "Error reloading OCR configuration"
}
```

### Notification API

### Test Notification

```
POST /api/test_notification
```

Sends a test notification using the specified notification channel.

**Request Body:**

```json
{
  "type": "email",  // Can be "email", "sms", or "webhook"
  "plate_number": "TEST123"  // Optional, defaults to "TEST123"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Test email sent successfully"
}
```

or in case of error:

```json
{
  "success": false,
  "error": "Failed to send test email. Check server logs for details."
}
```

## Integration Examples

### Python Example

```python
import requests
import json

# Base URL of the VisiGate API
base_url = "https://192.168.1.100/api"

# Get all authorized vehicles
response = requests.get(f"{base_url}/vehicles", params={"authorized": "true"}, headers={"Authorization": "Bearer your-token"})
authorized_vehicles = response.json()
print(f"Authorized vehicles: {len(authorized_vehicles)}")

# Get access logs for a specific vehicle
plate_number = "ABC123"
response = requests.get(f"{base_url}/logs", params={"plate_number": plate_number}, headers={"Authorization": "Bearer your-token"})
access_logs = response.json()
print(f"Access logs for {plate_number}: {len(access_logs)}")

# Get system statistics
response = requests.get(f"{base_url}/statistics", headers={"Authorization": "Bearer your-token"})
stats = response.json()
print(f"Average parking duration: {stats['parking_stats']['avg_duration_minutes']} minutes")
print(f"Total vehicles in system: {stats['vehicle_stats']['total_vehicles']}")
```

### JavaScript Example

```javascript
// Base URL of the VisiGate API
const baseUrl = 'https://192.168.1.100/api';

// Get all authorized vehicles
async function getAuthorizedVehicles() {
  try {
    const response = await fetch(`${baseUrl}/vehicles?authorized=true`, {
      headers: {
        'Authorization': 'Bearer your-token'
      }
    });
    const vehicles = await response.json();
    console.log(`Authorized vehicles: ${vehicles.length}`);
    return vehicles;
  } catch (error) {
    console.error('Error fetching authorized vehicles:', error);
  }
}

// Get access logs for a specific vehicle
async function getVehicleAccessLogs(plateNumber) {
  try {
    const response = await fetch(`${baseUrl}/logs?plate_number=${plateNumber}`, {
      headers: {
        'Authorization': 'Bearer your-token'
      }
    });
    const logs = await response.json();
    console.log(`Access logs for ${plateNumber}: ${logs.length}`);
    return logs;
  } catch (error) {
    console.error(`Error fetching access logs for ${plateNumber}:`, error);
  }
}

// Get system statistics
async function getSystemStatistics() {
  try {
    const response = await fetch(`${baseUrl}/statistics`, {
      headers: {
        'Authorization': 'Bearer your-token'
      }
    });
    const stats = await response.json();
    console.log(`Average parking duration: ${stats.parking_stats.avg_duration_minutes} minutes`);
    console.log(`Total vehicles in system: ${stats.vehicle_stats.total_vehicles}`);
    return stats;
  } catch (error) {
    console.error('Error fetching system statistics:', error);
  }
}

// Usage
getAuthorizedVehicles();
getVehicleAccessLogs('ABC123');
getSystemStatistics();
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: The request was successful
- `404 Not Found`: The requested resource was not found
- `500 Internal Server Error`: An error occurred on the server

Error responses include a JSON object with an `error` field containing a description of the error.
