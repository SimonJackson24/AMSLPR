# Configuration Parameter Reference

This document provides a comprehensive reference for all AMSLPR configuration parameters, including descriptions, valid values, and examples.

## Configuration Files

AMSLPR uses multiple configuration files:

- `config/config.json` - Main application configuration
- `config/ocr_config.json` - OCR-specific configuration
- `config/camera_config.json` - Camera configuration
- `config/users.json` - User management configuration

## Main Configuration (config.json)

### Database Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `database.path` | string | `"data/amslpr.db"` | Path to SQLite database file |

**Example:**
```json
{
  "database": {
    "path": "/app/data/amslpr.db"
  }
}
```

### Recognition Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `recognition.confidence_threshold` | number | `0.7` | Minimum confidence score for license plate detection (0.0-1.0) |
| `recognition.save_images` | boolean | `true` | Whether to save captured images to disk |
| `recognition.image_save_path` | string | `"data/images"` | Directory path for saving images |
| `recognition.ocr_config_path` | string | `"config/ocr_config.json"` | Path to OCR configuration file |

**Example:**
```json
{
  "recognition": {
    "confidence_threshold": 0.8,
    "save_images": true,
    "image_save_path": "/app/data/images",
    "ocr_config_path": "/app/config/ocr_config.json"
  }
}
```

### Barrier Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `barrier.enabled` | boolean | `true` | Enable/disable barrier control |
| `barrier.gpio_pin` | integer | `18` | GPIO pin number for barrier control |
| `barrier.open_time` | integer | `5` | Time in seconds to keep barrier open |

**Example:**
```json
{
  "barrier": {
    "enabled": true,
    "gpio_pin": 18,
    "open_time": 5
  }
}
```

### Web Server Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `web.host` | string | `"0.0.0.0"` | Host address to bind the web server |
| `web.port` | integer | `5050` | Port number for the web server |
| `web.debug` | boolean | `true` | Enable/disable debug mode |
| `web.secret_key` | string | `"your-secret-key-here"` | Secret key for session management |
| `web.csrf_secret_key` | string | `"your-csrf-secret-key-here"` | Secret key for CSRF protection |

**SSL Configuration:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `web.ssl.enabled` | boolean | `false` | Enable/disable SSL/TLS |
| `web.ssl.certificate` | string | `"config/ssl/cert.pem"` | Path to SSL certificate file |
| `web.ssl.key` | string | `"config/ssl/key.pem"` | Path to SSL private key file |

**Example:**
```json
{
  "web": {
    "host": "0.0.0.0",
    "port": 5001,
    "debug": false,
    "secret_key": "your-secure-secret-key-here",
    "csrf_secret_key": "your-csrf-secret-key-here",
    "ssl": {
      "enabled": true,
      "certificate": "/app/ssl/cert.pem",
      "key": "/app/ssl/key.pem"
    }
  }
}
```

### Notifications Configuration

#### Email Notifications

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `notifications.email.enabled` | boolean | `true` | Enable/disable email notifications |
| `notifications.email.smtp_server` | string | `"smtp.example.com"` | SMTP server hostname |
| `notifications.email.smtp_port` | integer | `587` | SMTP server port |
| `notifications.email.username` | string | `"user@example.com"` | SMTP authentication username |
| `notifications.email.password` | string | `"your-password"` | SMTP authentication password |
| `notifications.email.from_address` | string | `"amslpr@example.com"` | Email sender address |
| `notifications.email.to_addresses` | array | `["admin@example.com"]` | List of recipient email addresses |

#### SMS Notifications

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `notifications.sms.enabled` | boolean | `false` | Enable/disable SMS notifications |
| `notifications.sms.provider` | string | `"twilio"` | SMS provider (twilio, aws-sns, etc.) |
| `notifications.sms.account_sid` | string | `"your-account-sid"` | Twilio account SID |
| `notifications.sms.auth_token` | string | `"your-auth-token"` | Twilio authentication token |
| `notifications.sms.from_number` | string | `"+1234567890"` | Twilio phone number |
| `notifications.sms.to_numbers` | array | `["+1987654321"]` | List of recipient phone numbers |

#### Webhook Notifications

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `notifications.webhook.enabled` | boolean | `false` | Enable/disable webhook notifications |
| `notifications.webhook.url` | string | `"https://example.com/webhook"` | Webhook endpoint URL |
| `notifications.webhook.headers` | object | `{}` | HTTP headers for webhook requests |

**Example:**
```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "amslpr@example.com",
      "password": "your-app-password",
      "from_address": "amslpr@example.com",
      "to_addresses": ["admin@example.com", "security@example.com"]
    },
    "sms": {
      "enabled": false,
      "provider": "twilio",
      "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "auth_token": "your_auth_token_here",
      "from_number": "+1234567890",
      "to_numbers": ["+1987654321"]
    },
    "webhook": {
      "enabled": true,
      "url": "https://api.example.com/webhooks/amslpr",
      "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer your-webhook-token",
        "X-API-Key": "your-api-key"
      }
    }
  }
}
```

