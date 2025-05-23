
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

"""License plate detection and recognition module."""
import cv2
import numpy as np
import os
import logging
import time
import pytesseract
from datetime import datetime
import json

# Add imports for deep learning OCR
import tensorflow as tf
try:
    # Import Hailo-specific libraries if available
    import hailo_platform
    try:
        # Optional: model zoo provides convenience utilities but is not strictly required
        import hailo_model_zoo
    except ImportError:
        # Log a warning but do not fail TPU availability if model zoo is missing
        logging.getLogger('AMSLPR.recognition').warning(
            "hailo_model_zoo not found – continuing without it. Ensure .hef models are provided via 'hailo_ocr_model_path'."
        )
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False

logger = logging.getLogger('AMSLPR.recognition')

class LicensePlateDetector:
    """
    License plate detection and recognition class.
    Uses OpenCV and Tesseract OCR to detect and recognize license plates.
    Can also use deep learning models with Hailo TPU acceleration.
    """
    
    def __init__(self, config, ocr_config=None):
        """
        Initialize the license plate detector.
        
        Args:
            config (dict): Configuration dictionary for recognition
            ocr_config (dict, optional): OCR-specific configuration
        """
        self.config = config
        self.camera_id = config.get('camera_id', 0)
        self.frame_width = config.get('frame_width', 640)
        self.frame_height = config.get('frame_height', 480)
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.save_images = config.get('save_images', True)
        self.image_save_path = config.get('image_save_path', 'data/images')
        self.use_onvif = config.get('use_onvif', True)
        self.mock_mode = config.get('mock_mode', False)
        
        # Initialize ONVIF camera manager
        try:
            from src.recognition.onvif_camera import init_camera_manager
            self.onvif_camera_manager = init_camera_manager(config)
            if not self.onvif_camera_manager:
                raise RuntimeError("Failed to initialize ONVIF camera manager")
        except Exception as e:
            logger.error(f"Failed to initialize ONVIF camera manager: {e}")
            self.mock_mode = True
        
        # Load OCR configuration
        if ocr_config is None:
            # Try to load from the path specified in the main config
            ocr_config_path = config.get('ocr_config_path')
            if ocr_config_path and os.path.exists(ocr_config_path):
                try:
                    with open(ocr_config_path, 'r') as f:
                        ocr_config = json.load(f)
                        logger.info(f"Loaded OCR configuration from {ocr_config_path}")
                except Exception as e:
                    logger.error(f"Failed to load OCR configuration from {ocr_config_path}: {e}")
                    ocr_config = {}
            else:
                ocr_config = {}
        
        # OCR configuration
        self.ocr_method = ocr_config.get('ocr_method', config.get('ocr_method', 'tesseract'))
        self.use_hailo_tpu = ocr_config.get('use_hailo_tpu', config.get('use_hailo_tpu', False)) and HAILO_AVAILABLE
        self.tesseract_config = ocr_config.get('tesseract_config', {})
        self.deep_learning_config = ocr_config.get('deep_learning', {})
        self.preprocessing_config = ocr_config.get('preprocessing', {})
        self.postprocessing_config = ocr_config.get('postprocessing', {})
        self.regional_settings = ocr_config.get('regional_settings', {})
        
        # Create image save directory if it doesn't exist
        if self.save_images and not os.path.exists(self.image_save_path):
            os.makedirs(self.image_save_path)
        
        # Initialize detector
        self._init_detector()
        
        # Initialize OCR models
        self._init_ocr_models()
        
        logger.info(f"License plate detector initialized with OCR method: {self.ocr_method}")
        if self.use_hailo_tpu:
            logger.info("Using Hailo TPU for acceleration")
        if self.mock_mode:
            logger.info("Running in mock mode - no camera available")

    def _init_ocr_models(self):
        """
        Initialize OCR models based on configuration.
        """
        if self.ocr_method == 'tesseract':
            # No initialization needed for Tesseract
            pass
        elif self.ocr_method in ['deep_learning', 'hybrid']:
            try:
                # Load deep learning OCR model
                if self.use_hailo_tpu:
                    self._init_hailo_ocr_model()
                else:
                    self._init_tensorflow_ocr_model()
            except Exception as e:
                logger.error(f"Failed to initialize deep learning OCR model: {e}")
                logger.warning("Falling back to Tesseract OCR")
                self.ocr_method = 'tesseract'
    
    def _init_hailo_ocr_model(self):
        """
        Initialize OCR model for Hailo TPU.
        """
        if not HAILO_AVAILABLE:
            raise ImportError("Hailo libraries not available")
        
        try:
            # Initialize Hailo device
            self.hailo_device = hailo_platform.HailoDevice()
            
            # Load CRNN or other OCR model from Hailo Model Zoo
            model_path = self.config.get('hailo_ocr_model_path', 'models/ocr_model.hef')
            self.ocr_model = self.hailo_device.load_model(model_path)
            
            # Load character mapping for decoding
            self.char_map = self._load_char_map()
            
            logger.info("Hailo TPU OCR model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Hailo OCR model: {e}")
            raise
    
    def _init_tensorflow_ocr_model(self):
        """
        Initialize TensorFlow OCR model as fallback.
        """
        try:
            # Load TensorFlow model
            model_path = self.config.get('tf_ocr_model_path', 'models/ocr_model.h5')
            self.ocr_model = tf.keras.models.load_model(model_path)
            
            # Load character mapping for decoding
            self.char_map = self._load_char_map()
            
            logger.info("TensorFlow OCR model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TensorFlow OCR model: {e}")
            raise
    
    def _load_char_map(self):
        """
        Load character mapping for OCR model.
        """
        char_map_path = self.config.get('char_map_path', 'models/char_map.json')
        if os.path.exists(char_map_path):
            import json
            with open(char_map_path, 'r') as f:
                return json.load(f)
        else:
            # Default character map for license plates
            return {i: c for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')}

    def _init_camera(self):
        """
        Initialize the camera.
        """
        try:
            if self.use_onvif:
                if hasattr(self, 'onvif_camera_manager') and self.onvif_camera_manager:
                    if not self.onvif_camera_manager.start_stream(self.camera_id):
                        logger.error(f"Failed to start stream for ONVIF camera {self.camera_id}")
                        raise RuntimeError(f"Failed to start stream for ONVIF camera {self.camera_id}")
                else:
                    logger.error("ONVIF camera manager not provided")
                    raise ValueError("ONVIF camera manager not provided")
            else:
                # Don't try to use a local camera, raise an error since we only support ONVIF cameras
                logger.error("Only ONVIF cameras are supported")
                raise ValueError("Only ONVIF cameras are supported")
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            raise
        
    def _init_detector(self):
        """
        Initialize the license plate detector.
        In a real implementation, this would load a trained model.
        For this example, we'll use a simple placeholder.
        """
        # In a real implementation, this would load a trained model
        # For example, a YOLO or SSD model trained for license plate detection
        logger.info("License plate detector model loaded")
    
    def process_frame(self):
        """
        Process a frame from the camera and detect license plates.
        
        Returns:
            str: Detected license plate text, or None if no plate detected
        """
        # Capture frame from camera
        if self.use_onvif:
            # Get frame from ONVIF camera manager
            frame, timestamp = self.onvif_camera_manager.get_frame(self.camera_id)
            if frame is None:
                logger.error("Failed to get frame from ONVIF camera")
                return None
        else:
            # Don't try to use a local camera, raise an error since we only support ONVIF cameras
            logger.error("Only ONVIF cameras are supported")
            raise ValueError("Only ONVIF cameras are supported")
        
        # Detect license plate
        plates = self.detect_license_plates(frame, self.config.get('camera_settings'))
        
        if not plates:
            return None
        
        # Recognize text on the plate
        plate_text = self._recognize_text(frame, plates[0])
        
        # Save image if enabled
        if self.save_images and plate_text:
            self._save_plate_image(frame, plates[0], plate_text)
        
        return plate_text
    
    def detect_license_plates(self, frame, camera_settings=None):
        """
        Detect license plates in a frame.
        
        Args:
            frame (numpy.ndarray): Frame to detect license plates in
            camera_settings (dict): Camera detection settings
        
        Returns:
            list: List of detected license plates with coordinates and confidence
        """
        if frame is None:
            return []
        
        # Default settings
        confidence_threshold = 0.7
        min_plate_size = 5  # percentage of frame size
        
        # Apply camera settings if provided
        if camera_settings:
            confidence_threshold = float(camera_settings.get('confidence_threshold', confidence_threshold))
            min_plate_size = float(camera_settings.get('min_plate_size', min_plate_size))
        
        # Convert minimum plate size from percentage to pixels
        frame_height, frame_width = frame.shape[:2]
        min_width = int(frame_width * min_plate_size / 100)
        min_height = int(frame_height * min_plate_size / 100)
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours
        license_plates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by size
            if w < min_width or h < min_height:
                continue
            
            # Filter by aspect ratio (license plates are typically rectangular)
            aspect_ratio = w / h
            if not (1.5 <= aspect_ratio <= 5.0):
                continue
            
            # Calculate confidence based on contour area and perimeter
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # Rectangularity: how rectangular the contour is (1.0 is perfect)
            rectangularity = (w * h) / area if area > 0 else 0
            
            # Calculate confidence score (simplified)
            confidence = min(1.0, (rectangularity * 0.8) + (min(aspect_ratio, 4.0) / 5.0 * 0.2))
            
            if confidence >= confidence_threshold:
                license_plates.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'confidence': confidence
                })
        
        return license_plates
    
    def _recognize_text(self, frame, plate):
        """
        Recognize text on the license plate.
        
        Args:
            frame (numpy.ndarray): Frame containing the license plate
            plate (dict): License plate coordinates and confidence
        
        Returns:
            str: Recognized text, or None if no text recognized
        """
        try:
            # Extract the license plate from the frame
            x, y, w, h = plate['x'], plate['y'], plate['width'], plate['height']
            plate_img = frame[y:y+h, x:x+w]
            
            # Preprocess the image for OCR
            from src.utils.helpers import enhance_plate_image
            enhanced_img = enhance_plate_image(plate_img, self.preprocessing_config)
            
            # Use the selected OCR method
            if self.ocr_method == 'tesseract':
                # Use Tesseract OCR with configured parameters
                psm_mode = self.tesseract_config.get('psm_mode', 7)
                oem_mode = self.tesseract_config.get('oem_mode', 1)
                whitelist = self.tesseract_config.get('whitelist', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                
                config_str = f'--psm {psm_mode} --oem {oem_mode} -c tessedit_char_whitelist={whitelist}'
                text = pytesseract.image_to_string(enhanced_img, config=config_str)
                text = self._clean_plate_text(text)
                
            elif self.ocr_method == 'deep_learning':
                # Use deep learning OCR
                text = self._deep_learning_ocr(enhanced_img)
                text = self._clean_plate_text(text)
                
            elif self.ocr_method == 'hybrid':
                # Use both methods and select the most reliable result
                # Tesseract OCR
                psm_mode = self.tesseract_config.get('psm_mode', 7)
                oem_mode = self.tesseract_config.get('oem_mode', 1)
                whitelist = self.tesseract_config.get('whitelist', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                
                config_str = f'--psm {psm_mode} --oem {oem_mode} -c tessedit_char_whitelist={whitelist}'
                tesseract_text = pytesseract.image_to_string(enhanced_img, config=config_str)
                tesseract_text = self._clean_plate_text(tesseract_text)
                
                # Deep learning OCR
                dl_text = self._deep_learning_ocr(enhanced_img)
                dl_text = self._clean_plate_text(dl_text)
                
                # Use confidence scores or heuristics to select the best result
                text = self._select_best_text(tesseract_text, dl_text, enhanced_img)
            
            # Apply post-processing
            if text:
                # Apply minimum length check
                min_length = self.postprocessing_config.get('min_plate_length', 4)
                max_length = self.postprocessing_config.get('max_plate_length', 10)
                
                if len(text) < min_length or len(text) > max_length:
                    logger.debug(f"Rejected plate text '{text}' due to length constraints ({min_length}-{max_length})")
                    return None
                
                # Apply regex validation if configured
                if self.postprocessing_config.get('apply_regex_validation', False) and self.regional_settings.get('plate_format'):
                    import re
                    pattern = self.regional_settings.get('plate_format')
                    if not re.match(pattern, text):
                        logger.debug(f"Rejected plate text '{text}' due to format validation")
                        return None
                
                return text
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error recognizing text: {e}")
            return None
            
    def _clean_plate_text(self, text):
        """
        Clean and normalize license plate text.
        
        Args:
            text (str): Raw recognized text
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
            
        # Remove whitespace
        text = text.strip()
        
        # Remove common OCR errors and unwanted characters
        text = ''.join(c for c in text if c.isalnum()).upper()
        
        # Apply common substitutions for OCR errors
        substitutions = {
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B'
        }
        
        # Apply region-specific formatting rules if configured
        if hasattr(self, 'plate_format_rules') and self.plate_format_rules:
            # Apply format validation and correction based on regional rules
            pass
            
        return text
        
    def _select_best_text(self, tesseract_text, dl_text, image):
        """
        Select the most reliable text from multiple OCR methods.
        
        Args:
            tesseract_text (str): Text recognized by Tesseract
            dl_text (str): Text recognized by deep learning
            image (numpy.ndarray): Preprocessed license plate image
            
        Returns:
            str: The most reliable text
        """
        # If texts match exactly, return that (high confidence)
        if tesseract_text == dl_text and tesseract_text:
            return tesseract_text
            
        # If one is empty and the other isn't, return the non-empty one
        if not tesseract_text and dl_text:
            return dl_text
        if tesseract_text and not dl_text:
            return tesseract_text
            
        # If both are valid but different, use heuristics to decide
        if tesseract_text and dl_text:
            # Check length - typically prefer the longer one as it likely captured more characters
            if len(tesseract_text) > len(dl_text) + 2:
                return tesseract_text
            if len(dl_text) > len(tesseract_text) + 2:
                return dl_text
                
            # If lengths are similar, prefer deep learning result as it's typically more robust
            return dl_text
            
        # If both methods failed, return None
        return None
    
    def _deep_learning_ocr(self, image):
        """
        Perform deep learning OCR on the given image.
        
        Args:
            image (numpy.ndarray): Preprocessed license plate image
            
        Returns:
            str: Recognized text
        """
        try:
            # Prepare the image for the model
            input_width = self.deep_learning_config.get('input_width', 100)
            input_height = self.deep_learning_config.get('input_height', 32)
            
            # Resize the image to the expected input size
            input_image = cv2.resize(image, (input_width, input_height), interpolation=cv2.INTER_CUBIC)
            
            # Normalize the image
            input_image = input_image.astype(np.float32) / 255.0
            
            # Add batch dimension if needed
            if len(input_image.shape) == 2:  # grayscale
                input_image = np.expand_dims(input_image, axis=-1)  # add channel dimension
            input_image = np.expand_dims(input_image, axis=0)  # add batch dimension
            
            # Use Hailo TPU or TensorFlow for OCR based on configuration
            if self.use_hailo_tpu:
                # Run inference on Hailo TPU
                try:
                    input_data = hailo_platform.Input(self.ocr_model.get_input_names()[0], input_image)
                    outputs = self.hailo_device.run(self.ocr_model, [input_data])
                    output_data = outputs[0].get_data()
                    
                    # Decode output using character mapping
                    text = self._decode_output(output_data, self.char_map)
                    logger.debug(f"Hailo TPU OCR result: {text}")
                    return text
                except Exception as e:
                    logger.error(f"Error running inference on Hailo TPU: {e}")
                    # Fall back to TensorFlow if available
                    if hasattr(self, 'ocr_model') and not isinstance(self.ocr_model, hailo_platform.Model):
                        logger.warning("Falling back to TensorFlow model")
                    else:
                        return None
            
            # Run inference on TensorFlow model
            if hasattr(self, 'ocr_model') and not isinstance(self.ocr_model, hailo_platform.Model):
                output = self.ocr_model.predict(input_image, verbose=0)
                
                # Decode output using character mapping
                text = self._decode_output(output, self.char_map)
                logger.debug(f"TensorFlow OCR result: {text}")
                return text
            else:
                logger.error("No OCR model available for inference")
                return None
        except Exception as e:
            logger.error(f"Error performing deep learning OCR: {e}")
            return None
    
    def _decode_output(self, output, char_map):
        """
        Decode the output of the OCR model using the character mapping.
        
        Args:
            output (numpy.ndarray): Output of the OCR model
            char_map (dict): Character mapping for decoding
        
        Returns:
            str: Decoded text
        """
        try:
            # Get the indices of the highest confidence characters
            indices = np.argmax(output, axis=1)
            
            # Map the indices to characters using the character mapping
            text = ''.join(char_map[i] for i in indices)
            
            return text
        except Exception as e:
            logger.error(f"Error decoding output: {e}")
            return None
    
    def _save_plate_image(self, frame, plate, plate_text):
        """
        Save the frame with the detected license plate.
        
        Args:
            frame (numpy.ndarray): Input frame
            plate (dict): License plate coordinates and confidence
            plate_text (str): Recognized plate text
        """
        try:
            # Draw rectangle around the plate
            x, y, w, h = plate['x'], plate['y'], plate['width'], plate['height']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add text with the recognized plate
            cv2.putText(frame, plate_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{plate_text}.jpg"
            filepath = os.path.join(self.image_save_path, filename)
            
            # Save the image
            cv2.imwrite(filepath, frame)
            logger.info(f"Saved plate image to {filepath}")
        except Exception as e:
            logger.error(f"Error saving plate image: {e}")
    
    def reload_ocr_config(self, ocr_config=None):
        """
        Reload OCR configuration.
        
        Args:
            ocr_config (dict, optional): New OCR configuration. If None, reloads from file.
        """
        if ocr_config is None:
            # Try to load from the path specified in the main config
            ocr_config_path = self.config.get('ocr_config_path')
            if ocr_config_path and os.path.exists(ocr_config_path):
                try:
                    with open(ocr_config_path, 'r') as f:
                        ocr_config = json.load(f)
                        logger.info(f"Reloaded OCR configuration from {ocr_config_path}")
                except Exception as e:
                    logger.error(f"Failed to reload OCR configuration from {ocr_config_path}: {e}")
                    return False
            else:
                logger.error(f"OCR configuration file not found at {ocr_config_path}")
                return False
        
        # Update OCR configuration
        self.ocr_method = ocr_config.get('ocr_method', self.ocr_method)
        self.use_hailo_tpu = ocr_config.get('use_hailo_tpu', self.use_hailo_tpu) and HAILO_AVAILABLE
        self.tesseract_config = ocr_config.get('tesseract_config', self.tesseract_config)
        self.deep_learning_config = ocr_config.get('deep_learning', self.deep_learning_config)
        self.preprocessing_config = ocr_config.get('preprocessing', self.preprocessing_config)
        self.postprocessing_config = ocr_config.get('postprocessing', self.postprocessing_config)
        self.regional_settings = ocr_config.get('regional_settings', self.regional_settings)
        
        # Reinitialize OCR models
        self._init_ocr_models()
        
        logger.info(f"OCR configuration reloaded with method: {self.ocr_method}")
        if self.use_hailo_tpu:
            logger.info("Using Hailo TPU for acceleration")
        
        return True
    
    def cleanup(self):
        """
        Clean up resources.
        """
        if self.use_onvif:
            # No need to clean up ONVIF camera manager here
            # It will be cleaned up by the caller
            pass
        else:
            # Don't try to use a local camera, raise an error since we only support ONVIF cameras
            logger.error("Only ONVIF cameras are supported")
            raise ValueError("Only ONVIF cameras are supported")
