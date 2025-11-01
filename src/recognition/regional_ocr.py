#!/usr/bin/env python3
"""
Regional OCR adaptations for license plate recognition.
Supports different character sets, formatting rules, and regional variations.
"""

import cv2
import numpy as np
import logging
import re
import pytesseract
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('VisiGate.regional_ocr')

class RegionalOCRAdapter:
    """
    Regional OCR adapter for different license plate formats.
    """

    def __init__(self, config):
        """
        Initialize regional OCR adapter.

        Args:
            config (dict): Regional OCR configuration
        """
        self.config = config
        self.regions = self._load_region_definitions()
        self.current_region = config.get('default_region', 'US')

    def _load_region_definitions(self):
        """
        Load region-specific definitions.

        Returns:
            dict: Region definitions
        """
        return {
            'US': {
                'name': 'United States',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^[A-Z]{1,3}\d{3,4}[A-Z]{0,2}$',
                'max_length': 8,
                'min_length': 5,
                'preprocessing': {
                    'morph_kernel': (3, 3),
                    'blur_size': (3, 3)
                }
            },
            'EU': {
                'name': 'European Union',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^[A-Z]{1,3}\d{1,4}[A-Z]{1,3}$',
                'max_length': 9,
                'min_length': 4,
                'preprocessing': {
                    'morph_kernel': (2, 2),
                    'blur_size': (2, 2)
                }
            },
            'UK': {
                'name': 'United Kingdom',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^[A-Z]{1,2}\d{1,2}[A-Z]{1,3}$',
                'max_length': 7,
                'min_length': 5,
                'preprocessing': {
                    'morph_kernel': (3, 3),
                    'blur_size': (3, 3)
                }
            },
            'JP': {
                'name': 'Japan',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^\d{1,4}[A-Z]{1,3}\d{1,4}$',
                'max_length': 8,
                'min_length': 4,
                'preprocessing': {
                    'morph_kernel': (2, 2),
                    'blur_size': (2, 2)
                }
            },
            'CN': {
                'name': 'China',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^[A-Z]\d{5}[A-Z]$',
                'max_length': 7,
                'min_length': 7,
                'preprocessing': {
                    'morph_kernel': (3, 3),
                    'blur_size': (3, 3)
                }
            },
            'KR': {
                'name': 'South Korea',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^\d{2,3}[A-Z]\d{4}$',
                'max_length': 7,
                'min_length': 6,
                'preprocessing': {
                    'morph_kernel': (2, 2),
                    'blur_size': (2, 2)
                }
            },
            'AU': {
                'name': 'Australia',
                'char_set': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                'format_pattern': r'^[A-Z]{1,3}\d{2,3}[A-Z]{1,3}$',
                'max_length': 7,
                'min_length': 5,
                'preprocessing': {
                    'morph_kernel': (3, 3),
                    'blur_size': (3, 3)
                }
            }
        }

    def set_region(self, region_code):
        """
        Set current region for OCR processing.

        Args:
            region_code (str): Region code (e.g., 'US', 'EU', 'UK')
        """
        if region_code not in self.regions:
            logger.warning(f"Unknown region code: {region_code}, using default")
            region_code = self.config.get('default_region', 'US')

        self.current_region = region_code
        logger.info(f"Set OCR region to: {self.regions[region_code]['name']}")

    def get_region_config(self, region_code=None):
        """
        Get configuration for a specific region.

        Args:
            region_code (str, optional): Region code, uses current if None

        Returns:
            dict: Region configuration
        """
        region = region_code or self.current_region
        return self.regions.get(region, self.regions['US'])

    def preprocess_for_region(self, image, region_code=None):
        """
        Preprocess image for specific regional requirements.

        Args:
            image (numpy.ndarray): Input image
            region_code (str, optional): Region code

        Returns:
            numpy.ndarray: Preprocessed image
        """
        region_config = self.get_region_config(region_code)

        # Apply region-specific preprocessing
        preprocessing = region_config.get('preprocessing', {})

        # Morphological operations
        kernel_size = preprocessing.get('morph_kernel', (3, 3))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
        processed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

        # Gaussian blur
        blur_size = preprocessing.get('blur_size', (3, 3))
        processed = cv2.GaussianBlur(processed, blur_size, 0)

        # Adaptive thresholding
        processed = cv2.adaptiveThreshold(
            processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return processed

    def get_tesseract_config(self, region_code=None):
        """
        Get Tesseract configuration for specific region.

        Args:
            region_code (str, optional): Region code

        Returns:
            str: Tesseract configuration string
        """
        region_config = self.get_region_config(region_code)
        char_set = region_config['char_set']

        # Build whitelist
        whitelist = f'tessedit_char_whitelist={char_set}'

        # PSM mode based on region
        psm_mode = 7  # Single line of text

        # OEM mode
        oem_mode = 1  # Neural nets LSTM engine

        config = f'--psm {psm_mode} --oem {oem_mode} -c {whitelist}'

        return config

    def validate_plate_format(self, text, region_code=None):
        """
        Validate license plate format for specific region.

        Args:
            text (str): License plate text
            region_code (str, optional): Region code

        Returns:
            bool: True if format is valid
        """
        if not text:
            return False

        region_config = self.get_region_config(region_code)
        pattern = region_config['format_pattern']

        # Check length constraints
        if not (region_config['min_length'] <= len(text) <= region_config['max_length']):
            return False

        # Check format pattern
        if not re.match(pattern, text):
            return False

        return True

    def normalize_plate_text(self, text, region_code=None):
        """
        Normalize license plate text for specific region.

        Args:
            text (str): Raw license plate text
            region_code (str, optional): Region code

        Returns:
            str: Normalized text
        """
        if not text:
            return ""

        # Remove whitespace and convert to uppercase
        text = ''.join(text.split()).upper()

        # Remove non-alphanumeric characters except region-specific allowed chars
        region_config = self.get_region_config(region_code)
        allowed_chars = set(region_config['char_set'])
        text = ''.join(c for c in text if c in allowed_chars)

        return text

    def detect_region_from_plate(self, text):
        """
        Attempt to detect region from license plate format.

        Args:
            text (str): License plate text

        Returns:
            str: Detected region code or None
        """
        if not text:
            return None

        text = self.normalize_plate_text(text, 'US')  # Basic normalization

        for region_code, region_config in self.regions.items():
            if self.validate_plate_format(text, region_code):
                return region_code

        return None

    def get_region_specific_ocr(self, image, region_code=None):
        """
        Perform region-specific OCR.

        Args:
            image (numpy.ndarray): Preprocessed license plate image
            region_code (str, optional): Region code

        Returns:
            str: Recognized text
        """
        region = region_code or self.current_region

        # Preprocess for region
        processed_image = self.preprocess_for_region(image, region)

        # Get Tesseract config for region
        config = self.get_tesseract_config(region)

        # Perform OCR
        try:
            text = pytesseract.image_to_string(processed_image, config=config)
            text = self.normalize_plate_text(text, region)

            # Validate format
            if self.validate_plate_format(text, region):
                return text
            else:
                logger.debug(f"OCR result '{text}' doesn't match {region} format")
                return ""

        except Exception as e:
            logger.error(f"OCR failed for region {region}: {e}")
            return ""

class DynamicOCRSwitcher:
    """
    Dynamic OCR model switching based on region detection.
    """

    def __init__(self, regional_adapter, model_configs=None):
        """
        Initialize dynamic OCR switcher.

        Args:
            regional_adapter (RegionalOCRAdapter): Regional OCR adapter
            model_configs (dict, optional): Model configurations per region
        """
        self.regional_adapter = regional_adapter
        self.model_configs = model_configs or {}
        self.model_cache = {}  # region -> model

    def switch_model(self, region_code):
        """
        Switch to OCR model for specific region.

        Args:
            region_code (str): Region code

        Returns:
            bool: True if switch successful
        """
        if region_code in self.model_cache:
            logger.debug(f"Using cached model for region {region_code}")
            return True

        # Load model for region (placeholder - would load actual models)
        model_config = self.model_configs.get(region_code, {})

        # In a real implementation, this would load region-specific models
        # For now, just cache the region
        self.model_cache[region_code] = model_config

        logger.info(f"Switched OCR model to region: {region_code}")
        return True

    def process_with_auto_region(self, image):
        """
        Process image with automatic region detection.

        Args:
            image (numpy.ndarray): License plate image

        Returns:
            tuple: (recognized_text, detected_region)
        """
        # Try default region first
        text = self.regional_adapter.get_region_specific_ocr(image)
        if text:
            detected_region = self.regional_adapter.detect_region_from_plate(text)
            if detected_region:
                return text, detected_region

        # Try other regions if default fails
        for region_code in self.regional_adapter.regions.keys():
            if region_code == self.regional_adapter.current_region:
                continue

            self.regional_adapter.set_region(region_code)
            text = self.regional_adapter.get_region_specific_ocr(image, region_code)

            if text and self.regional_adapter.validate_plate_format(text, region_code):
                return text, region_code

        return "", None

class MultiLanguageOCR:
    """
    Multi-language OCR support for international license plates.
    """

    def __init__(self, regional_adapter):
        """
        Initialize multi-language OCR.

        Args:
            regional_adapter (RegionalOCRAdapter): Regional OCR adapter
        """
        self.regional_adapter = regional_adapter
        self.language_map = {
            'US': 'eng',
            'EU': 'eng+deu+fra',
            'UK': 'eng',
            'JP': 'jpn',
            'CN': 'chi_sim',
            'KR': 'kor',
            'AU': 'eng'
        }

    def get_ocr_text_multilang(self, image, languages=None):
        """
        Perform multi-language OCR.

        Args:
            image (numpy.ndarray): License plate image
            languages (list, optional): List of language codes

        Returns:
            dict: Results per language
        """
        if languages is None:
            languages = ['eng']  # Default to English

        results = {}

        for lang in languages:
            try:
                config = f'-l {lang} --psm 7 --oem 1'
                text = pytesseract.image_to_string(image, config=config)
                text = self.regional_adapter.normalize_plate_text(text)

                if text:
                    results[lang] = text

            except Exception as e:
                logger.error(f"Multi-language OCR failed for {lang}: {e}")

        return results

    def select_best_result(self, results, region_code=None):
        """
        Select best OCR result from multi-language results.

        Args:
            results (dict): OCR results per language
            region_code (str, optional): Expected region

        Returns:
            str: Best recognized text
        """
        if not results:
            return ""

        # Score results based on format validation and confidence
        scored_results = []

        for lang, text in results.items():
            score = 0

            # Format validation score
            if self.regional_adapter.validate_plate_format(text, region_code):
                score += 10

            # Length score (prefer reasonable lengths)
            length = len(text)
            if 4 <= length <= 8:
                score += 5
            elif length < 4:
                score -= 5

            # Character diversity score
            unique_chars = len(set(text))
            score += min(unique_chars, 5)

            scored_results.append((text, score))

        # Return highest scoring result
        if scored_results:
            scored_results.sort(key=lambda x: x[1], reverse=True)
            return scored_results[0][0]

        return ""