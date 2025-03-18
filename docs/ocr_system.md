# OCR System Documentation

## Overview

The AMSLPR system uses an advanced OCR (Optical Character Recognition) system for license plate recognition. The system supports multiple OCR methods and can be configured to use hardware acceleration via the Hailo TPU for improved performance and reliability.

## OCR Methods

The system supports three OCR methods:

1. **Tesseract OCR**: Uses the open-source Tesseract OCR engine for license plate recognition. This is the default method and works well for clear, well-lit license plates.

2. **Deep Learning OCR**: Uses a deep learning model for license plate recognition. This method can be hardware-accelerated using the Hailo TPU and is more robust to variations in lighting, angle, and image quality.

3. **Hybrid**: Combines both Tesseract and deep learning methods for maximum reliability. The system uses heuristics to select the most reliable result or combines results from both methods.

## Hardware Acceleration

The system can use the Hailo TPU for hardware acceleration of the deep learning OCR method. The Hailo TPU provides significant performance improvements over CPU-based inference, allowing for faster and more reliable license plate recognition.

## Configuration

The OCR system is highly configurable through the following:

1. **OCR Configuration File**: Located at `config/ocr_config.json`, this file contains all OCR-related configuration options.

2. **Admin Dashboard**: OCR settings can be configured through the admin dashboard under **OCR Settings** in the main navigation menu. This provides a user-friendly interface to adjust all OCR parameters without directly editing configuration files.

### Configuration Reloading

The OCR system supports dynamic configuration reloading, allowing changes to be applied without restarting the application. This can be done in two ways:

1. **Through the Admin Dashboard**: After saving changes to the OCR configuration, the system automatically reloads the configuration for all active detectors.

2. **Using the Reload Button**: The OCR Settings page includes a "Reload Configuration" button that forces all active detectors to reload the configuration from disk. This is useful when the configuration file has been modified externally.

3. **Via API**: The system provides an API endpoint at `/ocr/api/reload` for programmatically reloading the OCR configuration.

### Configuration Options

#### OCR Method

- `ocr_method`: The OCR method to use. Can be `tesseract`, `deep_learning`, or `hybrid`.
- `use_hailo_tpu`: Whether to use the Hailo TPU for hardware acceleration. Only applicable for `deep_learning` and `hybrid` methods.

#### Tesseract Configuration

- `psm_mode`: Page segmentation mode for Tesseract. Default is `7` (treat image as a single line of text).
- `oem_mode`: OCR engine mode for Tesseract. Default is `1` (neural nets LSTM engine only).
- `whitelist`: Characters to recognize. Default is alphanumeric characters.

#### Deep Learning Configuration

- `model_type`: Type of deep learning model to use. Default is `crnn` (Convolutional Recurrent Neural Network).
- `input_width`: Width of input image for the model. Default is `100`.
- `input_height`: Height of input image for the model. Default is `32`.

#### Preprocessing Configuration

- `resize_factor`: Factor to resize the license plate image by before OCR. Default is `2.0`.
- `apply_contrast_enhancement`: Whether to apply contrast enhancement. Default is `true`.
- `apply_noise_reduction`: Whether to apply noise reduction. Default is `true`.
- `apply_perspective_correction`: Whether to apply perspective correction. Default is `false`.

#### Postprocessing Configuration

- `apply_regex_validation`: Whether to apply regex validation to the recognized text. Default is `true`.
- `min_plate_length`: Minimum length for a valid license plate. Default is `4`.
- `max_plate_length`: Maximum length for a valid license plate. Default is `10`.
- `common_substitutions`: Common OCR errors to correct. Default includes `0->O`, `1->I`, etc.

#### Regional Settings

- `country_code`: Country code for region-specific formatting. Default is `US`.
- `plate_format`: Regex pattern for license plate format validation. Default is `[A-Z0-9]{3,8}`.

## Setup and Testing

The OCR system includes a setup and testing script to help administrators set up and test the OCR system, including the Hailo TPU integration.

