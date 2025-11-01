#!/usr/bin/env python3
"""
Confidence scoring and quality assessment for license plate recognition.
Provides multi-factor confidence scoring and quality-based decision making.
"""

import cv2
import numpy as np
import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('VisiGate.confidence_scorer')

class ImageQualityAssessor:
    """
    Image quality assessment for license plates.
    """

    def __init__(self, config):
        """
        Initialize image quality assessor.

        Args:
            config (dict): Quality assessment configuration
        """
        self.config = config
        self.blur_threshold = config.get('blur_threshold', 100)
        self.brightness_range = config.get('brightness_range', (50, 200))
        self.contrast_threshold = config.get('contrast_threshold', 30)
        self.min_resolution = config.get('min_resolution', (50, 20))

    def assess_image_quality(self, image):
        """
        Assess overall image quality.

        Args:
            image (numpy.ndarray): License plate image

        Returns:
            dict: Quality metrics
        """
        if image is None or image.size == 0:
            return {'overall_score': 0, 'blur_score': 0, 'brightness_score': 0,
                   'contrast_score': 0, 'resolution_score': 0}

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Assess different quality factors
        blur_score = self._assess_blur(gray)
        brightness_score = self._assess_brightness(gray)
        contrast_score = self._assess_contrast(gray)
        resolution_score = self._assess_resolution(image)

        # Calculate overall score (weighted average)
        weights = {
            'blur': 0.3,
            'brightness': 0.2,
            'contrast': 0.3,
            'resolution': 0.2
        }

        overall_score = (
            blur_score * weights['blur'] +
            brightness_score * weights['brightness'] +
            contrast_score * weights['contrast'] +
            resolution_score * weights['resolution']
        )

        return {
            'overall_score': overall_score,
            'blur_score': blur_score,
            'brightness_score': brightness_score,
            'contrast_score': contrast_score,
            'resolution_score': resolution_score
        }

    def _assess_blur(self, image):
        """
        Assess image blur using Laplacian variance.

        Args:
            image (numpy.ndarray): Grayscale image

        Returns:
            float: Blur score (0-1, higher is better)
        """
        try:
            # Calculate Laplacian variance
            laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()

            # Normalize to 0-1 scale
            # Lower variance = more blur
            score = min(1.0, laplacian_var / self.blur_threshold)
            return score
        except Exception as e:
            logger.error(f"Blur assessment failed: {e}")
            return 0.0

    def _assess_brightness(self, image):
        """
        Assess image brightness.

        Args:
            image (numpy.ndarray): Grayscale image

        Returns:
            float: Brightness score (0-1, higher is better)
        """
        try:
            mean_brightness = np.mean(image)
            min_bright, max_bright = self.brightness_range

            if min_bright <= mean_brightness <= max_bright:
                return 1.0
            elif mean_brightness < min_bright:
                return mean_brightness / min_bright
            else:
                return max_bright / mean_brightness
        except Exception as e:
            logger.error(f"Brightness assessment failed: {e}")
            return 0.0

    def _assess_contrast(self, image):
        """
        Assess image contrast.

        Args:
            image (numpy.ndarray): Grayscale image

        Returns:
            float: Contrast score (0-1, higher is better)
        """
        try:
            # Calculate standard deviation as contrast measure
            contrast = np.std(image)

            # Normalize to 0-1 scale
            score = min(1.0, contrast / self.contrast_threshold)
            return score
        except Exception as e:
            logger.error(f"Contrast assessment failed: {e}")
            return 0.0

    def _assess_resolution(self, image):
        """
        Assess image resolution.

        Args:
            image (numpy.ndarray): Image

        Returns:
            float: Resolution score (0-1, higher is better)
        """
        try:
            height, width = image.shape[:2]
            min_width, min_height = self.min_resolution

            width_score = min(1.0, width / min_width)
            height_score = min(1.0, height / min_height)

            return min(width_score, height_score)
        except Exception as e:
            logger.error(f"Resolution assessment failed: {e}")
            return 0.0

