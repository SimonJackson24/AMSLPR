#!/usr/bin/env python3
"""
License plate detection and recognition module - Fixed version with proper error handling.
"""

import cv2
import numpy as np
import os
import logging
import time
import pytesseract
from datetime import datetime
import json
import threading
import concurrent.futures
import queue

logger = logging.getLogger('VisiGate.recognition')

# Advanced features imports
try:
    from src.recognition.camera_sync import CameraSyncManager
    CAMERA_SYNC_AVAILABLE = True
except ImportError:
    CAMERA_SYNC_AVAILABLE = False

try:
    from src.recognition.plate_tracker import LicensePlateTracker
    PLATE_TRACKER_AVAILABLE = True
except ImportError:
    PLATE_TRACKER_AVAILABLE = False

try:
    from src.recognition.regional_ocr import RegionalOCRAdapter, DynamicOCRSwitcher
    REGIONAL_OCR_AVAILABLE = True
except ImportError:
    REGIONAL_OCR_AVAILABLE = False

try:
    from src.recognition.confidence_scorer import (
        MultiFactorConfidenceScorer,
        QualityBasedDecisionMaker,
        OCRConfidenceAggregator
    )
    CONFIDENCE_SCORER_AVAILABLE = True
except ImportError:
    CONFIDENCE_SCORER_AVAILABLE = False

# Add imports for deep learning OCR with proper error handling
try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
    logger.debug("TensorFlow imported successfully")
except (ImportError, Exception) as e:
    tf = None
    TENSORFLOW_AVAILABLE = False
    logger.warning(f"TensorFlow not available: {e}")

try:
    # Import Hailo-specific libraries if available
    try:
        import hailo_platform  # type: ignore
    except ImportError:
        raise ImportError("hailo_platform not available")

    try:
        # Optional: model zoo provides convenience utilities but is not strictly required
        import hailo_model_zoo  # type: ignore
        HAILO_MODEL_ZOO_AVAILABLE = True
    except ImportError:
        # Log a warning but do not fail TPU availability if model zoo is missing
        HAILO_MODEL_ZOO_AVAILABLE = False
        logger.warning(
            "hailo_model_zoo not found – continuing without it. Ensure .hef models are provided via 'hailo_ocr_model_path'."
        )
    HAILO_AVAILABLE = True
    logger.info("Hailo platform libraries imported successfully")