### Setup Script

The setup script is located at `scripts/setup_ocr.py` and can be run with the following command:

```bash
./scripts/setup_ocr.py
```

This script performs the following tasks:
1. Checks for required dependencies
2. Verifies the OCR configuration
3. Tests the OCR system with sample images
4. Provides guidance for optimizing the OCR configuration

You can skip specific steps by using the following options:

```bash
./scripts/setup_ocr.py --skip-deps    # Skip dependency checking
./scripts/setup_ocr.py --skip-config  # Skip configuration verification
./scripts/setup_ocr.py --skip-models  # Skip model checking
./scripts/setup_ocr.py --skip-test    # Skip OCR testing
```

### Model Preparation

The OCR system requires pre-trained models for deep learning OCR. These models can be prepared using the `scripts/prepare_ocr_models.py` script:

```bash
./scripts/prepare_ocr_models.py
```

This script downloads and prepares the required models for both CPU and Hailo TPU usage.

## Performance Tuning

### Improving Recognition Accuracy

1. **Camera Positioning**: Ensure the camera is positioned correctly to capture clear images of license plates.
2. **Lighting**: Ensure adequate lighting, especially at night. Consider using infrared illumination.
3. **Image Preprocessing**: Adjust preprocessing parameters to improve image quality before OCR.
4. **OCR Method**: Use the `hybrid` method for maximum reliability, especially in challenging conditions.

### Improving Performance

1. **Hardware Acceleration**: Use the Hailo TPU for hardware acceleration of deep learning OCR.
2. **Preprocessing Optimization**: Disable unnecessary preprocessing steps to reduce processing time.
3. **Resolution**: Use an appropriate resolution that balances detail and processing time.

## Testing

The OCR system includes a test script to verify the functionality of the OCR system, including the configuration reloading feature.

### Test Script

The test script is located at `tests/test_ocr_reload.py` and can be run with the following command:

```bash
./tests/test_ocr_reload.py
```

This script tests the direct reloading of the OCR configuration by:
1. Loading the current OCR configuration
2. Making a change to the configuration
3. Saving the configuration
4. Triggering a reload
5. Verifying that the change was applied

### API Testing

The test script also supports testing the OCR configuration reloading via the API:

```bash
./tests/test_ocr_reload.py --api
```

This tests the API endpoints for updating and reloading the OCR configuration.

## Troubleshooting

### Common Issues

1. **Poor Recognition Accuracy**: Check camera positioning, lighting, and image quality. Adjust preprocessing parameters.
2. **Slow Recognition**: Check if hardware acceleration is enabled and working correctly. Reduce image resolution or disable unnecessary preprocessing steps.
3. **Hardware Acceleration Not Working**: Ensure the Hailo TPU is properly connected and the drivers are installed. Check the system logs for errors.

### Logging

The OCR system logs detailed information about the recognition process. Logs are stored in `data/logs/amslpr.log` and can be viewed through the admin dashboard under System > Logs.

## Model Management

The OCR system uses pre-trained models for deep learning OCR. These models are stored in the `models` directory and can be managed using the `scripts/prepare_ocr_models.py` script.

### Preparing Models

To prepare the OCR models, run the following command:

```bash
python scripts/prepare_ocr_models.py --all
```

This will download or create the necessary models for both Tesseract and deep learning OCR.

### Custom Models

You can use custom models by placing them in the `models` directory and updating the OCR configuration file accordingly.

## API

The OCR system exposes the following API endpoints:

- `GET /ocr/settings`: Web interface for configuring OCR settings.
- `GET /ocr/test`: Web interface for testing OCR with custom images.
- `GET /ocr/api/config`: Get the current OCR configuration.
- `POST /ocr/api/config`: Update the OCR configuration.
- `POST /ocr/api/test`: Test the OCR system with a provided image.
- `POST /ocr/api/reload`: Reload the OCR configuration.

See the [API documentation](api.md) for more details.
