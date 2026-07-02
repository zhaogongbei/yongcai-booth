"""
Green Screen Processing Service
Chroma key (green screen) background removal and compositing
Gracefully degrades when dependencies are not available
"""
import io
import logging
import numpy as np
from typing import Tuple, Optional, List, Literal
from PIL import Image

from app.schemas.green_screen import GreenScreenSettingsBase
from .background_removal_service import background_removal_service

logger = logging.getLogger(__name__)

# Try to import optional dependencies
OPENCV_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV not available, green screen service will return original images")


class GreenScreenService:
    """
    Service for green screen processing including chroma key removal and background compositing
    Gracefully degrades to return original image if dependencies are missing
    """

    def __init__(self):
        self.opencv_available = OPENCV_AVAILABLE
        self.background_removal = background_removal_service
        logger.info(f"Green screen service initialized: OpenCV={self.opencv_available}")

    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color string (e.g. "#00FF00") to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hsv(self, r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space"""
        if not self.opencv_available:
            return (0, 0, 0)
        rgb = np.uint8([[[b, g, r]]])  # OpenCV uses BGR
        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        return (hsv[0][0][0], hsv[0][0][1], hsv[0][0][2])

    def chroma_key_remove(
        self,
        image: np.ndarray,
        color_to_remove: str = "#00FF00",
        sensitivity: int = 50,
        smoothness: int = 30,
        use_flash: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Remove background using chroma key technique
        Returns: (foreground_rgba, mask)
        """
        if not self.opencv_available:
            logger.warning("OpenCV not available, returning original image")
            # Create RGBA image with full alpha
            rgba = self._numpy_to_rgba(image)
            mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255
            return rgba, mask

        try:
            # Convert target color to HSV
            r, g, b = self.hex_to_rgb(color_to_remove)
            target_h, target_s, target_v = self.rgb_to_hsv(r, g, b)

            # Convert image to HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Adjust sensitivity (0-100 to actual threshold ranges)
            hue_tolerance = int((sensitivity / 100) * 30 + 10)  # 10-40
            sat_tolerance = int((sensitivity / 100) * 100 + 50)  # 50-150
            val_tolerance = int((sensitivity / 100) * 100 + 50)  # 50-150

            # Adjust for flash mode (wider tolerance for uneven lighting)
            if use_flash:
                hue_tolerance = int(hue_tolerance * 1.2)
                val_tolerance = int(val_tolerance * 1.3)

            # Create color range
            lower_hsv = np.array([
                max(0, target_h - hue_tolerance),
                max(0, target_s - sat_tolerance),
                max(0, target_v - val_tolerance)
            ])
            upper_hsv = np.array([
                min(179, target_h + hue_tolerance),
                min(255, target_s + sat_tolerance),
                min(255, target_v + val_tolerance)
            ])

            # Create mask
            mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

            # Invert mask: we want to keep foreground, remove background
            mask = cv2.bitwise_not(mask)

            # Apply smoothing
            if smoothness > 0:
                # Convert smoothness 0-100 to kernel size
                kernel_size = int((smoothness / 100) * 10 + 1)
                if kernel_size % 2 == 0:
                    kernel_size += 1

                # Gaussian blur for soft edges
                mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)

                # Morphological operations to remove noise
                morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, morph_kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, morph_kernel)

            # Apply despill (remove green reflections from foreground)
            image = self._apply_despill(image, mask, color_to_remove)

            # Create RGBA image
            b, g, r = cv2.split(image)
            rgba = cv2.merge((b, g, r, mask))

            return rgba, mask

        except Exception as e:
            logger.error(f"Chroma key removal failed: {str(e)}", exc_info=True)
            # Return original image on error
            rgba = self._numpy_to_rgba(image)
            mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255
            return rgba, mask

    def _apply_despill(self, image: np.ndarray, mask: np.ndarray, color_to_remove: str) -> np.ndarray:
        """Remove color spill (reflections) from foreground edges"""
        if not self.opencv_available:
            return image

        try:
            # For green screen, reduce green channel in edge areas
            if color_to_remove.lower() in ["#00ff00", "00ff00", "green", "#0f0"]:
                # Create edge mask (areas where mask is not fully opaque or transparent)
                edge_mask = cv2.inRange(mask, 10, 245)
                if np.sum(edge_mask) > 0:
                    # Split channels
                    b, g, r = cv2.split(image)

                    # Reduce green channel in edge areas
                    g[edge_mask > 0] = np.minimum(g[edge_mask > 0], (r[edge_mask > 0] + b[edge_mask > 0]) // 2)

                    # Merge back
                    image = cv2.merge((b, g, r))

            return image

        except Exception as e:
            logger.warning(f"Despill failed: {str(e)}")
            return image

    def composite_background(
        self,
        foreground_rgba: np.ndarray,
        background: np.ndarray,
        overlay: Optional[np.ndarray] = None,
        output_size: Tuple[int, int] = (1800, 1200)
    ) -> np.ndarray:
        """
        Composite foreground with background and optional overlay
        output_size: (width, height)
        """
        if not self.opencv_available:
            logger.warning("OpenCV not available, returning foreground")
            return foreground_rgba[:, :, :3]  # Return RGB without alpha

        try:
            # Resize foreground to output size
            fg_h, fg_w = foreground_rgba.shape[:2]
            target_w, target_h = output_size

            # Calculate scaling to fit while preserving aspect ratio
            scale = max(target_w / fg_w, target_h / fg_h)
            new_w = int(fg_w * scale)
            new_h = int(fg_h * scale)
            foreground_resized = cv2.resize(foreground_rgba, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Crop to exact size
            x_offset = (new_w - target_w) // 2
            y_offset = (new_h - target_h) // 2
            foreground_cropped = foreground_resized[y_offset:y_offset+target_h, x_offset:x_offset+target_w]

            # Resize background to output size
            background_resized = self._resize_and_crop(background, target_w, target_h)

            # Split alpha channel
            if foreground_cropped.shape[2] == 4:
                alpha = foreground_cropped[:, :, 3] / 255.0
                alpha = np.expand_dims(alpha, axis=2)
                foreground_rgb = foreground_cropped[:, :, :3]
            else:
                alpha = np.ones((target_h, target_w, 1), dtype=np.float32)
                foreground_rgb = foreground_cropped

            # Composite foreground and background
            composite = (foreground_rgb * alpha + background_resized * (1 - alpha)).astype(np.uint8)

            # Apply overlay if present (overlay is on top of everything)
            if overlay is not None:
                overlay_resized = self._resize_and_crop(overlay, target_w, target_h)
                if overlay_resized.shape[2] == 4:
                    overlay_alpha = overlay_resized[:, :, 3] / 255.0
                    overlay_alpha = np.expand_dims(overlay_alpha, axis=2)
                    overlay_rgb = overlay_resized[:, :, :3]
                    composite = (overlay_rgb * overlay_alpha + composite * (1 - overlay_alpha)).astype(np.uint8)

            return composite

        except Exception as e:
            logger.error(f"Background compositing failed: {str(e)}", exc_info=True)
            # Return foreground if compositing fails
            return foreground_rgba[:, :, :3] if foreground_rgba.shape[2] == 4 else foreground_rgba

    def _resize_and_crop(self, image: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """Resize image to fit target size while preserving aspect ratio, then crop to exact dimensions"""
        if not self.opencv_available:
            return image

        h, w = image.shape[:2]

        # Scale to cover target size
        scale = max(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Resize
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Crop to exact size
        x_offset = (new_w - target_w) // 2
        y_offset = (new_h - target_h) // 2
        cropped = resized[y_offset:y_offset+target_h, x_offset:x_offset+target_w]

        return cropped

    def process_image(
        self,
        image: np.ndarray,
        settings: GreenScreenSettingsBase,
        background: Optional[np.ndarray] = None,
        overlay: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Process image with green screen settings
        Automatically selects algorithm based on mode
        """
        if not settings.enabled:
            # Return original image if green screen is disabled
            return image[:, :, :3] if len(image.shape) == 3 and image.shape[2] == 4 else image

        try:
            # Select algorithm based on mode
            if settings.mode == "chroma_key":
                foreground, mask = self.chroma_key_remove(
                    image,
                    color_to_remove=settings.color_to_remove,
                    sensitivity=settings.sensitivity,
                    smoothness=settings.smoothness,
                    use_flash=settings.use_flash
                )
            elif settings.mode == "ai_removal":
                foreground, mask = self.background_removal.remove_background_ai(image)
            else:  # auto mode
                # Analyze background to decide best algorithm
                complexity_score = self.background_removal.score_background_complexity(image)
                is_green, suggested_sensitivity = self.background_removal.detect_green_background(image)

                if is_green and complexity_score > 0.7:
                    # Simple green background: use chroma key
                    foreground, mask = self.chroma_key_remove(
                        image,
                        color_to_remove=settings.color_to_remove,
                        sensitivity=suggested_sensitivity,
                        smoothness=settings.smoothness,
                        use_flash=settings.use_flash
                    )
                else:
                    # Complex background: use AI removal
                    foreground, mask = self.background_removal.remove_background_ai(image)

            # Composite with background if provided
            if background is not None:
                # Parse output size
                if settings.output_size == "1800x1200":
                    output_size = (1800, 1200)
                elif settings.output_size == "max":
                    output_size = (image.shape[1], image.shape[0])
                else:  # template (default)
                    output_size = (1800, 1200)  # Will be replaced with actual template size later

                composite = self.composite_background(foreground, background, overlay, output_size)
                return composite
            else:
                # Return foreground with alpha if no background provided
                return foreground

        except Exception as e:
            logger.error(f"Green screen processing failed: {str(e)}", exc_info=True)
            # Return original image on error
            return image[:, :, :3] if len(image.shape) == 3 and image.shape[2] == 4 else image

    def analyze_test_photo(self, image: np.ndarray) -> dict:
        """Analyze test photo and provide recommendations"""
        if not self.opencv_available:
            return {
                "complexity_score": 0.5,
                "recommended_mode": "ai_removal",
                "is_green_background": False,
                "suggested_sensitivity": 50,
                "suggestions": ["OpenCV not available, limited analysis"]
            }

        try:
            complexity_score = self.background_removal.score_background_complexity(image)
            is_green, suggested_sensitivity = self.background_removal.detect_green_background(image)

            suggestions = []
            if is_green:
                suggestions.append("Detected green background - chroma key mode is recommended")
                if complexity_score > 0.8:
                    suggestions.append("Background is very uniform - lower sensitivity for better results")
                elif complexity_score < 0.5:
                    suggestions.append("Background has uneven lighting - increase sensitivity or use flash")
            else:
                suggestions.append("No green background detected - AI removal mode is recommended")

            if complexity_score > 0.7:
                recommended_mode = "chroma_key"
                suggestions.append("Background is simple - chroma key will be fast and accurate")
            else:
                recommended_mode = "ai_removal"
                suggestions.append("Background is complex - AI removal will provide better results")

            return {
                "complexity_score": float(complexity_score),
                "recommended_mode": recommended_mode,
                "is_green_background": is_green,
                "suggested_sensitivity": suggested_sensitivity,
                "suggestions": suggestions
            }

        except Exception as e:
            logger.error(f"Test photo analysis failed: {str(e)}")
            return {
                "complexity_score": 0.5,
                "recommended_mode": "ai_removal",
                "is_green_background": False,
                "suggested_sensitivity": 50,
                "suggestions": ["Analysis failed, using default settings"]
            }

    @staticmethod
    def _numpy_to_rgba(image: np.ndarray) -> np.ndarray:
        """Convert RGB/BGR numpy array to RGBA with full alpha"""
        if len(image.shape) == 3 and image.shape[2] == 3:
            alpha = np.ones((image.shape[0], image.shape[1], 1), dtype=np.uint8) * 255
            return np.concatenate([image, alpha], axis=2)
        return image


# Singleton instance
green_screen_service = GreenScreenService()