class MultiFactorConfidenceScorer:
    """
    Multi-factor confidence scoring for license plate recognition.
    """

    def __init__(self, config):
        """
        Initialize confidence scorer.

        Args:
            config (dict): Confidence scoring configuration
        """
        self.config = config
        self.quality_assessor = ImageQualityAssessor(config.get('quality', {}))
        self.weights = config.get('weights', {
            'ocr_confidence': 0.4,
            'image_quality': 0.3,
            'format_validation': 0.2,
            'consistency': 0.1
        })

    def calculate_overall_confidence(self, detection_result):
        """
        Calculate overall confidence score from multiple factors.

        Args:
            detection_result (dict): Detection result with various metrics

        Returns:
            dict: Confidence scores and factors
        """
        factors = {}

        # OCR confidence
        factors['ocr_confidence'] = detection_result.get('ocr_confidence', 0.0)

        # Image quality score
        image = detection_result.get('image')
        if image is not None:
            quality_metrics = self.quality_assessor.assess_image_quality(image)
            factors['image_quality'] = quality_metrics['overall_score']
        else:
            factors['image_quality'] = 0.0

        # Format validation score
        factors['format_validation'] = self._calculate_format_score(detection_result)

        # Consistency score (based on multiple detections)
        factors['consistency'] = self._calculate_consistency_score(detection_result)

        # Calculate weighted overall score
        overall_score = sum(
            factors[factor] * weight
            for factor, weight in self.weights.items()
        )

        # Ensure score is between 0 and 1
        overall_score = max(0.0, min(1.0, overall_score))

        return {
            'overall_confidence': overall_score,
            'factors': factors,
            'weights': self.weights
        }

    def _calculate_format_score(self, detection_result):
        """
        Calculate format validation score.

        Args:
            detection_result (dict): Detection result

        Returns:
            float: Format score (0-1)
        """
        text = detection_result.get('text', '')
        if not text:
            return 0.0

        # Basic format checks
        score = 0.0

        # Length check (reasonable license plate length)
        if 4 <= len(text) <= 10:
            score += 0.3

        # Character diversity (should have both letters and numbers)
        has_letters = any(c.isalpha() for c in text)
        has_numbers = any(c.isdigit() for c in text)

        if has_letters and has_numbers:
            score += 0.4
        elif has_letters or has_numbers:
            score += 0.2

        # No special characters
        if all(c.isalnum() for c in text):
            score += 0.3

        return min(1.0, score)

    def _calculate_consistency_score(self, detection_result):
        """
        Calculate consistency score based on multiple detections.

        Args:
            detection_result (dict): Detection result

        Returns:
            float: Consistency score (0-1)
        """
        # This would typically compare with previous detections
        # For now, return a default score
        return 0.8

    def get_confidence_thresholds(self):
        """
        Get confidence thresholds for decision making.

        Returns:
            dict: Thresholds for different confidence levels
        """
        return {
            'high_confidence': 0.8,
            'medium_confidence': 0.6,
            'low_confidence': 0.4,
            'reject_threshold': 0.2
        }

    def make_decision(self, confidence_result):
        """
        Make decision based on confidence score.

        Args:
            confidence_result (dict): Confidence scoring result

        Returns:
            dict: Decision result
        """
        overall_score = confidence_result['overall_confidence']
        thresholds = self.get_confidence_thresholds()

        if overall_score >= thresholds['high_confidence']:
            decision = 'accept_high'
            confidence_level = 'high'
        elif overall_score >= thresholds['medium_confidence']:
            decision = 'accept_medium'
            confidence_level = 'medium'
        elif overall_score >= thresholds['low_confidence']:
            decision = 'review'
            confidence_level = 'low'
        else:
            decision = 'reject'
            confidence_level = 'very_low'

        return {
            'decision': decision,
            'confidence_level': confidence_level,
            'score': overall_score,
            'thresholds': thresholds
        }