except ImportError as e:
    hailo_platform = None
    HAILO_AVAILABLE = False
    logger.warning(f"Hailo platform not available: {e}")

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

        # Performance optimization configuration
        self.performance_config = config.get('performance', {})
        self.enable_buffer_prealloc = self.performance_config.get('enable_buffer_prealloc', True)
        self.enable_parallel = self.performance_config.get('enable_parallel', True)
        self.frame_skip_threshold = self.performance_config.get('frame_skip_threshold', 0.033)  # ~30 FPS
        self.enable_monitoring = self.performance_config.get('enable_monitoring', True)
        self.max_workers = self.performance_config.get('max_workers', 4)

        # Pre-allocate buffers to avoid dynamic memory allocation
        if self.enable_buffer_prealloc:
            self.frame_buffer = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
            self.gray_buffer = np.zeros((self.frame_height, self.frame_width), dtype=np.uint8)
            self.blur_buffer = np.zeros((self.frame_height, self.frame_width), dtype=np.uint8)
            self.thresh_buffer = np.zeros((self.frame_height, self.frame_width), dtype=np.uint8)

        # Memory pool for plate images
        self.plate_pool = queue.Queue(maxsize=10)

        # Thread pool for parallel processing
        if self.enable_parallel:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

        # Performance monitoring
        self.last_process_time = 0
        self.metrics = {
            'frame_count': 0,
            'total_time': 0,
            'avg_latency': 0,
            'skipped_frames': 0,
            'processing_times': [],
            # Cache metrics
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_hit_rate': 0.0,
            'cache_memory_usage': 0,
            'cache_redis_connected': False,
            'cache_file_size': 0,
            'cache_health_status': 'unknown'
        }
        self.metrics_lock = threading.Lock()
        # Cache monitoring
        self.cache_metrics_enabled = self.performance_config.get('cache_metrics_enabled', True)
        self.cache_health_check_interval = self.performance_config.get('cache_health_check_interval', 60)  # seconds
        self.last_cache_health_check = 0

        # Create image save directory if it doesn't exist
        if self.save_images and not os.path.exists(self.image_save_path):
            os.makedirs(self.image_save_path)

        # Initialize detector
        self._init_detector()

        # Initialize OCR models
        self._init_ocr_models()

        # Initialize caching system
        self._init_caching()

        # Initialize advanced features
        self._init_advanced_features()

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
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow not available")

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

    def _init_caching(self):
        """
        Initialize caching system for performance optimization.
        """
        try:
            from src.cache.cache_manager import CacheManager

            # Cache configuration
            cache_config = self.config.get('cache', {})
            cache_config.setdefault('memory', {'max_size': 1000, 'default_ttl': 300})
            cache_config.setdefault('redis', {'enabled': False})
            cache_config.setdefault('file', {'enabled': True, 'cache_dir': 'cache/detector'})

            self.cache_manager = CacheManager(cache_config)
            self.enable_caching = cache_config.get('enabled', True)

            if self.enable_caching:
                logger.info("Caching system initialized for license plate detector")
            else:
                logger.info("Caching system disabled")
        except Exception as e:
            logger.error(f"Failed to initialize caching system: {e}")
            self.cache_manager = None
            self.enable_caching = False

    def _init_advanced_features(self):
        """
        Initialize advanced features for the detector.
        """
        # Camera synchronization
        if CAMERA_SYNC_AVAILABLE:
            try:
                sync_config = self.config.get('camera_sync', {})
                self.camera_sync = CameraSyncManager(sync_config)
                logger.info("Camera synchronization initialized")
            except Exception as e:
                logger.error(f"Failed to initialize camera synchronization: {e}")
                self.camera_sync = None
        else:
            self.camera_sync = None
            logger.warning("Camera synchronization not available")

        # License plate tracking
        if PLATE_TRACKER_AVAILABLE:
            try:
                tracking_config = self.config.get('plate_tracking', {})
                self.plate_tracker = LicensePlateTracker(tracking_config)
                logger.info("License plate tracking initialized")
            except Exception as e:
                logger.error(f"Failed to initialize plate tracking: {e}")
                self.plate_tracker = None
        else:
            self.plate_tracker = None
            logger.warning("License plate tracking not available")

        # Regional OCR
        if REGIONAL_OCR_AVAILABLE:
            try:
                regional_config = self.config.get('regional_ocr', {})
                self.regional_ocr = RegionalOCRAdapter(regional_config)
                self.ocr_switcher = DynamicOCRSwitcher(self.regional_ocr, regional_config.get('models', {}))
                logger.info("Regional OCR initialized")
            except Exception as e:
                logger.error(f"Failed to initialize regional OCR: {e}")
                self.regional_ocr = None
                self.ocr_switcher = None
        else:
            self.regional_ocr = None
            self.ocr_switcher = None
            logger.warning("Regional OCR not available")

        # Confidence scoring
        if CONFIDENCE_SCORER_AVAILABLE:
            try:
                confidence_config = self.config.get('confidence_scoring', {})
                self.confidence_scorer = MultiFactorConfidenceScorer(confidence_config)
                self.decision_maker = QualityBasedDecisionMaker(self.confidence_scorer)
                logger.info("Confidence scoring initialized")
            except Exception as e:
                logger.error(f"Failed to initialize confidence scoring: {e}")
                self.confidence_scorer = None
                self.decision_maker = None
        else:
            self.confidence_scorer = None
            self.decision_maker = None
            logger.warning("Confidence scoring not available")

    def process_frame(self):
        """
        Process a frame from the camera and detect license plates.

        Returns:
            str: Detected license plate text, or None if no plate detected
        """
        start_time = time.perf_counter()

        # Frame skipping for high-frame-rate streams
        current_time = time.perf_counter()
        if self.last_process_time > 0 and (current_time - self.last_process_time) < self.frame_skip_threshold:
            with self.metrics_lock:
                self.metrics['skipped_frames'] += 1
            logger.debug(f"Skipping frame for camera {self.camera_id} to maintain performance")
            return None

        logger.debug(f"Processing frame for camera {self.camera_id}, mock_mode: {self.mock_mode}")

        # Capture frame from camera
        if self.use_onvif:
            # Get frame from ONVIF camera manager
            logger.debug("Attempting to get frame from ONVIF camera manager")
            frame, timestamp = self.onvif_camera_manager.get_frame(self.camera_id)
            if frame is None:
                logger.error("Failed to get frame from ONVIF camera")
                return None
            logger.debug(f"Successfully got frame from camera, shape: {frame.shape if frame is not None else 'None'}")
        else:
            # Don't try to use a local camera, raise an error since we only support ONVIF cameras
            logger.error("Only ONVIF cameras are supported")
            raise ValueError("Only ONVIF cameras are supported")

        # Detect license plate
        logger.debug("Starting license plate detection")
        plates = self.detect_license_plates(frame, self.config.get('camera_settings'))
        logger.debug(f"Detected {len(plates)} potential license plates")

        if not plates:
            logger.debug("No license plates detected")
            return None

        # Recognize text on the plate
        logger.debug(f"Attempting to recognize text on plate: {plates[0]}")
        plate_text = self._recognize_text(frame, plates[0])
        logger.debug(f"Recognized text: '{plate_text}'")

        # Apply confidence scoring if available
        if CONFIDENCE_SCORER_AVAILABLE and self.confidence_scorer and self.decision_maker:
            x, y, w, h = plates[0]['x'], plates[0]['y'], plates[0]['width'], plates[0]['height']
            detection_result = {
                'text': plate_text,
                'image': frame[y:y+h, x:x+w] if plate_text else None,
                'confidence': plates[0].get('confidence', 0.5),
                'bbox': plates[0]
            }

            decision = self.decision_maker.should_process_plate(detection_result)
            if not decision['should_process']:
                logger.debug(f"Plate rejected by confidence scoring: {decision['decision_result']['reason']}")
                return None

            logger.debug(f"Plate accepted with confidence: {decision['confidence_result']['overall_confidence']:.3f}")

        # Save image if enabled
        if self.save_images and plate_text:
            self._save_plate_image(frame, plates[0], plate_text)

        # Update performance metrics
        if self.enable_monitoring:
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            with self.metrics_lock:
                self.metrics['frame_count'] += 1
                self.metrics['total_time'] += processing_time
                self.metrics['processing_times'].append(processing_time)
                if len(self.metrics['processing_times']) > 100:  # Keep last 100 times
                    self.metrics['processing_times'].pop(0)
                self.metrics['avg_latency'] = sum(self.metrics['processing_times']) / len(self.metrics['processing_times'])

        # Perform periodic cache health check
        if self.cache_metrics_enabled and self.enable_caching and self.cache_manager:
            current_time = time.time()
            if current_time - self.last_cache_health_check >= self.cache_health_check_interval:
                self._perform_cache_health_check()
                self.last_cache_health_check = current_time

        self.last_process_time = current_time

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

        # Convert to grayscale using pre-allocated buffer
        if self.enable_buffer_prealloc:
            # Ensure frame matches buffer size
            if frame.shape[:2] != (self.frame_height, self.frame_width):
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY, dst=self.gray_buffer)
            blur = cv2.GaussianBlur(gray, (5, 5), 0, dst=self.blur_buffer)
            thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2, dst=self.thresh_buffer)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
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
            # Extract the license plate from the frame using memory pool
            x, y, w, h = plate['x'], plate['y'], plate['width'], plate['height']
            if self.enable_buffer_prealloc and not self.plate_pool.empty():
                try:
                    plate_img = self.plate_pool.get_nowait()
                    # Resize if necessary
                    if plate_img.shape[:2] != (h, w):
                        plate_img = cv2.resize(plate_img, (w, h))
                    frame[y:y+h, x:x+w].copyTo(plate_img)
                except queue.Empty:
                    plate_img = frame[y:y+h, x:x+w].copy()
            else:
                plate_img = frame[y:y+h, x:x+w].copy()
            # Check cache for OCR result if caching is enabled
            if self.enable_caching and self.cache_manager:
                cached_result = self.cache_manager.get_ocr_result(plate_img)
                if cached_result:
                    logger.debug(f"Cache hit for OCR result: {cached_result.text}")
                    return cached_result.text

            # Preprocess the image for OCR
            from src.utils.helpers import enhance_plate_image
            enhanced_img = enhance_plate_image(plate_img, self.preprocessing_config)

            # Use advanced OCR features if available
            if REGIONAL_OCR_AVAILABLE and self.regional_ocr:
                # Use regional OCR with automatic region detection
                text, detected_region = self.ocr_switcher.process_with_auto_region(enhanced_img)
                if detected_region and detected_region != self.regional_ocr.current_region:
                    logger.debug(f"Detected region changed to: {detected_region}")
            else:
                # Use the selected OCR method
                if self.ocr_method == 'tesseract':
                    # Use Tesseract OCR with configured parameters
                    psm_mode = self.tesseract_config.get('psm_mode', 7)
                    oem_mode = self.tesseract_config.get('oem_mode', 1)
                    whitelist = self.tesseract_config.get('whitelist', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

                    config_str = f'--psm {psm_mode} --oem {oem_mode} -c tessedit_char_whitelist={whitelist}'
                    if self.enable_parallel:
                        future = self.executor.submit(pytesseract.image_to_string, enhanced_img, config=config_str)
                        text = future.result()
                    else:
                        text = pytesseract.image_to_string(enhanced_img, config=config_str)
                        text = self._clean_plate_text(text)

                elif self.ocr_method == 'deep_learning':
                    # Use deep learning OCR
                    text = self._deep_learning_ocr(enhanced_img)
                    text = self._clean_plate_text(text)

                elif self.ocr_method == 'hybrid':
                    # Use both methods and select the most reliable result
                    # Parallel OCR processing
                    psm_mode = self.tesseract_config.get('psm_mode', 7)
                    oem_mode = self.tesseract_config.get('oem_mode', 1)
                    whitelist = self.tesseract_config.get('whitelist', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                    config_str = f'--psm {psm_mode} --oem {oem_mode} -c tessedit_char_whitelist={whitelist}'

                    if self.enable_parallel:
                        # Submit both OCR tasks in parallel
                        tesseract_future = self.executor.submit(pytesseract.image_to_string, enhanced_img, config=config_str)
                        dl_future = self.executor.submit(self._deep_learning_ocr, enhanced_img)

                        tesseract_text = tesseract_future.result()
                        dl_text = dl_future.result()
                    else:
                        tesseract_text = pytesseract.image_to_string(enhanced_img, config=config_str)
                        dl_text = self._deep_learning_ocr(enhanced_img)

                    tesseract_text = self._clean_plate_text(tesseract_text)
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
                # Apply regex validation if configured
                if self.postprocessing_config.get('apply_regex_validation', False) and self.regional_settings.get('plate_format'):
                    import re
                    pattern = self.regional_settings.get('plate_format')
                    if not re.match(pattern, text):
                        logger.debug(f"Rejected plate text '{text}' due to format validation")
                        return None

                # Cache the OCR result if caching is enabled and we have valid text
                if self.enable_caching and self.cache_manager and text and len(text) >= 4:
                    confidence = plate.get('confidence', 0.8)  # Use plate detection confidence as proxy
                    self.cache_manager.cache_ocr_result(plate_img, text, confidence)
                    logger.debug(f"Cached OCR result: {text}")

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

    def get_performance_metrics(self):
        """
        Get current performance metrics.

        Returns:
            dict: Performance metrics
        """
        # Collect cache metrics if enabled
        if self.cache_metrics_enabled and self.enable_caching and self.cache_manager:
            self._collect_cache_metrics()

        with self.metrics_lock:
            return self.metrics.copy()

    def _collect_cache_metrics(self):
        """
        Collect cache metrics from cache manager and update metrics dictionary.
        Thread-safe implementation.
        """
        if not self.cache_manager:
            return

        try:
            # Get cache statistics
            cache_stats = self.cache_manager.get_stats()

            # Extract metrics
            result_cache_stats = cache_stats.get('result_cache', {})
            memory_stats = cache_stats.get('memory', {})
            redis_stats = cache_stats.get('redis', {})
            file_stats = cache_stats.get('file', {})

            # Calculate cache metrics
            cache_hits = result_cache_stats.get('hits', 0)
            cache_misses = result_cache_stats.get('misses', 0)
            total_requests = cache_hits + cache_misses
            cache_hit_rate = (cache_hits / total_requests) if total_requests > 0 else 0.0

            cache_memory_usage = memory_stats.get('size', 0)
            cache_redis_connected = redis_stats.get('connected', False)
            cache_file_size = file_stats.get('size', 0)

            # Update metrics thread-safely
            with self.metrics_lock:
                self.metrics['cache_hits'] = cache_hits
                self.metrics['cache_misses'] = cache_misses
                self.metrics['cache_hit_rate'] = cache_hit_rate
                self.metrics['cache_memory_usage'] = cache_memory_usage
                self.metrics['cache_redis_connected'] = cache_redis_connected
                self.metrics['cache_file_size'] = cache_file_size

        except Exception as e:
            logger.warning(f"Failed to collect cache metrics: {e}")
            # Graceful fallback - don't update metrics on error

    def _perform_cache_health_check(self):
        """
        Perform cache health check and update health status.
        """
        if not self.cache_manager:
            with self.metrics_lock:
                self.metrics['cache_health_status'] = 'no_cache'
            return

        try:
            health = self.cache_manager.health_check()

            # Determine overall health status
            overall_healthy = True
            health_details = []

            for cache_type, status in health.items():
                if not status.get('healthy', False):
                    overall_healthy = False
                    health_details.append(f"{cache_type}: unhealthy")
                else:
                    health_details.append(f"{cache_type}: healthy")

            health_status = 'healthy' if overall_healthy else 'degraded'

            with self.metrics_lock:
                self.metrics['cache_health_status'] = health_status

            logger.debug(f"Cache health check: {health_status} - {', '.join(health_details)}")

        except Exception as e:
            logger.warning(f"Cache health check failed: {e}")
            with self.metrics_lock:
                self.metrics['cache_health_status'] = 'error'

    def cleanup(self):
        """
        Clean up resources.
        """
        # Log final cache statistics
        if self.cache_metrics_enabled and self.enable_caching and self.cache_manager:
            try:
                final_metrics = self.get_performance_metrics()
                logger.info("Final cache statistics:")
                logger.info(f"  Cache hits: {final_metrics.get('cache_hits', 0)}")
                logger.info(f"  Cache misses: {final_metrics.get('cache_misses', 0)}")
                logger.info(f"  Cache hit rate: {final_metrics.get('cache_hit_rate', 0):.2%}")
                logger.info(f"  Cache memory usage: {final_metrics.get('cache_memory_usage', 0)}")
                logger.info(f"  Cache file size: {final_metrics.get('cache_file_size', 0)}")
                logger.info(f"  Cache health status: {final_metrics.get('cache_health_status', 'unknown')}")
                logger.info(f"  Redis connected: {final_metrics.get('cache_redis_connected', False)}")
            except Exception as e:
                logger.warning(f"Failed to log final cache statistics: {e}")

        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=True)

        if self.use_onvif:
            # No need to clean up ONVIF camera manager here
            # It will be cleaned up by the caller
            pass
        else:
            # Don't try to use a local camera, raise an error since we only support ONVIF cameras
            logger.error("Only ONVIF cameras are supported")
            raise ValueError("Only ONVIF cameras are supported")

    def get_advanced_features_status(self):
        """
        Get status of advanced features.

        Returns:
            dict: Status of all advanced features
        """
        return {
            'camera_sync': {
                'available': CAMERA_SYNC_AVAILABLE,
                'enabled': self.camera_sync is not None,
                'status': self.camera_sync.get_sync_status() if self.camera_sync else None
            },
            'plate_tracking': {
                'available': PLATE_TRACKER_AVAILABLE,
                'enabled': self.plate_tracker is not None,
                'stats': self.plate_tracker.get_tracking_stats() if self.plate_tracker else None
            },
            'regional_ocr': {
                'available': REGIONAL_OCR_AVAILABLE,
                'enabled': self.regional_ocr is not None,
                'current_region': self.regional_ocr.current_region if self.regional_ocr else None
            },
            'confidence_scoring': {
                'available': CONFIDENCE_SCORER_AVAILABLE,
                'enabled': self.confidence_scorer is not None
            }
        }

    def synchronize_cameras(self, camera_ids):
        """
        Synchronize multiple cameras.

        Args:
            camera_ids (list): List of camera IDs to synchronize

        Returns:
            dict: Synchronization results
        """
        if not self.camera_sync:
            logger.warning("Camera synchronization not available")
            return {}

        return self.camera_sync.synchronize_cameras(camera_ids)

    def track_plate(self, plate_id, detection, camera_id):
        """
        Track a license plate across frames.

        Args:
            plate_id (str): Unique plate identifier
            detection (dict): Detection data
            camera_id (str): Camera identifier

        Returns:
            dict: Tracking information
        """
        if not self.plate_tracker:
            logger.warning("Plate tracking not available")
            return {}

        return self.plate_tracker.update_track(plate_id, detection, camera_id)

    def correlate_cross_camera(self, detections, camera_ids):
        """
        Correlate license plates across multiple cameras.

        Args:
            detections (dict): Camera detections
            camera_ids (list): Camera IDs

        Returns:
            dict: Correlation results
        """
        if not self.plate_tracker:
            logger.warning("Plate tracking not available")
            return {}

        return self.plate_tracker.correlate_cross_camera(detections, camera_ids)

    def set_ocr_region(self, region_code):
        """
        Set OCR region for regional adaptations.

        Args:
            region_code (str): Region code (e.g., 'US', 'EU', 'UK')

        Returns:
            bool: Success status
        """
        if not self.regional_ocr:
            logger.warning("Regional OCR not available")
            return False

        self.regional_ocr.set_region(region_code)
        return True

    def get_confidence_score(self, detection_result):
        """
        Calculate confidence score for a detection result.

        Args:
            detection_result (dict): Detection result

        Returns:
            dict: Confidence scoring results
        """
        if not self.confidence_scorer:
            logger.warning("Confidence scoring not available")
            return {'overall_confidence': detection_result.get('confidence', 0.5)}

        return self.confidence_scorer.calculate_overall_confidence(detection_result)

    def make_quality_decision(self, detection_result):
        """
        Make quality-based decision for processing.

        Args:
            detection_result (dict): Detection result

        Returns:
            dict: Decision result
        """
        if not self.decision_maker:
            logger.warning("Decision maker not available")
            return {'should_process': True, 'decision': 'accept_default'}

        return self.decision_maker.should_process_plate(detection_result)