### Camera Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `camera.discovery_enabled` | boolean | `true` | Enable automatic camera discovery |
| `camera.discovery_interval` | integer | `60` | Camera discovery interval in seconds |
| `camera.default_username` | string | `"admin"` | Default username for camera access |
| `camera.default_password` | string | `"admin"` | Default password for camera access |

#### Camera Array Configuration

Each camera in the `camera.cameras` array has the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for the camera |
| `name` | string | Yes | Human-readable name for the camera |
| `location` | string | No | Physical location of the camera |
| `ip` | string | Yes | IP address of the camera |
| `port` | integer | Yes | Port number for camera access |
| `username` | string | Yes | Username for camera authentication |
| `password` | string | Yes | Password for camera authentication |
| `rtsp_url` | string | No | RTSP stream URL for the camera |
| `enabled` | boolean | No | Whether the camera is enabled (default: true) |
| `detection_area` | object | No | Detection area coordinates |

**Example:**
```json
{
  "camera": {
    "discovery_enabled": true,
    "discovery_interval": 60,
    "default_username": "admin",
    "default_password": "password123",
    "cameras": [
      {
        "id": "entrance_main",
        "name": "Main Entrance Camera",
        "location": "Front Gate",
        "ip": "192.168.1.100",
        "port": 80,
        "username": "admin",
        "password": "secure_password",
        "rtsp_url": "rtsp://192.168.1.100:554/stream1",
        "enabled": true,
        "detection_area": {
          "x": 100,
          "y": 50,
          "width": 400,
          "height": 200
        }
      },
      {
        "id": "exit_main",
        "name": "Main Exit Camera",
        "location": "Exit Gate",
        "ip": "192.168.1.101",
        "port": 80,
        "username": "admin",
        "password": "secure_password",
        "rtsp_url": "rtsp://192.168.1.101:554/stream1",
        "enabled": true
      }
    ]
  }
}
```

## OCR Configuration (ocr_config.json)

### General OCR Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `confidence_threshold` | number | `0.7` | Minimum confidence score for OCR results (0.0-1.0) |
| `ocr_method` | string | `"hybrid"` | OCR method: "tesseract", "deep_learning", or "hybrid" |
| `use_hailo_tpu` | boolean | `true` | Enable Hailo TPU acceleration |

**Example:**
```json
{
  "confidence_threshold": 0.8,
  "ocr_method": "hybrid",
  "use_hailo_tpu": true
}
```

### Tesseract Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tesseract_config.psm_mode` | integer | `7` | Page segmentation mode (0-13) |
| `tesseract_config.oem_mode` | integer | `1` | OCR Engine mode (0-3) |
| `tesseract_config.whitelist` | string | `"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"` | Character whitelist |

**PSM Modes:**
- `0`: Orientation and script detection (OSD) only
- `1`: Automatic page segmentation with OSD
- `2`: Automatic page segmentation, but no OSD, or OCR
- `3`: Fully automatic page segmentation, but no OSD
- `4`: Assume a single column of text of variable sizes
- `5`: Assume a single uniform block of vertically aligned text
- `6`: Assume a single uniform block of text
- `7`: Treat the image as a single text line
- `8`: Treat the image as a single word
- `9`: Treat the image as a single word in a circle
- `10`: Treat the image as a single character
- `11`: Sparse text. Find as much text as possible in no particular order
- `12`: Sparse text with OSD
- `13`: Raw line. Treat the image as a single text line, bypassing hacks that are Tesseract-specific

**OEM Modes:**
- `0`: Legacy engine only
- `1`: Neural nets LSTM engine only
- `2`: Tesseract + LSTM
- `3`: Default, based on what is available

### Deep Learning Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deep_learning.model_type` | string | `"crnn"` | Deep learning model type |
| `deep_learning.input_width` | integer | `100` | Input image width for model |
| `deep_learning.input_height` | integer | `32` | Input image height for model |
| `deep_learning.tf_ocr_model_path` | string | `"models/ocr_crnn.h5"` | Path to TensorFlow OCR model |
| `deep_learning.hailo_ocr_model_path` | string | `"models/lprnet_vehicle_license_recognition.hef"` | Path to Hailo OCR model |
| `deep_learning.char_map_path` | string | `"models/char_map.json"` | Path to character mapping file |
| `deep_learning.hailo_detector_model_path` | string | `"models/yolov5m_license_plates.hef"` | Path to Hailo detector model |
| `deep_learning.use_hailo_detector` | boolean | `true` | Use Hailo for license plate detection |

### Preprocessing Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `preprocessing.resize_factor` | number | `2.0` | Image resize factor |
| `preprocessing.apply_contrast_enhancement` | boolean | `true` | Apply contrast enhancement |
| `preprocessing.apply_noise_reduction` | boolean | `true` | Apply noise reduction |
| `preprocessing.apply_perspective_correction` | boolean | `true` | Apply perspective correction |