class OCRConfidenceAggregator:
    """
    OCR confidence aggregation from multiple sources.
    """

    def __init__(self, config):
        """
        Initialize OCR confidence aggregator.

        Args:
            config (dict): Aggregation configuration
        """
        self.config = config
        self.methods = config.get('ocr_methods', ['tesseract', 'deep_learning'])

    def aggregate_confidence(self, ocr_results):
        """
        Aggregate confidence from multiple OCR methods.

        Args:
            ocr_results (dict): Results from different OCR methods

        Returns:
            dict: Aggregated confidence results
        """
        if not ocr_results:
            return {'aggregated_confidence': 0.0, 'method_confidences': {}}

        method_confidences = {}
        weights = {}

        # Calculate confidence for each method
        for method, result in ocr_results.items():
            if method == 'tesseract':
                confidence = self._calculate_tesseract_confidence(result)
                weights[method] = 0.4
            elif method == 'deep_learning':
                confidence = self._calculate_dl_confidence(result)
                weights[method] = 0.6
            else:
                confidence = 0.5
                weights[method] = 0.3

            method_confidences[method] = confidence

        # Weighted average
        total_weight = sum(weights.values())
        if total_weight > 0:
            aggregated = sum(
                conf * weights[method]
                for method, conf in method_confidences.items()
            ) / total_weight
        else:
            aggregated = 0.0

        # Consensus bonus
        if len(ocr_results) > 1:
            texts = [result.get('text', '') for result in ocr_results.values()]
            if len(set(texts)) == 1 and texts[0]:  # All methods agree
                aggregated = min(1.0, aggregated + 0.2)

        return {
            'aggregated_confidence': aggregated,
            'method_confidences': method_confidences,
            'consensus_bonus': 0.2 if len(set(texts)) == 1 else 0.0
        }

    def _calculate_tesseract_confidence(self, result):
        """
        Calculate confidence from Tesseract result.

        Args:
            result (dict): Tesseract OCR result

        Returns:
            float: Confidence score
        """
        # Tesseract provides confidence scores per character
        # This is a simplified implementation
        confidence = result.get('confidence', 0.5)
        return min(1.0, confidence / 100.0)  # Convert to 0-1 scale

    def _calculate_dl_confidence(self, result):
        """
        Calculate confidence from deep learning result.

        Args:
            result (dict): Deep learning OCR result

        Returns:
            float: Confidence score
        """
        # Deep learning models typically output confidence scores
        confidence = result.get('confidence', 0.5)
        return confidence

class QualityBasedDecisionMaker:
    """
    Quality-based decision making for license plate processing.
    """

    def __init__(self, confidence_scorer):
        """
        Initialize decision maker.

        Args:
            confidence_scorer (MultiFactorConfidenceScorer): Confidence scorer
        """
        self.confidence_scorer = confidence_scorer

    def should_process_plate(self, detection_result):
        """
        Decide whether to process a detected license plate.

        Args:
            detection_result (dict): Detection result

        Returns:
            dict: Processing decision
        """
        confidence_result = self.confidence_scorer.calculate_overall_confidence(detection_result)
        decision_result = self.confidence_scorer.make_decision(confidence_result)

        # Additional quality checks
        quality_metrics = detection_result.get('quality_metrics', {})
        image_quality = quality_metrics.get('overall_score', 0.0)

        # Reject if image quality is too poor
        if image_quality < 0.3:
            decision_result['decision'] = 'reject'
            decision_result['reason'] = 'poor_image_quality'

        # Flag for manual review if medium confidence
        if decision_result['confidence_level'] == 'medium':
            decision_result['requires_review'] = True

        return {
            'should_process': decision_result['decision'] in ['accept_high', 'accept_medium'],
            'confidence_result': confidence_result,
            'decision_result': decision_result,
            'requires_review': decision_result.get('requires_review', False)
        }

    def get_processing_priority(self, detection_result):
        """
        Get processing priority based on quality and confidence.

        Args:
            detection_result (dict): Detection result

        Returns:
            str: Priority level
        """
        confidence_result = self.confidence_scorer.calculate_overall_confidence(detection_result)
        score = confidence_result['overall_confidence']

        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        elif score >= 0.4:
            return 'low'
        else:
            return 'defer'