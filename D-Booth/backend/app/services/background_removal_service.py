"""
Background Removal Service using AI segmentation models
Gracefully degrades when dependencies are not available
"""

import io
import logging
from typing import Literal, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import optional dependencies
OPENCV_AVAILABLE = False
MEDIAPIPE_AVAILABLE = False
REMBG_AVAILABLE = False

try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV not available, background analysis will be limited")

try:
    import mediapipe as mp

    mp_selfie_segmentation = mp.solutions.selfie_segmentation
    selfie_segmenter = mp_selfie_segmentation.SelfieSegmentation(model_selection=1)
    MEDIAPIPE_AVAILABLE = True
except Exception as exc:
    mp_selfie_segmentation = None
    selfie_segmenter = None
    logger.warning("MediaPipe not available, AI background removal disabled: %s", exc)

try:
    from rembg import remove as rembg_remove

    REMBG_AVAILABLE = True
except ImportError:
    logger.warning("rembg not available, fallback to MediaPipe if available")


class BackgroundRemovalService:
    """
    Service for AI-powered background removal
    Supports multiple backends with graceful degradation
    """

    def __init__(self):
        self.opencv_available = OPENCV_AVAILABLE
        self.mediapipe_available = MEDIAPIPE_AVAILABLE
        self.rembg_available = REMBG_AVAILABLE
        logger.info(
            f"Background removal service initialized: "
            f"OpenCV={self.opencv_available}, "
            f"MediaPipe={self.mediapipe_available}, "
            f"rembg={self.rembg_available}"
        )

    def remove_background_ai(
        self, image: np.ndarray, model: Literal["mediapipe", "rembg", "u2net"] = "mediapipe"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Remove background using AI segmentation
        Returns: (foreground_rgba, mask)
        If no AI models available, returns original image with full alpha
        """
        if not (self.mediapipe_available or self.rembg_available):
            logger.warning("No AI background removal models available, returning original image")
            # Create RGBA image with full alpha
            rgba = (
                cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
                if self.opencv_available
                else self._numpy_to_rgba(image)
            )
            mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255
            return rgba, mask

        try:
            # Try rembg first if requested and available
            if model == "rembg" and self.rembg_available:
                return self._remove_background_rembg(image)

            # Fallback to MediaPipe
            if self.mediapipe_available:
                return self._remove_background_mediapipe(image)

            # Last resort: return original
            logger.warning("Requested AI model not available, returning original image")
            rgba = (
                cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
                if self.opencv_available
                else self._numpy_to_rgba(image)
            )
            mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255
            return rgba, mask

        except Exception as e:
            logger.error(f"AI background removal failed: {str(e)}", exc_info=True)
            # Return original image on error
            rgba = (
                cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
                if self.opencv_available
                else self._numpy_to_rgba(image)
            )
            mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255
            return rgba, mask

    def _remove_background_mediapipe(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Remove background using MediaPipe Selfie Segmentation"""
        if not self.mediapipe_available or not self.opencv_available:
            raise RuntimeError("MediaPipe or OpenCV not available")

        # Convert BGR to RGB for MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process with MediaPipe
        results = selfie_segmenter.process(image_rgb)
        mask = results.segmentation_mask

        # Post-process mask
        mask = (mask > 0.5).astype(np.uint8) * 255

        # Smooth mask edges
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        # Create RGBA image
        b, g, r = cv2.split(image)
        rgba = cv2.merge((b, g, r, mask))

        return rgba, mask

    def _remove_background_rembg(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Remove background using rembg library"""
        if not self.rembg_available:
            raise RuntimeError("rembg not available")

        # Convert numpy array to PIL Image
        img_pil = Image.fromarray(
            cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if self.opencv_available else image
        )

        # Process with rembg
        result_pil = rembg_remove(img_pil)

        # Convert back to numpy array
        result_np = np.array(result_pil)

        # Extract mask and RGBA
        rgba = cv2.cvtColor(result_np, cv2.COLOR_RGBA2BGRA) if self.opencv_available else result_np
        mask = result_np[:, :, 3]

        return rgba, mask

    def score_background_complexity(self, image: np.ndarray) -> float:
        """
        Evaluate background complexity
        Returns score between 0 (complex) and 1 (simple solid color)
        """
        if not self.opencv_available:
            logger.warning("OpenCV not available, returning default complexity score")
            return 0.5  # Neutral score

        try:
            # Convert to HSV for color analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)

            # Calculate variance of hue channel
            hue_variance = np.var(h)
            sat_variance = np.var(s)
            val_variance = np.var(v)

            # Normalize variances (lower variance = more uniform)
            max_hue_var = 3000  # Empirical value
            max_sat_var = 5000
            max_val_var = 8000

            hue_score = 1 - min(hue_variance / max_hue_var, 1)
            sat_score = 1 - min(sat_variance / max_sat_var, 1)
            val_score = 1 - min(val_variance / max_val_var, 1)

            # Weighted average
            complexity_score = hue_score * 0.5 + sat_score * 0.3 + val_score * 0.2

            return float(complexity_score)

        except Exception as e:
            logger.error(f"Background complexity analysis failed: {str(e)}")
            return 0.5

    def detect_green_background(
        self, image: np.ndarray, threshold: float = 0.3
    ) -> Tuple[bool, int]:
        """
        Detect if background is primarily green
        Returns: (is_green_background, suggested_sensitivity)
        """
        if not self.opencv_available:
            return False, 50

        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Standard green range in HSV
            lower_green = np.array([35, 40, 40])
            upper_green = np.array([75, 255, 255])

            # Create mask
            mask = cv2.inRange(hsv, lower_green, upper_green)

            # Calculate percentage of green pixels
            green_ratio = np.sum(mask > 0) / (image.shape[0] * image.shape[1])

            # Suggest sensitivity based on green purity
            suggested_sensitivity = 50
            if green_ratio > 0.7:
                suggested_sensitivity = 40
            elif green_ratio > 0.5:
                suggested_sensitivity = 55
            else:
                suggested_sensitivity = 70

            return green_ratio > threshold, suggested_sensitivity

        except Exception as e:
            logger.error(f"Green background detection failed: {str(e)}")
            return False, 50

    @staticmethod
    def _numpy_to_rgba(image: np.ndarray) -> np.ndarray:
        """Convert RGB/BGR numpy array to RGBA with full alpha"""
        if len(image.shape) == 3 and image.shape[2] == 3:
            alpha = np.ones((image.shape[0], image.shape[1], 1), dtype=np.uint8) * 255
            return np.concatenate([image, alpha], axis=2)
        return image


# Singleton instance
background_removal_service = BackgroundRemovalService()