### Postprocessing Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `postprocessing.apply_regex_validation` | boolean | `true` | Apply regex validation to results |
| `postprocessing.min_plate_length` | integer | `4` | Minimum license plate length |
| `postprocessing.max_plate_length` | integer | `10` | Maximum license plate length |
| `postprocessing.common_substitutions` | object | `{}` | Character substitution mapping |

### Regional Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `regional_settings.country_code` | string | `"US"` | Country code for license plate format |
| `regional_settings.plate_format` | string | `"[A-Z0-9]{3,8}"` | Regular expression for plate format |

**Example OCR Configuration:**
```json
{
  "confidence_threshold": 0.8,
  "ocr_method": "hybrid",
  "use_hailo_tpu": true,
  "tesseract_config": {
    "psm_mode": 7,
    "oem_mode": 1,
    "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
  },
  "deep_learning": {
    "model_type": "crnn",
    "input_width": 100,
    "input_height": 32,
    "tf_ocr_model_path": "/app/models/ocr_crnn.h5",
    "hailo_ocr_model_path": "/app/models/lprnet_vehicle_license_recognition.hef",
    "char_map_path": "/app/models/char_map.json",
    "hailo_detector_model_path": "/app/models/yolov5m_license_plates.hef",
    "use_hailo_detector": true
  },
  "preprocessing": {
    "resize_factor": 2.0,
    "apply_contrast_enhancement": true,
    "apply_noise_reduction": true,
    "apply_perspective_correction": true
  },
  "postprocessing": {
    "apply_regex_validation": true,
    "min_plate_length": 4,
    "max_plate_length": 10,
    "common_substitutions": {
      "0": "O",
      "1": "I",
      "5": "S",
      "8": "B"
    }
  },
  "regional_settings": {
    "country_code": "US",
    "plate_format": "[A-Z0-9]{3,8}"
  }
}
```

## Environment Variables

AMSLPR also supports configuration via environment variables:

| Environment Variable | Configuration Path | Description |
|---------------------|-------------------|-------------|
| `PORT` | `web.port` | Web server port |
| `DEBUG` | `web.debug` | Enable debug mode |
| `SECRET_KEY` | `web.secret_key` | Flask secret key |
| `DATABASE_URL` | `database.url` | Database connection URL |
| `REDIS_URL` | `cache.redis_url` | Redis connection URL |
| `HAILO_ENABLED` | `recognition.use_hailo_tpu` | Enable Hailo TPU |
| `TZ` | System timezone | System timezone |

## Configuration Validation

AMSLPR validates configuration files at startup. Common validation rules:

- **Port numbers**: Must be between 1-65535
- **Confidence thresholds**: Must be between 0.0-1.0
- **File paths**: Must be accessible and writable where required
- **IP addresses**: Must be valid IPv4 or IPv6 addresses
- **Email addresses**: Must be valid email format
- **URLs**: Must be valid HTTP/HTTPS URLs

## Configuration Management

### Configuration File Locations

- **Linux/macOS**: `/etc/amslpr/`, `~/.config/amslpr/`, `./config/`
- **Windows**: `%APPDATA%\amslpr\`, `./config/`
- **Docker**: `/app/config/`

### Configuration Reloading

Some configuration changes require application restart:

- **Requires restart**: Database path, web server settings, SSL configuration
- **Hot reload**: OCR settings, notification settings, camera settings

### Backup and Restore

Always backup configuration files before making changes:

```bash
# Backup configuration
cp config/config.json config/config.json.backup
cp config/ocr_config.json config/ocr_config.json.backup

# Restore configuration
cp config/config.json.backup config/config.json
cp config/ocr_config.json.backup config/ocr_config.json
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

1. **Invalid JSON syntax**: Use a JSON validator
2. **File permission issues**: Ensure proper read/write permissions
3. **Path not found**: Use absolute paths or verify relative paths
4. **Invalid values**: Check parameter ranges and formats
5. **Missing required fields**: Review documentation for required parameters

### Configuration Debugging

Enable debug logging to troubleshoot configuration issues:

```json
{
  "web": {
    "debug": true
  }
}
```

Check application logs for configuration-related errors:

```bash
tail -f logs/amslpr.log | grep -i config
```

## Best Practices

1. **Use environment-specific configurations** for different deployment environments
2. **Store sensitive data** (passwords, keys) in environment variables or secrets management
3. **Validate configurations** before deploying to production
4. **Document configuration changes** and their impact
5. **Use version control** for configuration files
6. **Test configuration changes** in staging environment first
7. **Monitor configuration drift** between environments
8. **Implement configuration backups** and recovery procedures

## Support

For additional support with configuration:

- Check the [troubleshooting guide](../troubleshooting/configuration_issues.md)
- Review the [deployment guides](../deployment/)
- Contact support at support@automatesystems.com